"""
drag_drop_core.py - Základní drag & drop komponenty s sample selection podporou - OPRAVENÁ VERZE
"""

from typing import List, Optional, TYPE_CHECKING
from PySide6.QtWidgets import (QListWidget, QListWidgetItem, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint, QTimer
from PySide6.QtGui import QDrag, QPainter, QColor, QPixmap, QKeyEvent, QMouseEvent

from models import SampleMetadata
from midi_utils import MidiUtils

# Avoid circular imports
if TYPE_CHECKING:
    from drag_drop_components import DragDropSampleList


class DragDropListWidget(QListWidget):
    """Seznam samples s podporou drag operací a klávesových zkratek."""

    play_requested = Signal(object)  # SampleMetadata
    compare_requested = Signal(object)  # SampleMetadata
    simultaneous_requested = Signal(object)  # SampleMetadata

    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event: QKeyEvent):
        """Obsluha klávesových zkratek."""
        current_item = self.currentItem()

        # Klávesa T - sortování podle MIDI a RMS
        if event.key() == Qt.Key.Key_T:
            self._sort_by_midi_rms()
            event.accept()
            return

        if not current_item:
            super().keyPressEvent(event)
            return

        sample = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Space:
            # Mezerník - přehraj vybraný sample
            self.play_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key.Key_S:
            # S klávesa - srovnávací přehrávání
            self.compare_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key.Key_D:
            # D klávesa - současné přehrávání
            self.simultaneous_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Escape:
            # ESC - stop přehrávání (emit through parent)
            parent_widget = self.parent()
            while parent_widget:
                if hasattr(parent_widget, 'audio_player'):
                    parent_widget.audio_player.stop_playback()
                    break
                parent_widget = parent_widget.parent()
            event.accept()
            return

        super().keyPressEvent(event)

    def _sort_by_midi_rms(self):
        """Sortuje samples podle MIDI noty (vysoká→nízká) a RMS (vysoká→nízká)."""
        # Získej všechny samples z items
        samples = []
        for i in range(self.count()):
            item = self.item(i)
            sample = item.data(Qt.ItemDataRole.UserRole)
            if sample:
                samples.append(sample)

        if not samples:
            return

        # Sortovací funkce
        def sort_key(sample):
            # MIDI nota: nejvyšší první (descending), pokud není detekována, dej na konec
            midi = sample.detected_midi if sample.detected_midi is not None else -1

            # RMS: nejvyšší první (descending), pokud není detekována, dej na konec
            amplitude = sample.velocity_amplitude if sample.velocity_amplitude is not None else -1

            # Sortování: MIDI sestupně, pak RMS sestupně
            return (-midi, -amplitude)

        # Seřaď samples
        sorted_samples = sorted(samples, key=sort_key)

        # Aktualizuj UI - OPRAVA: Získej parent pro vytvoření item text
        parent_sample_list = self._find_parent_sample_list()
        if not parent_sample_list:
            return

        self.clear()
        for sample in sorted_samples:
            item_text = parent_sample_list._create_new_format_item_text(sample)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, sample)

            # Nastavení barev
            if sample.is_filtered:
                item.setBackground(QColor("#e0e0e0"))
                item.setForeground(QColor("#666666"))
            elif sample.mapped:
                item.setBackground(QColor("#e8f5e8"))
            else:
                item.setBackground(QColor("#ffffff"))

            self.addItem(item)

    def _find_parent_sample_list(self):
        """Najde parent DragDropSampleList widget."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_create_new_format_item_text'):
                return parent
            parent = parent.parent()
        return None

    def startDrag(self, dropActions):
        """Spustí drag operaci."""
        item = self.currentItem()
        if not item:
            return

        sample = item.data(Qt.ItemDataRole.UserRole)
        if not sample or sample.is_filtered or sample.mapped:
            return

        mime_data = QMimeData()
        # OPRAVA: Použij jednoduchý identifikátor místo filename
        mime_data.setData("application/x-sample-metadata", str(id(sample)).encode())

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self._create_drag_pixmap(sample))
        drag.exec(Qt.DropAction.MoveAction)

    def _create_drag_pixmap(self, sample: SampleMetadata) -> QPixmap:
        """Vytvoří pixmap pro drag."""
        width, height = 200, 60
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(173, 216, 230, 180))  # Světle modrá

        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 0, 0))

        painter.drawText(5, 15, sample.filename)

        if sample.detected_midi:
            note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
            painter.drawText(5, 30, f"{note_name} (MIDI {sample.detected_midi})")

        if sample.velocity_amplitude:
            painter.drawText(5, 45, f"RMS: {sample.velocity_amplitude:.6f}")

        painter.end()
        return pixmap


class DragDropMatrixCell(QPushButton):
    """Buňka v mapovací matici s podporou drag & drop - OPRAVENÁ VERZE."""

    sample_dropped = Signal(object, int, int)  # sample, midi_note, velocity
    sample_removed = Signal(object, int, int)  # sample, midi_note, velocity
    sample_clicked = Signal(object)  # sample
    sample_play_requested = Signal(object)  # sample - přidán signál
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity

    def __init__(self, midi_note: int, velocity: int):
        super().__init__()
        self.midi_note = midi_note
        self.velocity = velocity
        self.sample: Optional[SampleMetadata] = None

        self.setAcceptDrops(True)
        self.setFixedSize(120, 30)
        self.setToolTip(f"MIDI {midi_note}, Velocity {velocity}")
        self.clicked.connect(self._on_clicked)

        self._update_style()

    def _update_style(self):
        """Aktualizuje styl buňky."""
        if self.sample:
            self.setText(self.sample.filename[:15] + "..." if len(self.sample.filename) > 15 else self.sample.filename)
            self.setStyleSheet("background-color: #90ee90; border: 1px solid #ccc;")
        else:
            self.setText("")
            self.setStyleSheet("background-color: white; border: 1px solid #ccc;")

    def _on_clicked(self):
        """Obsluha kliku na buňku."""
        if self.sample:
            self.sample_clicked.emit(self.sample)
            self.sample_play_requested.emit(self.sample)  # Emit přehrání při kliknutí

    def mousePressEvent(self, event: QMouseEvent):
        """Spustí drag pokud je buňka obsazená."""
        if event.button() == Qt.MouseButton.LeftButton and self.sample:
            mime_data = QMimeData()
            # OPRAVA: Použij sample ID místo filename pro robustnější identifikaci
            data = f"{id(self.sample)}|{self.midi_note}|{self.velocity}"
            mime_data.setData("application/x-matrix-sample", data.encode())

            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.setPixmap(self._create_drag_pixmap())
            drag.exec(Qt.DropAction.MoveAction)

    def _create_drag_pixmap(self) -> QPixmap:
        """Vytvoří pixmap pro drag z matice."""
        width, height = 260, 100
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 140, 0, 180))  # Oranžová

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))

        painter.drawText(5, 15, "PŘESUN V MATICI")
        filename_text = self.sample.filename[:25] + "..." if len(self.sample.filename) > 25 else self.sample.filename
        painter.drawText(5, 30, filename_text)

        current_note = MidiUtils.midi_to_note_name(self.midi_note)
        painter.drawText(5, 45, f"Z: {current_note} (MIDI {self.midi_note}, V{self.velocity})")

        if self.sample.detected_midi:
            sample_note = MidiUtils.midi_to_note_name(self.sample.detected_midi)
            painter.drawText(5, 60, f"Sample: {sample_note} (MIDI {self.sample.detected_midi})")

        if self.sample.velocity_amplitude:
            painter.drawText(5, 75, f"Velocity amplitude: {self.sample.velocity_amplitude:.6f}")

        painter.end()
        return pixmap

    def dragEnterEvent(self, event):
        """Obsluha vstupu drag operace."""
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
        """Obsluha drop operace."""
        if event.mimeData().hasFormat("application/x-sample-metadata"):
            self._handle_list_drop(event)
        elif event.mimeData().hasFormat("application/x-matrix-sample"):
            self._handle_matrix_drop(event)
        else:
            event.ignore()

        self._update_style()

    def _handle_list_drop(self, event):
        """Obsluha drop ze seznamu samples."""
        sample_id_str = event.mimeData().data("application/x-sample-metadata").data().decode()

        try:
            sample_id = int(sample_id_str)
        except ValueError:
            event.ignore()
            return

        # OPRAVA: Najdi sample pomocí aplikačního stavu
        sample = self._find_sample_by_id(sample_id)
        if not sample:
            event.ignore()
            return

        if sample.is_filtered:
            QMessageBox.warning(self, "Filtrovaný sample",
                                f"Sample {sample.filename} je filtrován (mimo amplitude rozsah).\n"
                                f"Nejprve upravte amplitude filter.")
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

        # OPRAVA: Najdi a vyčisti starou pozici pomocí parent hierarchy
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
        # Najdi main window v hierarchii
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