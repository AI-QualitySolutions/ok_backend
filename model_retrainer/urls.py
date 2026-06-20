from django.urls import path
from .views import UniversalAccuracyAPIView

urlpatterns = [
    path('accuracy/', UniversalAccuracyAPIView.as_view(), name='universal_accuracy'),
]