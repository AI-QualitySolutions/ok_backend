from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sensor.views import (EnvironmentSensorListCreateAPIView, EnvironmentSensorDetailAPIView,
                          SensorUploadCSVview, SensorDataByHour,
                          SensorReportView, SensorData, CreateSensor, SensorSampleCSVView, EnvironmentSensorsWithoutRecordsView,
                          ReassignSensorWithRecordsView, AssignNewSensorView, SensorLocationAPIView, IngestEnvironmentSensorData)

urlpatterns = [
    path('', EnvironmentSensorListCreateAPIView.as_view()),
    path('<int:pk>/', EnvironmentSensorDetailAPIView.as_view()),
    path('tents-sensor-csv/', SensorDataByHour.as_view()),
    path('tents-sensor-csv/<int:tent_id>/', SensorDataByHour.as_view()),
    path('sensor-csv-upload/', SensorUploadCSVview.as_view()),
    path('sensor-graph-report/<int:tent_id>/', SensorReportView.as_view()),
    path('tents-sensor-intervel/', SensorData.as_view()),  # csv and data
    # path('tents-sensor-intervel/<int:tent_id>/', SensorData.as_view()),
    path('create-sensor/', CreateSensor.as_view()),
    path('sensor-csv-sample-download/', SensorSampleCSVView.as_view()),
    path('sensors-without-assigned/', EnvironmentSensorsWithoutRecordsView.as_view()),
    path('assign-sensor/', ReassignSensorWithRecordsView.as_view()),
    path('assign-new-sensor/<int:id>/', AssignNewSensorView.as_view()),
    
    path('sensor-location/', SensorLocationAPIView.as_view()),
    path('sensor-location/<int:id>/', SensorLocationAPIView.as_view()),
    path('ingest-environment/', IngestEnvironmentSensorData.as_view()),
]

# api/camera/tent-sensor-csv?start_date=${formattedStartDate}&end_date=${formattedendDate}`;
