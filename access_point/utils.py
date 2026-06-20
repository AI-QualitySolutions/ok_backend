from django.conf import settings
from django.core.exceptions import PermissionDenied


def match_router_key(provided_key):
    if settings.ROUTER_SECRET_KEY != provided_key:
        raise PermissionDenied("Invalid router secret key.")
    return True
