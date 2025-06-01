from django.urls import path
from . import views


app_name = "accounts"
urlpatterns = [
    path("my/", views.user_profile, name="user_profile"),
    path("auth/login/", views.log_in, name="login"),
    path("auth/logout/", views.log_out, name="logout"),
]
