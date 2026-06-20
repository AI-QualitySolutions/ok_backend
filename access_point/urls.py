from django.urls import path
from . import views

urlpatterns = [
    path('router-heartbeat/', views.save_router_heartbeat, name='save_router_heartbeat'),
    path('router-status/', views.router_status, name='router_status'),
]