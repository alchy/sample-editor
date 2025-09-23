"""
models.py - DatovÃ© modely pro Sampler Editor s rozšířenou analýzou
"""

from pathlib import Path
from typing import Optional


class SampleMetadata:
    """Metadata pro audio sample s rozšířenou analýzou"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name

        # AnalÃ½za vÃ½sledky - Pitch
        self.detected_midi: Optional[int] = None
        self.detected_frequency: Optional[float] = None
        self.pitch_confidence: Optional[float] = None
        self.pitch_method: Optional[str] = None  # Nový: metoda detekce (crepe, librosa, fallback)

        # Analýza výsledky - Amplitude (nové)
        self.peak_amplitude: Optional[float] = None  # Číselná hodnota (ne 0-7)
        self.peak_amplitude_db: Optional[float] = None
        self.rms_amplitude: Optional[float] = None
        self.rms_amplitude_db: Optional[float] = None
        self.peak_position: Optional[int] = None  # Pozice peaku v samples
        self.peak_position_seconds: Optional[float] = None

        # Attack envelope analýza (nové)
        self.attack_peak: Optional[float] = None
        self.attack_time: Optional[float] = None
        self.attack_slope: Optional[float] = None

        # Velocity mapping (nové řešení)
        self.velocity_level: Optional[int] = None  # 0-7, vypočteno z amplitude mappingu
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
               f"Peak: {self.peak_amplitude:.6f} if self.peak_amplitude else 'None', " \
               f"Vel: {self.velocity_level}, Filtered: {self.is_filtered})"

    def __repr__(self):
        return self.__str__()

    def get_pitch_info(self) -> str:
        """Vrátí formátovanou informaci o pitch"""
        if not self.detected_midi:
            return "No pitch detected"

        from midi_utils import MidiUtils
        note_name = MidiUtils.midi_to_note_name(self.detected_midi)
        confidence_str = f" (conf: {self.pitch_confidence:.2f})" if self.pitch_confidence else ""
        method_str = f" [{self.pitch_method}]" if self.pitch_method else ""

        return f"{note_name} ({self.detected_frequency:.1f} Hz){confidence_str}{method_str}"

    def get_amplitude_info(self) -> str:
        """Vrátí formátovanou informaci o amplitude"""
        if self.peak_amplitude is None:
            return "No amplitude data"

        db_str = f" ({self.peak_amplitude_db:.1f} dB)" if self.peak_amplitude_db is not None else ""
        vel_str = f" → Vel{self.velocity_level}" if self.velocity_level is not None else ""
        filtered_str = " [FILTERED]" if self.is_filtered else ""

        return f"Peak: {self.peak_amplitude:.6f}{db_str}{vel_str}{filtered_str}"

    def is_valid_for_mapping(self) -> bool:
        """Kontroluje, zda je sample validní pro mapování"""
        return (self.analyzed and
                not self.is_filtered and
                self.detected_midi is not None and
                self.velocity_level is not None)

    def reset_velocity_mapping(self):
        """Resetuje velocity mapping (při změně filtru)"""
        self.velocity_level = None
        self.is_filtered = False


class AnalysisProgress:
    """Model pro sledování progress analýzy"""

    def __init__(self, total_samples: int = 0):
        self.total_samples = total_samples
        self.completed_samples = 0
        self.current_sample = ""
        self.pitch_detections = 0
        self.amplitude_detections = 0
        self.errors = []

    def update(self, sample_name: str):
        """Aktualizuje progress"""
        self.completed_samples += 1
        self.current_sample = sample_name

    def add_error(self, sample_name: str, error: str):
        """Přidá chybu"""
        self.errors.append(f"{sample_name}: {error}")

    def get_progress_percent(self) -> int:
        """Vrátí progress v procentech"""
        if self.total_samples == 0:
            return 0
        return int((self.completed_samples / self.total_samples) * 100)

    def get_status_message(self) -> str:
        """Vrátí status zprávu"""
        if self.completed_samples == 0:
            return "Preparing analysis..."
        elif self.completed_samples < self.total_samples:
            return f"Analyzing: {self.current_sample} ({self.completed_samples}/{self.total_samples})"
        else:
            error_str = f", {len(self.errors)} errors" if self.errors else ""
            return f"Analysis completed: {self.completed_samples} samples{error_str}"


class AmplitudeFilterSettings:
    """Model pro nastavení amplitude filtru"""

    def __init__(self):
        self.global_min: float = 0.0
        self.global_max: float = 1.0
        self.filter_min: float = 0.0
        self.filter_max: float = 1.0
        self.num_levels: int = 8  # 0-7 velocity levels
        self.total_samples: int = 0
        self.valid_samples: int = 0

        # Statistiky
        self.mean_amplitude: float = 0.0
        self.std_amplitude: float = 0.0
        self.percentile_5: float = 0.0
        self.percentile_95: float = 0.0

    def update_from_range_info(self, range_info: dict):
        """Aktualizuje nastavení z AmplitudeRangeManager"""
        self.global_min = range_info.get('min', 0.0)
        self.global_max = range_info.get('max', 1.0)
        self.total_samples = range_info.get('count', 0)
        self.mean_amplitude = range_info.get('mean', 0.0)
        self.std_amplitude = range_info.get('std', 0.0)
        self.percentile_5 = range_info.get('percentile_5', 0.0)
        self.percentile_95 = range_info.get('percentile_95', 1.0)

        # Výchozí filtr na celý rozsah
        if self.filter_min == 0.0 and self.filter_max == 1.0:
            self.filter_min = self.global_min
            self.filter_max = self.global_max

    def get_velocity_thresholds(self) -> list:
        """Vrátí thresholdy pro velocity mapování"""
        if self.filter_min >= self.filter_max:
            return [0.0] * self.num_levels

        import numpy as np
        return np.linspace(self.filter_min, self.filter_max, self.num_levels).tolist()

    def is_in_range(self, amplitude: float) -> bool:
        """Kontroluje, zda je amplitude v povoleném rozsahu"""
        return self.filter_min <= amplitude <= self.filter_max

    def get_velocity_level(self, amplitude: float) -> int:
        """Vrátí velocity level pro danou amplitude"""
        if not self.is_in_range(amplitude):
            return -1  # Filtrováno

        thresholds = self.get_velocity_thresholds()

        # Najdi odpovídající level
        for i, threshold in enumerate(thresholds[1:], 1):
            if amplitude <= threshold:
                return i - 1

        return self.num_levels - 1  # Maximální level


class AmplitudeFilterSettings:
    """Model pro nastavení amplitude filtru"""

    def __init__(self):
        self.global_min: float = 0.0
        self.global_max: float = 1.0
        self.filter_min: float = 0.0
        self.filter_max: float = 1.0
        self.num_levels: int = 8  # 0-7 velocity levels
        self.total_samples: int = 0
        self.valid_samples: int = 0

        # Statistiky
        self.mean_amplitude: float = 0.0
        self.std_amplitude: float = 0.0
        self.percentile_5: float = 0.0
        self.percentile_95: float = 1.0

    def update_from_range_info(self, range_info: dict):
        """Aktualizuje nastavení z AmplitudeRangeManager"""
        self.global_min = range_info.get('min', 0.0)
        self.global_max = range_info.get('max', 1.0)
        self.total_samples = range_info.get('count', 0)
        self.mean_amplitude = range_info.get('mean', 0.0)
        self.std_amplitude = range_info.get('std', 0.0)
        self.percentile_5 = range_info.get('percentile_5', 0.0)
        self.percentile_95 = range_info.get('percentile_95', 1.0)

        # Výchozí filtr na celý rozsah
        if self.filter_min == 0.0 and self.filter_max == 1.0:
            self.filter_min = self.global_min
            self.filter_max = self.global_max

    def get_velocity_thresholds(self) -> list:
        """Vrátí thresholdy pro velocity mapování"""
        if self.filter_min >= self.filter_max:
            return [0.0] * self.num_levels

        import numpy as np
        return np.linspace(self.filter_min, self.filter_max, self.num_levels).tolist()

    def is_in_range(self, amplitude: float) -> bool:
        """Kontroluje, zda je amplitude v povoleném rozsahu"""
        return self.filter_min <= amplitude <= self.filter_max

    def get_velocity_level(self, amplitude: float) -> int:
        """Vrátí velocity level pro danou amplitude"""
        if not self.is_in_range(amplitude):
            return -1  # Filtrováno

        thresholds = self.get_velocity_thresholds()

        # Najdi odpovídající level
        for i, threshold in enumerate(thresholds[1:], 1):
            if amplitude <= threshold:
                return i - 1

        return self.num_levels - 1  # Maximální level