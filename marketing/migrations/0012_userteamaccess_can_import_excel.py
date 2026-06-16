from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketing", "0011_invoice_amounts_and_reference"),
    ]

    operations = [
        migrations.AddField(
            model_name="userteamaccess",
            name="can_import_excel",
            field=models.BooleanField(default=False),
        ),
    ]
