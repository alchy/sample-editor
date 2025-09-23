"""
drag_drop_core.py - Základní drag & drop komponenty pro Sampler Editor
"""

from typing import List, Optional
from PySide6.QtWidgets import (QListWidget, QListWidgetItem, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QDrag, QPainter, QColor, QPixmap, QKeyEvent, QMouseEvent

from models import SampleMetadata
from midi_utils import MidiUtils, VelocityUtils


class DragDropListWidget(QListWidget):
    """Seznam samples s podporou drag operací a klávesových zkratek"""

    play_requested = Signal(object)  # SampleMetadata
    compare_requested = Signal(object)  # SampleMetadata
    simultaneous_requested = Signal(object)  # SampleMetadata

    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setDragDropMode(QListWidget.DragOnly)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event: QKeyEvent):
        """Obsluha klávesových zkratek"""
        current_item = self.currentItem()
        if not current_item:
            super().keyPressEvent(event)
            return

        sample = current_item.data(Qt.UserRole)
        if not sample:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_Space:
            # Mezerník - přehraj vybraný sample
            self.play_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key_S:
            # S klávesa - srovnávací přehrávání
            self.compare_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key_D:
            # D klávesa - současné přehrávání
            self.simultaneous_requested.emit(sample)
            event.accept()
            return

        super().keyPressEvent(event)

    def startDrag(self, supportedActions):
        """Spustí drag operaci s rozšířeným pixmapem"""
        item = self.currentItem()
        if not item:
            return

        sample = item.data(Qt.UserRole)
        if not sample:
            return

        # Vytvoř drag objekt
        drag = QDrag(self)
        mimeData = QMimeData()

        # Ulož sample data do mime data
        mimeData.setText(f"sample:{sample.filename}")
        mimeData.setData("application/x-sample-metadata", sample.filename.encode())
        drag.setMimeData(mimeData)

        # Vytvoř rozšířený drag pixmap
        pixmap = self._create_enhanced_drag_pixmap(sample)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Spusť drag
        drag.exec_(Qt.CopyAction)

    def _create_enhanced_drag_pixmap(self, sample: SampleMetadata) -> QPixmap:
        """Vytvoří rozšířený pixmap pro drag operaci"""
        width, height = 280, 90
        pixmap = QPixmap(width, height)

        # Barva podle stavu filtrace
        if sample.is_filtered:
            pixmap.fill(QColor(150, 150, 150, 180))  # Šedá pro filtrované
        else:
            pixmap.fill(QColor(100, 150, 255, 180))  # Modrá pro validní

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))

        # Název souboru
        filename_text = sample.filename[:30] + "..." if len(sample.filename) > 30 else sample.filename
        painter.drawText(5, 15, filename_text)

        # Pitch info
        if sample.detected_midi:
            note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
            pitch_text = f"{note_name} (MIDI {sample.detected_midi})"
            if sample.pitch_method:
                pitch_text += f" [{sample.pitch_method}]"
            painter.drawText(5, 30, pitch_text)
        else:
            painter.drawText(5, 30, "No pitch detected")

        # Amplitude info
        if sample.peak_amplitude is not None:
            amp_text = f"Peak: {sample.peak_amplitude:.6f}"
            if sample.velocity_level is not None:
                amp_text += f" → V{sample.velocity_level}"
            painter.drawText(5, 45, amp_text)
        else:
            painter.drawText(5, 45, "No amplitude data")

        # Status info
        status_text = ""
        if sample.is_filtered:
            status_text = "FILTERED - outside range"
        elif sample.mapped:
            status_text = "MAPPED to matrix"
        else:
            status_text = "Ready for mapping"

        painter.drawText(5, 60, status_text)

        # Confidence info
        if sample.pitch_confidence:
            painter.drawText(5, 75, f"Confidence: {sample.pitch_confidence:.2f}")

        painter.end()
        return pixmap


class DragDropMatrixCell(QPushButton):
    """Buňka matice s podporou drop operací, přehrávání a drag mezi pozicemi"""

    sample_dropped = Signal(object, int, int)  # sample, midi, velocity
    sample_play_requested = Signal(object)  # sample
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity

    def __init__(self, midi_note: int, velocity: int):
        super().__init__()
        self.midi_note = midi_note
        self.velocity = velocity
        self.sample = None
        self.drag_start_position = None

        self.setAcceptDrops(True)
        self.setFixedSize(70, 35)
        self._update_style()

    def _update_style(self):
        """Aktualizuje styl buňky podle stavu"""
        if self.sample:
            # Obsazená buňka
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: 2px solid #45a049;
                    border-radius: 5px;
                    font-size: 9px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                    border: 2px solid #3d8b40;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            # Zkrácený název souboru
            display_name = self.sample.filename[:8] + "..." if len(self.sample.filename) > 8 else self.sample.filename
            self.setText(display_name)

            # Rozšířený tooltip s amplitude info
            tooltip_text = self._create_sample_tooltip()
            self.setToolTip(tooltip_text)
        else:
            # Prázdná buňka
            self.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border: 2px dashed #ccc;
                    border-radius: 5px;
                    color: #999;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background-color: #f0f8ff;
                    border: 2px dashed #4CAF50;
                }
            """)
            self.setText("Drop here")
            self.setToolTip("Přetáhněte sem sample ze seznamu nebo z jiné pozice v matici")

    def _create_sample_tooltip(self) -> str:
        """Vytvoří rozšířený tooltip pro sample"""
        tooltip_text = (f"Levý klik = přehrát | Pravý klik = info | Tažení = přesunout\n"
                       f"Soubor: {self.sample.filename}\n")

        if self.sample.detected_midi:
            note_name = MidiUtils.midi_to_note_name(self.sample.detected_midi)
            tooltip_text += f"Detekovaný pitch: {note_name} (MIDI {self.sample.detected_midi})\n"

        if self.sample.peak_amplitude:
            tooltip_text += f"Peak amplitude: {self.sample.peak_amplitude:.6f}\n"

        if self.sample.velocity_level is not None:
            tooltip_text += f"Velocity level: {self.sample.velocity_level}\n"

        return tooltip_text

    def mousePressEvent(self, event: QMouseEvent):
        """Obsluha stisknutí tlačítka myši"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

            if self.sample:
                # Pokud buňka obsahuje sample, můžeme ho přehrát
                self.sample_play_requested.emit(self.sample)

        elif event.button() == Qt.RightButton and self.sample:
            # Pravé tlačítko - zobraz rozšířené info o sample
            self._show_sample_info()

        super().mousePressEvent(event)

    def _show_sample_info(self):
        """Zobrazí rozšířené info o sample"""
        if not self.sample:
            return

        note_name = MidiUtils.midi_to_note_name(self.midi_note)
        velocity_desc = VelocityUtils.velocity_to_description(self.velocity)

        # Sestavení info textu
        info_text = f"Pozice: {note_name} (MIDI {self.midi_note})\n"
        info_text += f"Velocity: {velocity_desc} (V{self.velocity})\n"
        info_text += f"Sample: {self.sample.filename}\n\n"

        # Pitch info
        if self.sample.detected_midi:
            detected_note = MidiUtils.midi_to_note_name(self.sample.detected_midi)
            info_text += f"Detekovaný pitch: {detected_note} (MIDI {self.sample.detected_midi})\n"
            if self.sample.pitch_confidence:
                info_text += f"Pitch confidence: {self.sample.pitch_confidence:.2f}\n"
            if self.sample.pitch_method:
                info_text += f"Detekční metoda: {self.sample.pitch_method}\n"
        else:
            info_text += "Pitch: Nedetekován\n"

        # Amplitude info
        if self.sample.peak_amplitude is not None:
            info_text += f"\nPeak amplitude: {self.sample.peak_amplitude:.6f}\n"
            if self.sample.peak_amplitude_db is not None:
                info_text += f"Peak amplitude (dB): {self.sample.peak_amplitude_db:.1f}\n"
            if self.sample.velocity_level is not None:
                info_text += f"Velocity level: {self.sample.velocity_level}\n"
        else:
            info_text += "\nAmplitude: Nedetekována\n"

        # Status info
        if self.sample.is_filtered:
            info_text += "\nStatus: FILTROVÁNO (mimo amplitude rozsah)"
        elif self.sample.mapped:
            info_text += "\nStatus: Namapováno v matici"
        else:
            info_text += "\nStatus: Připraveno k mapování"

        QMessageBox.information(self, "Sample Info", info_text)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Obsluha pohybu myši - spustí drag pokud je sample v buňce"""
        if (event.buttons() == Qt.LeftButton and
            self.drag_start_position and
            self.sample and
            (event.pos() - self.drag_start_position).manhattanLength() >= 10):

            # Spustí drag operaci pro přesun sample v matici
            self._start_matrix_drag()

    def _start_matrix_drag(self):
        """Spustí drag operaci pro přesun sample v matici"""
        if not self.sample:
            return

        drag = QDrag(self)
        mimeData = QMimeData()

        # Označ jako matrix drag s pozičními informacemi
        mimeData.setText(f"matrix_sample:{self.sample.filename}")
        mimeData.setData("application/x-matrix-sample",
                        f"{self.sample.filename}|{self.midi_note}|{self.velocity}".encode())

        # Vytvoř drag pixmap
        pixmap = self._create_matrix_drag_pixmap(self.sample)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Spusť drag - používáme MoveAction pro přesun
        result = drag.exec_(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)

        # Reset drag start pozice
        self.drag_start_position = None

    def _create_matrix_drag_pixmap(self, sample: SampleMetadata) -> QPixmap:
        """Vytvoří pixmap pro drag operaci z matice"""
        width, height = 260, 100
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 140, 0, 180))  # Oranžová pro rozlišení od drag ze seznamu

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))

        # Označení jako přesun v matici
        painter.drawText(5, 15, "PŘESUN V MATICI")

        # Název souboru
        filename_text = sample.filename[:25] + "..." if len(sample.filename) > 25 else sample.filename
        painter.drawText(5, 30, filename_text)

        # Aktuální pozice
        current_note = MidiUtils.midi_to_note_name(self.midi_note)
        painter.drawText(5, 45, f"Z: {current_note} (MIDI {self.midi_note}, V{self.velocity})")

        # Sample info
        if sample.detected_midi:
            sample_note = MidiUtils.midi_to_note_name(sample.detected_midi)
            painter.drawText(5, 60, f"Sample: {sample_note} (MIDI {sample.detected_midi})")

        # Amplitude info
        if sample.peak_amplitude:
            painter.drawText(5, 75, f"Amplitude: {sample.peak_amplitude:.6f}")

        painter.end()
        return pixmap

    def dragEnterEvent(self, event):
        """Obsluha vstupu drag operace"""
        if (event.mimeData().hasFormat("application/x-sample-metadata") or
            event.mimeData().hasFormat("application/x-matrix-sample")):

            # Kontrola, jestli se nepokouším droppit na sebe sama
            if event.mimeData().hasFormat("application/x-matrix-sample"):
                data = event.mimeData().data("application/x-matrix-sample").data().decode()
                filename, old_midi, old_velocity = data.split("|")

                if int(old_midi) == self.midi_note and int(old_velocity) == self.velocity:
                    # Nepřijímáme drop na stejnou pozici
                    event.ignore()
                    return

            event.acceptProposedAction()

            # Zvýrazni buňku během drag over
            if self.sample:
                # Obsazená buňka - žlutá pro varování
                highlight_color = "#fff3cd"
                border_color = "#ffc107"
            else:
                # Prázdná buňka - modrá pro přijetí
                highlight_color = "#e3f2fd"
                border_color = "#2196F3"

            self.setStyleSheet(self.styleSheet() + f"""
                QPushButton {{
                    background-color: {highlight_color} !important;
                    border: 2px solid {border_color} !important;
                }}
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Obsluha opuštění drag operace"""
        self._update_style()

    def dropEvent(self, event):
        """Obsluha drop operace"""
        if event.mimeData().hasFormat("application/x-sample-metadata"):
            # Drop ze seznamu samples
            self._handle_list_drop(event)

        elif event.mimeData().hasFormat("application/x-matrix-sample"):
            # Drop z jiné pozice v matici
            self._handle_matrix_drop(event)

        else:
            event.ignore()

        self._update_style()

    def _handle_list_drop(self, event):
        """Obsluha drop ze seznamu samples"""
        filename = event.mimeData().data("application/x-sample-metadata").data().decode()

        # Najdi sample v parent widget
        main_window = WidgetFinder.find_main_window(self)
        if not main_window:
            event.ignore()
            return

        sample = WidgetFinder.find_sample_by_filename(main_window, filename)
        if not sample:
            event.ignore()
            return

        # Kontrola, zda sample není filtrován
        if sample.is_filtered:
            QMessageBox.warning(self, "Filtrovaný sample",
                              f"Sample {sample.filename} je filtrován (mimo amplitude rozsah).\n"
                              f"Nejprve upravte amplitude filter nebo přiřaďte velocity levels.")
            event.ignore()
            return

        if self.sample:
            # Buňka už je obsazená - zeptej se na přepsání
            reply = QMessageBox.question(self, "Přepsat sample?",
                                       f"Buňka MIDI {self.midi_note}, Velocity {self.velocity} "
                                       f"už obsahuje {self.sample.filename}.\n"
                                       f"Chcete ji přepsat sample {sample.filename}?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return

            # Označ starý sample jako nemapovaný
            self.sample.mapped = False

        # Namapuj nový sample
        self.sample = sample
        sample.mapped = True
        self._update_style()

        # Emit signal
        self.sample_dropped.emit(sample, self.midi_note, self.velocity)
        event.acceptProposedAction()

    def _handle_matrix_drop(self, event):
        """Obsluha drop z jiné pozice v matici"""
        data = event.mimeData().data("application/x-matrix-sample").data().decode()
        filename, old_midi_str, old_velocity_str = data.split("|")
        old_midi = int(old_midi_str)
        old_velocity = int(old_velocity_str)

        # Kontrola, že to není drop na stejnou pozici
        if old_midi == self.midi_note and old_velocity == self.velocity:
            event.ignore()
            return

        # Najdi sample v parent widget
        main_window = WidgetFinder.find_main_window(self)
        if not main_window:
            event.ignore()
            return

        sample = WidgetFinder.find_sample_by_filename(main_window, filename)
        if not sample:
            event.ignore()
            return

        # Kontrola obsazené buňky
        if self.sample:
            old_note = MidiUtils.midi_to_note_name(old_midi)
            new_note = MidiUtils.midi_to_note_name(self.midi_note)

            reply = QMessageBox.question(self, "Přepsat sample?",
                                       f"Pozice {new_note} (MIDI {self.midi_note}, V{self.velocity}) "
                                       f"už obsahuje {self.sample.filename}.\n\n"
                                       f"Chcete přesunout {sample.filename} "
                                       f"z {old_note} (MIDI {old_midi}, V{old_velocity}) "
                                       f"a přepsat současný sample?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return

            # Označ přepsaný sample jako nemapovaný
            self.sample.mapped = False

        # Najdi a vyčisti starou pozici
        matrix_widget = WidgetFinder.find_matrix_widget(self)
        if matrix_widget:
            old_key = (old_midi, old_velocity)
            if old_key in matrix_widget.matrix_cells:
                old_cell = matrix_widget.matrix_cells[old_key]
                old_cell.sample = None
                old_cell._update_style()

                # Odstraň z mapping
                if old_key in matrix_widget.mapping:
                    del matrix_widget.mapping[old_key]

        # Nastav novou pozici
        self.sample = sample
        self._update_style()

        # Aktualizuj mapping v matrix widget
        if matrix_widget:
            matrix_widget.mapping[(self.midi_note, self.velocity)] = sample
            matrix_widget._update_stats()

        # Emit signál pro přesun
        self.sample_moved.emit(sample, old_midi, old_velocity, self.midi_note, self.velocity)
        event.acceptProposedAction()


# Utility funkce pro nalezení parent widgetů
class WidgetFinder:
    """Utility třída pro nalezení parent widgetů"""

    @staticmethod
    def find_main_window(widget):
        """Najde hlavní okno aplikace"""
        current_widget = widget
        while current_widget.parent():
            current_widget = current_widget.parent()
            if hasattr(current_widget, 'samples'):
                return current_widget
        return None

    @staticmethod
    def find_matrix_widget(widget):
        """Najde matrix widget"""
        current_widget = widget
        while current_widget.parent():
            current_widget = current_widget.parent()
            if hasattr(current_widget, 'mapping') and hasattr(current_widget, 'matrix_cells'):
                return current_widget
        return None

    @staticmethod
    def find_sample_by_filename(main_window, filename: str) -> Optional[SampleMetadata]:
        """Najde sample podle filename v hlavním okně"""
        if not main_window or not hasattr(main_window, 'samples'):
            return None

        for sample in main_window.samples:
            if sample.filename == filename:
                return sample
        return None