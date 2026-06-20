from django.contrib import admin

from .models import TuyaProxyApiKey


@admin.register(TuyaProxyApiKey)
class TuyaProxyApiKeyAdmin(admin.ModelAdmin):
    list_display = ("tuya_user_id", "api_key", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("tuya_user_id", "api_key", "metadata")
    readonly_fields = ("api_key", "created_at", "updated_at")
