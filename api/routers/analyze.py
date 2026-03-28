"""
Analyze endpoints:
  POST /api/v1/analyze              — analýza jednoho souboru
  POST /api/v1/analyze/batch        — dávková analýza (blocking)
  WS   /api/v1/analyze/batch/ws     — dávková analýza s real-time progress
  GET  /api/v1/audio/file           — stream audio souboru
  GET  /api/v1/audio/info           — základní info o souboru (bez analýzy)
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from api.data_dirs import DATA_ROOT
from api.schemas import (
    AnalyzeRequest, AnalyzeResponse, SampleAnalysisResult,
    BatchAnalyzeRequest, BatchAnalyzeResponse,
    AudioInfoResponse,
)
from api.dependencies import get_analysis_service, get_session_service
from src.application.services.analysis_service import AnalysisService
from src.application.services.session_service import SessionService
from src.domain.models.sample import SampleMetadata

router = APIRouter()

_DATA_ROOT = DATA_ROOT.resolve()


def _resolve_safe_path(file_path: str) -> Path:
    """
    Přeloží cestu a ověří, že leží uvnitř data/ adresáře.
    Vyhodí HTTPException 403 při pokusu o přístup mimo data/.
    """
    resolved = Path(file_path).resolve()
    try:
        resolved.relative_to(_DATA_ROOT)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Přístup k souboru mimo data/ adresář je zakázán.",
        )
    return resolved


def _sample_to_result(sample: SampleMetadata, success: bool, error: Optional[str] = None) -> SampleAnalysisResult:
    """Převede SampleMetadata domain objekt na API response schema."""
    return SampleAnalysisResult(
        filename=sample.filename,
        file_path=str(sample.filepath),
        detected_midi=sample.detected_midi,
        detected_frequency=sample.detected_frequency,
        pitch_confidence=sample.pitch_confidence,
        pitch_method=sample.pitch_method,
        velocity_amplitude=sample.velocity_amplitude,
        velocity_amplitude_db=sample.velocity_amplitude_db,
        duration=sample.duration,
        sample_rate=sample.sample_rate,
        channels=sample.channels,
        analyzed=sample.analyzed,
        success=success,
        error=error,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_single(
    request: AnalyzeRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    session_service: SessionService = Depends(get_session_service),
) -> AnalyzeResponse:
    """
    Analyzuje jeden audio soubor — detekce MIDI noty (CREPE) a velocity (RMS).
    Pokud je zadána session_name, výsledek se uloží do cache.
    """
    path = Path(request.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Soubor '{request.file_path}' nenalezen.")

    sample = SampleMetadata(filepath=path)

    if request.session_name:
        session_service.load_session(request.session_name)
        cached, _ = session_service.analyze_with_cache([sample])
        if cached:
            return AnalyzeResponse(result=_sample_to_result(cached[0], success=True), from_cache=True)

    try:
        success = analysis_service.analyze_sample(sample)
    except Exception as exc:
        return AnalyzeResponse(
            result=_sample_to_result(sample, success=False, error=str(exc)),
            from_cache=False,
        )

    if request.session_name and success:
        session_service.cache_analyzed_samples([sample])

    return AnalyzeResponse(result=_sample_to_result(sample, success=success), from_cache=False)


@router.post("/analyze/batch", response_model=BatchAnalyzeResponse)
def analyze_batch(
    request: BatchAnalyzeRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    session_service: SessionService = Depends(get_session_service),
) -> BatchAnalyzeResponse:
    """
    Dávková analýza seznamu souborů (blocking HTTP).
    Pro real-time progress použijte WebSocket endpoint /analyze/batch/ws.
    """
    if not request.file_paths:
        return BatchAnalyzeResponse(results=[], successful=0, failed=0, from_cache=0)

    samples = [SampleMetadata(filepath=Path(fp)) for fp in request.file_paths if Path(fp).exists()]
    if not samples:
        raise HTTPException(status_code=400, detail="Žádný ze zadaných souborů neexistuje.")

    from_cache_count = 0
    results = []
    to_analyze = samples

    if request.session_name:
        session_service.load_session(request.session_name)
        cached, to_analyze = session_service.analyze_with_cache(samples)
        from_cache_count = len(cached)
        for s in cached:
            results.append(_sample_to_result(s, success=True))

    successful = from_cache_count
    failed = 0

    if to_analyze:
        ok, fail = analysis_service.analyze_batch(to_analyze)
        successful += ok
        failed += fail
        for s in to_analyze:
            results.append(_sample_to_result(s, success=s.analyzed))

        if request.session_name:
            analyzed = [s for s in to_analyze if s.analyzed]
            if analyzed:
                session_service.cache_analyzed_samples(analyzed)

    return BatchAnalyzeResponse(results=results, successful=successful, failed=failed, from_cache=from_cache_count)


@router.websocket("/analyze/batch/ws")
async def analyze_batch_ws(websocket: WebSocket):
    """
    WebSocket endpoint pro dávkovou analýzu s real-time progress.

    Protokol (klient → server):
      {"file_paths": [...], "session_name": "..."}   ← volitelné session_name

    Protokol (server → klient):
      {"type": "start",    "total": N}
      {"type": "progress", "current": N, "total": M, "filename": "..."}
      {"type": "result",   "filename": "...", "success": bool, ...}
      {"type": "done",     "successful": N, "failed": M, "from_cache": K}
      {"type": "error",    "message": "..."}
    """
    await websocket.accept()

    analysis_service = get_analysis_service()
    session_service = get_session_service()

    try:
        data = await websocket.receive_json()
        file_paths = data.get("file_paths", [])
        session_name = data.get("session_name")

        samples = [SampleMetadata(filepath=Path(fp)) for fp in file_paths if Path(fp).exists()]
        if not samples:
            await websocket.send_json({"type": "error", "message": "Žádný soubor nenalezen."})
            return

        total = len(samples)
        await websocket.send_json({"type": "start", "total": total})

        # Cache lookup
        from_cache_count = 0
        to_analyze = samples
        if session_name:
            session_service.load_session(session_name)
            cached, to_analyze = session_service.analyze_with_cache(samples)
            from_cache_count = len(cached)
            for s in cached:
                await websocket.send_json({
                    "type": "result",
                    **_sample_to_result(s, success=True).model_dump(),
                    "from_cache": True,
                })

        successful = from_cache_count
        failed = 0

        for i, sample in enumerate(to_analyze, 1):
            await websocket.send_json({
                "type": "progress",
                "current": from_cache_count + i,
                "total": total,
                "filename": sample.filename,
            })

            # Blokující analýza v thread poolu — neblokuje event loop
            ok = await asyncio.to_thread(analysis_service.analyze_sample, sample)

            await websocket.send_json({
                "type": "result",
                **_sample_to_result(sample, success=ok).model_dump(),
                "from_cache": False,
            })

            if ok:
                successful += 1
            else:
                failed += 1

        if session_name and to_analyze:
            analyzed = [s for s in to_analyze if s.analyzed]
            if analyzed:
                session_service.cache_analyzed_samples(analyzed)

        await websocket.send_json({
            "type": "done",
            "successful": successful,
            "failed": failed,
            "from_cache": from_cache_count,
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.get("/audio/file")
def serve_audio(file_path: str):
    """
    Vrátí audio soubor pro přehrávání v prohlížeči.
    Přístup je omezen pouze na soubory uvnitř data/ adresáře.
    """
    path = _resolve_safe_path(file_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Soubor nenalezen.")
    return FileResponse(str(path), media_type="audio/wav")


@router.get("/audio/info", response_model=AudioInfoResponse)
def audio_info(
    file_path: str,
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> AudioInfoResponse:
    """Vrátí základní technické informace o audio souboru (délka, sample rate, kanály)."""
    path = _resolve_safe_path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Soubor nenalezen.")

    info = analysis_service.get_audio_info(path)
    if info is None:
        raise HTTPException(status_code=422, detail="Soubor nelze přečíst jako audio.")

    return AudioInfoResponse(
        file_path=str(path),
        duration=info.get("duration"),
        sample_rate=info.get("sample_rate"),
        channels=info.get("channels"),
        frames=info.get("frames"),
    )
