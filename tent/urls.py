from django.urls import path, include
from rest_framework.routers import DefaultRouter

from tent.views import (
    DashboardClimbMonitoring, DashboardCrowdMonitoring, TentAPIView, AllTentCamerasView, TentEnvironmentSensorView,
    TentWaterTankHistoryView, ReportView, TentWaterTankAPIView,
    TentTotalCapacityView, AllTentEnvironmentSensorView,
    TentTankGaurdCleanHistoryView, CreateWaterLevelSensor,
    TentTankGaurdCleanHistoryReportView, TentsWaterTankSampleCSVView,
    TentsWaterTankUploadView, TentSampleCSVView, TentUploadView, CountryDetail,
    FilterTentView, DashboardKitchen, DashboardFood, DashboardGuard, DashboardCounter,
    DashboardSensor, TentCreateFromServerView, DashboardBuffet, DashboardCleaner, DashboardGarbage, DashboardRecycle, DashboardFallDetection, DashboardViolenceMonitoring, DashboardAbnormalActivity, DashboardSentiment
)

# Router setup
router = DefaultRouter()

# URL patterns
urlpatterns = [
    # Country
    path('countries/', CountryDetail.as_view(), name='country-list'),
    path('countries/<int:pk>/', CountryDetail.as_view(), name='country-detail'),

    # Tent Capacity
    path('tent_capacity_staying/', TentTotalCapacityView.as_view()),
    path('tent_capacity_staying/<int:tent_id>/', TentTotalCapacityView.as_view()),

    # Tent Tank Guard & Clean History
    path('tent-tank-gaurd-clean-history/', TentTankGaurdCleanHistoryView.as_view()),
    path('tent-tank-gaurd-clean-history/<int:tent_id>/', TentTankGaurdCleanHistoryView.as_view()),
    path('tent-tank-gaurd-clean-history-report/', TentTankGaurdCleanHistoryReportView.as_view()),

    # Tent CSV Upload/Download
    path('tent-csv-sample-download/', TentSampleCSVView.as_view()),
    path('tent-csv-upload/', TentUploadView.as_view()),

    # Water Tank
    path('water_tank/', TentWaterTankAPIView.as_view()),
    path('water_tank/<int:pk>/', TentWaterTankAPIView.as_view()),
    path('water-tank-csv-sample-download/', TentsWaterTankSampleCSVView.as_view()),
    path('water-tank-csv-upload/', TentsWaterTankUploadView.as_view()),

    # Tent related
    path('<int:tent_id>/cameras/', AllTentCamerasView.as_view()),
    path('<int:tent_id>/sensors_with_avg/', TentEnvironmentSensorView.as_view()),
    path('all/sensors_data_avg/', AllTentEnvironmentSensorView.as_view()),

    # Water Tank Graphs and Reports
    path('water_tank_graph/<int:tent_id>/', TentWaterTankHistoryView.as_view()),
    path('water_graph_report/', ReportView.as_view()),

    # Water Level Sensor
    path('water-level-sensor/', CreateWaterLevelSensor.as_view()),

    # Tent
    path('', TentAPIView.as_view()),
    path('<int:pk>/', TentAPIView.as_view()),

    # Filter tents
    path('filter/', FilterTentView.as_view()),

    # Dashboard
    path('dashboard/kitchen/', DashboardKitchen.as_view()),
    path('dashboard/food/', DashboardFood.as_view()),
    path('dashboard/guard/', DashboardGuard.as_view()),
    path('dashboard/counter/', DashboardCounter.as_view()),
    path('dashboard/sensor/', DashboardSensor.as_view()),
    path('dashboard/buffet/', DashboardBuffet.as_view()),
    path('dashboard/cleaner/', DashboardCleaner.as_view()),
    path('dashboard/garbage/', DashboardGarbage.as_view()),
    path('dashboard/recycle/', DashboardRecycle.as_view()),
    path('dashboard/fall-detection/', DashboardFallDetection.as_view()),
    path('dashboard/violence/', DashboardViolenceMonitoring.as_view()),
    path('dashboard/crowd/', DashboardCrowdMonitoring.as_view()),
    path('dashboard/climb/', DashboardClimbMonitoring.as_view()),
    path('dashboard/abnormal-activity/', DashboardAbnormalActivity.as_view()),
    path('dashboard/sentiment/', DashboardSentiment.as_view()),


    # Tent from server
    path('tent-from-server/', TentCreateFromServerView.as_view()),
]

