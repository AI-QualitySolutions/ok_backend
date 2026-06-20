from django.contrib import admin
from .models import Router, RouterHeartbeat

@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    # Columns to display in the admin list view
    list_display = ('SN', 'ip_address', 'name','mac_address')
    # Add a search bar to easily find a router
    search_fields = ('SN', 'ip_address')

@admin.register(RouterHeartbeat)
class RouterHeartbeatAdmin(admin.ModelAdmin):
    list_display = ('router', 'heartbeat_time')
    # Add filters on the right sidebar
    list_filter = ('heartbeat_time', 'router')