"""后台任务。向量化入库走这里，不要堵在 Gateway 请求线程里。"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from worker.celery_app import celery_app


@celery_app.task(name="worker.ping")
def ping_task() -> str:
    return "pong"


@celery_app.task(name="worker.ingest_document")
def ingest_document_task(title: str, content: str, source: str = "") -> dict:
    from data.rag import ingest_document

    return ingest_document(title=title, content=content, source=source)
