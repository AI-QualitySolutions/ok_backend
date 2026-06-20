from django.urls import path

from .views import (ActivityLogListView, ActivitySummaryView, AnnotatorRankingView,
                    AnnotatorReportView, CameraDeliveryStatusView,
                    CameraDetailView, CameraListView, CameraSummaryView,
                    CompanyTentListView,
                    KitchenViolationListView, OrangePiDeviceListView,
                    OrangePiHeartbeatView, OrangePiSummaryView)


urlpatterns = [
    path('companies/', CompanyTentListView.as_view(), name='td-company-tent-list'),
    path('orange-heartbeat/', OrangePiHeartbeatView.as_view(), name='td-orangepi-heartbeat'),
    path('oranges/', OrangePiDeviceListView.as_view(), name='td-orangepi-list'),
    path('oranges/summary/', OrangePiSummaryView.as_view(), name='td-orangepi-summary'),
    path('camera/', CameraListView.as_view(), name='td-camera-list'),
    path('camera/summary/', CameraSummaryView.as_view(), name='td-camera-summary'),
    path('camera/<int:pk>/', CameraDetailView.as_view(), name='td-camera-detail'),
    path(
        'camera-delivery-status/',
        CameraDeliveryStatusView.as_view(),
        name='td-camera-delivery-status'
    ),
    path('kitchen-model/', KitchenViolationListView.as_view(), name='td-kitchen-violation-list'),
    path('annotator-report/', AnnotatorReportView.as_view(), name='td-annotator-report'),

    # Activity logs
    path('activity-logs/', ActivityLogListView.as_view(), name='td-activity-log-list'),
    path(
        'activity-logs/cameras/',
        ActivityLogListView.as_view(),
        {'device_type': 'camera'},
        name='td-activity-log-cameras',
    ),
    path(
        'activity-logs/oranges/',
        ActivityLogListView.as_view(),
        {'device_type': 'orange_pi'},
        name='td-activity-log-oranges',
    ),
    path(
        'activity-logs/access-points/',
        ActivityLogListView.as_view(),
        {'device_type': 'access_point'},
        name='td-activity-log-access-points',
    ),
    path('activity-summary/', ActivitySummaryView.as_view(), name='td-activity-summary'),
    path("annotation-by-user/", AnnotatorRankingView.as_view()),
]