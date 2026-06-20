from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from authentication.views import UserRegistrationView, UserLoginView, UserView, CompanyWithPerm, CompanyWithLogo, PermissionList, CompanyListView, ServerTime, UserPermissionView

urlpatterns = [
    path("register/", UserRegistrationView.as_view(),),
    path("login/", UserLoginView.as_view()),
    path("users/", UserView.as_view()),
    path("users/<int:pk>/", UserView.as_view()),
    path('token-refresh/', TokenRefreshView.as_view()),
    path('permissions/', PermissionList.as_view()),
    path('user-permission/', UserPermissionView.as_view()),
    path('company-logo/', CompanyWithLogo.as_view()),

    # need to delete this as soon as possible
    path('company/', CompanyWithPerm.as_view()),
    path('all-company/', CompanyListView.as_view()),
    path('time/', ServerTime.as_view()),
]
