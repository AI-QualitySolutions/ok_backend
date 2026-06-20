from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .services import fetch_user_devices
from .utils import validate_api_key


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_devices(request):
    api_key = request.headers.get("X-Api-Key")
    if not api_key:
        return Response(
            {
                "success": False,
                "message": "X-Api-Key header is required.",
                "code": status.HTTP_400_BAD_REQUEST,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        record = validate_api_key(api_key)
    except PermissionDenied as exc:
        return Response(
            {
                "success": False,
                "message": str(exc),
                "code": status.HTTP_403_FORBIDDEN,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        response = fetch_user_devices(record.tuya_user_id)
    except Exception as exc:
        return Response(
            {
                "success": False,
                "message": f"Failed to fetch devices from Tuya API: {exc}",
                "code": status.HTTP_502_BAD_GATEWAY,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not isinstance(response, dict):
        return Response(
            {
                "success": False,
                "message": "Unexpected response from Tuya API.",
                "code": status.HTTP_502_BAD_GATEWAY,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    response["message"] = (
        "Devices fetched successfully"
        if response.get("success")
        else response.get("msg", "Failed to fetch devices from Tuya API.")
    )
    response["code"] = (
        status.HTTP_200_OK
        if response.get("success")
        else status.HTTP_502_BAD_GATEWAY
    )

    return Response(
        response,
        status=status.HTTP_200_OK if response.get("success") else status.HTTP_502_BAD_GATEWAY,
    )
