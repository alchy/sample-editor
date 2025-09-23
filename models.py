"""
models.py - Datové modely pro Sampler Editor
"""

from pathlib import Path
from typing import Optional


class SampleMetadata:
    """Metadata pro audio sample"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name

        # Analýza výsledky
        self.detected_midi: Optional[int] = None
        self.detected_frequency: Optional[float] = None
        self.pitch_confidence: Optional[float] = None
        self.velocity_level: Optional[int] = None  # 0-7
        self.rms_db: Optional[float] = None

        # Audio info
        self.duration: Optional[float] = None
        self.sample_rate: Optional[int] = None
        self.channels: Optional[int] = None

        # Status
        self.analyzed: bool = False
        self.mapped: bool = False

    def __str__(self):
        return f"SampleMetadata({self.filename}, MIDI: {self.detected_midi}, Vel: {self.velocity_level})"

    def __repr__(self):
        return self.__str__()