"""
drag_drop_sample_list.py - Seznam samples s inline MIDI editorem a propojením na session cache
"""

from typing import List, Optional
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QKeyEvent

from models import SampleMetadata
from inline_midi_editor import SampleListItem
import logging

logger = logging.getLogger(__name__)


class SimplifiedListWidget(QListWidget):
    """Zjednodušený seznam samples BEZ drag & drop - pouze keyboard shortcuts."""

    play_requested = Signal(object)  # SampleMetadata
    compare_requested = Signal(object)  # SampleMetadata
    simultaneous_requested = Signal(object)  # SampleMetadata

    def __init__(self):
        super().__init__()

        # VYPNUTO drag & drop - nový přístup s drag tlačítky
        self.setDragEnabled(False)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # Pro lepší keyboard handling
        self.current_selected_sample = None

    def keyPressEvent(self, event: QKeyEvent):
        """Obsluha klávesových zkratek - pouze audio funkce."""
        current_item = self.currentItem()

        # Klávesa T - sortování podle MIDI a RMS
        if event.key() == Qt.Key.Key_T:
            self._sort_by_midi_rms()
            event.accept()
            return

        if not current_item:
            super().keyPressEvent(event)
            return

        # Získej sample z custom item
        sample = self._get_sample_from_item(current_item)
        if not sample:
            super().keyPressEvent(event)
            return

        # Audio signály
        if event.key() == Qt.Key.Key_Space:
            logger.debug(f"Space pressed - playing {sample.filename}")
            self.play_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key.Key_S:
            logger.debug(f"S pressed - compare playing {sample.filename}")
            self.compare_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key.Key_D:
            logger.debug(f"D pressed - simultaneous playing {sample.filename}")
            self.simultaneous_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Escape:
            # ESC - stop přehrávání
            self._emit_stop_audio()
            event.accept()
            return

        super().keyPressEvent(event)

    def _get_sample_from_item(self, item: QListWidgetItem) -> Optional[SampleMetadata]:
        """Získá sample z QListWidgetItem."""
        widget = self.itemWidget(item)
        if widget and hasattr(widget, 'sample'):
            return widget.sample
        return item.data(Qt.ItemDataRole.UserRole)

    def _emit_stop_audio(self):
        """Emit stop audio signal through parent hierarchy."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'audio_player'):
                parent.audio_player.stop_playback()
                return
            if hasattr(parent, 'safe_stop_audio'):
                parent.safe_stop_audio()
                return
            parent = parent.parent()

    def _sort_by_midi_rms(self):
        """Sortuje samples podle MIDI noty a RMS."""
        # Získej všechny samples z items
        samples = []
        for i in range(self.count()):
            item = self.item(i)
            sample = self._get_sample_from_item(item)
            if sample:
                samples.append(sample)

        if not samples:
            return

        # Sortovací funkce
        def sort_key(sample):
            midi = sample.detected_midi if sample.detected_midi is not None else -1
            amplitude = sample.velocity_amplitude if sample.velocity_amplitude is not None else -1
            return (-midi, -amplitude)

        # Seřaď samples
        sorted_samples = sorted(samples, key=sort_key)

        # Získej parent pro refresh
        parent_sample_list = self._find_parent_sample_list()
        if parent_sample_list:
            parent_sample_list._rebuild_list_with_samples(sorted_samples)

    def _find_parent_sample_list(self):
        """Najde parent DragDropSampleList widget."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_rebuild_list_with_samples'):
                return parent
            parent = parent.parent()
        return None


class DragDropSampleList(QGroupBox):
    """Seznam samples s inline MIDI editorem a dedikovanými drag tlačítky - OPRAVENÁ VERZE."""

    sample_selected = Signal(object)  # SampleMetadata
    samples_loaded = Signal()  # Signál pro indikaci dokončení
    midi_changed = Signal(object, int, int)  # sample, old_midi, new_midi - NOVÝ SIGNÁL

    def __init__(self):
        super().__init__("Seznam samples s inline MIDI editory a drag tlačítky")
        self.samples: List[SampleMetadata] = []
        self.sample_items: List[SampleListItem] = []
        self.current_selected_sample: Optional[SampleMetadata] = None
        self.init_ui()

    def init_ui(self):
        """Inicializace seznamu samples."""
        layout = QVBoxLayout()

        # Info label
        self.info_label = QLabel("Žádné samples načteny")
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)

        # Použij SimplifiedListWidget - BEZ tradičního drag & drop
        self.sample_list = SimplifiedListWidget()
        self.sample_list.setAlternatingRowColors(True)
        self.sample_list.setStyleSheet("""
            QListWidget {
                alternate-background-color: #f8f8f8;
                border: 2px solid #2196F3;
                border-radius: 5px;
            }
            QListWidget:focus {
                border: 3px solid #1976D2;
                background-color: #f3f8ff;
            }
        """)
        layout.addWidget(self.sample_list)

        self.setLayout(layout)

    def update_samples(self, samples: List[SampleMetadata]):
        """Aktualizuje seznam samples s inline editory."""
        self.samples = samples
        self._rebuild_list_with_samples(samples)

    def _rebuild_list_with_samples(self, samples: List[SampleMetadata]):
        """Rebuild list s danými samples."""
        self.sample_list.clear()
        self.sample_items.clear()

        if not samples:
            self.info_label.setText("Žádné samples načteny")
            return

        # Statistiky
        total_count = len(samples)
        pitch_detected = sum(1 for s in samples if s.detected_midi is not None)
        rms_detected = sum(1 for s in samples if s.velocity_amplitude is not None)
        filtered_count = sum(1 for s in samples if s.is_filtered)
        mapped_count = sum(1 for s in samples if s.mapped)

        self.info_label.setText(
            f"Načteno {total_count} samples | Pitch: {pitch_detected} | RMS: {rms_detected} | "
            f"Filtrováno: {filtered_count} | Namapováno: {mapped_count} | Klávesy: MEZNÍK/S/D/ESC/T"
        )
        self.info_label.setStyleSheet("color: #666; font-size: 14px; font-weight: bold;")

        # Postupné vytváření items
        self._create_items_progressively(samples)

    def _create_items_progressively(self, samples: List[SampleMetadata]):
        """Vytváří items postupně."""
        total_samples = len(samples)
        self.info_label.setText(f"Vytváření UI pro {total_samples} samples...")

        self._items_to_create = samples.copy()
        self._creation_timer = QTimer()
        self._creation_timer.timeout.connect(self._create_next_item)
        self._creation_timer.start(10)

    def _create_next_item(self):
        """Vytvoří další item v sekvenci."""
        if not self._items_to_create:
            self._creation_timer.stop()
            self._finalize_samples_loading()
            return

        sample = self._items_to_create.pop(0)
        self._create_single_sample_item(sample)

        created_count = len(self.samples) - len(self._items_to_create)
        self.info_label.setText(f"Vytváření UI: {created_count}/{len(self.samples)} samples...")

    def _create_single_sample_item(self, sample: SampleMetadata):
        """Vytvoří jeden sample item."""
        sample_item_widget = SampleListItem(sample)

        # KLÍČOVÉ PROPOJENÍ: Připoj MIDI změny na parent signál
        sample_item_widget.sample_selected.connect(self._on_sample_selected)
        sample_item_widget.sample_play_requested.connect(self._emit_play_request)
        sample_item_widget.midi_changed.connect(self._on_midi_changed)  # NOVÉ!
        sample_item_widget.sample_disabled_changed.connect(self._on_sample_disabled_changed)

        list_item = QListWidgetItem()
        list_item.setData(Qt.ItemDataRole.UserRole, sample)
        list_item.setSizeHint(sample_item_widget.sizeHint())

        self.sample_list.addItem(list_item)
        self.sample_list.setItemWidget(list_item, sample_item_widget)
        self.sample_items.append(sample_item_widget)

    def _finalize_samples_loading(self):
        """Dokončí načítání samples."""
        self.sample_list.play_requested.connect(self._emit_play_request)
        self.sample_list.compare_requested.connect(self._emit_compare_request)
        self.sample_list.simultaneous_requested.connect(self._emit_simultaneous_request)

        QTimer.singleShot(200, self._set_focus_to_list)

        total_count = len(self.samples)
        pitch_detected = sum(1 for s in self.samples if s.detected_midi is not None)
        rms_detected = sum(1 for s in self.samples if s.velocity_amplitude is not None)
        filtered_count = sum(1 for s in self.samples if s.is_filtered)
        mapped_count = sum(1 for s in self.samples if s.mapped)

        self.info_label.setText(
            f"Načteno {total_count} samples | Pitch: {pitch_detected} | RMS: {rms_detected} | "
            f"Filtrováno: {filtered_count} | Namapováno: {mapped_count} | Klávesy: MEZNÍK/S/D/ESC/T | DRAG TLAČÍTKA AKTIVNÍ"
        )

        self.samples_loaded.emit()
        logger.info(f"Sample list UI vytvořeno: {len(self.samples)} samples, drag tlačítka aktivní")

    def _set_focus_to_list(self):
        """Nastav focus na sample list."""
        self.sample_list.setFocus(Qt.FocusReason.OtherFocusReason)

        if self.sample_list.count() > 0:
            self.sample_list.setCurrentRow(0)
            first_item = self.sample_list.item(0)
            if first_item:
                first_widget = self.sample_list.itemWidget(first_item)
                if first_widget and hasattr(first_widget, 'sample'):
                    self._on_sample_selected(first_widget.sample)

        logger.debug("Focus set to sample list with first item selected")

    def _on_sample_disabled_changed(self, sample: SampleMetadata, disabled: bool):
        """Handler pro změnu disable stavu sample."""
        logger.info(f"Sample {sample.filename} disabled: {disabled}")

    def _on_sample_selected(self, sample: SampleMetadata):
        """Handler pro výběr sample."""
        self.current_selected_sample = sample

        for item_widget in self.sample_items:
            item_widget.set_selected(item_widget.sample == sample)

        self.sample_selected.emit(sample)

    def _on_midi_changed(self, sample: SampleMetadata, old_midi: int, new_midi: int):
        """
        KLÍČOVÁ NOVÁ METODA: Handler pro změnu MIDI noty v inline editoru.
        Propaguje signál výše do main window pro session cache aktualizaci.
        """
        logger.info(f"MIDI changed in sample list: {sample.filename} {old_midi} -> {new_midi}")

        # Propaguj signál výše do parent hierarchy (main window)
        self.midi_changed.emit(sample, old_midi, new_midi)

    def _emit_play_request(self, sample: SampleMetadata):
        """Emit play request through parent hierarchy."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'safe_play_sample'):
                parent.safe_play_sample(sample)
                return
            parent = parent.parent()

    def _emit_compare_request(self, sample: SampleMetadata):
        """Emit compare request."""
        self._emit_play_request(sample)

    def _emit_simultaneous_request(self, sample: SampleMetadata):
        """Emit simultaneous request."""
        self._emit_play_request(sample)

    def refresh_display(self):
        """Obnoví zobrazení."""
        for item_widget in self.sample_items:
            item_widget.refresh()

    def highlight_sample_in_list(self, sample: SampleMetadata):
        """Zvýrazní sample v seznamu."""
        for i, item_widget in enumerate(self.sample_items):
            if item_widget.sample == sample:
                list_item = self.sample_list.item(i)
                self.sample_list.setCurrentItem(list_item)
                self.sample_list.scrollToItem(list_item, QAbstractItemView.ScrollHint.PositionAtCenter)

                item_widget.set_selected(True)
                QTimer.singleShot(1000, lambda: item_widget.set_selected(False))
                break