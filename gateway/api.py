"""REST：会话 / 记忆 / 知识库 / 健康检查。聊天 SSE 在 chat.py。"""

from __future__ import annotations

from django.conf import settings as dj_settings
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config import settings
from data.db import (
    delete_conversation,
    list_conversations,
    load_messages,
    ping,
)
from data.memory import delete_memory, list_memories, memory_count
from data.rag import chunk_count, delete_document, list_documents, pgvector_available


def index(_request):
    path = dj_settings.CLIENT_DIR / "index.html"
    return HttpResponse(path.read_bytes(), content_type="text/html; charset=utf-8")


async def api_health(_request):
    """async：避免 Django ASGI 线程池里跑 Celery inspect 把自己卡死。"""
    from data.cache import ping as redis_ping
    from model.embed import embedding_backend
    from model.llm import inspect_llm
    from tools import ALL_TOOLS, catalog
    from tools.sandbox import jail_status
    from worker.jobs import celery_alive

    db_ok = False
    try:
        db_ok = ping()
    except Exception:
        db_ok = False
    llm = inspect_llm()
    return JsonResponse(
        {
            "ok": db_ok and llm["ready"],
            "postgres": db_ok,
            "redis": redis_ping(),
            "celery": celery_alive(),
            "sandbox": jail_status(),
            "llm": llm,
            "has_api_key": True if llm["local"] else bool(settings.llm_api_key),
            "model": settings.llm_model,
            "tools": [t.name for t in ALL_TOOLS],
            "tool_groups": catalog(),
            "memories": memory_count(),
            "rag": {
                "pgvector": pgvector_available(),
                "chunks": chunk_count(),
                "embedding": embedding_backend(),
            },
        }
    )


class ToolsView(APIView):
    def get(self, _request):
        from tools import catalog

        return Response(catalog())


class ConversationListView(APIView):
    def get(self, _request):
        return Response(list_conversations())


class ConversationDetailView(APIView):
    def delete(self, _request, conversation_id: str):
        from gateway.chat import cancel_run

        cancel_run(conversation_id)
        if not delete_conversation(conversation_id):
            return Response({"detail": "会话不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"ok": True})


class MessageListView(APIView):
    def get(self, _request, conversation_id: str):
        return Response(load_messages(conversation_id, limit=200))


class MemoryListView(APIView):
    def get(self, _request):
        return Response(list_memories())


class MemoryDetailView(APIView):
    def delete(self, _request, memory_id: int):
        if not delete_memory(memory_id):
            return Response({"detail": "记忆不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"ok": True})


class DocumentListView(APIView):
    def get(self, _request):
        return Response(list_documents())

    def post(self, request):
        from worker.jobs import enqueue_ingest

        title = (request.data.get("title") or "").strip()
        content = request.data.get("content") or ""
        try:
            return Response(enqueue_ingest(title, content, "ui"), status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": f"任务队列不可用：{exc}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class DocumentDetailView(APIView):
    def delete(self, _request, document_id: int):
        if not delete_document(document_id):
            return Response({"detail": "文档不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"ok": True})


class JobDetailView(APIView):
    def get(self, _request, job_id: str):
        from worker.jobs import job_status

        return Response(job_status(job_id))
