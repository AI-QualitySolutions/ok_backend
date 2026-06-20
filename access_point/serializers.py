from rest_framework import serializers

class DevicePayloadSerializer(serializers.Serializer):
    # Define the expected fields from the incoming POST request
    SN = serializers.CharField(max_length=100)
    ip_address = serializers.IPAddressField()
    mac_address = serializers.CharField(max_length=50, required=False, allow_blank=True)
    heartbeat_time = serializers.DateTimeField()