import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the configured Django admin user if it does not exist"

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()

        if not username and not password and not email:
            self.stdout.write("Admin user is not configured; skipping.")
            return

        if not username or not password:
            raise CommandError(
                "Set both DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD."
            )

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        lookup = {username_field: username}
        user, created = user_model.objects.get_or_create(
            **lookup,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(f"Created admin user '{username}'.")
        elif not user.is_superuser or not user.is_staff:
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            self.stdout.write(f"Granted admin access to existing user '{username}'.")
        else:
            self.stdout.write(f"Admin user '{username}' already exists.")
