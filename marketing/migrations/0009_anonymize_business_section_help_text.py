from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketing", "0008_invoice_business_section"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="business_section",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Business segment from Excel Business Section (e.g. Consumer, Youth, Enterprise).",
                max_length=120,
            ),
        ),
    ]
