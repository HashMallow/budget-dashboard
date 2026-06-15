from __future__ import annotations

from django.db.models import QuerySet

from marketing.models import CostBucket, Team, normalize_name

# Workbook labels that mark cost buckets, not marketing teams (per product voice notes).
_REFERRAL_PSEUDO_NAMES = frozenset(
    {
        normalize_name("Referral"),
        normalize_name("referral"),
        normalize_name("ریفرال"),
    }
)
_SMS_PSEUDO_NAMES = frozenset(
    {
        normalize_name("SMS"),
        normalize_name("sms"),
        normalize_name("پیامک"),
        normalize_name("اس ام اس"),
    }
)
PSEUDO_TEAM_NORMALIZED_NAMES = _REFERRAL_PSEUDO_NAMES | _SMS_PSEUDO_NAMES

PSEUDO_TEAM_SLUGS = frozenset({"referral", "sms"})

# Referral and SMS roll up to configured parent teams while remaining separate cost buckets.
BUCKET_PARENT_TEAM_NAMES: dict[str, str] = {
    CostBucket.REFERRAL: "Growth",
    CostBucket.SMS: "Retention",
}

TEAM_ROLLUP_BUCKETS: dict[str, str] = {
    normalize_name("Growth"): CostBucket.REFERRAL,
    normalize_name("Retention"): CostBucket.SMS,
}

REFERRAL_SMS_BUCKETS = frozenset({CostBucket.REFERRAL, CostBucket.SMS})


def is_pseudo_team_name(name: str) -> bool:
    return bool(name) and normalize_name(name) in PSEUDO_TEAM_NORMALIZED_NAMES


def infer_cost_bucket_from_pseudo_team_name(name: str) -> str | None:
    normalized = normalize_name(name)
    if normalized in _REFERRAL_PSEUDO_NAMES:
        return CostBucket.REFERRAL
    if normalized in _SMS_PSEUDO_NAMES:
        return CostBucket.SMS
    return None


def parent_team_name_for_bucket(cost_bucket: str) -> str | None:
    return BUCKET_PARENT_TEAM_NAMES.get(cost_bucket)


def rollup_cost_bucket_for_team(team: Team | None) -> str | None:
    if team is None:
        return None
    return TEAM_ROLLUP_BUCKETS.get(normalize_name(team.name))


def team_spend_cost_buckets(team: Team) -> list[str]:
    buckets = [CostBucket.TEAM]
    rollup = rollup_cost_bucket_for_team(team)
    if rollup:
        buckets.append(rollup)
    return buckets


def exclude_pseudo_teams(queryset: QuerySet[Team]) -> QuerySet[Team]:
    return queryset.exclude(slug__in=PSEUDO_TEAM_SLUGS)


def detect_cost_bucket_from_text(text: str) -> str | None:
    normalized = normalize_name(text)
    if not normalized:
        return None
    if normalized in _REFERRAL_PSEUDO_NAMES or "referral" in normalized or "ریفرال" in normalized:
        return CostBucket.REFERRAL
    if normalized in _SMS_PSEUDO_NAMES or "sms" in normalized or "پیامک" in normalized:
        return CostBucket.SMS
    return None
