"""
Session endpoints:
  GET  /api/v1/session/list          — seznam všech sessions
  POST /api/v1/session               — vytvoření nové session
  GET  /api/v1/session/{name}        — načtení session
  POST /api/v1/session/{name}/folders — nastavení složek
  GET  /api/v1/session/{name}/scan   — skenování input složky
"""

import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    SessionCreateRequest, SessionInfo, SessionListResponse,
    FolderScanRequest, FolderScanResponse,
)
from api.dependencies import get_session_service
from src.application.services.session_service import SessionService

router = APIRouter()


def _session_to_info(service: SessionService, name: str) -> SessionInfo:
    """Převede interní stav session na SessionInfo schema."""
    data = service.repository.load_session(name) if hasattr(service, "repository") else {}
    if not data:
        # Fallback: přímé čtení přes service
        service.load_session(name)
        data = getattr(service, "_current_session_data", {}) or {}

    return SessionInfo(
        name=name,
        created=data.get("created"),
        last_modified=data.get("last_modified"),
        velocity_layers=data.get("velocity_layers", 4),
        cached_samples=len(data.get("samples_cache", {})),
        mapping_entries=len(data.get("mapping", {})),
        input_folder=data.get("folders", {}).get("input"),
        output_folder=data.get("folders", {}).get("output"),
    )


@router.get("/session/list", response_model=SessionListResponse)
def list_sessions(service: SessionService = Depends(get_session_service)):
    """Vrátí seznam názvů všech existujících sessions."""
    names = service.list_sessions() if hasattr(service, "list_sessions") else []
    return SessionListResponse(sessions=names)


@router.post("/session", response_model=SessionInfo)
def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
):
    """Vytvoří novou session."""
    ok = service.create_session(request.name)
    if not ok:
        raise HTTPException(status_code=409, detail=f"Session '{request.name}' již existuje nebo ji nelze vytvořit.")

    # Nastavení volitelných metadat
    if any([request.velocity_layers, request.instrument_name, request.input_folder, request.output_folder]):
        data = service.get_session_data(request.name) if hasattr(service, "get_session_data") else {}
        if data is not None:
            data["velocity_layers"] = request.velocity_layers
            if request.instrument_name:
                data.setdefault("metadata", {})["instrument_name"] = request.instrument_name
            if request.author:
                data.setdefault("metadata", {})["author"] = request.author
            if request.input_folder or request.output_folder:
                data.setdefault("folders", {})
                if request.input_folder:
                    data["folders"]["input"] = request.input_folder
                if request.output_folder:
                    data["folders"]["output"] = request.output_folder
            service.save_session_data(request.name, data) if hasattr(service, "save_session_data") else None

    return _session_to_info(service, request.name)


@router.get("/session/{name}", response_model=SessionInfo)
def get_session(name: str, service: SessionService = Depends(get_session_service)):
    """Načte informace o existující session."""
    ok = service.load_session(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{name}' nenalezena.")
    return _session_to_info(service, name)


@router.post("/session/{name}/scan", response_model=FolderScanResponse)
def scan_folder(
    name: str,
    request: FolderScanRequest,
    service: SessionService = Depends(get_session_service),
):
    """
    Prohledá zadanou složku a vrátí seznam audio souborů.
    Neanalyzuje — jen vrátí cesty pro následné volání /analyze/batch.
    """
    folder = Path(request.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Složka '{request.folder_path}' neexistuje.")

    extensions = {ext.lower() for ext in request.extensions}
    files: List[str] = [
        str(f) for f in sorted(folder.iterdir())
        if f.is_file() and f.suffix.lower() in extensions
    ]
    return FolderScanResponse(files=files, count=len(files))
