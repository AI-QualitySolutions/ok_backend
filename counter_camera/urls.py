from django.urls import path
from counter_camera.views import CameraHeartbeatView, CounterHistoryView, TentCameraInfoView

urlpatterns = [
    path("heartBeat", CameraHeartbeatView.as_view()),
    path("dataUpload", CounterHistoryView.as_view()),
    path("tentCameraInfo/", TentCameraInfoView.as_view()),
]