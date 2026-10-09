from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="login.html", redirect_authenticated_user=True),
        name="login",
    ),
    # В Django 5+ выход работает только через POST — в шаблонах это форма с кнопкой.
    path("logout/", auth_views.LogoutView.as_view(next_page="index"), name="logout"),
    path("", include("core.urls")),
]
