from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

GROUP_NAMES = ["Admin", "Manager", "Editor", "Observer"]


class Command(BaseCommand):
    help = "Create baseline auth groups used by the marketing dashboard."

    def handle(self, *args, **options):
        created = []
        existing = []
        for name in GROUP_NAMES:
            _, was_created = Group.objects.get_or_create(name=name)
            if was_created:
                created.append(name)
            else:
                existing.append(name)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created groups: {', '.join(created)}"))
        if existing:
            self.stdout.write(f"Already existed: {', '.join(existing)}")
