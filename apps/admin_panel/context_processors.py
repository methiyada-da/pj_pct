from .utils import get_system_email_domain


def system_config(request):
    email_domain = get_system_email_domain()
    return {
        'UNIVERSITY_EMAIL_DOMAIN': email_domain,
        'UNIVERSITY_EMAIL_SUFFIX': '@' + email_domain,
    }
