from django.urls import path, include
from rest_framework.routers import DefaultRouter
from weight.views import (DeviceWeightViewSet, AddNewOrderView, WeightConditionsViewSet,
                          TentFoodWeightsView, FoodWeightsView,
                          FoodWeightReportView, FoodCardView, FoodGraphView
                          )

router = DefaultRouter()
router.register('device-weights', DeviceWeightViewSet)
router.register('weight-conditions', WeightConditionsViewSet)

urlpatterns = [
    path('add-new-order/', AddNewOrderView.as_view()),
    path('tent-food-weight/', FoodWeightsView.as_view()),
    path('tent-food-weight/<int:tent_id>/', TentFoodWeightsView.as_view()),
    path('food-weight-report/', FoodWeightReportView.as_view()),
    path('food-card-view/', FoodCardView.as_view()),
    path('food-graph-view/', FoodGraphView.as_view()),
    path('', include(router.urls)),
]
