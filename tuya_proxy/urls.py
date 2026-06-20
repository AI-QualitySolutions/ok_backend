from django.urls import path

from . import views

urlpatterns = [
    path("devices/", views.get_user_devices, name="tuya_devices"),
]
