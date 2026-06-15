from django.db import migrations, models


def backfill_business_section(apps, schema_editor):
    Invoice = apps.get_model("marketing", "Invoice")
    for invoice in Invoice.objects.iterator():
        raw = invoice.raw_data_json or {}
        value = raw.get("Business Section", "")
        text = " ".join(str(value or "").split()).strip()
        if text and invoice.business_section != text:
            invoice.business_section = text
            invoice.save(update_fields=["business_section"])


class Migration(migrations.Migration):
    dependencies = [
        ("marketing", "0007_remove_generic_ongoing_campaigns"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="business_section",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Business segment from Excel Business Section (e.g. Consumer, Youth, Enterprise).",
                max_length=120,
            ),
        ),
        migrations.RunPython(backfill_business_section, migrations.RunPython.noop),
    ]
