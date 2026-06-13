import pytest

from marketing.cost_buckets import (
    infer_cost_bucket_from_pseudo_team_name,
    is_pseudo_team_name,
    parent_team_name_for_bucket,
    team_spend_cost_buckets,
)
from marketing.models import CostBucket, Team

pytestmark = pytest.mark.django_db


def test_referral_and_sms_labels_are_not_teams():
    assert is_pseudo_team_name("Referral")
    assert is_pseudo_team_name("SMS")
    assert not is_pseudo_team_name("Growth")
    assert not is_pseudo_team_name("Retention")


def test_bucket_parent_teams_match_product_rules():
    assert parent_team_name_for_bucket(CostBucket.REFERRAL) == "Growth"
    assert parent_team_name_for_bucket(CostBucket.SMS) == "Retention"
    assert infer_cost_bucket_from_pseudo_team_name("Referral") == CostBucket.REFERRAL


def test_growth_and_retention_include_rollup_buckets():
    growth = Team.objects.create(name="Growth", slug="growth")
    retention = Team.objects.create(name="Retention", slug="retention")
    brand = Team.objects.create(name="Brand", slug="brand")

    assert team_spend_cost_buckets(growth) == [CostBucket.TEAM, CostBucket.REFERRAL]
    assert team_spend_cost_buckets(retention) == [CostBucket.TEAM, CostBucket.SMS]
    assert team_spend_cost_buckets(brand) == [CostBucket.TEAM]
