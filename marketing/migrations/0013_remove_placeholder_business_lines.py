from django.db import migrations

# Generic starter values that were seeded by 0011 but are not part of the real
# business-line set (Retail / Junior / Business per product voice notes).
PLACEHOLDER_BUSINESS_LINES = ("Consumer", "Youth", "Enterprise")


def _norm(value: str) -> str:
    return (value or "").strip().casefold()


def _remove_placeholder_business_lines(apps, schema_editor):
    """Drop unused placeholder business lines from existing databases.

    A placeholder is only removed when no invoice references it, so this never
    changes data that is actually in use; invoices keep their stored value either
    way because ``business_section`` is a plain text field, not a foreign key.
    """
    BusinessLine = apps.get_model("marketing", "BusinessLine")
    Invoice = apps.get_model("marketing", "Invoice")

    used = {
        _norm(section)
        for section in Invoice.objects.exclude(business_section="").values_list("business_section", flat=True)
    }
    for name in PLACEHOLDER_BUSINESS_LINES:
        normalized = _norm(name)
        if normalized in used:
            continue
        BusinessLine.objects.filter(normalized_name=normalized).delete()


def _restore_placeholder_business_lines(apps, schema_editor):
    """Recreate the placeholders so the migration is reversible."""
    BusinessLine = apps.get_model("marketing", "BusinessLine")
    for name in PLACEHOLDER_BUSINESS_LINES:
        BusinessLine.objects.get_or_create(normalized_name=_norm(name), defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [
        ("marketing", "0012_userteamaccess_can_import_excel"),
    ]

    operations = [
        migrations.RunPython(
            _remove_placeholder_business_lines,
            _restore_placeholder_business_lines,
        ),
    ]
