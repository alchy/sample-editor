"""
SSE log stream:
  GET /api/v1/logs/stream  — Server-Sent Events stream Python logů
"""

import asyncio
import json
import logging
import queue
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

_MAX_QUEUE = 500


class SseLogHandler(logging.Handler):
    """
    Logging handler zachytávající záznamy do thread-safe queue.
    emit() je volán z libovolného vlákna (analýza běží v thread poolu).
    """

    def __init__(self):
        super().__init__()
        self._q: queue.Queue = queue.Queue(maxsize=_MAX_QUEUE)
        self.setFormatter(logging.Formatter("%(name)s — %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._q.put_nowait({
                "level": record.levelname,
                "msg": self.format(record),
                "time": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
            })
        except queue.Full:
            pass  # zahoď nový záznam, queue je plná


# Singleton handler — sdílen celou aplikací
_handler: SseLogHandler | None = None


def get_sse_handler() -> SseLogHandler:
    global _handler
    if _handler is None:
        _handler = SseLogHandler()
    return _handler


async def _event_generator(handler: SseLogHandler):
    """Async generátor čtoucí záznamy z queue a emitující SSE data."""
    keepalive = 0
    while True:
        try:
            record = handler._q.get_nowait()
            yield f"data: {json.dumps(record, ensure_ascii=False)}\n\n"
            keepalive = 0
        except queue.Empty:
            await asyncio.sleep(0.1)
            keepalive += 1
            if keepalive >= 150:          # komentář / keepalive každých ~15 s
                yield ": keepalive\n\n"
                keepalive = 0


@router.get("/logs/stream")
async def stream_logs():
    """
    SSE endpoint — streamuje Python log záznamy (INFO+) do prohlížeče.
    Klient se připojí přes EventSource a přijímá JSON záznamy:
      { "level": "INFO", "msg": "...", "time": "HH:MM:SS" }
    """
    handler = get_sse_handler()
    return StreamingResponse(
        _event_generator(handler),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # vypne Nginx buffering
        },
    )
