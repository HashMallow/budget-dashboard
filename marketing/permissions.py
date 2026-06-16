from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q, QuerySet

from .cost_buckets import REFERRAL_SMS_BUCKETS, exclude_pseudo_teams
from .models import BudgetLine, Campaign, Contract, CostBucket, Invoice, Role, Team, UserTeamAccess


@dataclass(frozen=True)
class UserScope:
    is_admin: bool
    is_global: bool
    team_ids: frozenset[int]
    roles: frozenset[str]
    can_view_referral_sms: bool
    can_export: bool
    can_upload_invoice_files: bool
    can_upload_payment_proofs: bool
    can_import_excel: bool


def user_has_admin_access(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name="Admin").exists()


def active_access_for_user(user) -> QuerySet[UserTeamAccess]:
    if not getattr(user, "is_authenticated", False):
        return UserTeamAccess.objects.none()
    return UserTeamAccess.objects.filter(user=user, is_active=True)


def get_user_scope(user) -> UserScope:
    if user_has_admin_access(user):
        return UserScope(
            is_admin=True,
            is_global=True,
            team_ids=frozenset(),
            roles=frozenset({Role.MANAGER, Role.EDITOR, Role.OBSERVER}),
            can_view_referral_sms=True,
            can_export=True,
            can_upload_invoice_files=True,
            can_upload_payment_proofs=True,
            can_import_excel=True,
        )

    accesses = list(
        active_access_for_user(user).values(
            "team_id",
            "role",
            "is_global",
            "can_view_referral_sms",
            "can_export",
            "can_upload_invoice_files",
            "can_upload_payment_proofs",
            "can_import_excel",
        )
    )
    return UserScope(
        is_admin=False,
        is_global=any(access["is_global"] for access in accesses),
        team_ids=frozenset(access["team_id"] for access in accesses if access["team_id"]),
        roles=frozenset(access["role"] for access in accesses),
        can_view_referral_sms=any(access["can_view_referral_sms"] for access in accesses),
        can_export=any(access["can_export"] for access in accesses),
        can_upload_invoice_files=any(access["can_upload_invoice_files"] for access in accesses),
        can_upload_payment_proofs=any(access["can_upload_payment_proofs"] for access in accesses),
        can_import_excel=any(access["can_import_excel"] for access in accesses),
    )


def filter_teams_for_user(queryset: QuerySet[Team], user) -> QuerySet[Team]:
    queryset = exclude_pseudo_teams(queryset)
    scope = get_user_scope(user)
    if scope.is_admin or scope.is_global:
        return queryset
    if not scope.team_ids:
        return queryset.none()
    return queryset.filter(id__in=scope.team_ids)


def filter_invoices_for_user(queryset: QuerySet[Invoice], user) -> QuerySet[Invoice]:
    scope = get_user_scope(user)
    if scope.is_admin or scope.is_global:
        return queryset
    if not scope.team_ids and not scope.can_view_referral_sms:
        return queryset.none()

    filters = Q()
    if scope.team_ids:
        filters |= Q(team_id__in=scope.team_ids)
    if scope.can_view_referral_sms:
        filters |= Q(cost_bucket__in=REFERRAL_SMS_BUCKETS)
    return queryset.filter(filters)


def filter_budget_lines_for_user(queryset: QuerySet[BudgetLine], user) -> QuerySet[BudgetLine]:
    scope = get_user_scope(user)
    if scope.is_admin or scope.is_global:
        return queryset
    if not scope.team_ids:
        return queryset.none()
    return queryset.filter(team_id__in=scope.team_ids)


def filter_campaigns_for_user(queryset: QuerySet[Campaign], user) -> QuerySet[Campaign]:
    scope = get_user_scope(user)
    if scope.is_admin or scope.is_global:
        return queryset
    if not scope.team_ids:
        return queryset.none()
    return queryset.filter(Q(team_id__in=scope.team_ids) | Q(team__isnull=True))


def can_view_invoice(user, invoice: Invoice) -> bool:
    return filter_invoices_for_user(Invoice.objects.filter(pk=invoice.pk), user).exists()


def _matching_accesses_for_invoice(user, invoice: Invoice) -> QuerySet[UserTeamAccess]:
    accesses = active_access_for_user(user)
    if invoice.cost_bucket in REFERRAL_SMS_BUCKETS and invoice.team_id:
        accesses = accesses.filter(Q(is_global=True) | Q(team_id=invoice.team_id) | Q(can_view_referral_sms=True))
    elif invoice.cost_bucket in REFERRAL_SMS_BUCKETS:
        accesses = accesses.filter(Q(is_global=True) | Q(can_view_referral_sms=True))
    elif invoice.team_id:
        accesses = accesses.filter(Q(is_global=True) | Q(team_id=invoice.team_id))
    else:
        accesses = accesses.filter(is_global=True)
    return accesses


def can_create_invoice_for_team(user, team: Team | None, cost_bucket: str = CostBucket.TEAM) -> bool:
    if user_has_admin_access(user):
        return True
    accesses = active_access_for_user(user).filter(role=Role.EDITOR)
    if cost_bucket in REFERRAL_SMS_BUCKETS and team is not None:
        accesses = accesses.filter(Q(is_global=True) | Q(team=team) | Q(can_view_referral_sms=True))
    elif cost_bucket in REFERRAL_SMS_BUCKETS:
        accesses = accesses.filter(Q(is_global=True) | Q(can_view_referral_sms=True))
    elif team is None:
        return accesses.filter(is_global=True).exists()
    else:
        accesses = accesses.filter(Q(is_global=True) | Q(team=team))
    return accesses.exists()


def can_edit_invoice(user, invoice: Invoice) -> bool:
    if user_has_admin_access(user):
        return True
    return _matching_accesses_for_invoice(user, invoice).filter(role=Role.EDITOR).exists()


def can_upload_invoice_file(user, invoice: Invoice) -> bool:
    if user_has_admin_access(user):
        return True
    return (
        _matching_accesses_for_invoice(user, invoice)
        .filter(
            role=Role.EDITOR,
            can_upload_invoice_files=True,
        )
        .exists()
    )


def can_upload_payment_proof(user, invoice: Invoice) -> bool:
    if user_has_admin_access(user):
        return True
    return (
        _matching_accesses_for_invoice(user, invoice)
        .filter(
            role=Role.EDITOR,
            can_upload_payment_proofs=True,
        )
        .exists()
    )


def can_export(user, scope=None) -> bool:
    if user_has_admin_access(user):
        return True
    return active_access_for_user(user).filter(can_export=True).exists()


def can_import(user) -> bool:
    if user_has_admin_access(user):
        return True
    return active_access_for_user(user).filter(can_import_excel=True).exists()


def filter_contracts_for_user(queryset: QuerySet[Contract], user) -> QuerySet[Contract]:
    scope = get_user_scope(user)
    if scope.is_admin or scope.is_global:
        return queryset
    if not scope.team_ids:
        return queryset.none()
    return queryset.filter(team_id__in=scope.team_ids)


def can_view_contract(user, contract: Contract) -> bool:
    return filter_contracts_for_user(Contract.objects.filter(pk=contract.pk), user).exists()


def can_create_contract_for_team(user, team: Team | None) -> bool:
    if user_has_admin_access(user):
        return True
    accesses = active_access_for_user(user).filter(role=Role.EDITOR)
    if team is None:
        return accesses.filter(is_global=True).exists()
    return accesses.filter(Q(is_global=True) | Q(team=team)).exists()


def can_edit_contract(user, contract: Contract) -> bool:
    if user_has_admin_access(user):
        return True
    accesses = active_access_for_user(user).filter(role=Role.EDITOR)
    if contract.team_id:
        accesses = accesses.filter(Q(is_global=True) | Q(team_id=contract.team_id))
    else:
        accesses = accesses.filter(is_global=True)
    return accesses.exists()


def can_upload_contract_file(user, contract: Contract) -> bool:
    # Whoever may edit a contract may also attach its documents (drafts/final text).
    return can_edit_contract(user, contract)


def user_can_create_contract(user) -> bool:
    scope = get_user_scope(user)
    return scope.is_admin or Role.EDITOR in scope.roles
