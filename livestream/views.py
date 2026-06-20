from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
 
from tent.models import Tent
from .models import LiveStream
from .serializers import LiveStreamSerializer
 
 
class LiveStreamListView(APIView):
    """
    GET /livestream/
    Returns all active LiveStream entries filtered by user role + optional tent_id.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request, format=None):
        user = request.user
        tent_ids_text = request.query_params.get('tent_id')
 
        # ── Resolve tents by user role ───────────────────────────
        if user.is_superuser:
            tents = Tent.objects.all()
        elif user.is_admin:
            tents = Tent.objects.filter(company=user.company)
        elif user.is_staff:
            tents = Tent.objects.filter(assigned_tent=user)
        else:
            tents = Tent.objects.none()
 
        # ── Optional tent filter from query param ────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = tents.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response(
                        {"detail": "No valid tents found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            except ValueError:
                return Response(
                    {"detail": "Invalid tent ID format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
 
        # ── Query only active streams for resolved tents ─────────
        queryset = LiveStream.objects.filter(
            Q(camera__tent__in=tents) &
            Q(is_active=True)
        ).select_related('camera__tent')
 
        serializer = LiveStreamSerializer(queryset, many=True)
 
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)