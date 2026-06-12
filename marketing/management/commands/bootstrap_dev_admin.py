from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a local development admin user. Refuses to run when DEBUG is false."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("ADMIN_USER", "admin"))
        parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@example.com"))
        parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("bootstrap_dev_admin is only allowed when DEBUG=True.")

        password = options["password"]
        if not password:
            raise CommandError("Pass --password or set ADMIN_PASSWORD.")

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username=options["username"])
        user.email = options["email"]
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        admin_group, _ = Group.objects.get_or_create(name="Admin")
        user.groups.add(admin_group)

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} local admin user: {user.username}"))
