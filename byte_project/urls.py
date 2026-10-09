from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.decorators.http import require_POST

from core import views
from core.auth_views import ReactLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path(
        "login/",
        ReactLoginView.as_view(),
        name="login",
    ),
    # В Django 5+ выход работает только через POST — в шаблонах это форма с кнопкой.
    path("logout/", require_POST(auth_views.LogoutView.as_view(next_page="index")), name="logout"),
    path("", include("core.urls")),
]
