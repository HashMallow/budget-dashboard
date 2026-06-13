from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from marketing.models import Contract, ContractStage, ContractStatusHistory, Role, Team, UserTeamAccess, Vendor
from marketing.permissions import (
    can_edit_contract,
    can_upload_contract_file,
    filter_contracts_for_user,
)

pytestmark = pytest.mark.django_db


def make_contract(*, team: Team | None, vendor: Vendor, title: str, end_date: date | None = None) -> Contract:
    return Contract.objects.create(
        title=title,
        vendor=vendor,
        team=team,
        stage=ContractStage.DRAFT,
        end_date=end_date,
        amount=Decimal("5000.00"),
    )


@pytest.fixture
def sample_data():
    user_model = get_user_model()
    growth = Team.objects.create(name="Growth", slug="growth")
    brand = Team.objects.create(name="Brand", slug="brand")
    vendor = Vendor.objects.create(name="Legal Vendor")
    growth_contract = make_contract(team=growth, vendor=vendor, title="Growth retainer")
    brand_contract = make_contract(team=brand, vendor=vendor, title="Brand agency deal")
    return {
        "user_model": user_model,
        "growth": growth,
        "brand": brand,
        "vendor": vendor,
        "growth_contract": growth_contract,
        "brand_contract": brand_contract,
    }


def test_superuser_sees_all_contracts(sample_data):
    admin = sample_data["user_model"].objects.create_superuser(username="admin", password="test-pass")

    visible_ids = set(filter_contracts_for_user(Contract.objects.all(), admin).values_list("id", flat=True))

    assert visible_ids == {sample_data["growth_contract"].id, sample_data["brand_contract"].id}


def test_team_editor_scoped_to_assigned_team(sample_data):
    editor = sample_data["user_model"].objects.create_user(username="growth-editor")
    UserTeamAccess.objects.create(user=editor, team=sample_data["growth"], role=Role.EDITOR)

    visible_ids = set(filter_contracts_for_user(Contract.objects.all(), editor).values_list("id", flat=True))

    assert visible_ids == {sample_data["growth_contract"].id}
    assert can_edit_contract(editor, sample_data["growth_contract"]) is True
    assert can_edit_contract(editor, sample_data["brand_contract"]) is False
    assert can_upload_contract_file(editor, sample_data["growth_contract"]) is True


def test_observer_cannot_edit_or_upload(sample_data):
    observer = sample_data["user_model"].objects.create_user(username="observer")
    UserTeamAccess.objects.create(user=observer, team=sample_data["growth"], role=Role.OBSERVER)

    assert can_edit_contract(observer, sample_data["growth_contract"]) is False
    assert can_upload_contract_file(observer, sample_data["growth_contract"]) is False


def test_stage_change_creates_history_and_sets_signed_at(sample_data):
    editor = sample_data["user_model"].objects.create_user(username="legal-editor")
    contract = sample_data["growth_contract"]

    contract.set_stage(ContractStage.SIGNED, changed_by=editor, note="Both legal teams approved")

    contract.refresh_from_db()
    history = ContractStatusHistory.objects.get(contract=contract)
    assert contract.stage == ContractStage.SIGNED
    assert contract.signed_at is not None
    assert history.old_stage == ContractStage.DRAFT
    assert history.new_stage == ContractStage.SIGNED
    assert history.changed_by == editor
    assert history.note == "Both legal teams approved"


def test_expiry_helpers(sample_data):
    soon = timezone.now().date() + timedelta(days=10)
    past = timezone.now().date() - timedelta(days=5)
    expiring = make_contract(team=sample_data["growth"], vendor=sample_data["vendor"], title="Expiring", end_date=soon)
    expired = make_contract(team=sample_data["growth"], vendor=sample_data["vendor"], title="Expired", end_date=past)

    assert expiring.is_expiring_soon is True
    assert expiring.is_expired is False
    assert expired.is_expired is True
    assert expired.is_expiring_soon is False
    assert sample_data["growth_contract"].days_until_expiry is None
