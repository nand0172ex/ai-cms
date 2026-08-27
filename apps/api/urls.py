from django.urls import path

from apps.api import views

app_name = "api"

urlpatterns = [
    path("api/v1/chat/", views.chat, name="chat"),
    path("api/v1/chat/stream/", views.chat_stream, name="chat_stream"),
    path("api/v1/upload-file/", views.upload_file, name="upload_file"),
    path("api/v1/conversations/", views.conversations, name="conversations"),
    path("api/v1/assistants/", views.assistants, name="assistants"),
    path("api/v1/knowledge-bases/", views.knowledge_bases, name="knowledge_bases"),
    path("api/v1/jobs/status/", views.job_status, name="job_status"),
    path("api/v1/runtime-health/", views.runtime_health, name="runtime_health"),
    path("api/v1/errors/summary/", views.error_summary, name="error_summary"),
]
