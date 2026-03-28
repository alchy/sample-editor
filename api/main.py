"""
FastAPI aplikace — Sample Editor API
=====================================
Spouštění: python api/run.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routers import analyze, session, export, files

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

# Routery
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(export.router,  prefix="/api/v1", tags=["export"])
app.include_router(files.router,   prefix="/api/v1", tags=["files"])


_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(str(_frontend_dir / "index.html"))


# Statické soubory frontendu (CSS, JS, assets)
app.mount("/", StaticFiles(directory=str(_frontend_dir)), name="frontend")
