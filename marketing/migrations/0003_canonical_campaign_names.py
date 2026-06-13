import re
import unicodedata

from django.db import migrations

# Same map as marketing.importers.excel.CAMPAIGN_NAME_ALIASES, keyed by normalized form.
CAMPAIGN_NAME_ALIASES = {
    "on going": "Ongoing",
    "ongoing": "Ongoing",
    "on going campaign": "Ongoing",
}


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^\w\sآ-ی]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def canonicalize_campaigns(apps, schema_editor):
    Campaign = apps.get_model("marketing", "Campaign")
    Invoice = apps.get_model("marketing", "Invoice")
    BudgetLine = apps.get_model("marketing", "BudgetLine")

    for campaign in Campaign.objects.all():
        canonical = CAMPAIGN_NAME_ALIASES.get(normalize_name(campaign.name))
        if not canonical or canonical == campaign.name:
            continue

        # Merge into an existing canonical campaign for the same (year, team) if present,
        # otherwise rename in place so invoice/budget foreign keys stay intact.
        existing = (
            Campaign.objects.filter(name=canonical, year=campaign.year, team=campaign.team)
            .exclude(pk=campaign.pk)
            .first()
        )
        if existing:
            Invoice.objects.filter(campaign=campaign).update(campaign=existing)
            BudgetLine.objects.filter(campaign=campaign).update(campaign=existing)
            campaign.delete()
        else:
            campaign.name = canonical
            campaign.save(update_fields=["name"])


def noop_reverse(apps, schema_editor):
    # Canonicalization is not reversible; the original spelling variants are not recorded.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0002_add_team_aliases"),
    ]

    operations = [
        migrations.RunPython(canonicalize_campaigns, noop_reverse),
    ]
