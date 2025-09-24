"""
core/config.py - Centralizované konfigurační nastavení pro Sampler Editor
"""

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Konfigurace pro audio processing."""

    # CREPE nastavení
    crepe_model_capacity: str = 'medium'  # 'tiny', 'small', 'medium', 'large', 'full'
    crepe_step_size: int = 10  # ms
    crepe_confidence_threshold: float = 0.3

    # Amplitude analysis
    velocity_duration_ms: float = 500.0  # RMS window pro velocity
    amplitude_percentile: float = 99.5
    amplitude_window_ms: float = 10.0

    # Audio player
    auto_stop_timeout_ms: int = 10000  # 10 sekund
    play_delay_ms: int = 100  # Delay před přehráváním

    # Podporované formáty
    supported_extensions: List[str] = None

    def __post_init__(self):
        if self.supported_extensions is None:
            self.supported_extensions = [
                '*.wav', '*.WAV',
                '*.flac', '*.FLAC',
                '*.aiff', '*.AIFF',
                '*.mp3', '*.MP3'
            ]


@dataclass
class ExportConfig:
    """Konfigurace pro export operace."""

    # Export formáty
    sample_rates: List[Tuple[int, str]] = None
    velocity_levels: int = 8  # 0-7

    # Piano rozsah
    piano_min_midi: int = 21  # A0
    piano_max_midi: int = 108  # C8

    # Export options
    cleanup_old_exports: bool = True
    verify_exported_files: bool = True
    max_filename_length: int = 100

    def __post_init__(self):
        if self.sample_rates is None:
            self.sample_rates = [
                (44100, 'f44'),
                (48000, 'f48')
            ]

    def get_export_pattern(self) -> str:
        """Vrátí pattern pro čištění starých exportů."""
        return "m*-vel*-f*.wav"


@dataclass
class UIConfig:
    """Konfigurace pro uživatelské rozhraní."""

    # Main window
    window_width: int = 1400
    window_height: int = 900
    window_title: str = "Sampler Editor - CREPE Pitch + Amplitude Detection + Sync"

    # Matrix zobrazení
    matrix_cell_width: int = 120
    matrix_cell_height: int = 30
    matrix_scroll_height: int = 600

    # Sample list
    sample_list_item_height: int = 60
    sample_list_alternating_colors: bool = True

    # Progress bars
    progress_update_interval_ms: int = 100

    # Colors
    color_filtered_sample: str = "#e0e0e0"
    color_mapped_sample: str = "#e8f5e8"
    color_normal_sample: str = "#ffffff"
    color_selected_highlight: str = "#ffeb3b"
    color_matrix_occupied: str = "#90ee90"
    color_matrix_empty: str = "#ffffff"

    # Keyboard shortcuts
    shortcuts: Dict[str, str] = None

    def __post_init__(self):
        if self.shortcuts is None:
            self.shortcuts = {
                'play_sample': 'Space',
                'stop_audio': 'Escape',
                'compare_play': 'S',
                'simultaneous_play': 'D',
                'sort_samples': 'T',
                'transpose_up_semitone': '+',
                'transpose_down_semitone': '-',
                'transpose_up_octave': 'Shift++',
                'transpose_down_octave': 'Shift+-'
            }


@dataclass
class AnalysisConfig:
    """Konfigurace pro audio analýzu."""

    # Parallel processing
    max_parallel_workers: int = 4
    enable_parallel_processing: bool = False  # Zatím vypnuto pro stabilitu

    # Memory management
    max_memory_mb: int = 512
    chunk_size: int = 1024

    # Error handling
    max_retries: int = 2
    retry_delay_ms: int = 1000

    # Progress reporting
    progress_report_interval: int = 1  # Každý N-tý sample

    # Validation
    min_audio_duration_ms: float = 100.0
    max_audio_duration_ms: float = 300000.0  # 5 minut
    max_file_size_mb: int = 100


@dataclass
class LoggingConfig:
    """Konfigurace pro logging."""

    # Log levels
    console_level: str = 'INFO'
    file_level: str = 'DEBUG'

    # Log formáty
    console_format: str = '%(asctime)s - %(levelname)s - %(message)s'
    file_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'

    # Log soubory
    log_file: str = 'sampler_editor.log'
    max_log_size_mb: int = 10
    backup_count: int = 5

    # Debug options
    enable_event_logging: bool = False
    enable_performance_logging: bool = False


class ApplicationConfig:
    """Hlavní konfigurační třída obsahující všechna nastavení."""

    def __init__(self):
        self.audio = AudioConfig()
        self.export = ExportConfig()
        self.ui = UIConfig()
        self.analysis = AnalysisConfig()
        self.logging = LoggingConfig()

        # Application metadata
        self.version = "0.8.0"
        self.app_name = "Sampler Editor"
        self.author = "Sampler Editor Team"

        logger.info(f"Configuration initialized for {self.app_name} v{self.version}")

    def get_audio_formats(self) -> List[str]:
        """Vrátí seznam podporovaných audio formátů."""
        return [ext.replace('*', '') for ext in self.audio.supported_extensions]

    def get_export_sample_rates(self) -> List[int]:
        """Vrátí seznam export sample rates."""
        return [rate for rate, _ in self.export.sample_rates]

    def get_velocity_range(self) -> Tuple[int, int]:
        """Vrátí rozsah velocity hodnot."""
        return (0, self.export.velocity_levels - 1)

    def get_piano_range(self) -> Tuple[int, int]:
        """Vrátí MIDI rozsah piano."""
        return (self.export.piano_min_midi, self.export.piano_max_midi)

    def validate_midi_note(self, midi_note: int) -> bool:
        """Validuje MIDI notu v piano rozsahu."""
        return self.export.piano_min_midi <= midi_note <= self.export.piano_max_midi

    def validate_velocity(self, velocity: int) -> bool:
        """Validuje velocity hodnotu."""
        return 0 <= velocity < self.export.velocity_levels

    def setup_logging(self):
        """Nastaví logging podle konfigurace."""
        import logging.handlers

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.logging.console_level))
        console_formatter = logging.Formatter(self.logging.console_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                self.logging.log_file,
                maxBytes=self.logging.max_log_size_mb * 1024 * 1024,
                backupCount=self.logging.backup_count
            )
            file_handler.setLevel(getattr(logging, self.logging.file_level))
            file_formatter = logging.Formatter(self.logging.file_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Převede konfiguraci na dictionary."""
        return {
            'audio': self.audio.__dict__,
            'export': self.export.__dict__,
            'ui': self.ui.__dict__,
            'analysis': self.analysis.__dict__,
            'logging': self.logging.__dict__,
            'version': self.version,
            'app_name': self.app_name,
            'author': self.author
        }

    def save_to_file(self, filepath: Path):
        """Uloží konfiguraci do souboru."""
        import json
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def load_from_file(self, filepath: Path):
        """Načte konfiguraci ze souboru."""
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Update configurations
            if 'audio' in data:
                for key, value in data['audio'].items():
                    if hasattr(self.audio, key):
                        setattr(self.audio, key, value)

            if 'export' in data:
                for key, value in data['export'].items():
                    if hasattr(self.export, key):
                        setattr(self.export, key, value)

            if 'ui' in data:
                for key, value in data['ui'].items():
                    if hasattr(self.ui, key):
                        setattr(self.ui, key, value)

            if 'analysis' in data:
                for key, value in data['analysis'].items():
                    if hasattr(self.analysis, key):
                        setattr(self.analysis, key, value)

            if 'logging' in data:
                for key, value in data['logging'].items():
                    if hasattr(self.logging, key):
                        setattr(self.logging, key, value)

            logger.info(f"Configuration loaded from {filepath}")

        except Exception as e:
            logger.warning(f"Failed to load configuration from {filepath}: {e}")
            logger.info("Using default configuration")


# Global instance
_app_config_instance = None


def get_config() -> ApplicationConfig:
    """Globální funkce pro získání konfigurace."""
    global _app_config_instance
    if _app_config_instance is None:
        _app_config_instance = ApplicationConfig()
    return _app_config_instance


def setup_application_logging():
    """Nastaví aplikační logging."""
    config = get_config()
    config.setup_logging()


# Convenience functions pro časté operace
def get_audio_config() -> AudioConfig:
    """Vrátí audio konfiguraci."""
    return get_config().audio


def get_export_config() -> ExportConfig:
    """Vrátí export konfiguraci."""
    return get_config().export


def get_ui_config() -> UIConfig:
    """Vrátí UI konfiguraci."""
    return get_config().ui


def get_analysis_config() -> AnalysisConfig:
    """Vrátí analysis konfiguraci."""
    return get_config().analysis


def get_logging_config() -> LoggingConfig:
    """Vrátí logging konfiguraci."""
    return get_config().logging