# Built-in imports
import csv
import io
import re
import math
from collections import defaultdict
from datetime import datetime, timedelta, time, date
import pandas as pd
# Third-party imports
import pytz
from django.utils.timezone import make_aware, is_aware, localtime
from django.utils.dateparse import parse_datetime
from django.db.models.functions import Cast
# Django imports
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import (
    Sum, IntegerField, Max, Min, Avg, Q, F, ExpressionWrapper, DurationField, Prefetch, Exists, OuterRef, Count, Subquery
)
from django.db.models.functions import TruncMonth, TruncHour, TruncDay, TruncDate, Coalesce


# DRF imports
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# Local app imports
from authentication.utils import standard_response_api
from authentication.models import Company

from tent.models import Tent, TentsWaterTank, WaterTankSensorHistory, Country
from tent.serializers import (
    TentSerializer, WaterSensorHistorySerializer,
    TentWaterTankSerializer, WaterTankMonthlyDataSerializer, CountrySerializer, CreateTentFromServerSerializer
)
from tent.utils import generate_csv_response, CustomPagination

from camera.models import AbnormalActivities, Camera, CounterHistory, CrowdMonitoringReport, SentimentAnalysis, KitchenViolationReport, GarbageMonitoringReport, RecycleMonitoringReport, FallDetectionMonitoringReport, ViolenceMonitoringReport, GuardPresenceHistory, BuffetViolationReport, BathroomMonitoringHistory, WallClimbMonitoringReport, EmptyChairDetectionReport, CleanersPresenceHistory
from camera.views import smart_aggregate
from camera.serializers import CameraSerializer

from sensor.models import EnvironmentSensor, EnvironmentSensorRecord
from sensor.serializers import EnvironmentSensorSerializer, DateWiseEnvironmentSensorSerializer, EnvironmentSensorAverageSerializer

from weight.utils import match_water_level_key
from weight.models import OrderWeight, WeightConditions

from utils.sorting import tent_name_list_dict_sorting
from utils.time import Current_saudi_time, convert_utc_to_riyadh, saudi_tz
from authentication.permissions import TemperaturePermission


def custom_sort_key(item):
    match = re.match(r"(\d+)([A-Za-z]*)", item.name)
    if match:
        number = int(match.group(1))
        suffix = match.group(2)
        return (number, suffix)
    return (float('inf'), '')


def date_time_to_aware(date_time):
    if not is_aware(date_time):
        date_time = make_aware(date_time)
    return date_time


class CountryDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        user = request.user
        if pk:
            try:
                country = Country.objects.get(pk=pk)
                serializer = CountrySerializer(country)
                return Response(serializer.data)
            except Country.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "Country not found."

                }, status=status.HTTP_404_NOT_FOUND)
        if user.is_admin:
            tents = Tent.objects.filter(company=request.user.company)
        else:
            assigned_tent_ids = user.assigned_tent.values_list('id', flat=True)
            tents = Tent.objects.filter(
                id__in=assigned_tent_ids, company=request.user.company)
        countries = Country.objects.filter(tent__in=tents).distinct()
        serializer = CountrySerializer(countries, many=True)
        data = {
            "success": True,
            "message": "List of countries",
            "data": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CountrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            data = {
                "success": True,
                "message": "Country successfully created!",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_201_CREATED)

        data = {
            "success": False,
            "message": "Invalid data",
            "errors": serializer.errors
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        try:
            country = Country.objects.get(pk=pk)
        except Country.DoesNotExist:
            data = {
                "success": False,
                "message": "Country not found."
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        serializer = CountrySerializer(
            country, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            data = {
                "success": True,
                "message": "Country successfully updated!",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)

        data = {
            "success": False,
            "message": "Invalid data",
            "errors": serializer.errors
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        try:
            country = Country.objects.get(pk=pk)
        except Country.DoesNotExist:
            data = {
                "success": False,
                "message": "Country not found."
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        country.delete()
        data = {
            "success": True,
            "message": "Country successfully deleted!"
        }
        return Response(data, status=status.HTTP_202_ACCEPTED)


class TentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        user = request.user
        is_arafa_param = request.GET.get("is_arafa", None)
        if is_arafa_param is None:
            is_arafa = None
        else:
            is_arafa = is_arafa_param.lower() == "true"
        company_ids_qr = request.GET.get('company_ids', '')

        # Parse ID list

        def parse_id_list(param: str) -> list[int]:
            return [int(i) for i in param.split(',') if i.strip().isdigit()]

        company_ids = parse_id_list(company_ids_qr)

        if pk:
            # Single tent detail
            tent = get_object_or_404(
                Tent.objects.prefetch_related('sensors'), pk=pk)
            if tent.company != request.user.company:
                return Response({
                    "success": False,
                    "message": f"Tent with ID {pk} does not belong to your company."
                }, status=status.HTTP_403_FORBIDDEN)
            if not user.is_admin and tent not in user.assigned_tent.all():
                return Response({
                    "success": False,
                    "message": f"Tent with ID {pk} is not assigned to you."
                }, status=status.HTTP_403_FORBIDDEN)
            serializer = TentSerializer(tent, context={'request': request})
            return Response({
                "success": True,
                "data": serializer.data
            })
        elif company_ids and user.is_annotator:
            queryset = Tent.objects.prefetch_related(
                'sensors').filter(
                company__id__in=company_ids,
                is_arafa=is_arafa
            )
            queryset = sorted(
                queryset, key=lambda tent: tent_name_list_dict_sorting(tent.name))
            serializer = TentSerializer(
                queryset, many=True, context={'request': request})
            return Response({
                "success": True,
                "results": serializer.data
            })
        elif is_arafa is not None:
            if user.is_admin:
                queryset = Tent.objects.prefetch_related(
                    'sensors').filter(
                    company=request.user.company, is_arafa=is_arafa)
                queryset = sorted(
                    queryset, key=lambda tent: tent_name_list_dict_sorting(tent.name))
                serializer = TentSerializer(
                    queryset, many=True, context={'request': request})
                return Response({
                    "success": True,
                    "results": serializer.data
                })
            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                queryset = Tent.objects.prefetch_related(
                    'sensors').filter(
                    id__in=assigned_tent_ids, company=request.user.company, is_arafa=is_arafa)
                serializer = TentSerializer(
                    queryset, many=True, context={'request': request})
                return Response({
                    "success": True,
                    "results": serializer.data
                }, status=status.HTTP_200_OK)
        else:
            # List tents
            paginate = request.query_params.get(
                'paginate', 'false').lower() == 'true'
            if user.is_admin:
                queryset = Tent.objects.prefetch_related(
                    'sensors').filter(
                    company=request.user.company)
            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                queryset = Tent.objects.prefetch_related(
                    'sensors').filter(
                    id__in=assigned_tent_ids, company=request.user.company)
            if paginate:
                queryset = sorted(
                    queryset, key=lambda tent: tent_name_list_dict_sorting(tent.name))
                paginator = CustomPagination()
                paginated_queryset = paginator.paginate_queryset(
                    queryset, request)
                serializer = TentSerializer(
                    paginated_queryset, many=True, context={'request': request})
                return paginator.get_paginated_response(serializer.data)
            else:
                queryset = sorted(
                    queryset, key=lambda tent: tent_name_list_dict_sorting(tent.name))
                serializer = TentSerializer(
                    queryset, many=True, context={'request': request})
                return Response({
                    "success": True,
                    "results": serializer.data
                })

    def post(self, request):
        if not request.user.is_admin:
            return Response({
                "success": False,
                "message": "You are not authorized to create tents."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = TentSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Tent created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "message": serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        if not request.user.is_admin:
            return Response({
                "success": False,
                "message": "You are not authorized to update tents."
            }, status=status.HTTP_403_FORBIDDEN)

        tent = get_object_or_404(Tent, pk=pk)

        # check ownership
        if tent.company != request.user.company:
            return Response({
                "success": False,
                "message": "This tent does not belong to your company."
            }, status=status.HTTP_403_FORBIDDEN)
        name = request.data.get('name')
        if name and name != tent.name and Tent.objects.filter(name=name).exists():
            return Response({
                "success": False,
                "message": f"Tent with name {name} already exists"
            }, status=status.HTTP_400_BAD_REQUEST)
        serializer = TentSerializer(
            tent, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Tent updated successfully.",
                "data": serializer.data
            })
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        if not request.user.is_admin:
            return Response({
                "success": False,
                "message": "You are not authorized to update tents."
            }, status=status.HTTP_403_FORBIDDEN)
        tent = get_object_or_404(Tent, pk=pk)

        # check ownership
        if tent.company != request.user.company:
            return Response({
                "success": False,
                "message": "This tent does not belong to your company."
            }, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name')
        if name and name != tent.name and Tent.objects.filter(name=name).exists():
            return Response({
                "success": False,
                "message": f"Tent with name {name} already exists"
            }, status=status.HTTP_400_BAD_REQUEST)
        serializer = TentSerializer(
            tent, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Tent partially updated successfully.",
                "data": serializer.data
            })
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if not request.user.is_admin:
            return Response({
                "success": False,
                "message": "You are not authorized to delete tents."
            }, status=status.HTTP_403_FORBIDDEN)
        try:
            tent = get_object_or_404(Tent, pk=pk)
        except Tent.DoesNotExist:
            return Response({
                "success": False,
                "message": "Tent not found"
            }, status=status.HTTP_404_NOT_FOUND)

        # check ownership
        if tent.company != request.user.company:
            return Response({
                "success": False,
                "message": "This tent does not belong to your company."
            }, status=status.HTTP_403_FORBIDDEN)

        tent.delete()
        return Response({
            "success": True,
            "message": "Tent deleted successfully."
        }, status=status.HTTP_202_ACCEPTED)


class AllTentCamerasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tent_id=None):
        tent = get_object_or_404(Tent, id=tent_id)
        cameras = tent.camera.all()

        cameras_data = CameraSerializer(cameras, many=True).data

        return standard_response_api(
            success=True,
            message='Cameras retrieved successfully.',
            data={'cameras': cameras_data},
            status_code=status.HTTP_200_OK
        )


class TentEnvironmentSensorView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tent_id=None):
        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        tent = get_object_or_404(Tent, pk=tent_id)
        sensor_list = EnvironmentSensor.objects.select_related('tent').filter(
            tent=tent, type="environment", tempareture__gt=0)

        is_live = request.GET.get('is_live', 'true').lower() == "true"
        filter = True if request.GET.get(
            'is_kitchen_corridor', 'false').lower() == "true" else False
        paginate = True if request.GET.get(
            'paginate', 'true').lower() == "true" else False

        exclude_conditions = (
            Q(location__icontains='Outside') |
            Q(location__icontains='kitchen') |
            Q(location__icontains='corridor')
        )
        if not filter:
            sensor_list = sensor_list.exclude(exclude_conditions)

        def round_half_up(value):
            if value is None:
                return None
            return math.floor(value + 0.5)

        summary_data = sensor_list.exclude(exclude_conditions).aggregate(
            min_humidity=Min('humidity'),
            max_humidity=Max('humidity'),
            avg_humidity=Avg('humidity'),
            min_temperature=Min(F('tempareture')),
            max_temperature=Max(F('tempareture')),
            avg_temperature=Avg(F('tempareture')),
        )

        # Apply rounding
        rounded_summary = {
            key: round_half_up(value)
            for key, value in summary_data.items()
        }

        # Inside your view:
        # paginator = CustomPagination()
        # if paginate:
        #     paginated_sensor_list = paginator.paginate_queryset(sensor_list, request)
        # else:
        #     paginated_sensor_list = sensor_list
        if is_live:
            serializer = EnvironmentSensorAverageSerializer(
                sensor_list, many=True)
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or None
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or None
            if start_date_time > end_date_time:
                return standard_response_api(
                    success=False,
                    message='Invalid date range.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            serializer = DateWiseEnvironmentSensorSerializer(
                sensor_list, many=True, context={
                    'request': request,
                    'start_date_time': start_date_time,
                    'end_date_time': end_date_time,
                    'is_live': is_live
                }
            )

        return standard_response_api(
            success=True,
            message='Environments retrieved successfully.',
            data={"summary_data": rounded_summary,
                  'sensor_list': serializer.data},
            status_code=status.HTTP_200_OK
        )


class AllTentEnvironmentSensorView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_arafa = request.GET.get('isarafa', False)

        # Step 1: Filter tents based on user access
        if user.is_admin:
            tents = Tent.objects.filter(company=user.company)
        elif user.is_superuser:
            tents = Tent.objects.all()
        else:
            tents = Tent.objects.filter(
                id__in=user.assigned_tent.values_list('id', flat=True),
                company=user.company
            )

        # Step 2: Apply is_arafa filter if provided
        if is_arafa == "true":
            tents = tents.filter(is_arafa=True)
        elif is_arafa == "false":
            tents = tents.filter(is_arafa=False)

        sensor_q = (Q(sensors__location__isnull=True) | ~Q(sensors__location__iexact='kitchen')) & Q(sensors__tempareture__gt=0)

        annotated_tents = tents.annotate(
            _min_humidity=Min('sensors__humidity', filter=sensor_q),
            _max_humidity=Max('sensors__humidity', filter=sensor_q),
            _avg_humidity=Avg('sensors__humidity', filter=sensor_q),
            _min_temp=Min('sensors__tempareture', filter=sensor_q),
            _max_temp=Max('sensors__tempareture', filter=sensor_q),
            _avg_temp=Avg('sensors__tempareture', filter=sensor_q),
            _latest_at=Max('sensors__created_at', filter=sensor_q),
        ).values(
            'id', 'name', 'air_condition',
            '_min_humidity', '_max_humidity', '_avg_humidity',
            '_min_temp', '_max_temp', '_avg_temp', '_latest_at',
        )

        all_sensor_data = []
        for t in annotated_tents:
            min_temp = (t['_min_temp'] or 0) / 10.0
            max_temp = (t['_max_temp'] or 0) / 10.0
            avg_temp = (t['_avg_temp'] or 0) / 10.0

            if max_temp >= 40:
                warning_level = 'red'
            elif max_temp <= 25:
                warning_level = 'green'
            else:
                warning_level = 'neutral'

            all_sensor_data.append({
                'tent_id': t['id'],
                'name': t['name'],
                'air_condition': t['air_condition'],
                'min_humidity': t['_min_humidity'] or 0,
                'max_humidity': t['_max_humidity'] or 0,
                'avg_humidity': t['_avg_humidity'] or 0,
                'min_temperature': min_temp,
                'max_temperature': max_temp,
                'avg_temperature': avg_temp,
                'created_at': t['_latest_at'],
                'warning_level': warning_level,
            })

        response_data = {
            'success': True,
            'message': 'Environments average successfully.',
            'data': all_sensor_data
        }
        return Response(response_data, status=status.HTTP_200_OK)


class TentWaterTankHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tent_id=None, format=None):
        interval = request.GET.get('interval', None)
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)

        if not interval:
            return Response({"detail": "interval is required."}, status=status.HTTP_400_BAD_REQUEST)

        water_tanks = TentsWaterTank.objects.filter(tent_id=tent_id)
        if not water_tanks.exists():
            return Response({
                "success": True,
                "results": []
            }, status=status.HTTP_200_OK)

        if interval == "hour":
            if not start_date_str:
                return Response({"detail": "start_date is required."}, status=status.HTTP_400_BAD_REQUEST)
            start_date = parse_date(start_date_str)
            return self._get_hourly_data(water_tanks, start_date, start_date_str)

        elif interval == "day":
            if not start_date_str or not end_date_str:
                return Response({"detail": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)

            if start_date == end_date:
                end_date = end_date + timedelta(days=1)

            if start_date > end_date:
                return Response({"detail": "start_date must be before end_date."}, status=status.HTTP_400_BAD_REQUEST)

            return self._get_daily_data(water_tanks, start_date, end_date)

        elif interval == "month":
            if not start_date_str or not end_date_str:
                return Response({"detail": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)

            if start_date == end_date:
                end_date = end_date + timedelta(days=1)

            if start_date > end_date:
                return Response({"detail": "start_date must be before end_date."}, status=status.HTTP_400_BAD_REQUEST)

            return self._get_monthly_data(water_tanks, start_date, end_date)

        else:
            return Response({"detail": f"Unsupported interval: {interval}. Supported values are 'days', 'hours', or 'month'."}, status=status.HTTP_400_BAD_REQUEST)

    def _get_hourly_data(self, water_tanks, start_date, start_date_str):
        # Create a nested dictionary for each hour and sensor
        history_data = defaultdict(lambda: defaultdict(dict))
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        end_datetime = start_datetime + timedelta(days=1)

        # Query history data for the selected sensors and the specific date range
        history_query = WaterTankSensorHistory.objects.filter(
            water_sensor__in=water_tanks,
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        ).annotate(hour=TruncHour('created_at')).values('hour', 'water_sensor').annotate(
            avg_water_level_percent=Avg('water_level_percent')).order_by('hour', 'water_sensor')

        result_data = []

        for history in history_query:
            water_sensor_obj = TentsWaterTank.objects.get(
                pk=history['water_sensor'])

            result_data.append({
                'water_sensor': history['water_sensor'],
                'hour': history['hour'],
                'avg_water_level_percent': history['avg_water_level_percent'],
                'tank_number': water_sensor_obj.tank_number,
            })

        return Response(self._format_sensor_data_hour(result_data, start_date_str))

    def _get_daily_data(self, water_tanks, start_date, end_date):
        # Ensure start_date and end_date are timezone-aware
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        end_datetime = timezone.make_aware(timezone.datetime.combine(
            end_date, timezone.datetime.min.time())) + timedelta(days=1)

        # Query history data for the selected sensors and specific date range, grouping by day
        history_query = WaterTankSensorHistory.objects.filter(
            water_sensor__in=water_tanks,
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        ).annotate(day=TruncDate('created_at')).values('day', 'water_sensor').annotate(
            avg_water_level_percent=Avg('water_level_percent')
        ).order_by('day', 'water_sensor')

        result_data = []

        for history in history_query:
            # print(history['water_sensor'])
            water_sensor_obj = TentsWaterTank.objects.get(
                pk=history['water_sensor'])

            result_data.append({
                'water_sensor': history['water_sensor'],
                'day': history['day'],
                'avg_water_level_percent': history['avg_water_level_percent'],
                'tank_number': water_sensor_obj.tank_number,
            })

        # Generate a list of all dates between start_date and end_date
        all_dates = [start_date + timedelta(days=i)
                     for i in range((end_date - start_date).days + 1)]

        # Call the formatting function to structure the result
        return Response(self._format_sensor_data_day(result_data, all_dates))

    def _get_monthly_data(self, water_tanks, start_date, end_date):
        # Ensure start_date and end_date are timezone-aware
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        end_datetime = timezone.make_aware(timezone.datetime.combine(
            end_date, timezone.datetime.min.time())) + timedelta(days=1)

        # Query history data for the selected sensors and specific date range, grouping by month
        history_query = WaterTankSensorHistory.objects.filter(
            water_sensor__in=water_tanks,
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        ).annotate(month=TruncMonth('created_at')).values('month', 'water_sensor').annotate(
            avg_water_level_percent=Avg('water_level_percent')
        ).order_by('month', 'water_sensor')

        result_data = []

        for history in history_query:
            water_sensor_obj = TentsWaterTank.objects.get(
                pk=history['water_sensor'])

            result_data.append({
                'water_sensor': history['water_sensor'],
                'month': history['month'],
                'avg_water_level_percent': history['avg_water_level_percent'],
                'tank_number': water_sensor_obj.tank_number,
            })

        # Generate a list of all months between start_date and end_date
        all_months = [
            (start_date + timedelta(days=i * 30)).replace(day=1)
            for i in range((end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1)
        ]

        # Call the formatting function to structure the result
        return Response(self._format_sensor_data_month(result_data, all_months))

    def _format_sensor_data_hour(self, input_data, start_time, interval_hours=24):

        # Parse and initialize
        # Each hour for a day
        tank_data = defaultdict(lambda: [0] * interval_hours)
        date_labels = []
        start_time = datetime.strptime(
            start_time, "%Y-%m-%d").replace(tzinfo=pytz.UTC)

        # Process each entry
        for entry in input_data:
            tank_number = entry["tank_number"]
            avg_water_level = entry["avg_water_level_percent"]

            # Ensure hour is always a datetime object
            if isinstance(entry["hour"], str):
                hour = datetime.fromisoformat(
                    entry["hour"]).astimezone(pytz.UTC)
            else:
                hour = entry["hour"].astimezone(pytz.UTC)

            # Find index for the hourly interval
            index = (hour - start_time).seconds // 3600
            if 0 <= index < interval_hours:
                tank_data[f'Tank {tank_number}'][index] = avg_water_level

        # Generate time labels for each hour of the day
        for i in range(interval_hours):
            interval_time = start_time + timedelta(hours=i)
            # date_labels.append(interval_time.strftime("%Y-%m-%d %H:%M:%S"))
            # label = f'{i + 1}'  # Add hour index
            # date_labels.append(label)
            date_labels.append(interval_time.strftime("%H"))
            # date_labels.append(interval_time.strftime("%Y-%m-%d %H:%M:%S"))

        # Arrange into result dict
        final_result = {
            'data': [{'name': name, 'data': [round(value, 3) for value in values]} for name, values in tank_data.items()],
            'dates': date_labels
        }

        return final_result

    def _format_sensor_data_day(self, input_data, all_dates):

        # print(all_dates)
        # Initialize daily data structure
        tank_data = defaultdict(lambda: [0] * len(all_dates))
        date_labels = [date.strftime("%Y-%m-%d") for date in all_dates]

        # Map input data to appropriate daily slots
        date_to_index = {date: idx for idx, date in enumerate(all_dates)}
        for entry in input_data:
            tank_number = entry['tank_number']
            avg_water_level = entry['avg_water_level_percent']
            day = entry['day']
            if day in date_to_index:
                index = date_to_index[day]
                tank_data[f'Tank {tank_number}'][index] = avg_water_level

        # Format the result
        final_result = {
            'data': [{'name': name, 'data': [round(value, 3) for value in values]} for name, values in tank_data.items()],
            'dates': date_labels
        }

        return final_result

    def _format_sensor_data_month(self, input_data, all_months):

        # Ensure all_months contains all unique months from input_data
        unique_months = sorted(
            set(all_months + [entry['month'].date() for entry in input_data]))
        month_labels = [month.replace(day=1) for month in unique_months]

        # Initialize monthly data structure
        tank_data = defaultdict(lambda: [0] * len(unique_months))

        # Map input data to appropriate monthly slots
        month_to_index = {month: idx for idx,
                          month in enumerate(unique_months)}
        for entry in input_data:
            tank_number = entry['tank_number']
            avg_water_level = entry['avg_water_level_percent']
            # Ensure it's a datetime.date object
            month = entry['month'].date().replace(day=1)

            if month in month_to_index:
                index = month_to_index[month]
                tank_data[f'Tank {tank_number}'][index] = avg_water_level

        # Format the result
        final_result = {
            'data': [{'name': name, 'data': [round(value, 3) for value in values]} for name, values in tank_data.items()],
            'months': month_labels
        }

        return final_result


class ReportView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WaterTankMonthlyDataSerializer
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        response_type = request.GET.get('type', 'json')
        interval = request.GET.get('interval', 'hour')
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'
        tent_ids = []
        water_tanks = None
        tents = None

        if user.is_superuser:
            tents = Tent.objects.all()
        # elif user.is_staff:
        #     tents = Tent.objects.filter(assigned_staff=user)
        else:
            # Regular user, return only tents from their company
            tents = Tent.objects.filter(company=user.company)

        # Parse and validate dates
        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None

        if not interval or not start_date or not end_date:
            return Response({"detail": "interval, start_date, and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)
        if start_date > end_date:
            return Response({"detail": "start_date must be before end_date."}, status=status.HTTP_400_BAD_REQUEST)
        if start_date == end_date:
            end_date += timedelta(days=1)

        # Convert to datetime objects
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.min.time()))

        if tent_id_list:
            try:
                tent_ids = [int(tid.strip()) for tid in tent_id_list.split(
                    ',') if tid.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid tent_ids parameter. It must be a comma-separated list of integers."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter water sensors by tent_id if provided
        if len(tent_ids) > 0:
            water_tanks = TentsWaterTank.objects.filter(tent_id__in=tent_ids)
        else:
            water_tanks = TentsWaterTank.objects.filter(tent__in=tents)
        if not water_tanks.exists():
            return Response({"detail": "No water sensors found for the specified tent."}, status=status.HTTP_400_BAD_REQUEST)

        # Annotate and aggregate based on the interval
        queryset = WaterTankSensorHistory.objects.filter(
            water_sensor__in=water_tanks,
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        )

        if interval == "hour":
            queryset = queryset.annotate(period=TruncHour('created_at'))
        elif interval == "day":
            queryset = queryset.annotate(period=TruncDay('created_at'))
        elif interval == "month":
            queryset = queryset.annotate(period=TruncMonth('created_at'))
        else:
            return Response({"detail": f"Invalid interval: {interval}. Valid options are 'hour', 'day', or 'month'."}, status=status.HTTP_400_BAD_REQUEST)

        # Aggregate data by period and sensor
        queryset = queryset.values('period', 'water_sensor').annotate(
            min_water_level_percent=Min('water_level_percent'),
            max_water_level_percent=Max('water_level_percent'),
            avg_water_level_percent=Avg('water_level_percent')
        ).order_by('period', 'water_sensor')

        # Pre-fetch related tent data
        water_tanks_dict = {
            tank.id: tank for tank in water_tanks.select_related('tent')}

        # Format the data with additional details
        result_data = []
        for record in queryset:
            sensor_id = record['water_sensor']
            period = record['period']
            sensor = water_tanks_dict.get(sensor_id)

            min_time = WaterTankSensorHistory.objects.filter(
                water_sensor_id=sensor_id,
                created_at__range=(period, period + timedelta(hours=1)),
                water_level_percent=record['min_water_level_percent']
            ).values_list('created_at', flat=True).first()

            max_time = WaterTankSensorHistory.objects.filter(
                water_sensor_id=sensor_id,
                created_at__range=(period, period + timedelta(hours=1)),
                water_level_percent=record['max_water_level_percent']
            ).values_list('created_at', flat=True).first()

            result_data.append({
                'tent_id': sensor.tent.id,
                'tent_name': sensor.tent.name,
                'tank_number': sensor.tank_number,
                'sensor_id': sensor.sensor_sn,
                'date_and_time': period,
                'min_water_level_percent': record['min_water_level_percent'],
                'min_water_level_percent_date_and_time': min_time,
                'max_water_level_percent': record['max_water_level_percent'],
                'max_water_level_percent_date_and_time': max_time,
                'avg': f"{record['avg_water_level_percent']:.3f}" if record['avg_water_level_percent'] is not None else None,
            })

        # Sort the data
        result_data = sorted(result_data, key=lambda x: x['tent_id'])

        # Handle CSV or JSON response
        if response_type == 'csv':
            return generate_csv_response(result_data, 'report_data.csv')

            # Apply pagination if requested
        if paginate:
            # Apply pagination
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                result_data, request, view=self)
            return paginator.get_paginated_response(paginated_data)
        else:
            return Response({
                'success': True,
                'message': "Water tanks Report Data Retrieved Successfully",
                'results': result_data,
            }, status=status.HTTP_200_OK)


class TentWaterTankAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, pk=None, *args, **kwargs):
        user = request.user
        tanks = []
        latest_history_pf = Prefetch(
            'sensor_history',
            queryset=WaterTankSensorHistory.objects.order_by('-end_time'),
            to_attr='_prefetched_history',
        )

        if pk:
            # Retrieve a single tank
            tank = get_object_or_404(
                TentsWaterTank.objects.prefetch_related(latest_history_pf), pk=pk)
            serializer = TentWaterTankSerializer(tank)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Retrieve all tanks
            if user.is_admin:
                tanks = TentsWaterTank.objects.prefetch_related(
                    latest_history_pf).filter(
                    tent__company=user.company).order_by('id')

            elif user.is_superuser:
                tanks = TentsWaterTank.objects.prefetch_related(
                    latest_history_pf).all().order_by('id')

            else:
                assigned_tent_ids = user.assigned_tent.values_list(
                    'id', flat=True)
                tanks = TentsWaterTank.objects.prefetch_related(
                    latest_history_pf).filter(
                    tent__id__in=assigned_tent_ids
                ).order_by('id')

            serializer = TentWaterTankSerializer(tanks, many=True)

            # Apply pagination
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                serializer.data, request, view=self)
            return paginator.get_paginated_response(paginated_data)

    def post(self, request, *args, **kwargs):
        serializer = TentWaterTankSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, pk, *args, **kwargs):
        tank = get_object_or_404(TentsWaterTank, pk=pk)
        serializer = TentWaterTankSerializer(tank, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk, *args, **kwargs):
        tank = get_object_or_404(TentsWaterTank, pk=pk)
        serializer = TentWaterTankSerializer(
            tank, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        tank = get_object_or_404(TentsWaterTank, pk=pk)
        tank.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TentTotalCapacityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tent_id=None):
        user = request.user
        tent_list = []
        all_tent_list = []
        date_filter = {}
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)

        # Parse dates
        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None

        # Validate date inputs
        if (start_date_str and not end_date_str) or (end_date_str and not start_date_str):
            return Response(
                {"detail": "Both start_date and end_date are required if one is provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_date_str and end_date_str:
            if start_date > end_date:
                return Response(
                    {"detail": "start_date must be before end_date."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if start_date == end_date:
                start_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        start_date, timezone.datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        end_date, timezone.datetime.max.time())
                )
            else:
                start_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        start_date, timezone.datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        end_date, timezone.datetime.min.time())
                )
            date_filter = {
                'created_at__gte': start_datetime,
                'created_at__lt': end_datetime
            }
        else:
            start_datetime = None
            end_datetime = None

        # Determine which tents to process
        if tent_id:
            tent = get_object_or_404(Tent, pk=tent_id)
            tent_list = Tent.objects.filter(pk=tent.pk).order_by('name')
        else:
            if user.is_admin:
                tent_list = Tent.objects.filter(
                    company=request.user.company).order_by('id')
            else:
                tent_ids = user.assigned_tent.values_list('id', flat=True)
                tent_list = Tent.objects.filter(id__in=tent_ids).order_by('id')

        # Calculate total capacity for all tents
        total_capacity = tent_list.aggregate(
            total=Sum('capacity'))['total'] or 0

        # Use a consistent approach for calculating staying counts
        # Get per-tent staying counts
        all_tent_list = []
        total_staying = 0

        for tent in tent_list:
            counter_history = CounterHistory.objects.filter(
                camera__tent=tent, **date_filter)
            count_history = counter_history.aggregate(
                staying=Sum(F('total_in')) - Sum(F('total_out')),
            )
            # Default to 0 if None
            staying_count = count_history['staying'] or 0
            total_staying += staying_count

            all_tent_list.append({
                'tent_id': tent.pk,
                'tent_name': tent.name,
                'capacity': tent.capacity,
                'staying': staying_count,
                'available_capacity': tent.capacity - staying_count
            })

        # Calculate totals using the same method
        total_data = {
            'total_capacity': total_capacity,
            'total_staying': total_staying,
            'available_capacity': total_capacity - total_staying
        }

        if tent_id is None:
            result = {
                'total_data': total_data,
                'all_tent_list': all_tent_list,
            }
        else:
            result = all_tent_list[0] if all_tent_list else {}

        return standard_response_api(
            success=True,
            message='Total capacity and staying retrieved successfully.',
            data=result,
            status_code=status.HTTP_200_OK
        )


class TentTankGaurdCleanHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tent_id=None):
        user = request.user
        tents = []
        # If tent_id is provided, validate and retrieve the specific tent

        if tent_id:
            try:
                tent = Tent.objects.get(id=tent_id)
            except Tent.DoesNotExist:
                return Response({"detail": "Tent not found."}, status=status.HTTP_404_NOT_FOUND)
            tents = [tent]

        else:
            # Step 1: Filter tents based on user access
            if user.is_admin:
                tents = Tent.objects.filter(
                    company=user.company, is_arafa=False)
            elif user.is_superuser:
                try:
                    tent = Tent.objects.filter(
                        id=tent_id, is_arafa=False).get()
                except Tent.DoesNotExist:
                    return Response({"detail": "Tent not found."}, status=status.HTTP_404_NOT_FOUND)

            else:
                tents = Tent.objects.filter(
                    id__in=user.assigned_tent.values_list('id', flat=True),
                    company=user.company,
                    is_arafa=False
                )
                if not tents.exists():
                    return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare data for each tent
        data = []
        for tent in tents:
            water_tanks = self._get_water_sensor_history(tent)
            clean_indicator_history = self._get_clean_indicator_history(tent)
            guard_presence_histories = self._get_guard_presence_history(
                tent, request)
            violation_list = self._get_kitchen_violation_report(tent)
            data.append({
                "tent_id": tent.id,
                "tent_name": tent.name,
                "water_tanks": water_tanks,
                'clean_indicator_history': clean_indicator_history,
                "guard_presence_histories": guard_presence_histories,
                "kitchen_violation_list": violation_list
            })
        return Response(
            {
                "success": True,
                "message": "Averages retrieved successfully for all water tanks.",
                "data": data
            },
            status=status.HTTP_200_OK
        )

    def _get_water_sensor_history(self, tent):
        # Retrieve water tanks for the tent
        water_tanks = tent.water_tanks.all()

        if not water_tanks.exists():
            return []
        # Calculate averages for each water tank
        results = []
        for water_tank in water_tanks:
            data = water_tank.sensor_history.aggregate(
                avg_water_level=Avg('water_level'),
                avg_water_level_percent=Avg('water_level_percent'),
                min_water_level=Min('water_level'),
                max_water_level=Max('water_level'),
                min_water_level_percent=Min('water_level_percent'),
                max_water_level_percent=Max('water_level_percent'),

            )
            results.append({
                "tank_id": water_tank.id,
                "tank_number": water_tank.tank_number,
                "avg_water_level": data.get('avg_water_level', 0),
                "avg_water_level_percent": data.get('avg_water_level_percent', 0),
                "min_water_level": data.get("min_water_level", 0),
                "max_water_level": data.get("max_water_level", 0),
                "min_water_level_percent": data.get("min_water_level_percent", 0),
                "max_water_level_percent": data.get("max_water_level_percent", 0)
            })
        return results

    def _get_clean_indicator_history(self, tent):
        cameras = tent.camera.filter(type="clean")
        # print(cameras)
        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.clean_indicator_histories.order_by(
                '-created_at').first()
            # print("clean histroy data:", data.image)
            if data is None:
                continue

            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "is_clean": data.is_clean if data else None,
                "last_created_at": data.created_at if data else None,
                "image": data.image.url if data and data.image else None,
                "data_id": data.id if data else None,
                "created_at": data.created_at if data else None
            })
        return results

    def _get_guard_presence_history(self, tent, request):
        cameras = tent.camera.filter(type="guard")

        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.guard_presence_histories.order_by(
                '-created_at').first()
            if data is None:
                continue
            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "present": data.present if data else None,
                "last_created_at": data.created_at if data else None,
                "image": data.image.url if data and data.image else None,
                "data_id": data.id if data else None,
                "created_at": data.created_at if data else None
            })
        return results

    def _get_kitchen_violation_report(self, tent):
        cameras = tent.camera.filter(type="kitchen")

        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.kitchen_violation_histories.order_by(
                '-created_at').first()
            if data is None:
                continue
            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "violation": data.violation if data else None,
                "violation_list": data.violation_list if data else None,
            })
        return results


@method_decorator(csrf_exempt, name='dispatch')
class CreateWaterLevelSensor(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WaterSensorHistorySerializer(data=request.data)
        # Extract and validate the secret key
        header_key = request.headers.get('X-Secret-Key')

        match_water_level_key(header_key)
        if serializer.is_valid():
            water_level_sensor = serializer.save()
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


class TentTankGaurdCleanHistoryReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        type = request.GET.get('type')
        tents = None

        if not (type == 'clean' or type == 'kitchen' or type == 'guard' or type == 'garbage' or type == 'recycle' or type == 'buffet' or type == 'bathroom'):
            return Response({"detail": "Invalid type. Type should be clean, kitchen, guard, garbage, recycle or buffet."}, status=status.HTTP_400_BAD_REQUEST)

        # If no tent_id is provided, retrieve all tents
        if user.is_admin:
            tents = Tent.objects.filter(
                company=request.user.company).order_by('id')
        else:
            tents = user.assigned_tent.values_list('id', flat=True)
        if not tents.exists():
            return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare data for each tent
        data = []
        for tent in tents:
            if type == "clean":
                results = self._get_clean_indicator_history(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'clean_indicator_history': results,
                })
            elif type == "guard":
                results = self._get_guard_presence_history(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'guard_presence_histories': results,
                })
            elif type == "garbage":
                results = self._get_garbage_indicator_history(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'garbage_indicator_history': results,
                })
            elif type == "recycle":
                results = self._get_recycle_indicator_history(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'recycle_indicator_history': results,
                })
            elif type == "buffet":
                results = self._get_buffet_indicator_history(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'buffet_indicator_history': results,
                })
            elif type == "bathroom":
                results = self._get_bathroom_monitoring_history(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'bathroom_indicator_history': results,
                })
            else:
                results = self._get_kitchen_violation_report(tent, request)
                data.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    'kitchen_violation_list': results,
                })

        return Response(
            {
                "success": True,
                "message": "Averages retrieved successfully for all water tanks.",
                "data": data
            },
            status=status.HTTP_200_OK
        )

    def _get_clean_indicator_history(self, tent, request):
        cameras = tent.camera.filter(type="clean")
        # print(cameras)
        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.clean_indicator_histories.order_by(
                '-created_at').first()

            if data is None:
                continue

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)

            # print("clean histroy data:", data.image)
            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "is_clean": data.is_clean if data else None,
                "last_created_at": data.created_at if data else None,
                "image": image_url if data and data.image else None,
                "data_id": data.id,
                "created_at": data.created_at
            })
        return results

    def _get_garbage_indicator_history(self, tent, request):
        cameras = tent.camera.filter(type="garbage")
        # print(cameras)
        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.garbage_monitoring_histories.order_by(
                '-created_at').first()

            if data is None:
                continue

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)

            # print("clean histroy data:", data.image)
            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "is_clean": data.is_clean if data else None,
                "last_created_at": data.created_at if data else None,
                "image": image_url if data and data.image else None,
                "data_id": data.id,
                "created_at": data.created_at
            })
        return results

    def _get_recycle_indicator_history(self, tent, request):
        cameras = tent.camera.filter(type="recycle")
        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.recycle_monitoring_histories.order_by(
                '-created_at').first()

            if data is None:
                continue

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)

            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "is_clean": data.is_clean if data else None,
                "last_created_at": data.created_at if data else None,
                "image": image_url if data and data.image else None,
                "data_id": data.id,
                "created_at": data.created_at
            })
        return results

    def _get_guard_presence_history(self, tent, request):
        cameras = tent.camera.filter(type="guard")

        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.guard_presence_histories.order_by(
                '-created_at').first()

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)

            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "present": data.present if data else None,
                "last_created_at": data.created_at if data else None,
                "image": image_url if data and data.image else None,
                "data_id": data.id if data else None,
                "created_at": data.created_at if data else None
            })
        return results

    def _get_kitchen_violation_report(self, tent, request):
        cameras = tent.camera.filter(type="kitchen")

        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.kitchen_violation_histories.order_by(
                '-created_at').first()

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)
            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "image": image_url if data and data.image else None,
                "violation": data.violation if data else None,
                "violation_list": data.violation_list if data else None,
            })
        return results

    def _get_buffet_indicator_history(self, tent, request):
        cameras = tent.camera.filter(type="buffet")

        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.buffet_violation_histories.order_by(
                '-created_at').first()

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)
            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "image": image_url if data and data.image else None,
                "violation": data.violation if data else None,
                "violation_list": data.violation_list if data else None,
            })
        return results

    def _get_bathroom_monitoring_history(self, tent, request):
        cameras = tent.camera.filter(type="bathroom")

        if not cameras.exists():
            return []
        results = []
        for camera in cameras:
            data = camera.bathroom_monitoring_histories.order_by(
                '-created_at').first()

            image_url = None
            if data and data.image:
                image_url = request.build_absolute_uri(data.image.url)

            results.append({
                "camera_id": camera.id,
                "camera_sn": camera.sn,
                "camera_type": camera.type,
                "present": data.present if data else None,
                "last_created_at": data.created_at if data else None,
                "image": image_url if data and data.image else None,
                "data_id": data.id if data else None,
                "created_at": data.created_at if data else None
            })
        return results


@method_decorator(csrf_exempt, name='dispatch')
class TentsWaterTankUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"error": "No CSV file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Decode and read CSV
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
        except Exception as e:
            return Response({"error": f"Failed to read CSV file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        errors = []

        for idx, row in enumerate(reader, start=1):
            tent_name = row.get('tent_name')  # or tent name if you prefer
            tank_number = row.get('tank_number')
            sensor_sn = row.get('sensor_sn')

            if not tent_name or not tank_number:
                errors.append(f"Row {idx}: Missing tent_name or tank_number.")
                continue
            # TODO
            try:
                tent = Tent.objects.get(name=tent_name)
            except Tent.DoesNotExist:
                errors.append(
                    f"Row {idx}: Tent with ID {tent_name} does not exist.")
                continue

            try:
                TentsWaterTank.objects.create(
                    tent=tent,
                    tank_number=tank_number,
                    sensor_sn=sensor_sn
                )
                created += 1
            except Exception as e:
                errors.append(
                    f"Row {idx}: Failed to create TentsWaterTank - {str(e)}")

        return Response({
            "success": True,
            "message": f"{created} records created successfully.",
            "errors": errors
        }, status=status.HTTP_201_CREATED)


class TentsWaterTankSampleCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Prepare CSV content
        csv_content = "tent_name,tank_number,sensor_sn\n"
        csv_content += "TENT001,TANK001,SENSOR001\n"
        csv_content += "TENT002,TANK002,SENSOR002\n"

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_tents_water_tank.csv"'
        return response


class TentUploadView(APIView):
    # permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get('csv')
        if not csv_file:
            return Response({"error": "No CSV file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Decode and read CSV
        try:
            csv_data = pd.read_csv(io.StringIO(
                csv_file.read().decode('latin-1')))
        except Exception as e:
            return Response({"error": f"Failed to read CSV file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        data_as_list_of_dicts = []
        for _, row in csv_data.iterrows():
            data_as_list_of_dicts.append({
                'name': row.get('name', '').strip(),
                'latitude': row.get('latitude', ''),
                'longitude': row.get('longitude', ''),
                'location': row.get('location', '').strip()
            })

        created_count = 0
        errors = []

        for value in data_as_list_of_dicts:
            if not pd.isna(value['name']) and not pd.isna(value['latitude']) and not pd.isna(value['longitude']):
                try:
                    tent = Tent.objects.filter(name=value['name']).first()
                    if tent:
                        errors.append(
                            f"Tent with name '{value['name']}' already exists.")
                        continue
                    Tent.objects.create(
                        name=value['name'],
                        latitude=value['latitude'],
                        longitude=value['longitude'],
                        location=value['location']
                    )
                    created_count += 1
                except Exception as e:
                    errors.append(
                        f"Failed to create tent '{value['name']}': {str(e)}")

        return Response({
            "success": True,
            "message": f"{created_count} tents created successfully.",
            "errors": errors
        }, status=status.HTTP_201_CREATED)


class TentSampleCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Prepare CSV content
        csv_content = "name,longitude,latitude,location\n"
        csv_content += "Tent 1,10.123,20.456,Location 1\n"
        csv_content += "Tent 2,30.789,40.012,Location 2\n"

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_tent.csv"'
        return response


class FilterTentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list")

        user = request.user

        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

        # Filter by nationality if it's not 'all'
        if nationality and nationality.lower() != "all":
            tents = tents.filter(nationality__id__in=nationality)

        # Only return id and name
        tent_data = tents.values('id', 'name')
        data = {
            "success": True,
            "message": "Tents filtered successfully.",
            "data": list(tent_data)
        }
        return Response(data, status=status.HTTP_200_OK)


class DashboardKitchen(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__kitchen_violation_histories',
                filter=Q(
                    camera__type='kitchen',
                    camera__kitchen_violation_histories__created_at__range=(start_date_time, end_date_time),
                    camera__kitchen_violation_histories__violation=True,
                    camera__kitchen_violation_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='kitchen')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Kitchen Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardGarbage(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__garbage_monitoring_histories',
                filter=Q(
                    camera__type='garbage',
                    camera__garbage_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__garbage_monitoring_histories__is_clean=False,
                    camera__garbage_monitoring_histories__is_annotated=True,
                    camera__garbage_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='garbage')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Kitchen Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardRecycle(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user
        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return make_aware(dt) if not is_aware(dt) else dt
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__recycle_monitoring_histories',
                filter=Q(
                    camera__type='recycle',
                    camera__recycle_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__recycle_monitoring_histories__is_clean=False,
                    camera__recycle_monitoring_histories__is_annotated=True,
                    camera__recycle_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='recycle')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Recycle Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardSecurity(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user
        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return make_aware(dt) if not is_aware(dt) else dt
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__security_monitoring_histories',
                filter=Q(
                    camera__type='security',
                    camera__security_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__security_monitoring_histories__is_safe=False,
                    camera__security_monitoring_histories__is_annotated=True,
                    camera__security_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='security')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Security Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardFallDetection(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user

        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [
                    int(x) for x in nationality_param.split(',')
                    if x.strip().isdigit()
                ]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [
                    int(tid) for tid in tent_list.split(',')
                    if tid.strip().isdigit()
                ]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')
            ) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')
            ) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__fall_detection_monitoring_histories',
                filter=Q(
                    camera__type='falldetection',
                    camera__fall_detection_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__fall_detection_monitoring_histories__is_fall_detected=True,
                    camera__fall_detection_monitoring_histories__is_annotated=True,
                    camera__fall_detection_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='falldetection')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))

        return Response({
            "success": True,
            "message": "Dashboard Fall Detection Data",
            "results": results
        }, status=status.HTTP_200_OK)
        
        
class DashboardViolenceMonitoring(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user

        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [
                    int(x) for x in nationality_param.split(',')
                    if x.strip().isdigit()
                ]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [
                    int(tid) for tid in tent_list.split(',')
                    if tid.strip().isdigit()
                ]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')
            ) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')
            ) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__violence_monitoring_histories',
                filter=Q(
                    camera__type='violence',
                    camera__violence_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__violence_monitoring_histories__is_violence=True,
                    camera__violence_monitoring_histories__is_annotated=True,
                    camera__violence_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='violence')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))

        return Response({
            "success": True,
            "message": "Dashboard Violence Monitoring Data",
            "results": results
        }, status=status.HTTP_200_OK)

class DashboardCrowdMonitoring(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user

        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [
                    int(x) for x in nationality_param.split(',')
                    if x.strip().isdigit()
                ]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [
                    int(tid) for tid in tent_list.split(',')
                    if tid.strip().isdigit()
                ]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')
            ) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')
            ) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__crowd_monitoring_histories',
                filter=Q(
                    camera__type='crowdmonitoring',
                    camera__crowd_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__crowd_monitoring_histories__is_crowd=True,
                    camera__crowd_monitoring_histories__is_annotated=True,
                    camera__crowd_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='crowdmonitoring')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))

        return Response({
            "success": True,
            "message": "Dashboard Crowd Monitoring Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardChairDetection(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        tent_list = request.GET.get("tent_list", None)
        user = request.user

        tents = Tent.objects.filter(is_arafa=is_arafa)

        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

        tents = tents.annotate(
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='chairdetection')
            )
        )

        tent_ids_list = list(tents.values_list('id', flat=True))

        latest_empty_sq = EmptyChairDetectionReport.objects.filter(
            camera=OuterRef('pk')
        ).order_by('-start_time').values('empty_chair_count')[:1]

        latest_total_sq = EmptyChairDetectionReport.objects.filter(
            camera=OuterRef('pk')
        ).order_by('-start_time').values('total_chair_count')[:1]

        cam_qs = Camera.objects.filter(
            tent_id__in=tent_ids_list, type='chairdetection'
        ).annotate(
            lat_empty=Coalesce(Subquery(latest_empty_sq, output_field=IntegerField()), 0),
            lat_total=Coalesce(Subquery(latest_total_sq, output_field=IntegerField()), 0),
        ).values('tent_id', 'lat_empty', 'lat_total')

        chairs_per_tent = {}
        for cam in cam_qs:
            t_id = cam['tent_id']
            if t_id not in chairs_per_tent:
                chairs_per_tent[t_id] = {'empty': 0, 'total': 0}
            chairs_per_tent[t_id]['empty'] += cam['lat_empty']
            chairs_per_tent[t_id]['total'] += cam['lat_total']

        results = []
        for t in tents.values('id', 'name', 'is_sensor_available'):
            chair_data = chairs_per_tent.get(t['id'], {'empty': 0, 'total': 0})
            results.append({
                "tent_id": t['id'],
                "tent_name": t['name'],
                "empty_chair_count": chair_data['empty'],
                "total_chair_count": chair_data['total'],
                "is_sensor_available": t['is_sensor_available'],
            })

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))

        return Response({
            "success": True,
            "message": "Dashboard Chair Detection Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardClimbMonitoring(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user

        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [
                    int(x) for x in nationality_param.split(',')
                    if x.strip().isdigit()
                ]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [
                    int(tid) for tid in tent_list.split(',')
                    if tid.strip().isdigit()
                ]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')
            ) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')
            ) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__wall_climb_monitoring_histories',
                filter=Q(
                    camera__type='climbmonitoring',
                    camera__wall_climb_monitoring_histories__created_at__range=(start_date_time, end_date_time),
                    camera__wall_climb_monitoring_histories__is_climb=True,
                    camera__wall_climb_monitoring_histories__is_annotated=True,
                    camera__wall_climb_monitoring_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='climbmonitoring')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))

        return Response({
            "success": True,
            "message": "Dashboard Wall Climb Monitoring Data",
            "results": results
        }, status=status.HTTP_200_OK)
        

class DashboardAbnormalActivity(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user

        tents = Tent.objects.filter(is_arafa=is_arafa)

        if nationality_param.lower() != "all":
            try:
                nationality_ids = [
                    int(x) for x in nationality_param.split(',')
                    if x.strip().isdigit()
                ]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []

        if tent_list:
            try:
                tent_ids = [
                    int(tid) for tid in tent_list.split(',')
                    if tid.strip().isdigit()
                ]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')
            ) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')
            ) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__abnormal_activity_histories',
                filter=Q(
                    camera__type='abnormalactivity',
                    camera__abnormal_activity_histories__created_at__range=(start_date_time, end_date_time),
                    camera__abnormal_activity_histories__is_motion_detected=True,
                    camera__abnormal_activity_histories__is_annotated=True,
                    camera__abnormal_activity_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='abnormalactivity')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))

        return Response({
            "success": True,
            "message": "Dashboard Abnormal Activities Monitoring Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardBuffet(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        tents = tents.annotate(
            violation_count=Count(
                'camera__buffet_violation_histories',
                filter=Q(
                    camera__type='buffet',
                    camera__buffet_violation_histories__created_at__range=(start_date_time, end_date_time),
                    camera__buffet_violation_histories__violation=True,
                    camera__buffet_violation_histories__is_annotated=True,
                    camera__buffet_violation_histories__is_rejected=False,
                )
            ),
            is_sensor_available=Exists(
                Camera.objects.filter(tent=OuterRef('pk'), type='buffet')
            )
        )

        results = [
            {
                "tent_id": t['id'],
                "tent_name": t['name'],
                "violation_count": t['violation_count'],
                "indicator": "red" if t['violation_count'] > 0 else "green",
                "is_sensor_available": t['is_sensor_available'],
            }
            for t in tents.values('id', 'name', 'violation_count', 'is_sensor_available')
        ]

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Buffet Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardFood(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)

        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        result_list = []

        for tent in tents:
            weight_sensors = EnvironmentSensor.objects.filter(
                tent=tent, type="weight")

            if not weight_sensors.exists():
                result_list.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    "capacity": tent.capacity,
                    "breakfast_rejected_meals": 0,
                    "lunch_rejected_meals": 0,
                    "dinner_rejected_meals": 0,
                    "total_breakfast_meals": 0,
                    "total_lunch_meals": 0,
                    "total_dinner_meals": 0,
                    "breakfast_indicator": 'red',
                    "lunch_indicator": 'red',
                    "dinner_indicator": 'red',
                    "indicator": 'red',
                    "is_sensor_available": False

                })
                continue

            tent_food_weights = OrderWeight.objects.filter(
                weight_sensor__tent=tent,
                date__range=(start_date_time, end_date_time),
                weight__gte=0
            )

            if not tent_food_weights.exists():
                result_list.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    "capacity": tent.capacity,
                    "breakfast_rejected_meals": 0,
                    "lunch_rejected_meals": 0,
                    "dinner_rejected_meals": 0,
                    "total_breakfast_meals": 0,
                    "total_lunch_meals": 0,
                    "total_dinner_meals": 0,
                    "breakfast_indicator": 'red',
                    "lunch_indicator": 'red',
                    "dinner_indicator": 'red',
                    "indicator": 'red',
                    "is_sensor_available": True
                })
                continue

            weight_condition = (
                WeightConditions.objects.filter(start_date__date__lte=start_date_time.date(
                ), end_date__date__gte=start_date_time.date()).first()
                or WeightConditions.objects.filter(end_date__date__lte=start_date_time.date()).order_by('-end_date').first()
                or WeightConditions.objects.filter(start_date__date__gte=start_date_time.date()).order_by('start_date').first()
            )

            if not weight_condition:
                result_list.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    "capacity": tent.capacity,
                    "breakfast_rejected_meals": 0,
                    "lunch_rejected_meals": 0,
                    "dinner_rejected_meals": 0,
                    "total_breakfast_meals": 0,
                    "total_lunch_meals": 0,
                    "total_dinner_meals": 0,
                    "breakfast_indicator": 'red',
                    "lunch_indicator": 'red',
                    "dinner_indicator": 'red',
                    "indicator": 'red',
                    "is_sensor_available": True
                })
                continue

            # Meal timing and thresholds
            b_start, b_end, b_thresh = weight_condition.breakfast_start, weight_condition.breakfast_end, weight_condition.breakfast_weight_accepted
            l_start, l_end, l_thresh = weight_condition.lunch_start, weight_condition.lunch_end, weight_condition.lunch_weight_accepted
            d_start, d_end, d_thresh = weight_condition.dinner_start, weight_condition.dinner_end, weight_condition.dinner_weight_accepted

            stats = {
                'breakfast': {'accepted': 0, 'rejected': 0},
                'lunch': {'accepted': 0, 'rejected': 0},
                'dinner': {'accepted': 0, 'rejected': 0},
            }

            for weight in tent_food_weights:
                record_time = localtime(weight.date).time()
                w = weight.weight

                if b_start <= record_time <= b_end:
                    if w >= b_thresh:
                        stats['breakfast']['accepted'] += 1
                    else:
                        stats['breakfast']['rejected'] += 1
                elif l_start <= record_time <= l_end:
                    if w >= l_thresh:
                        stats['lunch']['accepted'] += 1
                    else:
                        stats['lunch']['rejected'] += 1
                elif d_start <= record_time <= d_end:
                    if w >= d_thresh:
                        stats['dinner']['accepted'] += 1
                    else:
                        stats['dinner']['rejected'] += 1
            capacity = tent.capacity
            total_breakfast_meals = stats['breakfast']['accepted'] + \
                stats['breakfast']['rejected']
            total_lunch_meals = stats['lunch']['accepted'] + \
                stats['lunch']['rejected']
            total_dinner_meals = stats['dinner']['accepted'] + \
                stats['dinner']['rejected']

            indicator = "red" if (
                total_breakfast_meals < 0.75 * capacity or
                total_lunch_meals < 0.75 * capacity or
                total_dinner_meals < 0.75 * capacity
            ) else "green"
            result_list.append({
                "tent_id": tent.id,
                "tent_name": tent.name,
                "capacity": capacity,
                "breakfast_rejected_meals": stats['breakfast']['rejected'],
                "lunch_rejected_meals": stats['lunch']['rejected'],
                "dinner_rejected_meals": stats['dinner']['rejected'],
                "total_breakfast_meals": total_breakfast_meals,
                "total_lunch_meals": total_lunch_meals,
                "total_dinner_meals": total_dinner_meals,
                "breakfast_indicator": "red" if stats['breakfast']['rejected'] > 25 else "green",
                "lunch_indicator": "red" if stats['lunch']['rejected'] > 25 else "green",
                "dinner_indicator": "red" if stats['dinner']['rejected'] > 25 else "green",
                "indicator": indicator,
                "is_sensor_available": True
            })

        result_list.sort(
            key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Kitchen Data",
            "results": result_list
        }, status=status.HTTP_200_OK)


class DashboardGuard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)

        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)
        current_guard_state = None

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        all_tent_data = []

        for tent in tents:
            guard_camera = Camera.objects.filter(
                tent=tent, type="guard").first()

            history_qs = GuardPresenceHistory.objects.filter(
                camera=guard_camera,
                start_time__gte=start_date_time,
                end_time__lte=end_date_time,
                is_rejected=False
            ).order_by('start_time')

            is_sensor_available = guard_camera is not None

            if history_qs:
                last_instance = history_qs.last()
                current_guards = last_instance.guard_count or 0

                current_guard_state = False if current_guards == 0 else True
            else:
                current_guards = 0
                current_guard_state = False

            no_show_time = 0  #
            no_show_count = 0  #
            count_duration = 0
            total_duration = 0
            inside_zero_block = False
            last_end_time = None
            not_present_list = []
            for entry in history_qs:
                if entry.start_time and entry.end_time:
                    duration = (entry.end_time -
                                entry.start_time).total_seconds() / 60.0
                    total_duration += duration
                if not entry.present and entry.start_time and entry.end_time:
                    not_present_list.append({
                        "start_time": convert_utc_to_riyadh(entry.start_time),
                        "end_time": convert_utc_to_riyadh(entry.end_time),
                        "duration": duration
                    })
                    if last_end_time:
                        time_gap = (entry.start_time -
                                    last_end_time).total_seconds()
                        if time_gap > 119:  # if the gap is less than 5 seconds119time_gap < 900:  # if the gap is more than 5 seconds
                            count_duration = 0  # reset

                    count_duration += duration
                    if count_duration > 5.0:
                        inside_zero_block = True

                    last_end_time = entry.end_time  # update last_end_time

                else:
                    if inside_zero_block:
                        no_show_count += 1
                        no_show_time += count_duration
                    count_duration = 0
                    last_end_time = None
                    inside_zero_block = False

            if inside_zero_block:
                no_show_count += 1
                no_show_time += count_duration

            # total_duration = int(
            #     (end_date_time - start_date_time).total_seconds() / 60)
            available_minutes = max(total_duration - no_show_time, 0)
            available_percentage = round(
                (available_minutes / total_duration) * 100, 2) if total_duration > 0 else 0.0

            # Build response
            tent_data = {
                "tent_id": tent.id,
                "tent_name": tent.name,
                "present_percentage": available_percentage,
                "is_available": current_guard_state,
                "indicator": "green" if available_percentage >= 97.0 else "red",
                "is_sensor_available": is_sensor_available,
                "no_show_time": no_show_time,
                "no_show_count": no_show_count,
                "total_duration": total_duration,
                "start_date_time": start_date_time,
                "end_date_time": end_date_time,
                "current_guards": current_guards,
                "current_guard_state": current_guard_state,
                "available_percentage": available_percentage,
                "not_present_list": not_present_list
            }

            all_tent_data.append(tent_data)
        all_tent_data.sort(
            key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Guard Data",
            "results": all_tent_data
        }, status=status.HTTP_200_OK)


class DashboardCleaner(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)

        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == 'true'

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        all_tent_data = []

        for tent in tents:
            guard_camera = Camera.objects.filter(
                tent=tent, type="cleaners").first()

            is_sensor_available = False
            if guard_camera:
                is_sensor_available = True

            # Group by time window, summing cleaner_count across all person classes
            history_qs = (
                CleanersPresenceHistory.objects.filter(
                    camera=guard_camera,
                    start_time__gte=start_date_time,
                    end_time__lte=end_date_time,
                    is_rejected=False,
                )
                .values('start_time', 'end_time')
                .annotate(total_count=Sum('cleaner_count'))
                .order_by('start_time')
            )

            if history_qs:
                last_instance = history_qs.last()
                current_guards = last_instance['total_count'] or 0
                current_guard_state = current_guards > 0
            else:
                current_guards = 0
                current_guard_state = False

            no_show_time = 0  # in total unavailable minutes
            count_duration = 0
            last_end_time = None  # track the end time of the previous entry

            for entry in history_qs:
                if entry['total_count'] == 0 and entry['start_time'] and entry['end_time']:
                    # duration in minutes
                    duration = (entry['end_time'] -
                                entry['start_time']).total_seconds() / 60.0

                    if last_end_time:
                        time_gap = (entry['start_time'] -
                                    last_end_time).total_seconds()
                        if time_gap > 5:  # if the gap is more than 5 seconds
                            count_duration = 0  # reset

                    count_duration += duration
                    if count_duration > 5.0:
                        no_show_time += int(duration)
                        count_duration = 0

                    last_end_time = entry['end_time']

                else:
                    count_duration = 0
                    last_end_time = None

            total_duration = int(
                (end_date_time - start_date_time).total_seconds() / 60)
            available_minutes = max(total_duration - no_show_time, 0)
            available_percentage = round(
                (available_minutes / total_duration) * 100, 2) if total_duration > 0 else 0.0

            # Build response
            tent_data = {
                "tent_id": tent.id,
                "tent_name": tent.name,
                "present_percentage": round(available_percentage, 2),
                "is_available": current_guard_state,
                "indicator": "green" if available_percentage >= 97.0 else "red",
                "is_sensor_available": is_sensor_available
            }

            all_tent_data.append(tent_data)
        all_tent_data.sort(
            key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Guard Data",
            "results": all_tent_data
        }, status=status.HTTP_200_OK)


# class DashboardCounter(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         # GET parameters with defaults and normalization
#         is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
#         nationality_param = request.GET.get("nationality", "all")
#         tent_list = request.GET.get("tent_list", None)

#         user = request.user
#         # Base queryset
#         tents = Tent.objects.filter(is_arafa=is_arafa)

#         # Parse nationality filter
#         if nationality_param.lower() != "all":
#             try:
#                 nationality_ids = [int(x) for x in nationality_param.split(
#                     ',') if x.strip().isdigit()]
#             except ValueError:
#                 return Response({"detail": "Invalid nationality list."}, status=400)
#         else:
#             nationality_ids = []
#         # Filter by tent_list if provided
#         if tent_list:
#             try:
#                 tent_ids = [int(tid) for tid in tent_list.split(
#                     ',') if tid.strip().isdigit()]
#                 tents = tents.filter(id__in=tent_ids)
#             except ValueError:
#                 return Response({"detail": "Invalid tent_id list."}, status=400)
#         else:
#             if user.is_admin:
#                 tents = tents.filter(company=user.company)
#             else:
#                 assigned_ids = user.assigned_tent.values_list('id', flat=True)
#                 tents = tents.filter(id__in=assigned_ids, company=user.company)
#             # Filter by nationality if it's not 'all'
#             if nationality_ids:
#                 tents = tents.filter(nationality__id__in=nationality_ids)

#         def get_aware_datetime_from_str(date_str):
#             if not date_str:
#                 return None
#             dt = parse_datetime(date_str)
#             if dt is not None:
#                 return date_time_to_aware(dt)
#             return None

#         is_live = request.GET.get('is_live', 'false').lower() == 'true'

#         if is_live:
#             start_date_time, end_date_time = Current_saudi_time()
#         else:
#             start_date_time = get_aware_datetime_from_str(
#                 request.GET.get('start_date_time')) or timezone.now()
#             end_date_time = get_aware_datetime_from_str(
#                 request.GET.get('end_date_time')) or timezone.now()

#         results = []
#         for tent in tents:

#             counter_cameras = Camera.objects.filter(
#                 tent=tent, type="peoplecount")

#             is_sensor_available = False
#             if counter_cameras.exists():
#                 is_sensor_available = True

#             filtered_entries = CounterHistory.objects.filter(
#                 camera__in=counter_cameras,
#                 end_time__lte=end_date_time
#             )
#             total_in = filtered_entries.aggregate(
#                 total=Sum('total_in'))['total'] or 0
#             total_out = filtered_entries.aggregate(
#                 total=Sum('total_out'))['total'] or 0
#             total_people = 0 if total_in < total_out else total_in - total_out
#             indicator = "green"
#             if total_people > tent.capacity:
#                 indicator = "red"

#             results.append({
#                 "tent_id": tent.id,
#                 "tent_name": tent.name,
#                 "capacity": tent.capacity,
#                 "total_people": total_people,
#                 "indicator": indicator,
#                 "is_sensor_available": is_sensor_available
#             })

#         results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
#         return Response({
#             "success": True,
#             "message": "Dashboard Counter Data",
#             "results": results
#         }, status=status.HTTP_200_OK)


class DashboardCounter(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Standard parameter parsing
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        user = request.user
        
        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        # 2. Base QuerySet
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # 3. Filter Logic (Unchanged)
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(',') if x.strip().isdigit()]
                tents = tents.filter(nationality__id__in=nationality_ids)
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

        # 4. Date Logic
        is_live = request.GET.get('is_live', 'false').lower() == 'true'
        if is_live:
            HAJJ_START_DATE = date(2026, 5, 26)
            now_saudi = timezone.now().astimezone(saudi_tz)
            start_date_time = saudi_tz.localize(datetime.combine(HAJJ_START_DATE, time(7,0,0)))
            end_date_time = now_saudi
        else:
            start_date_time = get_aware_datetime_from_str(request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(request.GET.get('end_date_time')) or timezone.now()

        # 5. Query 1 — all peoplecount cameras for these tents
        all_cameras = (
            Camera.objects
            .filter(type="peoplecount", tent__in=tents)
            .select_related('tent', 'gate')
        )

        # Which tents actually have a peoplecount camera
        tents_with_sensor = set(all_cameras.values_list('tent_id', flat=True))

        # Query 2 — all records in the date range
        all_records = (
            CounterHistory.objects
            .filter(
                camera__in=all_cameras,
                created_at__gte=start_date_time,
                created_at__lte=end_date_time,
            )
            .only('camera_id', 'total_in', 'total_out', 'created_at')
        )

        # Build cam_id → tent_id and cam_id → gate_key maps
        cam_to_tent = {c.id: c.tent_id for c in all_cameras}
        cam_to_gate = {c.id: (c.gate_id if c.gate_id else 'default') for c in all_cameras}

        BUCKET_SECS = 300  # 5 minutes
        # tent_id → gate_key → bucket_idx → cam_id → [in, out]
        tent_gate_buckets = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

        for rec in all_records:
            if not rec.created_at:
                continue
            tid = cam_to_tent.get(rec.camera_id)
            if not tid:
                continue
            gk       = cam_to_gate.get(rec.camera_id)
            delta    = (rec.created_at - start_date_time).total_seconds()
            buck_idx = int(delta // BUCKET_SECS)
            if rec.camera_id not in tent_gate_buckets[tid][gk][buck_idx]:
                tent_gate_buckets[tid][gk][buck_idx][rec.camera_id] = [0, 0]
            tent_gate_buckets[tid][gk][buck_idx][rec.camera_id][0] += rec.total_in
            tent_gate_buckets[tid][gk][buck_idx][rec.camera_id][1] += rec.total_out

        # 6. Assembly Loop — smart_aggregate within each gate, sum across gates
        results = []
        for tent in tents:
            total_in  = 0
            total_out = 0

            for gate_buckets in tent_gate_buckets[tent.id].values():
                for cam_totals in gate_buckets.values():
                    in_values  = [v[0] for v in cam_totals.values()]
                    out_values = [v[1] for v in cam_totals.values()]
                    total_in  += smart_aggregate(in_values)
                    total_out += smart_aggregate(out_values)

            total_people = max(total_in - total_out, 0)
            indicator    = "red" if total_people > tent.capacity else "green"

            results.append({
                "tent_id":            tent.id,
                "tent_name":          tent.name,
                "capacity":           tent.capacity,
                "total_people":       total_people,
                "indicator":          indicator,
                "is_sensor_available": tent.id in tents_with_sensor,
            })

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        
        return Response({
            "success": True,
            "message": "Dashboard Counter Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardSensor(APIView):
    permission_classes = [IsAuthenticated, TemperaturePermission]

    def get(self, request):
        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        def round_half_up(value):
            if value is None:
                return None
            return math.floor(value + 0.5)
        user = request.user

        # Parse query parameters
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)
        is_live = request.GET.get("is_live", "false").lower() == "true"

        # Filter tents
        tents = Tent.objects.filter(is_arafa=is_arafa)

        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)

        # Filter by nationality if needed
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
                tents = tents.filter(nationality__id__in=nationality_ids)
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)

        # Define time range
        if is_live:

            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or None
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or None
            if start_date_time and end_date_time and start_date_time > end_date_time:
                return standard_response_api(
                    success=False,
                    message='Invalid date range.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        results = []

        for tent in tents:
            sensors = EnvironmentSensor.objects.filter(
                tent=tent,
                type="environment",
                tempareture__gt=0
            )

            sensors_available = EnvironmentSensor.objects.filter(
                tent=tent,
                type="environment"
            )

            is_sensor_available = False
            if sensors_available.exists():
                is_sensor_available = True

            exclude_conditions = (
                Q(location__icontains='Outside') |
                Q(location__icontains='kitchen') |
                Q(location__icontains='corridor')
            )
            if is_live:
                summary_data_raw = sensors.exclude(exclude_conditions).aggregate(
                    min_humidity=Min('humidity'),
                    max_humidity=Max('humidity'),
                    avg_humidity=Avg('humidity'),
                    min_temperature=Min(F('tempareture')),
                    max_temperature=Max(F('tempareture')),
                    avg_temperature=Avg(F('tempareture')),)
                # Apply rounding
                summary_data = {
                    key: round_half_up(value)
                    for key, value in summary_data_raw.items()
                }
                results.append({
                    "tent_id": tent.id,
                    "tent_name": tent.name,
                    "min_hum": summary_data['min_humidity'] if summary_data['min_humidity'] is not None else 0,
                    "max_hum": summary_data['max_humidity'] if summary_data['max_humidity'] is not None else 0,
                    "avg_hum": summary_data['avg_humidity'] if summary_data['avg_humidity'] is not None else 0,
                    "min_temp": summary_data['min_temperature'] if summary_data['min_temperature'] is not None else 0,
                    "max_temp": summary_data['max_temperature'] if summary_data['max_temperature'] is not None else 0,
                    "ave_temp": summary_data['avg_temperature'] if summary_data['avg_temperature'] is not None else 0,
                    "indicator": "green" if summary_data['avg_temperature'] is not None and summary_data['avg_temperature'] < 38.0 else "red",
                    "last_updated": convert_utc_to_riyadh(timezone.now()),
                    "is_sensor_available": is_sensor_available

                })
            else:
                max_temp = float('-inf')
                min_temp = float('inf')
                max_hum = float('-inf')
                min_hum = float('inf')
                total_temp = 0
                total_hum = 0
                valid_count = 0
                last_updated = None
                for sensor in sensors:
                    record = EnvironmentSensorRecord.objects.filter(
                        sensor=sensor,
                        last_entry_time__range=(start_date_time, end_date_time)
                    ).order_by('-created_at').first()
                    if record and record.tempareture is not None:
                        temp = record.tempareture
                        hum = record.humidity
                        max_temp = max(max_temp, temp)
                        min_temp = min(min_temp, temp)
                        max_hum = max(max_hum, hum)
                        min_hum = min(min_hum, hum)
                        total_temp += temp
                        total_hum += hum
                        valid_count += 1
                        if not last_updated or record.last_entry_time > last_updated:
                            last_updated = record.last_entry_time

                if valid_count > 0:
                    ave_temp = total_temp / valid_count
                    ave_hum = total_hum / valid_count
                else:
                    max_temp = min_temp = ave_temp = 0
                    max_hum = min_hum = ave_hum = 0

                indicator = "green"
                if ave_temp > 38.0:
                    indicator = "red"

                results.append({
                    "tent_id": tent.id,
                    "is_sensor_available": is_sensor_available,
                    "tent_name": tent.name,
                    "max_temp": round_half_up(max_temp),
                    "min_temp": round_half_up(min_temp),
                    "ave_temp": round_half_up(ave_temp),
                    "max_hum": round_half_up(max_hum),
                    "min_hum": round_half_up(min_hum),
                    "avg_hum": round_half_up(ave_hum),
                    "indicator": indicator,
                    "last_updated": convert_utc_to_riyadh(last_updated) if last_updated else last_updated
                })

        results.sort(key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({
            "success": True,
            "message": "Dashboard Sensor Data",
            "results": results
        }, status=status.HTTP_200_OK)


class DashboardSentiment(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # GET parameters with defaults and normalization
        is_arafa = request.GET.get("is_arafa", "false").lower() == "true"
        nationality_param = request.GET.get("nationality", "all")
        tent_list = request.GET.get("tent_list", None)

        user = request.user
        # Base queryset
        tents = Tent.objects.filter(is_arafa=is_arafa)

        # Parse nationality filter
        if nationality_param.lower() != "all":
            try:
                nationality_ids = [int(x) for x in nationality_param.split(
                    ',') if x.strip().isdigit()]
            except ValueError:
                return Response({"detail": "Invalid nationality list."}, status=400)
        else:
            nationality_ids = []
        # Filter by tent_list if provided
        if tent_list:
            try:
                tent_ids = [int(tid) for tid in tent_list.split(
                    ',') if tid.strip().isdigit()]
                tents = tents.filter(id__in=tent_ids)
            except ValueError:
                return Response({"detail": "Invalid tent_id list."}, status=400)
        else:
            if user.is_admin:
                tents = tents.filter(company=user.company)
            else:
                assigned_ids = user.assigned_tent.values_list('id', flat=True)
                tents = tents.filter(id__in=assigned_ids, company=user.company)
            # Filter by nationality if it's not 'all'
            if nationality_ids:
                tents = tents.filter(nationality__id__in=nationality_ids)

        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None

        is_live = request.GET.get('is_live', 'false').lower() == "true"

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        data = []
        for tent in tents:

            sentiment_cameras = tent.camera.filter(type='sentiment')
            is_sensor_available = sentiment_cameras.exists()

            # print(SentimentAnalysis.objects.filter(
            #     camera__in=sentiment_cameras, average_sentiment__gte=0, end_time__range=(start_date_time, end_date_time),is_annotated=True, ).count())

            sentiment_list = SentimentAnalysis.objects.filter(
                camera__in=sentiment_cameras,
                end_time__range=(start_date_time, end_date_time),
                is_annotated=True,
                is_rejected=False
            )

            happy_faces   = 0
            neutral_faces = 0
            sad_faces     = 0

            for sentiment in sentiment_list:
                if sentiment.annotator_status and isinstance(sentiment.annotator_status, list):
                    labels = set(sentiment.annotator_status)
                    if 'happy' in labels:
                        happy_faces += 1
                    elif 'neutral' in labels and 'sad' not in labels:
                        neutral_faces += 1
                    elif 'sad' in labels:
                        sad_faces += 1

            total_person = happy_faces + neutral_faces + sad_faces
            if total_person > 0:
                weighted_score = (happy_faces * 100) + (neutral_faces * 95) + (sad_faces * 0)
                ave_sentiment  = round(weighted_score / (total_person * 100), 4)
            else:
                ave_sentiment = None

            data.append({
                "tent_id":         tent.id,
                "tent_name":       tent.name,
                "ave_sentiment":   ave_sentiment,
                "total_person":    total_person,
                "happy_faces":     happy_faces,
                "neutral_faces":   neutral_faces,
                "sad_faces":       sad_faces,
                "indicator":       "green",
                "is_sensor_available": is_sensor_available
            })
            data.sort(
                key=lambda x: tent_name_list_dict_sorting(x["tent_name"]))
        return Response({"success": True, "results": data, "message": "Dashboard sentiment Data", }, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class TentCreateFromServerView(APIView):
    def post(self, request, *args, **kwargs):
        header_key = request.headers.get('X-Secret-Key')
        if header_key != 'F[F4.+092]S-lZz':
            return Response({
                "success": False,
                "message": "Invalid secret key"
            }, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        company_name = data.get('company')

        company = Company.objects.filter(name__icontains=company_name).first()
        if not company:
            return Response({
                "success": False,
                "message": "Invalid company name"
            }, status=status.HTTP_400_BAD_REQUEST)

        data['company'] = company.id  # Set the actual FK ID
        serializer = CreateTentFromServerSerializer(
            data=data)  # <<< FIXED LINE
        if serializer.is_valid():
            serializer.save()
            data = {
                "success": True,
                "message": "Tent created successfully"
            }
            return Response(data, status=status.HTTP_201_CREATED)
        data = {
            "success": False,
            "message": "Invalid data",
            "errors": serializer.errors
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)
