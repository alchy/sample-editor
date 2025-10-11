"""
AudioFileLoader - Načítání audio souborů pomocí dostupných knihoven.
"""
import logging
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from src.domain.interfaces.audio_analyzer import IAudioFileLoader, AudioData

logger = logging.getLogger(__name__)

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available")


class AudioFileLoader(IAudioFileLoader):
    """Načítá audio soubory pomocí soundfile nebo librosa."""

    def load(self, file_path: Path) -> Optional[AudioData]:
        """
        Načte audio soubor.

        Args:
            file_path: Cesta k audio souboru

        Returns:
            AudioData nebo None při chybě
        """
        filepath = file_path
        errors = []
        
        # Pokus o soundfile
        if SOUNDFILE_AVAILABLE:
            try:
                waveform, sr = sf.read(str(filepath))
                channels = 1 if len(waveform.shape) == 1 else waveform.shape[1]
                logger.debug(f"Loaded {filepath.name} with soundfile")
                return AudioData(waveform, sr, channels)
            except Exception as e:
                errors.append(f"soundfile: {str(e)[:100]}")
                logger.debug(f"Soundfile failed: {e}")
        
        # Pokus o librosa
        if LIBROSA_AVAILABLE:
            try:
                waveform, sr = librosa.load(str(filepath), sr=None)
                channels = 1 if len(waveform.shape) == 1 else waveform.shape[1]
                if len(waveform.shape) == 1:
                    waveform = waveform.reshape(-1, 1)
                logger.debug(f"Loaded {filepath.name} with librosa")
                return AudioData(waveform, sr, channels)
            except Exception as e:
                errors.append(f"librosa: {str(e)[:100]}")
                logger.debug(f"Librosa failed: {e}")
        
        # Chyba
        all_errors = "; ".join(errors)
        logger.error(f"Failed to load {filepath.name}. Tried: {all_errors}")
        return None
    
    def get_audio_info(self, file_path: Path) -> Optional[dict]:
        """
        Získá informace o audio souboru bez načtení celého obsahu.

        Args:
            file_path: Cesta k souboru

        Returns:
            Dict s info (duration, sample_rate, channels) nebo None
        """
        filepath = file_path
        if SOUNDFILE_AVAILABLE:
            try:
                info = sf.info(str(filepath))
                return {
                    "duration": info.duration,
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "frames": info.frames
                }
            except Exception as e:
                logger.debug(f"Failed to get info: {e}")
        
        return None
    
    @staticmethod
    def get_supported_formats() -> list:
        """Vrátí seznam podporovaných formátů."""
        formats = []
        
        if SOUNDFILE_AVAILABLE:
            formats.extend(['WAV', 'FLAC', 'AIFF'])
        
        if LIBROSA_AVAILABLE:
            formats.extend(['MP3', 'OGG', 'M4A'])
        
        return list(set(formats))
