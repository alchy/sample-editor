"""
Domain interfaces pro Sample Editor.
"""

from .session_repository import ISessionRepository
from .audio_analyzer import (
    IAudioAnalyzer,
    IPitchAnalyzer,
    IAmplitudeAnalyzer,
    IAudioFileLoader,
    AudioData,
    PitchAnalysisResult,
    AmplitudeAnalysisResult
)

__all__ = [
    "ISessionRepository",
    "IAudioAnalyzer",
    "IPitchAnalyzer",
    "IAmplitudeAnalyzer",
    "IAudioFileLoader",
    "AudioData",
    "PitchAnalysisResult",
    "AmplitudeAnalysisResult",
]
