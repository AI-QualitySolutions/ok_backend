from django.conf import settings

def add_base_url(path):
    from django.conf import settings
    if path and not path.startswith('http'):
        return f"{settings.BASE_URL}{settings.MEDIA_URL}{path}".replace('//', '/').replace(':/', '://')
    return path
