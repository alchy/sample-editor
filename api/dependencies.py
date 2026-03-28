"""
Dependency injection — vytváří singleton instance services.
FastAPI volá tyto funkce automaticky při každém requestu (lru_cache zajistí sdílení).
"""

from functools import lru_cache

from src.infrastructure.audio.audio_file_loader import AudioFileLoader
from src.infrastructure.audio.crepe_analyzer import CrepeAnalyzer
from src.infrastructure.audio.rms_analyzer import RmsAnalyzer
from src.application.services.analysis_service import AnalysisService
from src.application.services.session_service import SessionService


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """
    Singleton AnalysisService.
    CREPE model se načte při prvním volání (~5-10s), pak se drží v paměti.
    """
    return AnalysisService(
        audio_loader=AudioFileLoader(),
        pitch_analyzer=CrepeAnalyzer(model_capacity="tiny", max_analysis_duration=5.0),
        amplitude_analyzer=RmsAnalyzer(velocity_duration_ms=500.0),
    )


@lru_cache(maxsize=1)
def get_session_service() -> SessionService:
    """Singleton SessionService."""
    return SessionService()
