from django.contrib import admin
from .models import LiveStream
 
 
@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display  = ('sn', 'tent_name', 'hls_url', 'is_active', 'created_at')
    list_filter   = ('is_active', 'camera__tent')
    search_fields = ('camera__sn', 'camera__tent__name')
    readonly_fields = ('hls_url', 'sn', 'tent_name', 'created_at', 'updated_at')
 
    def sn(self, obj):
        return obj.camera.sn
    sn.short_description = 'Camera SN'
 
    def tent_name(self, obj):
        return obj.camera.tent.name if obj.camera.tent else '—'
    tent_name.short_description = 'Tent'
 
    def hls_url(self, obj):
        return obj.hls_url
    hls_url.short_description = 'HLS URL'
 