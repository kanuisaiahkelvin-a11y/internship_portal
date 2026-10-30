import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = (
        'Create or update a coordinator superuser from environment variables. '
        'Optionally load the demo dataset.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            action='store_true',
            help='Load the demo dataset after creating the superuser.',
        )

    def handle(self, *args, **options):
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')

        if email and password:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': os.getenv('DJANGO_SUPERUSER_FIRST_NAME', 'Portal'),
                    'last_name': os.getenv('DJANGO_SUPERUSER_LAST_NAME', 'Admin'),
                    'role': User.Role.COORDINATOR,
                    'is_staff': True,
                    'is_superuser': True,
                },
            )
            user.first_name = os.getenv(
                'DJANGO_SUPERUSER_FIRST_NAME', user.first_name or 'Portal'
            )
            user.last_name = os.getenv(
                'DJANGO_SUPERUSER_LAST_NAME', user.last_name or 'Admin'
            )
            user.role = User.Role.COORDINATOR
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()

            action = 'created' if created else 'updated'
            self.stdout.write(self.style.SUCCESS(f'Superuser {action}: {email}'))
        else:
            self.stdout.write(
                'Skipping superuser creation: '
                'DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD are not set.'
            )

        if options['seed']:
            self.stdout.write('Loading demo data...')
            call_command('seed_demo')
