import re
import unicodedata

from django.db import migrations

GENERIC_CAMPAIGN_NAMES = {
    "on going",
    "ongoing",
    "on going campaign",
    "ongoing campaign",
}


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^\w\sآ-ی]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def remove_generic_campaigns(apps, schema_editor):
    Campaign = apps.get_model("marketing", "Campaign")
    Invoice = apps.get_model("marketing", "Invoice")
    BudgetLine = apps.get_model("marketing", "BudgetLine")

    generic_ids = [
        campaign.id
        for campaign in Campaign.objects.all()
        if normalize_name(campaign.name) in GENERIC_CAMPAIGN_NAMES
    ]
    if not generic_ids:
        return

    Invoice.objects.filter(campaign_id__in=generic_ids).update(campaign=None)
    BudgetLine.objects.filter(campaign_id__in=generic_ids).update(campaign=None)
    Campaign.objects.filter(id__in=generic_ids).delete()


def noop_reverse(apps, schema_editor):
    # Generic placeholder campaigns were not meaningful source data.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0006_budgetline_unique_budget_line_source_row_month"),
    ]

    operations = [
        migrations.RunPython(remove_generic_campaigns, noop_reverse),
    ]
