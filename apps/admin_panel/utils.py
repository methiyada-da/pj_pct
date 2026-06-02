DEFAULT_EMAIL_DOMAIN = 'rmuti.ac.th'


def normalize_email_domain(domain):
    domain = (domain or DEFAULT_EMAIL_DOMAIN).strip().lower().lstrip('@')
    return domain or DEFAULT_EMAIL_DOMAIN


def get_system_email_domain():
    from django.db import OperationalError, ProgrammingError
    from .models import System

    try:
        system = System.objects.first()
    except (OperationalError, ProgrammingError):
        return DEFAULT_EMAIL_DOMAIN
    return normalize_email_domain(getattr(system, 'email_domain', ''))


def get_system_email_suffix():
    return '@' + get_system_email_domain()
