from django.urls import path

from . import views
from .ent_views import ent_specification, ent_forecast

urlpatterns = [
    path("api/ent/forecast/", ent_forecast, name="ent_forecast"),
    path("api/ent/specifications/<int:year>/", ent_specification, name="ent_specification"),
    path("language/", views.set_language, name="set_language"),
    path("api/leads/", views.lead_create, name="lead_create"),

    # Кабинет: материалы
    path("app/", views.dashboard, name="dashboard"),
    path("app/analytics/", views.analytics, name="analytics"),
    path("app/materials/<slug:slug>/", views.dashboard, name="section"),
    path("app/materials/<slug:slug>/quiz/", views.topic_quiz, name="topic_quiz"),
    path("app/ai/ask/", views.ai_ask_home, name="ai_ask_home"),
    path("app/ai/reset/", views.ai_reset_home, name="ai_reset_home"),
    path("app/materials/<slug:slug>/ai/ask/", views.ai_ask, name="ai_ask"),
    path("app/materials/<slug:slug>/ai/reset/", views.ai_reset, name="ai_reset"),

    # Лайв-контест
    path("contest/", views.contest, name="contest"),
    path("contest/login/", views.contest_login, name="contest_login"),
    path("contest/logout/", views.contest_logout, name="contest_logout"),
    path("contest/submit/", views.contest_submit, name="contest_submit"),
]
