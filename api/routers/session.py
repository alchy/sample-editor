"""
Session endpoints:
  GET  /api/v1/session/list          — seznam všech sessions
  POST /api/v1/session               — vytvoření nové session
  GET  /api/v1/session/{name}        — načtení session
  POST /api/v1/session/{name}/folders — nastavení složek
  POST /api/v1/session/{name}/scan   — skenování složky
"""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    SessionCreateRequest, SessionInfo, SessionListResponse,
    FolderScanRequest, FolderScanResponse,
)
from api.dependencies import get_session_service
from api.data_dirs import DATA_ROOT
from src.application.services.session_service import SessionService

router = APIRouter()


def _session_to_info(service: SessionService, name: str) -> SessionInfo:
    """Převede data session na SessionInfo schema."""
    data = service.get_session_data(name) or {}
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
    return SessionListResponse(sessions=service.list_sessions())


@router.post("/session", response_model=SessionInfo)
def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
):
    """Vytvoří novou session."""
    ok = service.create_session(request.name)
    if not ok:
        raise HTTPException(status_code=409, detail=f"Session '{request.name}' již existuje.")

    data = service.get_session_data(request.name) or {}
    data["velocity_layers"] = request.velocity_layers

    if request.instrument_name or request.author:
        meta = data.setdefault("metadata", {})
        if request.instrument_name:
            meta["instrument_name"] = request.instrument_name
        if request.author:
            meta["author"] = request.author

    if request.input_folder or request.output_folder:
        folders = data.setdefault("folders", {})
        if request.input_folder:
            folders["input"] = request.input_folder
        if request.output_folder:
            folders["output"] = request.output_folder

    service.save_session_data(request.name, data)
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
    folder = Path(request.folder_path).resolve()
    # Omezení na DATA_ROOT — nelze skenovat libovolné systémové složky
    try:
        folder.relative_to(DATA_ROOT.resolve())
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Skenování složek mimo data/ adresář je zakázáno.",
        )
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Složka neexistuje.")

    extensions = {ext.lower() for ext in request.extensions}
    files: List[str] = [
        str(f) for f in sorted(folder.iterdir())
        if f.is_file() and f.suffix.lower() in extensions
    ]
    return FolderScanResponse(files=files, count=len(files))
