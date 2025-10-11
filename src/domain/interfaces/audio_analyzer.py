"""
Interface pro Audio Analyzery - definuje kontrakt pro analýzu audio.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
import numpy as np


class AudioData:
    """Value object pro audio data."""
    
    def __init__(self, samples: np.ndarray, sample_rate: int, channels: int = 1):
        self.samples = samples
        self.sample_rate = sample_rate
        self.channels = channels
        self.duration = len(samples) / sample_rate


class PitchAnalysisResult:
    """Výsledek pitch analýzy."""
    
    def __init__(
        self,
        detected_midi: Optional[int] = None,
        detected_frequency: Optional[float] = None,
        confidence: Optional[float] = None,
        method: str = "unknown"
    ):
        self.detected_midi = detected_midi
        self.detected_frequency = detected_frequency
        self.confidence = confidence
        self.method = method


class AmplitudeAnalysisResult:
    """Výsledek amplitude analýzy."""
    
    def __init__(
        self,
        velocity_amplitude: Optional[float] = None,
        velocity_amplitude_db: Optional[float] = None,
        velocity_duration_ms: Optional[float] = None,
        rms_amplitude: Optional[float] = None,
        peak_amplitude: Optional[float] = None
    ):
        self.velocity_amplitude = velocity_amplitude
        self.velocity_amplitude_db = velocity_amplitude_db
        self.velocity_duration_ms = velocity_duration_ms
        self.rms_amplitude = rms_amplitude
        self.peak_amplitude = peak_amplitude


class IAudioAnalyzer(ABC):
    """
    Base interface pro audio analyzéry.
    Konkrétní implementace: CrepeAnalyzer, RmsAnalyzer, atd.
    """

    @abstractmethod
    def analyze(self, audio_data: AudioData) -> dict:
        """
        Analyzuje audio data a vrátí výsledky.
        
        Args:
            audio_data: Audio data k analýze
            
        Returns:
            Dictionary s výsledky analýzy
        """
        pass


class IPitchAnalyzer(IAudioAnalyzer):
    """Interface pro pitch detection analyzéry."""

    @abstractmethod
    def analyze(self, audio_data: AudioData) -> PitchAnalysisResult:
        """
        Detekuje pitch (výšku tónu) z audio dat.
        
        Args:
            audio_data: Audio data
            
        Returns:
            PitchAnalysisResult s MIDI notou, frekvencí a confidence
        """
        pass


class IAmplitudeAnalyzer(IAudioAnalyzer):
    """Interface pro amplitude/velocity analyzéry."""

    @abstractmethod
    def analyze(self, audio_data: AudioData) -> AmplitudeAnalysisResult:
        """
        Analyzuje amplitudu/velocity z audio dat.
        
        Args:
            audio_data: Audio data
            
        Returns:
            AmplitudeAnalysisResult s RMS a peak hodnotami
        """
        pass


class IAudioFileLoader(ABC):
    """Interface pro načítání audio souborů."""

    @abstractmethod
    def load(self, file_path: Path) -> Optional[AudioData]:
        """
        Načte audio soubor.
        
        Args:
            file_path: Cesta k audio souboru
            
        Returns:
            AudioData nebo None při chybě
        """
        pass

    @abstractmethod
    def get_audio_info(self, file_path: Path) -> Optional[dict]:
        """
        Získá informace o audio souboru bez načtení celého obsahu.
        
        Args:
            file_path: Cesta k souboru
            
        Returns:
            Dictionary s info (duration, sample_rate, channels) nebo None
        """
        pass
