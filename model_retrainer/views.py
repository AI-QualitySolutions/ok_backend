from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from datetime import datetime, time
from utils.time import saudi_tz

from camera.models import (
    KitchenViolationReport, GuardPresenceHistory, BuffetViolationReport,
    SentimentAnalysis, GarbageMonitoringReport, RecycleMonitoringReport, FallDetectionMonitoringReport,
    ViolenceMonitoringReport, CrowdMonitoringReport, WallClimbMonitoringReport,
    AbnormalActivities, BathroomMonitoringHistory, AGGFViolationReport,
    SmokingViolationReport
)

# Registry: (model_class, display_name, only_fields for accuracy loop)
# only_fields = annotator_status + columns read by ai_status property
MODEL_REGISTRY = {
    'kitchen':           (KitchenViolationReport,         "Kitchen Model",            ('annotator_status', 'violation_list')),
    'guard':             (GuardPresenceHistory,            "Guard Model",              ('annotator_status', 'guard_count')),
    'buffet':            (BuffetViolationReport,           "Buffet Model",             ('annotator_status', 'violation_list')),
    'sentiment':         (SentimentAnalysis,               "Sentiment Model",          ('annotator_status', 'average_sentiment')),
    'garbage':           (GarbageMonitoringReport,         "Garbage Model",            ('annotator_status', 'is_clean')),
    'recycle':           (RecycleMonitoringReport,         "Recycle Model",            ('annotator_status', 'violation_list')),
    'fall_detection':    (FallDetectionMonitoringReport,   "Fall Detection Model",     ('annotator_status', 'is_fall_detected')),
    'violence':          (ViolenceMonitoringReport,        "Violence Detection Model", ('annotator_status', 'is_violence')),
    'crowd':             (CrowdMonitoringReport,           "Crowd Monitoring Model",   ('annotator_status', 'is_crowd')),
    'wall_climb':        (WallClimbMonitoringReport,       "Wall Climb Model",         ('annotator_status', 'is_climb')),
    'abnormal_activity': (AbnormalActivities,              "Abnormal Activity Model",  ('annotator_status', 'is_motion_detected')),
    'bathroom':          (BathroomMonitoringHistory,       "Bathroom Model",           ('annotator_status', 'cleaner_count')),
    'aggf':              (AGGFViolationReport,             "AGGF Model",               ('annotator_status', 'violation_list')),
    'smoking':           (SmokingViolationReport,          "Smoking Model",            ('annotator_status', 'violation_list')),
}

class UniversalAccuracyAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # 1. Get the requested model type
        model_type = request.GET.get('type')
        
        if not model_type or model_type not in MODEL_REGISTRY:
            return Response({
                "error": f"Please provide a valid 'type' parameter. Available types: {', '.join(MODEL_REGISTRY.keys())}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. Extract specific model class and name based on type
        model_class, model_name, only_fields = MODEL_REGISTRY[model_type]

        # 3. Date handling logic (Asia/Riyadh Timezone)
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        now = datetime.now(saudi_tz)

        if not start_date_str and not end_date_str:
            start_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            try:
                if start_date_str:
                    start_datetime = parse_datetime(start_date_str)
                    if not start_datetime:
                        start_dt_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
                        start_datetime = make_aware(datetime.combine(start_dt_obj, time.min), saudi_tz)
                    elif start_datetime.tzinfo is None:
                        start_datetime = make_aware(start_datetime, saudi_tz)
                else:
                    start_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)

                if end_date_str:
                    end_datetime = parse_datetime(end_date_str)
                    if not end_datetime:
                        end_dt_obj = datetime.strptime(end_date_str, '%Y-%m-%d')
                        end_datetime = make_aware(datetime.combine(end_dt_obj, time.max), saudi_tz)
                    elif end_datetime.tzinfo is None:
                        end_datetime = make_aware(end_datetime, saudi_tz)
                else:
                    end_datetime = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            except ValueError:
                return Response({"error": "Invalid format. Use YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if start_datetime > end_datetime:
            return Response({"error": "Start datetime cannot be after end datetime."}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Total records in DB (Total AI Processed Images)
        total_image_count = model_class.objects.filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).count()

        # 5. Total records that a human has annotated
        annotated_records = model_class.objects.filter(
            is_annotated=True, 
            is_rejected=False,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        )

        total_human_annotated = annotated_records.count()
        start_formatted = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        end_formatted = end_datetime.strftime('%Y-%m-%d %H:%M:%S')

        # Handle edge case where no data is annotated yet
        if total_human_annotated == 0:
            return Response({
                "model_name": model_name,
                "start_timestamp": start_formatted,
                "end_timestamp": end_formatted,
                "total_image_count": total_image_count,
                "total_human_annotated_data": 0,
                "total_correct_ai_predictions": 0,
                "accuracy_percentage": 0
            }, status=status.HTTP_200_OK)

        exact_matches = 0

        # Safe normalizer to compare Human vs AI outputs properly
        def normalize_output(val):
            if not val:
                return set()
            if isinstance(val, str):
                return {val.strip().lower()}
            if isinstance(val, list):
                return set([str(x).strip().lower() for x in val])
            if isinstance(val, dict):
                return set([str(x).strip().lower() for x in val.keys()])
            try:
                return set([str(x).strip().lower() for x in val])
            except TypeError:
                return {str(val).strip().lower()}
        
        # 6. Compare AI vs Human
        for record in annotated_records.only(*only_fields).iterator(chunk_size=2000):
            human_output = normalize_output(record.annotator_status)
            ai_output = normalize_output(record.ai_status)

            if human_output == ai_output:
                exact_matches += 1

        # 7. Calculate accuracy percentage
        accuracy_percentage = (exact_matches / total_human_annotated) * 100 if total_human_annotated > 0 else 0

        return Response({
            "model_name": model_name,
            "start_timestamp": start_formatted,
            "end_timestamp": end_formatted,
            "total_image_count": total_image_count,
            "total_human_annotated_data": total_human_annotated,
            "total_correct_ai_predictions": exact_matches,
            "accuracy_percentage": round(accuracy_percentage, 2)
        }, status=status.HTTP_200_OK)