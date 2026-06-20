from django.conf import settings
from tuya_connector import TuyaOpenAPI


def fetch_user_devices(tuya_user_id):
    openapi = TuyaOpenAPI(
        settings.TUYA_API_ENDPOINT,
        settings.TUYA_ACCESS_ID,
        settings.TUYA_ACCESS_KEY,
    )
    openapi.connect()
    return openapi.get(f"/v1.0/users/{tuya_user_id}/devices")
