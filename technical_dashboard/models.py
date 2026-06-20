from django.db import models
from authentication.models import BaseModel, Company
from tent.models import Tent


class OrangePiDevice(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name='orangepi_devices')
    tent = models.ForeignKey(
        Tent, on_delete=models.CASCADE, null=True, blank=True, related_name='orangepi_devices')
    name = models.CharField(max_length=255)
    device_id = models.CharField(max_length=255, unique=True)
    mac_address = models.CharField(
        max_length=17, unique=True, help_text="Format: AA:BB:CC:DD:EE:FF")
    port = models.IntegerField(default=8000)
    last_seen = models.DateTimeField(null=True, blank=True)
    online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} | {self.device_id}"


class DeviceActivityLog(BaseModel):
    DEVICE_TYPE_CHOICES = [
        ('camera', 'Camera'),
        ('orange_pi', 'Orange Pi'),
        ('access_point', 'Access Point'),
    ]
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField()

    camera = models.ForeignKey(
        'camera.Camera', on_delete=models.CASCADE,
        null=True, blank=True, related_name='activity_logs')
    orange_pi_device = models.ForeignKey(
        'technical_dashboard.OrangePiDevice', on_delete=models.CASCADE,
        null=True, blank=True, related_name='activity_logs')
    access_point = models.ForeignKey(
        'access_point.Router', on_delete=models.CASCADE,
        null=True, blank=True, related_name='activity_logs')

    details = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['device_type', 'timestamp']),
            models.Index(fields=['device_type', 'camera']),
            models.Index(fields=['device_type', 'orange_pi_device']),
            models.Index(fields=['device_type', 'access_point']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        device_label = ''
        if self.device_type == 'camera' and self.camera:
            device_label = self.camera.sn
        elif self.device_type == 'orange_pi' and self.orange_pi_device:
            device_label = self.orange_pi_device.device_id
        elif self.device_type == 'access_point' and self.access_point:
            device_label = self.access_point.SN
        return f"[{self.device_type}] {device_label} -> {self.status} @ {self.timestamp}"