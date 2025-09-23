"""
drag_drop_components.py - Komponenty s podporou drag & drop pro Sampler Editor
Kompletní verze s celým scrollovatelným piano rozsahem
"""

from typing import List, Optional
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QPushButton,
                               QScrollArea, QGridLayout, QFrame, QMessageBox, QWidget)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QDrag, QPainter, QColor, QPixmap, QKeyEvent, QFont, QMouseEvent

from models import SampleMetadata
from midi_utils import MidiUtils, VelocityUtils


class DragDropListWidget(QListWidget):
    """Seznam sampleů s podporou drag operací a klávesových zkratek"""

    play_requested = Signal(object)  # SampleMetadata - signál pro přehrávání
    compare_requested = Signal(object)  # SampleMetadata - signál pro srovnávací přehrávání (S klávesa)
    simultaneous_requested = Signal(object)  # SampleMetadata - signál pro současné přehrávání (D klávesa)

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
            # S klávesa - srovnávací přehrávání (sine tón + pauza + sample)
            self.compare_requested.emit(sample)
            event.accept()
            return

        elif event.key() == Qt.Key_D:
            # D klávesa - současné přehrávání (sine tón + sample současně)
            self.simultaneous_requested.emit(sample)
            event.accept()
            return

        # Předej ostatní klávesy rodičovské třídě
        super().keyPressEvent(event)

    def startDrag(self, supportedActions):
        """Spustí drag operaci s vlastním pixmapem"""
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

        # Vytvoř drag pixmap s informacemi o sample
        pixmap = self._create_drag_pixmap(sample)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Spusť drag
        drag.exec_(Qt.CopyAction)

    def _create_drag_pixmap(self, sample: SampleMetadata) -> QPixmap:
        """Vytvoří pixmap pro drag operaci"""
        width, height = 200, 60
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(100, 150, 255, 180))

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))

        # Název souboru
        filename_text = sample.filename[:25] + "..." if len(sample.filename) > 25 else sample.filename
        painter.drawText(5, 15, filename_text)

        # MIDI info
        note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
        painter.drawText(5, 30, f"{note_name} (MIDI {sample.detected_midi})")

        # Velocity info
        velocity_desc = VelocityUtils.velocity_to_description(sample.velocity_level)
        painter.drawText(5, 45, f"{velocity_desc} (V{sample.velocity_level})")

        painter.end()
        return pixmap


class DragDropMatrixCell(QPushButton):
    """Buňka matice s podporou drop operací, přehrávání a drag mezi pozicemi"""

    sample_dropped = Signal(object, int, int)  # sample, midi, velocity
    sample_play_requested = Signal(object)  # sample - signál pro přehrávání
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
            self.setToolTip(f"Levý klik = přehrát | Pravý klik = info | Tažení = přesunout\n{self.sample.filename}")
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

    def mousePressEvent(self, event: QMouseEvent):
        """Obsluha stisknutí tlačítka myši"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

            if self.sample:
                # Pokud buňka obsahuje sample, můžeme ho přehrát
                self.sample_play_requested.emit(self.sample)

        elif event.button() == Qt.RightButton and self.sample:
            # Pravé tlačítko - zobraz info o sample
            note_name = MidiUtils.midi_to_note_name(self.midi_note)
            velocity_desc = VelocityUtils.velocity_to_description(self.velocity)

            QMessageBox.information(self, "Sample Info",
                                  f"Pozice: {note_name} (MIDI {self.midi_note})\n"
                                  f"Velocity: {velocity_desc} (V{self.velocity})\n"
                                  f"Sample: {self.sample.filename}\n"
                                  f"Detekovaná nota: {MidiUtils.midi_to_note_name(self.sample.detected_midi)}\n"
                                  f"Confidence: {self.sample.pitch_confidence:.2f}")

        super().mousePressEvent(event)

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

        # Označíme jako matrix drag s pozičními informacemi
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
        width, height = 220, 80
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 140, 0, 180))  # Oranžová pro rozlišení od drag ze seznamu

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))

        # Označení jako přesun v matici
        painter.drawText(5, 15, "PŘESUN V MATICI")

        # Název souboru
        filename_text = sample.filename[:22] + "..." if len(sample.filename) > 22 else sample.filename
        painter.drawText(5, 30, filename_text)

        # Aktuální pozice
        current_note = MidiUtils.midi_to_note_name(self.midi_note)
        painter.drawText(5, 45, f"Z: {current_note} (MIDI {self.midi_note}, V{self.velocity})")

        # MIDI info samplu
        sample_note = MidiUtils.midi_to_note_name(sample.detected_midi)
        painter.drawText(5, 60, f"Sample: {sample_note} (MIDI {sample.detected_midi})")

        painter.end()
        return pixmap

    def dragEnterEvent(self, event):
        """Obsluha vstupu drag operace"""
        if (event.mimeData().hasFormat("application/x-sample-metadata") or
            event.mimeData().hasFormat("application/x-matrix-sample")):

            # Kontrola, jestli se nepokoušíme dropit na sebe sama
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
            # Drop ze seznamu sampleů
            self._handle_list_drop(event)

        elif event.mimeData().hasFormat("application/x-matrix-sample"):
            # Drop z jiné pozice v matici
            self._handle_matrix_drop(event)

        else:
            event.ignore()

        self._update_style()

    def _handle_list_drop(self, event):
        """Obsluha drop ze seznamu sampleů"""
        filename = event.mimeData().data("application/x-sample-metadata").data().decode()

        # Najdi sample v parent widget
        parent_window = self._find_main_window()
        if not parent_window:
            event.ignore()
            return

        sample = self._find_sample_by_filename(parent_window, filename)
        if not sample:
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

            # Označit starý sample jako nemapovaný
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
        parent_window = self._find_main_window()
        if not parent_window:
            event.ignore()
            return

        sample = self._find_sample_by_filename(parent_window, filename)
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

            # Označit přepsaný sample jako nemapovaný
            self.sample.mapped = False

        # Najdi a vyčisti starou pozici
        matrix_widget = self._find_matrix_widget()
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

    def _find_main_window(self):
        """Najde hlavní okno aplikace"""
        widget = self
        while widget.parent():
            widget = widget.parent()
            if hasattr(widget, 'samples'):
                return widget
        return None

    def _find_matrix_widget(self):
        """Najde matrix widget"""
        widget = self
        while widget.parent():
            widget = widget.parent()
            if hasattr(widget, 'mapping') and hasattr(widget, 'matrix_cells'):
                return widget
        return None

    def _find_sample_by_filename(self, main_window, filename: str) -> Optional[SampleMetadata]:
        """Najde sample podle filename v hlavním okně"""
        for sample in main_window.samples:
            if sample.filename == filename:
                return sample
        return None


class DragDropMappingMatrix(QGroupBox):
    """Mapovací matice s podporou drag & drop a celým piano rozsahem"""

    sample_mapped = Signal(object, int, int)  # sample, midi, velocity
    sample_unmapped = Signal(object, int, int)  # sample, midi, velocity
    sample_play_requested = Signal(object)  # sample - signál pro přehrávání z matice
    midi_note_play_requested = Signal(int)  # midi_note - signál pro přehrávání MIDI tónu
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity

    def __init__(self):
        super().__init__("Mapovací matice: Celý piano rozsah A0-C8 (nejvyšší frekvence nahoře)")
        self.mapping = {}  # (midi, velocity) -> SampleMetadata
        self.matrix_cells = {}

        # MIDI rozsah piano
        self.piano_min_midi = MidiUtils.PIANO_MIN_MIDI  # 21 (A0)
        self.piano_max_midi = MidiUtils.PIANO_MAX_MIDI  # 108 (C8)

        self.init_ui()

    def init_ui(self):
        """Inicializace mapovací matice s celým piano rozsahem"""
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
        """Vytvoří info panel s celkovými statistikami"""
        info_layout = QHBoxLayout()

        range_info_label = QLabel(f"Celý piano rozsah: A0-C8 (MIDI {self.piano_min_midi}-{self.piano_max_midi}) | Nejvyšší frekvence nahoře")
        range_info_label.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(range_info_label)

        info_layout.addStretch()

        self.stats_label = QLabel("Namapováno: 0 sampleů")
        self.stats_label.setStyleSheet("color: #333; font-weight: bold;")
        info_layout.addWidget(self.stats_label)

        layout.addLayout(info_layout)

    def _create_full_matrix(self):
        """Vytvoří matici buněk pro celý piano rozsah"""
        # Vyčisti existující layout
        if self.matrix_widget.layout():
            while self.matrix_widget.layout().count():
                child = self.matrix_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        matrix_layout = QGridLayout()
        matrix_layout.setSpacing(2)  # Menší spacing pro kompaktnější zobrazení

        # Header řádek
        matrix_layout.addWidget(self._create_header_label("MIDI"), 0, 0)
        matrix_layout.addWidget(self._create_header_label("Nota"), 0, 1)
        for vel in range(8):
            vel_label = self._create_header_label(f"V{vel}")
            matrix_layout.addWidget(vel_label, 0, vel + 2)

        # Vytvoř buňky pro celý piano rozsah - od nejvyšší noty (C8) k nejnižší (A0)
        self.matrix_cells.clear()

        # Seřazení od nejvyšší po nejnižší MIDI notu
        midi_notes = list(range(self.piano_min_midi, self.piano_max_midi + 1))
        midi_notes.reverse()  # C8 (108) na vrcholu, A0 (21) na spodku

        for i, midi_note in enumerate(midi_notes):
            row = i + 1

            # MIDI číslo - klikací pro přehrávání tónu
            midi_label = self._create_clickable_midi_label(midi_note)
            matrix_layout.addWidget(midi_label, row, 0)

            # Nota jméno
            note_name = MidiUtils.midi_to_note_name(midi_note)
            note_label = QLabel(note_name)
            note_label.setAlignment(Qt.AlignCenter)
            note_label.setStyleSheet("background-color: #f5f5f5; padding: 3px; border-radius: 3px; font-weight: bold; font-size: 10px;")
            matrix_layout.addWidget(note_label, row, 1)

            # Velocity buňky
            for velocity in range(8):
                cell = DragDropMatrixCell(midi_note, velocity)
                cell.sample_dropped.connect(self._on_sample_dropped)
                cell.sample_play_requested.connect(self.sample_play_requested.emit)
                cell.sample_moved.connect(self._on_sample_moved)

                # Pokud už je namapovaný sample, nastav ho
                key = (midi_note, velocity)
                if key in self.mapping:
                    cell.sample = self.mapping[key]
                    cell._update_style()

                matrix_layout.addWidget(cell, row, velocity + 2)
                self.matrix_cells[(midi_note, velocity)] = cell

        self.matrix_widget.setLayout(matrix_layout)

    def _create_header_label(self, text: str) -> QLabel:
        """Vytvoří header label pro matici"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                background-color: #e0e0e0; 
                padding: 5px; 
                border-radius: 3px;
                color: #333;
                border: 1px solid #ccc;
                font-size: 11px;
            }
        """)
        return label

    def _create_clickable_midi_label(self, midi_note: int) -> QPushButton:
        """Vytvoří klikací MIDI label pro přehrávání tónu"""
        label = QPushButton(str(midi_note))
        label.setFixedSize(40, 30)
        label.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: 1px solid #2980b9;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        label.setToolTip(f"Klik = přehrát MIDI tón {midi_note} ({MidiUtils.midi_to_note_name(midi_note)})")
        label.clicked.connect(lambda: self.midi_note_play_requested.emit(midi_note))
        return label

    def _on_sample_dropped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Obsluha drop sample na buňku"""
        key = (midi_note, velocity)
        old_sample = self.mapping.get(key)

        if old_sample and old_sample != sample:
            old_sample.mapped = False
            self.sample_unmapped.emit(old_sample, midi_note, velocity)

        self.mapping[key] = sample
        self._update_stats()
        self.sample_mapped.emit(sample, midi_note, velocity)

    def _on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int, new_velocity: int):
        """Obsluha přesunu sample v matici"""
        # Signál je už zpracovaný v buňce, jen předáváme dál a aktualizujeme stats
        self._update_stats()
        self.sample_moved.emit(sample, old_midi, old_velocity, new_midi, new_velocity)

    def add_sample(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Programově přidá sample (pro auto-mapping)"""
        key = (midi_note, velocity)
        self.mapping[key] = sample
        sample.mapped = True

        # Aktualizuj buňku pokud je zobrazená
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            cell.sample = sample
            cell._update_style()

        self._update_stats()
        self.sample_mapped.emit(sample, midi_note, velocity)

    def get_mapped_samples(self) -> List[SampleMetadata]:
        """Vrátí všechny namapované samples"""
        return list(self.mapping.values())

    def _update_stats(self):
        """Aktualizuje statistiky"""
        count = len(self.mapping)
        self.stats_label.setText(f"Namapováno: {count} sampleů")

    def scroll_to_sample(self, sample: SampleMetadata):
        """Posune zobrazení na pozici obsahující daný sample"""
        for (midi_note, velocity), mapped_sample in self.mapping.items():
            if mapped_sample == sample:
                # Najdi widget buňky a poskoč na něj
                if (midi_note, velocity) in self.matrix_cells:
                    cell = self.matrix_cells[(midi_note, velocity)]
                    # Spočítej řádek v matici (nejvyšší MIDI má řádek 1)
                    row_index = self.piano_max_midi - midi_note + 1

                    # Najdi scroll area parent
                    scroll_area = None
                    parent = cell.parent()
                    while parent:
                        if isinstance(parent, QScrollArea):
                            scroll_area = parent
                            break
                        parent = parent.parent()

                    if scroll_area:
                        # Aproximace pozice pro scroll
                        cell_height = 37  # Výška buňky + spacing
                        target_y = row_index * cell_height
                        scroll_area.verticalScrollBar().setValue(target_y - 200)  # Offset pro lepší viditelnost
                break

    def get_displayed_range(self):
        """Vrátí celý piano rozsah (pro kompatibilitu)"""
        return (self.piano_min_midi, self.piano_max_midi)


class DragDropSampleList(QGroupBox):
    """Seznam sampleů s podporou drag operací a přehrávání"""

    sample_selected = Signal(object)
    play_requested = Signal(object)
    compare_requested = Signal(object)
    simultaneous_requested = Signal(object)

    def __init__(self):
        super().__init__("Analyzované samples - MEZERNÍK = přehrát | S = porovnat | D = současně")
        self.samples = []
        self.init_ui()

    def init_ui(self):
        """Inicializace seznamu s drag podporou"""
        layout = QVBoxLayout()

        # Info panel
        self.info_label = QLabel("Žádné samples načteny")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.info_label)

        # Instrukce s přehrávání
        instructions = QLabel(
            "Tip: Přetáhněte sample do matice | "
            "MEZERNÍK = přehrát | S = porovnat (tón→sample) | D = současně (tón+sample)"
        )
        instructions.setStyleSheet(
            "color: #0066cc; font-size: 12px; background-color: #f0f8ff; "
            "padding: 8px; border-radius: 4px; border: 1px solid #cce7ff;"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Seznam s drag podporou a klávesovými zkratkami
        self.sample_list = DragDropListWidget()
        self.sample_list.itemClicked.connect(self._on_item_clicked)
        self.sample_list.play_requested.connect(self.play_requested.emit)
        self.sample_list.compare_requested.connect(self.compare_requested.emit)
        self.sample_list.simultaneous_requested.connect(self.simultaneous_requested.emit)
        layout.addWidget(self.sample_list)

        self.setLayout(layout)

    def update_samples(self, samples: List[SampleMetadata]):
        """Aktualizuje seznam sampleů"""
        self.samples = samples
        self.sample_list.clear()

        if not samples:
            self.info_label.setText("Žádné samples načteny")
            return

        self.info_label.setText(f"Načteno {len(samples)} sampleů")

        for sample in samples:
            note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
            velocity_desc = VelocityUtils.velocity_to_description(sample.velocity_level)

            item_text = (f"{sample.filename}\n"
                        f"  {note_name} (MIDI {sample.detected_midi})\n"
                        f"  {velocity_desc} (V{sample.velocity_level}), Conf: {sample.pitch_confidence:.2f}")

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, sample)

            # Barva podle stavu
            if sample.mapped:
                item.setBackground(QColor("#e8f5e8"))
                item.setToolTip("Sample je namapován v matici | MEZERNÍK = přehrát | S = porovnat | D = současně")
            else:
                item.setBackground(QColor("#ffffff"))
                item.setToolTip("Přetáhněte do mapovací matice | MEZERNÍK = přehrát | S = porovnat | D = současně")

            self.sample_list.addItem(item)

    def _on_item_clicked(self, item):
        """Obsluha kliknutí na item"""
        sample = item.data(Qt.UserRole)
        self.sample_selected.emit(sample)

    def refresh_display(self):
        """Obnoví zobrazení"""
        for i in range(self.sample_list.count()):
            item = self.sample_list.item(i)
            sample = item.data(Qt.UserRole)

            if sample.mapped:
                item.setBackground(QColor("#e8f5e8"))
                item.setToolTip("Sample je namapován v matici | MEZERNÍK = přehrát | S = porovnat | D = současně")
            else:
                item.setBackground(QColor("#ffffff"))
                item.setToolTip("Přetáhněte do mapovací matice | MEZERNÍK = přehrát | S = porovnat | D = současně")