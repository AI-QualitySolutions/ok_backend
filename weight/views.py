import os
from django.db.models import (
    Sum, F, Q, When, ExpressionWrapper, Min, Subquery, OuterRef, Func, Max)
from django.db.models.functions import TruncMonth, TruncHour, TruncDay
from django.conf import settings
from datetime import datetime
from django.http import JsonResponse, FileResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import parsers
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import make_aware, is_naive, now, localtime, get_current_timezone
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from datetime import datetime, time
from datetime import datetime, timedelta
import datetime as datenowtime


from authentication.permissions import FoodWeightPermission
from weight.models import OrderWeight, WeightConditions, EnvironmentSensor
from weight.serializers import OrderWeightSerializer, WeightConditionsSerializer, TentFoodWeightsSerializer

from tent.models import Tent

from utils.time import Current_saudi_time, start_end_time_to_riyad

from authentication.utils import standard_response
from tent.utils import generate_csv_response, CustomPagination

from weight.utils import match_add_new_order_secret_key
from django.utils.timezone import make_aware, is_aware
import logging
import json

logger = logging.getLogger(__name__)


class CustomJSONParser(JSONParser):
    """
    Custom JSON parser that handles both application/json and application/json-patch+json
    """
    media_type = 'application/json-patch+json'
    
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse the incoming stream as JSON and return the parsed data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        
        try:
            data = stream.read().decode(encoding)
            return json.loads(data)
        except ValueError as exc:
            from rest_framework.exceptions import ParseError
            raise ParseError('JSON parse error - %s' % str(exc))


class FlexibleJSONParser(JSONParser):
    """
    Flexible JSON parser that handles both application/json and application/json-patch+json
    """
    media_type = '*/*'
    
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse the incoming stream as JSON regardless of content type.
        """
        # Only handle JSON-like content types
        if media_type and not any(ct in media_type for ct in ['json', 'javascript']):
            from rest_framework.exceptions import UnsupportedMediaType
            raise UnsupportedMediaType(media_type)
            
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        
        try:
            data = stream.read().decode(encoding)
            return json.loads(data)
        except ValueError as exc:
            from rest_framework.exceptions import ParseError
            raise ParseError('JSON parse error - %s' % str(exc))


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

class DeviceWeightViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, FoodWeightPermission]
    queryset = OrderWeight.objects.filter(weight__gte=0)
    serializer_class = OrderWeightSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(*standard_response(True, 'Order Weight successfully created!', serializer.data, status.HTTP_201_CREATED))

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(*standard_response(True, 'Order Weight successfully updated!', serializer.data, status.HTTP_200_OK))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(*standard_response(True, 'Order Weight details fetched successfully!', serializer.data, status.HTTP_200_OK))

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(*standard_response(True, 'Order Weight list fetched successfully!', serializer.data, status.HTTP_200_OK))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(*standard_response(True, 'Order Weight successfully deleted!', {}, status.HTTP_204_NO_CONTENT))


@method_decorator(csrf_exempt, name='dispatch')
class AddNewOrderView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [FlexibleJSONParser, JSONParser, CustomJSONParser]
    def post(self, request):
        try:
            # Extract data from the request
            # logger.info(f"Request data: {request.data}")
            device_num = request.data.get('deviceNum')
            weight = request.data.get('weight')
            date = request.data.get('date') or timezone.now()
            secret = request.data.get('secret')
            

            try:
                weight_sensor = EnvironmentSensor.objects.get(sn=device_num)
            except EnvironmentSensor.DoesNotExist:
                weight_sensor = EnvironmentSensor.objects.create(
                    sn=device_num, type="weight")

            # Extract and validate the secret key
            # header_key = request.headers.get('X-Secret-Key')

            # match_add_new_order_secret_key(header_key)

            # # Validate required fields
            # if not all([device_num, weight, date, secret]):
            #     return Response(
            #         *standard_response(False, "All fields are required.", {}, status.HTTP_400_BAD_REQUEST)
            #     )

            # Create the OrderWeight object
            order_weight = OrderWeight.objects.create(
                device_num=device_num,
                weight=weight,
                date=date,
                secret=secret,
                weight_sensor=weight_sensor
            )

            # Serialize the created object
            serializer = OrderWeightSerializer(order_weight)

            return Response(
                *standard_response(True, "Order Weight successfully created!", serializer.data, status.HTTP_201_CREATED)
            )

        except PermissionDenied as e:
            return Response(
                *standard_response(False, str(e), {}, status.HTTP_403_FORBIDDEN)
            )

        except Exception as e:
            from traceback import format_exc
            logger.error(f"Unexpected error in AddNewOrderView: {str(e), format_exc()}")
            return Response(
                *standard_response(False, "An unexpected error occurred.", {}, status.HTTP_500_INTERNAL_SERVER_ERROR)
            )


class WeightConditionsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, FoodWeightPermission]
    queryset = WeightConditions.objects.all()
    serializer_class = WeightConditionsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(*standard_response(True, 'Weight Condition successfully created!', serializer.data, status.HTTP_201_CREATED))

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(*standard_response(True, 'Weight Condition successfully updated!', serializer.data, status.HTTP_200_OK))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(*standard_response(True, 'Weight Condition details fetched successfully!', serializer.data, status.HTTP_200_OK))

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(*standard_response(True, 'Weight Condition list fetched successfully!', serializer.data, status.HTTP_200_OK))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(*standard_response(True, 'Weight Condition successfully deleted!', {}, status.HTTP_204_NO_CONTENT))


class FoodWeightsView(APIView):
    permission_classes = [IsAuthenticated, FoodWeightPermission]

    def get(self, request):
        date = request.GET.get('date', None)
        if not date:
            return Response(*standard_response(False, "Date is required.", {}, status.HTTP_400_BAD_REQUEST))
        try:
            date = parse_date(date)

            tents_data = Tent.objects.filter(
                # Correct way to filter based on orderweight
                sensors__order_weights__date__date=date
            ).annotate(
                # Correct way to count orderweight rows
                total_rows=Count('sensors__order_weights'),
                # Correct way to calculate average weight
                avg_weight=Avg('sensors__order_weights__weight')
            ).values('id', 'name', 'capacity', 'total_rows', 'avg_weight')

            result_data = []
            for tent_data in tents_data:
                data = {}
                data["id"] = tent_data["id"]
                data["tent_name"] = tent_data["name"]
                data["capacity"] = tent_data["capacity"]
                data["total_meals"] = tent_data["total_rows"]
                data["average_weight"] = round(tent_data["avg_weight"], 2)
                result_data.append(data)
            return Response(*standard_response(True, 'Weight successfully!', result_data, status.HTTP_201_CREATED))

        except Exception as e:
            logger.error(f"Unexpected error in FoodWeightsView: {str(e)}")
            return Response({"detail": f"Invalid date format.: {e}"}, status=status.HTTP_400_BAD_REQUEST)


class TentFoodWeightsView(APIView):
    permission_classes = [IsAuthenticated, FoodWeightPermission]

    def get(self, request, tent_id=None):
        date = request.GET.get('date', None)
        if not date:
            return Response(*standard_response(False, "Date is required.", {}, status.HTTP_400_BAD_REQUEST))
        try:
            if tent_id and date:
                tent_id = int(tent_id)
                date = parse_date(date)
            else:
                return Response({"detail": "Tent ID and Date are Required."}, status=status.HTTP_400_BAD_REQUEST)
            # Querying the Tent model and related OrderWeight model with tent and date filtering for a specific tent and date
            tent = Tent.objects.filter(id=tent_id).first()

            if not tent:
                return Response({"detail": "No tent found for the given ID."}, status=status.HTTP_404_NOT_FOUND)

            tent_food_weights = OrderWeight.objects.filter(
                weight_sensor__tent=tent, date__date=date, weight__gte=0)
            if not tent_food_weights:
                return Response({"detail": "No data found for the given tent and date."}, status=status.HTTP_404_NOT_FOUND)
            # Query the WeightConditions model to find records where the specific date is within the range of start_date and end_date
            weight_condition = WeightConditions.objects.all().first()

            if not weight_condition:
                return Response({"detail": "I don't get any condition"}, status=status.HTTP_404_NOT_FOUND)

            breakfast_start = weight_condition.breakfast_start
            breakfast_end = weight_condition.breakfast_end
            lunch_start = weight_condition.lunch_start
            lunch_end = weight_condition.lunch_end
            dinner_start = weight_condition.dinner_start
            dinner_end = weight_condition.dinner_end
            breakfast_weight_accepted = weight_condition.breakfast_weight_accepted
            lunch_weight_accepted = weight_condition.lunch_weight_accepted
            dinner_weight_accepted = weight_condition.dinner_weight_accepted

            breakfast_rejected_meals = 0
            breakfast_accepted_meals = 0
            breakfast_total_weight = 0

            lunch_rejected_meals = 0
            lunch_accepted_meals = 0
            lunch_total_weight = 0

            dinner_rejected_meals = 0
            dinner_accepted_meals = 0
            dinner_total_weight = 0

            for tent_food_weight in tent_food_weights:
                if tent_food_weight.date.time() > breakfast_start and tent_food_weight.date.time() < breakfast_end:
                    if tent_food_weight.weight >= breakfast_weight_accepted:
                        breakfast_accepted_meals += 1
                        breakfast_total_weight += tent_food_weight.weight
                    else:
                        breakfast_rejected_meals += 1
                        breakfast_total_weight += tent_food_weight.weight
                elif tent_food_weight.date.time() > lunch_start and tent_food_weight.date.time() < lunch_end:
                    if tent_food_weight.weight >= lunch_weight_accepted:
                        lunch_accepted_meals += 1
                        lunch_total_weight += tent_food_weight.weight
                    else:
                        lunch_rejected_meals += 1
                        lunch_total_weight += tent_food_weight.weight
                elif tent_food_weight.date.time() > dinner_start and tent_food_weight.date.time() < dinner_end:
                    if tent_food_weight.weight >= dinner_weight_accepted:
                        dinner_accepted_meals += 1
                        dinner_total_weight += tent_food_weight.weight
                    else:
                        dinner_rejected_meals += 1
                        dinner_total_weight += tent_food_weight.weight

                if (breakfast_accepted_meals + breakfast_rejected_meals) > 0:
                    breakfast_average_weight = float(
                        breakfast_total_weight / (breakfast_accepted_meals + breakfast_rejected_meals))
                else:
                    breakfast_average_weight = 0.0  # Default to 0 if no meals

                if (lunch_accepted_meals + lunch_rejected_meals) > 0:
                    lunch_average_weight = float(
                        lunch_total_weight / (lunch_accepted_meals + lunch_rejected_meals))
                else:
                    lunch_average_weight = 0.0  # Default to 0 if no meals

                if (dinner_accepted_meals + dinner_rejected_meals) > 0:
                    dinner_average_weight = float(
                        dinner_total_weight / (dinner_accepted_meals + dinner_rejected_meals))
                else:
                    dinner_average_weight = 0.0  # Default to 0 if no meals

                data = {
                    "id": tent_id,
                    "capacity": tent.capacity,
                    "breakfast_rejected_meals": breakfast_rejected_meals,
                    "breakfast_accepted_meals": breakfast_accepted_meals,
                    "lunch_rejected_meals": lunch_rejected_meals,
                    "lunch_accepted_meals": lunch_accepted_meals,
                    "dinner_rejected_meals": dinner_rejected_meals,
                    "dinner_accepted_meals": dinner_accepted_meals,
                    "breakfast_average_weight": breakfast_average_weight,
                    "lunch_average_weight": lunch_average_weight,
                    "dinner_average_weight": dinner_average_weight,
                    "total_rejected_meals": breakfast_rejected_meals + lunch_rejected_meals + dinner_rejected_meals,
                    "total_accepted_meals": breakfast_accepted_meals + lunch_accepted_meals + dinner_accepted_meals

                }
                # data.append()
            serializer = TentFoodWeightsSerializer(data)
            return Response(*standard_response(True, 'Food Weight successfully!', serializer.data, status.HTTP_201_CREATED))

        except Exception as e:
            logger.error(f"Unexpected error in TentFoodWeightsView: {str(e)}")
            return Response({"detail": f"Invalid tent ID or date format.{e}"}, status=status.HTTP_400_BAD_REQUEST)


class FoodWeightReportView(APIView):
    permission_classes = [IsAuthenticated, FoodWeightPermission]
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        # Get query parameters
        user = request.user
        response_type = request.GET.get('type', 'json')
        start_date_str = request.GET.get('start_date', None)
        end_date_str = request.GET.get('end_date', None)
        tent_id_list = request.GET.get('tent_id', None)
        paginate = request.GET.get('paginate', 'true').lower() == 'true'

        # Validate required parameters
        if not start_date_str or not end_date_str:
            return Response({"detail": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse and validate dates
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({"detail": "start_date must be before end_date."}, status=status.HTTP_400_BAD_REQUEST)

        # Convert to datetime objects
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

        def get_food_type_and_acceptance(record, weight_conditions):
            """
            Determine the food type based on the record's time and weight conditions.
            Also returns whether the food weight is accepted based on meal thresholds.
            Returns (food_type, is_accepted), where food_type can be None.
            """
            record_time = record.date.time()  # Extract time from DateTimeField

            # Check breakfast
            if (weight_conditions.breakfast_start and weight_conditions.breakfast_end and
                    weight_conditions.breakfast_start <= record_time <= weight_conditions.breakfast_end):
                accepted = (weight_conditions.breakfast_weight_accepted is None or
                            record.weight >= weight_conditions.breakfast_weight_accepted)
                return "Breakfast", accepted

            # Check lunch
            if (weight_conditions.lunch_start and weight_conditions.lunch_end and
                    weight_conditions.lunch_start <= record_time <= weight_conditions.lunch_end):
                accepted = (weight_conditions.lunch_weight_accepted is None or
                            record.weight >= weight_conditions.lunch_weight_accepted)
                return "Lunch", accepted

            # Check dinner
            if (weight_conditions.dinner_start and weight_conditions.dinner_end and
                    weight_conditions.dinner_start <= record_time <= weight_conditions.dinner_end):
                accepted = (weight_conditions.dinner_weight_accepted is None or
                            record.weight >= weight_conditions.dinner_weight_accepted)
                return "Dinner", accepted

            return None, False  # No matching meal time

        records = OrderWeight.objects.filter(
                weight_sensor__tent__in=tents,
                date__gte=start_datetime,
                date__lte=end_datetime,
                weight__gte=0
            ).order_by('weight_sensor__tent', 'weight_sensor', 'date')


        weight_conditions = WeightConditions.objects.all().first()
        data = []
        for record in records:
            food_type, is_accepted = get_food_type_and_acceptance(
                record, weight_conditions) if weight_conditions else (None, False)
            data.append({
                'office_name': record.weight_sensor.tent.name,
                'device_number': record.device_num,
                'date': record.date.date(),
                'timestamp': record.date.time(),
                'food_type': food_type,
                'food_weight': record.weight,
                'is_accepted': is_accepted
            })

        # Return CSV if requested
        if response_type == "csv":
            return generate_csv_response(data, 'food_weight_report.csv')

        # Apply pagination if requested
        if paginate:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(
                data, request, view=self)
            return paginator.get_paginated_response(paginated_data)
        else:
            return Response({
                'success': True,
                'message': "Food Weight Report Data Retrieved Successfully",
                'results': data,
            }, status=status.HTTP_200_OK)


class FoodCardView(APIView):
    permission_classes = [IsAuthenticated, FoodWeightPermission]
    def get(self, request):
        user = request.user
        tent_ids = request.query_params.get('tent_ids')

        start_date_time = None
        end_date_time = None
        date_str = request.query_params.get('date')


        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_date_time = datetime.combine(date_obj, time.min)  # 00:00:00
                end_date_time = datetime.combine(date_obj, time.max)    # 23:59:59.999999
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        else:
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

        # Fetch the latest weight condition globally
        condition = WeightConditions.objects.order_by('-created_at').first()

        if not condition:
            return Response({"error": "No weight conditions defined."}, status=400)

        for tent in tents:
            print("tent")
            sensors = EnvironmentSensor.objects.filter(
                tent=tent, type="weight")
            print("sensors")

            # print(start_date_time, end_date_time)
            weights = OrderWeight.objects.filter(
                weight_sensor__in=sensors,
                date__gte=start_date_time,
                date__lte=end_date_time,
                weight__gte=0
            ).order_by('date')
            # Split weights into meals
            # meal_data = {
            #     'breakfast': {'start': condition.breakfast_start, 'end': condition.breakfast_end, 'accepted': condition.breakfast_weight_accepted},
            #     'lunch': {'start': condition.lunch_start, 'end': condition.lunch_end, 'accepted': condition.lunch_weight_accepted},
            #     'dinner': {'start': condition.dinner_start, 'end': condition.dinner_end, 'accepted': condition.dinner_weight_accepted},
            # }
            breakfast_start, breakfast_end, breakfast_weight_accepted = condition.breakfast_start, condition.breakfast_end, condition.breakfast_weight_accepted
            lunch_start, lunch_end, lunch_weight_accepted = condition.lunch_start, condition.lunch_end, condition.lunch_weight_accepted
            dinner_start, dinner_end, dinner_weight_accepted = condition.dinner_start, condition.dinner_end, condition.dinner_weight_accepted

            tent_summary = {
                "tent_id": tent.id,
                "tent_name": tent.name,
                "meals": {
                    "breakfast": {"total": 0, "rejected": 0},
                    "lunch": {"total": 0, "rejected": 0},
                    "dinner": {"total": 0, "rejected": 0},
                }
            }

            for w in weights:
                weight_time = localtime(w.date).time()
                # Breakfast
                if breakfast_start and breakfast_end and breakfast_start <= weight_time <= breakfast_end:
                    tent_summary['meals']['breakfast']['total'] += 1
                    if breakfast_weight_accepted is not None and w.weight < breakfast_weight_accepted:
                        tent_summary['meals']['breakfast']['rejected'] += 1
                # Lunch
                if lunch_start and lunch_end and lunch_start <= weight_time <= lunch_end:
                    tent_summary['meals']['lunch']['total'] += 1
                    if lunch_weight_accepted is not None and w.weight < lunch_weight_accepted:
                        tent_summary['meals']['lunch']['rejected'] += 1
                # Dinner
                if dinner_start and dinner_end and dinner_start <= weight_time <= dinner_end:
                    tent_summary['meals']['dinner']['total'] += 1
                    if dinner_weight_accepted is not None and w.weight < dinner_weight_accepted:
                        tent_summary['meals']['dinner']['rejected'] += 1

            # Compute percentages
            for meal in ['breakfast', 'lunch', 'dinner']:
                total = tent_summary['meals'][meal]['total']
                rejected = tent_summary['meals'][meal]['rejected']
                percentage = (total / tent.capacity) * 100 if tent.capacity else 0
                rejection_percentage = (rejected / total) * 100 if total > 0 else 0

                tent_summary['meals'][meal]['color'] = "red" if percentage < 70.0 else "green"
                tent_summary['meals'][meal]['rejection_percentage'] = round(rejection_percentage, 2)


            # for meal, timing in meal_data.items():
            #     start_time = timing['start']
            #     end_time = timing['end']
            #     accepted_weight = timing['accepted']
            #     each_meal = []
            #     rejected_count = 0
            #     for w in weights:
            #         local_created_time = localtime(w.created_at).time()
            #         if start_time and end_time and start_time <= local_created_time <= end_time:
            #             each_meal.append(w)
            #             if accepted_weight is not None and w.weight < accepted_weight:
            #                 rejected_count += 1

            #     total = len(each_meal)
            #     percentage = 0
            #     if total != 0:
            #         percentage = (total/tent.capacity) * 100.0
            #     tent_summary['meals'][meal] = {
            #         "total": total,
            #         "rejected": rejected_count,
            #         "color": "red" if percentage < 70.0 else "green",
            #         "rejection_percentage": round((rejected_count / total) * 100, 2) if total > 0 else 0.0
            #     }

            result.append(tent_summary)

        data = {
            'success': True,
            'message': "Kitchen Violation Report Data Retrieved Successfully",
            "start_time": start_date_time,
            "end_time": end_date_time,
            'results': result,
        }

        return Response(data, status=status.HTTP_200_OK)


class FoodGraphView(APIView):
    permission_classes = [IsAuthenticated, FoodWeightPermission]

    def get(self, request, *args, **kwargs):
        tent_id = request.query_params.get('tent_id')
        date_str = request.query_params.get('date', None)
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, "%Y-%m-%d")
                fixed_date = make_aware(selected_date)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        else:
            date = datenowtime.datetime.now()
            fixed_date = make_aware(date)

        if not tent_id:
            return Response({"error": "tent_id must needed"}, status=400)

        try:
            tent = Tent.objects.filter(id=int(tent_id)).first()
            if not tent:
                return Response({"error": "Tent not found"}, status=404)
        except ValueError:
            return Response({"error": "Invalid tent_id format"}, status=400)

        weight_condition = (
            WeightConditions.objects.filter(
                created_at__gte=fixed_date, created_at__lte=fixed_date).first()
            or WeightConditions.objects.filter(created_at__lte=fixed_date).order_by('-end_date').first()
            or WeightConditions.objects.filter(created_at__gte=fixed_date).order_by('start_date').first()
        )

        if not weight_condition:
            return Response({"error": "No weight conditions found for the selected date"}, status=404)
        # Meal timing and thresholds
        b_start, b_end, b_thresh = weight_condition.breakfast_start, weight_condition.breakfast_end, weight_condition.breakfast_weight_accepted
        l_start, l_end, l_thresh = weight_condition.lunch_start, weight_condition.lunch_end, weight_condition.lunch_weight_accepted
        d_start, d_end, d_thresh = weight_condition.dinner_start, weight_condition.dinner_end, weight_condition.dinner_weight_accepted

        sensors = EnvironmentSensor.objects.filter(tent=tent, type="weight")
        intervals = 5  # Minutes

        # ========= BREAKFAST =========
        breakfast_rejection_percentage = []
        breakfast_labels = []
        breakfast_total_counts = []
        breakfast_rejected_counts = []

        start_time = fixed_date.replace(
            hour=b_start.hour, minute=b_start.minute, second=0, microsecond=0)
        end_time = fixed_date.replace(
            hour=b_end.hour, minute=b_end.minute, second=0, microsecond=0)
        current_time = start_time
        breakfast_total = 0
        breakfast_total_rejected = 0

        while current_time < end_time:
            next_time = current_time + timedelta(minutes=intervals)
            weights = OrderWeight.objects.filter(
                weight_sensor__in=sensors,
                date__gte=current_time,
                date__lt=next_time,
                weight__gte=0
            )
            total = weights.count()
            breakfast_total += total
            rejected = weights.filter(
                weight__lt=b_thresh).count() if b_thresh is not None else 0

            breakfast_total_rejected += rejected
            rejection_percentage = (
                breakfast_total_rejected / breakfast_total * 100) if total > 0 else 0.0

            breakfast_total_counts.append(breakfast_total)
            breakfast_rejected_counts.append(breakfast_total_rejected)
            breakfast_rejection_percentage.append(
                round(rejection_percentage, 2))
            breakfast_labels.append(start_end_time_to_riyad(current_time))
            current_time = next_time

        # ========= LUNCH =========
        lunch_rejection_percentage = []
        lunch_labels = []
        lunch_total_counts = []
        lunch_rejected_counts = []

        start_time = fixed_date.replace(
            hour=l_start.hour, minute=l_start.minute, second=0, microsecond=0)
        end_time = fixed_date.replace(
            hour=l_end.hour, minute=l_end.minute, second=0, microsecond=0)
        current_time = start_time

        lunch_total = 0
        lunch_total_rejected = 0

        while current_time < end_time:
            next_time = current_time + timedelta(minutes=intervals)
            weights = OrderWeight.objects.filter(
                weight_sensor__in=sensors,
                date__gte=current_time,
                date__lt=next_time,
                weight__gte=0
            )
            total = weights.count()
            lunch_total += total
            rejected = weights.filter(
                weight__lt=l_thresh).count() if l_thresh is not None else 0

            lunch_total_rejected += rejected
            rejection_percentage = (
                lunch_total_rejected / lunch_total * 100) if lunch_total > 0 else 0.0

            lunch_total_counts.append(lunch_total)
            lunch_rejected_counts.append(lunch_total_rejected)
            lunch_rejection_percentage.append(round(rejection_percentage, 2))
            lunch_labels.append(start_end_time_to_riyad(current_time))
            current_time = next_time

        # ========= DINNER =========
        dinner_rejection_percentage = []
        dinner_labels = []
        dinner_total_counts = []
        dinner_rejected_counts = []

        start_time = fixed_date.replace(
            hour=d_start.hour, minute=d_start.minute, second=0, microsecond=0)
        end_time = fixed_date.replace(
            hour=d_end.hour, minute=d_end.minute, second=0, microsecond=0)
        current_time = start_time

        dinner_total = 0
        dinner_total_rejected = 0

        while current_time < end_time:
            next_time = current_time + timedelta(minutes=intervals)
            weights = OrderWeight.objects.filter(
                weight_sensor__in=sensors,
                date__gte=current_time,
                date__lt=next_time,
                weight__gte=0
            )

            total = weights.count()
            dinner_total += total

            rejected = weights.filter(
                weight__lt=d_thresh).count() if d_thresh is not None else 0

            dinner_total_rejected += rejected

            rejection_percentage = (
                dinner_total_rejected / dinner_total * 100) if dinner_total > 0 else 0.0

            dinner_total_counts.append(dinner_total)
            dinner_rejected_counts.append(dinner_total_rejected)
            dinner_rejection_percentage.append(round(rejection_percentage, 2))
            dinner_labels.append(start_end_time_to_riyad(current_time))
            current_time = next_time

        return Response({
            "success": True,
            "message": "Meal rejection data fetched successfully.",
            "data": {
                "breakfast": {
                    "labels": breakfast_labels,
                    "series": [
                        {
                            "name": "Rejection Rate",
                            "data": breakfast_rejection_percentage,
                        },
                        {
                            "name": "Processed Meals",
                            "data": breakfast_total_counts
                        },
                        {
                            "name": "Rejected Meals",
                            "data": breakfast_rejected_counts
                        }
                    ],
                },
                "lunch": {
                    "labels": lunch_labels,
                    "series": [
                        {
                            "name": "Rejection Rate",
                            "data": lunch_rejection_percentage,
                        },
                        {
                            "name": "Processed Meals",
                            "data": lunch_total_counts
                        },
                        {
                            "name": "Rejected Meals",
                            "data": lunch_rejected_counts
                        }
                    ]
                },
                "dinner": {
                    "labels": dinner_labels,
                    "series": [
                        {
                            "name": "Rejection Rate",
                            "data": dinner_rejection_percentage,
                        },
                        {
                            "name": "Processed Meals",
                            "data": dinner_total_counts
                        },
                        {
                            "name": "Rejected Meals",
                            "data": dinner_rejected_counts
                        }
                    ]
                }
            }
        }, status=status.HTTP_200_OK)
