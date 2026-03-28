"""
Export endpoints:
  POST /api/v1/export          — spustí export
  POST /api/v1/export/preview  — náhled co se bude exportovat (bez zápisu na disk)
"""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import ExportRequest, ExportResult, ExportPreviewItem, MappingEntry
from api.dependencies import get_session_service
from api.data_dirs import export_dir
from src.application.services.session_service import SessionService
from src.domain.models.sample import SampleMetadata
from src.export_utils import ExportManager

router = APIRouter()


def _build_mapping(entries: List[MappingEntry]) -> dict:
    """
    Sestaví mapping dict ve formátu, který očekává ExportManager:
    { (midi_note, velocity): SampleMetadata }
    """
    mapping = {}
    for entry in entries:
        path = Path(entry.file_path)
        if not path.exists():
            continue
        sample = SampleMetadata(filepath=path)
        mapping[(entry.midi_note, entry.velocity)] = sample
    return mapping


@router.post("/export", response_model=ExportResult)
def export_samples(
    request: ExportRequest,
    session_service: SessionService = Depends(get_session_service),
) -> ExportResult:
    """
    Exportuje namapované sampley do output složky.
    Vytvoří WAV soubory ve formátu mXXX-velY-fZZ.wav a instrument-definition.json.
    """
    if request.output_folder:
        output_folder = Path(request.output_folder)
        try:
            output_folder.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Nelze vytvořit output složku: {exc}")
    else:
        output_folder = export_dir(request.session_name)

    if not request.mapping:
        raise HTTPException(status_code=400, detail="Mapping je prázdný.")

    mapping = _build_mapping(request.mapping)
    if not mapping:
        raise HTTPException(status_code=400, detail="Žádný ze souborů v mappingu neexistuje.")

    manager = ExportManager(output_folder)

    try:
        result = manager.export_mapped_samples(mapping)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export selhal: {exc}")

    instrument_def_path = None
    if request.include_instrument_definition:
        # Načíst metadata ze session
        session_metadata = {}
        if request.session_name:
            session_service.load_session(request.session_name)
            data = getattr(session_service, "_session_data", {}) or {}
            session_metadata = data.get("metadata", {})
            session_metadata["session_name"] = request.session_name

        try:
            def_path = manager.export_instrument_definition(session_metadata, mapping)
            instrument_def_path = str(def_path) if def_path else None
        except Exception:
            pass  # instrument definition je volitelná

    failed_files = [
        {"filename": str(f[0]), "error": str(f[1])} if isinstance(f, tuple) else {"filename": str(f), "error": "unknown"}
        for f in result.get("failed_files", [])
    ]

    return ExportResult(
        exported_count=result.get("exported_count", 0),
        failed_count=result.get("failed_count", 0),
        total_files=result.get("total_files", 0),
        exported_files=[str(f) for f in result.get("exported_files", [])],
        failed_files=failed_files,
        instrument_definition_path=instrument_def_path,
    )


@router.post("/export/preview", response_model=List[ExportPreviewItem])
def export_preview(
    request: ExportRequest,
    session_service: SessionService = Depends(get_session_service),
) -> List[ExportPreviewItem]:
    """
    Vrátí náhled co by se exportovalo — bez zápisu na disk.
    Užitečné pro zobrazení v UI před samotným exportem.
    """
    if not request.mapping:
        return []

    if request.output_folder:
        output_folder = Path(request.output_folder)
    else:
        output_folder = export_dir(request.session_name)
    mapping = _build_mapping(request.mapping)
    if not mapping:
        return []

    manager = ExportManager(output_folder)

    try:
        preview = manager.get_export_preview(mapping)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Náhled exportu selhal: {exc}")

    return [
        ExportPreviewItem(
            source_file=item.get("source_file", ""),
            output_file=item.get("output_file", ""),
            midi_note=item.get("midi_note", 0),
            note_name=item.get("note_name", ""),
            velocity=item.get("velocity", 0),
            sample_rate=item.get("sample_rate", 44100),
            valid=item.get("valid", False),
        )
        for item in preview
    ]
