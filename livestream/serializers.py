from rest_framework import serializers
from .models import LiveStream
 
 
class LiveStreamSerializer(serializers.ModelSerializer):
    hls_url   = serializers.ReadOnlyField()
    sn        = serializers.ReadOnlyField()
    tent_name = serializers.ReadOnlyField()
    tent_id   = serializers.ReadOnlyField()

    class Meta:
        model  = LiveStream
        fields = ('id', 'sn', 'tent_id', 'tent_name', 'hls_url')