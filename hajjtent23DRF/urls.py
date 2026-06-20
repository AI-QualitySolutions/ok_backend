from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("authentication.urls")),
    path("camera/", include("camera.urls")),
    path("sensor/", include("sensor.urls")),
    path("tent/", include("tent.urls")),
    path("weight/", include("weight.urls")),
    path("livestream/", include("livestream.urls")),
    path("api/camera/", include("counter_camera.urls")),
    path('api/technical-dashboard/', include('technical_dashboard.urls')),
    path("api/access-point/", include("access_point.urls")),
    path("api/tuya/", include("tuya_proxy.urls")),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/',
         SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/',
         SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('model-retrainer/', include('model_retrainer.urls')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    # Only use custom handlers if DEBUG is False
    handler500 = 'rest_framework.exceptions.server_error'
    handler400 = 'rest_framework.exceptions.bad_request'
