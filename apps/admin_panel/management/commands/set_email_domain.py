from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.admin_panel.models import System
from apps.admin_panel.utils import normalize_email_domain


class Command(BaseCommand):
    help = 'Change the locked university email domain for the system.'

    def add_arguments(self, parser):
        parser.add_argument('domain', help='New email domain, for example rmuti.ac.th')
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirm that you understand this affects registration and member email policy.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            raise CommandError('Refusing to change email domain without --yes.')

        domain = normalize_email_domain(options['domain'])
        try:
            validate_email(f'test@{domain}')
        except ValidationError as exc:
            raise CommandError(f'Invalid email domain: {domain}') from exc

        system = System.objects.first()
        if not system:
            raise CommandError('System settings do not exist.')

        old_domain = normalize_email_domain(system.email_domain)
        if old_domain == domain:
            self.stdout.write(self.style.WARNING(f'Email domain is already {domain}.'))
            return

        system.email_domain = domain
        system.save(update_fields=['email_domain'])
        self.stdout.write(self.style.SUCCESS(f'Email domain changed: {old_domain} -> {domain}'))
