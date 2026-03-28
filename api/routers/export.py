"""
Export endpoints:
  POST /api/v1/export          — spustí export (Ithaca WAV formát)
  POST /api/v1/export/preview  — náhled co se bude exportovat (bez zápisu na disk)
  POST /api/v1/export/sf2      — generuje a vrátí SF2 soubor ke stažení
"""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

from api.schemas import ExportRequest, ExportResult, ExportPreviewItem, MappingEntry, Sf2ExportRequest
from api.dependencies import get_session_service
from api.data_dirs import export_dir, DATA_ROOT
from src.application.services.session_service import SessionService
from src.domain.models.sample import SampleMetadata
from src.export_utils import ExportManager
from src.infrastructure.export.sf2_exporter import Sf2Exporter

router = APIRouter()


_DATA_ROOT = DATA_ROOT.resolve()


def _safe_source_path(file_path: str) -> Path | None:
    """Přeloží cestu a ověří, že leží uvnitř data/. Vrátí None pro neplatné cesty."""
    try:
        p = Path(file_path).resolve()
        p.relative_to(_DATA_ROOT)
        return p if p.exists() else None
    except ValueError:
        return None


def _build_mapping(entries: List[MappingEntry]) -> dict:
    """
    Sestaví mapping dict ve formátu, který očekává ExportManager.
    Soubory mimo data/ jsou tiše přeskočeny.
    """
    mapping = {}
    for entry in entries:
        path = _safe_source_path(entry.file_path)
        if path is None:
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
        session_metadata = {}
        if request.session_name:
            data = session_service.get_session_data(request.session_name) or {}
            session_metadata = data.get("metadata", {})
            session_metadata["session_name"] = request.session_name
            session_metadata["velocity_layers"] = data.get("velocity_layers", 4)

        try:
            def_path = manager.export_instrument_definition(session_metadata, mapping)
            instrument_def_path = str(def_path) if def_path else None
        except Exception as exc:
            logger.warning(f"Export instrument-definition.json selhal: {exc}")

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


@router.post("/export/sf2")
def export_sf2(
    request: Sf2ExportRequest,
    session_service: SessionService = Depends(get_session_service),
) -> Response:
    """
    Vygeneruje SoundFont 2 (.sf2) soubor ze stávajícího mappingu a vrátí jej ke stažení.
    """
    if not request.mapping:
        raise HTTPException(status_code=400, detail="Mapping je prázdný.")

    # Zjisti instrument_name a velocity_layers ze session, pokud nejsou explicitně zadány
    instrument_name = request.instrument_name or "Custom Bank"
    velocity_layers = request.velocity_layers

    if request.session_name:
        data = session_service.get_session_data(request.session_name) or {}
        meta = data.get("metadata", {})
        if not request.instrument_name:
            instrument_name = meta.get("instrument_name", instrument_name)
        if request.velocity_layers == 4:
            velocity_layers = data.get("velocity_layers", velocity_layers)

    # Sestav mapping {(midi_note, vel_layer): Path} — pouze soubory uvnitř data/
    path_mapping: dict[tuple[int, int], Path] = {}
    for entry in request.mapping:
        p = _safe_source_path(entry.file_path)
        if p is not None:
            path_mapping[(entry.midi_note, entry.velocity)] = p

    if not path_mapping:
        raise HTTPException(status_code=400, detail="Žádný ze souborů v mappingu neexistuje.")

    try:
        sf2_bytes = Sf2Exporter().export(path_mapping, instrument_name, velocity_layers)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SF2 export selhal: {exc}")

    filename = f"{request.session_name or 'export'}.sf2"
    return Response(
        content=sf2_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
