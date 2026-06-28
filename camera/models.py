from django.db import models
from django.core.exceptions import ValidationError
from authentication.models import BaseModel, MyUser
from tent.models import Tent, TentGate

from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

type_choices = [
    ("guard", "guard"),
    ("kitchen", "kitchen"),
    ("garbage", "garbage"),
    ("recycle", "recycle"),
    ("buffet", "buffet"),
    ("bathroom", "bathroom"),
    ("sentiment", "sentiment"),
    ("peoplecount", "peoplecount"),
    ("employeeactivity", "employeeactivity"),
    ("smoking", "smoking"),
    ("facedetection", "facedetection"),
    ("falldetection", "falldetection"),
    ("violencedetection", "violencedetection"),
    ("crowdmonitoring", "crowdmonitoring"),
    ("climbmonitoring", "climbmonitoring"),
    ("abnormalactivity", "abnormalactivity"),
    ("livestream", "livestream"),
    ("cleaners", "cleaners"),
    ("chairdetection", "chairdetection"),
    ("security", "security"),
]


class CameraType(models.Model):
    """Model to store individual camera types"""
    type = models.CharField(max_length=255, choices=type_choices, unique=True)
    name = models.CharField(
        max_length=255, default=None, null=True, blank=True)
    name_ar = models.CharField(
        max_length=255, default=None, null=True, blank=True)

    def __str__(self):
        return self.type


class CameraStatus(models.Model):
    """Camera status model that can have multiple types"""
    name = models.CharField(max_length=255)
    type = models.ForeignKey(
        CameraType, on_delete=models.CASCADE, related_name="camera_statuses")

    def __str__(self):
        return self.name


class Camera(BaseModel):
    sn = models.CharField(max_length=255, unique=True)
    tent = models.ForeignKey(
        Tent, on_delete=models.SET_NULL, null=True, blank=True, related_name="camera")
    heart_beat_time = models.DateTimeField(auto_now_add=True)
    type = models.CharField(
        max_length=255, choices=type_choices, default="guard")
    video_link = models.URLField(null=True, blank=True)
    gate = models.ForeignKey(
        TentGate, on_delete=models.SET_NULL, null=True, blank=True, related_name='cameras')

    class Meta:
        indexes = [
            models.Index(fields=["tent", "type"], name="cam_tent_type_idx"),
        ]

    def __str__(self):
        company_name = self.tent.company.name if self.tent and self.tent.company else "No Company"
        tent_name = self.tent.name if self.tent else "No Tent"
        tent_pk = self.tent.pk if self.tent else "No Tent"
        return f"{company_name} - tent_name:{tent_name}->tent_pk:{tent_pk} -> {self.sn}"

    def clean(self):
        if self.sn and self.tent and self.tent.company:
            existing = Camera.objects.filter(
                sn=self.sn,
                tent__company=self.tent.company
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    f"Camera with SN '{self.sn}' already exists in this company.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class GuardPresenceHistory(BaseModel):
    ANNOTATOR_CHOICES = [
        ('absent', 'absent'),
    ] + [(str(i), str(i)) for i in range(1, 9)]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE,
                               null=False, blank=False, related_name="guard_presence_histories")
    guard_count = models.IntegerField(default=0)
    present = models.BooleanField(default=False)
    annotator_status = models.CharField(
        max_length=10, choices=ANNOTATOR_CHOICES, default='absent', blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='guard_presence_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='guard_presence_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "start_time", "-end_time"],
                name="guard_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="guard_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return [str(self.guard_count)] if self.guard_count > 0 else ["absent"]

    def save(self, *args, **kwargs):
        self.current_status = [
            self.annotator_status] if self.is_annotated else self.ai_status

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]
            if status_value == "absent":
                self.present = False
            else:
                try:
                    self.present = int(status_value) > 0
                except ValueError:
                    self.present = False
        else:
            self.present = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Guard Presence History for Camera SN: {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"


class KitchenViolationReport(BaseModel):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="kitchen_violation_histories")
    violation = models.BooleanField(default=False)
    violation_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='kitchen_violation_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='kitchen_violation_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="kitchen_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="kitchen_acc_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.current_status = self.annotator_status if self.is_annotated else self.violation_list
        if isinstance(self.current_status, (list, dict)):
            self.violation = len(self.current_status) > 0
        else:
            self.violation = False
        super().save(*args, **kwargs)

    @property
    def ai_status(self):
        return self.violation_list

    def __str__(self):
        return f"Violation Report for Camera {self.camera.tent.company.name} at {self.start_time}"


class AGGFViolationReport(BaseModel):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="aggf_violation_histories")
    violation = models.BooleanField(default=False)
    violation_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='aggf_violation_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='aggf_violation_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="aggf_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="aggf_acc_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.current_status = self.annotator_status if self.is_annotated else self.violation_list
        if isinstance(self.current_status, (list, dict)):
            self.violation = len(self.current_status) > 0
        else:
            self.violation = False
        super().save(*args, **kwargs)

    @property
    def ai_status(self):
        return self.violation_list

    def __str__(self):
        return f"Violation Report for Camera {self.camera.tent.company.name} at {self.start_time}"

class SmokingViolationReport(BaseModel):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="smoking_violation_histories")
    violation = models.BooleanField(default=False)
    violation_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='smoking_violation_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='smoking_violation_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="smoking_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="smoking_acc_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.current_status = self.annotator_status if self.is_annotated else self.violation_list
        if isinstance(self.current_status, (list, dict)):
            self.violation = len(self.current_status) > 0
        else:
            self.violation = False
        super().save(*args, **kwargs)

    @property
    def ai_status(self):
        return self.violation_list

    def __str__(self):
        return f"Violation Report for Camera {self.camera.tent.company.name} at {self.start_time}"
    
class FaceDetectionReport(BaseModel):
    camera = models.ForeignKey(
        'camera.Camera',
        on_delete=models.CASCADE,
        related_name="face_detection_histories"
    )

    # Single detected person name (from camera recognition)
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Recognized person name from camera"
    )

    time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time when face was detected"
    )

    image = models.ImageField(
        upload_to='face_detection_history/%Y/%m/%d/',
        null=True,
        blank=True
    )

    is_annotated = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='face_detection_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="face_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
        ]

    def __str__(self):
        return (
            f"FaceDetectionReport | "
            f"Camera={self.camera_id} | "
            f"Name={self.name or 'Unknown'} | "
            f"Time={self.time}"
        )

class CounterHistory(BaseModel):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    sn = models.CharField(max_length=255)
    total_in = models.IntegerField(default=0)
    total_out = models.IntegerField(default=0)
    passby = models.IntegerField(default=0)
    turnback = models.IntegerField(default=0)
    avg_stay_time = models.IntegerField(default=0)
    in_adult = models.IntegerField(default=0)
    out_adult = models.IntegerField(default=0)
    passby_adult = models.IntegerField(default=0)
    turnback_adult = models.IntegerField(default=0)
    in_child = models.IntegerField(default=0)
    out_child = models.IntegerField(default=0)
    passby_child = models.IntegerField(default=0)
    turnback_child = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(
        upload_to='counter_image/%Y/%m/%d/', default="", blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["camera", "end_time"], name="counter_cam_end_idx"),
            models.Index(fields=["camera", "created_at"], name="counter_cam_created_idx"),
        ]

    def save(self, *args, **kwargs):
        self.total = self.total_in - self.total_out
        super().save(*args, **kwargs)


class CameraHeartbeat(BaseModel):
    camera = models.OneToOneField(
        Camera, on_delete=models.CASCADE, related_name='heartbeat')
    sn = models.CharField(max_length=255)
    version = models.CharField(max_length=50, null=True, blank=True)
    mac_address = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.CharField(max_length=255, null=True, blank=True)
    connection_type = models.CharField(max_length=255, null=True, blank=True)
    ip_address_method = models.CharField(max_length=255, null=True, blank=True)
    host_name = models.CharField(max_length=255, null=True, blank=True)
    time_zone = models.IntegerField(null=True, blank=True)
    hw_platform = models.CharField(max_length=255, null=True, blank=True)
    report_date = models.DateField(null=True, blank=True)
    time = models.DateTimeField(null=True, blank=True)
    status_log = models.TextField(null=True, blank=True, default="")

    def __str__(self):
        return f"Heartbeat from {self.camera.sn}"


class KitchenImage(BaseModel):
    # Fields remain the same
    tent = models.ForeignKey(
        Tent, on_delete=models.CASCADE, null=True, blank=True)
    camera = models.ForeignKey(
        Camera, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='kitchen_images/%Y/%m/%d/')
    location = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Image from {self.location}"

    def save(self, *args, **kwargs):
        # Resize and compress the image
        if self.image:
            img = Image.open(self.image)
            img = img.convert("RGB")  # Ensure RGB mode for consistency

            # Resize the image to 640x640 pixels
            img = img.resize((640, 640), Image.Resampling.LANCZOS)

            # Compress the image
            output = BytesIO()
            # Adjust quality as needed
            img.save(output, format='JPEG', quality=70)
            output.seek(0)

            # Replace the original image with the resized and compressed image
            self.image = ContentFile(output.read(), name=self.image.name)

        super().save(*args, **kwargs)


class GarbageMonitoringReport(BaseModel):
    ANNOTATOR_CHOICES = [
        ('clean', 'clean'),
        ('garbage', 'garbage'),
    ]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="garbage_monitoring_histories")
    is_clean = models.BooleanField(default=False)
    annotator_status = models.CharField(
        max_length=10, choices=ANNOTATOR_CHOICES, default='', blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    current_status = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='garbage_monitoring_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='garbage_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="garbage_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="garbage_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return ["garbage"] if not self.is_clean else ["clean"]

    def save(self, *args, **kwargs):
        self.current_status = [
            self.annotator_status] if self.is_annotated else self.ai_status

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]
            if status_value == "garbage":
                self.is_clean = False
            elif status_value == "clean":
                self.is_clean = True
            else:
                self.is_clean = False  # fallback
        else:
            self.is_clean = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Garbage Monitoring History for Camera {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"


class RecycleMonitoringReport(BaseModel):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="recycle_monitoring_histories")
    is_clean = models.BooleanField(default=False)
    violation_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(null=True, blank=True, default=None)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='recycle_monitoring_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='recycle_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="recycle_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="recycle_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return self.violation_list

    def save(self, *args, **kwargs):
        self.current_status = self.annotator_status if self.is_annotated else self.violation_list
        if isinstance(self.current_status, (list, dict)):
            self.is_clean = len(self.current_status) == 0
        else:
            self.is_clean = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Recycle Monitoring History for Camera {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"


class FallDetectionMonitoringReport(BaseModel):
    ANNOTATOR_CHOICES = [
        ('not_detected', 'not detected'),
        ('fall_detected', 'fall detected'),
    ]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="fall_detection_monitoring_histories")
    is_fall_detected = models.BooleanField(default=False)
    annotator_status = models.CharField(
        max_length=15, choices=ANNOTATOR_CHOICES, default='', blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    current_status = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='fall_detection_monitoring_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='fall_detection_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="fall_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="fall_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return ["fall_detected"] if self.is_fall_detected else ["not_detected"]

    def save(self, *args, **kwargs):
        self.current_status = [
            self.annotator_status] if self.is_annotated else self.ai_status

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]
            if status_value == "fall_detected":
                self.is_fall_detected = True
            elif status_value == "not_detected":
                self.is_fall_detected = False
            else:
                self.is_fall_detected = False  # fallback
        else:
            self.is_fall_detected = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Fall Detection Monitoring History for Camera {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"

class ViolenceMonitoringReport(BaseModel):
    ANNOTATOR_CHOICES = [
        ('non_violence', 'non-violence'),
        ('violence', 'violence'),
    ]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="violence_monitoring_histories")
    is_violence = models.BooleanField(default=False)
    annotator_status = models.CharField(
        max_length=15, choices=ANNOTATOR_CHOICES, default='', blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    current_status = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='violence_monitoring_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='violence_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="violence_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="violence_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return ["violence"] if self.is_violence else ["non_violence"]

    def save(self, *args, **kwargs):
        self.current_status = [
            self.annotator_status] if self.is_annotated else self.ai_status

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]
            if status_value == "violence":
                self.is_violence = True
            elif status_value == "non_violence":
                self.is_violence = False
            else:
                self.is_violence = False  # fallback
        else:
            self.is_violence = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Violence Monitoring History for Camera {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"


class CrowdMonitoringReport(BaseModel):
    ANNOTATOR_CHOICES = [
        # ('warn', 'warn'),
        # ('high', 'high'),
        ('red', 'red'),
        ('orange', 'orange'),
        ('green', 'green'),
    ]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="crowd_monitoring_histories")
    is_crowd = models.BooleanField(default=False)
    annotator_status = models.CharField(
        max_length=15, choices=ANNOTATOR_CHOICES, default='', blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    current_status = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='crowd_monitoring_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='crowd_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="crowd_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="crowd_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return ["high"] if self.is_crowd else ["warn"]

    def save(self, *args, **kwargs):
        self.current_status = [
            self.annotator_status] if self.is_annotated else self.ai_status

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]
            # if status_value == "high":
            #     self.is_crowd = True
            # elif status_value == "warn":
            #     self.is_crowd = False
            if status_value == "red":
                self.is_crowd = True
            elif status_value == "orange":
                self.is_crowd = True
            elif status_value == "green":
                self.is_crowd = False
            else:
                self.is_crowd = False  # fallback
        else:
            self.is_crowd = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Crowd Monitoring History for Camera {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"
    

class WallClimbMonitoringReport(BaseModel):
    ANNOTATOR_CHOICES = [
        ('no_climb', 'no_climb'),
        ('climb', 'climb'),
    ]

    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="wall_climb_monitoring_histories"
    )

    is_climb = models.BooleanField(default=False)

    annotator_status = models.CharField(
        max_length=15,
        choices=ANNOTATOR_CHOICES,
        default='',
        blank=True
    )

    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)

    ai_annotation_time = models.DateTimeField(
        null=True,
        blank=True,
        default=None
    )

    current_status = models.JSONField(null=True, blank=True)

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    is_rejected = models.BooleanField(default=False)

    image = models.ImageField(
        upload_to='wall_climb_monitoring_history/%Y/%m/%d/',
        null=True,
        blank=True
    )

    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='wall_climb_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="wall_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="wall_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return ["climb"] if self.is_climb else ["no_climb"]

    def save(self, *args, **kwargs):
        self.current_status = (
            [self.annotator_status] if self.is_annotated else self.ai_status
        )

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]

            if status_value == "climb":
                self.is_climb = True
            elif status_value == "no_climb":
                self.is_climb = False
            else:
                self.is_climb = False
        else:
            self.is_climb = False

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Wall Climb Monitoring History for Camera "
            f"{self.camera.tent.company.name} "
            f"from {self.start_time} to {self.end_time}"
        )


class AbnormalActivities(BaseModel):
    ANNOTATOR_CHOICES = [
        ('no_motion', 'no_motion'),
        ('motion_detected', 'motion_detected'),
    ]

    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="abnormal_activity_histories"
    )

    is_motion_detected = models.BooleanField(default=False)

    annotator_status = models.CharField(
        max_length=20,
        choices=ANNOTATOR_CHOICES,
        default='',
        blank=True
    )

    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)

    ai_annotation_time = models.DateTimeField(
        null=True,
        blank=True,
        default=None
    )

    current_status = models.JSONField(null=True, blank=True)

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    is_rejected = models.BooleanField(default=False)

    image = models.ImageField(
        upload_to='abnormal_activity_monitoring_history/%Y/%m/%d/',
        null=True,
        blank=True
    )

    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='abnormal_activity_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="abnormal_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="abnormal_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return ["motion_detected"] if self.is_motion_detected else ["no_motion"]

    def save(self, *args, **kwargs):
        self.current_status = (
            [self.annotator_status] if self.is_annotated else self.ai_status
        )

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]

            if status_value == "motion_detected":
                self.is_motion_detected = True
            elif status_value == "no_motion":
                self.is_motion_detected = False
            else:
                self.is_motion_detected = False
        else:
            self.is_motion_detected = False

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Abnormal Activity History for Camera "
            f"{self.camera.tent.company.name} "
            f"from {self.start_time} to {self.end_time}"
        )


class BuffetViolationReport(BaseModel):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=False,
                               blank=False, related_name="buffet_violation_histories")
    violation = models.BooleanField(default=False)
    violation_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    current_status = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='buffet_violation_history/%Y/%m/%d/', null=True, blank=True)
    from_human = models.BooleanField(default=False)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='buffet_violation_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="buffet_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="buffet_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return self.violation_list

    def save(self, *args, **kwargs):
        self.current_status = self.annotator_status if self.is_annotated else self.violation_list
        if isinstance(self.current_status, (list, dict)):
            self.violation = len(self.current_status) > 0
        else:
            self.violation = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Buffet Violation Report for Camera {self.camera.tent} from {self.start_time} to {self.end_time}"


class BathroomMonitoringHistory(BaseModel):
    ANNOTATOR_CHOICES = [
        ('absent', 'absent'),
    ] + [(str(i), str(i)) for i in range(1, 9)]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE,
                               null=False, blank=False, related_name="bathroom_monitoring_histories")
    cleaner_count = models.IntegerField(default=0)
    present = models.BooleanField(default=False)
    annotator_status = models.CharField(
        max_length=10, choices=ANNOTATOR_CHOICES, default='absent', blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='bathroom_monitoring_history/%Y/%m/%d/', null=True, blank=True)

    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='bath_monitor_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="bath_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="bath_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return [str(self.cleaner_count)] if self.cleaner_count > 0 else ["absent"]

    def save(self, *args, **kwargs):
        self.current_status = [
            self.annotator_status] if self.is_annotated else self.ai_status

        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            status_value = self.current_status[0]
            if status_value == "absent":
                self.present = False
            else:
                try:
                    self.present = int(status_value) > 0
                except ValueError:
                    self.present = False
        else:
            self.present = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Guard Presence History for Camera SN: {self.camera.tent.company.name} from {self.start_time} to {self.end_time}"


class SentimentAnalysis(BaseModel):
    camera = models.ForeignKey(
        Camera, on_delete=models.SET_NULL, related_name='sentiment_analysis', null=True, blank=True)
    sentiment_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(
        null=True, blank=True, default=None)
    average_sentiment = models.FloatField(null=True, blank=True)
    version = models.IntegerField(null=True, blank=True)
    mac_address = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.CharField(max_length=255, null=True, blank=True)
    connection_type = models.CharField(max_length=255, null=True, blank=True)
    current_status = models.JSONField(null=True, blank=True)
    current_average = models.FloatField(null=True, blank=True)
    ip_address_method = models.CharField(max_length=255, null=True, blank=True)
    host_name = models.CharField(max_length=255, null=True, blank=True)
    time_zone = models.IntegerField(null=True, blank=True)
    hw_platform = models.CharField(max_length=255, null=True, blank=True)
    report_date = models.DateField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(
        upload_to='sentiment_analysis_history/%Y/%m/%d/', null=True, blank=True)
    annotator = models.ForeignKey(
        'authentication.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='sentiment_analysis_history'
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="sentiment_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=''),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="sentiment_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        if self.average_sentiment is None:
            return None

        status_map = {
            1.0: "very happy",
            0.75: "happy",
            0.5: "neutral",
            0.25: "sad",
            0.0: "very_sad"
        }

        return status_map.get(self.average_sentiment, "unknown")

    def save(self, *args, **kwargs):
        status_map = {
            1.0: "happy",
            0.75: "happy",
            0.5: "neutral",
            0.25: "sad",
            0.0: "very_sad"
        }

        reverse_map = {v: k for k, v in status_map.items()}

        # Annotator-based logic
        if self.is_annotated:
            if self.annotator_status:
                if isinstance(self.annotator_status, str):
                    self.current_average = reverse_map.get(
                        self.annotator_status, None)
                elif isinstance(self.annotator_status, list):
                    self.current_average = reverse_map.get(
                        self.annotator_status[0], None)
                else:
                    self.current_average = None
            else:
                self.current_average = None
        else:
            self.current_average = self.average_sentiment

        if self.is_annotated:
            if isinstance(self.annotator_status, str):
                self.current_status = [self.annotator_status]
            elif isinstance(self.annotator_status, list):
                self.current_status = self.annotator_status
            else:
                self.current_status = []
        else:
            self.current_status = [self.ai_status] if self.ai_status else []
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sentiment Analysis for Camera SN: {self.camera.tent}"


class CleanersPresenceHistory(models.Model):
    PERSON_CLASS_CHOICES = [
        ('cleaner-female', 'Cleaner Female'),
        ('cleaner-male', 'Cleaner Male'),
        ('supervisor-female', 'Supervisor Female'),
        ('supervisor-male', 'Supervisor Male'),
    ]

    camera = models.ForeignKey(
        Camera, on_delete=models.CASCADE, related_name='cleaners_presence_histories'
    )
    person_class = models.CharField(max_length=20, choices=PERSON_CLASS_CHOICES)
    annotator_status = models.CharField(
        max_length=20, choices=PERSON_CLASS_CHOICES, null=True, blank=True
    )
    cleaner_count = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(
        upload_to='cleaners_presence/%Y/%m/%d/', null=True, blank=True
    )
    is_annotated = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    annotator = models.ForeignKey(
        'authentication.MyUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cleaners_presence_annotations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["camera", "-start_time"], name="cleaners_cam_start_idx"),
        ]

    @property
    def current_status(self):
        value = self.annotator_status if self.is_annotated else self.person_class
        return [value] if value else []

    def __str__(self):
        return f"{self.person_class} - {self.camera.sn} ({self.start_time})"


class EmptyChairDetectionReport(BaseModel):
    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="empty_chair_detection_histories",
    )
    empty_chair_count = models.IntegerField(default=0)
    total_chair_count = models.IntegerField(default=0)
    is_empty_detected = models.BooleanField(default=False)
    annotator_status = models.CharField(max_length=20, null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(null=True, blank=True, default=None)
    current_status = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to="empty_chair_detection_history/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    annotator = models.ForeignKey(
        "authentication.MyUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="empty_chair_detection_history",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="chair_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=""),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="chair_acc_idx",
            ),
            models.Index(
                fields=["camera", "-start_time"],
                name="chair_cam_start_idx",
            ),
        ]

    @property
    def ai_status(self):
        return [str(self.empty_chair_count)]

    def save(self, *args, **kwargs):
        self.current_status = (
            [self.annotator_status] if self.is_annotated else self.ai_status
        )
        if isinstance(self.current_status, list) and len(self.current_status) > 0:
            try:
                self.is_empty_detected = int(self.current_status[0]) > 0
            except (ValueError, TypeError):
                self.is_empty_detected = False
        else:
            self.is_empty_detected = False
        super().save(*args, **kwargs)

    def __str__(self):
        company = self.camera.tent.company.name if self.camera.tent and self.camera.tent.company else "No Company"
        return f"Empty Chair Detection for Camera {company} from {self.start_time} to {self.end_time}"


class SecurityMonitoringReport(BaseModel):
    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="security_monitoring_histories",
    )
    is_safe = models.BooleanField(default=True)
    violation_list = models.JSONField(null=True, blank=True)
    annotator_status = models.JSONField(null=True, blank=True)
    current_status = models.JSONField(null=True, blank=True)
    is_annotated = models.BooleanField(default=False)
    is_ai_annotated = models.BooleanField(default=False)
    ai_annotation_time = models.DateTimeField(null=True, blank=True, default=None)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to="security_monitoring_history/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    annotator = models.ForeignKey(
        "authentication.MyUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="security_monitor_history",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["camera", "is_annotated", "-created_at"],
                name="security_gal_idx",
                condition=models.Q(is_rejected=False, image__isnull=False) & ~models.Q(image=""),
            ),
            models.Index(
                fields=["is_annotated", "is_rejected", "created_at"],
                name="security_acc_idx",
            ),
        ]

    @property
    def ai_status(self):
        return self.violation_list

    def save(self, *args, **kwargs):
        self.current_status = self.annotator_status if self.is_annotated else self.violation_list
        if isinstance(self.current_status, (list, dict)):
            self.is_safe = len(self.current_status) == 0
        else:
            self.is_safe = True
        super().save(*args, **kwargs)

    def __str__(self):
        company = self.camera.tent.company.name if self.camera.tent and self.camera.tent.company else "No Company"
        return f"Security Monitoring for Camera {company} from {self.start_time} to {self.end_time}"
