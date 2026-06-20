from django.core.exceptions import PermissionDenied

from .models import TuyaProxyApiKey


def get_api_key_record(provided_key):
    if not provided_key:
        return None
    return TuyaProxyApiKey.objects.filter(api_key=provided_key).first()


def validate_api_key(provided_key):
    if not provided_key:
        raise PermissionDenied("API key is required.")

    record = get_api_key_record(provided_key)
    if record is None:
        raise PermissionDenied("Invalid API key.")

    if not record.is_active:
        raise PermissionDenied("API key is inactive.")

    return record


def get_tuya_user_id(provided_key):
    return validate_api_key(provided_key).tuya_user_id
