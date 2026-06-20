import pytz
from datetime import datetime, timedelta
from django.db.models import Count, OuterRef, Q, Subquery
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import HttpResponse
import csv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from django.utils.timezone import make_aware, is_naive, now, localtime
from io import StringIO
from authentication.models import Company
from authentication.utils import standard_response

from camera.models import (
    Camera, KitchenViolationReport,
    GuardPresenceHistory, AGGFViolationReport, SmokingViolationReport,
    FaceDetectionReport, GarbageMonitoringReport, RecycleMonitoringReport, FallDetectionMonitoringReport,
    ViolenceMonitoringReport, CrowdMonitoringReport, type_choices,
    BuffetViolationReport, BathroomMonitoringHistory, SentimentAnalysis,
    WallClimbMonitoringReport, AbnormalActivities,
)
from authentication.models import MyUser
from utils.pagination import paginate_queryset
from .models import DeviceActivityLog, OrangePiDevice
from .serializers import (
    CAMERA_HEARTBEAT_ONLINE_WINDOW,
    CameraBriefSerializer,
    CameraDeliveryBucketSerializer,
    CameraDetailSerializer,
    CompanyWithTentsSerializer,
    DeviceActivityLogSerializer,
    KitchenViolationSerializer,
    OrangePiDeviceSerializer,
)

RIYADH_TZ = pytz.timezone("Asia/Riyadh")

CAMERA_DELIVERY_INTERVAL_TYPES = {
    'hour': timedelta(hours=1),
    'day': timedelta(days=1),
}


def _format_riyadh(dt):
    return dt.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _activity_log_summary_for_devices(device_qs, device_type, log_fk_name):
    """
    Count total registered devices and online/offline from each device's latest
    DeviceActivityLog row (devices with no log count as offline).
    """
    latest_status = (
        DeviceActivityLog.objects
        .filter(device_type=device_type, **{log_fk_name + '__isnull': False})
        .filter(**{log_fk_name: OuterRef('pk')})
        .order_by('-timestamp')
        .values('status')[:1]
    )
    annotated = device_qs.annotate(latest_status=Subquery(latest_status))
    stats = annotated.aggregate(
        total=Count('pk'),
        online=Count('pk', filter=Q(latest_status='online')),
    )
    return stats['total'], stats['online']


def _camera_online_q(threshold):
    """Same rules as CameraBriefSerializer.get_is_online — DB-side for aggregates."""
    return Q(heartbeat__updated_at__gte=threshold) | Q(
        heartbeat__updated_at__isnull=True,
        heartbeat__time__gte=threshold,
    )


def _filtered_camera_queryset(request):
    """
    Apply optional type / tent_id filters shared by camera list and summary.
    Returns (queryset, error_response) where error_response is set on bad tent_id.
    """
    queryset = Camera.objects.all().order_by('id')

    camera_type = request.query_params.get('type')
    if camera_type:
        queryset = queryset.filter(type=camera_type)

    tent_id = request.query_params.get('tent_id')
    if tent_id:
        try:
            queryset = queryset.filter(tent_id=int(tent_id))
        except ValueError:
            return None, Response(
                *standard_response(False, 'Invalid tent_id.', None, status.HTTP_400_BAD_REQUEST)
            )

    return queryset, None


def _discover_camera_event_models():
    """
    Return models that represent camera events generically.

    A model is included when it has a ForeignKey named `camera` pointing to
    Camera and a DateTimeField named `created_at`. This keeps the delivery
    status endpoint independent from specific camera types.
    """
    event_models = []

    for model in apps.get_models():
        try:
            camera_field = model._meta.get_field('camera')
            created_at_field = model._meta.get_field('created_at')
        except FieldDoesNotExist:
            continue

        if not isinstance(camera_field, models.ForeignKey):
            continue
        if camera_field.remote_field.model != Camera:
            continue
        if not isinstance(created_at_field, models.DateTimeField):
            continue

        event_models.append(model)

    return event_models


def _build_delivery_buckets(start_at, end_at, interval_delta, expected_event_every_seconds):
    buckets = []
    current = start_at

    while current < end_at:
        bucket_end = min(current + interval_delta, end_at)
        bucket_seconds = int((bucket_end - current).total_seconds())
        expected_count = bucket_seconds // expected_event_every_seconds
        buckets.append({
            'start': current,
            'end': bucket_end,
            'actual_count': 0,
            'expected_count': expected_count,
        })
        current = bucket_end

    return buckets


class CompanyTentListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            companies = Company.objects.prefetch_related('tent').annotate(
                _tent_count=Count('tent')).all()
            serializer = CompanyWithTentsSerializer(companies, many=True)
            return Response(
                *standard_response(
                    True,
                    'Companies with tents retrieved successfully.',
                    {
                        'count': companies.count(),
                        'companies': serializer.data
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class OrangePiHeartbeatView(APIView):
    """
    Called by each OrangePi every 60 seconds.
    Saves last_seen in Saudi (Riyadh) time.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            mac_address = request.data.get('mac_address')

            if not mac_address:
                return Response(
                    *standard_response(False, 'mac_address is required.', None, status.HTTP_400_BAD_REQUEST)
                )

            device = OrangePiDevice.objects.filter(mac_address=mac_address).first()
            if not device:
                return Response(
                    *standard_response(False, 'Device not registered.', None, status.HTTP_404_NOT_FOUND)
                )

            # Always store in Saudi time
            device.last_seen = timezone.now().astimezone(RIYADH_TZ)
            device.save()

            return Response(
                *standard_response(True, 'Heartbeat received.', {
                    'device': device.name,
                    'device_id': device.device_id,
                    'last_seen': device.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
                })
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class OrangePiDeviceListView(APIView):
    """
    Lists all OrangePi devices.
    is_online is calculated in real time:
    if last_seen >= now - 1 minute → online, else → offline.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            devices = OrangePiDevice.objects.select_related('company', 'tent').all()
            serializer = OrangePiDeviceSerializer(devices, many=True)

            total        = devices.count()
            online_count = devices.filter(online=True).count()

            return Response(
                *standard_response(
                    True,
                    'Devices retrieved successfully.',
                    {
                        'total': total,
                        'online': online_count,
                        'offline': total - online_count,
                        'devices': serializer.data
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class OrangePiSummaryView(APIView):
    """
    GET /technical-dashboard/oranges/summary/

    Returns total / online / offline for all registered Orange Pi devices.
    Status comes from the latest DeviceActivityLog row per device (celery task).
    Devices with no log yet count as offline.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            total, online = _activity_log_summary_for_devices(
                OrangePiDevice.objects.all(),
                'orange_pi',
                'orange_pi_device',
            )
            return Response(
                *standard_response(
                    True,
                    'Orange Pi summary retrieved successfully.',
                    {
                        'total': total,
                        'online': online,
                        'offline': total - online,
                    },
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class CameraSummaryView(APIView):
    """
    GET /technical-dashboard/camera/summary/

    Lightweight counts only (no camera rows). Same online rules as the list view:
    heartbeat updated_at, else time, within CAMERA_HEARTBEAT_ONLINE_WINDOW.

    Optional query params: type, tent_id (same as camera list).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            queryset, error_response = _filtered_camera_queryset(request)
            if error_response:
                return error_response

            now_riyadh = timezone.now().astimezone(RIYADH_TZ)
            threshold = now_riyadh - CAMERA_HEARTBEAT_ONLINE_WINDOW
            stats = queryset.aggregate(
                total=Count('pk'),
                online=Count('pk', filter=_camera_online_q(threshold)),
            )
            total = stats['total']
            online = stats['online']

            return Response(
                *standard_response(
                    True,
                    'Camera summary retrieved successfully.',
                    {
                        'total': total,
                        'online': online,
                        'offline': total - online,
                    },
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class CameraListView(APIView):
    """
    GET /technical-dashboard/camera/
    Optional query params: type, tent_id (each works independently or combined).
      page: page number (default 1)
      page_size: items per page (default 10, max 100)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            page        = request.query_params.get('page', 1)
            page_size_raw = request.query_params.get('page_size', 10)

            queryset, error_response = _filtered_camera_queryset(request)
            if error_response:
                return error_response

            queryset = queryset.select_related('tent__company', 'heartbeat')

            try:
                page_size = int(page_size_raw)
                page_size = min(max(1, page_size), 100)
            except (ValueError, TypeError):
                return Response(
                    *standard_response(False, 'Invalid page_size.', None, status.HTTP_400_BAD_REQUEST)
                )

            paginated_qs, _total_count, pagination_info = paginate_queryset(
                queryset, page, page_size
            )
            serializer = CameraBriefSerializer(paginated_qs, many=True)
            return Response(
                *standard_response(
                    True,
                    'Cameras retrieved successfully.',
                    {
                        'results':    serializer.data,
                        'pagination': pagination_info,
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class CameraDetailView(APIView):
    """
    GET /technical-dashboard/camera/<id>/
    Returns full details of a single camera including heartbeat and livestream info.
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            camera = (
                Camera.objects
                .select_related('tent', 'heartbeat', 'livestream')
                .filter(pk=pk)
                .first()
            )
            if not camera:
                return Response(
                    *standard_response(False, 'Camera not found.', None, status.HTTP_404_NOT_FOUND)
                )

            serializer = CameraDetailSerializer(camera)
            return Response(
                *standard_response(True, 'Camera retrieved successfully.', serializer.data)
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class CameraDeliveryStatusView(APIView):
    """
    GET /api/technical-dashboard/camera-delivery-status/

    Returns time-based delivery status for cameras filtered by type.
    The endpoint discovers all models with a `camera` ForeignKey and
    `created_at` field, then counts rows per camera across those models.

    Query params:
      - camera_type: required. One of the registered camera types
        (e.g. kitchen, guard, garbage, buffet, bathroom, etc.).
        Case-insensitive.
      - camera_sn: optional. Further filter to a specific camera serial
        number within the given type.
      - from_date: optional YYYY-MM-DD. Must be sent with to_date.
      - to_date: optional YYYY-MM-DD. Must be sent with from_date.
      - interval_value: optional positive integer. Default: 1.
      - interval_type: optional bucket unit: hour or day (case-insensitive). Default: hour.
      - expected_event_every_seconds: optional cadence - one expected event every N seconds.
        Default: 300 (expected one event every 5 minutes (5*60 seconds)).

    Default window:
      If from_date and to_date are omitted, the endpoint uses the previous
      complete clock hour in Asia/Riyadh (boundaries on the hour), not a rolling
      60-minute window. For example, if local time is between 23:00 and 23:59,
      the window is 22:00:00 through 22:59:59 inclusive of events before 23:00
      (i.e. [22:00, 23:00)).

    Response structure:
      - camera_type: the queried type.
      - total_cameras: number of cameras included.
      - interval: window and cadence metadata.
      - cameras: list of per-camera results, each containing:
        - camera: {id, sn, type, tent_id}
        - total_events_in_range: sum of events across all buckets.
        - buckets: list with actual_count, expected_count, missing_count,
          delivery_percent, status (ok | partial | missing).
    """
    permission_classes = [AllowAny]

    def _parse_window(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if bool(from_date) != bool(to_date):
            return None, None, 'from_date and to_date must be provided together.'

        if not from_date and not to_date:
            now = timezone.now().astimezone(RIYADH_TZ)
            end_at = now.replace(minute=0, second=0, microsecond=0)
            start_at = end_at - timedelta(hours=1)
            return start_at, end_at, None

        parsed_from = parse_date(from_date)
        parsed_to = parse_date(to_date)
        if not parsed_from:
            return None, None, 'Invalid from_date. Use YYYY-MM-DD.'
        if not parsed_to:
            return None, None, 'Invalid to_date. Use YYYY-MM-DD.'
        if parsed_from > parsed_to:
            return None, None, 'from_date must be before or equal to to_date.'

        start_at = RIYADH_TZ.localize(
            datetime.combine(parsed_from, datetime.min.time())
        )
        end_at = RIYADH_TZ.localize(
            datetime.combine(parsed_to, datetime.min.time())
        ) + timedelta(days=1)
        return start_at, end_at, None

    def _compute_camera_buckets(self, camera, start_at, end_at, interval_delta,
                                expected_event_every_seconds, event_models):
        """Build delivery buckets for a single camera."""
        buckets = _build_delivery_buckets(
            start_at, end_at, interval_delta, expected_event_every_seconds
        )
        total_events = 0

        for event_model in event_models:
            timestamps = event_model.objects.filter(
                camera=camera,
                created_at__gte=start_at,
                created_at__lt=end_at,
            ).values_list('created_at', flat=True)

            for created_at in timestamps:
                if not created_at:
                    continue
                event_time = created_at.astimezone(RIYADH_TZ)
                bucket_index = int(
                    (event_time - start_at).total_seconds()
                    // interval_delta.total_seconds()
                )
                if 0 <= bucket_index < len(buckets):
                    buckets[bucket_index]['actual_count'] += 1
                    total_events += 1

        response_buckets = []
        for bucket in buckets:
            actual_count = bucket['actual_count']
            expected_count = bucket['expected_count']
            missing_count = max(expected_count - actual_count, 0)
            delivery_percent = (
                round((actual_count / expected_count) * 100, 2)
                if expected_count else 0
            )

            if actual_count >= expected_count:
                bucket_status = 'ok'
            elif actual_count > 0:
                bucket_status = 'partial'
            else:
                bucket_status = 'missing'

            response_buckets.append({
                'bucket_start': _format_riyadh(bucket['start']),
                'bucket_end': _format_riyadh(bucket['end']),
                'actual_count': actual_count,
                'expected_count': expected_count,
                'missing_count': missing_count,
                'delivery_percent': delivery_percent,
                'status': bucket_status,
            })

        return response_buckets, total_events

    def get(self, request):
        try:
            camera_type_raw = request.query_params.get('camera_type', '').strip()
            camera_type = camera_type_raw.lower() if camera_type_raw else ''
            if not camera_type:
                return Response(
                    *standard_response(
                        False, 'camera_type is required.', None, status.HTTP_400_BAD_REQUEST
                    )
                )

            valid_types = [choice[0] for choice in type_choices]
            if camera_type not in valid_types:
                return Response(
                    *standard_response(
                        False,
                        f'Invalid camera_type. Use one of: {", ".join(valid_types)}.',
                        None,
                        status.HTTP_400_BAD_REQUEST,
                    )
                )

            cameras_qs = Camera.objects.select_related('tent').filter(type=camera_type)

            camera_sn = request.query_params.get('camera_sn', '').strip()
            if camera_sn:
                cameras_qs = cameras_qs.filter(sn=camera_sn)

            if not cameras_qs.exists():
                msg = (
                    f'No cameras found for type "{camera_type}".'
                    if not camera_sn
                    else f'No camera found with type "{camera_type}" and sn "{camera_sn}".'
                )
                return Response(
                    *standard_response(False, msg, None, status.HTTP_404_NOT_FOUND)
                )

            try:
                interval_value = int(request.query_params.get('interval_value', 1))
            except (TypeError, ValueError):
                return Response(
                    *standard_response(
                        False,
                        'interval_value must be an integer.',
                        None,
                        status.HTTP_400_BAD_REQUEST
                    )
                )

            if interval_value <= 0:
                return Response(
                    *standard_response(
                        False,
                        'interval_value must be greater than zero.',
                        None,
                        status.HTTP_400_BAD_REQUEST
                    )
                )

            interval_type_raw = (request.query_params.get('interval_type') or 'hour').strip()
            interval_type = interval_type_raw.lower() if interval_type_raw else 'hour'
            base_interval_delta = CAMERA_DELIVERY_INTERVAL_TYPES.get(interval_type)
            if not base_interval_delta:
                return Response(
                    *standard_response(
                        False,
                        'Invalid interval_type. Use one of: hour, day.',
                        None,
                        status.HTTP_400_BAD_REQUEST
                    )
                )
            interval_delta = base_interval_delta * interval_value

            try:
                expected_event_every_seconds = int(
                    request.query_params.get('expected_event_every_seconds', 300)
                )
            except (TypeError, ValueError):
                return Response(
                    *standard_response(
                        False,
                        'expected_event_every_seconds must be an integer.',
                        None,
                        status.HTTP_400_BAD_REQUEST
                    )
                )

            if expected_event_every_seconds <= 0:
                return Response(
                    *standard_response(
                        False,
                        'expected_event_every_seconds must be greater than zero.',
                        None,
                        status.HTTP_400_BAD_REQUEST
                    )
                )

            start_at, end_at, window_error = self._parse_window(request)
            if window_error:
                return Response(
                    *standard_response(False, window_error, None, status.HTTP_400_BAD_REQUEST)
                )

            event_models = _discover_camera_event_models()
            cameras_result = []

            for camera in cameras_qs:
                response_buckets, total_events = self._compute_camera_buckets(
                    camera, start_at, end_at, interval_delta,
                    expected_event_every_seconds, event_models
                )
                serializer = CameraDeliveryBucketSerializer(response_buckets, many=True)
                cameras_result.append({
                    'camera': {
                        'id': camera.id,
                        'sn': camera.sn,
                        'type': camera.type,
                        'tent_id': camera.tent_id,
                    },
                    'total_events_in_range': total_events,
                    'buckets': serializer.data,
                })

            return Response(
                *standard_response(
                    True,
                    'Camera delivery status retrieved successfully.',
                    {
                        'camera_type': camera_type,
                        'total_cameras': len(cameras_result),
                        'interval': {
                            'value': interval_value,
                            'type': interval_type,
                            'seconds': int(interval_delta.total_seconds()),
                            'expected_event_every_seconds': expected_event_every_seconds,
                            'window_start': _format_riyadh(start_at),
                            'window_end': _format_riyadh(end_at),
                        },
                        'cameras': cameras_result,
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class KitchenViolationListView(APIView):
    """
    GET /api/technical-dashboard/kitchen-model/
    Optional query params:
      - from_date: YYYY-MM-DD  (created_at >= from_date)
      - to_date:   YYYY-MM-DD  (created_at <= to_date)
      - page:      page number (default 1)
      - page_size: items per page (default 20, max 100)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from_date = request.query_params.get('from_date')
            to_date   = request.query_params.get('to_date')
            page      = request.query_params.get('page', 1)
            page_size = 100

            queryset = KitchenViolationReport.objects.select_related(
                'camera__tent'
            ).all().order_by('-created_at')

            if from_date:
                try:
                    queryset = queryset.filter(created_at__date__gte=from_date)
                except ValueError:
                    return Response(
                        *standard_response(False, 'Invalid from_date. Use YYYY-MM-DD.', None, status.HTTP_400_BAD_REQUEST)
                    )

            if to_date:
                try:
                    queryset = queryset.filter(created_at__date__lte=to_date)
                except ValueError:
                    return Response(
                        *standard_response(False, 'Invalid to_date. Use YYYY-MM-DD.', None, status.HTTP_400_BAD_REQUEST)
                    )

            paginated_qs, total_count, pagination_info = paginate_queryset(queryset, page, page_size)
            serializer = KitchenViolationSerializer(paginated_qs, many=True)
            return Response(
                *standard_response(
                    True,
                    'Kitchen violation reports retrieved successfully.',
                    {
                        'results':    serializer.data,
                        'pagination': pagination_info,
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class AnnotatorReportView(APIView):
    """
    GET /api/technical-dashboard/annotator-report/
    Optional query params:
      - annotator_id : filter to a single annotator
      - from_date    : YYYY-MM-DD
      - to_date      : YYYY-MM-DD
    """
    permission_classes = [AllowAny]

    MODELS = [
        ('kitchen_violation',   KitchenViolationReport),
        ('guard_presence',      GuardPresenceHistory),
        ('aggf_violation',      AGGFViolationReport),
        ('smoking_violation',   SmokingViolationReport),
        ('face_detection',      FaceDetectionReport),
        ('garbage_monitoring',  GarbageMonitoringReport),
        ('recycle_monitoring',  RecycleMonitoringReport),
        ('fall_detection',      FallDetectionMonitoringReport),
        ('violence_monitoring', ViolenceMonitoringReport),
        ('crowd_monitoring',    CrowdMonitoringReport),
    ]

    def get(self, request):
        try:
            annotator_id = request.query_params.get('annotator_id')
            from_date    = request.query_params.get('from_date')
            to_date      = request.query_params.get('to_date')

            annotators = MyUser.objects.filter(is_annotator=True)
            if annotator_id:
                annotators = annotators.filter(pk=annotator_id)

            counts_by_model = {}
            for key, Model in self.MODELS:
                qs = Model.objects.filter(is_annotated=True)
                if annotator_id:
                    qs = qs.filter(annotator_id=annotator_id)
                if from_date:
                    qs = qs.filter(updated_at__date__gte=from_date)
                if to_date:
                    qs = qs.filter(updated_at__date__lte=to_date)
                counts_by_model[key] = dict(
                    qs.values('annotator_id')
                    .annotate(c=Count('pk'))
                    .values_list('annotator_id', 'c')
                )

            results = []
            for annotator in annotators:
                breakdown = {}
                total = 0
                for key, _Model in self.MODELS:
                    count = counts_by_model[key].get(annotator.pk, 0)
                    breakdown[key] = count
                    total += count

                results.append({
                    'annotator_id':    annotator.pk,
                    'annotator_name':  annotator.username,
                    'annotator_email': annotator.email,
                    'total_annotated': total,
                    'breakdown':       breakdown,
                })

            return Response(
                *standard_response(
                    True,
                    'Annotator report retrieved successfully.',
                    {
                        'count':   len(results),
                        'results': results,
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


VALID_DEVICE_TYPES = {c[0] for c in DeviceActivityLog.DEVICE_TYPE_CHOICES}

DEVICE_IDENTIFIER_FILTERS = {
    'camera': lambda qs, val: qs.filter(camera__sn=val),
    'orange_pi': lambda qs, val: qs.filter(
        models.Q(orange_pi_device__device_id=val) |
        models.Q(orange_pi_device__mac_address=val)
    ),
    'access_point': lambda qs, val: qs.filter(access_point__SN=val),
}

DEVICE_ID_FK_MAP = {
    'camera': 'camera_id',
    'orange_pi': 'orange_pi_device_id',
    'access_point': 'access_point_id',
}


class ActivityLogListView(APIView):
    """
    GET /api/technical-dashboard/activity-logs/
    GET /api/technical-dashboard/activity-logs/cameras/
    GET /api/technical-dashboard/activity-logs/oranges/
    GET /api/technical-dashboard/activity-logs/access-points/

    Returns activity logs **grouped per device**. Each device entry includes
    summary fields (current_status, last_online, last_offline,
    current_status_since, current_status_duration_seconds) computed relative
    to the request time, plus its recent log entries.

    Query params:
      - device_type:       camera | orange_pi | access_point (optional on generic URL)
      - status:            online | offline  (filter devices whose *current* status matches)
      - from_date:         YYYY-MM-DD
      - to_date:           YYYY-MM-DD
      - device_id:         filter by device PK
      - device_identifier: filter by real-world id (camera sn, orange pi device_id/mac, router SN)
      - page:              page number (default 1)
      - page_size:         devices per page (default 20, max 100)
    """
    permission_classes = [AllowAny]

    def _apply_filters(self, queryset, request, device_type):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if from_date:
            queryset = queryset.filter(timestamp__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(timestamp__date__lte=to_date)

        device_id = request.query_params.get('device_id', '').strip()
        if device_id:
            if device_type and device_type in DEVICE_ID_FK_MAP:
                queryset = queryset.filter(**{DEVICE_ID_FK_MAP[device_type]: device_id})
            else:
                queryset = queryset.filter(
                    models.Q(camera_id=device_id) |
                    models.Q(orange_pi_device_id=device_id) |
                    models.Q(access_point_id=device_id)
                )

        device_identifier = request.query_params.get('device_identifier', '').strip()
        if device_identifier:
            if device_type and device_type in DEVICE_IDENTIFIER_FILTERS:
                queryset = DEVICE_IDENTIFIER_FILTERS[device_type](queryset, device_identifier)
            else:
                queryset = queryset.filter(
                    models.Q(camera__sn=device_identifier) |
                    models.Q(orange_pi_device__device_id=device_identifier) |
                    models.Q(orange_pi_device__mac_address=device_identifier) |
                    models.Q(access_point__SN=device_identifier)
                )

        return queryset

    def _device_info(self, log):
        """Extract device metadata from a log entry (already select_related)."""
        info = {
            'device_type': log.device_type,
            'device_id': None,
            'device_identifier': None,
            'device_name': None,
            'company_name': None,
            'tent_name': None,
        }
        if log.device_type == 'camera' and log.camera:
            cam = log.camera
            info['device_id'] = cam.id
            info['device_identifier'] = cam.sn
            info['device_name'] = cam.sn
            info['company_name'] = cam.tent.company.name if cam.tent and cam.tent.company else None
            info['tent_name'] = cam.tent.name if cam.tent else None
        elif log.device_type == 'orange_pi' and log.orange_pi_device:
            dev = log.orange_pi_device
            info['device_id'] = dev.id
            info['device_identifier'] = dev.device_id
            info['device_name'] = dev.name
            info['company_name'] = dev.company.name if dev.company else None
            info['tent_name'] = dev.tent.name if dev.tent else None
        elif log.device_type == 'access_point' and log.access_point:
            rt = log.access_point
            info['device_id'] = rt.id
            info['device_identifier'] = rt.SN
            info['device_name'] = rt.SN
        return info

    def get(self, request, device_type=None):
        try:
            now = timezone.now().astimezone(RIYADH_TZ)
            device_type = device_type or request.query_params.get('device_type', '').strip()

            log_status_filter = request.query_params.get('status', '').strip()
            if log_status_filter and log_status_filter not in ('online', 'offline'):
                return Response(
                    *standard_response(
                        False,
                        'Invalid status. Use one of: online, offline.',
                        None,
                        status.HTTP_400_BAD_REQUEST,
                    )
                )

            try:
                page = max(1, int(request.query_params.get('page', 1)))
                page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
            except (TypeError, ValueError):
                return Response(
                    *standard_response(
                        False,
                        'page and page_size must be integers.',
                        None,
                        status.HTTP_400_BAD_REQUEST,
                    )
                )

            queryset = DeviceActivityLog.objects.select_related(
                'camera__tent__company',
                'orange_pi_device__company',
                'orange_pi_device__tent',
                'access_point',
            ).order_by('-timestamp')

            if device_type:
                if device_type not in VALID_DEVICE_TYPES:
                    return Response(
                        *standard_response(
                            False,
                            f'Invalid device_type. Use one of: {", ".join(sorted(VALID_DEVICE_TYPES))}.',
                            None,
                            status.HTTP_400_BAD_REQUEST,
                        )
                    )
                queryset = queryset.filter(device_type=device_type)

            queryset = self._apply_filters(queryset, request, device_type)

            fk_field = DEVICE_ID_FK_MAP.get(device_type) if device_type else None

            if fk_field:
                device_keys = (
                    queryset.values(fk_field, 'device_type')
                    .distinct()
                    .order_by(fk_field)
                )
            else:
                device_keys = (
                    queryset.values('device_type', 'camera_id', 'orange_pi_device_id', 'access_point_id')
                    .distinct()
                    .order_by('device_type', 'camera_id', 'orange_pi_device_id', 'access_point_id')
                )

            device_keys_list = list(device_keys)

            results_all = []
            for key_row in device_keys_list:
                dt = key_row.get('device_type', device_type)
                fk = DEVICE_ID_FK_MAP.get(dt)
                if not fk:
                    continue

                device_pk = key_row.get(fk)
                if not device_pk:
                    continue

                logs = (
                    queryset
                    .filter(device_type=dt, **{fk: device_pk})
                    .order_by('-timestamp')
                )

                latest_log = logs.first()
                if not latest_log:
                    continue

                info = self._device_info(latest_log)

                last_online_log = logs.filter(status='online').first()
                last_offline_log = logs.filter(status='offline').first()

                current_status = latest_log.status
                current_status_since = latest_log.timestamp
                duration_seconds = int((now - current_status_since).total_seconds()) if current_status_since else 0

                if log_status_filter and current_status != log_status_filter:
                    continue

                log_entries = DeviceActivityLogSerializer(logs[:10], many=True).data

                results_all.append({
                    **info,
                    'current_status': current_status,
                    'last_online': _format_riyadh(last_online_log.timestamp) if last_online_log else None,
                    'last_offline': _format_riyadh(last_offline_log.timestamp) if last_offline_log else None,
                    'current_status_since': _format_riyadh(current_status_since),
                    'current_status_duration_seconds': max(duration_seconds, 0),
                    'logs': log_entries,
                })

            total_devices = len(results_all)
            start = (page - 1) * page_size
            end = start + page_size
            results = results_all[start:end]

            total_pages = (total_devices + page_size - 1) // page_size if total_devices else 0
            pagination_info = {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_devices,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'next_page': page + 1 if page < total_pages else None,
                'previous_page': page - 1 if page > 1 else None,
            }

            return Response(
                *standard_response(
                    True,
                    'Activity logs retrieved successfully.',
                    {
                        'results': results,
                        'pagination': pagination_info,
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class ActivitySummaryView(APIView):
    """
    GET /api/technical-dashboard/activity-summary/

    Returns per-device-type counts of current online/offline status based on
    the most recent activity log entry per device.

    Optional query param:
      - device_type: camera | orange_pi | access_point
    """
    permission_classes = [AllowAny]

    def _summarize_type(self, device_type, fk_field):
        latest_logs = (
            DeviceActivityLog.objects
            .filter(device_type=device_type, **{fk_field + '__isnull': False})
            .filter(**{fk_field: OuterRef(fk_field)})
            .order_by('-timestamp')
            .values('status')[:1]
        )

        logs_with_latest = (
            DeviceActivityLog.objects
            .filter(device_type=device_type, **{fk_field + '__isnull': False})
            .values(fk_field)
            .distinct()
            .annotate(latest_status=Subquery(latest_logs))
        )

        total = logs_with_latest.count()
        online = sum(1 for row in logs_with_latest if row['latest_status'] == 'online')

        return {
            'device_type': device_type,
            'total': total,
            'online': online,
            'offline': total - online,
        }

    def get(self, request):
        try:
            device_type = request.query_params.get('device_type', '').strip()

            type_fk_map = {
                'camera': 'camera_id',
                'orange_pi': 'orange_pi_device_id',
                'access_point': 'access_point_id',
            }

            if device_type:
                if device_type not in type_fk_map:
                    return Response(
                        *standard_response(
                            False,
                            f'Invalid device_type. Use one of: {", ".join(sorted(type_fk_map.keys()))}.',
                            None,
                            status.HTTP_400_BAD_REQUEST,
                        )
                    )
                summary = [self._summarize_type(device_type, type_fk_map[device_type])]
            else:
                summary = [
                    self._summarize_type(dt, fk)
                    for dt, fk in type_fk_map.items()
                ]

            totals = {
                'total': sum(s['total'] for s in summary),
                'online': sum(s['online'] for s in summary),
                'offline': sum(s['offline'] for s in summary),
            }

            return Response(
                *standard_response(
                    True,
                    'Activity summary retrieved successfully.',
                    {
                        'totals': totals,
                        'by_device_type': summary,
                    }
                )
            )
        except Exception as e:
            return Response(
                *standard_response(False, str(e), None, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )
            

class AnnotatorRankingView(APIView):
    #permission_classes = [IsAuthenticated]

    # --- NEW: Delete / Reject Method ---
    def delete(self, request, *args, **kwargs):
        # Frontend query params othoba body theke data nibe
        image_id = request.data.get('image_id') or request.GET.get('image_id')
        model_name = request.data.get('model_name') or request.GET.get('model_name')

        if not image_id or not model_name:
            return Response({
                "success": False,
                "message": "Both image_id and model_name are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        model_mapping = {
            "KitchenViolationReport": KitchenViolationReport,
            "AGGFViolationReport": AGGFViolationReport,
            "SmokingViolationReport": SmokingViolationReport,
            "FaceDetectionReport": FaceDetectionReport,
            "GuardPresenceHistory": GuardPresenceHistory,
            "GarbageMonitoringReport": GarbageMonitoringReport,
            "RecycleMonitoringReport": RecycleMonitoringReport,
            "BuffetViolationReport": BuffetViolationReport,
            "BathroomMonitoringHistory": BathroomMonitoringHistory,
            "SentimentAnalysis": SentimentAnalysis,
            "FallDetectionMonitoringReport": FallDetectionMonitoringReport,
            "ViolenceMonitoringReport": ViolenceMonitoringReport,
            "CrowdMonitoringReport": CrowdMonitoringReport,
            "WallClimbMonitoringReport": WallClimbMonitoringReport,
            "AbnormalActivities": AbnormalActivities,
        }

        target_model = model_mapping.get(model_name)
        if target_model:
            try:
                record = target_model.objects.get(id=image_id)
                
                # Soft delete logic based on WhatsApp requirement
                record.is_annotated = False
                record.is_reject = True
                record.save()
                
                return Response({
                    "success": True,
                    "message": f"Record successfully rejected and annotation removed."
                }, status=status.HTTP_200_OK)
                
            except target_model.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "No record found with this ID in the selected feature."
                }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "success": False,
            "message": "Invalid model_name provided."
        }, status=status.HTTP_400_BAD_REQUEST)

    # --- GET Method (Existing Search and Ranking Logic) ---
    def get(self, request, *args, **kwargs):
        image_id = request.GET.get('image_id')
        model_name = request.GET.get('model_name')

        # Target a specific model if both image_id and model_name are provided
        if image_id and model_name:
            model_mapping = {
                "KitchenViolationReport": KitchenViolationReport,
                "AGGFViolationReport": AGGFViolationReport,
                "SmokingViolationReport": SmokingViolationReport,
                "FaceDetectionReport": FaceDetectionReport,
                "GuardPresenceHistory": GuardPresenceHistory,
                "GarbageMonitoringReport": GarbageMonitoringReport,
                "RecycleMonitoringReport": RecycleMonitoringReport,
                "BuffetViolationReport": BuffetViolationReport,
                "BathroomMonitoringHistory": BathroomMonitoringHistory,
                "SentimentAnalysis": SentimentAnalysis,
                "FallDetectionMonitoringReport": FallDetectionMonitoringReport,
                "ViolenceMonitoringReport": ViolenceMonitoringReport,
                "CrowdMonitoringReport": CrowdMonitoringReport,
                "WallClimbMonitoringReport": WallClimbMonitoringReport,
                "AbnormalActivities": AbnormalActivities,
            }

            target_model = model_mapping.get(model_name)
            if target_model:
                try:
                    record = target_model.objects.get(id=image_id)
                    if getattr(record, 'annotator', None):
                        return Response({
                            "success": True,
                            "email": record.annotator.email,
                            "model_name": model_name
                        }, status=status.HTTP_200_OK)
                except target_model.DoesNotExist:
                    pass

            return Response({
                "success": False,
                "message": "No record found with this ID in the selected feature."
            }, status=status.HTTP_404_NOT_FOUND)

        # Existing logic for listing and calculating annotator rankings
        all_annotators = MyUser.objects.filter(is_annotator=True)
        csv_requested = request.GET.get('csv', '').lower() == 'true'

        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        base_query = Q(is_annotated=True)
        riyadh_tz = pytz.timezone('Asia/Riyadh')

        def parse_and_make_aware(dt_str, label):
            dt = parse_datetime(dt_str)
            if not dt:
                raise ValidationError({
                    label: f"Invalid datetime format for {label}. Use ISO 8601 (e.g., '2025-06-24T00:00:00Z')."
                })
            if is_naive(dt):
                dt = make_aware(dt)
            return dt

        start_date = end_date = None

        if start_date_str:
            start_date = parse_and_make_aware(start_date_str, "start_date")

        if end_date_str:
            end_date = parse_and_make_aware(end_date_str, "end_date")

        if start_date and end_date and start_date.date() == end_date.date():
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        if start_date:
            base_query &= Q(updated_at__gte=start_date)
        if end_date:
            base_query &= Q(updated_at__lte=end_date)

        start_date_riyadh = start_date.astimezone(riyadh_tz) if start_date else None
        end_date_riyadh = end_date.astimezone(riyadh_tz) if end_date else None

        results = []
        overall_total = 0

        for user in all_annotators:
            user_query = base_query & Q(annotator=user)

            total_annotation = (
                KitchenViolationReport.objects.filter(user_query).count() +
                GuardPresenceHistory.objects.filter(user_query).count() +
                BathroomMonitoringHistory.objects.filter(user_query).count() +
                GarbageMonitoringReport.objects.filter(user_query).count() +
                RecycleMonitoringReport.objects.filter(user_query).count() +
                BuffetViolationReport.objects.filter(user_query).count() +
                SentimentAnalysis.objects.filter(user_query).count()
            )

            overall_total += total_annotation

            results.append({
                "email": user.email,
                "username": user.username,
                "total_annotation": total_annotation,
                "start_date": start_date_riyadh.isoformat() if start_date_riyadh else None,
                "end_date": end_date_riyadh.isoformat() if end_date_riyadh else None,
            })

        results.sort(key=lambda x: x["total_annotation"], reverse=True)

        if csv_requested:
            output = StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["email", "username", "total_annotation", "start_date", "end_date"]
            )
            writer.writeheader()
            writer.writerows(results)

            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="annotator_ranking.csv"'
            return response

        return Response(
            {
                "detail": "Data retrieved successfully",
                "total_annotations_by_all_users": overall_total,
                "annotators": results
            },
            status=status.HTTP_200_OK
        )