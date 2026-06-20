from django.utils.dateparse import parse_date
from django.views.generic.base import View
from django.utils.datastructures import MultiValueDictKeyError
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
from django.db.models.functions import TruncMonth, TruncHour, TruncDay, TruncDate, ExtractMinute
from django.db.models import Func, Avg, Min, Max, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from dateutil.relativedelta import relativedelta

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import pytz
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

import io
import csv
import pandas as pd
from datetime import datetime, timedelta, time
from django.utils.timezone import make_aware, is_aware, localtime
from django.utils.dateparse import parse_datetime
from collections import defaultdict

from authentication.utils import standard_response_api
from tent.utils import generate_csv_response, CustomPagination
from tent.models import Tent

from sensor.models import EnvironmentSensor, EnvironmentSensorRecord, SensorLocation
from sensor.serializers import EnvironmentSensorSerializer, SensorLocationSerializer
from sensor.utils import check_arafat, get_string_before_dash

from authentication.utils import standard_response

from tent.utils import CustomPagination
from weight.utils import match_temperature_key

from utils.time import Current_saudi_time, convert_utc_to_riyadh


class Abs(Func):
    function = 'ABS'
    arity = 1

# need to implement later................


def date_time_to_aware(date_time):
    if not is_aware(date_time):
        date_time = make_aware(date_time)
    return date_time


class SensorLocationAPIView(APIView):
    def get(self, request, id=None):
        if id:
            location = get_object_or_404(SensorLocation, id=id)
            serializer = SensorLocationSerializer(location)
            data = {
                "success": True,
                "message": "Sensor location fetched successfully.",
                "results": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            locations = SensorLocation.objects.all()
            serializer = SensorLocationSerializer(locations, many=True)
            data = {
                "success": True,
                "message": "Sensor locations fetched successfully.",
                "results": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SensorLocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            locations = SensorLocation.objects.all()
            response_serializer = SensorLocationSerializer(
                locations, many=True)
            data = {
                "success": True,
                "message": "Sensor location created successfully.",
                "results": response_serializer.data
            }
            return Response(data, status=status.HTTP_201_CREATED)
        data = {
            "success": False,
            "message": "Sensor location creation failed.",
            "results": serializer.errors
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id=None):
        if not id:
            data = {
                "success": False,
                "message": "Method PATCH not allowed without ID."
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        location = get_object_or_404(SensorLocation, id=id)
        serializer = SensorLocationSerializer(
            location, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            data = {
                "success": True,
                "message": "Sensor location updated successfully.",
                "results": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)
        data = {
            "success": False,
            "message": "Sensor location update failed.",
            "results": serializer.errors
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None):
        if not id:
            data = {
                "success": False,
                "message": "Method DELETE not allowed without ID."
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        location = get_object_or_404(SensorLocation, id=id)
        location.delete()
        data = {
            "success": True,
            "message": "Sensor location deleted successfully."
        }
        return Response(data, status=status.HTTP_204_NO_CONTENT)


class EnvironmentSensorListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        paginate = request.query_params.get(
            'paginate', 'false').lower() == 'true'
        sensor_type = request.query_params.get('type', 'all').lower()

        sensor_qs = EnvironmentSensor.objects.select_related('tent')

        if user.is_admin:
            queryset = sensor_qs.filter(
                tent__company=user.company)
        elif user.is_superuser:
            queryset = sensor_qs.all()
        else:
            assigned_tent_ids = user.assigned_tent.values_list('id', flat=True)
            queryset = sensor_qs.filter(
                tent__id__in=assigned_tent_ids)

        if sensor_type != 'all':
            queryset = queryset.filter(type__iexact=sensor_type)

        queryset = queryset.order_by('id')

        if paginate:
            paginator = CustomPagination()
            page = paginator.paginate_queryset(queryset, request)
            serializer = EnvironmentSensorSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        else:
            serializer = EnvironmentSensorSerializer(queryset, many=True)
            return Response(
                {
                    "message": 'Environment Sensor list fetched successfully!',
                    "results": serializer.data,
                    "status": status.HTTP_200_OK
                }
            )

    def post(self, request):
        serializer = EnvironmentSensorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(*standard_response(True, 'Environment Sensor successfully created!', serializer.data, status.HTTP_201_CREATED))


class EnvironmentSensorDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(EnvironmentSensor, pk=pk)

    def get(self, request, pk):
        sensor = self.get_object(pk)
        serializer = EnvironmentSensorSerializer(sensor)
        return Response(*standard_response(True, 'Environment Sensor details fetched successfully!', serializer.data, status.HTTP_200_OK))

    def put(self, request, pk):
        sensor = self.get_object(pk)
        serializer = EnvironmentSensorSerializer(
            sensor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(*standard_response(True, 'Environment Sensor successfully updated!', serializer.data, status.HTTP_200_OK))

    def delete(self, request, pk):
        sensor = self.get_object(pk)
        sensor.delete()
        return Response(*standard_response(True, 'Environment Sensor successfully deleted!', {}, status.HTTP_204_NO_CONTENT))


@method_decorator(csrf_exempt, name='dispatch')
class CreateSensor(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = EnvironmentSensorSerializer(data=request.data)
        # Extract and validate the secret key
        header_key = request.headers.get('X-Secret-Key')

        match_temperature_key(header_key)
        if serializer.is_valid():
            water_level_sensor = serializer.save()
            return Response(
                {
                    "message": "Temparature level sensor created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": "Invalid data", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# {
#     "id": 26,
#     "tent": 1,
#     "tent_name": "Robertson-Williams",
#     "sn": "d7ce3dc8-7a38-4f2c-8c79-344a2fcdff8d",
#     "name": "Hard",
#     "ip": "105.193.9.118",
#     "lat": "24.662189",
#     "long": "42.931426",
#     "location": "395 Kathryn Cliffs Apt. 856\nNew Crystalview, AS 52051",
#     "top": 19.01,
#     "left": null,
#     "online": true,
#     "tempareture": 16,
#     "humidity": 77,
#     "last_entry_time": "2025-09-12T21:45:48+03:00",
#     "type": "environment"
# }

class SensorSampleCSVView(APIView):
    def get(self, request, *args, **kwargs):
        csv_content = "sn, name, ip, lat, long,  location, top, left, center_name, type\n"
        csv_content += "d7ce3dc8, Hard,  105.1913.9.11, 24.6612189, 42.931426, 395 Kathryn C1liffs Apt. 856 New 1Crystalview,19.101, 191.01, Robertson-Williams, environment\n"

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sensor.csv"'
        return response


class SensorUploadCSVview(APIView):
    permission_classes = [IsAuthenticated]

    REQUIRED_COLUMNS = [
        'sn', 'name', 'center_name'
    ]

    def post(self, request, *args, **kwargs):

        try:
            csv_file = request.FILES['csv']
        except MultiValueDictKeyError:
            return JsonResponse({'error': 'CSV file is required under key "csv".'}, status=400)

        try:
            csv_data = pd.read_csv(io.StringIO(
                csv_file.read().decode('utf-8')))
            csv_data.columns = csv_data.columns.str.strip()
        except pd.errors.ParserError as e:
            return JsonResponse({'error': f'CSV parsing failed: {str(e)}'}, status=400)
        except UnicodeDecodeError:
            return JsonResponse({'error': 'Encoding issue: Please upload a UTF-8 encoded CSV file.'}, status=400)

        # Validate required columns
        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in csv_data.columns]
        if missing_columns:
            return JsonResponse({'error': f'Missing required columns: {", ".join(missing_columns)}'}, status=400)

        created_count = 0
        updated_count = 0

        for _, row in csv_data.iterrows():
            sensor_sn = row.get('sn')
            if pd.isna(sensor_sn):
                continue

            name = row.get('name', '') or ''
            ip = row.get('ip') or None
            lat = self._get_val(row, 'lat')
            long = self._get_val(row, 'long')
            top = self._get_val(row, 'top')
            left = self._get_val(row, 'left')
            location = row.get('location', '')
            type = row.get('type', 'environment')
            center_name = row.get('center_name')

            try:
                sensor = EnvironmentSensor.objects.get(sn=sensor_sn)
                updated = True
            except EnvironmentSensor.DoesNotExist:
                sensor = EnvironmentSensor.objects.create(
                    sn=sensor_sn,
                    type=type,
                    name=name,
                    ip=ip,
                    lat=lat,
                    long=long,
                    top=top,
                    left=left,
                    location=location
                )
                created_count += 1
                updated = False

            if updated:
                sensor.name = name
                sensor.ip = ip
                sensor.lat = lat
                sensor.long = long
                sensor.top = top
                sensor.left = left
                sensor.location = location
                sensor.type = type  # optional: update if needed
                updated_count += 1

            if center_name:
                tent = Tent.objects.filter(
                    name__iexact=center_name.strip()).first()
                sensor.tent = tent
            else:
                sensor.tent = None

            sensor.save()

        return JsonResponse({
            'message': f'CSV processed successfully.',
            'updated': updated_count,
            'created': created_count,
        }, status=200)

    def _get_val(self, row, field):
        val = row.get(field)
        return None if pd.isna(val) else val


class SensorDataByHour(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        try:
            start_date = parse_date(start_date_str)
            if not start_date:
                raise ValueError

            if end_date_str:
                end_date = parse_date(end_date_str)
                if not end_date:
                    raise ValueError
            else:
                # If end_date_str is not provided, set end_date to start_date's end of day
                end_date = start_date + \
                    timedelta(days=1) - timedelta(seconds=1)
        except (ValueError, TypeError):
            return Response({"error": "Invalid date format"}, status=400)

        # Ensure end_date is greater than or equal to start_date
        if end_date and start_date:
            if end_date < start_date:
                return Response({"error": "end_date cannot be earlier than start_date"}, status=400)
        else:
            return Response({"error": "Invalid start_date or end_date"}, status=400)

        # Query data with aggregation at the database level
        sensor_records = (
            EnvironmentSensorRecord.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            .annotate(
                record_hour=TruncHour('created_at'),
                tent_name=F('sensor__tent__name'),
                sensor_name=F('sensor__name'),
            )
            # Filter to get only the record closest to the hour mark
            .annotate(
                time_diff=Abs(ExtractMinute('created_at') - 30)
            )
            .filter(time_diff=Min('time_diff'))
            .values('tent_name', 'record_hour', 'sensor_name')
            .annotate(
                tempareture_avg=Avg(F('tempareture') / 10.0),
                humidity_avg=Avg('humidity'),
                tempareture_max=Max(F('tempareture') / 10.0),
                tempareture_min=Min(F('tempareture') / 10.0),
                humidity_max=Max('humidity'),
                humidity_min=Min('humidity'),
            )
            .order_by('tent_name', 'record_hour', 'sensor_name')
        )

        # Process data to calculate averages per hour and per tent
        aggregated_records = {}
        for record in sensor_records:
            key = (record['tent_name'], record['record_hour'])
            if key not in aggregated_records:
                aggregated_records[key] = {
                    'tent_name': record['tent_name'],
                    'record_hour': record['record_hour'],
                    'tempareture_sum': record['tempareture_avg'],
                    'tempareture_max': record['tempareture_max'],
                    'tempareture_min': record['tempareture_min'],
                    'humidity_sum': record['humidity_avg'],
                    'humidity_max': record['humidity_max'],
                    'humidity_min': record['humidity_min'],
                    'count': 1
                }
            else:
                aggregated_records[key]['tempareture_sum'] += record['tempareture_avg']
                aggregated_records[key]['humidity_sum'] += record['humidity_avg']
                aggregated_records[key]['tempareture_max'] = max(
                    aggregated_records[key]['tempareture_max'], record['tempareture_max'])
                aggregated_records[key]['tempareture_min'] = min(
                    aggregated_records[key]['tempareture_min'], record['tempareture_min'])
                aggregated_records[key]['humidity_max'] = max(
                    aggregated_records[key]['humidity_max'], record['humidity_max'])
                aggregated_records[key]['humidity_min'] = min(
                    aggregated_records[key]['humidity_min'], record['humidity_min'])
                aggregated_records[key]['count'] += 1

        # Calculate final averages
        final_records = [
            {
                'tent_name': key[0],
                'record_hour': key[1],
                'tempareture_avg': round(aggregated_records[key]['tempareture_sum'] / aggregated_records[key]['count'], 3),
                'tempareture_max': round(aggregated_records[key]['tempareture_max'], 3),
                'tempareture_min': round(aggregated_records[key]['tempareture_min'], 3),
                'humidity_avg': round(aggregated_records[key]['humidity_sum'] / aggregated_records[key]['count'], 2),
                'humidity_max': round(aggregated_records[key]['humidity_max'], 2),
                'humidity_min': round(aggregated_records[key]['humidity_min'], 2)
            }
            for key in aggregated_records
        ]

        # Sort final_records by tent_name and record_hour
        final_records.sort(key=lambda x: (
            x['tent_name'] or '', x['record_hour'] or datetime.min))

        # Generate CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sensor_data.csv"'

        writer = csv.writer(response)
        writer.writerow(['date', 'hour', 'tent', 'tempareture_avg', 'tempareture_max',
                        'tempareture_min', 'humidity_avg', 'humidity_max', 'humidity_min'])
        for record in final_records:
            writer.writerow([
                record['record_hour'].date(),
                record['record_hour'].hour,
                record['tent_name'],
                round(record['tempareture_avg'], 3),
                record['tempareture_max'],
                record['tempareture_min'],
                round(record['humidity_avg'], 2),
                record['humidity_max'],
                record['humidity_min']
            ])

        return response


class SensorReportView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def paginate_response(self, data):
        """Apply pagination to the data."""
        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(data, self.request)
        return paginator.get_paginated_response(paginated_data)

    def get(self, request, tent_id=None):
        def get_aware_datetime_from_str(date_str):
            if not date_str:
                return None
            dt = parse_datetime(date_str)
            if dt is not None:
                return date_time_to_aware(dt)
            return None
        if tent_id:
            try:
                tent = Tent.objects.get(id=tent_id)
            except Tent.DoesNotExist:
                return Response({"detail": "Tent not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"detail": "No tents found."}, status=status.HTTP_404_NOT_FOUND)

        is_live = True if request.GET.get('is_live') == 'true' else False

        if is_live:
            start_date_time, end_date_time = Current_saudi_time()
        else:
            start_date_time = get_aware_datetime_from_str(
                request.GET.get('start_date_time')) or timezone.now()
            end_date_time = get_aware_datetime_from_str(
                request.GET.get('end_date_time')) or timezone.now()

        interval = request.GET.get('interval', 'hour')
        sensors_id_text = request.GET.get('sensors', "all")
        if sensors_id_text == "all":
            sensors = EnvironmentSensor.objects.filter(tent=tent, type='environment').exclude(
                location__icontains="kitchen").exclude(location__icontains="Corridor")

        else:
            try:
                sensors_id = [int(sid) for sid in sensors_id_text.split(
                    ",") if sid.strip().isdigit()]
                sensors = EnvironmentSensor.objects.filter(id__in=sensors_id)
            except ValueError:
                return Response({"detail": "Invalid sensor ID(s). All IDs must be integers."}, status=status.HTTP_400_BAD_REQUEST)
        # Call the appropriate function based on the interval
        if interval == "hour":
            return self._get_hourly_data(sensors, start_date_time, end_date_time, sensors_id_text)
        elif interval == "day":
            # assuming _get_daily_data exists
            return self._get_daily_data(sensors, start_date_time, end_date_time, sensors_id_text)
        else:
            return Response({"detail": f"Invalid interval: {interval}. Valid options are 'hour' or 'day'."}, status=status.HTTP_400_BAD_REQUEST)

    def _get_hourly_data(self, sensors, start_datetime, end_datetime, sensors_id_text):
        interval_hours = int(
            (end_datetime - start_datetime).total_seconds() / 3600)+1
        result_data = []

        if sensors_id_text == "all":
            # Combined hourly average for all sensors
            hourly_aggregates = (
                EnvironmentSensorRecord.objects
                .filter(sensor__in=sensors, last_entry_time__gte=start_datetime, last_entry_time__lt=end_datetime)
                .annotate(hour=TruncHour('last_entry_time'))
                .values('hour')
                .annotate(avg_temperature=Avg('tempareture'))
                .order_by('hour')
            )
            for item in hourly_aggregates:
                if item['avg_temperature'] != 0:
                    result_data.append({
                        'sensor_name': sensors.first().tent.name,
                        'date_and_time': item['hour'],
                        'tempareture': item['avg_temperature']
                    })
            total_temp = 0
            count = 0
            last_time = None

            for sensor in sensors:
                last_data = EnvironmentSensorRecord.objects.filter(
                    sensor=sensor,
                    last_entry_time__gte=start_datetime,
                    last_entry_time__lt=end_datetime
                ).order_by('-last_entry_time').first()

                if last_data:
                    # Update last_time with the latest available time
                    if last_time is None or last_data.last_entry_time > last_time:
                        last_time = last_data.last_entry_time

                    total_temp += last_data.tempareture
                    count += 1

            average_temp = total_temp / count if count > 0 else None

        else:
            sensor_data = defaultdict(lambda: {'tempareture': [], 'dates': []})
            date_labels = set()
            for sensor in sensors:
                existing_dates = set()

                # Per-sensor hourly average
                hourly_aggregates = (
                    EnvironmentSensorRecord.objects
                    .filter(sensor=sensor, last_entry_time__gte=start_datetime, last_entry_time__lt=end_datetime)
                    .order_by('last_entry_time')
                )
                intervals = 30
                current_time = start_datetime
                while current_time < end_datetime:
                    end_time = current_time + timedelta(minutes=intervals)
                    if end_time > end_datetime:
                        end_time = end_datetime
                    data = hourly_aggregates.filter(
                        last_entry_time__gte=current_time,
                        last_entry_time__lt=end_time
                    ).order_by('-last_entry_time').first()
                    if data:
                        riyadh_time = convert_utc_to_riyadh(
                            data.last_entry_time)
                        if riyadh_time in existing_dates:
                            continue  # Skip duplicate dates
                        sensor_data[sensor.name]['tempareture'].append(
                            data.tempareture)
                        sensor_data[sensor.name]['dates'].append(
                            data.last_entry_time.strftime('%Y-%m-%dT%H:%M:%S'))
                        date_labels.add(riyadh_time)
                    current_time = end_time

                # for item in hourly_aggregates:
                #     riyadh_time =  convert_utc_to_riyadh(item.last_entry_time)
                #     if riyadh_time in existing_dates:
                #         continue  # Skip duplicate dates
                #     existing_dates.add(riyadh_time)
                #     timestamp = item.last_entry_time.strftime('%Y-%m-%dT%H:%M:%S')
                #     sensor_data[sensor.name]['tempareture'].append(item.tempareture)
                #     sensor_data[sensor.name]['dates'].append(timestamp)
                #     date_labels.add(riyadh_time)
            # Sort dates
            date_labels = sorted(date_labels)

            # Build final result
            final_result = {
                'data': [
                    {
                        'name': name,
                        'data': [round(temp, 3) for temp in data['tempareture']],
                    }
                    for name, data in sensor_data.items()
                ],
                'dates': date_labels
            }
            return Response({
                "success": True,
                "message": "Hourly data fetched successfully.",
                "start_date": start_datetime,
                "end_date": end_datetime,
                "results": final_result
            }, status=status.HTTP_200_OK)

        return Response(self._format_sensor_data_hour(result_data, start_datetime, interval_hours, average_temp, last_time))

    def _format_sensor_data_hour(self, input_data, start_time, interval_hours, average_temp, last_time):

        sensor_data = defaultdict(
            lambda: {'temperature': [0] * interval_hours})

        # Process each input entry
        for entry in input_data:
            sensor_name = entry["sensor_name"]  # Group by sensor ID
            tempareture = entry["tempareture"]

            # Parse and adjust hour
            if isinstance(entry["date_and_time"], str):
                hour = datetime.fromisoformat(
                    entry["date_and_time"]).astimezone(pytz.UTC)
            else:
                hour = entry["date_and_time"].astimezone(pytz.UTC)

            # Find the index for this hour
            index = int((hour - start_time).total_seconds() // 3600)
            if 0 <= index < interval_hours:  # Only include valid intervals
                sensor_data[sensor_name]['temperature'][index] = tempareture

        date_labels = [
            (start_time + timedelta(hours=i)).isoformat()
            for i in range(interval_hours)
        ]
        temp_name = None
        if sensor_data:
            temp_name = next(iter(sensor_data))
        final_result = {'data': [], 'dates': []}
        for name, data in sensor_data.items():
            temps = data['temperature']
            # Filter out 0s and collect corresponding non-zero dates
            filtered_data = []
            filtered_dates = []

            for i, temp in enumerate(temps):
                if temp != 0:
                    filtered_data.append(round(temp, 3))
                    filtered_dates.append(date_labels[i])

            final_result['data'].append({
                'name': name,
                'data': filtered_data,
            })

            # Only set dates once (assumes all sensors use same interval pattern)
            if not final_result['dates']:
                final_result['dates'] = filtered_dates
        # Construct the final result
        # final_result = {
        #     'data': [
        #         {
        #             'name': name,
        #             'data': [round(temp, 3) for temp in data['temperature']],
        #         }
        #         for name, data in sensor_data.items()
        #     ],
        #     'dates': date_labels
        # }

        # Append average temp to the correct sensor and time to date list
        if average_temp and last_time and temp_name:
            for sensor in final_result['data']:
                if sensor['name'] == temp_name:  # Adjust this condition if needed
                    sensor['data'].append(round(average_temp, 3))
            final_result['dates'].append(convert_utc_to_riyadh(last_time))

        response_data = {
            "success": True,
            "message": "Temparature level sensor created successfully.",
            "results": final_result

        }
        return response_data

    def _get_daily_data(self, sensors, start_datetime, end_datetime, sensors_id_text):
        interval_days = (end_datetime - start_datetime).days+1
        result_data = []
        # end_datetime += timedelta(days=1)
        if sensors_id_text == "all":
            # Daily average temperature across all sensors
            daily_aggregates = (
                EnvironmentSensorRecord.objects
                .filter(sensor__in=sensors, last_entry_time__gte=start_datetime, last_entry_time__lt=end_datetime)
                .annotate(day=TruncDay('last_entry_time'))
                .values('day')
                .annotate(avg_temperature=Avg('tempareture'))
                .order_by('day')
            )

            for item in daily_aggregates:
                if item['avg_temperature'] != 0:
                    result_data.append({
                        'sensor_name': 'All Sensors',
                        'date': item['day'],
                        'tempareture': item['avg_temperature']
                    })
        else:
            for sensor in sensors:
                # Latest record per day for each sensor
                # Per-sensor hourly average
                hourly_aggregates = (
                    EnvironmentSensorRecord.objects
                    .filter(sensor=sensor, last_entry_time__gte=start_datetime, last_entry_time__lt=end_datetime)
                    .annotate(day=TruncDay('last_entry_time'))
                    .values('day', 'sensor')
                    .annotate(avg_temperature=Avg('tempareture'))
                    .order_by('day')
                )

                for item in hourly_aggregates:
                    result_data.append({
                        'tent_id': sensor.tent.id,
                        'tent_name': sensor.tent.name,
                        'sensor_id': sensor.id,
                        'sensor_name': sensor.name,
                        'date': item['day'],
                        'tempareture': item['avg_temperature']
                    })

        return Response(self._format_sensor_data_daily(result_data, start_datetime, interval_days))

    def _format_sensor_data_daily(self, input_data, start_datetime, interval_days):

        # Initialize storage
        sensor_data = defaultdict(lambda: {'temperature': [0] * interval_days})

        # Process entries
        for entry in input_data:
            sensor_name = entry["sensor_name"]
            avg_tempareture = entry["tempareture"]

            if isinstance(entry["date"], str):
                day = datetime.fromisoformat(entry["date"])
            else:
                day = entry["date"]

            index = (day.date() - start_datetime.date()).days

            if 0 <= index < interval_days:
                sensor_data[sensor_name]['temperature'][index] = avg_tempareture

        # Generate date labels
        date_labels = [
            (start_datetime + timedelta(days=i)).isoformat()
            for i in range(interval_days)
        ]
        results_data = {
            'data': [
                {
                    'name': name,
                    'data': [round(temp, 3) for temp in data['temperature']],
                }
                for name, data in sensor_data.items()
            ],
            'dates': date_labels,
        }
        response_data = {
            "success": True,
            "message": "Temparature level sensor created successfully.",
            "results": results_data
        }
        return response_data


class SensorData(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        # Get query parameters
        response_type = request.GET.get('type', 'json')
        interval = request.GET.get('interval', 'hour')
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'
        tents = None

        # Validate required parameters
        if not interval or not start_date_str or not end_date_str:
            return Response({"detail": "interval, start_date, and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse and validate dates
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({"detail": "start_date must be before end_date."}, status=status.HTTP_400_BAD_REQUEST)

        # Convert to datetime objects with proper time boundaries
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.min.time())) + timedelta(days=1)

        # Parse tent IDs
        tent_ids = []
        if tent_id_list:
            try:
                tent_ids = [int(tid.strip()) for tid in tent_id_list.split(
                    ',') if tid.strip().isdigit()]
            except ValueError:
                return Response({
                    "detail": "Invalid tent_ids parameter. It must be a comma-separated list of integers."
                }, status=status.HTTP_400_BAD_REQUEST)

        # Get tents
        if tent_ids:
            tents = Tent.objects.filter(id__in=tent_ids)
            if not tents.exists():
                return Response({"detail": f"No tents found with IDs: {tent_ids}"}, status=status.HTTP_404_NOT_FOUND)

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

        # Set grouping function based on interval
        if interval == 'hour':
            trunc_func = TruncHour
        elif interval == 'day':
            trunc_func = TruncDay
        elif interval == 'month':
            trunc_func = TruncMonth
        else:
            return Response({
                "detail": "Invalid interval. Choose from 'hour', 'day', or 'month'."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Query for EnvironmentSensorRecord with proper aggregation
        sensor_records = (
            EnvironmentSensorRecord.objects
            .select_related('sensor__tent')
            .filter(
                sensor__tent__in=tents,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            )
            .annotate(
                interval_group=trunc_func('created_at'),
                tent_name=F('sensor__tent__name'),
                sensor_name=F('sensor__name'),
            )
            .values('interval_group', 'tent_name', 'sensor_name')
            .annotate(
                temperature_avg=Avg('tempareture'),
                temperature_max=Max('tempareture'),
                temperature_min=Min('tempareture'),
                humidity_avg=Avg('humidity'),
                humidity_max=Max('humidity'),
                humidity_min=Min('humidity'),
            )
            .order_by('tent_name', 'sensor_name', '-interval_group')
        )

        # Format the data
        data = []
        for record in sensor_records:
            data.append({
                'interval': record['interval_group'],
                'tent_name': record['tent_name'],
                'sensor_name': record['sensor_name'],
                'temperature_avg': round(record['temperature_avg'], 2) if record['temperature_avg'] is not None else None,
                'temperature_max': record['temperature_max'],
                'temperature_min': record['temperature_min'],
                'humidity_avg':  round(record['humidity_avg'], 2) if record['humidity_avg'] is not None else None,
                'humidity_max': record['humidity_max'],
                'humidity_min': record['humidity_min'],
            })

        # Return CSV if requested
        if response_type == "csv":
            return generate_csv_response(data, 'sensor_data.csv')

        # Apply pagination if requested
        if paginate:
            # Apply pagination for JSON response
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)
        else:
            return Response({
                'success': True,
                'message': "Sensor Report Data Retrieved Successfully",
                'results': data,
            }, status=status.HTTP_200_OK)


class EnvironmentSensorsWithoutRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get sensors of type 'environment' that do not have any related records
        sensors_without_records = EnvironmentSensor.objects.filter(
            type='environment', tent__isnull=True).order_by('id')
        if sensors_without_records.exists():
            serializer = EnvironmentSensorSerializer(
                sensors_without_records, many=True)
            data = serializer.data
        else:
            data = []
        data = {
            "success": True,
            "message": "Environments retrieved successfully.",
            "results": data
        }
        return Response(data, status=status.HTTP_200_OK)


class ReassignSensorWithRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        old_sensor_id = request.data.get('old_sensor_id')
        new_sensor_id = request.data.get('new_sensor_id')

        if not old_sensor_id or not new_sensor_id:
            return Response({
                "success": False,
                "message": "Both old_sensor_id and new_sensor_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        old_sensor = EnvironmentSensor.objects.filter(id=old_sensor_id).first()
        new_sensor = EnvironmentSensor.objects.filter(id=new_sensor_id).first()

        if not old_sensor or not new_sensor:
            return Response({
                "success": False,
                "message": "Invalid old_sensor_id or new_sensor_id"
            }, status=status.HTTP_400_BAD_REQUEST)
        if new_sensor and new_sensor.tent:
            return Response({
                "success": False,
                "message": "Sensor is already assigned to a tent."
            }, status=status.HTTP_400_BAD_REQUEST)
        # Assign the tent of the old sensor to the new sensor
        new_sensor.tent = old_sensor.tent
        if old_sensor.location:
            new_sensor.location = old_sensor.location
        if old_sensor.top:
            new_sensor.top = old_sensor.top
        if old_sensor.left:
            new_sensor.left = old_sensor.left
        if old_sensor.tempareture:
            new_sensor.tempareture = old_sensor.tempareture
        if old_sensor.humidity:
            new_sensor.humidity = old_sensor.humidity
        if old_sensor.last_entry_time:
            new_sensor.last_entry_time = old_sensor.last_entry_time
        new_sensor.save()
        old_sensor.tent = None
        old_sensor.top = None
        old_sensor.left = None
        old_sensor.save()

        try:
            # Reassign all records from old sensor to new sensor
            EnvironmentSensorRecord.objects.filter(
                sensor=old_sensor).update(sensor=new_sensor)
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Error reassigning records: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = {
            "success": True,
            "message": "Environment Sensor successfully updated!"
        }
        return Response(data, status.HTTP_200_OK)


class AssignNewSensorView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id=None):
        sensor = get_object_or_404(EnvironmentSensor, id=id)
        is_detach = True if request.GET.get(
            'is_detach', "false").lower() == "true" else False
        if is_detach:
            sensor.tent = None
            sensor.left = None
            sensor.top = None
            sensor.location = None
            sensor.save()
            return Response({
                "success": True,
                "message": "Sensor detouched successfully."
            }, status=status.HTTP_200_OK)

        # Prevent reassigning if already assigned
        if sensor.tent:
            return Response({
                "success": False,
                "message": "Sensor is already assigned to a tent."
            }, status=status.HTTP_400_BAD_REQUEST)

        tent_id = request.data.get('tent')
        top = request.data.get('top')
        left = request.data.get('left')
        location = request.data.get('location')

        # Tent assignment
        if tent_id:
            tent = Tent.objects.filter(id=tent_id).first()
            if not tent:
                return Response({
                    "success": False,
                    "message": "Tent not found."
                }, status=status.HTTP_400_BAD_REQUEST)
            sensor.tent = tent

        # Optional fields update
        if top is None:
            return Response({
                "success": False,
                "message": "Top field is required."
            }, status=status.HTTP_400_BAD_REQUEST)
        if left is None:
            return Response({
                "success": False,
                "message": "Left field is required."
            }, status=status.HTTP_400_BAD_REQUEST)
        sensor.top = top
        sensor.left = left
        if location is not None:
            sensor.location = location

        sensor.save()
        serializers = EnvironmentSensorSerializer(sensor)

        return Response({
            "success": True,
            "message": "Environment Sensor successfully updated!",
            "results": serializers.data
        }, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class IngestEnvironmentSensorData(APIView):
    authentication_classes = []   # MQTT doesn’t need login
    permission_classes = []

    def post(self, request):
        """
        Expected JSON:
        {
          "sn": "d896e0efff0007c2",
          "temperature": 27.2,
          "humidity": 40.7,
          "timestamp": "2025-12-17T15:34:56Z"
        }
        """

        sn = request.data.get("sn")
        temperature = request.data.get("temperature")
        humidity = request.data.get("humidity")
        timestamp = request.data.get("timestamp")

        if not all([sn, temperature, humidity]):
            return Response(
                {"error": "sn, temperature and humidity are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        sensor = EnvironmentSensor.objects.filter(sn=sn).first()
        if not sensor:
            return Response(
                {"error": f"Sensor with sn {sn} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        entry_time = parse_datetime(timestamp) if timestamp else timezone.now()
        if entry_time and timezone.is_naive(entry_time):
            entry_time = timezone.make_aware(entry_time)

        # Save record
        EnvironmentSensorRecord.objects.create(
            sensor=sensor,
            tempareture=float(temperature),
            humidity=int(humidity),
            last_entry_time=entry_time
        )

        # Update sensor latest values
        sensor.tempareture = temperature
        sensor.humidity = humidity
        sensor.last_entry_time = entry_time
        sensor.save(update_fields=[
            'tempareture', 'humidity', 'last_entry_time'
        ])

        return Response(
            {
                "success": True,
                "message": "Sensor data saved successfully"
            },
            status=status.HTTP_201_CREATED
        )
