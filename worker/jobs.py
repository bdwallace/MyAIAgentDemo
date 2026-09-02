"""把「排队 / 查进度」从 Gateway 路由里抽出来。"""

from __future__ import annotations

from celery.result import AsyncResult

from worker.celery_app import celery_app
from worker.tasks import ingest_document_task


def celery_alive() -> bool:
    try:
        ping = celery_app.control.inspect(timeout=0.8).ping()
        return bool(ping)
    except Exception:
        return False


def enqueue_ingest(title: str, content: str, source: str = "") -> dict:
    if not (content or "").strip():
        raise ValueError("正文是空的")
    async_result = ingest_document_task.delay(title, content, source)
    return {"job_id": async_result.id, "status": "queued"}


def job_status(job_id: str) -> dict:
    result = AsyncResult(job_id, app=celery_app)
    payload = {
        "job_id": job_id,
        "status": result.state,
        "result": None,
        "error": None,
    }
    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result)
    return payload
