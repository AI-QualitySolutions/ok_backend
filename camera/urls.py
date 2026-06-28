from django.urls import path, include
from rest_framework.routers import DefaultRouter

from camera.views import (
    # Camera API
    CameraAPIView, CameraDetailAPIView,
    CameraSampleCSVView, CameraUploadView,
    CameraByTentView, CounterHistoryReportChartView, CrowdMonitoringReportUpdateView, FallDetectionReportUpdateView, GalleryByCameraView, GarbageMonitoringReportChartView, GarbageMonitoringReportView, ViolenceReportUpdateView, WallClimbHistoryReportChartView, WallClimbHistoryReportView, CrowdMonitoringHistoryReportView, CrowdMonitoringReportChartView, AbnormalActivitiesReportChartView, AbnormalActivitiesHistoryReportView,
    get_camera_statistics_for_tent,

    # Tent Calculations
    tent_camera_calculation, tent_graph_calculation, tent_real_data_calculation,

    # Kitchen & Reports
    KitchenImageView, CreateKitchenViolationReportView, KitchenViolationReportByTentView,

    #AGGF & Reports
    CreateAGGFViolationReportView,

    #Smoking & Reports
    CreateSmokingViolationReportView,
    
    #Face Detection & Reports
    CreateFaceDetectionViolationReportView, FaceDetectionGalleryView,

    # History Views & Reports
    GuardPresenceHistoryViewSet,
    CreateCounterHistory, CreateGuardPresenceHistory,CreateBuffetViolationReportView,
    CreateBuffetViolationFromHumanReportView,
    CreateCameraHeartbeatView, CreateSentimentAnalysisView,
    CleanIndicatorHistoryReportView, GuardPresenceHistoryReportView, CounterHistoryReportView,
    CreateGarbageMonitoringHistory, CreateRecycleMonitoringHistory, CreateCleanersPresenceHistory, KitchenHistoryReport, BuffetHistoryViewReport, 
    SentimentAnalysisReportView, GuardPresenceHistoryReportNoShowPeriodView,
    
    # Fall Detection
    CreateFallDetectionMonitoringHistory,
     # Violence Detection
    CreateViolenceMonitoringHistory,
    
    #Crowd Detection
    CreateCrowdMonitoringHistory,
    CrowdCurrentStatusView,
    
    #Wall Climb Detection
    CreateWallClimbMonitoringHistory,
    ClimbMonitoringReportUpdateView,
    
     #Abnormal Activity Detection
     CreateAbnormalActivitiesHistory,
     AbnormalActivitiesUpdateView,

    # New DRF Views with Pagination
    GarbageMonitoringReportListAPIView, GarbageMonitoringReportDetailAPIView,

    #     Anotation update
    GuardPresentHistoryUpdateView,
    KitchenViolationReportUpdateView,
    EmployeeActivityViolationReportUpdateView,
    SmokingViolationReportUpdateView,
    GarbageMonitoringReportUpdateView, RecycleMonitoringReportUpdateView,
    BuffetViolationReportUpdateView,
    BathroomMonitoringHistoryUpdateView,
    SentimentAnalysisUpdateView,

    # Charts & Summaries
    GuardChartView, TentViolationSummaryView, CameraViolationSummaryView, CameraTypesView,
    TentGarbageSummaryView, CameraGarbageSummaryView, TentRecycleSummaryView, CameraRecycleSummaryView,
    TentBuffetSummaryView, CameraBuffetSummaryView,
    BuffetCameraLinkList, CameraStatusByTypeView, PeopleCountingCardView, PeopleGraphView, GuardCardViewData,
    GuardGraphViewData, KitchenViolatioReportDetailsView, BuffetViolatioReportDetailsView, CleanerCardViewData, CleanerChartView,
    CreateNewCleanersPresenceHistory, NewCleanerCardViewData, NewCleanerChartView, CleanersPresenceReportView,
    CleanersPresenceHistoryUpdateView,
    GarbageViolatioReportDetailsView, RecycleViolatioReportDetailsView,
    RecycleMonitoringReportView, RecycleMonitoringReportChartView, RecycleIndicatorHistoryReportView,
    CameraWithCameraHeartbeat, GalleryByCameraViewForData,

    #Ai annotation
    BuffetAiAnnotationAPIView, AnnotatorRankingView,

    # Reject image
    RejectImageView,

    # Empty Chair Detection
    CreateEmptyChairDetectionView,
    EmptyChairDetectionUpdateView,
    EmptyChairDetectionHistoryReportView,
    EmptyChairDetectionReportChartView,
    EmptyChairLiveCountView,

    # Security Monitoring
    CreateSecurityMonitoringHistory,
    SecurityMonitoringReportUpdateView,
    SecurityMonitoringHistoryReportView,
    SecurityIndicatorHistoryReportView,
    SecurityMonitoringReportChartView,
    SecurityMonitoringReportView,
    TentSecuritySummaryView,
    CameraSecuritySummaryView,
    SecurityViolatioReportDetailsView,
)

# Router setup for ViewSets
router = DefaultRouter()
router.register(r'guard-presence-history', GuardPresenceHistoryViewSet)

# URL patterns
urlpatterns = [
    # === Camera API ===
    path('camera-statuses/', CameraStatusByTypeView.as_view(),
         name='camera-statuses-by-type'),
    path('', CameraAPIView.as_view(), name='camera-list-create'),
    path('<int:pk>/', CameraDetailAPIView.as_view(), name='camera-detail'),
    path('camera-types/', CameraTypesView.as_view(), name="camera-type"),

    # === Tent Data Calculations ===
    path('tent-camera-data/<int:pk>/', tent_camera_calculation),
    path('tent-graph-data/<int:pk>/', tent_graph_calculation),
    path('tent-realtime-data/<int:pk>/', tent_real_data_calculation),

    # === Kitchen Operations ===
    path('kitchen-image/', KitchenImageView.as_view()),
    path('kitchen-violation-report-by-tent/<int:tent_id>/',
         KitchenViolationReportByTentView.as_view()),

    # === History Creation ===
    path('create-kitchen-violation-report/', CreateKitchenViolationReportView.as_view()),
    path('create-aggf-violation-report/', CreateAGGFViolationReportView.as_view()),
    path('create-smoking-violation-report/', CreateSmokingViolationReportView.as_view()),
    path('create-face-detection-report/', CreateFaceDetectionViolationReportView.as_view()),
    path('create-counter-history/', CreateCounterHistory.as_view()),
    path('counter-history-report-chart/', CounterHistoryReportChartView.as_view()),
    path('create-guard-detect/', CreateGuardPresenceHistory.as_view()),
    path('create-guard-detect/<int:pk>/', CreateGuardPresenceHistory.as_view()),

    path('create-camera-heartbeat/', CreateCameraHeartbeatView.as_view()),
    path('create-garbage-monitoring/', CreateGarbageMonitoringHistory.as_view()),
    path('create-garbage-monitoring/<int:pk>/', CreateGarbageMonitoringHistory.as_view()),
    path('create-recycle-monitoring/', CreateRecycleMonitoringHistory.as_view()),
    path('create-recycle-monitoring/<int:pk>/', CreateRecycleMonitoringHistory.as_view()),
    path('create-fall-detection-monitoring/', CreateFallDetectionMonitoringHistory.as_view()),
    path('create-fall-detection-monitoring/<int:pk>/', CreateFallDetectionMonitoringHistory.as_view()),
    path('create-violence-monitoring/', CreateViolenceMonitoringHistory.as_view()),
    path('create-violence-monitoring/<int:pk>/', CreateViolenceMonitoringHistory.as_view()),
    path('create-crowd-monitoring/', CreateCrowdMonitoringHistory.as_view()),
    path('create-crowd-monitoring/<int:pk>/', CreateCrowdMonitoringHistory.as_view()),
    path('crowd-current-status/', CrowdCurrentStatusView.as_view()),
    path('create-wallclimb-monitoring/', CreateWallClimbMonitoringHistory.as_view()),
    path('create-wallclimb-monitoring/<int:pk>/', CreateWallClimbMonitoringHistory.as_view()),
    path('create-abnormal-activity-monitoring/', CreateAbnormalActivitiesHistory.as_view()),
    path('create-abnormal-activity-monitoring/<int:pk>/', CreateAbnormalActivitiesHistory.as_view()),

    # === DRF Views with Pagination ===
#    path('garbage-monitoring-reports/', GarbageMonitoringReportListAPIView.as_view(), name='garbage-monitoring-reports-list'),
#    path('garbage-monitoring-reports/<int:pk>/', GarbageMonitoringReportDetailAPIView.as_view(),name='garbage-monitoring-reports-detail'),


    path('create-buffet-violation/', CreateBuffetViolationReportView.as_view()),
    path('create-cleaners-presence/', CreateCleanersPresenceHistory.as_view()),
    path('create-sentiment-analysis/', CreateSentimentAnalysisView.as_view()),
    path('create-sentiment-analysis/<int:pk>/', CreateSentimentAnalysisView.as_view()),


    path('buffet-ai-annotation/', BuffetAiAnnotationAPIView.as_view()),
    path('buffet-ai-annotation/<int:id>/', BuffetAiAnnotationAPIView.as_view()),


    # Anotations Update
    path("update-guard-violation/<int:pk>/", GuardPresentHistoryUpdateView.as_view()),
    path('update-kitchen-violation/<int:pk>/', KitchenViolationReportUpdateView.as_view()),
    path('update-employeeactivity-violation/<int:pk>/', EmployeeActivityViolationReportUpdateView.as_view()),
    path('update-smoking-violation/<int:pk>/', SmokingViolationReportUpdateView.as_view()),
    path('update-garbage-violation/<int:pk>/', GarbageMonitoringReportUpdateView.as_view()),
    path('update-recycle-violation/<int:pk>/', RecycleMonitoringReportUpdateView.as_view()),
    path('update-buffet-violation/<int:pk>/', BuffetViolationReportUpdateView.as_view()),
    path('update-bathroom-violation/<int:pk>/', BathroomMonitoringHistoryUpdateView.as_view()),
    path('update-sentiment-violation/<int:pk>/', SentimentAnalysisUpdateView.as_view()),
    path('update-falldetection-violation/<int:pk>/', FallDetectionReportUpdateView.as_view()),
    path('update-violencedetection-violation/<int:pk>/', ViolenceReportUpdateView.as_view()),
    path('update-crowdmonitoring-violation/<int:pk>/', CrowdMonitoringReportUpdateView.as_view()),
    path('update-climbmonitoring-violation/<int:pk>/', ClimbMonitoringReportUpdateView.as_view()),
    path('update-abnormalactivity-violation/<int:pk>/', AbnormalActivitiesUpdateView.as_view()),

    # HeadCount
    path('people-counter/', PeopleCountingCardView.as_view()),
    path('people-counter-graph/', PeopleGraphView.as_view()),

    # GuardCount
    path('guard-card/', GuardCardViewData.as_view()),
    path('guard-chart/', GuardChartView.as_view()),

    # CleanerCount
    path('cleaner-card/', CleanerCardViewData.as_view()),
    path('cleaner-chart/', CleanerChartView.as_view()),

    # New Cleaners Presence (with person_class)
    path('new-cleaners-presence/', CreateNewCleanersPresenceHistory.as_view()),
    path('new-cleaner-card/', NewCleanerCardViewData.as_view()),
    path('new-cleaner-chart/', NewCleanerChartView.as_view()),
    path('new-cleaners-presence-report/', CleanersPresenceReportView.as_view()),
    path('update-cleaners-presence/<int:pk>/', CleanersPresenceHistoryUpdateView.as_view()),
    path('update-cleaners-violation/<int:pk>/', CleanersPresenceHistoryUpdateView.as_view()),

    # Kitchen Violation
    path('kitchen-violation-report-details/',
         KitchenViolatioReportDetailsView.as_view()),

    # Buffet Violation
    path('buffet-violation-report-details/',
         BuffetViolatioReportDetailsView.as_view()),

    # Garbage Violation
    path('garbage-violation-report-details/',
         GarbageViolatioReportDetailsView.as_view()),
    path('recycle-violation-report-details/',
         RecycleViolatioReportDetailsView.as_view()),



    # === History Creation from Human ===
    path('create-buffet-violation-from-human/',
         CreateBuffetViolationFromHumanReportView.as_view()),

    # === Reports ===
    path('clean-indicator-report/', CleanIndicatorHistoryReportView.as_view()),
    path('recycle-indicator-report/', RecycleIndicatorHistoryReportView.as_view()),
    path('guard-presence-report/', GuardPresenceHistoryReportView.as_view()),
    path('guard-presence-report/no-show-period/', GuardPresenceHistoryReportNoShowPeriodView.as_view()),
    path('counter-history-report/', CounterHistoryReportView.as_view()),
    path('kitchen-history-report/', KitchenHistoryReport.as_view()),
    path('buffet-history-report/', BuffetHistoryViewReport.as_view()),
    path('sentiment-history-report/', SentimentAnalysisReportView.as_view()),
    path('garbage-monitoring-report/', GarbageMonitoringReportView.as_view()),
    path('garbage-monitoring-report-chart/', GarbageMonitoringReportChartView.as_view()),
    path('recycle-monitoring-report/', RecycleMonitoringReportView.as_view()),
    path('recycle-monitoring-report-chart/', RecycleMonitoringReportChartView.as_view()),
    path('climb-history-report/', WallClimbHistoryReportView.as_view()),
    path('climb-history-report-chart/', WallClimbHistoryReportChartView.as_view()),
    path('crowd-monitoring-report/', CrowdMonitoringHistoryReportView.as_view()),
    path('crowd-monitoring-report-chart/', CrowdMonitoringReportChartView.as_view()),
    path('abnormal-activity-report/',       AbnormalActivitiesHistoryReportView.as_view()),
    path('abnormal-activity-report-chart/', AbnormalActivitiesReportChartView.as_view()),

    # === Ranking ===
    path('tent-kitchen-report-sort/', TentViolationSummaryView.as_view()),
    path('camera-kitchen-report-sort/', CameraViolationSummaryView.as_view()),
    path('tent-garbage-report-sort/', TentGarbageSummaryView.as_view()),
    path('camera-garbage-report-sort/', CameraGarbageSummaryView.as_view()),
    path('tent-recycle-report-sort/', TentRecycleSummaryView.as_view()),
    path('camera-recycle-report-sort/', CameraRecycleSummaryView.as_view()),
    path('tent-buffet-report-sort/', TentBuffetSummaryView.as_view()),
    path('camera-buffet-report-sort/', CameraBuffetSummaryView.as_view()),

    # === Camera & Gallery Views ===
    path('camera-by-tent/', CameraByTentView.as_view()),
    path('camera-by-tent/<int:tent_id>/', CameraByTentView.as_view()),
    path('gallery-by-camera/', GalleryByCameraView.as_view()),
    path('gallery-by-camera/<int:camera_id>/', GalleryByCameraView.as_view()),

    # === Face Detection Gallery View ===
    path('face-detection-gallery/', FaceDetectionGalleryView.as_view()),
    path('face-detection-gallery/<int:camera_id>/', FaceDetectionGalleryView.as_view()),
    # === Statistics & Charts ===
    path('<int:tent_id>/camera_statistics/',
         get_camera_statistics_for_tent, name='camera_statistics'),
    path('<int:tent_id>/camera_statistics/<str:date>/',
         get_camera_statistics_for_tent, name='camera_statistics_by_date'),


    # === CSV Operations ===
    path('camera-csv-sample-download/', CameraSampleCSVView.as_view()),
    path('camera-csv-upload/', CameraUploadView.as_view()),

    # === Buffet Operations ===
    path('buffet-camera-link-list/', BuffetCameraLinkList.as_view()),
    path("camera-heartbeat/", CameraWithCameraHeartbeat.as_view()),

    # === ViewSet Routes ===
    path('', include(router.urls)),
    path("gallery-data/", GalleryByCameraViewForData.as_view()),

    # Reject image
    path('reject-image/', RejectImageView.as_view()),

    # === Empty Chair Detection ===
    path('create-empty-chair-detection/', CreateEmptyChairDetectionView.as_view()),
    path('create-empty-chair-detection/<int:pk>/', CreateEmptyChairDetectionView.as_view()),
    path('update-empty-chair-detection/<int:pk>/', EmptyChairDetectionUpdateView.as_view()),
    path('empty-chair-detection-report/', EmptyChairDetectionHistoryReportView.as_view()),
    path('empty-chair-detection-chart/', EmptyChairDetectionReportChartView.as_view()),
    path('empty-chair-live-count/', EmptyChairLiveCountView.as_view()),

    # === Security Monitoring ===
    path('create-security-monitoring/', CreateSecurityMonitoringHistory.as_view()),
    path('create-security-monitoring/<int:pk>/', CreateSecurityMonitoringHistory.as_view()),
    path('update-security-violation/<int:pk>/', SecurityMonitoringReportUpdateView.as_view()),
    path('security-monitoring-history/', SecurityMonitoringHistoryReportView.as_view()),
    path('security-indicator-report/', SecurityIndicatorHistoryReportView.as_view()),
    path('security-monitoring-report/', SecurityMonitoringReportView.as_view()),
    path('security-monitoring-report-chart/', SecurityMonitoringReportChartView.as_view()),
    path('tent-security-report-sort/', TentSecuritySummaryView.as_view()),
    path('camera-security-report-sort/', CameraSecuritySummaryView.as_view()),
    path('security-violation-report-details/', SecurityViolatioReportDetailsView.as_view()),
]
