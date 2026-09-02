from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from gateway import api, chat

urlpatterns = [
    path("", api.index),
    path("api/health", api.api_health),
    path("api/tools", api.ToolsView.as_view()),
    path("api/conversations", api.ConversationListView.as_view()),
    path("api/conversations/<str:conversation_id>/messages", api.MessageListView.as_view()),
    path("api/conversations/<str:conversation_id>/stop", chat.api_stop),
    path("api/conversations/<str:conversation_id>", api.ConversationDetailView.as_view()),
    path("api/memories", api.MemoryListView.as_view()),
    path("api/memories/<int:memory_id>", api.MemoryDetailView.as_view()),
    path("api/documents", api.DocumentListView.as_view()),
    path("api/documents/<int:document_id>", api.DocumentDetailView.as_view()),
    path("api/jobs/<str:job_id>", api.JobDetailView.as_view()),
    path("api/chat", chat.api_chat),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.CLIENT_DIR)
