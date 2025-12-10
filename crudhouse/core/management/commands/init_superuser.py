from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings


class Command(BaseCommand):
    help = 'Create a superuser from settings'

    def handle(self, *args, **options):
        superuser_config = getattr(settings, 'SUPERUSER', {})
        username = superuser_config.get('username', 'admin')
        email = superuser_config.get('email', 'admin@example.com')
        password = superuser_config.get('password', 'admin')

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists')
            )
        else:
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully')
            )
