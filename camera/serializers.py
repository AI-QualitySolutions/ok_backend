
from rest_framework import serializers
from django.conf import settings
from datetime import datetime

from camera.models import (Camera, CameraHeartbeat,
                           CounterHistory, GuardPresenceHistory,   KitchenImage,
                           KitchenViolationReport, AGGFViolationReport, SmokingViolationReport, FaceDetectionReport, GarbageMonitoringReport, RecycleMonitoringReport, FallDetectionMonitoringReport, ViolenceMonitoringReport, CrowdMonitoringReport, WallClimbMonitoringReport, AbnormalActivities, BuffetViolationReport, BathroomMonitoringHistory, SentimentAnalysis, CameraStatus, CameraType, CleanersPresenceHistory, EmptyChairDetectionReport, SecurityMonitoringReport)
from tent.models import Tent, TentGate
from django.core.exceptions import ValidationError


class CameraTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraType
        fields = ['type', 'name', 'name_ar']


class CameraStatusSerializer(serializers.ModelSerializer):
    """Simple serializer for CameraStatus model"""
    class Meta:
        model = CameraStatus
        fields = ['name']


class CameraHeartbeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraHeartbeat
        fields = ('sn', 'version', 'mac_address', 'ip_address', 'connection_type',
                  'ip_address_method', 'host_name', 'time_zone', 'hw_platform', 'report_date', 'time', 'status_log')


class TentSerializer(serializers.ModelSerializer):
    company = serializers.StringRelatedField()

    class Meta:
        model = Tent
        # Add more fields if needed
        fields = ('id', 'name', 'location', 'company', 'is_arafa')


class CameraSerializer(serializers.ModelSerializer):
    heartbeat = CameraHeartbeatSerializer(read_only=True)
    tent = TentSerializer(read_only=True)
    tent_id = serializers.PrimaryKeyRelatedField(
        queryset=Tent.objects.all(), source='tent', write_only=True
    )
    gate_id = serializers.PrimaryKeyRelatedField(
        queryset=TentGate.objects.all(), source='gate', write_only=True,
        allow_null=True, required=False
    )
    gate = serializers.SerializerMethodField(read_only=True)

    def get_gate(self, obj):
        if obj.gate:
            return {"id": obj.gate.id, "name": obj.gate.name}
        return None

    class Meta:
        model = Camera
        fields = ("id", 'sn', "type", "heartbeat", "tent", "tent_id", "gate", "gate_id")


class BuffetCameraSerializer(serializers.ModelSerializer):

    class Meta:
        model = Camera
        fields = ("id", 'sn', "tent", "video_link")


class OnlyCameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = ("id", 'sn', "type")


class GarbageMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = GarbageMonitoringReport
        fields = ('id', 'camera', 'is_clean', 'current_status', 'annotator_status',  'ai_status', 'start_time', 'end_time',
                  'image', 'created_at', 'updated_at', 'camera_type', 'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
                  "is_ai_annotated", "ai_annotation_time", "time")

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        """Handle creation of the GarbageMonitoringReport instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)
        instance = GarbageMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        # is_annotated = validated_data.get('is_annotated', None)
        #is_rejected = validated_data.get('is_rejected', False)

        #instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
            
        if "is_rejected" in validated_data:
            instance.is_rejected = validated_data["is_rejected"]

        # Apply other validated fields
        # for attr, value in validated_data.items():
        #     setattr(instance, attr, value)

        instance.save()
        return instance
    

    def to_internal_value(self, data):
        data = data.copy()

        annotator_status = data.get("annotator_status")

        # Convert list to single value
        if isinstance(annotator_status, list):
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)


class RecycleMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = RecycleMonitoringReport
        fields = ('id', 'camera', 'is_clean', 'violation_list', 'current_status', 'annotator_status', 'ai_status',
                  'start_time', 'end_time',
                  'image', 'created_at', 'updated_at', 'camera_type', 'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
                  "is_ai_annotated", "ai_annotation_time", "time")

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = RecycleMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user

        instance.save()
        return instance


class FallDetectionMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = FallDetectionMonitoringReport
        fields = (
            'id', 'camera', 'is_fall_detected', 'current_status',
            'annotator_status', 'ai_status', 'start_time', 'end_time',
            'image', 'created_at', 'updated_at', 'camera_type',
            'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
            "is_ai_annotated", "ai_annotation_time", "time"
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = FallDetectionMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request")

        annotator_status = validated_data.get("annotator_status")
        is_rejected = validated_data.get("is_rejected", False)

        # ✅ FIX: Convert list to string if needed
        if isinstance(annotator_status, list):
            annotator_status = annotator_status[0] if annotator_status else None

        instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = request.user if request else None

        instance.save()
        return instance
    def to_internal_value(self, data):
        # Convert list to string before validation
        annotator_status = data.get("annotator_status")

        if isinstance(annotator_status, list):
            data = data.copy()
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)
    
class ViolenceMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = ViolenceMonitoringReport
        fields = (
            'id', 'camera', 'is_violence', 'current_status',
            'annotator_status', 'ai_status', 'start_time', 'end_time',
            'image', 'created_at', 'updated_at', 'camera_type',
            'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
            "is_ai_annotated", "ai_annotation_time", "time"
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = ViolenceMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        # is_annotated = validated_data.get('is_annotated', None)
        #is_rejected = validated_data.get('is_rejected', False)

        #instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
            
        if "is_rejected" in validated_data:
            instance.is_rejected = validated_data["is_rejected"]

        instance.save()
        return instance
    

    def to_internal_value(self, data):
        data = data.copy()

        annotator_status = data.get("annotator_status")

        if isinstance(annotator_status, list):
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)
    
class CrowdMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()
    camera_current_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CrowdMonitoringReport
        fields = (
            'id', 'camera', 'is_crowd', 'current_status',
            'annotator_status', 'ai_status', 'start_time', 'end_time',
            'image', 'created_at', 'updated_at', 'camera_type',
            'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
            "is_ai_annotated", "ai_annotation_time", "time",
            "camera_current_status",
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def get_camera_current_status(self, obj):
        ann_status = getattr(obj, '_latest_ann_status', None)
        ann_updated = getattr(obj, '_latest_ann_updated', None)
        if ann_status is not None:
            return {"status": ann_status, "updated_at": ann_updated}

        latest = (
            CrowdMonitoringReport.objects
            .filter(camera=obj.camera, is_annotated=True)
            .order_by('-updated_at')
            .values('annotator_status', 'updated_at')
            .first()
        )
        if latest:
            return {
                "status": latest['annotator_status'],
                "updated_at": latest['updated_at'],
            }
        return None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = CrowdMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        # is_annotated = validated_data.get('is_annotated', None)
        #is_rejected = validated_data.get('is_rejected', False)

        #instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
            
        if "is_rejected" in validated_data:
            instance.is_rejected = validated_data["is_rejected"]

        instance.save()
        return instance
    
    
    def to_internal_value(self, data):
        data = data.copy()

        annotator_status = data.get("annotator_status")

        # Convert list → single value
        if isinstance(annotator_status, list):
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)
    
    
class WallClimbMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = WallClimbMonitoringReport
        fields = (
            'id', 'camera', 'is_climb', 'current_status',
            'annotator_status', 'ai_status', 'start_time', 'end_time',
            'image', 'created_at', 'updated_at', 'camera_type',
            'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
            "is_ai_annotated", "ai_annotation_time", "time"
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = WallClimbMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        # is_annotated = validated_data.get('is_annotated', None)
        #is_rejected = validated_data.get('is_rejected', False)

        #instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
            
        if "is_rejected" in validated_data:
            instance.is_rejected = validated_data["is_rejected"]

        instance.save()
        return instance

    def to_internal_value(self, data):
        data = data.copy()

        annotator_status = data.get("annotator_status")

        # Convert list → single value
        if isinstance(annotator_status, list):
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)


class AbnormalActivitiesSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = AbnormalActivities
        fields = (
            'id', 'camera', 'is_motion_detected', 'current_status',
            'annotator_status', 'ai_status', 'start_time', 'end_time',
            'image', 'created_at', 'updated_at', 'camera_type',
            'is_annotated', 'tent_name', 'camera_sn', 'is_rejected',
            "is_ai_annotated", "ai_annotation_time", "time"
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = AbnormalActivities.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        # is_annotated = validated_data.get('is_annotated', None)
        #is_rejected = validated_data.get('is_rejected', False)

        #instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
            
        if "is_rejected" in validated_data:
            instance.is_rejected = validated_data["is_rejected"]

        instance.save()
        return instance

    def to_internal_value(self, data):
        data = data.copy()

        annotator_status = data.get("annotator_status")

        # Convert list → single value
        if isinstance(annotator_status, list):
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)

class GuardPresenceHistorySerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = GuardPresenceHistory
        fields = ('id', 'camera', 'present', "current_status", 'camera_sn', 'annotator_status', 'ai_status', 'guard_count', 'start_time', 'end_time',
                  'image', 'created_at', 'updated_at', 'camera_type', 'is_annotated', 'tent_name', 'is_rejected', "is_ai_annotated", "ai_annotation_time", "time")

    def get_time(self, obj):
        return obj.start_time

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        """Handle creation of the CleanIndicatorHistory instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)
        instance = GuardPresenceHistory.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)
        request = self.context.get('request')

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = request.user

        instance.save()

        return instance
    def to_internal_value(self, data):
        data = data.copy()

        annotator_status = data.get("annotator_status")

        # Convert list to single value
        if isinstance(annotator_status, list):
            data["annotator_status"] = annotator_status[0] if annotator_status else None

        return super().to_internal_value(data)


class GuardPresenceHistoryChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardPresenceHistory
        fields = ('guard_count', 'updated_at')


class CounterHistorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CounterHistory
        fields = ('camera', 'sn', 'total_in', 'total_out', 'passby', 'turnback', 'avg_stay_time', 'in_adult', 'out_adult', 'passby_adult',
                  'turnback_adult', 'in_child', 'out_child', 'passby_child', 'turnback_child', 'total', 'start_time', 'end_time', 'created_at', 'updated_at', 'image', 'image_url')

    def get_image_url(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None


class CreateCounterHistorySerializer(serializers.ModelSerializer):
    out = serializers.IntegerField(source="total_out")
    avgStayTime = serializers.IntegerField(source="avg_stay_time")
    startTime = serializers.IntegerField()
    endTime = serializers.IntegerField()

    class Meta:
        model = CounterHistory
        fields = [
            "sn",
            "total_in",
            "out",
            "passby",
            "turnback",
            "avgStayTime",
            "in_adult",
            "out_adult",
            "passby_adult",
            "turnback_adult",
            "in_child",
            "out_child",
            "passby_child",
            "turnback_child",
            "total",
            "startTime",
            "endTime",
            "image"
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        start_time = None
        try:
            start_time = validated_data.pop("startTime")
            start_time = datetime.fromtimestamp(start_time)
        except:
            start_time = None
        end_time = None
        end_time = validated_data.pop("endTime")
        end_time = datetime.fromtimestamp(end_time)
        image = request.FILES.get("image", None)
        sn = validated_data.get("sn", None)
        camera = None
        if sn:
            cameras = Camera.objects.filter(sn=sn)
            if cameras.exists():
                camera = cameras[0]
                camera.save()
            else:
                camera = Camera.objects.create(sn=str(sn), tent=None)
        else:
            raise Exception("error")
        history = CounterHistory.objects.create(
            camera=camera, start_time=start_time, end_time=end_time, image=image, **validated_data
        )
        return history


class KitchenImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = KitchenImage
        fields = ('camera', 'image', 'location')

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        """Handle creation of the CleanIndicatorHistory instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)
        instance = KitchenImage.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance


class KitchenViolationReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(source="image")
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = KitchenViolationReport
        fields = ("id", "current_status", "camera", "image", "image_url", "annotator_status", "ai_status", "camera_type", "camera_sn", "violation_list",
                  "violation", "start_time", "end_time", "created_at", "updated_at", "is_annotated", "tent_name", "is_rejected", "time")

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def get_image_url(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        """Handle creation of the BuffetViolationReport instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)

        instance = KitchenViolationReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
        instance.save()
        return instance

# don't modify


class AGGFViolationReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(source="image")
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = AGGFViolationReport
        fields = ("id", "current_status", "camera", "image", "image_url", "annotator_status", "ai_status", "camera_type", "camera_sn", "violation_list",
                  "violation", "start_time", "end_time", "created_at", "updated_at", "is_annotated", "tent_name", "is_rejected", "time")

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def get_image_url(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        """Handle creation of the BuffetViolationReport instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)

        instance = AGGFViolationReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
        instance.save()
        return instance

class SmokingViolationReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(source="image")
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = SmokingViolationReport
        fields = ("id", "current_status", "camera", "image", "image_url", "annotator_status", "ai_status", "camera_type", "camera_sn", "violation_list",
                  "violation", "start_time", "end_time", "created_at", "updated_at", "is_annotated", "tent_name", "is_rejected", "time")

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def get_image_url(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None
    def create(self, validated_data):
        """Handle creation of the BuffetViolationReport instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)

        instance = SmokingViolationReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
        instance.save()
        return instance

class FaceDetectionReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FaceDetectionReport
        fields = (
            "id",
            "camera",
            "camera_type",
            "camera_sn",
            "tent_name",
            "name",          # ✅ single person name
            "time",          # ✅ detection time
            "image",
            "image_url",
            "is_annotated",
            "is_rejected",
            "created_at",
            "updated_at",
        )

    # ----------------------------
    # Derived fields
    # ----------------------------
    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera and obj.camera.tent else None

    def get_image_url(self, obj):
        if not obj.image:
            return None

        if settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"

        return obj.image.url

    # ----------------------------
    # Create
    # ----------------------------
    def create(self, validated_data):
        request = self.context.get("request")
        image = request.FILES.get("image") if request else None

        instance = FaceDetectionReport.objects.create(**validated_data)

        if image:
            instance.image = image
            instance.save(update_fields=["image"])

        return instance

    # ----------------------------
    # Update (annotation / reject)
    # ----------------------------
    def update(self, instance, validated_data):
        instance.is_rejected = validated_data.get(
            "is_rejected", instance.is_rejected
        )

        if validated_data.get("is_annotated", False):
            instance.is_annotated = True
            if self.context.get("request"):
                instance.annotator = self.context["request"].user

        instance.save()
        return instance


class BuffetAiAnnotationSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BuffetViolationReport
        fields = ("id", "camera", "violation", "violation_list",
                  "is_ai_annotated", "ai_annotation_time", "image", "image_url")
        extra_kwargs = {
            "image": {"required": False, "allow_null": True},
        }

    def get_image_url(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None


class BuffetViolationReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = BuffetViolationReport
        fields = ("id", "camera", "current_status", "image", "image_url", "camera_type", "camera_sn", "violation_list", "ai_status", "annotator_status",
                  "violation", "start_time", "end_time", "created_at", "updated_at", "is_annotated", "is_ai_annotated", "ai_annotation_time", "tent_name", 'is_rejected', 'time')

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def get_image_url(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        """Handle creation of the BuffetViolationReport instance."""
        # Extract image from validated data
        # Using the request context for file upload
        image = self.context['request'].FILES.get('image', None)

        instance = BuffetViolationReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
        instance.save()
        return instance


class BathroomMonitoringHistorySerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = BathroomMonitoringHistory
        fields = ['id', 'camera', 'cleaner_count', "current_status", 'present',
                  'annotator_status', 'start_time', 'end_time', 'ai_status', 'is_annotated', 'tent_name', "camera_sn", "image", "image_url", "camera_type", 'is_rejected', 'time']

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def get_image_url(self, obj):
        # Check if the image exists and if DEBUG is True
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        # Return the default URL if not in DEBUG mode or image doesn't exist
        return obj.image.url if obj.image else None

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)
        instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user
        instance.save()
        return instance


class TentViolationSummarySerializer(serializers.ModelSerializer):
    violation_count = serializers.IntegerField()

    class Meta:
        model = Tent
        fields = ['id', 'name', 'violation_count']


class CameraViolationSummarySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='tent.name')
    camera = serializers.CharField(source='sn')  # Camera name field
    violation_count = serializers.IntegerField()

    class Meta:
        model = Camera
        fields = ['id', 'camera', 'name', 'violation_count']


class SentimentAnalysisSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = SentimentAnalysis
        fields = [
            "id", "camera", "camera_sn", "camera_type", "current_status",
            "sentiment_list", "annotator_status", "average_sentiment", "version",
            "mac_address", "ip_address", "connection_type",
            "ip_address_method", "host_name", "time_zone",
            "hw_platform", "report_date", "start_time",
            "end_time", "image", "image_url", "is_ai_annotated", "ai_annotation_time", "ai_status", "is_annotated", "is_rejected", "tent_name"
        ]

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def get_image_url(self, obj):
        return self.get_image(obj)

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = SentimentAnalysis.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class CleanersPresenceHistorySerializer(serializers.ModelSerializer):
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField(read_only=True)
    annotator_status = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = CleanersPresenceHistory
        fields = [
            'id', 'camera', 'camera_sn', 'tent_name', 'camera_type',
            'person_class', 'annotator_status', 'current_status',
            'cleaner_count', 'start_time', 'end_time',
            'image', 'is_annotated', 'is_rejected', 'annotator',
            'created_at', 'updated_at',
        ]

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera and obj.camera.tent else None

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def get_current_status(self, obj):
        return obj.current_status

    def to_internal_value(self, data):
        annotator_status = data.get('annotator_status')
        if isinstance(annotator_status, list):
            person_classes = [c[0] for c in CleanersPresenceHistory.PERSON_CLASS_CHOICES]
            filtered = [v for v in annotator_status if v not in person_classes]
            data = {**data, 'annotator_status': filtered[-1] if filtered else (annotator_status[-1] if annotator_status else None)}
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status')

        is_rejected = validated_data.get('is_rejected', False)
        instance.is_rejected = is_rejected

        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user

        instance.save()
        return instance


class EmptyChairDetectionReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = EmptyChairDetectionReport
        fields = (
            'id', 'camera', 'empty_chair_count', 'total_chair_count',
            'is_empty_detected', 'current_status', 'annotator_status',
            'ai_status', 'start_time', 'end_time', 'image',
            'created_at', 'updated_at', 'camera_type', 'is_annotated',
            'tent_name', 'camera_sn', 'is_rejected',
            'is_ai_annotated', 'ai_annotation_time', 'time',
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera and obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = EmptyChairDetectionReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)

        if annotator_status is not None:
            instance.annotator_status = str(annotator_status)
            instance.is_annotated = True
            instance.annotator = self.context['request'].user

        if 'is_rejected' in validated_data:
            instance.is_rejected = validated_data['is_rejected']

        instance.save()
        return instance

    def to_internal_value(self, data):
        data = data.copy()
        annotator_status = data.get('annotator_status')
        if isinstance(annotator_status, list):
            data['annotator_status'] = annotator_status[0] if annotator_status else None
        return super().to_internal_value(data)


class SecurityMonitoringReportSerializer(serializers.ModelSerializer):
    camera_type = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    camera_sn = serializers.SerializerMethodField(read_only=True)
    tent_name = serializers.SerializerMethodField(read_only=True)
    time = serializers.SerializerMethodField()

    class Meta:
        model = SecurityMonitoringReport
        fields = (
            'id', 'camera', 'is_safe', 'violation_list', 'current_status', 'annotator_status',
            'ai_status', 'start_time', 'end_time', 'image',
            'created_at', 'updated_at', 'camera_type', 'is_annotated',
            'tent_name', 'camera_sn', 'is_rejected',
            'is_ai_annotated', 'ai_annotation_time', 'time',
        )

    def get_time(self, obj):
        return obj.created_at

    def get_camera_type(self, obj):
        return obj.camera.type if obj.camera else None

    def get_camera_sn(self, obj):
        return obj.camera.sn if obj.camera else None

    def get_tent_name(self, obj):
        return obj.camera.tent.name if obj.camera and obj.camera.tent else None

    def get_image(self, obj):
        if obj.image and settings.DEBUG:
            return f"{settings.BASE_URL}{obj.image.url}"
        return obj.image.url if obj.image else None

    def create(self, validated_data):
        image = self.context['request'].FILES.get('image', None)
        instance = SecurityMonitoringReport.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        annotator_status = validated_data.get('annotator_status', None)
        is_rejected = validated_data.get('is_rejected', False)

        instance.is_rejected = is_rejected
        if annotator_status is not None:
            instance.annotator_status = annotator_status
            instance.is_annotated = True
            instance.annotator = self.context['request'].user

        instance.save()
        return instance
