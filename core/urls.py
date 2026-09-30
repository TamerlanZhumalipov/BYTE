from django.urls import path

from . import views

urlpatterns = [
    path("api/leads/", views.lead_create, name="lead_create"),
    path("api/ai/", views.ai_chat, name="ai_chat"),

    # Кабинет: материалы
    path("app/", views.dashboard, name="dashboard"),
    path("app/materials/<slug:slug>/", views.dashboard, name="section"),

    # Лайв-контест
    path("contest/", views.contest, name="contest"),
    path("contest/login/", views.contest_login, name="contest_login"),
    path("contest/logout/", views.contest_logout, name="contest_logout"),
    path("contest/submit/", views.contest_submit, name="contest_submit"),
]
