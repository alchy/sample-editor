"""
core/state_manager.py - Centrální state management pro Sampler Editor
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
import logging

from models import SampleMetadata

logger = logging.getLogger(__name__)


@dataclass
class ApplicationState:
    """Centrální stav aplikace."""

    # Sample data
    samples: List[SampleMetadata] = field(default_factory=list)
    selected_sample: Optional[SampleMetadata] = None
    filtered_samples: List[SampleMetadata] = field(default_factory=list)

    # Mapping data
    mapping: Dict[Tuple[int, int], SampleMetadata] = field(default_factory=dict)

    # Folder paths
    input_folder: Optional[Path] = None
    output_folder: Optional[Path] = None

    # Analysis state
    analysis_in_progress: bool = False
    analysis_progress: int = 0
    analysis_message: str = ""
    amplitude_range_info: Dict[str, Any] = field(default_factory=dict)

    # Audio state
    audio_playing: bool = False
    current_playing_sample: Optional[SampleMetadata] = None

    # Export state
    export_in_progress: bool = False
    export_progress: int = 0
    last_export_info: Dict[str, Any] = field(default_factory=dict)

    # Filter state
    amplitude_filter_enabled: bool = False
    amplitude_filter_min: float = 0.0
    amplitude_filter_max: float = 1.0

    # UI state
    matrix_scroll_position: int = 0
    sample_list_selection: int = -1


class StateManager:
    """
    Centrální správce stavu aplikace.
    Poskytuje thread-safe přístup k aplikačnímu stavu.
    """

    def __init__(self):
        self._state = ApplicationState()
        self._state_history: List[ApplicationState] = []
        self._max_history = 10
        self._observers: List[Callable] = []
        logger.info("StateManager initialized")

    @property
    def state(self) -> ApplicationState:
        """Vrátí read-only přístup ke stavu."""
        return self._state

    # Sample management methods
    def set_samples(self, samples: List[SampleMetadata], range_info: Dict[str, Any] = None):
        """Nastaví seznam samples a amplitude range info."""
        self._save_state_to_history()
        self._state.samples = samples.copy()
        if range_info:
            self._state.amplitude_range_info = range_info.copy()
        self._apply_current_filter()
        self._notify_observers("samples_changed")
        logger.info(f"Set {len(samples)} samples")

    def get_samples(self) -> List[SampleMetadata]:
        """Vrátí všechny samples."""
        return self._state.samples.copy()

    def get_filtered_samples(self) -> List[SampleMetadata]:
        """Vrátí filtrované samples."""
        return self._state.filtered_samples.copy()

    def set_selected_sample(self, sample: Optional[SampleMetadata]):
        """Nastaví vybraný sample."""
        if self._state.selected_sample != sample:
            self._state.selected_sample = sample
            self._notify_observers("selection_changed")
            logger.debug(f"Selected sample: {sample.filename if sample else 'None'}")

    def get_selected_sample(self) -> Optional[SampleMetadata]:
        """Vrátí vybraný sample."""
        return self._state.selected_sample

    # Mapping management methods
    def add_sample_mapping(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Přidá sample do mapování."""
        self._save_state_to_history()

        key = (midi_note, velocity)

        # Odstraň starý mapping pokud existuje
        if key in self._state.mapping:
            old_sample = self._state.mapping[key]
            old_sample.mapped = False
            logger.debug(f"Removed old mapping: {old_sample.filename}")

        # Přidej nový mapping
        self._state.mapping[key] = sample
        sample.mapped = True

        self._notify_observers("mapping_changed")
        logger.info(f"Mapped {sample.filename} to MIDI {midi_note}, V{velocity}")

    def remove_sample_mapping(self, midi_note: int, velocity: int) -> Optional[SampleMetadata]:
        """Odebere sample z mapování."""
        key = (midi_note, velocity)

        if key in self._state.mapping:
            self._save_state_to_history()
            sample = self._state.mapping[key]
            sample.mapped = False
            del self._state.mapping[key]
            self._notify_observers("mapping_changed")
            logger.info(f"Unmapped {sample.filename} from MIDI {midi_note}, V{velocity}")
            return sample

        return None

    def move_sample_mapping(self, old_midi: int, old_velocity: int, new_midi: int, new_velocity: int) -> bool:
        """Přesune sample z jedné pozice na druhou."""
        old_key = (old_midi, old_velocity)
        new_key = (new_midi, new_velocity)

        if old_key not in self._state.mapping:
            return False

        self._save_state_to_history()

        sample = self._state.mapping[old_key]

        # Odstraň z původní pozice
        del self._state.mapping[old_key]

        # Pokud je nová pozice obsazená, odstraň starý sample
        if new_key in self._state.mapping:
            old_sample = self._state.mapping[new_key]
            old_sample.mapped = False

        # Přidej na novou pozici
        self._state.mapping[new_key] = sample

        self._notify_observers("mapping_changed")
        logger.info(
            f"Moved {sample.filename} from MIDI {old_midi}, V{old_velocity} to MIDI {new_midi}, V{new_velocity}")
        return True

    def get_mapping(self) -> Dict[Tuple[int, int], SampleMetadata]:
        """Vrátí kopii mapování."""
        return self._state.mapping.copy()

    def get_sample_at_position(self, midi_note: int, velocity: int) -> Optional[SampleMetadata]:
        """Vrátí sample na dané pozici."""
        key = (midi_note, velocity)
        return self._state.mapping.get(key)

    def clear_mapping(self):
        """Vyčistí celé mapování."""
        self._save_state_to_history()

        for sample in self._state.mapping.values():
            sample.mapped = False

        self._state.mapping.clear()
        self._notify_observers("mapping_changed")
        logger.info("Cleared all mappings")

    def get_mapping_stats(self) -> Dict[str, int]:
        """Vrátí statistiky mapování."""
        return {
            'total_mapped': len(self._state.mapping),
            'unique_samples': len(set(self._state.mapping.values())),
            'midi_range_min': min((k[0] for k in self._state.mapping.keys()), default=0),
            'midi_range_max': max((k[0] for k in self._state.mapping.keys()), default=0),
            'velocity_levels_used': len(set(k[1] for k in self._state.mapping.keys()))
        }

    # Folder management
    def set_input_folder(self, folder: Path):
        """Nastaví vstupní složku."""
        self._state.input_folder = folder
        self._notify_observers("input_folder_changed")
        logger.info(f"Input folder set: {folder}")

    def set_output_folder(self, folder: Path):
        """Nastaví výstupní složku."""
        self._state.output_folder = folder
        self._notify_observers("output_folder_changed")
        logger.info(f"Output folder set: {folder}")

    # Filter management
    def set_amplitude_filter(self, enabled: bool, min_val: float = 0.0, max_val: float = 1.0):
        """Nastaví amplitude filter."""
        self._state.amplitude_filter_enabled = enabled
        self._state.amplitude_filter_min = min_val
        self._state.amplitude_filter_max = max_val
        self._apply_current_filter()
        self._notify_observers("filter_changed")
        logger.info(f"Amplitude filter: {'enabled' if enabled else 'disabled'} ({min_val:.6f} - {max_val:.6f})")

    def _apply_current_filter(self):
        """Aplikuje současný filter na samples."""
        if not self._state.amplitude_filter_enabled:
            # Reset filter flags
            for sample in self._state.samples:
                sample.is_filtered = False
            self._state.filtered_samples = self._state.samples.copy()
        else:
            # Apply filter
            filtered = []
            for sample in self._state.samples:
                if (sample.velocity_amplitude is not None and
                        self._state.amplitude_filter_min <= sample.velocity_amplitude <= self._state.amplitude_filter_max):
                    sample.is_filtered = False
                    filtered.append(sample)
                else:
                    sample.is_filtered = True

            self._state.filtered_samples = filtered

        logger.debug(f"Filter applied: {len(self._state.filtered_samples)}/{len(self._state.samples)} samples pass")

    # Analysis state management
    def set_analysis_state(self, in_progress: bool, progress: int = 0, message: str = ""):
        """Nastaví stav analýzy."""
        self._state.analysis_in_progress = in_progress
        self._state.analysis_progress = progress
        self._state.analysis_message = message
        self._notify_observers("analysis_state_changed")

    # Audio state management
    def set_audio_state(self, playing: bool, sample: Optional[SampleMetadata] = None):
        """Nastaví stav audio přehrávání."""
        self._state.audio_playing = playing
        self._state.current_playing_sample = sample
        self._notify_observers("audio_state_changed")

    # Export state management
    def set_export_state(self, in_progress: bool, progress: int = 0, last_info: Dict[str, Any] = None):
        """Nastaví stav exportu."""
        self._state.export_in_progress = in_progress
        self._state.export_progress = progress
        if last_info:
            self._state.last_export_info = last_info.copy()
        self._notify_observers("export_state_changed")

    # Observer pattern
    def add_observer(self, callback: Callable):
        """Přidá observer pro změny stavu."""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable):
        """Odebere observer."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, change_type: str):
        """Upozorní všechny observers na změnu stavu."""
        for observer in self._observers:
            try:
                observer(change_type, self._state)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")

    # State history management
    def _save_state_to_history(self):
        """Uloží současný stav do historie."""
        # Create deep copy of current state
        import copy
        state_copy = copy.deepcopy(self._state)
        self._state_history.append(state_copy)

        # Limit history size
        if len(self._state_history) > self._max_history:
            self._state_history.pop(0)

    def undo_last_action(self) -> bool:
        """Vrátí poslední akci."""
        if not self._state_history:
            return False

        self._state = self._state_history.pop()
        self._notify_observers("state_restored")
        logger.info("State restored from history")
        return True

    def can_undo(self) -> bool:
        """Vrátí zda je možné udělat undo."""
        return len(self._state_history) > 0

    # Validation methods
    def validate_state(self) -> List[str]:
        """Validuje konzistenci stavu."""
        errors = []

        # Validate mapping consistency
        for key, sample in self._state.mapping.items():
            if not sample.mapped:
                errors.append(f"Sample {sample.filename} is in mapping but not marked as mapped")

        # Validate sample mapping flags
        mapped_samples = set(self._state.mapping.values())
        for sample in self._state.samples:
            if sample.mapped and sample not in mapped_samples:
                errors.append(f"Sample {sample.filename} marked as mapped but not in mapping")

        return errors

    # Utility methods
    def get_state_summary(self) -> Dict[str, Any]:
        """Vrátí shrnutí stavu pro debugging."""
        return {
            'samples_count': len(self._state.samples),
            'filtered_samples_count': len(self._state.filtered_samples),
            'mapped_samples_count': len(self._state.mapping),
            'selected_sample': self._state.selected_sample.filename if self._state.selected_sample else None,
            'input_folder': str(self._state.input_folder) if self._state.input_folder else None,
            'output_folder': str(self._state.output_folder) if self._state.output_folder else None,
            'analysis_in_progress': self._state.analysis_in_progress,
            'audio_playing': self._state.audio_playing,
            'export_in_progress': self._state.export_in_progress,
            'amplitude_filter_enabled': self._state.amplitude_filter_enabled,
            'history_size': len(self._state_history)
        }


# Global instance
_state_manager_instance = None


def get_state_manager() -> StateManager:
    """Globální funkce pro získání StateManager instance."""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance