"""
FastAPI aplikace — Sample Editor API
=====================================
Spouštění: python api/run.py
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routers import analyze, session, export, files
from api.routers.logs import router as logs_router, get_sse_handler

app = FastAPI(
    title="Sample Editor API",
    version="1.0.0",
    description="REST API pro Sample Mapping Editor — analýza, session management, export.",
)

# CORS: povolí přístup pouze z localhost (dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE log handler — zachytává logy z api.* a src.* a streamuje je do prohlížeče
_sse_handler = get_sse_handler()
_sse_handler.setLevel(logging.DEBUG)
for _log_name in ("api", "src"):
    _lg = logging.getLogger(_log_name)
    _lg.setLevel(logging.DEBUG)
    _lg.addHandler(_sse_handler)

# Routery
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(export.router,  prefix="/api/v1", tags=["export"])
app.include_router(files.router,   prefix="/api/v1", tags=["files"])
app.include_router(logs_router,    prefix="/api/v1", tags=["logs"])


_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(str(_frontend_dir / "index.html"))


# Statické soubory frontendu (CSS, JS, assets)
app.mount("/", StaticFiles(directory=str(_frontend_dir)), name="frontend")
