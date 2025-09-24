"""
core/events.py - Centrální Event Bus systém pro Sampler Editor
"""

from typing import Dict, List, Callable, Any, Optional
from PySide6.QtCore import QObject, Signal
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EventBus(QObject):
    """
    Centrální event bus pro komunikaci mezi komponentami aplikace.
    Implementuje Singleton pattern pro globální přístup.
    """

    # Sample management events
    sample_selected = Signal(object)  # SampleMetadata
    sample_deselected = Signal()
    samples_loaded = Signal(list, dict)  # List[SampleMetadata], range_info
    sample_analysis_started = Signal(object)  # Path (input_folder)
    sample_analysis_progress = Signal(int, str)  # percentage, message
    sample_analysis_completed = Signal(list, dict)  # samples, range_info

    # Mapping events
    sample_mapped = Signal(object, int, int)  # sample, midi_note, velocity
    sample_unmapped = Signal(object, int, int)  # sample, midi_note, velocity
    sample_moved_in_matrix = Signal(object, int, int, int, int)  # sample, old_midi, old_vel, new_midi, new_vel
    mapping_cleared = Signal()

    # Audio events
    audio_play_requested = Signal(object)  # SampleMetadata
    audio_stop_requested = Signal()
    midi_tone_play_requested = Signal(int)  # midi_note
    audio_status_changed = Signal(int)  # AudioPlayerStatus

    # MIDI editing events
    midi_note_changed = Signal(object, int, int)  # sample, old_midi, new_midi
    transpose_requested = Signal(object, int)  # sample, semitones

    # Export events
    export_requested = Signal()
    export_started = Signal()
    export_progress = Signal(int, str)  # percentage, message
    export_completed = Signal(dict)  # export_info
    export_failed = Signal(str)  # error_message

    # UI events
    folder_selected = Signal(str, object)  # folder_type ("input"/"output"), Path
    filter_applied = Signal(object)  # filter_settings
    ui_error_occurred = Signal(str, str)  # title, message
    ui_info_message = Signal(str, str)  # title, message

    # Application lifecycle events
    app_startup = Signal()
    app_shutdown = Signal()

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True
            self._event_log = []
            self._debug_mode = False
            logger.info("EventBus initialized")

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Získá singleton instanci EventBus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def enable_debug_logging(self, enabled: bool = True):
        """Zapne/vypne debug logging eventů."""
        self._debug_mode = enabled
        if enabled:
            logger.info("EventBus debug logging enabled")

    def emit_sample_selected(self, sample):
        """Emit sample selection event s debug loggingem."""
        if self._debug_mode:
            logger.debug(f"Event: sample_selected({sample.filename if sample else None})")
        self.sample_selected.emit(sample)

    def emit_sample_mapped(self, sample, midi_note: int, velocity: int):
        """Emit sample mapping event."""
        if self._debug_mode:
            logger.debug(f"Event: sample_mapped({sample.filename}, MIDI{midi_note}, V{velocity})")
        self.sample_mapped.emit(sample, midi_note, velocity)

    def emit_audio_play_requested(self, sample):
        """Emit audio play request."""
        if self._debug_mode:
            logger.debug(f"Event: audio_play_requested({sample.filename if sample else None})")
        self.audio_play_requested.emit(sample)

    def emit_midi_tone_play_requested(self, midi_note: int):
        """Emit MIDI tone play request."""
        if self._debug_mode:
            logger.debug(f"Event: midi_tone_play_requested(MIDI{midi_note})")
        self.midi_tone_play_requested.emit(midi_note)

    def emit_export_requested(self):
        """Emit export request."""
        if self._debug_mode:
            logger.debug("Event: export_requested")
        self.export_requested.emit()

    def emit_ui_error(self, title: str, message: str):
        """Emit UI error message."""
        logger.error(f"UI Error: {title} - {message}")
        self.ui_error_occurred.emit(title, message)

    def emit_ui_info(self, title: str, message: str):
        """Emit UI info message."""
        if self._debug_mode:
            logger.info(f"UI Info: {title} - {message}")
        self.ui_info_message.emit(title, message)

    def get_event_log(self) -> List[str]:
        """Vrátí log eventů pro debugging."""
        return self._event_log.copy()

    def clear_event_log(self):
        """Vyčistí log eventů."""
        self._event_log.clear()


class EventLogger:
    """Utility třída pro logování eventů."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.connect_all_signals()

    def connect_all_signals(self):
        """Připojí loggery ke všem signálům."""
        self.event_bus.sample_selected.connect(
            lambda sample: logger.debug(f"🎵 Sample selected: {sample.filename if sample else 'None'}")
        )

        self.event_bus.sample_mapped.connect(
            lambda sample, midi, vel: logger.debug(f"📍 Sample mapped: {sample.filename} -> MIDI{midi}, V{vel}")
        )

        self.event_bus.audio_play_requested.connect(
            lambda sample: logger.debug(f"🔊 Audio play: {sample.filename if sample else 'None'}")
        )

        self.event_bus.export_requested.connect(
            lambda: logger.debug("📤 Export requested")
        )


# Global instance
_event_bus_instance = None


def get_event_bus() -> EventBus:
    """Globální funkce pro získání EventBus instance."""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance


# Convenience functions for common events
def emit_sample_selected(sample):
    """Convenience funkce pro emission sample selection."""
    get_event_bus().emit_sample_selected(sample)


def emit_sample_mapped(sample, midi_note: int, velocity: int):
    """Convenience funkce pro emission sample mapping."""
    get_event_bus().emit_sample_mapped(sample, midi_note, velocity)


def emit_audio_play_requested(sample):
    """Convenience funkce pro emission audio play request."""
    get_event_bus().emit_audio_play_requested(sample)


def emit_export_requested():
    """Convenience funkce pro emission export request."""
    get_event_bus().emit_export_requested()


def emit_ui_error(title: str, message: str):
    """Convenience funkce pro emission UI error."""
    get_event_bus().emit_ui_error(title, message)


def emit_ui_info(title: str, message: str):
    """Convenience funkce pro emission UI info."""
    get_event_bus().emit_ui_info(title, message)