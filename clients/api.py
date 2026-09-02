"""多端共用的 Gateway HTTP 客户端。Web 用 fetch，CLI / 桌面用这个。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

DEFAULT_BASE = os.environ.get("AGENT_URL", "http://127.0.0.1:8080").rstrip("/")


class AgentClient:
    def __init__(self, base: str | None = None, client: str = "cli") -> None:
        self.base = (base or DEFAULT_BASE).rstrip("/")
        self.client = client

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"X-Client": self.client, "Accept": "application/json"}
        if extra:
            headers.update(extra)
        return headers

    def _open(self, path: str, method: str = "GET", payload: dict | None = None, timeout: int = 30):
        data = None
        headers = self._headers()
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        return urllib.request.urlopen(req, timeout=timeout)

    def _json(self, path: str, method: str = "GET", payload: dict | None = None, timeout: int = 30) -> Any:
        try:
            with self._open(path, method=method, payload=payload, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(detail)
                detail = parsed.get("detail") or detail
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"{exc.code}: {detail}") from exc
        if not raw:
            return None
        return json.loads(raw)

    def health(self) -> dict:
        return self._json("/api/health")

    def conversations(self) -> list:
        return self._json("/api/conversations") or []

    def messages(self, conversation_id: str) -> list:
        return self._json(f"/api/conversations/{conversation_id}/messages") or []

    def stop(self, conversation_id: str) -> dict:
        return self._json(f"/api/conversations/{conversation_id}/stop", method="POST") or {}

    def chat(self, message: str, conversation_id: str | None = None) -> Iterator[dict]:
        payload = {"message": message, "conversation_id": conversation_id}
        headers = self._headers({"Content-Type": "application/json", "Accept": "text/event-stream"})
        req = urllib.request.Request(
            f"{self.base}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=650)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"{exc.code}: {detail}") from exc
        with resp:
            buf = ""
            while True:
                chunk = resp.read(256)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", "replace")
                while "\n\n" in buf:
                    part, buf = buf.split("\n\n", 1)
                    line = next((ln for ln in part.split("\n") if ln.startswith("data: ")), None)
                    if not line:
                        continue
                    yield json.loads(line[6:])
