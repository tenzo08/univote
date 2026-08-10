from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import ChangePasswordView, EmailTokenObtainPairView, MeView

urlpatterns = [
    path("auth/login/", EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
