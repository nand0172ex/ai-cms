from django.urls import path

from apps.conversations import views

app_name = "conversations"

urlpatterns = [
    path("", views.ai_assistant_home, name="ai_assistant_home"),
    path("assistants/<slug:slug>/", views.assistant_chat_page, name="assistant_chat_page"),
]
