# Built-in imCleanIndicatorHistoryports
from django.http import HttpResponse
from django.db.models import Q
from django.utils.timezone import make_aware, is_naive
from django.utils.dateparse import parse_datetime
from rest_framework import request, status
import logging
import json
import csv
from io import StringIO
from operator import attrgetter
from io import BytesIO, StringIO
from csv import DictReader
from collections import defaultdict
from itertools import chain
from datetime import datetime, timedelta, time, date
from django.db.models import Count, F, Value, IntegerField
from django.db.models.functions import Length, Coalesce
import datetime as datenowtime
# Third-party imports
from PIL import Image
from django.conf import settings
from django.utils import timezone
from dateutil.parser import parse
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.db import models, transaction
from django.db.models import (
    Sum, F, Q, When, ExpressionWrapper, Subquery, OuterRef, Exists,
    Func, Avg, Min, Max, Prefetch
)
from django.db.models.functions import (
    TruncMonth, TruncHour, TruncDay, ExtractHour
)
from django.http import (
    StreamingHttpResponse, JsonResponse, HttpResponse, QueryDict
)

from functools import reduce
import operator

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, is_naive, now, localtime
from datetime import timedelta
from datetime import datetime
# Django Rest Framework imports
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from authentication.permissions import PeopleCountPermission
from rest_framework.exceptions import ValidationError

import pytz
import math
from itertools import combinations

# Local imports
from authentication.models import Company, MyUser
from authentication.utils import standard_response
from tent.models import Tent
from tent.utils import CustomPagination, generate_csv_response
from camera.models import (
    AbnormalActivities, Camera, CounterHistory, KitchenImage,
    GuardPresenceHistory, CameraHeartbeat, KitchenViolationReport, AGGFViolationReport, SmokingViolationReport, FaceDetectionReport, GarbageMonitoringReport, RecycleMonitoringReport, FallDetectionMonitoringReport, ViolenceMonitoringReport, CrowdMonitoringReport,
    BathroomMonitoringHistory, SentimentAnalysis, CameraType, CameraStatus, WallClimbMonitoringReport, type_choices, BuffetViolationReport,
    CleanersPresenceHistory, EmptyChairDetectionReport
)
from camera.serializers import (
    AbnormalActivitiesSerializer, CameraSerializer, KitchenImageSerializer,
    GuardPresenceHistorySerializer, CounterHistorySerializer,
    KitchenViolationReportSerializer, AGGFViolationReportSerializer, SmokingViolationReportSerializer, FaceDetectionReportSerializer, CameraHeartbeatSerializer,
    OnlyCameraSerializer, GuardPresenceHistoryChartSerializer,
    TentViolationSummarySerializer, CameraViolationSummarySerializer,
    GarbageMonitoringReportSerializer, RecycleMonitoringReportSerializer, FallDetectionMonitoringReportSerializer, ViolenceMonitoringReportSerializer, CrowdMonitoringReportSerializer, BuffetViolationReportSerializer,
    SentimentAnalysisSerializer, BuffetCameraSerializer, CameraStatusSerializer,
    BathroomMonitoringHistorySerializer, CameraTypeSerializer, BuffetAiAnnotationSerializer, WallClimbMonitoringReportSerializer,
    CleanersPresenceHistorySerializer, EmptyChairDetectionReportSerializer
)

from authentication.permissions import (BasePermission, BuffetPermission, CleanersPermission, CleannessPermission, RecyclePermission,
                                        FoodWeightPermission, GuardPermission, KitchenPermission, PeopleCountPermission, SentimentPermission,
                                        TemperaturePermission, WaterTankPermission, CanDeleteImagePermission, CleanersPresencePermission
                                        )

from utils.pagination import custom_array_pagination, paginate_queryset, CustomPageNumberPagination
from utils.time import Current_saudi_time, convert_utc_to_riyadh, start_end_time_to_riyad, calculate_duration_minutes, saudi_tz

# from camera.tasks import save_kitchen_image
from weight.utils import (
    match_people_count_key, match_guard_detection_key,
    match_garbage_detection_key, match_recycle_detection_key, match_kitchen_camera_key, match_aggf_camera_key, match_smoking_camera_key, match_face_detection_camera_key, match_garbage_monitoring_key,
    match_buffet_violation_key, match_cleaners_detection_key, match_sentiment_analysis_key, match_camera_key,
    match_empty_chair_detection_key
)

from django.utils.timezone import make_aware, is_aware
from utils.sorting import tent_name_list_dict_sorting


def safe_make_aware(dt):
    if dt is None:
        return None
    if is_aware(dt):
        return dt
    return make_aware(dt)


def date_time_to_aware(date_time):
    if not is_aware(date_time):
        date_time = make_aware(date_time)
    return date_time


def get_aware_datetime_from_str(date_str):
    if not date_str:
        return None
    dt = parse_datetime(date_str)
    if dt is not None:
        return date_time_to_aware(dt)
    return None


def skip_overlapping_entries(history_qs):
    """
    Skip GuardPresenceHistory entries that overlap with the previous one.
    Returns a cleaned list of non-overlapping entries.
    """
    cleaned_entries = []
    last_end = None

    for entry in history_qs:
        if not entry.start_time or not entry.end_time:
            continue  # skip incomplete records

        if last_end and entry.start_time < last_end:
            # Overlap detected — skip this entry
            continue

        cleaned_entries.append(entry)
        last_end = entry.end_time

    return cleaned_entries

def smart_aggregate(values: list) -> int:
    """
    Given a list of integer values from multiple cameras for the same
    time slot, return a single smart-aggregated integer.

    Rules:
      1. Empty or all-zero  → return 0
      2. Only one non-zero  → return that value  (e.g. [0, 0, 1] → 1)
      3. One value only     → return it as-is
      4. Outlier check      → if highest > 2x second-highest, return highest
      5. Closest pair       → average the two closest values, ignore the third
      6. Always ceil        → result is always an integer rounded up
    """
    if not values:
        return 0

    # Rule 1 — all zeros
    non_zero = [v for v in values if v > 0]
    if not non_zero:
        return 0

    # Rule 2 — only one camera has data
    if len(non_zero) == 1:
        return non_zero[0]

    # Rule 3 — only one camera total
    if len(values) == 1:
        return values[0]

    # Sort descending
    sorted_vals = sorted(values, reverse=True)
    highest = sorted_vals[0]
    second  = sorted_vals[1]

    # Rule 4 — outlier: highest is more than double the second value
    if second == 0 or highest > 2 * second:
        return highest

    # Rule 5 — find the closest pair among all combinations
    best_pair = None
    best_diff = float('inf')

    for a, b in combinations(sorted_vals, 2):
        diff = abs(a - b)
        if diff < best_diff:
            best_diff = diff
            best_pair = (a, b)

    # Rule 6 — ceiling round the average
    return math.ceil(sum(best_pair) / 2)
# Set up logging
logger = logging.getLogger(__name__)


class CameraTypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        companies = []
        user_enabled_types = []
        user = request.user
        company_ids_qr = request.GET.get('company_ids', '')

        # Parse ID list
        def parse_id_list(param: str) -> list[int]:
            return [int(i) for i in param.split(',') if i.strip().isdigit()]

        company_ids = parse_id_list(company_ids_qr)
        is_annotator = getattr(user, 'is_annotator', False)

        # Map permission fields to CameraType.type values
        permission_to_camera_type = {
            "is_guard": "guard",
            "is_kitchen": "kitchen",
            "is_cleanness": "garbage",      # Cleanness → garbage camera
            "is_recycle": "recycle",
            "is_cleaners": "bathroom",      # Cleaners → bathroom camera
            "is_cleaners_presence": "cleaners",  # Cleaners Presence → cleaners camera
            "is_buffet": "buffet",
            "is_sentiment": "sentiment",
            "is_peoplecount": "peoplecount",
            "is_aggf": "employeeactivity",
            "is_smoking": "smoking",
            "is_face_detection": "facedetection",
            "is_falldetection": "falldetection",
            "is_violencedetection": "violencedetection",
            "is_crowdmonitoring": "crowdmonitoring",
            "is_climbmonitoring": "climbmonitoring",
            "is_abnormalactivity": "abnormalactivity",
            "is_livestream": "livestream",
            "is_chairdetection": "chairdetection",
        }

        # Step 1: Gather all permissions from one or multiple companies
        combined_permissions = {
            perm: False for perm in permission_to_camera_type.keys()}

        if is_annotator:
            if company_ids:
                companies = Company.objects.filter(id__in=company_ids)
            else:
                companies = Company.objects.all()
        else:
            if user.is_admin:
                # Default: use the logged-in user's company
                companies = Company.objects.filter(id=user.company.id)
            elif user.is_staff:
                if user.is_guard:
                    user_enabled_types.append("guard")
                if user.is_kitchen:
                    user_enabled_types.append("kitchen")
                if user.is_cleanness:
                    user_enabled_types.append("garbage")
                if user.is_recycle:
                    user_enabled_types.append("recycle")
                if user.is_cleaners:
                    user_enabled_types.append("bathroom")
                if user.is_cleaners_presence:
                    user_enabled_types.append("cleaners")
                if user.is_sentiment:
                    # FIXED: Changed `is` to `if`
                    user_enabled_types.append("sentiment")
                if user.is_buffet:
                    user_enabled_types.append("buffet")
                if user.is_chairdetection:
                    user_enabled_types.append("chairdetection")

        for company in companies:
            for perm in combined_permissions:
                combined_permissions[perm] = combined_permissions[perm] or getattr(
                    company, perm, False)

        # Step 2: Collect camera types from enabled permissions
        enabled_types = [
            camera_type
            for perm, camera_type in permission_to_camera_type.items()
            if combined_permissions.get(perm)
        ]

        if user.is_staff and not user.is_admin and not user.is_annotator:
            enabled_types = user_enabled_types

        # Step 3: Fetch CameraTypes and exclude peoplecount type
        camera_types = CameraType.objects.filter(
            type__in=enabled_types
        ).exclude(type="peoplecount")

        serializer = CameraTypeSerializer(camera_types, many=True)
        return Response({'results': serializer.data}, status=200)


class CameraStatusByTypeView(APIView):
    permission_classes = [IsAuthenticated]
    """
    API view that returns a list of CameraStatus names, optionally filtered by one or more camera types.
    Example:
        GET /api/camera-statuses/?type=guard,kitchen
        GET /api/camera-statuses/  → returns all statuses
    """

    def get(self, request, format=None):
        user = request.user
        # Determine accessible camera types
        if user.is_annotator:
            cameras = Camera.objects.all()
            camera_types = CameraType.objects.filter(
                type__in=cameras.values_list('type', flat=True).distinct())
        elif user.is_admin:
            # Get all tents under user's company
            tents = Tent.objects.filter(company=user.company)
            # Get cameras under those tents
            cameras = Camera.objects.filter(tent__in=tents)
            # Get types of those cameras
            camera_types = CameraType.objects.filter(
                type__in=cameras.values_list('type', flat=True).distinct())
        else:
            # Regular user: only from assigned tents
            tents = user.assigned_tent.all()
            cameras = Camera.objects.filter(tent__in=tents)
            camera_types = CameraType.objects.filter(
                type__in=cameras.values_list('type', flat=True).distinct())

        # If ?type= is provided, further filter camera types
        type_param = request.query_params.get('type')
        if type_param:
            type_list = [t.strip() for t in type_param.split(',') if t.strip()]
            camera_types = camera_types.filter(type__in=type_list)

            if not camera_types.exists():
                return Response({"detail": "No matching camera types found."}, status=404)

        # Get statuses for those camera types, return distinct names
        camera_statuses = CameraStatus.objects.filter(
            type__in=camera_types).values('name').distinct().order_by('name')

        serializer = CameraStatusSerializer(camera_statuses, many=True)
        return Response(serializer.data)


class CameraAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        type_param = request.query_params.get('type', 'all')
        tent_id = request.query_params.get('tentId', None)
        paginate = request.query_params.get(
            'paginate', 'false').lower() == 'true'
        queryset = None
        tent_ids = []

        if tent_id:
            tent_ids = [int(i)
                        for i in tent_id.split(',') if i.strip().isdigit()]

        cam_select = Camera.objects.select_related(
            'heartbeat', 'tent', 'tent__company', 'gate')

        if user.is_admin:
            queryset = cam_select.filter(
                tent__isnull=False, tent__company=user.company)
        elif user.is_annotator:
            if tent_ids:
                queryset = cam_select.filter(tent_id__in=tent_ids)
            else:
                queryset = cam_select.all()
        else:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            queryset = cam_select.filter(tent__id__in=assigned_ids)

        if type_param and type_param.lower() != "all":
            type_list = [t.strip().lower()
                         for t in type_param.split(',') if t.strip()]
            queryset = queryset.filter(type__iexact=type_list[0]) if len(
                type_list) == 1 else queryset.filter(type__in=type_list)

        queryset = queryset.order_by('id')

        if paginate:
            paginator = CustomPagination()
            page = paginator.paginate_queryset(queryset, request)
            serializer = CameraSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        else:
            serializer = CameraSerializer(queryset, many=True)
            return Response({
                "success": True,
                "message": "Cameras retrieved successfully.",
                "results": serializer.data
            }, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.is_admin:
            return Response({
                "success": False,
                "message": "You are not authorized to create camera."
            }, status=status.HTTP_403_FORBIDDEN)
        serializer = CameraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            *standard_response(True, 'Camera and Heartbeat successfully created!', serializer.data, status.HTTP_201_CREATED)
        )


class CameraDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Camera.objects.select_related(
                'heartbeat', 'tent', 'tent__company', 'gate'
            ).get(pk=pk)
        except Camera.DoesNotExist:
            return None

    def get(self, request, pk):
        camera = self.get_object(pk)
        if not camera:
            return Response(*standard_response(False, 'Camera not found.', {}, status.HTTP_404_NOT_FOUND))
        serializer = CameraSerializer(camera)
        return Response(*standard_response(True, 'Camera details fetched successfully!', serializer.data, status.HTTP_200_OK))

    def put(self, request, pk):
        camera = self.get_object(pk)
        if not camera:
            return Response(*standard_response(False, 'Camera not found.', {}, status.HTTP_404_NOT_FOUND))

        serializer = CameraSerializer(camera, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(*standard_response(True, 'Camera successfully updated!', serializer.data, status.HTTP_200_OK))

    def delete(self, request, pk):
        camera = self.get_object(pk)
        if not camera:
            return Response(*standard_response(False, 'Camera not found.', {}, status.HTTP_404_NOT_FOUND))
        camera.delete()
        return Response(*standard_response(True, 'Camera successfully deleted!', {}, status.HTTP_204_NO_CONTENT))


class GuardPresenceHistoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    queryset = GuardPresenceHistory.objects.select_related('camera__tent').all()
    serializer_class = GuardPresenceHistorySerializer

    def create(self, request, *args, **kwargs):
        # Initialize the serializer with the request data
        serializer = self.get_serializer(data=request.data)

        # Validate the data
        serializer.is_valid(raise_exception=True)

        # Save the new object (perform the create action)
        self.perform_create(serializer)

        # Return a consistent success response using standard_response
        return Response(*standard_response(True, 'Guard Presence History successfully created!', serializer.data, status.HTTP_201_CREATED))

    def update(self, request, *args, **kwargs):
        # Get the camera object to update
        guard_presence_history_instance = self.get_object()

        # Initialize the serializer with the updated data
        serializer = self.get_serializer(
            guard_presence_history_instance, data=request.data)

        # Validate the data
        serializer.is_valid(raise_exception=True)

        # Save the updated object
        self.perform_update(serializer)

        # Return a consistent success response using standard_response
        return Response(*standard_response(True, 'Guard Presence History successfully updated!', serializer.data, status.HTTP_200_OK))

    def retrieve(self, request, *args, **kwargs):
        # Get the camera object to retrieve
        guard_presence_history_instance = self.get_object()

        # Serialize the camera object
        serializer = self.get_serializer(guard_presence_history_instance)

        # Return a consistent success response using standard_response
        return Response(*standard_response(True, 'Guard Presence History details fetched successfully!', serializer.data, status.HTTP_200_OK))

    def list(self, request, *args, **kwargs):
        # Retrieve all camera objects
        queryset = self.get_queryset()
        # Serialize the camera objects
        serializer = self.get_serializer(queryset, many=True)

        # Return a consistent success response using standard_response
        return Response(*standard_response(True, 'Guard Presence History list fetched successfully!', serializer.data, status.HTTP_200_OK))

    def destroy(self, request, *args, **kwargs):
        # Get the camera object to delete
        guard_presence_history_instance = self.get_object()

        # Perform the deletion
        self.perform_destroy(guard_presence_history_instance)

        # Return a consistent success response using standard_response
        return Response(*standard_response(True, 'Guard Presence History successfully deleted!', {}, status.HTTP_204_NO_CONTENT))


@method_decorator(csrf_exempt, name='dispatch')
class CreateGuardPresenceHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            try:
                guard_presence = GuardPresenceHistory.objects.get(id=pk)
            except GuardPresenceHistory.DoesNotExist:
                return Response({"message": "GuardPresenceHistory not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = GuardPresenceHistorySerializer(guard_presence)
            data = {
                "success": True,
                "message": "GuardPresenceHistory details fetched successfully!",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            guard_presence = GuardPresenceHistory.objects.filter(
                is_annotated=False, is_ai_annotated=False)
            serializer = GuardPresenceHistorySerializer(
                guard_presence, many=True)
            data = {
                "success": True,
                "message": "GuardPresenceHistory list fetched successfully!",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        if pk is None:
            data = {
                "success": False,
                "message": "GuardPresenceHistory id is required.",
                "data": None
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        try:
            guard_presence = GuardPresenceHistory.objects.get(id=pk)
        except GuardPresenceHistory.DoesNotExist:
            return Response({"message": "GuardPresenceHistory not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = GuardPresenceHistorySerializer(
            guard_presence, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            data = {
                "success": True,
                "message": "GuardPresenceHistory successfully updated!",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            data = {
                "success": False,
                "message": "GuardPresenceHistory update failed.",
                "data": serializer.errors
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        # return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        header_key = request.headers.get('X-Secret-Key')

        # Check the header key
        match_guard_detection_key(header_key)

        # Extract camera SN from the request data
        data = request.data
        # data = json.loads(raw_data)

        camera_sn = data.get('sn', None)
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        guard_count_raw = data.get('guard_count')
        try:
            guard_count = int(
                guard_count_raw) if guard_count_raw is not None else None
        except ValueError:
            return Response(
                {"message": f"Invalid guard_count: must be an integer, got '{guard_count_raw}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve the camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:

            # fetch image file from request.FILES
            image_file = request.FILES.get("image")
            present = str(data.get('present', False)).lower() in ['true']
            GuardPresenceHistory.objects.create(
                camera=camera,
                guard_count=guard_count,
                present=present,
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                image=image_file
            )

            return Response(
                {"message": "Guard Presence History created successfully."},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"message":
                    f"Error creating Guard Presence History: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GuardPresentHistoryUpdateView(APIView):
    def patch(self, request, pk):
        guard_present = get_object_or_404(GuardPresenceHistory, pk=pk)
        # if guard_present.is_annotated:
        #     user_email = guard_present.annotator.email if guard_present.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = GuardPresenceHistorySerializer(
            guard_present, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KitchenViolationReportUpdateView(APIView):
    def patch(self, request, pk):
        kitchen_violation = get_object_or_404(KitchenViolationReport, pk=pk)
        # if kitchen_violation.is_annotated:
        #     user_email = kitchen_violation.annotator.email if kitchen_violation.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = KitchenViolationReportSerializer(
            kitchen_violation, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmployeeActivityViolationReportUpdateView(APIView):
    def patch(self, request, pk):
        employee_activity_violation = get_object_or_404(AGGFViolationReport, pk=pk)
        # if kitchen_violation.is_annotated:
        #     user_email = kitchen_violation.annotator.email if kitchen_violation.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = AGGFViolationReportSerializer(
            employee_activity_violation, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SmokingViolationReportUpdateView(APIView):
    def patch(self, request, pk):
        smoking_violation = get_object_or_404(SmokingViolationReport, pk=pk)
        # if kitchen_violation.is_annotated:
        #     user_email = kitchen_violation.annotator.email if kitchen_violation.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = SmokingViolationReportSerializer(
            smoking_violation, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GarbageMonitoringReportUpdateView(APIView):
    def patch(self, request, pk):
        garbage_monitoring = get_object_or_404(GarbageMonitoringReport, pk=pk)
        # if garbage_monitoring.is_annotated:
        #     user_email = garbage_monitoring.annotator.email if garbage_monitoring.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = GarbageMonitoringReportSerializer(
            garbage_monitoring, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecycleMonitoringReportUpdateView(APIView):
    def patch(self, request, pk):
        recycle_monitoring = get_object_or_404(RecycleMonitoringReport, pk=pk)
        serializer = RecycleMonitoringReportSerializer(
            recycle_monitoring, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FallDetectionReportUpdateView(APIView):

    def patch(self, request, pk):
        fall_detection = get_object_or_404(
            FallDetectionMonitoringReport, pk=pk
        )

        # Prevent double annotation
        if fall_detection.is_annotated:
            user_email = (
                fall_detection.annotator.email
                if fall_detection.annotator
                else "Unknown"
            )

            data = {
                "success": False,
                "message": f"Already annotated by {user_email}"
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = FallDetectionMonitoringReportSerializer(
            fall_detection,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ViolenceReportUpdateView(APIView):

    def patch(self, request, pk):
        violence = get_object_or_404(
            ViolenceMonitoringReport, pk=pk
        )

        # Prevent double annotation
        if violence.is_annotated:
            user_email = (
                violence.annotator.email
                if violence.annotator
                else "Unknown"
            )

            data = {
                "success": False,
                "message": f"Already annotated by {user_email}"
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = ViolenceMonitoringReportSerializer(
            violence,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CrowdMonitoringReportUpdateView(APIView):

    def patch(self, request, pk):
        crowd = get_object_or_404(
            CrowdMonitoringReport, pk=pk
        )

        # Prevent double annotation
        if crowd.is_annotated:
            user_email = (
                crowd.annotator.email
                if crowd.annotator
                else "Unknown"
            )

            data = {
                "success": False,
                "message": f"Already annotated by {user_email}"
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        annotator_status = data.get('annotator_status')
        if isinstance(annotator_status, list):
            valid_choices = {'red', 'orange', 'green'}
            match = next((s for s in annotator_status if s in valid_choices), None)
            if match:
                data['annotator_status'] = match

        serializer = CrowdMonitoringReportSerializer(
            crowd,
            data=data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClimbMonitoringReportUpdateView(APIView):

    def patch(self, request, pk):
        print(f"DEBUG: Incoming Request Data: {request.data}")
        climb = get_object_or_404(
            WallClimbMonitoringReport, pk=pk
        )

        # Prevent double annotation
        if climb.is_annotated:
            user_email = (
                climb.annotator.email
                if climb.annotator
                else "Unknown"
            )

            data = {
                "success": False,
                "message": f"Already annotated by {user_email}"
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = WallClimbMonitoringReportSerializer(
            climb,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class AbnormalActivitiesUpdateView(APIView):

    def patch(self, request, pk):
        abnormal = get_object_or_404(
            AbnormalActivities, pk=pk
        )

        # Prevent double annotation
        if abnormal.is_annotated:
            user_email = (
                abnormal.annotator.email
                if abnormal.annotator
                else "Unknown"
            )

            data = {
                "success": False,
                "message": f"Already annotated by {user_email}"
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = AbnormalActivitiesSerializer(
            abnormal,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BuffetViolationReportUpdateView(APIView):
    def patch(self, request, pk):
        buffetViolation = get_object_or_404(
            BuffetViolationReport, pk=pk)
        # if buffetViolation.is_annotated:
        #     user_email = buffetViolation.annotator.email if buffetViolation.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = BuffetViolationReportSerializer(
            buffetViolation, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BathroomMonitoringHistoryUpdateView(APIView):
    def patch(self, request, pk):
        bathroomMonitor = get_object_or_404(BathroomMonitoringHistory, pk=pk)
        # if bathroomMonitor.is_annotated:
        #     user_email = bathroomMonitor.annotator.email if bathroomMonitor.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = BathroomMonitoringHistorySerializer(
            bathroomMonitor, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SentimentAnalysisUpdateView(APIView):
    def patch(self, request, pk):
        sentimentAna = get_object_or_404(SentimentAnalysis, pk=pk)
        # if sentimentAna.is_annotated:
        #     user_email = sentimentAna.annotator.email if sentimentAna.annotator else "Unknown"
        #     data = {
        #         "success": False,
        #         "message": f"Already annotated by {user_email}"
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        serializer = SentimentAnalysisSerializer(
            sentimentAna, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tent_camera_calculation(request, pk):

    if request.method != 'GET':
        return Response(
            *standard_response(
                False,
                'Invalid request method. Only GET method is allowed.',
                {},
                status.HTTP_405_METHOD_NOT_ALLOWED
            )
        )
    camera_qs = Camera.objects.filter(tent__pk=pk)
    if not camera_qs.exists():
        return Response(
            *standard_response(
                False,
                'No camera found for the given tent.',
                {},
                status.HTTP_404_NOT_FOUND
            )
        )
    threshold = timezone.now() - timedelta(minutes=5)
    camera_summary = list(
        camera_qs.annotate(
            totals=Sum('counterhistory__total'),
            totals_in=Sum('counterhistory__total_in'),
            totals_out=Sum('counterhistory__total_out'),
            totals_passby=Sum('counterhistory__passby'),
            _last_end=Max('counterhistory__end_time'),
        ).values('totals', 'totals_in', 'totals_out', 'totals_passby', 'heart_beat_time', '_last_end')
    )
    for s in camera_summary:
        s['is_active'] = bool(
            s.get('heart_beat_time') and s['heart_beat_time'] >= threshold)
        s['last_update'] = s.pop('_last_end', None)
        s.pop('heart_beat_time', None)

    return Response(
        *standard_response(
            True,
            'Camera summary fetched successfully!',
            camera_summary,
            status.HTTP_200_OK
        )
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tent_graph_calculation(request, pk):
    if request.method != 'GET':
        return Response(
            *standard_response(
                False,
                'Invalid request method. Only GET method is allowed.',
                {},
                status.HTTP_405_METHOD_NOT_ALLOWED
            )
        )

    graph_data = (
        CounterHistory.objects.filter(
            camera__tent__pk=pk,
            end_time__date=datetime.today().date(),
        )
        .values(hour=ExtractHour("end_time"))
        .annotate(user=Sum("passby"))
        .order_by("hour")
    )

    # Return the summarized graph data with a success response
    return Response(
        *standard_response(
            True,
            'Graph Data fetched successfully!',
            graph_data,
            status.HTTP_200_OK
        )
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tent_real_data_calculation(request, pk):
    if request.method != 'GET':
        return Response(
            *standard_response(
                False,
                'Invalid request method. Only GET method is allowed.',
                {},
                status.HTTP_405_METHOD_NOT_ALLOWED
            )
        )

    summary_data = CounterHistory.objects.filter(
        camera__tent__pk=pk,
    ).aggregate(
        staying=Sum(
            ExpressionWrapper(
                F("total_in") - F("total_out"),
                output_field=models.IntegerField(),
            )
        ),
        totals_in=Sum("total_in"),
        totals_out=Sum("total_out"),
        totals_passby=Sum("passby"),
    )

    try:
        # Attempt to fetch the Tent object and handle adjustments
        tent = Tent.objects.get(pk=pk)
        if summary_data["staying"]:
            summary_data["staying"] = (
                tent.adjust if tent.fixed else summary_data["staying"] + tent.adjust
            )
        else:
            summary_data["staying"] = tent.adjust
    except Tent.DoesNotExist:
        # Specific exception handling if the tent does not exist
        return Response(
            *standard_response(
                False,
                f'Tent with pk {pk} not found.',
                {},
                status.HTTP_404_NOT_FOUND
            )
        )
    except Exception as e:
        # General exception handling (logging can be added here)
        return Response(
            *standard_response(
                False,
                f'Error while processing tent data: {str(e)}',
                {},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        )

    # Return the summarized real data with a success response
    return Response(
        *standard_response(
            True,
            'Real Data fetched successfully!',
            summary_data,
            status.HTTP_200_OK
        )
    )


@method_decorator(csrf_exempt, name='dispatch')
class KitchenImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = KitchenImageSerializer

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_kitchen_camera_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Retrieve the camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Create a mutable copy of the request data
            data = request.data.copy()
            data['camera'] = camera.pk

            # Initialize the serializer with the data
            serializer = self.serializer_class(
                # Use `data=` keyword argument
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save()
                return Response(
                    {"message": "Image uploaded successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name='dispatch')
class CreateCounterHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        # Get the 'sn' from the request data
        sn = request.data.get('sn')
        if not sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try to get the camera based on the provided sn
        try:
            camera = Camera.objects.get(sn=sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": "Camera with the provided SN not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create a mutable copy of the request data
        if isinstance(request.data, QueryDict):
            mutable_data = request.data.copy()
        else:
            mutable_data = request.data

        # Add the camera ID to the mutable data
        mutable_data['camera'] = camera.id

        # Create the serializer with the updated data
        serializer = CounterHistorySerializer(
            data=mutable_data, context={"request": request})

        # Validate and save the CounterHistory
        if serializer.is_valid():
            counter_history = serializer.save()
            # counter_history_instance = serializer.instance
            # counter_history_instance.image = request.FILES.get("image", None)

            # counter_history_instance.save()

            difference = counter_history.total_in - counter_history.total_out

            if camera.tent:
                tent = camera.tent
                tent.staying += difference
                tent.save()

            return Response(
                {
                    "message": "Water level sensor created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"message": "Invalid data", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class CreateCameraHeartbeatView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        sn = request.data.get('sn')
        version = request.data.get('version', None)
        mac_address = request.data.get('mac_address', None)
        ip_address = request.data.get('ip_address', None)
        connection_type = request.data.get('connection_type', None)
        ip_address_method = request.data.get('ip_address_method', None)
        host_name = request.data.get('host_name', None)
        time_zone = request.data.get('time_zone', None)
        hw_platform = request.data.get('hw_platform', None)
        report_date = request.data.get('report_date', None)
        time = request.data.get('time', None)
        status_log = request.data.get('status_log', None)

        if not sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create camera if not exists
        camera, _ = Camera.objects.get_or_create(sn=sn)

        # Ensure data is mutable and clean
        data = request.data.copy() if isinstance(
            request.data, QueryDict) else dict(request.data)

        # Flatten single-item lists (form-data issues)
        for key, value in data.items():
            if isinstance(value, list) and len(value) == 1:
                data[key] = value[0]

        # Create or update heartbeat
        camera_heartbeat, _ = CameraHeartbeat.objects.update_or_create(
            camera=camera,  # Lookup field (because OneToOneField, it's unique)
            defaults={
                'sn': sn,
                'version': version,
                'mac_address': mac_address,
                'time': time,
                'ip_address': ip_address,
                'connection_type': connection_type,
                'ip_address_method': ip_address_method,
                'host_name': host_name,
                'time_zone': time_zone,
                'hw_platform': hw_platform,
                'report_date': report_date,
                "status_log": status_log
            }
        )

        serializer = CameraHeartbeatSerializer(camera_heartbeat)

        return Response(
            {
                "message": "Camera Heartbeat saved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CleanIndicatorHistoryReportView(APIView):
    permission_classes = [CleannessPermission]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        # Extract query params

        user = request.user
        response_type = request.GET.get('type', 'json')
        is_clean = request.GET.get('violation', None)
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'

        # Tent filtering
        if tent_id_list:
            try:
                tent_ids = list(map(int, tent_id_list.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)

        else:
            if user.is_admin:
                tents = Tent.objects.filter(
                    company=request.user.company).order_by('id')
            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                tents = Tent.objects.filter(
                    id__in=assigned_tent_ids, company=request.user.company).order_by('id')
            if not tents.exists():
                return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        if not tents.exists():
            return Response({"detail": "No tents found."}, status=404)

        # Parse and validate dates
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                return Response({"error": "Start and end dates are required."}, status=400)

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.min.time())) + timedelta(days=1)
        except Exception as e:
            return Response({"error": f"Invalid dates: {str(e)}"}, status=400)

        # Base queryset
        queryset = GarbageMonitoringReport.objects.filter(
            camera__tent__in=tents,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            is_rejected=False,
            is_annotated=True
        ).order_by('-created_at')

        if is_clean is not None:
            # Convert string to boolean
            is_clean_bool = is_clean.lower() == 'true'
            queryset = queryset.filter(current_status=is_clean_bool)

        # Fetch all matching records
        queryset = queryset.order_by('-created_at').values(
            'camera__tent__name',
            'created_at',
            'camera__sn',
            'is_clean',
            'image',
        )

        data = []
        for record in queryset:
            image_url = f"{settings.MEDIA_URL}{record['image']}" if record['image'] else None
            image_full_url = f"{settings.BASE_URL}{image_url}" if image_url and settings.DEBUG else image_url

            data.append({
                'tent_name': record['camera__tent__name'],
                'created_at': record['created_at'],
                'camera_sn': record['camera__sn'],
                'is_clean': record['is_clean'],
                'image': image_full_url,
            })

        # CSV Response
        if response_type == "csv":
            return generate_csv_response(data, 'report_data.csv')

        # Paginated or full response
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Clean Indicator Data Retrieved",
            'results': data,
        }, status=status.HTTP_200_OK)


class KitchenHistoryReport(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')
        tent_ids_text = request.query_params.get('tent_id')
        violation_str = request.query_params.get('violation', None).lower()
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']
        violation = None
        if violation_str == 'all':
            violation = 'all'
        else:
            violation = violation_str in ['true', '1', 'yes']

        # Validate and parse dates
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by tents
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # Build base query
        query = Q(camera__tent__in=tents) & Q(
            start_time__gte=start_datetime) & Q(end_time__lte=end_datetime) & Q(is_rejected=False) & Q(is_annotated=True)

        if violation == True:
            query &= Q(violation=True)

        histories = KitchenViolationReport.objects.filter(
            query).order_by('-created_at').select_related('camera__tent')

        histories = _dedup_kitchen_queryset(histories)

        serializer = KitchenViolationReportSerializer(
            histories, many=True, context={'request': request})
        data = serializer.data

        filtered_data = [
            {
                'current_status': item['current_status'],
                'tent_name': item['tent_name'],
                'start_time': item['start_time'],
                'end_time': item['end_time'],
                'image': item['image'],
                'camera_sn': item['camera_sn'],
            }
            for item in data
        ]

        # Return CSV if requested
        if response_type == "csv":
            status_labels = ["no_gloves", "no_masks", "no_hats",
                             "garbage", "food_uncovered", "uniform_missing"]
            csv_filtered_data = []
            for item in filtered_data:
                row = {
                    'tent_name': item['tent_name'],
                    'start_time': item['start_time'],
                    'end_time': item['end_time'],
                    'image': item['image'],
                    'camera_sn': item['camera_sn'],
                }
                for status in status_labels:
                    row[status] = status in item.get('current_status', [])
                csv_filtered_data.append(row)
            return generate_csv_response(csv_filtered_data, 'kitchen-history.csv')

        # Apply pagination if needed
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                filtered_data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Kitchen History Data Retrieved Successfully",
            'results': filtered_data,
        }, status=status.HTTP_200_OK)


class SentimentAnalysisReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')
        tent_ids_text = request.query_params.get('tent_id')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']

        # Validate and parse dates
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by tents
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # Build base query

        query = (
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(end_time__lte=end_datetime) &
            Q(is_rejected=False) &
            Q(is_annotated=True) &
            (Q(annotator_status__contains=['happy']) | Q(annotator_status__contains=['sad']))
        )


        histories = SentimentAnalysis.objects.filter(
            query).order_by('-created_at').select_related('camera__tent')

        serializer = SentimentAnalysisSerializer(
            histories, many=True, context={'request': request})
        data = serializer.data

        filtered_data = [
            {
                'current_status': item['current_status'],
                'tent_name': item['tent_name'],
                'start_time': item['start_time'],
                'end_time': item['end_time'],
                'image': item['image'],
                'camera_sn': item['camera_sn'],
            }
            for item in data
        ]

        # Return CSV if requested
        if response_type == "csv":
            return generate_csv_response(filtered_data, 'kitchen-history.csv')

        # Apply pagination if needed
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                filtered_data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Buffet History Data Retrieved Successfully",
            'results': filtered_data,
        }, status=status.HTTP_200_OK)


class GarbageMonitoringReportChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')

        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # ── Base queryset (only annotated) ───────────────────────
        queryset = GarbageMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).select_related('camera__tent')

        # ── Stats for cards ──────────────────────────────────────
        total    = queryset.count()
        garbage  = queryset.filter(is_clean=False).count()
        clean    = queryset.filter(is_clean=True).count()
        rejected = queryset.filter(is_rejected=True).count()

        # ── Hourly breakdown for bar chart ───────────────────────
        hourly_qs = (
            queryset
            .values('start_time__hour', 'is_clean')
            .annotate(count=Count('id'))
            .order_by('start_time__hour')
        )

        hourly_map = {}
        for row in hourly_qs:
            hour = str(row['start_time__hour']).zfill(2)
            if hour not in hourly_map:
                hourly_map[hour] = {'hour': hour, 'garbage': 0, 'clean': 0}
            key = 'clean' if row['is_clean'] else 'garbage'
            hourly_map[hour][key] = row['count']

        hourly = sorted(hourly_map.values(), key=lambda x: x['hour'])

        return Response({
            'stats': {
                'total':   total,
                'garbage': garbage,
                'clean':   clean,
                'rejected': rejected,
            },
            'hourly': hourly,
        }, status=status.HTTP_200_OK)


class GarbageMonitoringReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')
        filter_param = request.query_params.get('filter_param')  # garbage | clean | rejected | total
        hour = request.query_params.get('hour')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']

        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # ── Base queryset (only annotated) ───────────────────────
        queryset = GarbageMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).order_by('-start_time').select_related('camera__tent')

        # ── filter_param (card click) ────────────────────────────
        if filter_param == 'garbage':
            queryset = queryset.filter(is_clean=False)
        elif filter_param == 'clean':
            queryset = queryset.filter(is_clean=True)
        elif filter_param == 'rejected':
            queryset = queryset.filter(is_rejected=True)
        # 'total' → no additional filter, show all annotated

        # ── Hour filter (bar chart click) ────────────────────────
        if hour is not None:
            queryset = queryset.filter(start_time__hour=int(hour))

        # ── Serialize ────────────────────────────────────────────
        serializer = GarbageMonitoringReportSerializer(
            queryset, many=True, context={'request': request}
        )

        # ── Paginate ─────────────────────────────────────────────
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                serializer.data, request, view=self
            )
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Garbage Monitoring History Data Retrieved Successfully",
            'count': queryset.count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)


class WallClimbHistoryReportChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')

        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # ── Base queryset (only annotated) ───────────────────────
        queryset = WallClimbMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).select_related('camera__tent')

        # ── Stats for cards ──────────────────────────────────────
        total = queryset.count()
        climb = queryset.filter(is_climb=True).count()
        no_climb = queryset.filter(is_climb=False).count()
        rejected = queryset.filter(is_rejected=True).count()

        # ── Hourly breakdown for bar chart ───────────────────────
        hourly_qs = (
            queryset
            .values('start_time__hour', 'is_climb')
            .annotate(count=Count('id'))
            .order_by('start_time__hour')
        )

        hourly_map = {}
        for row in hourly_qs:
            hour = str(row['start_time__hour']).zfill(2)
            if hour not in hourly_map:
                hourly_map[hour] = {'hour': hour, 'climb': 0, 'no_climb': 0}
            key = 'climb' if row['is_climb'] else 'no_climb'
            hourly_map[hour][key] = row['count']

        hourly = sorted(hourly_map.values(), key=lambda x: x['hour'])

        return Response({
            'stats': {
                'total': total,
                'climb': climb,
                'no_climb': no_climb,
                'rejected': rejected,
            },
            'hourly': hourly,
        }, status=status.HTTP_200_OK)


class WallClimbHistoryReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')
        filter_param = request.query_params.get('filter_param')  # climb | no_climb | rejected | total
        hour = request.query_params.get('hour')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']

        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # ── Base queryset (only annotated) ───────────────────────
        queryset = WallClimbMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).order_by('-start_time').select_related('camera__tent')

        # ── filter_param (card click) ────────────────────────────
        if filter_param == 'climb':
            queryset = queryset.filter(is_climb=True)
        elif filter_param == 'no_climb':
            queryset = queryset.filter(is_climb=False)
        elif filter_param == 'rejected':
            queryset = queryset.filter(is_rejected=True)
        # 'total' → no additional filter, show all annotated

        # ── Hour filter (bar chart click) ────────────────────────
        if hour is not None:
            queryset = queryset.filter(start_time__hour=int(hour))

        # ── Serialize ────────────────────────────────────────────
        serializer = WallClimbMonitoringReportSerializer(
            queryset, many=True, context={'request': request}
        )

        # ── Paginate ─────────────────────────────────────────────
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                serializer.data, request, view=self
            )
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Wall Climb History Data Retrieved Successfully",
            'count': queryset.count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)



class CrowdMonitoringReportChartView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        tent_ids_text  = request.query_params.get('tent_id')
 
        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date   = parse_date(end_date_str)   if end_date_str   else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)
 
        # ── Base queryset (only annotated) ───────────────────────
        queryset = CrowdMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).select_related('camera__tent')
 
        # ── Stats ────────────────────────────────────────────────
        total    = queryset.count()
        crowd    = queryset.filter(is_crowd=True).count()
        no_crowd = queryset.filter(is_crowd=False).count()
        rejected = queryset.filter(is_rejected=True).count()
 
        # ── Hourly breakdown ─────────────────────────────────────
        hourly_qs = (
            queryset
            .values('start_time__hour', 'is_crowd')
            .annotate(count=Count('id'))
            .order_by('start_time__hour')
        )
 
        hourly_map = {}
        for row in hourly_qs:
            hour = str(row['start_time__hour']).zfill(2)
            if hour not in hourly_map:
                hourly_map[hour] = {'hour': hour, 'crowd': 0, 'no_crowd': 0}
            key = 'crowd' if row['is_crowd'] else 'no_crowd'
            hourly_map[hour][key] = row['count']
 
        hourly = sorted(hourly_map.values(), key=lambda x: x['hour'])
 
        return Response({
            'stats': {
                'total':    total,
                'crowd':    crowd,
                'no_crowd': no_crowd,
                'rejected': rejected,
            },
            'hourly': hourly,
        }, status=status.HTTP_200_OK)
 
 
class CrowdMonitoringHistoryReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
 
    def get(self, request, format=None):
        user          = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        tent_ids_text  = request.query_params.get('tent_id')
        filter_param   = request.query_params.get('filter_param')  # crowd | no_crowd | rejected | total
        hour           = request.query_params.get('hour')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate       = paginate_param in ['true', '1', 'yes']
 
        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date   = parse_date(end_date_str)   if end_date_str   else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)
 
        # ── Base queryset (only annotated) ───────────────────────
        latest_ann_sq = CrowdMonitoringReport.objects.filter(
            camera=OuterRef('camera'), is_annotated=True
        ).order_by('-updated_at')

        queryset = CrowdMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).annotate(
            _latest_ann_status=Subquery(latest_ann_sq.values('annotator_status')[:1]),
            _latest_ann_updated=Subquery(latest_ann_sq.values('updated_at')[:1]),
        ).order_by('-start_time').select_related('camera__tent')
 
        # ── filter_param ─────────────────────────────────────────
        if filter_param == 'crowd':
            queryset = queryset.filter(is_crowd=True)
        elif filter_param == 'no_crowd':
            queryset = queryset.filter(is_crowd=False)
        elif filter_param == 'rejected':
            queryset = queryset.filter(is_rejected=True)
        # 'total' → no extra filter
 
        # ── Hour filter ──────────────────────────────────────────
        if hour is not None:
            queryset = queryset.filter(start_time__hour=int(hour))
 
        # ── Serialize ────────────────────────────────────────────
        serializer = CrowdMonitoringReportSerializer(
            queryset, many=True, context={'request': request}
        )
 
        # ── Paginate ─────────────────────────────────────────────
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                serializer.data, request, view=self
            )
            return paginator.get_paginated_response(paginated_data)
 
        return Response({
            'success': True,
            'message': "Crowd Monitoring History Data Retrieved Successfully",
            'count':   queryset.count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)


class AbnormalActivitiesReportChartView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request, format=None):
        user           = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        tent_ids_text  = request.query_params.get('tent_id')
 
        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date   = parse_date(end_date_str)   if end_date_str   else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)
 
        # ── Base queryset (only annotated) ───────────────────────
        queryset = AbnormalActivities.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).select_related('camera__tent')
 
        # ── Stats ────────────────────────────────────────────────
        total           = queryset.count()
        motion_detected = queryset.filter(is_motion_detected=True).count()
        no_motion       = queryset.filter(is_motion_detected=False).count()
        rejected        = queryset.filter(is_rejected=True).count()
 
        # ── Hourly breakdown ─────────────────────────────────────
        hourly_qs = (
            queryset
            .values('start_time__hour', 'is_motion_detected')
            .annotate(count=Count('id'))
            .order_by('start_time__hour')
        )
 
        hourly_map = {}
        for row in hourly_qs:
            hour = str(row['start_time__hour']).zfill(2)
            if hour not in hourly_map:
                hourly_map[hour] = {'hour': hour, 'motion_detected': 0, 'no_motion': 0}
            key = 'motion_detected' if row['is_motion_detected'] else 'no_motion'
            hourly_map[hour][key] = row['count']
 
        hourly = sorted(hourly_map.values(), key=lambda x: x['hour'])
 
        return Response({
            'stats': {
                'total':           total,
                'motion_detected': motion_detected,
                'no_motion':       no_motion,
                'rejected':        rejected,
            },
            'hourly': hourly,
        }, status=status.HTTP_200_OK)
 
 
class AbnormalActivitiesHistoryReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
 
    def get(self, request, format=None):
        user           = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        tent_ids_text  = request.query_params.get('tent_id')
        filter_param   = request.query_params.get('filter_param')  # motion_detected | no_motion | rejected | total
        hour           = request.query_params.get('hour')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate       = paginate_param in ['true', '1', 'yes']
 
        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date   = parse_date(end_date_str)   if end_date_str   else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)
 
        # ── Base queryset (only annotated) ───────────────────────
        queryset = AbnormalActivities.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).order_by('-start_time').select_related('camera__tent')
 
        # ── filter_param ─────────────────────────────────────────
        if filter_param == 'motion_detected':
            queryset = queryset.filter(is_motion_detected=True)
        elif filter_param == 'no_motion':
            queryset = queryset.filter(is_motion_detected=False)
        elif filter_param == 'rejected':
            queryset = queryset.filter(is_rejected=True)
        # 'total' → no extra filter
 
        # ── Hour filter ──────────────────────────────────────────
        if hour is not None:
            queryset = queryset.filter(start_time__hour=int(hour))
 
        # ── Serialize ────────────────────────────────────────────
        serializer = AbnormalActivitiesSerializer(
            queryset, many=True, context={'request': request}
        )
 
        # ── Paginate ─────────────────────────────────────────────
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                serializer.data, request, view=self
            )
            return paginator.get_paginated_response(paginated_data)
 
        return Response({
            'success': True,
            'message': "Abnormal Activities History Data Retrieved Successfully",
            'count':   queryset.count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)

class CounterHistoryReportChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')

        # ── Validate and parse dates ─────────────────────────────
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date   = parse_date(end_date_str)   if end_date_str   else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = start_end_time_to_riyad(datetime.combine(start_date, time.min))
            end_datetime   = start_end_time_to_riyad(datetime.combine(end_date,   time.max))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ── Filter by tents ──────────────────────────────────────
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            else:
                tents = Tent.objects.none()

        # ── 2-query fetch ────────────────────────────────────────
        all_cameras = Camera.objects.filter(type="peoplecount", tent__in=tents)
        all_records = CounterHistory.objects.filter(
            camera__in=all_cameras,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
        ).only('camera_id', 'total_in', 'total_out', 'created_at')

        cam_to_tent = {c.id: c.tent_id for c in all_cameras}

        # Group: (hour in Riyadh time, tent_id) → camera_id → [in, out]
        hour_tent_cam = defaultdict(lambda: defaultdict(lambda: [0, 0]))

        for rec in all_records:
            if not rec.created_at:
                continue
            tid = cam_to_tent.get(rec.camera_id)
            if not tid:
                continue
            hour_key = convert_utc_to_riyadh(rec.created_at).hour
            hour_tent_cam[(hour_key, tid)][rec.camera_id][0] += rec.total_in
            hour_tent_cam[(hour_key, tid)][rec.camera_id][1] += rec.total_out

        # Smart-aggregate per (hour, tent), then sum across tents
        hour_totals = defaultdict(lambda: [0, 0])
        for (hour_key, _tid), cam_data in hour_tent_cam.items():
            in_vals  = [v[0] for v in cam_data.values()]
            out_vals = [v[1] for v in cam_data.values()]
            hour_totals[hour_key][0] += smart_aggregate(in_vals)
            hour_totals[hour_key][1] += smart_aggregate(out_vals)

        total_in  = sum(v[0] for v in hour_totals.values())
        total_out = sum(v[1] for v in hour_totals.values())
        net       = total_in - total_out

        hourly = [
            {
                'hour':      str(h).zfill(2),
                'total_in':  hour_totals[h][0],
                'total_out': hour_totals[h][1],
            }
            for h in sorted(hour_totals.keys())
        ]

        return Response({
            'stats': {
                'total_in':  total_in,
                'total_out': total_out,
                'net':       net,
            },
            'hourly': hourly,
        }, status=status.HTTP_200_OK)


class BuffetHistoryViewReport(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')
        tent_ids_text = request.query_params.get('tent_id')
        violation_str = request.query_params.get('violation', None).lower()
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']
        violation = None
        if violation_str == 'all':
            violation = 'all'
        else:
            violation = violation_str in ['true', '1', 'yes']

        # Validate and parse dates
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by tents
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # Build base query
        query = Q(camera__tent__in=tents) & Q(
            start_time__gte=start_datetime) & Q(end_time__lte=end_datetime) & Q(is_rejected=False) & Q(is_annotated=True)

        if violation == True:
            query &= Q(violation=True)

        histories = BuffetViolationReport.objects.filter(
            query).order_by('-created_at').select_related('camera__tent')

        serializer = BuffetViolationReportSerializer(
            histories, many=True, context={'request': request})
        data = serializer.data

        # Format data
        filtered_data = [
            {
                'current_status': item['current_status'],
                'tent_name': item['tent_name'],
                'start_time': item['start_time'],
                'end_time': item['end_time'],
                'image': item['image'],
                'camera_sn': item['camera_sn']
            }
            for item in data
        ]

        # Return CSV if requested
        if response_type == "csv":
            status_labels = ["no_waiter", "food_empty", "waiter_without_precaution",
                             "crowd", "garbage", "dirty_plate", "not_enough_food", "empty_container"]
            csv_filtered_data = []
            for item in filtered_data:
                row = {
                    'tent_name': item['tent_name'],
                    'start_time': item['start_time'],
                    'end_time': item['end_time'],
                    'image': item['image'],
                    'camera_sn': item['camera_sn'],
                }
                for status in status_labels:
                    row[status] = status in item.get('current_status', [])
                csv_filtered_data.append(row)
            return generate_csv_response(csv_filtered_data, 'buffet-history.csv')

        # Apply pagination if needed
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                filtered_data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Buffet History Data Retrieved Successfully",
            'results': filtered_data,
        }, status=status.HTTP_200_OK)


class GuardPresenceHistoryReportView(APIView):
    permission_classes = [GuardPermission]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        # Get query parameters
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')
        tent_ids_text = request.query_params.get('tent_id')
        is_present_str = request.query_params.get('violation')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']

        # Validate and parse dates
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by tents
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        # Build base query
        query = Q(camera__tent__in=tents) & Q(
            start_time__gte=start_datetime) & Q(end_time__lte=end_datetime) & Q(is_rejected=False) & Q(is_annotated=True)

        # Apply is_present filter if provided
        if is_present_str is not None:
            is_present = is_present_str.lower() in ['true', '1', 'yes']
            query &= Q(present=is_present)

        histories = GuardPresenceHistory.objects.filter(
            query).order_by("-start_time").select_related('camera__tent')

        # Format data
        data = []
        for record in histories:
            image_url = f"{settings.MEDIA_URL}{record.image}" if record.image else None
            if image_url and settings.DEBUG:
                image_url = f"{settings.BASE_URL}{image_url}"
            guard_count = 0 if record.current_status[0] == 'absent' else record.current_status[0]
            item = {
                'tent_name': record.camera.tent.name,
                'camera_sn': record.camera.sn,
                'guard_count': guard_count,
                'present': record.present,
                'start_time': convert_utc_to_riyadh(record.start_time),
                'end_time': convert_utc_to_riyadh(record.end_time),
                'image': image_url
            }

            data.append(item)

        # Return CSV if requested
        if response_type == "csv":
            return generate_csv_response(data, 'guard_presence_history.csv')

        # Apply pagination if needed
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Guard Presence History Data Retrieved Successfully",
            'results': data,
        }, status=status.HTTP_200_OK)


class CounterHistoryReportView(APIView):
    permission_classes = [PeopleCountPermission]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        # Query parameters

        user = request.user
        response_type = request.GET.get('type', 'json')
        interval = request.GET.get('interval', 'hour')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        tent_id_list = request.GET.get('tent_id')
        paginate = request.GET.get('paginate', 'true').lower() == 'true'
        tents = None

        # Validate and fetch tents
        if user.is_admin:
            tents = Tent.objects.filter(
                company=request.user.company).order_by('id')
        else:
            assigned_tent_ids = user.assigned_tent.values_list(
                'id', flat=True)
            tents = Tent.objects.filter(
                id__in=assigned_tent_ids, company=request.user.company).order_by('id')
        if not tents.exists():
            return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)
        if tent_id_list:
            try:
                tent_ids = [int(tid) for tid in tent_id_list.split(',')]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id parameter."}, status=status.HTTP_400_BAD_REQUEST)

        if not tents.exists():
            return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        # Parse date range
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date   = parse_date(end_date_str)   if end_date_str   else None
            if not (start_date and end_date):
                return Response({"detail": "Start date and end date are required."}, status=400)

            start_datetime = start_end_time_to_riyad(datetime.combine(start_date, time.min))
            end_datetime   = start_end_time_to_riyad(datetime.combine(end_date,   time.max))
        except Exception:
            return Response({"detail": "Invalid date format."}, status=400)

        # Determine grouping interval
        interval_map = {
            'hour': TruncHour,
            'day': TruncDay,
            'month': TruncMonth
        }
        trunc_func = interval_map.get(interval)
        if not trunc_func:
            return Response({"error": "Invalid interval. Choose from 'hour', 'day', or 'month'."}, status=400)

        # Query and aggregate
        records = (
            CounterHistory.objects.filter(
                camera__tent__in=tents,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime,
            )
            .annotate(
                time=trunc_func('created_at'),
                tent_name=F('camera__tent__name'),
                camera_name=F('camera__sn')
            )
            .values('time', 'tent_name', 'camera_name')
            .annotate(
                total_in=Sum('total_in'),
                total_out=Sum('total_out'),
                total=Sum('total')
            )
            .order_by('-time')
        )

        # Build response data
        data = [
            {
                'tent_name': r['tent_name'],
                'time': r['time'],
                'camera_name': r['camera_name'],
                'total_in': r['total_in'],
                'total_out': r['total_out'],
                'total': r['total'],
            }
            for r in records
        ]

        # CSV export
        if response_type == 'csv':
            return generate_csv_response(data, 'report_data.csv')

        # Paginate or return full data
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)
        else:
            return Response({
                'success': True,
                'message': "Guard Presence History Report Data Successfully",
                'results': data,
            }, status=status.HTTP_200_OK)


class KitchenViolationReportByTentView(APIView):

    permission_classes = [KitchenPermission]

    def get(self, request, *args, **kwargs):
        # Extract tent ID from the URL parameters
        tent_id = kwargs.get('tent_id')
        # Parse and validate tent ID
        try:
            tent = Tent.objects.get(id=tent_id)
        except Tent.DoesNotExist:
            return Response({"detail": "Tent not found."}, status=status.HTTP_404_NOT_FOUND)

        latest_per_camera = (
            KitchenViolationReport.objects
            .filter(camera__tent=tent)
            .order_by('camera', '-created_at')
            .distinct('camera')
            .values_list('id', flat=True)
        )
        records = (
            KitchenViolationReport.objects
            .filter(id__in=latest_per_camera)
            .select_related('camera__tent')
            .order_by('camera_id')
        )

        if records.exists():
            serializer = KitchenViolationReportSerializer(records, many=True)
            return Response({
                "success": True,
                "message": "Kitchen violation report for this tent retrieved successfully.",
                "kitchen_violation_list": serializer.data,
            }, status=status.HTTP_200_OK)
        else:
            data = {
                "success": False,
                "message": "No violation report found for this tent.",
                "kitchen_violation_list": []
            }
            return Response(data, status=status.HTTP_200_OK)


class CameraByTentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        user = request.user
        type_param = request.query_params.get('type', 'all')
        tent_ids = request.query_params.get('tent_ids')
        tent_id = kwargs.get('tent_id')
        user = request.user

        # Map company permission fields to camera types
        permission_to_camera_type = {
            "is_guard": "guard",
            "is_kitchen": "kitchen",
            "is_cleanness": "garbage",
            "is_recycle": "recycle",
            "is_cleaners": "bathroom",
            "is_cleaners_presence": "cleaners",
            "is_buffet": "buffet",
            "is_sentiment": "sentiment",
            "is_peoplecount": "peoplecount",
            "is_aggf": "employeeactivity",
            "is_smoking": "smoking",
            "is_face_detection": "facedetection",
            "is_falldetection": "falldetection",
            "is_violencedetection": "violencedetection",
            "is_crowdmonitoring": "crowdmonitoring",
            "is_climbmonitoring": "climbmonitoring",
            "is_abnormalactivity": "abnormalactivity",
        }

        # Get allowed camera types based on company permissions
        allowed_camera_types = [
            cam_type for perm, cam_type in permission_to_camera_type.items()
            if getattr(company, perm, False)
        ]
        queryset = None

        if user.is_annotator:
            # Annotator can access all cameras
            queryset = Camera.objects.all().exclude(type="peoplecount")
        elif user.is_admin:
            queryset = Camera.objects.filter(
                tent__company=company).exclude(type='peoplecount').exclude(type="peoplecount")
        else:
            queryset = Camera.objects.filter(
                tent__in=user.assigned_tent.all()).exclude(type="peoplecount")
            # Default: filter by user's company

        # Filter tents by company first
        company_tents = Tent.objects.filter(company=company)

        if tent_ids:
            tent_ids_list = tent_ids.split(',')
            # Filter tents by company and tent_ids
            company_tents = company_tents.filter(id__in=tent_ids_list)
            # Use filtered tents for cameras
            queryset = queryset.filter(tent__in=company_tents)
        elif tent_id:
            # Filter by single tent_id only if provided and belongs to company
            try:
                tent = company_tents.get(id=tent_id)
            except Tent.DoesNotExist:
                # Instead of returning error, just return empty results
                return Response({
                    "success": True,
                    "message": "No tents found for the given criteria.",
                    "results": []
                }, status=status.HTTP_200_OK)
            queryset = queryset.filter(tent=tent)
        else:
            # If no tent_ids or tent_id provided, filter cameras by all tents of the company
            queryset = queryset.filter(tent__in=company_tents)

        # Restrict to allowed camera types only
        queryset = queryset.filter(type__in=allowed_camera_types)

        # Handle multiple or single types in query param
        type_param = request.query_params.get('type', 'all')
        type_list = [t.strip() for t in type_param.split(',') if t.strip()]

        if type_list and 'all' not in type_list:
            valid_types = [t for t in type_list if t in allowed_camera_types]
            if valid_types:
                queryset = queryset.filter(type__in=valid_types)
            else:
                queryset = queryset.none()

        if queryset.exists():
            serializer = OnlyCameraSerializer(queryset, many=True)
            return Response({
                "success": True,
                "message": "Camera Data was successfully retrieved",
                "results": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": True,
                "message": "No cameras found for the given criteria.",
                "results": []
            }, status=status.HTTP_200_OK)


def _dedup_garbage_queryset(queryset):
    from datetime import timedelta
    records = list(
        queryset.values('id', 'camera_id', 'created_at', 'is_clean', 'annotator_status')
        .order_by('camera_id', 'created_at')
    )
    kept_ids = []
    last_kept = {}  # camera_id -> last kept record
    for rec in records:
        cam = rec['camera_id']
        last = last_kept.get(cam)
        if last is None:
            kept_ids.append(rec['id'])
            last_kept[cam] = rec
        else:
            same_state = (
                rec['is_clean'] == last['is_clean'] and
                rec['annotator_status'] == last['annotator_status']
            )
            within_hour = (rec['created_at'] - last['created_at']) < timedelta(hours=1)
            if not (same_state and within_hour):
                kept_ids.append(rec['id'])
                last_kept[cam] = rec
    return queryset.filter(id__in=kept_ids)


def _dedup_kitchen_queryset(queryset):
    from datetime import timedelta

    def _state(annotator_status):
        if not annotator_status:
            return frozenset()
        if isinstance(annotator_status, list):
            return frozenset(annotator_status)
        return frozenset([annotator_status])

    records = list(
        queryset.values('id', 'camera_id', 'created_at', 'annotator_status')
        .order_by('camera_id', 'created_at')
    )
    kept_ids = []
    last_kept = {}  # camera_id -> {'created_at': ..., 'state': frozenset}
    for rec in records:
        cam = rec['camera_id']
        last = last_kept.get(cam)
        current_state = _state(rec['annotator_status'])
        if last is None:
            kept_ids.append(rec['id'])
            last_kept[cam] = {'created_at': rec['created_at'], 'state': current_state}
        else:
            same_state = current_state == last['state']
            within_hour = (rec['created_at'] - last['created_at']) < timedelta(hours=1)
            if not (same_state and within_hour):
                kept_ids.append(rec['id'])
                last_kept[cam] = {'created_at': rec['created_at'], 'state': current_state}
    return queryset.filter(id__in=kept_ids)


class GalleryByCameraView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        camera_id = kwargs.pop("camera_id", None)

        def parse_id_list(param: str) -> list[int]:
            return [int(i) for i in param.split(',') if i.strip().isdigit()]

        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        camera_ids_qr = request.GET.get('camera_ids', '')
        company_ids_qr = request.GET.get('company_ids', '')
        tent_ids_qr = request.GET.get('tent_ids', '')
        type_list_qr = request.GET.get('types', '')
        annotator_param = request.GET.get('is_annotator', 'false').lower()
        annotator = annotator_param in ['true', '1', 'yes']
        paginate_param = request.query_params.get('paginate', "true").lower()
        paginate = paginate_param in ['true', '1', 'yes']

        camera_ids = parse_id_list(camera_ids_qr)
        tent_ids = parse_id_list(tent_ids_qr)
        company_ids = parse_id_list(company_ids_qr)
        type_list = [t.strip() for t in type_list_qr.split(',') if t.strip()]

        if not start_date_time_str or not end_date_time_str:
            return Response({"detail": "Start and end date are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date_time = parse_datetime(start_date_time_str)
        end_date_time = parse_datetime(end_date_time_str)

        filter_param = request.GET.get('filter_param', None)

        if not (start_date_time and end_date_time):
            return Response({"detail": "Invalid date or time format."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date_time = safe_make_aware(start_date_time)
        end_date_time = safe_make_aware(end_date_time)

        try:
            base_camera_query = Q()

            if camera_id:
                base_camera_query &= Q(id=camera_id)
            elif camera_ids:
                base_camera_query &= Q(id__in=camera_ids)
            else:
                if tent_ids:
                    base_camera_query &= Q(tent__id__in=tent_ids)
                elif company_ids:
                    base_camera_query &= Q(tent__company__id__in=company_ids)
                if type_list:
                    base_camera_query &= Q(type__in=type_list)

            if user.is_annotator:
                pass
            elif user.is_admin:
                base_camera_query &= Q(tent__company=user.company)
            elif user.is_staff:
                permission_list = []
                if user.is_guard:
                    permission_list.append("guard")
                if user.is_kitchen:
                    permission_list.append("kitchen")
                if user.is_cleanness:
                    permission_list.append("garbage")
                if user.is_recycle:
                    permission_list.append("recycle")
                if user.is_cleaners:
                    permission_list.append("bathroom")
                if user.is_cleaners_presence:
                    permission_list.append("cleaners")
                if user.is_sentiment:
                    permission_list.append("sentiment")
                if user.is_buffet:
                    permission_list.append("buffet")

                base_camera_query &= Q(tent__in=user.assigned_tent.all()) & Q(
                    type__in=permission_list)

            camera_ids_list = list(Camera.objects.filter(
                base_camera_query).values_list('id', flat=True))

        except Camera.DoesNotExist:
            return Response({"detail": "Camera not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if not camera_ids_list:
            if paginate:
                return Response({
                    "count": 0, "next": None, "previous": None,
                    "results": {"results": []},
                })
            return Response({"results": {"results": []}})

        base_filter = Q(
            camera_id__in=camera_ids_list,
            image__isnull=False,
            created_at__range=(start_date_time, end_date_time),
            is_rejected=False
        )

        guard_filter = Q(
            camera_id__in=camera_ids_list,
            image__isnull=False,
            start_time__gte=start_date_time,
            start_time__lte=end_date_time,
            is_rejected=False
        )

        facedetection_filter = Q(
            camera_id__in=camera_ids_list,
            image__isnull=False,
            created_at__range=(start_date_time, end_date_time),
            is_rejected=False
        )

        if annotator:
            base_filter &= Q(is_annotated=False)
            guard_filter &= Q(is_annotated=False)
            facedetection_filter &= Q(is_annotated=True)

        filter_values = [value.strip()
                         for value in filter_param.split(',')] if filter_param else []
        filter_values = [value for value in filter_values if value]

        if filter_values:
            status_filter = reduce(
                operator.or_,
                (Q(current_status__contains=value) for value in filter_values)
            )
            base_filter &= status_filter
            guard_filter &= status_filter

        report_specs = {
            'kitchen': {
                'model': KitchenViolationReport,
                'serializer': KitchenViolationReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'employeeactivity': {
                'model': AGGFViolationReport,
                'serializer': AGGFViolationReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'smoking': {
                'model': SmokingViolationReport,
                'serializer': SmokingViolationReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'facedetection': {
                'model': FaceDetectionReport,
                'serializer': FaceDetectionReportSerializer,
                'filter': facedetection_filter,
                'sort_field': 'created_at',
            },
            'guard': {
                'model': GuardPresenceHistory,
                'serializer': GuardPresenceHistorySerializer,
                'filter': guard_filter,
                'sort_field': 'end_time',
            },
            'garbage': {
                'model': GarbageMonitoringReport,
                'serializer': GarbageMonitoringReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'recycle': {
                'model': RecycleMonitoringReport,
                'serializer': RecycleMonitoringReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'buffet': {
                'model': BuffetViolationReport,
                'serializer': BuffetViolationReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'bathroom': {
                'model': BathroomMonitoringHistory,
                'serializer': BathroomMonitoringHistorySerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'sentiment': {
                'model': SentimentAnalysis,
                'serializer': SentimentAnalysisSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'falldetection': {
                'model': FallDetectionMonitoringReport,
                'serializer': FallDetectionMonitoringReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'violencedetection': {
                'model': ViolenceMonitoringReport,
                'serializer': ViolenceMonitoringReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'crowdmonitoring': {
                'model': CrowdMonitoringReport,
                'serializer': CrowdMonitoringReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'climbmonitoring': {
                'model': WallClimbMonitoringReport,
                'serializer': WallClimbMonitoringReportSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'abnormalactivity': {
                'model': AbnormalActivities,
                'serializer': AbnormalActivitiesSerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
            'cleaners': {
                'model': CleanersPresenceHistory,
                'serializer': CleanersPresenceHistorySerializer,
                'filter': base_filter,
                'sort_field': 'created_at',
            },
        }

        if type_list:
            report_specs = {k: v for k, v in report_specs.items() if k in type_list}

        querysets = {}
        key_querysets = []
        for source, spec in report_specs.items():
            queryset = spec['model'].objects.filter(
                spec['filter']).exclude(image='')

            if not annotator:
                queryset = queryset.filter(is_annotated=True)

            if source == 'garbage' and not annotator:
                queryset = _dedup_garbage_queryset(queryset)
            elif source == 'kitchen' and not annotator:
                queryset = _dedup_kitchen_queryset(queryset)

            querysets[source] = queryset
            key_querysets.append(
                queryset.annotate(
                    source=models.Value(
                        source, output_field=models.CharField()),
                    sort_time=F(spec['sort_field']),
                ).values('source', 'id', 'sort_time')
            )

        count_querysets = [
            qs.values('id') for qs in querysets.values()
        ]
        count_union = count_querysets[0].union(*count_querysets[1:], all=True)

        ordered_keys = key_querysets[0].union(
            *key_querysets[1:], all=True).order_by('-sort_time', 'source', '-id')

        if paginate:
            def parse_positive_int(value, default):
                try:
                    return max(int(value or default), 1)
                except (TypeError, ValueError):
                    return default

            page = parse_positive_int(request.query_params.get('page'), 1)
            default_page_size = self.pagination_class.page_size
            max_page_size = self.pagination_class.max_page_size
            requested_page_size = request.query_params.get(
                self.pagination_class.page_size_query_param, default_page_size)
            page_size = parse_positive_int(
                requested_page_size, default_page_size)
            page_size = min(page_size, max_page_size)
            total_count = count_union.count()
            start = (page - 1) * page_size
            stop = start + page_size
            page_keys = list(ordered_keys[start:stop])
        else:
            total_count = None
            page = None
            page_size = None
            page_keys = list(ordered_keys)

        ids_by_source = defaultdict(list)
        for item in page_keys:
            ids_by_source[item['source']].append(item['id'])

        objects_by_key = {}
        for source, ids in ids_by_source.items():
            fetched_objects = querysets[source].filter(
                id__in=ids).select_related('camera', 'camera__tent')
            objects_by_key.update(
                ((source, obj.id), obj) for obj in fetched_objects
            )

        serialized_by_source = {}
        for source, ids in ids_by_source.items():
            objs_ordered = [objects_by_key[(source, pk)]
                            for pk in ids if (source, pk) in objects_by_key]
            if objs_ordered:
                serialized_by_source[source] = {
                    obj.id: data for obj, data in zip(
                        objs_ordered,
                        report_specs[source]['serializer'](
                            objs_ordered, many=True).data
                    )
                }

        serialized_data = []
        for item in page_keys:
            source = item['source']
            data = serialized_by_source.get(source, {}).get(item['id'])
            if data is not None:
                serialized_data.append(data)

        if paginate:
            query_params = request.query_params.copy()

            def build_page_url(page_number):
                query_params['page'] = page_number
                return request.build_absolute_uri(
                    f"{request.path}?{query_params.urlencode()}")

            next_url = build_page_url(page + 1) if page * \
                page_size < total_count else None
            previous_url = build_page_url(page - 1) if page > 1 else None
            return Response({
                "count": total_count,
                "next": next_url,
                "previous": previous_url,
                "results": {"results": serialized_data},
            })

        return Response({"results": {"results": serialized_data}})


@method_decorator(csrf_exempt, name='dispatch')
class FaceDetectionGalleryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        camera_id = kwargs.pop("camera_id", None)

        def parse_id_list(param: str):
            return [int(i) for i in param.split(',') if i.strip().isdigit()]

        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        if not start_date_time_str or not end_date_time_str:
            return Response(
                {"detail": "Start and end date are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date_time = parse_datetime(start_date_time_str)
        end_date_time = parse_datetime(end_date_time_str)

        if not (start_date_time and end_date_time):
            return Response(
                {"detail": "Invalid date or time format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date_time = timezone.make_aware(start_date_time)
        end_date_time = timezone.make_aware(end_date_time)

        camera_ids = parse_id_list(request.GET.get('camera_ids', ''))
        tent_ids = parse_id_list(request.GET.get('tent_ids', ''))
        company_ids = parse_id_list(request.GET.get('company_ids', ''))

        annotator = request.GET.get('is_annotator', 'false').lower() in ['true', '1']
        paginate = request.GET.get('paginate', 'true').lower() in ['true', '1']

        # -------------------------
        # CAMERA FILTER (FaceDetection ONLY)
        # -------------------------
        base_camera_query = Q(type="facedetection")

        if camera_id:
            base_camera_query &= Q(id=camera_id)
        elif camera_ids:
            base_camera_query &= Q(id__in=camera_ids)
        else:
            if tent_ids:
                base_camera_query &= Q(tent__id__in=tent_ids)
            elif company_ids:
                base_camera_query &= Q(tent__company__id__in=company_ids)

        if user.is_admin or user.is_annotator:
            base_camera_query &= Q(tent__company=user.company)
        elif user.is_staff:
            base_camera_query &= Q(tent__in=user.assigned_tent.all())

        cameras = Camera.objects.filter(base_camera_query)

        # -------------------------
        # FACE DETECTION DATA ONLY
        # -------------------------
        facedetection_qs = FaceDetectionReport.objects.filter(
            camera__in=cameras,
            image__isnull=False,
            time__range=(start_date_time, end_date_time),
            is_rejected=False
        ).order_by('-time')

        if annotator:
            facedetection_qs = facedetection_qs.filter(is_annotated=False)
        else:
            facedetection_qs = facedetection_qs.filter(is_annotated=True)

        # -------------------------
        # PAGINATION
        # -------------------------
        if paginate:
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(facedetection_qs, request, view=self)
            serializer = FaceDetectionReportSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = FaceDetectionReportSerializer(facedetection_qs, many=True)
        return Response({"results": serializer.data})



class GuardChartView(APIView):
    permission_classes = [GuardPermission]

    def get(self, request, *args, **kwargs):
        tent_id = request.query_params.get('tent_id')

        start_date_time = get_aware_datetime_from_str(
            request.GET.get('start_date_time')) or None
        end_date_time = get_aware_datetime_from_str(
            request.GET.get('end_date_time')) or None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = None

        # ✅ Filter by single tent_id
        if tent_id:
            try:
                tent_id_int = int(tent_id)
                tents = Tent.objects.filter(id=tent_id_int).first()
            except ValueError:
                return Response({"error": "Invalid tent_id format. Must be an integer."}, status=400)
        else:
            return Response({"error": "tent_id must needed"}, status=400)

        result = []

        # Validate and retrieve camera objects
        camera = Camera.objects.filter(tent=tents, type="guard").first()
        if not camera:
            data = {
                "success": False,
                "message": "No guard cameras found for the provided serial numbers.",
                "results": []
            }
            return Response(data, status=status.HTTP_200_OK)

        # Iterate over cameras
        guard_data = GuardPresenceHistory.objects.filter(
            camera=camera,
            start_time__gte=start_date_time,
            end_time__lte=end_date_time,
            is_rejected=False
        ).order_by('start_time')

        compressed_data = []
        previous_guard_count = None
        segment_start_time = None
        segment_end_time = None
        clean_data = skip_overlapping_entries(guard_data)
        for entry in clean_data:

            current_status = entry.current_status
            guard_count = 0 if current_status[0] == 'absent' else int(
                current_status[0])

            # break handle
            if segment_end_time is not None and entry.start_time > segment_end_time:
                gap = (entry.start_time - segment_end_time).total_seconds()
                if gap > 900:
                    # print(current_status, guard_count, previous_guard_count)
                    # previous segment input
                    if segment_start_time is not None:
                        compressed_data.append({
                            "start_time": convert_utc_to_riyadh(segment_start_time),
                            "end_time": convert_utc_to_riyadh(segment_end_time),
                            "guard_count": previous_guard_count,
                            "time": convert_utc_to_riyadh(segment_end_time),
                        })
                    # # Duplicate previous segment with time = entry.start_time
                    # if segment_start_time is not None:
                    #     compressed_data.append({
                    #         "start_time": convert_utc_to_riyadh(segment_start_time),
                    #         "end_time": convert_utc_to_riyadh(segment_end_time),
                    #         "guard_count": previous_guard_count,
                    #         "time": convert_utc_to_riyadh(segment_end_time),
                    #     })

                    # Add the None segment
                    compressed_data.append({
                        "start_time": convert_utc_to_riyadh(segment_end_time),
                        "end_time": convert_utc_to_riyadh(entry.start_time),
                        "guard_count": None,
                        "time": convert_utc_to_riyadh(segment_end_time),
                    })

                    segment_end_time = None
                    previous_guard_count = None
                    segment_start_time = None
                    # segment_start_time = entry.start_time
                    # segment_end_time = entry.end_time
                    # previous_guard_count = guard_count
                # else:
                #     # Gap <= 119 seconds: Merge with maximum guard count
                #     previous_guard_count = max(
                #         previous_guard_count, guard_count)
                #     segment_end_time = entry.end_time
            if previous_guard_count is None:
                # Start the first segment
                previous_guard_count = guard_count
                segment_start_time = entry.start_time
                segment_end_time = entry.end_time
            elif guard_count != previous_guard_count and previous_guard_count > 0:
                # print(segment_start_time, segment_end_time, previous_guard_count)
                # Guard count changed, save the previous segment
                compressed_data.append({
                    "start_time": convert_utc_to_riyadh(segment_start_time),
                    "end_time": convert_utc_to_riyadh(entry.start_time),
                    "guard_count": previous_guard_count,
                    "time": convert_utc_to_riyadh(segment_start_time),
                })
                # Start new segment
                segment_start_time = entry.start_time
                previous_guard_count = guard_count
            elif guard_count != previous_guard_count and previous_guard_count == 0:
                # print(segment_start_time, segment_end_time, previous_guard_count)
                # Guard count changed, save the previous segment
                compressed_data.append({
                    "start_time": convert_utc_to_riyadh(segment_start_time),
                    "end_time": convert_utc_to_riyadh(segment_end_time),
                    "guard_count": previous_guard_count,
                    "time": convert_utc_to_riyadh(segment_start_time),
                })
                # Start new segment
                segment_start_time = segment_end_time
                previous_guard_count = guard_count
            # Update the segment_end_time regardless
            segment_end_time = entry.end_time

        # Append the final segment
        if segment_start_time is not None:
            # print(segment_start_time, segment_end_time, previous_guard_count)
            compressed_data.append({
                "start_time": convert_utc_to_riyadh(segment_start_time),
                "end_time": convert_utc_to_riyadh(segment_end_time),
                "guard_count": previous_guard_count,
                "time": convert_utc_to_riyadh(segment_start_time),
            })

        last_entry = guard_data.last()

        if last_entry:
            compressed_data.append({
                "start_time": convert_utc_to_riyadh(last_entry.start_time) if last_entry.start_time else None,
                "end_time": convert_utc_to_riyadh(last_entry.end_time) if last_entry.end_time else None,
                "guard_count": 0 if last_entry.current_status[0] == "absent" else int(last_entry.current_status[0]),
                "time": convert_utc_to_riyadh(last_entry.end_time) if last_entry.end_time else None
            })
        else:
            compressed_data.append({
                "start_time": None,
                "end_time": None,
                "guard_count": None,
                "time": None
            })

        result.append({
            "name": camera.sn,
            "data": compressed_data
        })

        return Response({
            "success": True,
            "message": "Guard presence history fetched successfully.",
            "results": result
        }, status=status.HTTP_200_OK)


class CleanerChartView(APIView):
    permission_classes = [CleanersPermission]

    def get(self, request, *args, **kwargs):
        tent_id = request.query_params.get('tent_id')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = None

        # ✅ Filter by single tent_id
        if tent_id:
            try:
                tent_id_int = int(tent_id)
                tents = Tent.objects.filter(id=tent_id_int).first()
            except ValueError:
                return Response({"error": "Invalid tent_id format. Must be an integer."}, status=400)
        else:
            return Response({"error": "tent_id must needed"}, status=400)

        result = []

        # Validate and retrieve camera objects
        camera = Camera.objects.filter(tent=tents, type="bathroom").first()
        if not camera:
            data = {
                "success": False,
                "message": "No Cleaners cameras found for the provided serial numbers.",
                "results": []
            }
            return Response(data, status=status.HTTP_200_OK)

        # Iterate over cameras
        cleaner_data = BathroomMonitoringHistory.objects.filter(
            camera=camera,
            start_time__gte=start_date_time,
            end_time__lte=end_date_time,
            is_annotated=True
        ).order_by('start_time')

        compressed_data = []
        previous_cleaner_count = None
        segment_start_time = None
        segment_end_time = None

        for entry in cleaner_data:
            if previous_cleaner_count is None:
                # Start the first segment
                previous_cleaner_count = entry.cleaner_count
                segment_start_time = entry.start_time
                segment_end_time = entry.end_time
            elif entry.cleaner_count != previous_cleaner_count:
                # Guard count changed, save the previous segment
                compressed_data.append({
                    "start_time": segment_start_time,
                    "end_time": entry.start_time,
                    "cleaner_count": previous_cleaner_count,
                    "time": segment_start_time,
                })
                # Start new segment
                segment_start_time = entry.start_time
                previous_cleaner_count = entry.cleaner_count
            # Update the segment_end_time regardless
            segment_end_time = entry.end_time

        # Append the final segment
        if segment_start_time is not None:
            compressed_data.append({
                "start_time": segment_start_time,
                "end_time": segment_end_time,
                "cleaner_count": previous_cleaner_count,
                "time": segment_start_time,
            })

        result.append({
            "name": camera.sn,
            "data": compressed_data
        })

        return Response({
            "success": True,
            "message": "Cleaner presence history fetched successfully.",
            "results": result
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class CreateKitchenViolationReportView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for the required header key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the secret key (assuming `match_kitchen_camera_key` is defined elsewhere)
        try:
            match_kitchen_camera_key(header_key)  # Implement this function
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve the camera SN from the request data
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the Camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Copy request data and add the camera reference
            data = request.data.copy()
            data['camera'] = camera.pk
            # Serialize and validate the data
            serializer = KitchenViolationReportSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save()
                return Response(
                    {"message": "Violation report created successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name='dispatch')
class CreateAGGFViolationReportView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for the required header key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the secret key (assuming `match_aggf_camera_key` is defined elsewhere)
        try:
            match_aggf_camera_key(header_key)  # Implement this function
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve the camera SN from the request data
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the Camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Copy request data and add the camera reference
            data = request.data.copy()
            data['camera'] = camera.pk
            # Serialize and validate the data
            serializer = AGGFViolationReportSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save()
                return Response(
                    {"message": "Violation report created successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

@method_decorator(csrf_exempt, name='dispatch')
class CreateSmokingViolationReportView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for the required header key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the secret key (assuming `match_aggf_camera_key` is defined elsewhere)
        try:
            match_smoking_camera_key(header_key)  # Implement this function
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve the camera SN from the request data
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the Camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Copy request data and add the camera reference
            data = request.data.copy()
            data['camera'] = camera.pk
            # Serialize and validate the data
            serializer = SmokingViolationReportSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save()
                return Response(
                    {"message": "Violation report created successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
@method_decorator(csrf_exempt, name='dispatch')
class CreateFaceDetectionViolationReportView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for the required header key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the secret key (assuming `match_aggf_camera_key` is defined elsewhere)
        try:
            match_face_detection_camera_key(header_key)  # Implement this function
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve the camera SN from the request data
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the Camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Copy request data and add the camera reference
            data = request.data.copy()
            data['camera'] = camera.pk
            # Serialize and validate the data
            serializer = FaceDetectionReportSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save()
                return Response(
                    {"message": "Face Detection report created successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

@method_decorator(csrf_exempt, name='dispatch')
class CreateBuffetViolationReportView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for the required header key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the secret key (assuming `match_kitchen_camera_key` is defined elsewhere)
        try:
            match_buffet_violation_key(header_key)  # Implement this function
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve the camera SN from the request data
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the Camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Copy request data and add the camera reference
            data = request.data.copy()
            data['camera'] = camera.pk
            # Serialize and validate the data
            serializer = BuffetViolationReportSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save()
                return Response(
                    {"message": "Violation report created successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name='dispatch')
class CreateBuffetViolationFromHumanReportView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for the required header key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the secret key (assuming `match_kitchen_camera_key` is defined elsewhere)
        try:
            match_buffet_violation_key(header_key)  # Implement this function
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve the camera SN from the request data
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the Camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Copy request data and add the camera reference
            data = request.data.copy()
            data['camera'] = camera.pk
            # Check if violation_list exists in the data and convert it to a list
            # Preprocess violation_list
            if 'violation_list' in data and isinstance(data['violation_list'], str):

                data['violation_list'] = json.dumps(
                    [item.strip() for item in data['violation_list'].split(',') if item.strip()])
            serializer = BuffetViolationReportSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                # Save the validated data
                serializer.save(from_human=True)
                return Response(
                    {"message": "Violation report created successfully.",
                     "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            # Catch-all for unexpected errors
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name='dispatch')
class CreateCleanersPresenceHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')

        # Check the header key
        match_cleaners_detection_key(header_key)

        data = request.data
        camera_sn = data.get('sn', None)
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Retrieve the camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:

            # fetch image file from request.FILES
            image_file = request.FILES.get('image')
            present = str(data.get('present', False)).lower() in ['true']

            bathroom_monitoring_history = BathroomMonitoringHistory.objects.create(
                camera=camera,
                cleaner_count=int(data.get('cleaner_count', 0)),
                present=present,
                start_time=data.get('start_time'),
                end_time=data.get('end_time')
            )
            bathroom_monitoring_history.image = image_file
            bathroom_monitoring_history.save()

            return Response(
                {"message": "Cleaners Presence History created successfully."},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"message":
                    f"Error creating Cleaners Presence History: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_camera_statistics_for_tent(request, tent_id, date=None):
    cameras = Camera.objects.filter(tent_id=tent_id, type="headcount")
    camera_stats = []
    if date:
        try:
            filter_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({"error": "Invalid date format. Please use YYYY-MM-DD."}, status=400)

        # Calculate the start and end of the day for filtering
        start_time = filter_date.replace(
            hour=0, minute=0, second=0, microsecond=0)
        end_time = filter_date.replace(
            hour=23, minute=59, second=59, microsecond=999999)
        counter_history = CounterHistory.objects.filter(
            camera__in=cameras, end_time__range=[start_time, end_time])

        # Sum the total_in and total_out for the specific date range
        total_in = counter_history.aggregate(Sum('total_in'))[
            'total_in__sum'] or 0
        total_out = counter_history.aggregate(Sum('total_out'))[
            'total_out__sum'] or 0

        # Append the summed values for the cameras on the specific date
        camera_stats.append({
            'tent_id': tent_id,
            'total_in': total_in,
            'total_out': total_out,
            'date': date
        })
    else:
        # If no date is provided, calculate the sums for all available data
        for camera in cameras:
            camera_data = CounterHistory.objects.filter(camera=camera)
            total_in = camera_data.aggregate(Sum('total_in'))[
                'total_in__sum'] or 0
            total_out = camera_data.aggregate(Sum('total_out'))[
                'total_out__sum'] or 0

            heartbeat = getattr(camera, 'heartbeat', None)
            heartbeat_time = heartbeat.time if heartbeat else None

            camera_stats.append({
                'camera_sn': camera.sn,
                'camera_type': camera.type,
                'total_in': total_in,
                'total_out': total_out,
                'heartbeat_time': heartbeat_time
            })

    # Return the result as JSON
    data = {
        "success": True,
        "message": "Camera statistics Fetched Successfully",
        "camera_statistics": camera_stats
    }
    return Response(data, status=status.HTTP_200_OK)


class CameraUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"error": "No CSV file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Decode and read CSV
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = StringIO(decoded_file)
            reader = DictReader(io_string)
        except Exception as e:
            return Response({"error": f"Failed to read CSV file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        errors = []

        for idx, row in enumerate(reader, start=1):
            sn = row.get('sn')
            tent_name = row.get('tent_name')
            type = row.get('type')

            if not sn or not tent_name or not type:
                errors.append(f"Row {idx}: Missing sn, tent_name, or type.")
                continue

            try:
                tent = Tent.objects.get(name=tent_name)
            except Tent.DoesNotExist:
                errors.append(
                    f"Row {idx}: Tent with name {tent_name} does not exist.")
                continue

            try:
                Camera.objects.create(
                    sn=sn,
                    tent=tent,
                    type=type
                )
                created += 1
            except Exception as e:
                errors.append(f"Row {idx}: Failed to create Camera - {str(e)}")

        return Response({
            "success": True,
            "message": f"{created} records created successfully.",
            "errors": errors
        }, status=status.HTTP_201_CREATED)


class CameraSampleCSVView(APIView):
    def get(self, request, *args, **kwargs):
        csv_content = "sn,tent_name,type\n"
        # csv_content += "SN001,Tent A,clean\n"

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="camera.csv"'
        return response


class TentViolationSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Get start and end date from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')

        # Parse the dates
        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        date_filter = None

        # Check if both start and end are provided
        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Make them timezone-aware if they're naive
        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        # If start_date == end_date (same day), filter the entire day
        if start.date() == end.date():
            start_of_day = start.replace(
                hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            date_filter = Q(camera__kitchen_violation_histories__created_at__gte=start_of_day,
                            camera__kitchen_violation_histories__created_at__lt=end_of_day)
        else:
            # Add 1 day to end to make it exclusive
            end = end + timedelta(days=1)
            date_filter = Q(camera__kitchen_violation_histories__created_at__gte=start,
                            camera__kitchen_violation_histories__created_at__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)
        kitchen_camera_exists = Camera.objects.filter(
                tent=OuterRef('pk'),
                type='kitchen'
            )

        tents = tents.annotate(
            kitchen_camera_exists=Exists(kitchen_camera_exists)
        ).filter(kitchen_camera_exists=True).order_by('name')
        # Annotate violation count and order
        tents = tents.annotate(
            violation_count=Count(
                'camera__kitchen_violation_histories',
                filter=Q(
                    camera__kitchen_violation_histories__violation=True) & date_filter
            )
        ).order_by('violation_count')
        # ✅ Step 4: Convert to list and sort:
        # violation_count ASC + tent name natural sort ASC
        tents = list(tents)
        tents = sorted(
            tents,
            key=lambda x: (x.violation_count, tent_name_list_dict_sorting(x.name))  # ASCENDING
        )

        # ✅ Step 5: Rank (1, 2, 3… regardless of tie)
        tent_data = []

        for index, tent in enumerate(tents, start=1):
            tent_data.append({
                "tent_id": tent.id,
                "tent_name": tent.name,
                "violation_count": tent.violation_count,
                "rank": index
            })
        if response_type == 'csv':
            return generate_csv_response(tent_data, 'kitchen_violation_ranking_data.csv')

        # serializer = TentViolationSummarySerializer(tents, many=True)
        return Response({
            "success": True,
            "message": "Tent-wise violation summary retrieved successfully.",
            "data": tent_data
        }, status=status.HTTP_200_OK)


class CameraViolationSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get start and end date from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Parse the dates
        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        date_filter = None

        # Check if both start and end are provided
        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Make them timezone-aware if they're naive
        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        # If start_date == end_date (same day), filter the entire day
        if start.date() == end.date():
            start_of_day = start.replace(
                hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            date_filter = Q(kitchen_violation_histories__created_at__gte=start_of_day,
                            kitchen_violation_histories__created_at__lt=end_of_day)
        else:
            # Add 1 day to end to make it exclusive
            end = end + timedelta(days=1)
            date_filter = Q(kitchen_violation_histories__created_at__gte=start,
                            kitchen_violation_histories__created_at__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)

        cameras = Camera.objects.filter(tent__in=tents, type='kitchen').annotate(
            violation_count=Count(
                'kitchen_violation_histories',
                filter=Q(kitchen_violation_histories__violation=True) & date_filter
            )
        ).select_related('tent').order_by('violation_count')
        # Add rank manually
        camera_data = []
        rank = 1
        previous_violation = None
        for cam in cameras:
            current_violation = cam.violation_count
            if previous_violation is None:
                previous_violation = current_violation
            elif current_violation != previous_violation:
                rank += 1
                previous_violation = current_violation
            # Append camera data to the list
            camera_data.append({
                'id': cam.id,
                'camera': cam.sn,
                'tent_name': cam.tent.name if cam.tent else None,
                "tent_id": cam.tent.id if cam.tent else None,
                'violation_count': cam.violation_count,
                'rank': rank
            })

        # serializer = CameraViolationSummarySerializer(cameras, many=True)
        return Response({
            "success": True,
            "message": "Camera-wise violation summary retrieved successfully.",
            "data": camera_data
        }, status=status.HTTP_200_OK)


class TentGarbageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Get start and end date from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')

        # Parse the dates
        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        # Check if both start and end are provided
        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Make them timezone-aware if they're naive
        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        # Add 1 day to end to make it exclusive
        end = end + timedelta(days=1)

        # Prepare filter condition
        date_filter = Q()
        date_filter = Q(camera__garbage_monitoring_histories__start_time__gte=start,
                        camera__garbage_monitoring_histories__start_time__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)
        # Step 2: Filter only tents that have at least one garbage camera
        garbage_camera_exists = Camera.objects.filter(
            tent=OuterRef('pk'),
            type='garbage'
        )

        tents = tents.annotate(
            garbage_camera_exists=Exists(garbage_camera_exists)
        ).filter(garbage_camera_exists=True)
        # Annotate violation count and order
        tents = tents.annotate(
            violation_count=Count(
                'camera__garbage_monitoring_histories',
                filter=Q(
                    camera__garbage_monitoring_histories__is_clean=False, camera__garbage_monitoring_histories__is_annotated=True) & date_filter
            )
        ).order_by('violation_count')
        
        # Step 4: Sort tents by violation_count descending, then tent_name (natural)
        tents = list(tents)
        tents = sorted(
            tents,
            key=lambda x: (x.violation_count, tent_name_list_dict_sorting(x.name))
        )


        tent_data = []
        for index, tent in enumerate(tents, start=1):
            tent_data.append({
                "tent_id": tent.id,
                'tent_name': tent.name,
                'violation_count': tent.violation_count,
                "rank": index
            })
            
        # rank = 1
        # previous_violation = None

        # # Ensure tents are sorted by violation_count in descending order
        # # sorted_tents = sorted(tents, key=lambda x: x.violation_count, reverse=True)

        # for tent in tents:
        #     current_violation = tent.violation_count
        #     if previous_violation is None:
        #         previous_violation = current_violation
        #     elif current_violation != previous_violation:
        #         rank += 1
        #         previous_violation = current_violation
        #     tent_data.append({
        #         "tent_id": tent.id,
        #         'tent_name': tent.name,
        #         'violation_count': current_violation,
        #         "rank": rank
        #     })
        if response_type == 'csv':
            return generate_csv_response(tent_data, 'garbage_violation_ranking_data.csv')
        # serializer = TentViolationSummarySerializer(tents, many=True)
        return Response({
            "success": True,
            "message": "Tent-wise Garbage summary retrieved successfully.",
            "data": tent_data
        }, status=status.HTTP_200_OK)


class CameraGarbageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get start and end date from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Parse the dates
        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        # Check if both start and end are provided
        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Make them timezone-aware if they're naive
        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        # Add 1 day to end to make it exclusive
        end = end + timedelta(days=1)

        # Prepare filter condition
        date_filter = Q()
        date_filter = Q(garbage_monitoring_histories__start_time__gte=start,
                        garbage_monitoring_histories__start_time__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)

        cameras = Camera.objects.filter(tent__in=tents, type='garbage').annotate(
            violation_count=Count(
                'garbage_monitoring_histories',
                filter=Q(
                    garbage_monitoring_histories__is_clean=False, garbage_monitoring_histories__is_annotated=True) & date_filter
            )
        ).select_related('tent').order_by('violation_count')
        # Add rank manually
        camera_data = []
        rank = 1
        previous_violation = None
        for cam in cameras:
            current_violation = cam.violation_count
            if previous_violation is None:
                previous_violation = current_violation
            elif current_violation != previous_violation:
                rank += 1
                previous_violation = current_violation
            # Append camera data to the list
            camera_data.append({
                'id': cam.id,
                'camera': cam.sn,
                'tent_name': cam.tent.name if cam.tent else None,
                "tent_id": cam.tent.id if cam.tent else None,
                'violation_count': cam.violation_count,
                'rank': rank
            })

        # serializer = CameraViolationSummarySerializer(cameras, many=True)
        return Response({
            "success": True,
            "message": "Camera-wise violation summary retrieved successfully.",
            "data": camera_data
        }, status=status.HTTP_200_OK)


class TentBuffetSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Get start and end date from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')

        # Parse the dates
        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        # Check if both start and end are provided
        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Make them timezone-aware if they're naive
        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        # Add 1 day to end to make it exclusive
        end = end + timedelta(days=1)

        # Prepare filter condition
        date_filter = Q()
        date_filter = Q(camera__buffet_violation_histories__start_time__gte=start,
                        camera__buffet_violation_histories__start_time__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)
        
        buffet_camera_exists = Camera.objects.filter(
            tent=OuterRef('pk'),
            type='buffet'
        )
        # Step 2: Filter only tents that have at least one buffet camera
        tents = tents.annotate(
            buffet_camera_exists=Exists(buffet_camera_exists)
        ).filter(buffet_camera_exists=True)
        
        # Annotate violation count and order
        tents = tents.annotate(
            violation_count=Count(
                'camera__buffet_violation_histories',
                filter=Q(
                    camera__buffet_violation_histories__violation=True, camera__buffet_violation_histories__is_annotated=True) & date_filter
            )
        ).order_by('violation_count')
        
        tents =list(tents)
        
        tents = sorted(
            tents,
            key=lambda x: (x.violation_count, tent_name_list_dict_sorting(x.name))
        )

        tent_data = []
        
        for index, tent in enumerate(tents, start=1):
            tent_data.append({
                "tent_id": tent.id,
                'tent_name': str(tent.name),
                'violation_count': tent.violation_count,
                "rank": index
            })
        if response_type == 'csv':
            return generate_csv_response(tent_data, 'buffet_violation_ranking_data.csv')
        # rank = 1
        # previous_violation = None

        # # Ensure tents are sorted by violation_count in descending order
        # # sorted_tents = sorted(tents, key=lambda x: x.violation_count, reverse=True)

        # for tent in tents:
        #     current_violation = tent.violation_count
        #     if previous_violation is None:
        #         previous_violation = current_violation
        #     elif current_violation != previous_violation:
        #         rank += 1
        #         previous_violation = current_violation
        #     tent_data.append({
        #         "tent_id": tent.id,
        #         'tent_name': tent.name,
        #         'violation_count': current_violation,
        #         "rank": rank
        #     })
        # serializer = TentViolationSummarySerializer(tents, many=True)
        return Response({
            "success": True,
            "message": "Tent-wise Buffet Violation summary retrieved successfully.",
            "data": tent_data
        }, status=status.HTTP_200_OK)


class CameraBuffetSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get start and end date from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Parse the dates
        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        # Check if both start and end are provided
        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Make them timezone-aware if they're naive
        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        # Add 1 day to end to make it exclusive
        end = end + timedelta(days=1)

        # Prepare filter condition
        date_filter = Q()
        date_filter = Q(buffet_violation_histories__start_time__gte=start,
                        buffet_violation_histories__start_time__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)

        cameras = Camera.objects.filter(tent__in=tents, type='buffet').annotate(
            violation_count=Count(
                'buffet_violation_histories',
                filter=Q(buffet_violation_histories__violation=True,
                         buffet_violation_histories__is_annotated=True) & date_filter
            )
        ).select_related('tent').order_by('violation_count')
        # Add rank manually
        camera_data = []
        rank = 1
        previous_violation = None
        for cam in cameras:
            current_violation = cam.violation_count
            if previous_violation is None:
                previous_violation = current_violation
            elif current_violation != previous_violation:
                rank += 1
                previous_violation = current_violation
            # Append camera data to the list
            camera_data.append({
                'id': cam.id,
                'camera': cam.sn,
                'tent_name': cam.tent.name if cam.tent else None,
                "tent_id": cam.tent.id if cam.tent else None,
                'violation_count': cam.violation_count,
                'rank': rank
            })

        # serializer = CameraViolationSummarySerializer(cameras, many=True)
        return Response({
            "success": True,
            "message": "Camera-wise Buffet Violation summary retrieved successfully.",
            "data": camera_data
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class CreateGarbageMonitoringHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            garbage_monitoring = GarbageMonitoringReport.objects.get(pk=pk)
            serializer = GarbageMonitoringReportSerializer(garbage_monitoring)
            data = {
                "success": True,
                "message": "Garbage Monitoring Report retrieved successfully.",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)

        garbage_monitorings = GarbageMonitoringReport.objects.filter(
            is_annotated=False, is_ai_annotated=False)
        serializer = GarbageMonitoringReportSerializer(
            garbage_monitorings, many=True)
        data = {
            "success": True,
            "message": "Garbage Monitoring Reports retrieved successfully.",
            "data": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        garbage_monitoring = GarbageMonitoringReport.objects.get(pk=pk)
        serializer = GarbageMonitoringReportSerializer(
            garbage_monitoring, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Garbage Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "message": "Error updating Garbage Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        #return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        header_key = request.headers.get('X-Secret-Key')

        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Retrieve the camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create a mutable copy of the request data
        data = request.data.copy()
        data['camera'] = camera.pk

        serializer = GarbageMonitoringReportSerializer(
            data=data, context={'request': request})

        if serializer.is_valid():
            garbage_monitoring = serializer.save(camera=camera)
            return Response(
                {
                    "message": "Garbage Monitoring History created successfully.",
                    "data": GarbageMonitoringReportSerializer(garbage_monitoring).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": "Invalid data", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class GarbageMonitoringHistoryReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        # Extract query params

        user = request.user
        response_type = request.GET.get('type', 'json')
        is_clean = request.GET.get('is_clean', None)
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'

        # Tent filtering
        if tent_id_list:
            try:
                tent_ids = list(map(int, tent_id_list.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)

        else:
            if user.is_admin:
                tents = Tent.objects.filter(
                    company=request.user.company).order_by('id')
            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                tents = Tent.objects.filter(
                    id__in=assigned_tent_ids, company=request.user.company).order_by('id')
            if not tents.exists():
                return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        if not tents.exists():
            return Response({"detail": "No tents found."}, status=404)

        # Parse and validate dates
        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                return Response({"error": "Start and end dates are required."}, status=400)

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.min.time())) + timedelta(days=1)
        except Exception as e:
            return Response({"error": f"Invalid dates: {str(e)}"}, status=400)

        # Base queryset
        queryset = GarbageMonitoringReport.objects.filter(
            camera__tent__in=tents,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            is_annotated=False
        )

        if is_clean is not None:
            # Convert string to boolean
            is_clean_bool = is_clean.lower() == 'true'
            queryset = queryset.filter(is_clean=is_clean_bool)

        queryset = _dedup_garbage_queryset(queryset)

        # Fetch all matching records
        queryset = queryset.order_by('-created_at').values(
            'camera__tent__name',
            'created_at',
            'camera__sn',
            'is_clean',
            'image',
        )

        data = []
        for record in queryset:
            image_url = f"{settings.MEDIA_URL}{record['image']}" if record['image'] else None
            image_full_url = f"{settings.BASE_URL}{image_url}" if image_url and settings.DEBUG else image_url

            data.append({
                'tent_name': record['camera__tent__name'],
                'created_at': record['created_at'].strftime('%Y-%m-%d %H:%M'),
                'camera_sn': record['camera__sn'],
                'is_clean': record['is_clean'],
                'image': image_full_url,
            })

        # CSV Response
        if response_type == "csv":
            return generate_csv_response(data, 'report_data.csv')

        # Paginated or full response
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Garbage Monitoring Data Retrieved",
            'results': data,
        }, status=status.HTTP_200_OK)


class GarbageMonitoringReportListAPIView(ListAPIView):
    """
    List all garbage monitoring reports with pagination support.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 10, max: 100)
    """
    serializer_class = GarbageMonitoringReportSerializer
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        """Return filtered queryset for garbage monitoring reports."""
        return GarbageMonitoringReport.objects.select_related(
            'camera__tent'
        ).filter(
            is_annotated=False, 
            is_ai_annotated=False
        ).order_by('-created_at')

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')

        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Retrieve the camera object using the SN
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create a mutable copy of the request data
        data = request.data.copy()
        data['camera'] = camera.pk

        serializer = GarbageMonitoringReportSerializer(
            data=data, context={'request': request})

        if serializer.is_valid():
            garbage_monitoring = serializer.save()
            return Response(
                {
                    "message": "Garbage Monitoring History created successfully.",
                    "data": GarbageMonitoringReportSerializer(garbage_monitoring).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": "Invalid data", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class GarbageMonitoringReportDetailAPIView(RetrieveAPIView):
    """
    Retrieve a specific garbage monitoring report by ID.
    """
    serializer_class = GarbageMonitoringReportSerializer
    queryset = GarbageMonitoringReport.objects.select_related('camera__tent').all()
    lookup_field = 'pk'

    def put(self, request, pk=None):
        garbage_monitoring = GarbageMonitoringReport.objects.get(pk=pk)
        serializer = GarbageMonitoringReportSerializer(
            garbage_monitoring, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Garbage Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "message": "Error updating Garbage Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CreateFallDetectionMonitoringHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            fall_detection_monitoring = FallDetectionMonitoringReport.objects.get(pk=pk)
            serializer = FallDetectionMonitoringReportSerializer(fall_detection_monitoring)
            return Response({
                "success": True,
                "message": "Fall Detection Monitoring Report retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        fall_detection_monitorings = FallDetectionMonitoringReport.objects.filter(
            is_annotated=False, is_ai_annotated=False
        )
        serializer = FallDetectionMonitoringReportSerializer(
            fall_detection_monitorings, many=True
        )
        return Response({
            "success": True,
            "message": "Fall Detection Monitoring Reports retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        fall_detection_monitoring = FallDetectionMonitoringReport.objects.get(pk=pk)
        serializer = FallDetectionMonitoringReportSerializer(
            fall_detection_monitoring, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Fall Detection Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Error updating Fall Detection Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response({"message": "Camera SN is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        data['camera'] = camera.pk

        fall_detection_value = data.get('fall_detection', None)

        if fall_detection_value == "fall_detected":
            data['is_fall_detected'] = True
        else:
            data['is_fall_detected'] = False
            
        
        serializer = FallDetectionMonitoringReportSerializer(
            data=data, context={'request': request}
        )

        if serializer.is_valid():
            instance = serializer.save(camera=camera)
            return Response({
                "message": "Fall Detection Monitoring History created successfully.",
                "data": FallDetectionMonitoringReportSerializer(instance).data,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Invalid data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CreateViolenceMonitoringHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            violence_monitoring = ViolenceMonitoringReport.objects.get(pk=pk)
            serializer = ViolenceMonitoringReportSerializer(violence_monitoring)
            return Response({
                "success": True,
                "message": "Violence Monitoring Report retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        violence_monitorings = ViolenceMonitoringReport.objects.filter(
            is_annotated=False, is_ai_annotated=False
        )
        serializer = ViolenceMonitoringReportSerializer(
            violence_monitorings, many=True
        )
        return Response({
            "success": True,
            "message": "Violence Monitoring Reports retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        violence_monitoring = ViolenceMonitoringReport.objects.get(pk=pk)
        serializer = ViolenceMonitoringReportSerializer(
            violence_monitoring, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Violence Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Error updating Violence Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response({"message": "Camera SN is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        data['camera'] = camera.pk

        violence_value = data.get('violence', None)
        if violence_value == "violence":
            data['is_violence'] = True
        elif violence_value == "non_violence":
            data['is_violence'] = False
        else:
            return Response({"message": "Invalid violence value."},
                            status=status.HTTP_400_BAD_REQUEST)
            
        
        serializer = ViolenceMonitoringReportSerializer(
            data=data, context={'request': request}
        )

        if serializer.is_valid():
            instance = serializer.save(camera=camera)
            return Response({
                "message": "Violence Monitoring History created successfully.",
                "data": ViolenceMonitoringReportSerializer(instance).data,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Invalid data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CreateCrowdMonitoringHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            crowd_monitoring = CrowdMonitoringReport.objects.get(pk=pk)
            serializer = CrowdMonitoringReportSerializer(crowd_monitoring)
            return Response({
                "success": True,
                "message": "Crowd Monitoring Report retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        page      = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        crowd_monitorings = CrowdMonitoringReport.objects.filter(
            is_annotated=False, is_ai_annotated=False
        ).select_related('camera__tent').order_by('-created_at')

        paginated_qs, total_count, pagination_info = paginate_queryset(
            crowd_monitorings, page, page_size
        )
        serializer = CrowdMonitoringReportSerializer(paginated_qs, many=True)
        return Response({
            "success": True,
            "message": "Crowd Monitoring Reports retrieved successfully.",
            "pagination": pagination_info,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        crowd_monitoring = CrowdMonitoringReport.objects.get(pk=pk)
        serializer = CrowdMonitoringReportSerializer(
            crowd_monitoring, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Crowd Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Error updating Crowd Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response({"message": "Camera SN is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        data['camera'] = camera.pk
        
        # crowd_value = data.get('crowd', None)
        # if crowd_value == "high":
        #     data['is_crowd'] = True
        # elif crowd_value == "warn":
        #     data['is_crowd'] = False
        # elif crowd_value is not None:
        #     return Response({"message": "Invalid crowd value. Use 'high' or 'warn'."},
        #                     status=status.HTTP_400_BAD_REQUEST)

        serializer = CrowdMonitoringReportSerializer(
            data=data, context={'request': request}
        )

        if serializer.is_valid():
            instance = serializer.save(camera=camera)
            return Response({
                "message": "Crowd Monitoring History created successfully.",
                "data": CrowdMonitoringReportSerializer(instance).data,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Invalid data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)        


class CrowdCurrentStatusView(APIView):
    """
    GET /camera/crowd-current-status/
    Returns the current crowd status for every crowdmonitoring camera.
    Current status = the most recent annotated record whose updated_at <= now.
    """
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        latest_status_sq = (
            CrowdMonitoringReport.objects
            .filter(camera=OuterRef('pk'), is_annotated=True, updated_at__lte=now)
            .order_by('-updated_at')
            .values('annotator_status')[:1]
        )
        latest_updated_sq = (
            CrowdMonitoringReport.objects
            .filter(camera=OuterRef('pk'), is_annotated=True, updated_at__lte=now)
            .order_by('-updated_at')
            .values('updated_at')[:1]
        )

        cameras = (
            Camera.objects
            .filter(type='crowdmonitoring')
            .select_related('tent__company')
            .annotate(
                current_status=Subquery(latest_status_sq),
                status_updated_at=Subquery(latest_updated_sq),
            )
            .order_by('tent__company__name', 'sn')
        )

        data = [
            {
                'camera_id': cam.id,
                'camera_sn': cam.sn,
                'tent_id': cam.tent_id,
                'tent_name': cam.tent.name if cam.tent else None,
                'company_name': cam.tent.company.name if cam.tent and cam.tent.company else None,
                'current_status': cam.current_status,
                'status_updated_at': cam.status_updated_at,
            }
            for cam in cameras
        ]

        return Response({
            'success': True,
            'message': 'Crowd current status retrieved successfully.',
            'total': len(data),
            'data': data,
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class CreateWallClimbMonitoringHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            climb_monitoring = WallClimbMonitoringReport.objects.get(pk=pk)
            serializer = WallClimbMonitoringReportSerializer(climb_monitoring)
            return Response({
                "success": True,
                "message": "Wall Climb Monitoring Report retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        climb_monitorings = WallClimbMonitoringReport.objects.filter(
            is_annotated=False, is_ai_annotated=False
        )
        serializer = WallClimbMonitoringReportSerializer(
            climb_monitorings, many=True
        )
        return Response({
            "success": True,
            "message": "Wall Climb Monitoring Reports retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        climb_monitoring = WallClimbMonitoringReport.objects.get(pk=pk)
        serializer = WallClimbMonitoringReportSerializer(
            climb_monitoring, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Wall Climb Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Error updating Wall Climb Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        data['camera'] = camera.pk

        climb_value = data.get('climb', None)

        if climb_value == "climb":
            data['is_climb'] = True
        elif climb_value == "no_climb":
            data['is_climb'] = False
        else:
            return Response(
                {"message": "Invalid climb value."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = WallClimbMonitoringReportSerializer(
            data=data,
            context={'request': request}
        )

        if serializer.is_valid():
            instance = serializer.save(camera=camera)
            return Response({
                "message": "Wall Climb Monitoring History created successfully.",
                "data": WallClimbMonitoringReportSerializer(instance).data,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Invalid data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        

@method_decorator(csrf_exempt, name='dispatch')
class CreateAbnormalActivitiesHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            abnormal = AbnormalActivities.objects.get(pk=pk)
            serializer = AbnormalActivitiesSerializer(abnormal)
            return Response({
                "success": True,
                "message": "Abnormal Activities Report retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        abnormals = AbnormalActivities.objects.filter(
            is_annotated=False, is_ai_annotated=False
        )
        serializer = AbnormalActivitiesSerializer(
            abnormals, many=True
        )
        return Response({
            "success": True,
            "message": "Abnormal Activities Reports retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        abnormal = AbnormalActivities.objects.get(pk=pk)
        serializer = AbnormalActivitiesSerializer(
            abnormal, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Abnormal Activities Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Error updating Abnormal Activities Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        print("FILES:", request.FILES)   # <-- ADD THIS LINE
        print("DATA:", request.data)     
        header_key = request.headers.get('X-Secret-Key')
        match_garbage_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        data['camera'] = camera.pk

        motion_value = data.get('status', None)

        if motion_value == "motion_detected":
            data['is_motion_detected'] = True
        elif motion_value == "no_motion":
            data['is_motion_detected'] = False
        else:
            return Response(
                {"message": "Invalid motion value."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AbnormalActivitiesSerializer(
            data=data,
            context={'request': request}
        )

        if serializer.is_valid():
            instance = serializer.save(camera=camera)
            return Response({
                "message": "Abnormal Activities History created successfully.",
                "data": AbnormalActivitiesSerializer(instance).data,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Invalid data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CreateSentimentAnalysisView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk:
            try:
                instance = SentimentAnalysis.objects.get(id=pk)
                serializer = SentimentAnalysisSerializer(instance)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except SentimentAnalysis.DoesNotExist:
                return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

        else:
            sort = request.GET.get('sort', None)
            total = int(request.GET.get('per_page', 100))

            queryset = SentimentAnalysis.objects.filter(
                is_annotated=False, is_ai_annotated=False)
            if sort == "new":
                queryset = queryset.order_by('id')
            else:
                queryset = queryset.order_by('-id')

            queryset = queryset[:total]
            serializer = SentimentAnalysisSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        data = request.data

        if pk:
            try:
                instance = SentimentAnalysis.objects.get(id=pk)
            except SentimentAnalysis.DoesNotExist:
                return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = SentimentAnalysisSerializer(
                instance, data=data, partial=True)
        else:
            serializer = SentimentAnalysisSerializer(data=data)

        if serializer.is_valid():
            saved_instance = serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        # return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # Validate secret key
        header_key = request.headers.get('X-Secret-Key')
        if not header_key:
            return Response(
                {"message": "X-Secret-Key header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match_sentiment_analysis_key(header_key)
        except Exception as e:
            return Response(
                {"message": "Invalid X-Secret-Key.", "details": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get camera SN
        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            data = request.data.copy()
            data['camera'] = camera.pk

            serializer = SentimentAnalysisSerializer(
                data=data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Sentiment analysis report created successfully.",
                        "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Invalid data.", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"message": "An unexpected error occurred.",
                    "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BuffetCameraLinkList(APIView):
    def get(self, request):
        cameras = Camera.objects.filter(type='buffet')
        serializer = BuffetCameraSerializer(cameras, many=True)
        data = {
            "success": True,
            "message": "Camera list fetched successfully.",
            "results": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)


class PeopleCountingCardView(APIView):
    permission_classes = [PeopleCountPermission]

    def get(self, request):
        user = request.user
        """
        Get counter statistics for all tents or for specific tents if tent_ids are provided.
        Optionally filter by date range using start_date_time and end_date_time.
        """
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            HAJJ_START_DATE = date(2026, 5, 26)
            now_saudi = timezone.now().astimezone(saudi_tz)
            start_date_time = saudi_tz.localize(datetime.combine(HAJJ_START_DATE, time(7,0,0)))
            end_date_time = now_saudi

        start_date_time = start_end_time_to_riyad(start_date_time)
        end_date_time   = start_end_time_to_riyad(end_date_time)

        if user.is_admin:
            tents = Tent.objects.filter(company=request.user.company)
        else:
            assigned_tent_ids = user.assigned_tent.values_list('id', flat=True)
            tents = Tent.objects.filter(
                id__in=assigned_tent_ids, company=request.user.company)

        if tent_ids:
            try:
                tent_id_list = [int(tid.strip()) for tid in tent_ids.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        # Fetch all peoplecount cameras for the filtered tents in one query
        all_cameras = (
            Camera.objects
            .filter(type="peoplecount", tent__in=tents)
            .select_related('tent')
        )

        # Fetch all records for those cameras in the date range in one query
        all_records = (
            CounterHistory.objects
            .filter(
                camera__in=all_cameras,
                created_at__gte=start_date_time,
                created_at__lte=end_date_time,
            )
            .order_by('camera_id', 'created_at')
        )

        # Group records by (tent_id, gate_key, camera_id)
        # gate_key = gate_id for cameras with a gate, else 'default' (all no-gate cameras smart_aggregated together)
        from collections import defaultdict
        cam_to_tent = {c.id: c.tent_id for c in all_cameras}
        cam_to_gate = {c.id: (c.gate_id if c.gate_id else 'default') for c in all_cameras}

        # tent_id → gate_key → cam_id → [recs]
        tent_gate_records = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for rec in all_records:
            tid = cam_to_tent.get(rec.camera_id)
            gk  = cam_to_gate.get(rec.camera_id)
            if tid:
                tent_gate_records[tid][gk][rec.camera_id].append(rec)

        # Build per-tent results using 5-min bucket smart aggregation per gate, summed across gates
        BUCKET_SIZE = timedelta(minutes=5)
        result      = []

        for tent in tents:
            gate_map  = tent_gate_records[tent.id]  # gate_key → cam_id → [recs]
            last_update = None
            count     = sum(len(recs) for cam_recs in gate_map.values() for recs in cam_recs.values())

            if gate_map:
                latest = max(
                    (rec for cam_recs in gate_map.values() for recs in cam_recs.values() for rec in recs),
                    key=lambda r: r.created_at,
                    default=None,
                )
                last_update = latest.created_at if latest else None

            total_in  = 0
            total_out = 0

            for cam_buckets in gate_map.values():
                # bucket_idx → cam_id → [sum_in, sum_out]  — one gate at a time
                bucket_cam = defaultdict(dict)
                for cam_id, recs in cam_buckets.items():
                    for rec in recs:
                        if rec.created_at:
                            idx = int((rec.created_at - start_date_time).total_seconds() // BUCKET_SIZE.total_seconds())
                            if cam_id not in bucket_cam[idx]:
                                bucket_cam[idx][cam_id] = [0, 0]
                            bucket_cam[idx][cam_id][0] += rec.total_in
                            bucket_cam[idx][cam_id][1] += rec.total_out

                # smart_aggregate cameras within this gate, then add to tent total
                for idx in sorted(bucket_cam.keys()):
                    cam_totals = bucket_cam[idx]
                    total_in  += smart_aggregate([v[0] for v in cam_totals.values()])
                    total_out += smart_aggregate([v[1] for v in cam_totals.values()])

            current_staying    = max(total_in - total_out, 0)
            current_percentage = round(
                (current_staying / tent.capacity) * 100, 2) if tent.capacity else 0.00

            result.append({
                'id':                 tent.id,
                'name':               tent.name,
                'capacity':           tent.capacity,
                'total_in':           total_in,
                'total_out':          total_out,
                'current_staying':    current_staying,
                'current_percentage': current_percentage,
                'last_update':        convert_utc_to_riyadh(last_update) if last_update else None,
                'count':              count,
            })

        return Response({
            "success":         True,
            "message":         "Camera list fetched successfully.",
            "start_date_time": start_date_time,
            "end_date_time":   end_date_time,
            "results":         result
        }, status=status.HTTP_200_OK)


class PeopleGraphView(APIView):
    permission_classes = [PeopleCountPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        # start_date_time_str = start_date_time_str.replace(' ', 'T')
        end_date_time_str = request.GET.get('end_date_time')
        # end_date_time_str = end_date_time_str.replace(' ', 'T')
        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None
        if start_date_time and end_date_time:
            start_date_time = start_end_time_to_riyad(start_date_time)
            end_date_time = start_end_time_to_riyad(end_date_time)

        if not start_date_time or not end_date_time:
            HAJJ_START_DATE = date(2026, 5, 26)
            now_saudi = timezone.now().astimezone(saudi_tz)
            start_date_time = saudi_tz.localize(datetime.combine(HAJJ_START_DATE, time(7,0,0)))
            end_date_time = now_saudi

        tents = None
        if user.is_admin:
            tents = Tent.objects.filter(
                company=request.user.company)

        else:
            assigned_tent_ids = user.assigned_tent.values_list(
                'id', flat=True)
            tents = Tent.objects.filter(
                id__in=assigned_tent_ids, company=request.user.company)

        if tent_ids:
            try:
                tent_id_list = [int(tid.strip()) for tid in tent_ids.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        # Generate 30-minute intervals
        # time_labels = []
        # current_time = start_date_time
        # while current_time <= end_date_time:
        #     time_labels.append(current_time)
        #     current_time += timedelta(minutes=5)

        # 2-query fetch: cameras then all records in range
        all_cameras = Camera.objects.filter(type="peoplecount", tent__in=tents).select_related('tent')
        all_records = CounterHistory.objects.filter(
            camera__in=all_cameras,
            created_at__gte=start_date_time,
            created_at__lte=end_date_time,
        ).only('camera_id', 'total_in', 'total_out', 'created_at')

        cam_to_tent = {c.id: c.tent_id for c in all_cameras}
        cam_to_gate = {c.id: (c.gate_id if c.gate_id else 'default') for c in all_cameras}
        BUCKET_SECS = 300  # 5 minutes

        # tent_id → gate_key → bucket_idx → camera_id → [in, out]
        tent_gate_buckets = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        total_counts = defaultdict(int)

        for rec in all_records:
            if not rec.created_at:
                continue
            tid = cam_to_tent.get(rec.camera_id)
            gk  = cam_to_gate.get(rec.camera_id)
            if not tid:
                continue
            delta    = (rec.created_at - start_date_time).total_seconds()
            buck_idx = int(delta // BUCKET_SECS)
            total_counts[tid] += 1
            if rec.camera_id not in tent_gate_buckets[tid][gk][buck_idx]:
                tent_gate_buckets[tid][gk][buck_idx][rec.camera_id] = [0, 0]
            tent_gate_buckets[tid][gk][buck_idx][rec.camera_id][0] += rec.total_in
            tent_gate_buckets[tid][gk][buck_idx][rec.camera_id][1] += rec.total_out

        time_labels = []
        current_time = start_date_time
        while current_time <= end_date_time:
            time_labels.append(current_time)
            current_time += timedelta(minutes=5)

        tent_staying_map = []
        for tent in tents:
            data = [0]  # baseline (no pre-range data since end_time is always NULL)
            current_staying = 0
            gate_map = tent_gate_buckets[tent.id]  # gate_key → bucket_idx → cam_id → [in, out]

            for i in range(1, len(time_labels)):
                buck_idx = i - 1
                # Sum smart_aggregate across all gates for this bucket
                b_in  = 0
                b_out = 0
                for gate_buckets in gate_map.values():
                    cam_totals = gate_buckets.get(buck_idx, {})
                    in_values  = [v[0] for v in cam_totals.values()]
                    out_values = [v[1] for v in cam_totals.values()]
                    b_in  += smart_aggregate(in_values)  if in_values  else 0
                    b_out += smart_aggregate(out_values) if out_values else 0
                current_staying += (b_in - b_out)
                data.append(max(current_staying, 0))

            tent_staying_map.append({
                "tent_id":       tent.id,
                "tent_name":     tent.name,
                "tent_capacity": tent.capacity,
                "count":         total_counts[tent.id],
                "hours":         time_labels,
                "records":       data,
            })

        return Response({
            "success":         True,
            "message":         "30-minute interval data per tent fetched successfully.",
            "start_date_time": start_date_time,
            "end_date_time":   end_date_time,
            "initial_total_in":  0,
            "initial_total_out": 0,
            "results":         tent_staying_map,
        }, status=status.HTTP_200_OK)


def check_overlapping_intervals_with_ids(history_qs):
    # Extract and sort intervals by start_time
    intervals = [
        {"id": entry.id, "start": entry.start_time,
            "end": entry.end_time, "status": entry.current_status}
        for entry in history_qs
        if entry.start_time and entry.end_time
    ]
    intervals.sort(key=lambda x: x["start"])  # sort by start_time

    overlaps = []

    for i in range(1, len(intervals)):
        prev = intervals[i - 1]
        curr = intervals[i]

        if curr["start"] < prev["end"]:
            # Overlap detected
            overlaps.append({
                "prev_id": prev["id"],
                "prev_start": prev["start"],
                "prev_end": prev["end"],
                "prev_status": prev["status"],
                "curr_id": curr["id"],
                "curr_start": curr["start"],
                "curr_end": curr["end"],
                "curr_status": curr["status"],
                "overlap_duration_min": (prev["end"] - curr["start"]).total_seconds() / 60.0
            })

    return overlaps


class GuardCardViewData(APIView):
    permission_classes = [GuardPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        nationality_param = request.GET.get("nationality", "all")

        start_date_time = get_aware_datetime_from_str(
            request.GET.get('start_date_time')) or None
        end_date_time = get_aware_datetime_from_str(
            request.GET.get('end_date_time')) or None

        if not start_date_time and not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
                tents = tents.filter(nationality__id__in=nationality_ids)
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        if tent_ids:
            try:
                tent_id_list = [int(tid.strip()) for tid in tent_ids.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        guard_cameras_map = {}
        for c in Camera.objects.filter(tent__in=tents, type="guard"):
            guard_cameras_map.setdefault(c.tent_id, c)

        all_cam_ids = [c.id for c in guard_cameras_map.values()]
        all_guard_histories = list(
            GuardPresenceHistory.objects.filter(
                camera_id__in=all_cam_ids,
                start_time__gte=start_date_time,
                end_time__lte=end_date_time,
                is_rejected=False,
            ).order_by('camera_id', 'start_time')
        )
        histories_by_cam = defaultdict(list)
        for h in all_guard_histories:
            histories_by_cam[h.camera_id].append(h)

        result = []

        for tent in tents:
            camera = guard_cameras_map.get(tent.id)
            history_qs = histories_by_cam.get(camera.id, []) if camera else []

            if history_qs:
                last_instance = history_qs[-1]
                last_update = last_instance.end_time or None
                current_status = last_instance.current_status
                if current_status[0] == 'absent':
                    current_guards = 0
                    current_guard_state = False
                else:
                    current_guards = int(current_status[0])
                    current_guard_state = True

            else:
                last_update = None
                current_guards = 0
                current_guard_state = False

            no_show_time = 0  #
            no_show_count = 0  #
            count_duration = 0
            total_duration = 0

            inside_zero_block = False
            last_end_time = None
            not_present_list = []
            cleaned_entries = skip_overlapping_entries(history_qs)
            temp_not_present_list = []
            last_data_insert = False

            for entry in cleaned_entries:
                if entry.start_time and entry.end_time:
                    duration = (entry.end_time -
                                entry.start_time).total_seconds() / 60.0
                    total_duration += duration
                if not entry.present and entry.start_time and entry.end_time:
                    if last_end_time:
                        time_gap = (entry.start_time -
                                    last_end_time).total_seconds()
                        if time_gap > 119:  # if the gap is more than 5 seconds
                            if inside_zero_block:
                                no_show_count += 1
                                no_show_time += int(count_duration)
                                not_present_list.append(temp_not_present_list)
                            temp_not_present_list = []  # reset
                            last_end_time = None  # reset
                            count_duration = 0  # reset
                            inside_zero_block = False
                            count_duration += duration
                        else:
                            temp_not_present_list.append({
                                "start_time": convert_utc_to_riyadh(entry.start_time),
                                "end_time": convert_utc_to_riyadh(entry.end_time),
                                "duration": duration,
                                "id": entry.id
                            })
                            count_duration += (entry.end_time - last_end_time).total_seconds() / 60.0
                    else:
                        temp_not_present_list.append({
                            "start_time": convert_utc_to_riyadh(entry.start_time),
                            "end_time": convert_utc_to_riyadh(entry.end_time),
                            "duration": duration,
                            "id": entry.id
                        })
                        count_duration += duration
                    if count_duration > 5.0:
                        inside_zero_block = True

                    last_end_time = entry.end_time  # update last_end_time

                else:
                    if inside_zero_block:
                        no_show_count += 1
                        no_show_time += int(count_duration)
                        not_present_list.append(temp_not_present_list)
                    temp_not_present_list = []  # reset
                    count_duration = 0
                    last_end_time = None
                    inside_zero_block = False

            if inside_zero_block:
                not_present_list.append(temp_not_present_list)
                last_data_insert = True
                no_show_count += 1
                no_show_time += count_duration
            # total_duration = int(
            #     (end_date_time - start_date_time).total_seconds() / 60)
            available_minutes = max(total_duration - no_show_time, 0)
            available_percentage = round(
                (available_minutes / total_duration) * 100, 2) if total_duration > 0 else 0.0

            tent_data = {
                'tent_id': tent.id,
                'tent_name': tent.name,
                'current_guards': current_guards,
                'current_guard_state': current_guard_state,
                'no_show_time': int(no_show_time),
                'no_show_count': no_show_count,
                'available_percentage': available_percentage,
                'indicator': "red" if available_percentage < 97 else "green",
                'last_update': convert_utc_to_riyadh(last_update) if last_update else last_update,
                "total_duration": total_duration,
                "start_date_time": start_date_time,
                "end_date_time": end_date_time,
                "not_present_list": not_present_list,
                "last_data_insert": last_data_insert,
                # "overlapping": check_overlapping_intervals_with_ids(history_qs),
            }

            result.append(tent_data)

        return Response({
            "success": True,
            "message": "Guard card data fetched successfully.",
            "results": result
        }, status=200)


class CleanerCardViewData(APIView):
    permission_classes = [CleanersPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')
        nationality_param = request.GET.get("nationality", "all")

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
                tents = tents.filter(nationality__id__in=nationality_ids)
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)

        if tent_ids:
            try:
                tent_id_list = [int(tid.strip()) for tid in tent_ids.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        bathroom_cameras_map = {}
        for c in Camera.objects.filter(tent__in=tents, type="bathroom"):
            bathroom_cameras_map.setdefault(c.tent_id, c)

        all_bath_cam_ids = [c.id for c in bathroom_cameras_map.values()]
        all_bath_histories = list(
            BathroomMonitoringHistory.objects.filter(
                camera_id__in=all_bath_cam_ids,
                start_time__gte=start_date_time,
                end_time__lte=end_date_time,
                is_annotated=True,
            ).order_by('camera_id', 'start_time')
        )
        bath_histories_by_cam = defaultdict(list)
        for h in all_bath_histories:
            bath_histories_by_cam[h.camera_id].append(h)

        result = []

        for tent in tents:
            camera = bathroom_cameras_map.get(tent.id)
            history_qs = bath_histories_by_cam.get(camera.id, []) if camera else []

            if history_qs:
                last_instance = history_qs[-1]
                last_update = last_instance.end_time
                current_cleaners = last_instance.cleaner_count or 0

                current_cleaner_state = False if current_cleaners == 0 else True
            else:
                last_update = start_date_time
                current_cleaners = 0
                current_cleaner_state = False

            no_show_time = 0  # in total unavailable minutes
            no_show_count = 0  # total unavailable times over 5 minutes
            count_duration = 0
            last_end_time = None  # track the end time of the previous entry

            for entry in history_qs:
                if entry.cleaner_count == 0 and entry.start_time and entry.end_time:
                    # duration in minutes
                    duration = (entry.end_time -
                                entry.start_time).total_seconds() / 60.0

                    if last_end_time:
                        time_gap = (entry.start_time -
                                    last_end_time).total_seconds()
                        if time_gap > 5:  # if the gap is more than 5 seconds
                            count_duration = 0  # reset

                    count_duration += duration
                    if count_duration > 5.0:
                        no_show_time += int(duration)
                        no_show_count += 1
                        count_duration = 0

                    last_end_time = entry.end_time  # update last_end_time

                else:
                    count_duration = 0
                    last_end_time = None

            total_duration = int(
                (end_date_time - start_date_time).total_seconds() / 60)
            available_minutes = max(total_duration - no_show_time, 0)
            available_percentage = round(
                (available_minutes / total_duration) * 100, 2) if total_duration > 0 else 0.0

            tent_data = {
                'tent_id': tent.id,
                'tent_name': tent.name,
                'current_cleaners': current_cleaners,
                'current_cleaner_state': current_cleaner_state,
                'no_show_time': no_show_time,
                'no_show_count': no_show_count,
                'available_percentage': available_percentage,
                'indicator': "red" if available_percentage < 97 else "green",
                'last_update': convert_utc_to_riyadh(last_update) if last_update else last_update,
            }

            result.append(tent_data)

        return Response({
            "success": True,
            "message": "Cleaner card data fetched successfully.",
            "results": result
        }, status=200)


class GuardGraphViewData(APIView):
    permission_classes = [GuardPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if tent_ids:
            try:
                tent_id_list = [int(tid.strip()) for tid in tent_ids.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        result = []

        for tent in tents:
            cameras = Camera.objects.filter(tent=tents)

            # Raw GuardPresenceHistory data for this tent
            raw_qs = GuardPresenceHistory.objects.filter(
                camera__in=cameras,
                start_time__gte=start_date_time,
                end_time__lte=end_date_time
            ).annotate(hour=ExtractHour('start_time')).order_by('start_time')

            # Prepare 24 buckets (0–23 hours)
            hourly_records = [[] for _ in range(24)]

            for entry in raw_qs:
                entry_data = {
                    "id": entry.id,
                    "camera_id": entry.camera_id,
                    "guard_count": entry.guard_count,
                    "start_time": entry.start_time,
                    "end_time": entry.end_time,
                }
                hour = entry.hour
                if 0 <= hour < 24:
                    hourly_records[hour].append(entry_data["guard_count"])

            tent_data = {
                "tent_id": tent.id,
                "tent_name": tent.name,
                "hours": list(range(24)),
                "records": hourly_records
            }

            result.append(tent_data)

        return Response({
            "success": True,
            "message": "Hourly guard data grouped successfully.",
            "results": result
        }, status=200)


class KitchenViolatioReportDetailsView(APIView):
    permission_classes = [KitchenPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')
        paginate = True if request.GET.get(
            'paginate', "true") == "true" else False
        page = int(request.GET.get('page', 1))
        itemsPerPage = int(request.GET.get('itemsPerPage', 10))

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if tent_ids:
            try:
                tent_id_list = list(map(int, tent_ids.split(',')))
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        result = []
        for tent in tents:
            cameras = Camera.objects.filter(tent=tent, type="kitchen")
            tent_violations = KitchenViolationReport.objects.filter(
                camera__in=cameras,
                created_at__range=(start_date_time, end_date_time),
                is_rejected=False,
                is_annotated=True
            ).order_by('-id')

            violations_records = tent_violations.filter(violation=True)

            last_violation = violations_records.order_by('-created_at').first()
            last_update = last_violation.created_at if last_violation else None

            count = violations_records.count()

            # Collect violation image URLs
            images = [
                {
                    'id': violation.id,
                    "camera_sn": violation.camera.sn,
                    'tent_name': violation.camera.tent.name,
                    'image': request.build_absolute_uri(violation.image.url),
                    'violation': violation.violation,
                    'violation_list': violation.violation_list,
                    'current_status': violation.current_status,
                    'created_at': convert_utc_to_riyadh(violation.created_at) if violation.created_at else None
                }
                for violation in violations_records
                if violation.image
            ]
            if paginate:
                paginated_images, total_images = custom_array_pagination(
                    images, page, itemsPerPage)
            else:
                total_images = len(images)
                paginated_images = images

            result.append({
                "tent_id": tent.id,
                'tent': tent.name,
                "violation_count": count,
                'count': total_images,
                'images': paginated_images,  # List of violation image URLs
                'last_updated': convert_utc_to_riyadh(last_update) if last_update else None
            })
        data = {
            'success': True,
            'message': "Kitchen Violation Report Data Retrieved Successfully",
            'results': result[0] if tent_ids and len(tent_id_list) == 1 and result else result,
        }
        return Response(data, status=status.HTTP_200_OK)


class GarbageViolatioReportDetailsView(APIView):
    permission_classes = [CleannessPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')
        paginate = True if request.GET.get(
            'paginate', "true") == "true" else False
        page = int(request.GET.get('page', 1))
        itemsPerPage = int(request.GET.get('itemsPerPage', 10))

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if tent_ids:
            try:
                tent_id_list = list(map(int, tent_ids.split(',')))
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        result = []
        for tent in tents:
            cameras = Camera.objects.filter(tent=tent, type="garbage")
            tent_violations = GarbageMonitoringReport.objects.filter(
                is_annotated=True,
                camera__in=cameras,
                created_at__range=(start_date_time, end_date_time),
                is_rejected=False
            ).order_by('-id')

            violations_records = tent_violations.filter(is_clean=False)

            count = violations_records.count()
            last_violation = violations_records.order_by('-created_at').first()
            last_update = last_violation.created_at if last_violation else None
            # Collect violation image URLs
            images = [
                {
                    'id': violation.id,
                    "camera_sn": violation.camera.sn,
                    'tent_name': violation.camera.tent.name,
                    'image': request.build_absolute_uri(violation.image.url),
                    'violation': violation.is_clean,
                    'current_status': violation.current_status,
                    'created_at': convert_utc_to_riyadh(violation.created_at)
                }
                for violation in violations_records
                if violation.image
            ]
            if paginate:
                paginated_images, total_images = custom_array_pagination(
                    images, page, itemsPerPage)
            else:
                total_images = len(images)
                paginated_images = images
            result.append({
                "tent_id": tent.id,
                'tent': tent.name,
                'violation_count': total_images,
                'images': paginated_images,  # List of violation image URLs
                "last_updated": convert_utc_to_riyadh(last_update) if last_update else None
            })
        data = {
            'success': True,
            'message': "Garbage Violation Report Data Retrieved Successfully",
            'results': result[0] if tent_ids and len(tent_id_list) == 1 and result else result,
        }
        return Response(data, status=status.HTTP_200_OK)


class RecycleIndicatorHistoryReportView(APIView):
    permission_classes = [RecyclePermission]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        response_type = request.GET.get('type', 'json')
        is_clean = request.GET.get('violation', None)
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'

        if tent_id_list:
            try:
                tent_ids = list(map(int, tent_id_list.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = Tent.objects.filter(
                    company=request.user.company).order_by('id')
            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                tents = Tent.objects.filter(
                    id__in=assigned_tent_ids, company=request.user.company).order_by('id')
            if not tents.exists():
                return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        if not tents.exists():
            return Response({"detail": "No tents found."}, status=404)

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                return Response({"error": "Start and end dates are required."}, status=400)

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.min.time())) + timedelta(days=1)
        except Exception as e:
            return Response({"error": f"Invalid dates: {str(e)}"}, status=400)

        queryset = RecycleMonitoringReport.objects.filter(
            camera__tent__in=tents,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            is_rejected=False,
            is_annotated=True
        ).order_by('-created_at')

        if is_clean is not None:
            is_clean_bool = is_clean.lower() == 'true'
            queryset = queryset.filter(current_status=is_clean_bool)

        queryset = queryset.order_by('-created_at').values(
            'camera__tent__name',
            'created_at',
            'camera__sn',
            'is_clean',
            'image',
        )

        data = []
        for record in queryset:
            image_url = f"{settings.MEDIA_URL}{record['image']}" if record['image'] else None
            image_full_url = f"{settings.BASE_URL}{image_url}" if image_url and settings.DEBUG else image_url

            data.append({
                'tent_name': record['camera__tent__name'],
                'created_at': record['created_at'],
                'camera_sn': record['camera__sn'],
                'is_clean': record['is_clean'],
                'image': image_full_url,
            })

        if response_type == "csv":
            return generate_csv_response(data, 'recycle_report_data.csv')

        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Recycle Indicator Data Retrieved",
            'results': data,
        }, status=status.HTTP_200_OK)


class RecycleMonitoringReportChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        queryset = RecycleMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).select_related('camera__tent')

        total = queryset.count()
        recycle = queryset.filter(is_clean=False).count()
        clean = queryset.filter(is_clean=True).count()
        rejected = queryset.filter(is_rejected=True).count()

        hourly_qs = (
            queryset
            .values('start_time__hour', 'is_clean')
            .annotate(count=Count('id'))
            .order_by('start_time__hour')
        )

        hourly_map = {}
        for row in hourly_qs:
            hour = str(row['start_time__hour']).zfill(2)
            if hour not in hourly_map:
                hourly_map[hour] = {'hour': hour, 'recycle': 0, 'clean': 0}
            key = 'clean' if row['is_clean'] else 'recycle'
            hourly_map[hour][key] = row['count']

        hourly = sorted(hourly_map.values(), key=lambda x: x['hour'])

        return Response({
            'stats': {
                'total': total,
                'recycle': recycle,
                'clean': clean,
                'rejected': rejected,
            },
            'hourly': hourly,
        }, status=status.HTTP_200_OK)


class RecycleMonitoringReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, format=None):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')
        filter_param = request.query_params.get('filter_param')
        hour = request.query_params.get('hour')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)

        queryset = RecycleMonitoringReport.objects.filter(
            Q(camera__tent__in=tents) &
            Q(start_time__gte=start_datetime) &
            Q(start_time__lte=end_datetime) &
            Q(is_annotated=True)
        ).order_by('-start_time').select_related('camera__tent')

        if filter_param == 'recycle':
            queryset = queryset.filter(is_clean=False)
        elif filter_param == 'clean':
            queryset = queryset.filter(is_clean=True)
        elif filter_param == 'rejected':
            queryset = queryset.filter(is_rejected=True)

        if hour is not None:
            queryset = queryset.filter(start_time__hour=int(hour))

        serializer = RecycleMonitoringReportSerializer(
            queryset, many=True, context={'request': request}
        )

        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                serializer.data, request, view=self
            )
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Recycle Monitoring History Data Retrieved Successfully",
            'count': queryset.count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)


class TentRecycleSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        response_type = request.query_params.get('type', 'json')

        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        end = end + timedelta(days=1)

        date_filter = Q(camera__recycle_monitoring_histories__start_time__gte=start,
                        camera__recycle_monitoring_histories__start_time__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)

        recycle_camera_exists = Camera.objects.filter(
            tent=OuterRef('pk'),
            type='recycle'
        )

        tents = tents.annotate(
            recycle_camera_exists=Exists(recycle_camera_exists)
        ).filter(recycle_camera_exists=True)

        tents = tents.annotate(
            violation_count=Count(
                'camera__recycle_monitoring_histories',
                filter=Q(
                    camera__recycle_monitoring_histories__is_clean=False,
                    camera__recycle_monitoring_histories__is_annotated=True) & date_filter
            )
        ).order_by('violation_count')

        tents = list(tents)
        tents = sorted(
            tents,
            key=lambda x: (x.violation_count, tent_name_list_dict_sorting(x.name))
        )

        tent_data = []
        for index, tent in enumerate(tents, start=1):
            tent_data.append({
                "tent_id": tent.id,
                'tent_name': tent.name,
                'violation_count': tent.violation_count,
                "rank": index
            })

        if response_type == 'csv':
            return generate_csv_response(tent_data, 'recycle_violation_ranking_data.csv')

        return Response({
            "success": True,
            "message": "Tent-wise Recycle summary retrieved successfully.",
            "data": tent_data
        }, status=status.HTTP_200_OK)


class CameraRecycleSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        start = parse_datetime(start_date) if start_date else None
        end = parse_datetime(end_date) if end_date else None

        if not start or not end:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        if is_naive(start):
            start = make_aware(start)
        if is_naive(end):
            end = make_aware(end)

        end = end + timedelta(days=1)

        date_filter = Q(recycle_monitoring_histories__start_time__gte=start,
                        recycle_monitoring_histories__start_time__lt=end)

        company = request.user.company
        if request.user.is_admin:
            tents = Tent.objects.filter(company=company)
        else:
            tents = request.user.assigned_tent.filter(company=company)

        cameras = Camera.objects.filter(tent__in=tents, type='recycle').annotate(
            violation_count=Count(
                'recycle_monitoring_histories',
                filter=Q(
                    recycle_monitoring_histories__is_clean=False,
                    recycle_monitoring_histories__is_annotated=True) & date_filter
            )
        ).select_related('tent').order_by('violation_count')

        camera_data = []
        rank = 1
        previous_violation = None
        for cam in cameras:
            current_violation = cam.violation_count
            if previous_violation is None:
                previous_violation = current_violation
            elif current_violation != previous_violation:
                rank += 1
                previous_violation = current_violation
            camera_data.append({
                'id': cam.id,
                'camera': cam.sn,
                'tent_name': cam.tent.name if cam.tent else None,
                "tent_id": cam.tent.id if cam.tent else None,
                'violation_count': current_violation,
                'rank': rank
            })

        return Response({
            "success": True,
            "message": "Camera-wise Recycle summary retrieved successfully.",
            "data": camera_data
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class CreateRecycleMonitoringHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    AVAILABLE_CLASSES = ['plastic', 'paper', 'metal', 'glass', 'other', 'clean']

    def get(self, request, pk=None):
        if pk is not None:
            recycle_monitoring = RecycleMonitoringReport.objects.get(pk=pk)
            serializer = RecycleMonitoringReportSerializer(recycle_monitoring)
            return Response({
                "success": True,
                "message": "Recycle Monitoring Report retrieved successfully.",
                "available_classes": self.AVAILABLE_CLASSES,
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        recycle_monitorings = RecycleMonitoringReport.objects.filter(
            is_annotated=False, is_ai_annotated=False)
        serializer = RecycleMonitoringReportSerializer(
            recycle_monitorings, many=True)
        return Response({
            "success": True,
            "message": "Recycle Monitoring Reports retrieved successfully.",
            "available_classes": self.AVAILABLE_CLASSES,
            "summary": {
                "total_pending": recycle_monitorings.count(),
                "recycle_detected": recycle_monitorings.filter(is_clean=False).count(),
                "clean_detected": recycle_monitorings.filter(is_clean=True).count(),
            },
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        recycle_monitoring = RecycleMonitoringReport.objects.get(pk=pk)
        serializer = RecycleMonitoringReportSerializer(
            recycle_monitoring, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Recycle Monitoring Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "message": "Error updating Recycle Monitoring Report.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_recycle_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()
        data['camera'] = camera.pk

        serializer = RecycleMonitoringReportSerializer(
            data=data, context={'request': request})

        if serializer.is_valid():
            recycle_monitoring = serializer.save(camera=camera)
            return Response(
                {
                    "message": "Recycle Monitoring History created successfully.",
                    "data": RecycleMonitoringReportSerializer(recycle_monitoring).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": "Invalid data", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RecycleMonitoringHistoryReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        response_type = request.GET.get('type', 'json')
        is_clean = request.GET.get('is_clean', None)
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'

        if tent_id_list:
            try:
                tent_ids = list(map(int, tent_id_list.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = Tent.objects.filter(
                    company=request.user.company).order_by('id')
            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                tents = Tent.objects.filter(
                    id__in=assigned_tent_ids, company=request.user.company).order_by('id')
            if not tents.exists():
                return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        if not tents.exists():
            return Response({"detail": "No tents found."}, status=404)

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                return Response({"error": "Start and end dates are required."}, status=400)

            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.min.time())) + timedelta(days=1)
        except Exception as e:
            return Response({"error": f"Invalid dates: {str(e)}"}, status=400)

        queryset = RecycleMonitoringReport.objects.filter(
            camera__tent__in=tents,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            is_annotated=False
        )

        if is_clean is not None:
            is_clean_bool = is_clean.lower() == 'true'
            queryset = queryset.filter(is_clean=is_clean_bool)

        queryset = queryset.order_by('-created_at').values(
            'camera__tent__name',
            'created_at',
            'camera__sn',
            'is_clean',
            'image',
        )

        data = []
        for record in queryset:
            image_url = f"{settings.MEDIA_URL}{record['image']}" if record['image'] else None
            image_full_url = f"{settings.BASE_URL}{image_url}" if image_url and settings.DEBUG else image_url

            data.append({
                'tent_name': record['camera__tent__name'],
                'created_at': record['created_at'].strftime('%Y-%m-%d %H:%M'),
                'camera_sn': record['camera__sn'],
                'is_clean': record['is_clean'],
                'image': image_full_url,
            })

        if response_type == "csv":
            return generate_csv_response(data, 'recycle_report_data.csv')

        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Recycle Monitoring Data Retrieved",
            'results': data,
        }, status=status.HTTP_200_OK)


class RecycleViolatioReportDetailsView(APIView):
    permission_classes = [RecyclePermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')
        paginate = True if request.GET.get(
            'paginate', "true") == "true" else False
        page = int(request.GET.get('page', 1))
        itemsPerPage = int(request.GET.get('itemsPerPage', 10))

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if tent_ids:
            try:
                tent_id_list = list(map(int, tent_ids.split(',')))
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        result = []
        for tent in tents:
            cameras = Camera.objects.filter(tent=tent, type="recycle")
            tent_violations = RecycleMonitoringReport.objects.filter(
                is_annotated=True,
                camera__in=cameras,
                created_at__range=(start_date_time, end_date_time),
                is_rejected=False
            ).order_by('-id')

            violations_records = tent_violations.filter(is_clean=False)

            last_violation = violations_records.order_by('-created_at').first()
            last_update = last_violation.created_at if last_violation else None
            images = [
                {
                    'id': violation.id,
                    "camera_sn": violation.camera.sn,
                    'tent_name': violation.camera.tent.name,
                    'image': request.build_absolute_uri(violation.image.url),
                    'violation': violation.is_clean,
                    'current_status': violation.current_status,
                    'created_at': convert_utc_to_riyadh(violation.created_at)
                }
                for violation in violations_records
                if violation.image
            ]
            if paginate:
                paginated_images, total_images = custom_array_pagination(
                    images, page, itemsPerPage)
            else:
                total_images = len(images)
                paginated_images = images
            result.append({
                "tent_id": tent.id,
                'tent': tent.name,
                'violation_count': total_images,
                'images': paginated_images,
                "last_updated": convert_utc_to_riyadh(last_update) if last_update else None
            })
        data = {
            'success': True,
            'message': "Recycle Violation Report Data Retrieved Successfully",
            'results': result[0] if tent_ids and len(tent_id_list) == 1 and result else result,
        }
        return Response(data, status=status.HTTP_200_OK)


class BuffetViolatioReportDetailsView(APIView):
    permission_classes = [BuffetPermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')
        paginate = True if request.GET.get(
            'paginate', "true") == "true" else False
        page = int(request.GET.get('page', 1))
        itemsPerPage = int(request.GET.get('itemsPerPage', 10))

        start_date_time = parse_datetime(start_date_time_str) if isinstance(
            start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(
            end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if tent_ids:
            try:
                tent_id_list = list(map(int, tent_ids.split(',')))
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        result = []
        for tent in tents:
            cameras = Camera.objects.filter(tent=tent, type="buffet")
            tent_violations = BuffetViolationReport.objects.filter(
                is_annotated=True,
                camera__in=cameras,
                created_at__range=(start_date_time, end_date_time),
                is_rejected=False
            ).order_by('-id')

            violations_records = tent_violations.filter(violation=True)

            last_violation = violations_records.order_by('-created_at').first()
            last_update = last_violation.created_at if last_violation else None

            # Collect violation image URLs
            images = [
                {
                    'id': violation.id,
                    "camera_sn": violation.camera.sn,
                    'tent_name': violation.camera.tent.name,
                    'image': request.build_absolute_uri(violation.image.url),
                    'violation': violation.violation,
                    'violation_list': violation.violation_list,
                    "current_status": violation.current_status,
                    'created_at': convert_utc_to_riyadh(violation.created_at) if violation.created_at else None
                }
                for violation in violations_records
                if violation.image
            ]
            if paginate:
                paginated_images, total_images = custom_array_pagination(
                    images, page, itemsPerPage)
            else:
                total_images = len(images)
                paginated_images = images

            result.append({
                "tent_id": tent.id,
                'tent': tent.name,
                'violation_count': total_images,
                'images': paginated_images,  # List of violation image URLs
                "last_updated": convert_utc_to_riyadh(last_update) if last_update else None
            })
        data = {
            'success': True,
            'message': "Buffet Violation Report Data Retrieved Successfully",
            'results': result[0] if tent_ids and len(tent_id_list) == 1 and result else result,
        }
        return Response(data, status=status.HTTP_200_OK)


class CameraWithCameraHeartbeat(APIView):
    def get(self, request):
        secret_key = request.headers.get('X-Secret-Key-camera')
        match_camera_key(secret_key)
        cameras = Camera.objects.all().select_related('tent')
        serializer = CameraSerializer(cameras, many=True)
        return Response({
            "success": True,
            "message": "Cameras retrieved successfully.",
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class BuffetAiAnnotationAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, id=None):
        if id:
            try:
                instance = BuffetViolationReport.objects.get(id=id)
                serializer = BuffetAiAnnotationSerializer(instance)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except BuffetViolationReport.DoesNotExist:
                return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            sort = request.GET.get('sort', None)
            total = int(request.GET.get('per_page', 100))

            queryset = BuffetViolationReport.objects.filter(
                is_annotated=False, is_ai_annotated=False)
            if sort == "new":
                queryset = queryset.order_by('id')
            else:
                queryset = queryset.order_by('-id')

            queryset = queryset[:total]
            serializer = BuffetAiAnnotationSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id=None):
        data = request.data

        if id:
            # Update existing
            try:
                instance = BuffetViolationReport.objects.get(id=id)
            except BuffetViolationReport.DoesNotExist:
                return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = BuffetAiAnnotationSerializer(
                instance, data=data, partial=True)
        else:
            # Create new
            serializer = BuffetAiAnnotationSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GalleryByCameraViewForData(APIView):
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        camera_id = kwargs.pop("camera_id", None)

        def parse_id_list(param: str) -> list[int]:
            return [int(i) for i in param.split(',') if i.strip().isdigit()]

        # Date range and time parsing
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        camera_ids_qr = request.GET.get('camera_ids', '')
        company_ids_qr = request.GET.get('company_ids', '')
        tent_ids_qr = request.GET.get('tent_ids', '')
        type_list_qr = request.GET.get('types', '')
        annotator_param = request.GET.get('is_annotator', 'false').lower()
        annotator = annotator_param in ['true', '1', 'yes']

        # Fix empty camera_ids handling
        camera_ids = parse_id_list(camera_ids_qr)
        tent_ids = parse_id_list(tent_ids_qr)
        company_ids = parse_id_list(company_ids_qr)
        type_list = [t.strip() for t in type_list_qr.split(',') if t.strip()]

        if not start_date_time_str or not end_date_time_str:
            return Response({"detail": "Start and end date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse and validate dates and times
        start_date_time = parse_datetime(start_date_time_str)
        end_date_time = parse_datetime(end_date_time_str)

        filter_param = request.GET.get('filter_param', None)

        if not (start_date_time and end_date_time):
            return Response({"detail": "Invalid date or time format."}, status=status.HTTP_400_BAD_REQUEST)

        # Make the datetime objects timezone-aware
        start_date_time = timezone.make_aware(
            start_date_time, timezone.get_current_timezone())
        end_date_time = timezone.make_aware(
            end_date_time, timezone.get_current_timezone())

        # Fix camera filter logic
        cameras = Camera.objects.none()

        try:
            base_camera_query = Q()

            # Priority 1: Specific camera ID
            if camera_id:
                base_camera_query &= Q(id=camera_id)

            # Priority 2: List of camera IDs
            elif camera_ids:
                base_camera_query &= Q(id__in=camera_ids)

            # Priority 3: Filter based on company, tent, and type if camera IDs are not provided
            else:
                if tent_ids:
                    base_camera_query &= Q(tent__id__in=tent_ids)
                elif company_ids:
                    base_camera_query &= Q(tent__company__id__in=company_ids)
                if type_list:
                    base_camera_query &= Q(type__in=type_list)
            # if user.is_annotator:
            #     pass
            # elif user.is_admin:
            #     base_camera_query &= Q(tent__company=user.company)
            # elif user.is_staff:
            #     base_camera_query &= Q(tent__in=user.assigned_tent.all())

            cameras = Camera.objects.filter(base_camera_query)
        except Camera.DoesNotExist:
            return Response({"detail": "Camera not found."}, status=status.HTTP_404_NOT_FOUND)

        base_filter = Q(
            camera__id__in=cameras,
            image__isnull=False,
            created_at__range=(start_date_time, end_date_time),
        )

        if annotator:
            base_filter &= Q(is_annotated=False)

        # Split the filter into a list of values
        filter_values = filter_param.split(',') if filter_param else []

        if filter_values:
            status_filter = reduce(
                operator.or_, (Q(current_status__contains=value) for value in filter_values))
            base_filter &= status_filter
            # base_filter &= Q(current_status__contains=filter_values)

        # Type wise
        kitchen_data = KitchenViolationReport.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')
        guard_data = GuardPresenceHistory.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')
        garbage_data = GarbageMonitoringReport.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')
        recycle_data = RecycleMonitoringReport.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')
        buffet_data = BuffetViolationReport.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')
        bathroom_data = BathroomMonitoringHistory.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')
        counter_data = CounterHistory.objects.filter(
            base_filter).exclude(image='').order_by('-created_at')

        all_data = list(chain(kitchen_data, guard_data, garbage_data, recycle_data,
                        buffet_data, bathroom_data, counter_data))
        # all_data_sorted = sorted(
        #     all_data, key=attrgetter('created_at'), reverse=True)

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(
            all_data, request, view=self)

        serialized_data = []
        for obj in paginated_data:
            if isinstance(obj, KitchenViolationReport):
                serialized_data.append(
                    KitchenViolationReportSerializer(obj).data)
            elif isinstance(obj, GuardPresenceHistory):
                serialized_data.append(
                    GuardPresenceHistorySerializer(obj).data)
            elif isinstance(obj, GarbageMonitoringReport):
                serialized_data.append(
                    GarbageMonitoringReportSerializer(obj).data)
            elif isinstance(obj, RecycleMonitoringReport):
                serialized_data.append(
                    RecycleMonitoringReportSerializer(obj).data)
            elif isinstance(obj, BuffetViolationReport):
                serialized_data.append(
                    BuffetViolationReportSerializer(obj).data)
            elif isinstance(obj, BathroomMonitoringHistory):
                serialized_data.append(
                    BathroomMonitoringHistorySerializer(obj).data)
            elif isinstance(obj, CounterHistory):
                serialized_data.append(CounterHistorySerializer(obj).data)

        return paginator.get_paginated_response({
            "results": serialized_data
        })


class AnnotatorRankingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
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

        # If both dates exist and fall on the same calendar day
        if start_date and end_date and start_date.date() == end_date.date():
            start_date = start_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(
                hour=23, minute=59, second=59, microsecond=999999)

        if start_date:
            base_query &= Q(updated_at__gte=start_date)
        if end_date:
            base_query &= Q(updated_at__lte=end_date)

        # Convert to Riyadh timezone
        start_date_riyadh = start_date.astimezone(
            riyadh_tz) if start_date else None
        end_date_riyadh = end_date.astimezone(riyadh_tz) if end_date else None

        annotator_ids = list(all_annotators.values_list('id', flat=True))
        report_models = [
            KitchenViolationReport, GuardPresenceHistory,
            BathroomMonitoringHistory, GarbageMonitoringReport,
            BuffetViolationReport, SentimentAnalysis,
        ]
        counts_by_user = defaultdict(int)
        for model in report_models:
            qs = (
                model.objects.filter(base_query, annotator_id__in=annotator_ids)
                .values('annotator_id')
                .annotate(cnt=Count('id'))
            )
            for row in qs:
                counts_by_user[row['annotator_id']] += row['cnt']

        results = []
        overall_total = 0
        annotator_map = {u.id: u for u in all_annotators}

        for uid, user in annotator_map.items():
            total_annotation = counts_by_user.get(uid, 0)
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
                fieldnames=["email", "username",
                            "total_annotation", "start_date", "end_date"]
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


class GuardPresenceHistoryReportNoShowPeriodView(APIView):
    permission_classes = [GuardPermission]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        # Get query parameters
        response_type = request.query_params.get('type', 'json')
        tent_ids_text = request.query_params.get('tent_ids')
        is_present_str = request.query_params.get('violation')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']
        tents = Tent.objects.none()
        is_present = True

        # Apply is_present filter if provided
        if is_present_str is not None:
            is_present = is_present_str.lower() in ['true', '1', 'yes']

        # Validate and parse dates
        try:
            start_date_time = get_aware_datetime_from_str(
                request.query_params.get('start_date')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.query_params.get('end_date')) or timezone.now()
            if not start_date_time or not end_date_time:
                start_date_time, end_date_time = Current_saudi_time()

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by tents
        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            elif user.is_staff:
                tents = Tent.objects.filter(assigned_tent=user)
        compressed_data = []
        for tent in tents:
            query = Q(camera__tent=tent,
                      start_time__gte=start_date_time,
                      end_time__lte=end_date_time,
                      is_rejected=False,
                      is_annotated=True)

            # if not is_present:
            #     query &= Q(present=False)

            guard_data = GuardPresenceHistory.objects.filter(
                query).order_by('start_time')
            camera = Camera.objects.filter(tent=tent, type="guard").first()

            previous_guard_count = None
            segment_start_time = None
            segment_end_time = None
            segment_images = []
            clean_data = skip_overlapping_entries(guard_data)

            for entry in clean_data:

                current_status = entry.current_status
                guard_count = 0 if current_status[0] == 'absent' else int(
                    current_status[0])

                if segment_end_time is not None and entry.start_time > segment_end_time:
                    gap = (entry.start_time - segment_end_time).total_seconds()
                    if gap > 119:
                        if segment_start_time is not None:
                            compressed_data.append({
                                "start_time": convert_utc_to_riyadh(segment_start_time),
                                "end_time": convert_utc_to_riyadh(segment_end_time),
                                "duration": calculate_duration_minutes(segment_start_time, segment_end_time),
                                "guard_count": previous_guard_count,
                                "time": convert_utc_to_riyadh(segment_end_time),
                                "tent": tent.name,
                                "camera": camera.sn,
                                "images": sorted(segment_images, key=lambda x: x['start_time'])
                            })
                            segment_images = []
                        compressed_data.append({
                            "start_time": convert_utc_to_riyadh(segment_end_time),
                            "end_time": convert_utc_to_riyadh(entry.start_time),
                            "duration": calculate_duration_minutes(segment_end_time, entry.start_time),
                            "guard_count": None,
                            "time": convert_utc_to_riyadh(segment_end_time),
                            "tent": tent.name,
                            "camera": camera.sn,
                            "images": None
                        })
                        segment_images = []

                        segment_end_time = None
                        previous_guard_count = None
                        segment_start_time = None
                if previous_guard_count is None:
                    previous_guard_count = guard_count
                    segment_start_time = entry.start_time
                    segment_end_time = entry.end_time
                elif guard_count != previous_guard_count and previous_guard_count > 0:
                    compressed_data.append({
                        "start_time": convert_utc_to_riyadh(segment_start_time),
                        "end_time": convert_utc_to_riyadh(entry.start_time),
                        "duration": calculate_duration_minutes(segment_start_time, entry.start_time),
                        "guard_count": previous_guard_count,
                        "time": convert_utc_to_riyadh(segment_start_time),
                        "tent": tent.name,
                        "camera": camera.sn,
                        "images": sorted(segment_images, key=lambda x: x['start_time'])
                    })
                    segment_images = []
                    segment_start_time = entry.start_time
                    previous_guard_count = guard_count
                elif guard_count != previous_guard_count and previous_guard_count == 0:
                    compressed_data.append({
                        "start_time": convert_utc_to_riyadh(segment_start_time),
                        "end_time": convert_utc_to_riyadh(segment_end_time),
                        "duration": calculate_duration_minutes(segment_start_time, segment_end_time),
                        "guard_count": previous_guard_count,
                        "time": convert_utc_to_riyadh(segment_start_time),
                        "tent": tent.name,
                        "camera": camera.sn,
                        "images": sorted(segment_images, key=lambda x: x['start_time'])
                    })
                    segment_images = []
                    segment_start_time = segment_end_time
                    previous_guard_count = guard_count
                segment_end_time = entry.end_time
                if entry.image:
                    segment_images.append(
                        {
                            'id': entry.id,
                            'image_url': request.build_absolute_uri(entry.image.url),
                            'start_time': convert_utc_to_riyadh(entry.start_time),
                            'end_time': convert_utc_to_riyadh(entry.end_time),
                            'current_status': entry.current_status,
                            'time': convert_utc_to_riyadh(entry.start_time),

                        })

            if segment_start_time is not None and segment_end_time is not None:
                compressed_data.append({
                    "start_time": convert_utc_to_riyadh(segment_start_time),
                    "end_time": convert_utc_to_riyadh(segment_end_time),
                    "duration": calculate_duration_minutes(segment_start_time, segment_end_time),
                    "guard_count": previous_guard_count,
                    "time": convert_utc_to_riyadh(segment_end_time),
                    "tent": tent.name,
                    "camera": camera.sn,
                    "images": sorted(segment_images, key=lambda x: x['start_time'])
                })

        if not is_present:
            compressed_data = [result for result in compressed_data if result['guard_count']
                               is not None and result['guard_count'] == 0 and result['duration'] > 0]
        compressed_data.sort(key=lambda x: x['duration'], reverse=True)
        # Return CSV if requested
        if response_type == "csv":
            return generate_csv_response(compressed_data, 'guard_presence_history.csv')

        # Apply pagination if needed
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                compressed_data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Guard Presence History Data Retrieved Successfully",
            'results': compressed_data,
        }, status=status.HTTP_200_OK)


MODEL_NAME_MAP = {
    'guard': GuardPresenceHistory,
    'kitchen': KitchenViolationReport,
    'employeeactivity': AGGFViolationReport,
    'smoking': SmokingViolationReport,
    'facedetection': FaceDetectionReport,
    'garbage': GarbageMonitoringReport,
    'recycle': RecycleMonitoringReport,
    'falldetection': FallDetectionMonitoringReport,
    'violencedetection': ViolenceMonitoringReport,
    'crowdmonitoring': CrowdMonitoringReport,
    'climbmonitoring': WallClimbMonitoringReport,
    'abnormalactivity': AbnormalActivities,
    'buffet': BuffetViolationReport,
    'bathroom': BathroomMonitoringHistory,
    'sentiment': SentimentAnalysis,
    'cleaners': CleanersPresenceHistory,
}


class RejectImageView(APIView):
    permission_classes = [CanDeleteImagePermission]

    def patch(self, request):
        model_name = request.data.get('model_name')
        image_id   = request.data.get('image_id')
        action     = request.data.get('action', 'reject')

        if not model_name or not image_id:
            return Response({
                'success': False,
                'message': 'model_name and image_id are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if action not in ('reject', 'annotate'):
            return Response({
                'success': False,
                'message': 'action must be "reject" or "annotate".'
            }, status=status.HTTP_400_BAD_REQUEST)

        model_class = MODEL_NAME_MAP.get(model_name)
        if model_class is None:
            return Response({
                'success': False,
                'message': f'Unknown model_name "{model_name}". Valid options: {list(MODEL_NAME_MAP.keys())}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = model_class.objects.get(id=image_id)
        except model_class.DoesNotExist:
            return Response({
                'success': False,
                'message': f'No record found with id {image_id} in {model_name}.'
            }, status=status.HTTP_404_NOT_FOUND)

        if action == 'reject':
            instance.is_annotated = False
            instance.is_rejected  = True
            instance.save()
            message = f'Record {image_id} in {model_name} marked as rejected.'

        else:  # annotate
            annotator_status = request.data.get('annotator_status')
            if not annotator_status:
                return Response({
                    'success': False,
                    'message': 'annotator_status is required when action is "annotate".'
                }, status=status.HTTP_400_BAD_REQUEST)

            instance.annotator_status = annotator_status
            instance.is_annotated     = True
            instance.annotator        = request.user
            instance.save()  # triggers model save() → updates current_status, is_clean, etc.
            message = f'Record {image_id} in {model_name} annotated as "{annotator_status}".'

        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)


class CreateNewCleanersPresenceHistory(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_cleaners_detection_key(header_key)

        data = request.data
        camera_sn = data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        person_class = data.get('person_class')
        valid_classes = [c[0] for c in CleanersPresenceHistory.PERSON_CLASS_CHOICES]
        if not person_class or person_class not in valid_classes:
            return Response(
                {"message": f"person_class is required and must be one of: {', '.join(valid_classes)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            image_file = request.FILES.get('image')
            record = CleanersPresenceHistory.objects.create(
                camera=camera,
                person_class=person_class,
                cleaner_count=int(data.get('cleaner_count', 0)),
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
            )
            if image_file:
                record.image = image_file
                record.save()

            return Response(
                {"message": "Cleaners Presence History created successfully."},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"message": f"Error creating Cleaners Presence History: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NewCleanerCardViewData(APIView):
    permission_classes = [CleanersPresencePermission]

    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')
        nationality_param = request.GET.get("nationality", "all")

        start_date_time = parse_datetime(start_date_time_str) if isinstance(start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        tents = Tent.objects.filter(company=user.company)
        if not user.is_admin:
            assigned_ids = user.assigned_tent.values_list('id', flat=True)
            tents = tents.filter(id__in=assigned_ids)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(',') if x.strip().isdigit()]
                tents = tents.filter(nationality__id__in=nationality_ids)
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)

        if tent_ids:
            try:
                tent_id_list = [int(tid.strip()) for tid in tent_ids.split(',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_id_list)
            except ValueError:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)

        result = []

        for tent in tents:
            camera = Camera.objects.filter(tent=tent, type="cleaners").first()
            history_qs = CleanersPresenceHistory.objects.filter(
                camera=camera,
                start_time__gte=start_date_time,
                end_time__lte=end_date_time,
            ).order_by('start_time')

            if history_qs.exists():
                last_instance = history_qs.last()
                last_update = last_instance.end_time
                current_cleaners = last_instance.cleaner_count or 0
                current_person_class = last_instance.person_class
                current_cleaner_state = current_cleaners > 0
            else:
                last_update = start_date_time
                current_cleaners = 0
                current_person_class = None
                current_cleaner_state = False

            no_show_time = 0
            no_show_count = 0
            count_duration = 0
            last_end_time = None

            for entry in history_qs:
                if entry.cleaner_count == 0 and entry.start_time and entry.end_time:
                    duration = (entry.end_time - entry.start_time).total_seconds() / 60.0
                    if last_end_time:
                        time_gap = (entry.start_time - last_end_time).total_seconds()
                        if time_gap > 5:
                            count_duration = 0
                    count_duration += duration
                    if count_duration > 5.0:
                        no_show_time += int(duration)
                        no_show_count += 1
                        count_duration = 0
                    last_end_time = entry.end_time
                else:
                    count_duration = 0
                    last_end_time = None

            total_duration = int((end_date_time - start_date_time).total_seconds() / 60)
            available_minutes = max(total_duration - no_show_time, 0)
            available_percentage = round((available_minutes / total_duration) * 100, 2) if total_duration > 0 else 0.0

            result.append({
                'tent_id': tent.id,
                'tent_name': tent.name,
                'current_cleaners': current_cleaners,
                'current_person_class': current_person_class,
                'current_cleaner_state': current_cleaner_state,
                'no_show_time': no_show_time,
                'no_show_count': no_show_count,
                'available_percentage': available_percentage,
                'indicator': "red" if available_percentage < 97 else "green",
                'last_update': convert_utc_to_riyadh(last_update) if last_update else last_update,
            })

        return Response({
            "success": True,
            "message": "Cleaner card data fetched successfully.",
            "results": result
        }, status=200)


class NewCleanerChartView(APIView):
    permission_classes = [CleanersPresencePermission]

    def get(self, request, *args, **kwargs):
        tent_id = request.query_params.get('tent_id')
        start_date_time_str = request.GET.get('start_date_time')
        end_date_time_str = request.GET.get('end_date_time')

        start_date_time = parse_datetime(start_date_time_str) if isinstance(start_date_time_str, str) else None
        end_date_time = parse_datetime(end_date_time_str) if isinstance(end_date_time_str, str) else None

        if not start_date_time or not end_date_time:
            start_date_time, end_date_time = Current_saudi_time()

        if not tent_id:
            return Response({"error": "tent_id is required."}, status=400)

        try:
            tent = Tent.objects.filter(id=int(tent_id)).first()
        except ValueError:
            return Response({"error": "Invalid tent_id format. Must be an integer."}, status=400)

        if not tent:
            return Response({"error": "Tent not found."}, status=404)

        camera = Camera.objects.filter(tent=tent, type="cleaners").first()
        if not camera:
            return Response({
                "success": False,
                "message": "No cleaners camera found for this tent.",
                "results": []
            }, status=200)

        history_qs = CleanersPresenceHistory.objects.filter(
            camera=camera,
            start_time__gte=start_date_time,
            end_time__lte=end_date_time,
        ).order_by('start_time')

        compressed_data = []
        previous_class = None
        previous_count = None
        segment_start_time = None
        segment_end_time = None

        for entry in history_qs:
            if previous_class is None:
                previous_class = entry.person_class
                previous_count = entry.cleaner_count
                segment_start_time = entry.start_time
                segment_end_time = entry.end_time
            elif entry.person_class != previous_class or entry.cleaner_count != previous_count:
                compressed_data.append({
                    "start_time": segment_start_time,
                    "end_time": entry.start_time,
                    "person_class": previous_class,
                    "cleaner_count": previous_count,
                    "time": segment_start_time,
                })
                previous_class = entry.person_class
                previous_count = entry.cleaner_count
                segment_start_time = entry.start_time
            segment_end_time = entry.end_time

        if segment_start_time is not None:
            compressed_data.append({
                "start_time": segment_start_time,
                "end_time": segment_end_time,
                "person_class": previous_class,
                "cleaner_count": previous_count,
                "time": segment_start_time,
            })

        return Response({
            "success": True,
            "message": "Cleaner presence history fetched successfully.",
            "results": [{
                "name": camera.sn,
                "data": compressed_data
            }]
        }, status=200)


class CleanersPresenceReportView(APIView):
    permission_classes = [CleanersPresencePermission]
    pagination_class = CustomPagination

    def get(self, request):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')
        person_class = request.query_params.get('person_class')
        paginate_param = request.query_params.get('paginate', '').lower()
        paginate = paginate_param in ['true', '1', 'yes']

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time()))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=404)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=400)
        else:
            if user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            else:
                tents = user.assigned_tent.all()

        query = Q(camera__tent__in=tents) & Q(
            start_time__gte=start_datetime) & Q(end_time__lte=end_datetime)

        if person_class:
            query &= Q(person_class=person_class)

        records = CleanersPresenceHistory.objects.filter(query).order_by('-created_at').select_related('camera__tent')

        data = [
            {
                'id': r.id,
                'tent_name': r.camera.tent.name if r.camera.tent else None,
                'camera_sn': r.camera.sn,
                'person_class': r.person_class,
                'cleaner_count': r.cleaner_count,
                'start_time': r.start_time,
                'end_time': r.end_time,
                'image': request.build_absolute_uri(r.image.url) if r.image else None,
            }
            for r in records
        ]

        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            "success": True,
            "message": "Cleaners presence report fetched successfully.",
            "count": len(data),
            "results": data,
        }, status=200)


class CleanersPresenceHistoryUpdateView(APIView):
    def patch(self, request, pk):
        record = get_object_or_404(CleanersPresenceHistory, pk=pk)
        serializer = CleanersPresenceHistorySerializer(
            record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# Empty Chair Detection
# ─────────────────────────────────────────────────────────────────────────────

class CreateEmptyChairDetectionView(APIView):
    """
    POST  — AI camera pushes a new detection record.
    GET   — Annotator queue: unannotated records (optionally by pk).
    PUT   — AI system updates an existing record by pk.
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk=None):
        if pk is not None:
            record = get_object_or_404(EmptyChairDetectionReport, pk=pk)
            serializer = EmptyChairDetectionReportSerializer(record)
            return Response({
                "success": True,
                "message": "Empty Chair Detection record retrieved successfully.",
                "data": serializer.data,
            }, status=status.HTTP_200_OK)

        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        qs = (
            EmptyChairDetectionReport.objects
            .filter(is_annotated=False, is_ai_annotated=False)
            .select_related('camera__tent')
            .order_by('-created_at')
        )
        paginated_qs, total_count, pagination_info = paginate_queryset(qs, page, page_size)
        serializer = EmptyChairDetectionReportSerializer(paginated_qs, many=True)
        return Response({
            "success": True,
            "message": "Empty Chair Detection records retrieved successfully.",
            "pagination": pagination_info,
            "data": serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        match_empty_chair_detection_key(header_key)

        camera_sn = request.data.get('sn')
        if not camera_sn:
            return Response(
                {"message": "Camera SN is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            camera = Camera.objects.get(sn=camera_sn)
        except Camera.DoesNotExist:
            return Response(
                {"message": f"Camera with SN '{camera_sn}' does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()
        data['camera'] = camera.pk

        serializer = EmptyChairDetectionReportSerializer(
            data=data, context={'request': request}
        )
        if serializer.is_valid():
            instance = serializer.save(camera=camera)
            return Response({
                "message": "Empty Chair Detection record created successfully.",
                "data": EmptyChairDetectionReportSerializer(instance).data,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Invalid data",
            "errors": serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        record = get_object_or_404(EmptyChairDetectionReport, pk=pk)
        serializer = EmptyChairDetectionReportSerializer(
            record, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Empty Chair Detection record updated successfully.",
                "data": serializer.data,
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "message": "Error updating record.",
            "errors": serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)


class EmptyChairDetectionUpdateView(APIView):
    """PATCH — Annotator updates (annotate / reject) a single record."""

    def patch(self, request, pk):
        record = get_object_or_404(EmptyChairDetectionReport, pk=pk)
        serializer = EmptyChairDetectionReportSerializer(
            record, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmptyChairDetectionHistoryReportView(APIView):
    """
    GET — Dashboard history report with date + tent filters.
    Query params:
        start_date, end_date  (YYYY-MM-DD, required)
        tent_id               (comma-separated ints, optional)
        filter_param          empty | occupied | rejected | total
        hour                  0-23 (optional)
        paginate              true/false
    """
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')
        filter_param = request.query_params.get('filter_param')
        hour = request.query_params.get('hour')
        paginate = request.query_params.get('paginate', '').lower() in ['true', '1', 'yes']

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            else:
                tents = Tent.objects.filter(assigned_tent=user)

        queryset = (
            EmptyChairDetectionReport.objects
            .filter(
                Q(camera__tent__in=tents) &
                Q(start_time__gte=start_datetime) &
                Q(start_time__lte=end_datetime) &
                Q(is_annotated=True)
            )
            .select_related('camera__tent')
            .order_by('-start_time')
        )

        if filter_param == 'empty':
            queryset = queryset.filter(is_empty_detected=True)
        elif filter_param == 'occupied':
            queryset = queryset.filter(is_empty_detected=False)
        elif filter_param == 'rejected':
            queryset = queryset.filter(is_rejected=True)

        if hour is not None:
            queryset = queryset.filter(start_time__hour=int(hour))

        serializer = EmptyChairDetectionReportSerializer(
            queryset, many=True, context={'request': request}
        )

        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(serializer.data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

        return Response({
            'success': True,
            'message': "Empty Chair Detection history retrieved successfully.",
            'count': queryset.count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)


class EmptyChairDetectionReportChartView(APIView):
    """
    GET — Hourly aggregated chart data (avg empty chairs per hour).
    Query params: start_date, end_date, tent_id (comma-separated, optional)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tent_ids_text = request.query_params.get('tent_id')

        try:
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required.")
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if tent_ids_text:
            try:
                tent_ids = list(map(int, tent_ids_text.split(',')))
                tents = Tent.objects.filter(id__in=tent_ids)
                if not tents.exists():
                    return Response({"detail": "No valid tents found."}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"detail": "Invalid tent ID format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.is_superuser:
                tents = Tent.objects.all()
            elif user.is_admin:
                tents = Tent.objects.filter(company=user.company)
            else:
                tents = Tent.objects.filter(assigned_tent=user)

        queryset = (
            EmptyChairDetectionReport.objects
            .filter(
                Q(camera__tent__in=tents) &
                Q(start_time__gte=start_datetime) &
                Q(start_time__lte=end_datetime) &
                Q(is_annotated=True) &
                Q(is_rejected=False)
            )
        )

        total = queryset.count()
        empty_detected = queryset.filter(is_empty_detected=True).count()
        all_occupied = queryset.filter(is_empty_detected=False).count()
        rejected = queryset.filter(is_rejected=True).count()

        hourly_data = (
            queryset
            .annotate(hour=ExtractHour('start_time'))
            .values('hour')
            .annotate(
                avg_empty=Avg('empty_chair_count'),
                avg_total=Avg('total_chair_count'),
                record_count=Count('id'),
            )
            .order_by('hour')
        )

        return Response({
            'success': True,
            'message': "Empty Chair Detection chart data retrieved successfully.",
            'summary': {
                'total': total,
                'empty_detected': empty_detected,
                'all_occupied': all_occupied,
                'rejected': rejected,
            },
            'hourly': list(hourly_data),
        }, status=status.HTTP_200_OK)


class EmptyChairLiveCountView(APIView):
    """
    GET — Live current empty chair count per camera.
    Returns the most recent record for each chairdetection camera.
    No auth required so the dashboard can poll freely (add IsAuthenticated if needed).
    """

    def get(self, request):
        latest_count_sq = (
            EmptyChairDetectionReport.objects
            .filter(camera=OuterRef('pk'))
            .order_by('-start_time')
            .values('empty_chair_count')[:1]
        )
        latest_total_sq = (
            EmptyChairDetectionReport.objects
            .filter(camera=OuterRef('pk'))
            .order_by('-start_time')
            .values('total_chair_count')[:1]
        )
        latest_time_sq = (
            EmptyChairDetectionReport.objects
            .filter(camera=OuterRef('pk'))
            .order_by('-start_time')
            .values('start_time')[:1]
        )

        cameras = (
            Camera.objects
            .filter(type='chairdetection')
            .select_related('tent__company')
            .annotate(
                latest_empty_count=Subquery(latest_count_sq),
                latest_total_count=Subquery(latest_total_sq),
                latest_time=Subquery(latest_time_sq),
            )
            .order_by('tent__company__name', 'sn')
        )

        data = [
            {
                'camera_id': cam.id,
                'camera_sn': cam.sn,
                'tent_id': cam.tent_id,
                'tent_name': cam.tent.name if cam.tent else None,
                'company_name': cam.tent.company.name if cam.tent and cam.tent.company else None,
                'empty_chair_count': cam.latest_empty_count or 0,
                'total_chair_count': cam.latest_total_count or 0,
                'last_seen': cam.latest_time,
            }
            for cam in cameras
        ]

        return Response({
            'success': True,
            'message': 'Live empty chair counts retrieved successfully.',
            'total_cameras': len(data),
            'data': data,
        }, status=status.HTTP_200_OK)
