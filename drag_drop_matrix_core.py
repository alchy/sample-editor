"""
drag_drop_matrix_core.py - Jádro mapovací matice s drag&drop podporou
"""

from typing import Dict, Tuple, Optional
from PySide6.QtWidgets import QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal, QMimeData, QTimer
from PySide6.QtGui import QDrag, QPainter, QColor, QPixmap, QMouseEvent, QKeyEvent

from models import SampleMetadata
from midi_utils import MidiUtils
import logging

logger = logging.getLogger(__name__)


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
        self.setToolTip(f"MIDI {midi_note}, Velocity {velocity}\nLevý klik: přehrát | Pravý klik/Delete: odstranit")

        # Přidáno pro handling kliků
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Povolení focus pro klávesové události
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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
                self._remove_sample()
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """
        Obsluha klávesových událostí - Delete/Backspace odstraní sample z buňky.

        Args:
            event: Klávesová událost
        """
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.sample:
                self._remove_sample()
                event.accept()
            else:
                event.ignore()
        else:
            super().keyPressEvent(event)

    def _remove_sample(self):
        """Odstraní sample z buňky."""
        if not self.sample:
            return

        removed_sample = self.sample
        self.sample.mapped = False
        self.sample = None
        self._update_style()
        self.sample_removed.emit(removed_sample, self.midi_note, self.velocity)
        logger.info(f"Removed {removed_sample.filename} from MIDI {self.midi_note}, V{self.velocity}")

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