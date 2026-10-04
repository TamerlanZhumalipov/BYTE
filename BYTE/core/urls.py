from django.urls import path

from . import views, learning

urlpatterns = [
    path("app/materials/<slug:slug>/complete/", learning.lesson_complete, name="lesson_complete"),
    path("app/quizzes/", learning.quizzes, name="quizzes"),
    path("app/quizzes/<int:pk>/", learning.quiz_detail, name="quiz_detail"),
    path("app/results/", learning.results, name="results"),
    path("app/results/<int:pk>/", learning.quiz_result, name="quiz_result"),
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
