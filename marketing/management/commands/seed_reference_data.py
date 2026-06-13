from __future__ import annotations

from django.core.management.base import BaseCommand

from marketing.reference_data import seed_reference_data_from_workbook


class Command(BaseCommand):
    help = "Seed lookup/reference rows (vendors, categories, sub-teams, requesters) from the workbook Data sheet."

    def add_arguments(self, parser):
        parser.add_argument("--file", dest="workbook", default=None, help="Path to the Excel workbook.")
        parser.add_argument(
            "--mapping",
            default="docs/discovery/column_mapping.yml",
            help="Path to column_mapping.yml.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Preview counts without writing to the database.")

    def handle(self, *args, **options):
        result = seed_reference_data_from_workbook(
            options["workbook"],
            mapping_path=options["mapping"],
            dry_run=options["dry_run"],
        )
        prefix = "Dry-run" if result.dry_run else "Seeded"
        self.stdout.write(f"{prefix} reference data from {result.workbook.name}")
        for label, counter in [
            ("Vendors", result.vendors),
            ("Categories", result.categories),
            ("Sub teams", result.sub_teams),
            ("Requesters", result.requesters),
        ]:
            self.stdout.write(
                f"  {label}: created={counter.created}, updated={counter.updated}, skipped={counter.skipped}"
            )
