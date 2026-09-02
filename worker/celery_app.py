"""Celery 应用。Worker 用这个入口：celery -A worker.celery_app worker --pool=solo"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows 子进程不一定带上项目根目录，先塞进 sys.path 和 PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
existing = os.environ.get("PYTHONPATH", "")
if str(ROOT_DIR) not in existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = str(ROOT_DIR) if not existing else str(ROOT_DIR) + os.pathsep + existing

from celery import Celery

from config import settings

# Windows 上 prefork 容易挂，solo 足够学习用
if os.name == "nt":
    os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")

celery_app = Celery(
    "myaiagent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    worker_hijack_root_logger=False,
)
