from django.contrib import admin

from camera.models import (AbnormalActivities, Camera, CrowdMonitoringReport,
                           GuardPresenceHistory, CounterHistory,
                           CameraHeartbeat,  KitchenImage, KitchenViolationReport,
                           GarbageMonitoringReport, RecycleMonitoringReport, BuffetViolationReport, BathroomMonitoringHistory, SentimentAnalysis, CameraStatus, CameraType, FallDetectionMonitoringReport, ViolenceMonitoringReport, WallClimbMonitoringReport,
                           CleanersPresenceHistory)

from .people_count_admin import *
# Register your models here
@admin.register(CameraType)
class CameraTypeAdmin(admin.ModelAdmin):
    search_fields = ['type']
    list_display = ['id', 'type']
admin.site.register(CameraStatus)


@admin.register(CameraHeartbeat)
class CameraHeartbeatAdmin(admin.ModelAdmin):
    search_fields = ["mac_address", "camera__sn"]
    list_display = ['id', 'camera', 'sn', 'time', 'version', 'updated_at', "status_log"]
    list_filter = ['created_at', "camera__tent__company__name"]


@admin.register(KitchenImage)
class KitchenImageAdmin(admin.ModelAdmin):
    search_fields = ['created_at', 'tent__id', "camera__id"]
    list_display = ['id', 'tent', 'camera', 'location']


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    search_fields = ['sn', 'id']
    list_display = ['id', 'tent', 'sn', 'type', 'gate']
    list_filter = ['type', 'tent__company__name']
    autocomplete_fields = ['tent', 'gate']

@admin.register(KitchenViolationReport)
class KitchenViolationReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id",  "camera__sn"]
    list_display = ['id', 'camera', 'violation', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', "camera__tent__company__name", 'violation']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="kitchen")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(GuardPresenceHistory)
class GuardPresenceHistoryAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn", "image"]
    list_display = ['id', 'camera', 'present', "is_rejected", 'current_status', 'start_time', 'end_time', 'created_at', 'updated_at']
    list_filter = ['created_at', "present", "is_rejected", "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="guard")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# @admin.register(CounterHistory)
# class CounterHistoryAdmin(admin.ModelAdmin):
#     search_fields = ['id', "sn", "camera__id", "camera__sn"]
#     list_display = ['id', 'camera', 'total_in', 'total_out', "end_time" , 'created_at', ]
#     list_filter = ['created_at', "camera__tent__company__name"]

#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "camera":
#             kwargs["queryset"] = Camera.objects.filter(type="peoplecount")
#         return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(GarbageMonitoringReport)
class GarbageMonitoringReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_clean', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_clean', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="garbage")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(RecycleMonitoringReport)
class RecycleMonitoringReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_clean', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_clean', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="recycle")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(FallDetectionMonitoringReport)
class FallDetectionMonitoringReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_fall_detected', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_fall_detected', "camera__tent__company__name"]
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="fall_detection")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
@admin.register(ViolenceMonitoringReport)
class ViolenceMonitoringReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_violence', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_violence', "camera__tent__company__name"]
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="violence")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(CrowdMonitoringReport)
class CrowdMonitoringReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_crowd', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_crowd', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="crowd")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
@admin.register(WallClimbMonitoringReport)
class WallClimbMonitoringReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_climb', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_climb', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="climb")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
@admin.register(AbnormalActivities)
class AbnormalActivitiesAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'is_motion_detected', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'is_motion_detected', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="abnormalactivity")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(BuffetViolationReport)
class BuffetViolationReportAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'violation', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'violation', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="buffet")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(BathroomMonitoringHistory)
class BathroomMonitoringHistoryAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'present', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'present', "camera__tent__company__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="bathroom")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    search_fields = ['id', "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'average_sentiment', 'start_time', 'end_time', 'created_at']
    list_filter = ['created_at', 'average_sentiment',
                   "camera__tent__company__name", "is_annotated"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="sentiment")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)




@admin.register(CleanersPresenceHistory)
class CleanersPresenceHistoryAdmin(admin.ModelAdmin):
    search_fields = ['id', 'camera__id', 'camera__sn']
    list_display = ['id', 'camera', 'person_class', 'cleaner_count', 'start_time', 'end_time', 'created_at']
    list_filter = ['person_class', 'created_at', 'camera__tent__company__name']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="cleaners")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
