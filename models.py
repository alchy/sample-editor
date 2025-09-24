"""
models.py - Datové modely pro Sampler Editor s rozšířenou analýzou
"""

from pathlib import Path
from typing import Optional


class SampleMetadata:
    """Metadata pro audio sample s rozšířenou analýzou"""

    def __init__(self, filepath: Path):
        """
        Inicializuje metadata pro audio sample.

        Args:
            filepath: Cesta k souboru.
        """
        self.filepath = filepath
        self.filename = filepath.name

        # Analýza výsledky - Pitch
        self.detected_midi: Optional[int] = None
        self.detected_frequency: Optional[float] = None
        self.pitch_confidence: Optional[float] = None
        self.pitch_method: Optional[str] = None  # Metoda detekce (crepe, librosa, fallback)

        # Analýza výsledky - Amplitude (RMS approach)
        self.velocity_amplitude: Optional[float] = None  # RMS prvních 500ms (pro filtraci a řazení)
        self.velocity_amplitude_db: Optional[float] = None
        self.velocity_duration_ms: Optional[float] = None  # Délka analyzovaného úseku

        # Legacy amplitude hodnoty (pro kompatibilitu)
        self.peak_amplitude: Optional[float] = None  # Percentilový peak (legacy)
        self.peak_amplitude_db: Optional[float] = None
        self.rms_amplitude: Optional[float] = None  # Celkový RMS
        self.rms_amplitude_db: Optional[float] = None
        self.peak_position: Optional[int] = None  # Pozice peaku v samples
        self.peak_position_seconds: Optional[float] = None

        # Attack envelope analýza
        self.attack_peak: Optional[float] = None
        self.attack_time: Optional[float] = None
        self.attack_slope: Optional[float] = None

        # Filtr status
        self.is_filtered: bool = False  # True pokud je mimo rozsah amplitude filtru

        # Audio info
        self.duration: Optional[float] = None
        self.sample_rate: Optional[int] = None
        self.channels: Optional[int] = None

        # Status
        self.analyzed: bool = False
        self.mapped: bool = False

    def __str__(self):
        return f"SampleMetadata({self.filename}, MIDI: {self.detected_midi}, " \
               f"Velocity amplitude: {self.velocity_amplitude:.6f} if self.velocity_amplitude else 'None', " \
               f"Filtered: {self.is_filtered})"

    def __repr__(self):
        return self.__str__()

    def get_pitch_info(self) -> str:
        """Vrátí formátovanou informaci o pitch."""
        if not self.detected_midi:
            return "No pitch detected"

        from midi_utils import MidiUtils
        note_name = MidiUtils.midi_to_note_name(self.detected_midi)
        confidence_str = f" (conf: {self.pitch_confidence:.2f})" if self.pitch_confidence else ""
        method_str = f" [{self.pitch_method}]" if self.pitch_method else ""

        return f"{note_name} ({self.detected_frequency:.1f} Hz){confidence_str}{method_str}"

    def get_amplitude_info(self) -> str:
        """Vrátí formátovanou informaci o amplitude - RMS prvních 500ms."""
        if self.velocity_amplitude is None:
            return "No amplitude data"

        db_str = f" ({self.velocity_amplitude_db:.1f} dB)" if self.velocity_amplitude_db is not None else ""
        filtered_str = " [FILTERED]" if self.is_filtered else ""
        duration_str = f" (RMS {self.velocity_duration_ms:.0f}ms)" if self.velocity_duration_ms else ""

        return f"RMS: {self.velocity_amplitude:.6f}{db_str}{duration_str}{filtered_str}"

    def is_valid_for_mapping(self) -> bool:
        """Kontroluje, zda je sample validní pro mapování."""
        return (self.analyzed and
                not self.is_filtered and
                self.detected_midi is not None)


class AnalysisProgress:
    """Model pro sledování progress analýzy."""

    def __init__(self, total_samples: int = 0):
        self.total_samples = total_samples
        self.completed_samples = 0
        self.current_sample = ""
        self.pitch_detections = 0
        self.amplitude_detections = 0
        self.errors = []

    def update(self, sample_name: str):
        """Aktualizuje progress."""
        self.completed_samples += 1
        self.current_sample = sample_name

    def add_error(self, sample_name: str, error: str):
        """Přidá chybu."""
        self.errors.append(f"{sample_name}: {error}")

    def get_status_message(self) -> str:
        """Vrátí statusovou zprávu."""
        error_str = f", {len(self.errors)} chyb" if self.errors else ""
        return f"Analýza dokončena: {self.completed_samples}/{self.total_samples} samples{error_str}"