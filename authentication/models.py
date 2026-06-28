from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser
from authentication.managers import MyUserManager, CompanyManager
import pytz
# from tent.models import Tent

RIYADH_TZ = pytz.timezone("Asia/Riyadh")


class BaseModel(models.Model):
    created_at = models.DateTimeField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    objects = CompanyManager()

    def save(self, *args, **kwargs):
        now = timezone.now().astimezone(RIYADH_TZ)

        if not self.created_at:
            self.created_at = now
        self.updated_at = now

        super().save(*args, **kwargs)


class PermissionModel(models.Model):
    is_temperature = models.BooleanField(default=False)  # temperature
    is_guard = models.BooleanField(default=False)  # guard
    is_peoplecount = models.BooleanField(default=False)  # headcount
    is_kitchen = models.BooleanField(default=False)  # kitchen
    is_aggf = models.BooleanField(default=False)  # AbdulGhaniGold Factory.
    is_smoking = models.BooleanField(default=False)  # Smoking.
    is_face_detection = models.BooleanField(default=False)  # Face Detection.
    is_falldetection = models.BooleanField(default=False)  # Fall Detection.
    is_violencedetection = models.BooleanField(default=False)  # Violence Detection.
    is_crowdmonitoring = models.BooleanField(default=False)  # Crowd Monitoring.
    is_climbmonitoring = models.BooleanField(default=False)  # Wall Climb Monitoring.
    is_abnormalactivity = models.BooleanField(default=False)  # Abnormal Activity Detection.
    is_livestream = models.BooleanField(default=False)  # Livestream Access
    is_foodweight = models.BooleanField(default=False)  # weight
    is_cleanness = models.BooleanField(default=False)  # cleaness
    is_recycle = models.BooleanField(default=False)  # recycle monitoring
    is_buffet = models.BooleanField(default=False)  # buffet
    is_cleaners = models.BooleanField(default=False)  # clearners
    is_sentiment = models.BooleanField(default=False)  # sentiment
    is_water_tank = models.BooleanField(
        default=False)  # water_sensor, water_tank
    is_sensor_assign = models.BooleanField(default=False)
    is_annotator_ranking = models.BooleanField(default=False)
    is_settings = models.BooleanField(default=False)
    is_can_delete_image = models.BooleanField(default=False)
    is_accesspoint = models.BooleanField(default=False)
    is_cleaners_presence = models.BooleanField(default=False)  # cleaners presence with person class
    is_chairdetection = models.BooleanField(default=False)  # empty chair detection
    is_security = models.BooleanField(default=False)  # security monitoring

    class Meta:
        abstract = True


class Company(BaseModel, PermissionModel):
    name = models.CharField(max_length=255, unique=True)
    name_ar = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    icon = models.ImageField(upload_to='company_fav_icon/', null=True, blank=True)
    def __str__(self):
        return self.name


class MyUser(AbstractBaseUser, PermissionModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name="users")
    email = models.EmailField(verbose_name="email", max_length=60, unique=True)
    username = models.CharField(max_length=30, null=False, blank=False)
    date_joined = models.DateTimeField(
        verbose_name="date joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="last login", auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_annotator = models.BooleanField(default=False)
    company_annotator = models.ManyToManyField(Company, blank=True)
    camera_type_annotator = models.ManyToManyField(
        'camera.CameraType', blank=True)

    sensor_update_permission = models.BooleanField(default=False)
    assigned_tent = models.ManyToManyField('tent.Tent', blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = MyUserManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return True
