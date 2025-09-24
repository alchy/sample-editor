"""
drag_drop_components.py - Refaktorované komponenty s dedikovaným drag tlačítkem - OPRAVENÉ IMPORTY
"""

from typing import List, Optional, Dict, Tuple, TYPE_CHECKING
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QPushButton, QScrollArea,
                               QGridLayout, QWidget, QAbstractItemView, QFrame, QApplication,
                               QMessageBox)
from PySide6.QtCore import Qt, Signal, QMimeData, QTimer  # OPRAVA: QTimer patří do QtCore
from PySide6.QtGui import QDrag, QPainter, QColor, QPixmap, QKeyEvent, QMouseEvent

from models import SampleMetadata
from midi_utils import MidiUtils
from inline_midi_editor import SampleListItem, InlineMidiEditor
import logging

logger = logging.getLogger(__name__)

# Avoid circular import
if TYPE_CHECKING:
    from main import MainWindow

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


class DragDropMatrixCell(QPushButton):
    """Buňka v mapovací matici s podporou drag & drop - zachovává původní funkcionalitu."""

    sample_dropped = Signal(object, int, int)  # sample, midi_note, velocity
    sample_removed = Signal(object, int, int)  # sample, midi_note, velocity
    sample_clicked = Signal(object)  # sample
    sample_play_requested = Signal(object)  # sample
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity

    def __init__(self, midi_note: int, velocity: int):
        super().__init__()
        self.midi_note = midi_note
        self.velocity = velocity
        self.sample: Optional[SampleMetadata] = None

        self.setAcceptDrops(True)
        self.setFixedSize(120, 30)
        self.setToolTip(f"MIDI {midi_note}, Velocity {velocity}\nLevý klik: přehrát/odstranit")

        # Přidáno pro handling kliků
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._update_style()

    def mousePressEvent(self, event: QMouseEvent):
        """Obsluha kliků na buňku - levý = přehrát, pravý = odstranit."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.sample:
                # Levý klik - pouze přehrát sample (bez dialogu)
                self.sample_play_requested.emit(self.sample)
                self.sample_clicked.emit(self.sample)
                logger.debug(f"Playing sample {self.sample.filename} from matrix cell")

            event.accept()

        elif event.button() == Qt.MouseButton.RightButton:
            if self.sample:
                # Pravý klik - odstranit sample bez notifikace
                removed_sample = self.sample
                self.sample.mapped = False
                self.sample = None
                self._update_style()
                self.sample_removed.emit(removed_sample, self.midi_note, self.velocity)
                logger.info(f"Removed {removed_sample.filename} from MIDI {self.midi_note}, V{self.velocity} (right-click)")
            event.accept()
        else:
            super().mousePressEvent(event)

    def _update_style(self):
        """Aktualizuje styl buňky."""
        if self.sample:
            self.setText(self.sample.filename[:15] + "..." if len(self.sample.filename) > 15 else self.sample.filename)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #90ee90; 
                    border: 1px solid #ccc;
                    text-align: left;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #7dd87d;
                }
            """)
        else:
            self.setText("")
            self.setStyleSheet("""
                QPushButton {
                    background-color: white; 
                    border: 1px solid #ccc;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)

    def dragEnterEvent(self, event):
        """Obsluha vstupu drag operace - přijímá pouze z drag tlačítek."""
        if (event.mimeData().hasFormat("application/x-sample-metadata") or
            event.mimeData().hasFormat("application/x-matrix-sample")):

            if event.mimeData().hasFormat("application/x-matrix-sample"):
                data = event.mimeData().data("application/x-matrix-sample").data().decode()
                parts = data.split("|")
                if len(parts) >= 3:
                    _, old_midi, old_velocity = parts[:3]
                    if int(old_midi) == self.midi_note and int(old_velocity) == self.velocity:
                        event.ignore()
                        return

            event.acceptProposedAction()
            highlight_color = "#fff3cd" if self.sample else "#e3f2fd"
            border_color = "#ffc107" if self.sample else "#2196F3"
            self.setStyleSheet(self.styleSheet() + f"""
                QPushButton {{
                    background-color: {highlight_color} !important;
                    border: 2px solid {border_color} !important;
                }}
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Obsluha opuštění drag operace."""
        self._update_style()

    def dropEvent(self, event):
        """Obsluha drop operace - nyní z drag tlačítek."""
        if event.mimeData().hasFormat("application/x-sample-metadata"):
            self._handle_list_drop(event)
        elif event.mimeData().hasFormat("application/x-matrix-sample"):
            self._handle_matrix_drop(event)
        else:
            event.ignore()

        self._update_style()

    def _handle_list_drop(self, event):
        """Obsluha drop z drag tlačítka."""
        sample_id_str = event.mimeData().data("application/x-sample-metadata").data().decode()

        try:
            sample_id = int(sample_id_str)
        except ValueError:
            event.ignore()
            return

        sample = self._find_sample_by_id(sample_id)
        if not sample:
            event.ignore()
            return

        if sample.is_filtered:
            QMessageBox.warning(self, "Filtrovaný sample",
                                f"Sample {sample.filename} je filtrován (mimo amplitude rozsah).")
            event.ignore()
            return

        if self.sample:
            reply = QMessageBox.question(self, "Přepsat sample?",
                                         f"Buňka MIDI {self.midi_note}, Velocity {self.velocity} "
                                         f"už obsahuje {self.sample.filename}.\n"
                                         f"Chcete ji přepsat sample {sample.filename}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            self.sample.mapped = False

        self.sample = sample
        sample.mapped = True
        self._update_style()

        self.sample_dropped.emit(sample, self.midi_note, self.velocity)
        event.acceptProposedAction()

    def _handle_matrix_drop(self, event):
        """Obsluha drop z jiné pozice v matici."""
        data = event.mimeData().data("application/x-matrix-sample").data().decode()
        parts = data.split("|")

        if len(parts) < 3:
            event.ignore()
            return

        sample_id_str, old_midi_str, old_velocity_str = parts[:3]

        try:
            sample_id = int(sample_id_str)
            old_midi = int(old_midi_str)
            old_velocity = int(old_velocity_str)
        except ValueError:
            event.ignore()
            return

        if old_midi == self.midi_note and old_velocity == self.velocity:
            event.ignore()
            return

        sample = self._find_sample_by_id(sample_id)
        if not sample:
            event.ignore()
            return

        if self.sample:
            old_note = MidiUtils.midi_to_note_name(old_midi)
            new_note = MidiUtils.midi_to_note_name(self.midi_note)

            reply = QMessageBox.question(self, "Přepsat sample?",
                                         f"Pozice {new_note} (MIDI {self.midi_note}, V{self.velocity}) "
                                         f"už obsahuje {self.sample.filename}.\n\n"
                                         f"Chcete přesunout {sample.filename} "
                                         f"z {old_note} (MIDI {old_midi}, V{old_velocity}) "
                                         f"a přepsat současný sample?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            self.sample.mapped = False

        # Najdi a vyčisti starou pozici
        matrix_widget = self._find_matrix_widget()
        if matrix_widget:
            old_key = (old_midi, old_velocity)
            if hasattr(matrix_widget, 'matrix_cells') and old_key in matrix_widget.matrix_cells:
                old_cell = matrix_widget.matrix_cells[old_key]
                old_cell.sample = None
                old_cell._update_style()

                if hasattr(matrix_widget, 'mapping') and old_key in matrix_widget.mapping:
                    del matrix_widget.mapping[old_key]

        self.sample = sample
        self._update_style()

        if matrix_widget:
            if hasattr(matrix_widget, 'mapping'):
                matrix_widget.mapping[(self.midi_note, self.velocity)] = sample
            if hasattr(matrix_widget, '_update_stats'):
                matrix_widget._update_stats()

        self.sample_moved.emit(sample, old_midi, old_velocity, self.midi_note, self.velocity)
        event.acceptProposedAction()

    def _find_sample_by_id(self, sample_id: int) -> Optional[SampleMetadata]:
        """Najde sample podle ID v aplikační hierarchii."""
        current = self.parent()
        while current:
            if hasattr(current, 'samples'):
                for sample in current.samples:
                    if id(sample) == sample_id:
                        return sample
            current = current.parent()
        return None

    def _find_matrix_widget(self):
        """Najde matrix widget v hierarchii."""
        current = self.parent()
        while current:
            if hasattr(current, 'matrix_cells') and hasattr(current, 'mapping'):
                return current
            current = current.parent()
        return None

    def highlight_if_matches(self, sample: SampleMetadata):
        """Zvýrazní buňku pokud obsahuje sample."""
        if self.sample == sample:
            original_style = self.styleSheet()
            self.setStyleSheet(original_style + "background-color: #ffd700 !important;")
            QTimer.singleShot(1000, lambda: self.setStyleSheet(original_style))


class DragDropSampleList(QGroupBox):
    """Seznam samples s inline MIDI editorem a dedikovanými drag tlačítky."""

    sample_selected = Signal(object)  # SampleMetadata
    samples_loaded = Signal()  # Signál pro indikaci dokončení

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
            f"Filtrováno: {filtered_count} | Namapováno: {mapped_count} | Klávesy: MEZERNÍK/S/D/ESC/T"
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
        sample_item_widget.sample_selected.connect(self._on_sample_selected)
        sample_item_widget.sample_play_requested.connect(self._emit_play_request)
        sample_item_widget.midi_changed.connect(self._on_midi_changed)
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
            f"Filtrováno: {filtered_count} | Namapováno: {mapped_count} | Klávesy: MEZERNÍK/S/D/ESC/T | DRAG TLAČÍTKA AKTIVNÍ"
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
        """Handler pro změnu MIDI noty v inline editoru."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_on_midi_note_changed'):
                parent._on_midi_note_changed(sample, old_midi, new_midi)
                break
            parent = parent.parent()

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


class DragDropMappingMatrix(QGroupBox):
    """Mapovací matice - zachovává všechnu funkcionalitu včetně center-based auto-assign."""

    sample_mapped = Signal(object, int, int)  # sample, midi, velocity
    sample_unmapped = Signal(object, int, int)  # sample, midi, velocity
    sample_play_requested = Signal(object)  # sample
    midi_note_play_requested = Signal(int)  # midi_note
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity
    sample_selected_in_matrix = Signal(object)  # sample vybraný v matici

    def __init__(self):
        super().__init__("Mapovací matice: Celý piano rozsah A0-C8 (Levý klik = přehrát/odstranit)")
        self.mapping: Dict[Tuple[int, int], SampleMetadata] = {}
        self.matrix_cells: Dict[Tuple[int, int], DragDropMatrixCell] = {}

        # MIDI rozsah piano
        self.piano_min_midi = MidiUtils.PIANO_MIN_MIDI  # 21 (A0)
        self.piano_max_midi = MidiUtils.PIANO_MAX_MIDI  # 108 (C8)

        self.init_ui()

    def init_ui(self):
        """Inicializace mapovací matice s celým piano rozsahem."""
        layout = QVBoxLayout()

        # Info panel s celkovými statistikami
        self._create_info_panel(layout)

        # Scroll area pro celou matici
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setMinimumHeight(600)

        # Widget pro matici
        self.matrix_widget = QWidget()
        self._create_full_matrix()

        scroll_area.setWidget(self.matrix_widget)
        layout.addWidget(scroll_area)

        self.setLayout(layout)

    def _create_info_panel(self, layout):
        """Vytvoří info panel s celkovými statistikami."""
        info_layout = QHBoxLayout()

        range_info_label = QLabel(
            f"Celý piano rozsah: A0-C8 (MIDI {self.piano_min_midi}-{self.piano_max_midi}) | Levý klik = přehrát/odstranit")
        range_info_label.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(range_info_label)

        info_layout.addStretch()

        self.stats_label = QLabel("Namapováno: 0 samples")
        self.stats_label.setStyleSheet("color: #333; font-weight: bold;")
        info_layout.addWidget(self.stats_label)

        layout.addLayout(info_layout)

    def _create_full_matrix(self):
        """Vytvoří matici buněk pro celý piano rozsah."""
        # Vyčisti existující layout
        if self.matrix_widget.layout():
            while self.matrix_widget.layout().count():
                child = self.matrix_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        matrix_layout = QGridLayout()
        matrix_layout.setSpacing(2)

        # Header řádek
        matrix_layout.addWidget(self._create_header_label("MIDI"), 0, 0)
        matrix_layout.addWidget(self._create_header_label("Nota"), 0, 1)
        matrix_layout.addWidget(self._create_header_label("Play"), 0, 2)
        matrix_layout.addWidget(self._create_header_label("Reset"), 0, 3)
        matrix_layout.addWidget(self._create_header_label("Assign"), 0, 4)
        for vel in range(8):
            vel_label = self._create_header_label(f"V{vel}")
            matrix_layout.addWidget(vel_label, 0, vel + 5)

        # Vytvoř buňky pro celý piano rozsah - od nejvyšší noty (C8) k nejnižší (A0)
        self.matrix_cells.clear()

        # Seřazení od nejvyšší po nejnižší MIDI notu
        midi_notes = list(range(self.piano_min_midi, self.piano_max_midi + 1))
        midi_notes.reverse()  # C8 (108) na vrcholu, A0 (21) na spodku

        for i, midi_note in enumerate(midi_notes):
            row = i + 1

            # MIDI číslo
            midi_label = QLabel(str(midi_note))
            midi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            midi_label.setStyleSheet("background-color: #f0f0f0; border: none; font-size: 10px; padding: 2px;")
            matrix_layout.addWidget(midi_label, row, 0)

            # Nota jméno
            note_name = MidiUtils.midi_to_note_name(midi_note)
            note_label = QLabel(note_name)
            note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note_label.setStyleSheet(
                "background-color: #f5f5f5; padding: 3px; border-radius: 3px; font-weight: bold; font-size: 10px;")
            matrix_layout.addWidget(note_label, row, 1)

            # Play tlačítko pro MIDI tón
            play_button = self._create_play_midi_button(midi_note)
            matrix_layout.addWidget(play_button, row, 2)

            # Reset tlačítko pro notu
            reset_button = self._create_reset_note_button(midi_note)
            matrix_layout.addWidget(reset_button, row, 3)

            # Assign tlačítko pro notu
            assign_button = self._create_assign_note_button(midi_note)
            matrix_layout.addWidget(assign_button, row, 4)

            # Velocity buňky
            for velocity in range(8):
                cell = DragDropMatrixCell(midi_note, velocity)
                # Připoj všechny signály
                cell.sample_dropped.connect(self._on_sample_dropped)
                cell.sample_removed.connect(self._on_sample_removed)
                cell.sample_clicked.connect(self.sample_selected_in_matrix.emit)
                cell.sample_play_requested.connect(self.sample_play_requested.emit)
                cell.sample_moved.connect(self.sample_moved.emit)
                matrix_layout.addWidget(cell, row, velocity + 5)

                key = (midi_note, velocity)
                self.matrix_cells[key] = cell

        self.matrix_widget.setLayout(matrix_layout)

    def _create_header_label(self, text: str) -> QLabel:
        """Vytvoří header label."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-weight: bold; background-color: #e0e0e0; padding: 5px;")
        return label

    def _create_play_midi_button(self, midi_note: int) -> QPushButton:
        """Vytvoří play tlačítko pro MIDI tón."""
        button = QPushButton("♪")
        button.setMaximumWidth(20)
        button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        button.clicked.connect(lambda: self._play_midi_note(midi_note))
        button.setToolTip(f"Přehrát MIDI tón {midi_note}")
        return button

    def _create_reset_note_button(self, midi_note: int) -> QPushButton:
        """Vytvoří reset tlačítko pro notu."""
        button = QPushButton("⌫")
        button.setMaximumWidth(20)
        button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
        button.clicked.connect(lambda: self._reset_note(midi_note))
        button.setToolTip(f"Odstranit všechny samples pro MIDI {midi_note}")
        return button

    def _create_assign_note_button(self, midi_note: int) -> QPushButton:
        """Vytvoří assign tlačítko pro notu."""
        button = QPushButton("⚡")
        button.setMaximumWidth(20)
        button.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """)
        button.clicked.connect(lambda: self._auto_assign_note(midi_note))
        button.setToolTip(f"Auto-přiřadit samples pro MIDI {midi_note} podle RMS")
        return button

    def _play_midi_note(self, midi_note: int):
        """Přehraje MIDI notu pomocí správného signálu."""
        logger.debug(f"Playing MIDI note {midi_note}")
        self.midi_note_play_requested.emit(midi_note)

    def _reset_note(self, midi_note: int):
        """Odstraní všechny samples pro danou notu."""
        removed_count = 0
        for velocity in range(8):
            key = (midi_note, velocity)
            if key in self.matrix_cells and self.matrix_cells[key].sample:
                self.remove_sample(midi_note, velocity)
                removed_count += 1

        if removed_count > 0:
            note_name = MidiUtils.midi_to_note_name(midi_note)
            logger.info(f"Reset note {note_name} (MIDI {midi_note}): removed {removed_count} samples")

    def _auto_assign_note(self, midi_note: int):
        """Center-based auto-assign algoritmus."""
        matching_samples = self._find_samples_for_midi_note(midi_note)

        if not matching_samples:
            note_name = MidiUtils.midi_to_note_name(midi_note)
            logger.info(f"No samples found for auto-assign of {note_name} (MIDI {midi_note})")
            return

        available_samples = [s for s in matching_samples if not s.mapped and s.velocity_amplitude is not None]

        if not available_samples:
            logger.info(f"No unmapped samples with RMS data available for {MidiUtils.midi_to_note_name(midi_note)}")
            return

        rms_values = [s.velocity_amplitude for s in available_samples]
        min_rms = min(rms_values)
        max_rms = max(rms_values)

        assigned_count = 0

        if min_rms == max_rms:
            self._assign_sample_to_velocity(available_samples[0], midi_note, 0)
            assigned_count = 1
        else:
            range_size = max_rms - min_rms

            for velocity in range(8):
                part_start = min_rms + (velocity / 8.0) * range_size
                part_end = min_rms + ((velocity + 1) / 8.0) * range_size
                part_center = (part_start + part_end) / 2.0

                best_sample = None
                best_distance = float('inf')

                for sample in available_samples:
                    distance = abs(sample.velocity_amplitude - part_center)
                    if distance < best_distance:
                        best_sample = sample
                        best_distance = distance

                if best_sample:
                    self._assign_sample_to_velocity(best_sample, midi_note, velocity)
                    available_samples.remove(best_sample)
                    assigned_count += 1

        note_name = MidiUtils.midi_to_note_name(midi_note)
        logger.info(f"Auto-assigned {assigned_count} samples for {note_name} (MIDI {midi_note}) "
                    f"using center-based algorithm (RMS range: {min_rms:.6f} - {max_rms:.6f})")

    def _find_samples_for_midi_note(self, midi_note: int) -> List[SampleMetadata]:
        """Najde všechny samples s danou MIDI notou."""
        main_window = self._find_main_window()
        if not main_window or not hasattr(main_window, 'samples'):
            return []

        matching_samples = []
        for sample in main_window.samples:
            if (sample.detected_midi == midi_note and
                    not sample.is_filtered and
                    sample.velocity_amplitude is not None):
                matching_samples.append(sample)

        return matching_samples

    def _find_main_window(self):
        """Najde main window v hierarchii."""
        current = self.parent()
        while current:
            if hasattr(current, 'samples'):
                return current
            current = current.parent()
        return None

    def _assign_sample_to_velocity(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Přiřadí sample na konkrétní MIDI pozici."""
        key = (midi_note, velocity)
        if key in self.mapping:
            old_sample = self.mapping[key]
            old_sample.mapped = False
        self.add_sample(sample, midi_note, velocity)

    def clear_matrix(self):
        """Vyčistí celou mapovací matici."""
        for key in list(self.mapping.keys()):
            midi_note, velocity = key
            self.remove_sample(midi_note, velocity)

    def add_sample(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Přidá sample do matice."""
        key = (midi_note, velocity)
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            if cell.sample:
                cell.sample.mapped = False

            cell.sample = sample
            sample.mapped = True
            cell._update_style()
            self.mapping[key] = sample
            self._update_stats()

            self.sample_mapped.emit(sample, midi_note, velocity)

    def remove_sample(self, midi_note: int, velocity: int):
        """Odebere sample z matice."""
        key = (midi_note, velocity)
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            if cell.sample:
                sample = cell.sample
                sample.mapped = False
                cell.sample = None
                cell._update_style()
                if key in self.mapping:
                    del self.mapping[key]
                self._update_stats()
                self.sample_unmapped.emit(sample, midi_note, velocity)

    def _on_sample_dropped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro drop sample."""
        key = (midi_note, velocity)
        self.mapping[key] = sample
        self._update_stats()
        self.sample_mapped.emit(sample, midi_note, velocity)

    def _on_sample_removed(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro odebrání sample."""
        key = (midi_note, velocity)
        if key in self.mapping:
            del self.mapping[key]
            self._update_stats()
        self.sample_unmapped.emit(sample, midi_note, velocity)

    def _update_stats(self):
        """Aktualizuje statistiky."""
        self.stats_label.setText(f"Namapováno: {len(self.mapping)} samples")

    def get_mapped_samples(self) -> Dict[Tuple[int, int], SampleMetadata]:
        """Vrátí mapování."""
        return self.mapping

    def highlight_sample_in_matrix(self, sample: SampleMetadata):
        """Zvýrazní sample v matici."""
        for cell in self.matrix_cells.values():
            cell.highlight_if_matches(sample)

    def find_cell_by_sample(self, sample: SampleMetadata) -> Optional[DragDropMatrixCell]:
        """Najde buňku podle sample."""
        for cell in self.matrix_cells.values():
            if cell.sample == sample:
                return cell
        return None