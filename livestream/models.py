from django.db import models
from camera.models import Camera


class LiveStream(models.Model):
    camera = models.OneToOneField(
        Camera,
        on_delete=models.CASCADE,
        related_name='livestream',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def hls_url(self):
        return f"https://dashboard.aiqualitysolutions.com/hls/camera-{self.camera.sn}/index.m3u8"

    @property
    def sn(self):
        return self.camera.sn

    @property
    def tent_name(self):
        return self.camera.tent.name if self.camera.tent else None

    @property
    def tent_id(self):
        return self.camera.tent.id if self.camera.tent else None

    def __str__(self):
        return f"LiveStream — {self.camera.sn}"

    class Meta:
        verbose_name = "Live Stream"
        verbose_name_plural = "Live Streams"