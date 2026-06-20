from django.urls import path
from .views import LiveStreamListView
 
urlpatterns = [
    path('', LiveStreamListView.as_view()),
]
 