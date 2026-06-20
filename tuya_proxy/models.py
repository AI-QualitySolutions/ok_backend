import uuid

from django.db import models

from authentication.models import BaseModel


class TuyaProxyApiKey(BaseModel):
    api_key = models.CharField(max_length=36, unique=True, db_index=True, blank=True)
    tuya_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tuya_user_id} ({self.api_key[:8]}...)"

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = str(uuid.uuid4())
        super().save(*args, **kwargs)
