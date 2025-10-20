"""
auto_assign_thread.py - Worker thread for asynchronous auto-assign with progress bar
"""

import logging
from typing import List, Dict
from PySide6.QtCore import QThread, Signal

from models import SampleMetadata
from midi_utils import MidiUtils

logger = logging.getLogger(__name__)


class AutoAssignWorker(QThread):
    """Worker thread for asynchronous auto-assign operation with progress bar."""

    progress_updated = Signal(int, str)  # progress percentage, message
    assign_completed = Signal(dict)  # stats dictionary
    assign_failed = Signal(str)  # error message
    sample_assignment_requested = Signal(object, int, int)  # sample, midi_note, velocity
    refresh_gui_requested = Signal()  # request GUI refresh after bulk operations

    def __init__(self, mapping_matrix, samples: List[SampleMetadata], piano_min: int, piano_max: int):
        super().__init__()
        self.mapping_matrix = mapping_matrix
        self.samples = samples
        self.piano_min = piano_min
        self.piano_max = piano_max
        self._is_cancelled = False

    def run(self):
        """Execute asynchronous auto-assign."""
        try:
            logger.info(f"Starting auto-assign thread for MIDI range {self.piano_min}-{self.piano_max}")

            stats = {
                'total_notes': 0,
                'assigned_notes': 0,
                'total_samples': 0
            }

            # Create list of MIDI notes from highest to lowest (C8 -> A0)
            midi_notes = list(range(self.piano_min, self.piano_max + 1))
            midi_notes.reverse()  # Reverse order: 108, 107, 106, ..., 22, 21
            total_notes = len(midi_notes)

            # Process all MIDI notes from highest to lowest
            for idx, midi_note in enumerate(midi_notes):
                if self._is_cancelled:
                    logger.info("Auto-assign cancelled by user")
                    return

                stats['total_notes'] += 1

                # Update progress every 5 notes (or at milestones) for smooth visual feedback
                if (idx + 1) % 5 == 0 or (idx + 1) == total_notes or idx == 0:
                    progress = int(((idx + 1) / total_notes) * 100)
                    note_name = MidiUtils.midi_to_note_name(midi_note)
                    self.progress_updated.emit(
                        progress,
                        f"Auto-assigning: {note_name} (MIDI {midi_note}) - {idx+1}/{total_notes} notes"
                    )

                # Count samples before assign
                before_count = sum(1 for key in self.mapping_matrix.mapping.keys() if key[0] == midi_note)

                # Perform auto-assign for this note
                self._auto_assign_note_threaded(midi_note)

                # Count samples after assign
                after_count = sum(1 for key in self.mapping_matrix.mapping.keys() if key[0] == midi_note)

                # If something was assigned, count it
                if after_count > before_count:
                    stats['assigned_notes'] += 1
                    stats['total_samples'] += (after_count - before_count)

            # Refresh GUI once at the end
            logger.info("Refreshing GUI after bulk auto-assign...")
            self.refresh_gui_requested.emit()

            # Give GUI time to refresh
            import time
            time.sleep(0.1)

            # Completion
            logger.info(f"Auto-assign completed: {stats['assigned_notes']} notes, {stats['total_samples']} samples")
            self.assign_completed.emit(stats)

        except Exception as e:
            logger.error(f"Auto-assign thread failed: {e}", exc_info=True)
            self.assign_failed.emit(f"Error during auto-assign: {e}")

    def _auto_assign_note_threaded(self, midi_note: int):
        """
        Thread-safe version of auto-assign for a single note.
        This mirrors the logic from DragDropMappingMatrix._auto_assign_note()
        """
        matching_samples = self._find_samples_for_midi_note(midi_note)

        if not matching_samples:
            note_name = MidiUtils.midi_to_note_name(midi_note)
            logger.debug(f"No samples found for auto-assign of {note_name} (MIDI {midi_note})")
            return

        available_samples = [s for s in matching_samples if not s.mapped and s.velocity_amplitude is not None]

        if not available_samples:
            logger.debug(f"No unmapped samples with RMS data available for {MidiUtils.midi_to_note_name(midi_note)}")
            return

        rms_values = [s.velocity_amplitude for s in available_samples]
        min_rms = min(rms_values)
        max_rms = max(rms_values)

        assigned_count = 0

        if min_rms == max_rms:
            self._assign_sample_to_velocity(available_samples[0], midi_note, 0)
            assigned_count = 1
        else:
            # Sort samples by velocity_amplitude (ascending: quietest to loudest)
            sorted_samples = sorted(available_samples, key=lambda s: s.velocity_amplitude)
            velocity_layers = self.mapping_matrix.velocity_layers
            num_samples = len(sorted_samples)

            # Distribute samples across layers ensuring each sample is used only once
            # If we have fewer samples than layers, spread them proportionally with gaps
            if num_samples >= velocity_layers:
                # More samples than layers - select subset using proportional indexing
                for velocity in range(velocity_layers):
                    sample_idx = int((velocity + 0.5) * num_samples / velocity_layers)
                    sample_idx = min(sample_idx, num_samples - 1)
                    sample = sorted_samples[sample_idx]
                    self._assign_sample_to_velocity(sample, midi_note, velocity)
                    assigned_count += 1
            else:
                # Fewer samples than layers - assign each sample to proportional layer
                # This leaves gaps where no sample is available
                for sample_idx, sample in enumerate(sorted_samples):
                    # Calculate which velocity layer this sample should go to
                    # Using (sample_idx + 0.5) to center the sample in its range
                    velocity_layer = int((sample_idx + 0.5) * velocity_layers / num_samples)
                    velocity_layer = min(velocity_layer, velocity_layers - 1)

                    self._assign_sample_to_velocity(sample, midi_note, velocity_layer)
                    assigned_count += 1

        note_name = MidiUtils.midi_to_note_name(midi_note)
        logger.debug(f"Auto-assigned {assigned_count} samples for {note_name} (MIDI {midi_note}) "
                    f"using monotonic distribution (RMS range: {min_rms:.6f} - {max_rms:.6f})")

    def _find_samples_for_midi_note(self, midi_note: int) -> List[SampleMetadata]:
        """Find all samples with given MIDI note (excluding disabled and filtered)."""
        matching_samples = []
        for sample in self.samples:
            # Check disabled flag (if exists)
            is_disabled = getattr(sample, 'disabled', False)

            if (sample.detected_midi == midi_note and
                    not sample.is_filtered and
                    not is_disabled and
                    sample.velocity_amplitude is not None):
                matching_samples.append(sample)

        return matching_samples

    def _assign_sample_to_velocity(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """
        Assign sample to specific MIDI position - thread-safe version.
        Emits signal to request assignment in GUI thread.
        """
        # Emit signal to add sample in GUI thread
        # The signal/slot mechanism handles thread-safety automatically
        self.sample_assignment_requested.emit(sample, midi_note, velocity)

    def cancel_assign(self):
        """Cancel ongoing auto-assign operation."""
        self._is_cancelled = True
        logger.info("Auto-assign cancellation requested")
        self.progress_updated.emit(0, "Cancelling auto-assign...")
