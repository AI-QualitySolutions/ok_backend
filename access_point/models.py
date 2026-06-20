from django.db import models


class Router(models.Model):
    SN = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    mac_address = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.SN

class RouterHeartbeat(models.Model):
    # Establish a one-to-many relationship with the Router model
    router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name='heartbeats')
    # Store the exact time the heartbeat was received
    heartbeat_time = models.DateTimeField()

    def __str__(self):
        return f"{self.router.SN} - {self.heartbeat_time}"