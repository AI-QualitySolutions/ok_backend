from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Router, RouterHeartbeat
from .serializers import DevicePayloadSerializer
from .utils import match_router_key

ACTIVE_THRESHOLD_MINUTES = 10

@api_view(['POST'])
def save_router_heartbeat(request):
    secret_key = request.headers.get('X-Secret-Key-Router')
    match_router_key(secret_key)

    serializer = DevicePayloadSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        
        # Get existing router or create a new one based on router_sn
        router_obj, created = Router.objects.update_or_create(
            SN=data['SN'],
            defaults={
                'ip_address': data.get('ip_address'),
                'mac_address': data.get('mac_address')
            }
        )
        
        # Create a new heartbeat record linked to this router
        RouterHeartbeat.objects.create(
            router=router_obj,
            heartbeat_time=data['heartbeat_time']
        )
        
        # Return success response
        return Response({
            "message": "Heartbeat saved successfully",
            "SN": router_obj.SN,
            "new_router_created": created
        }, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _router_status_data(router):
    threshold = timezone.now() - timedelta(minutes=ACTIVE_THRESHOLD_MINUTES)
    last_heartbeat = router.heartbeats.order_by('-heartbeat_time').first()
    if last_heartbeat is None:
        return {
            "SN": router.SN,
            "name": router.name,
            "is_active": False,
            "last_heartbeat": None,
        }
    return {
        "SN": router.SN,
        "name": router.name,
        "is_active": last_heartbeat.heartbeat_time >= threshold,
        "last_heartbeat": last_heartbeat.heartbeat_time,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def router_status(request):
    sn = request.query_params.get('sn')
    name = request.query_params.get('name')

    if not sn and not name:
        routers = Router.objects.all()
        return Response([_router_status_data(r) for r in routers])

    filters = {}
    if sn:
        filters['SN'] = sn
    if name:
        filters['name'] = name

    try:
        router = Router.objects.get(**filters)
    except Router.DoesNotExist:
        return Response(
            {"message": f"No router found matching the provided filters."},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(_router_status_data(router))