"""
inline_midi_editor.py - Kompaktní MIDI editor s propojením na session cache - OPRAVENÁ VERZE
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, QFrame,
                               QCheckBox, QDialog, QVBoxLayout, QDialogButtonBox, QTextEdit, QApplication)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QFont, QDrag, QPixmap, QPainter, QColor, QMouseEvent

from models import SampleMetadata
from midi_utils import MidiUtils
import logging

logger = logging.getLogger(__name__)


class SampleListItem(QWidget):
    """
    Rozšířený item pro sample list s dedikovaným drag tlačítkem.
    OPRAVENA - propojuje MIDI změny s parent hierarchií.
    """

    sample_selected = Signal(object)  # sample
    sample_play_requested = Signal(object)  # sample
    midi_changed = Signal(object, int, int)  # sample, old_midi, new_midi
    sample_disabled_changed = Signal(object, bool)  # sample, disabled
    drag_requested = Signal(object)  # sample
    drag_finished = Signal()  # Signál ukončení drag operace

    def __init__(self, sample: SampleMetadata, parent=None):
        super().__init__(parent)
        self.sample = sample
        self.is_selected = False

        # Přidáme disable flag do sample
        if not hasattr(self.sample, 'disabled'):
            self.sample.disabled = False

        self.init_ui()

    def init_ui(self):
        """Inicializuje kompaktní UI s dedikovaným drag tlačítkem."""
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # DRAG TLAČÍTKO - fixed width pro zarovnání
        self.drag_button = self._create_drag_button()
        layout.addWidget(self.drag_button)

        # Disable checkbox - fixed width pro zarovnání
        self.disable_checkbox = QCheckBox()
        self.disable_checkbox.setChecked(self.sample.disabled)
        self.disable_checkbox.setToolTip("Zakázat použití tohoto sample")
        self.disable_checkbox.stateChanged.connect(self._on_disable_changed)
        self.disable_checkbox.setFixedWidth(25)
        layout.addWidget(self.disable_checkbox)

        # MIDI info - prioritní informace s FIXED widths pro zarovnání do sloupců
        midi_info_layout = QHBoxLayout()
        midi_info_layout.setSpacing(4)

        # MIDI číslo - FIXED WIDTH
        self.midi_number_label = QLabel()
        self.midi_number_label.setFixedWidth(45)  # Fixed místo minimum
        self.midi_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.midi_number_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #e3f2fd;
                padding: 3px 5px;
                border-radius: 4px;
                border: 1px solid #1976d2;
                color: #1976d2;
                font-size: 11px;
            }
        """)
        midi_info_layout.addWidget(self.midi_number_label)

        # Nota název - FIXED WIDTH
        self.note_name_label = QLabel()
        self.note_name_label.setFixedWidth(45)  # Fixed místo minimum
        self.note_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_name_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #f3e5f5;
                padding: 3px 5px;
                border-radius: 4px;
                border: 1px solid #7b1fa2;
                color: #7b1fa2;
                font-size: 11px;
            }
        """)
        midi_info_layout.addWidget(self.note_name_label)

        # RMS info - FIXED WIDTH
        self.rms_label = QLabel()
        self.rms_label.setFixedWidth(100)  # Fixed místo minimum
        self.rms_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rms_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #e8f5e9;
                padding: 3px 5px;
                border-radius: 4px;
                border: 1px solid #388e3c;
                color: #388e3c;
                font-size: 10px;
            }
        """)
        midi_info_layout.addWidget(self.rms_label)

        layout.addLayout(midi_info_layout)

        # Transpozice tlačítka v rounded boxu
        self._create_compact_transpose_buttons_group(layout)

        # Play button v rounded boxu
        self._create_play_button_group(layout)

        layout.addStretch()

        self.setLayout(layout)
        self.setMaximumHeight(32)
        self._update_display()

        # Selection handling
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_file_info)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Selection handling - pouze na mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Kontrola, zda klik nebyl na drag tlačítko nebo jiné interaktivní prvky
            drag_button_rect = self.drag_button.geometry()
            checkbox_rect = self.disable_checkbox.geometry()

            click_pos = event.pos()

            # Ignoruj kliky na interaktivní prvky
            if (drag_button_rect.contains(click_pos) or
                checkbox_rect.contains(click_pos)):
                super().mouseReleaseEvent(event)
                return

            # Zkontroluj transpozice tlačítka
            for child in self.findChildren(QPushButton):
                if child != self.drag_button and child.geometry().contains(click_pos):
                    super().mouseReleaseEvent(event)
                    return

            # Jinak proveď selection
            self.sample_selected.emit(self.sample)
            logger.debug(f"Selected sample: {self.sample.filename}")

        super().mouseReleaseEvent(event)

    def _create_drag_button(self) -> QPushButton:
        """Vytvoří dedikované drag tlačítko."""
        drag_btn = QPushButton("⋮⋮")  # Vertical dots jako drag handle
        drag_btn.setMaximumWidth(30)
        drag_btn.setMaximumHeight(30)
        drag_btn.setToolTip("Přetáhnout do matice (Drag & Drop)")

        drag_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                font-size: 14px;
                letter-spacing: -1px;
            }
            QPushButton:hover {
                background-color: #1976D2;
                cursor: move;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        # Drag event handling
        drag_btn.mousePressEvent = self._drag_button_press
        drag_btn.mouseMoveEvent = self._drag_button_move

        return drag_btn

    def _drag_button_press(self, event):
        """Mouse press na drag tlačítku."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()

    def _drag_button_move(self, event):
        """Mouse move na drag tlačítku - spustí drag operaci."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if not hasattr(self, 'drag_start_position'):
            return

        distance = (event.pos() - self.drag_start_position).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        if not self._is_sample_draggable():
            return

        self._start_drag_operation()

    def _is_sample_draggable(self) -> bool:
        """Kontroluje, zda je sample vhodný pro drag."""
        if not self.sample:
            return False

        if self.sample.disabled:
            logger.debug(f"Sample {self.sample.filename} is disabled - not draggable")
            return False

        if self.sample.is_filtered:
            logger.debug(f"Sample {self.sample.filename} is filtered - not draggable")
            return False

        if self.sample.mapped:
            logger.debug(f"Sample {self.sample.filename} is already mapped - not draggable")
            return False

        return True

    def _find_parent_sample_list(self):
        """Najde parent DragDropSampleList widget."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_rebuild_list_with_samples'):
                return parent
            parent = parent.parent()
        return None

    def _start_drag_operation(self):
        """Spustí drag operaci pro tento sample."""
        # BEZPEČNOST: Kontrola zda není UI vytváření v průběhu
        parent_list = self._find_parent_sample_list()
        if parent_list and hasattr(parent_list, 'ui_creation_in_progress') and parent_list.ui_creation_in_progress:
            logger.warning(f"Cannot drag {self.sample.filename} - UI creation in progress")
            return

        try:
            mime_data = QMimeData()
            mime_data.setData("application/x-sample-metadata", str(id(self.sample)).encode())

            drag = QDrag(self)
            drag.setMimeData(mime_data)

            pixmap = self._create_drag_pixmap()
            if pixmap and not pixmap.isNull():
                drag.setPixmap(pixmap)

            self.drag_requested.emit(self.sample)

            logger.info(f"Starting drag operation: {self.sample.filename}")

            result = drag.exec(Qt.DropAction.MoveAction)
            logger.debug(f"Drag completed with result: {result}")

            # BEZPEČNOST: Oznámit ukončení drag operace
            self.drag_finished.emit()

        except Exception as e:
            logger.error(f"Drag operation failed: {e}")
            # BEZPEČNOST: I při chybě oznámit ukončení drag operace
            self.drag_finished.emit()

    def _create_drag_pixmap(self) -> QPixmap:
        """Vytvoří pixmap pro drag operaci."""
        try:
            width, height = 280, 90
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor(33, 150, 243, 200))

            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))

            # Header
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            painter.drawText(8, 18, "DRAG & DROP")

            # Filename
            painter.setFont(QFont("Arial", 10))
            filename_text = self.sample.filename[:35] + "..." if len(self.sample.filename) > 35 else self.sample.filename
            painter.drawText(8, 38, filename_text)

            # MIDI info
            if self.sample.detected_midi:
                note_name = MidiUtils.midi_to_note_name(self.sample.detected_midi)
                painter.drawText(8, 55, f"♪ {note_name} (MIDI {self.sample.detected_midi})")

            # RMS info
            if self.sample.velocity_amplitude:
                painter.drawText(8, 72, f"RMS: {self.sample.velocity_amplitude:.6f}")

            painter.end()
            return pixmap

        except Exception as e:
            logger.error(f"Failed to create drag pixmap: {e}")
    def _create_compact_transpose_buttons_group(self, layout):
        """Vytvoří transpozice tlačítka v rounded boxu (konzistentní s RMS/MIDI stylem)."""
        # Container frame pro rounded box - FIXED WIDTH pro zarovnání
        transpose_frame = QFrame()
        transpose_frame.setFixedWidth(135)  # Fixed width pro column alignment
        transpose_frame.setStyleSheet("""
            QFrame {
                background-color: #fff9e6;
                border-radius: 4px;
                border: 1px solid #ffa726;
                padding: 2px 4px;
            }
        """)

        transpose_layout = QHBoxLayout()
        transpose_layout.setContentsMargins(3, 2, 3, 2)
        transpose_layout.setSpacing(3)

        # -12, -1, +1, +12
        buttons_config = [
            ("-12", -12, "#c0392b", "Oktáva dolů"),
            ("-1", -1, "#e74c3c", "Půltón dolů"),
            ("+1", 1, "#27ae60", "Půltón nahoru"),
            ("+12", 12, "#2ecc71", "Oktáva nahoru")
        ]

        for text, semitones, color, tooltip in buttons_config:
            btn = QPushButton(text)
            btn.setFixedWidth(28)  # Fixed width
            btn.setMaximumHeight(24)
            btn.clicked.connect(lambda checked, s=semitones: self._transpose(s))
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            transpose_layout.addWidget(btn)

        transpose_frame.setLayout(transpose_layout)
        layout.addWidget(transpose_frame)

    def _create_play_button_group(self, layout):
        """Vytvoří play button v rounded boxu s větší šířkou a ikonou noty."""
        # Container frame pro rounded box - FIXED WIDTH pro zarovnání
        play_frame = QFrame()
        play_frame.setFixedWidth(60)  # Fixed width pro column alignment
        play_frame.setStyleSheet("""
            QFrame {
                background-color: #e8f5e9;
                border-radius: 4px;
                border: 1px solid #66bb6a;
                padding: 2px 4px;
            }
        """)

        play_layout = QHBoxLayout()
        play_layout.setContentsMargins(3, 2, 3, 2)
        play_layout.setSpacing(0)

        # Play button s fixed šířkou
        play_btn = QPushButton("♪")
        play_btn.setFixedWidth(48)  # Fixed width pro column alignment
        play_btn.setMaximumHeight(24)
        play_btn.setToolTip("Přehrát sample")
        play_btn.clicked.connect(self._play_sample)
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 3px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        play_layout.addWidget(play_btn)

        play_frame.setLayout(play_layout)
        layout.addWidget(play_frame)

    def _update_display(self):
        """Aktualizuje zobrazení informací."""
        if self.sample and self.sample.detected_midi:
            # MIDI číslo
            self.midi_number_label.setText(str(self.sample.detected_midi))

            # Nota název
            note_name = MidiUtils.midi_to_note_name(self.sample.detected_midi)
            self.note_name_label.setText(note_name)

            # RMS info
            if self.sample.velocity_amplitude:
                self.rms_label.setText(f"RMS:{self.sample.velocity_amplitude:.4f}")
            else:
                self.rms_label.setText("RMS:---")
        else:
            self.midi_number_label.setText("---")
            self.note_name_label.setText("---")
            self.rms_label.setText("RMS:---")

        # Aktualizace drag tlačítka
        self._update_drag_button_state()

        # Update colors based on state
        self._update_colors()

    def _update_drag_button_state(self):
        """Aktualizuje stav drag tlačítka."""
        draggable = self._is_sample_draggable()
        self.drag_button.setEnabled(draggable)

        if not draggable:
            tooltip = "Nelze přetáhnout: "
            if self.sample.disabled:
                tooltip += "sample je zakázán"
            elif self.sample.is_filtered:
                tooltip += "sample je filtrován"
            elif self.sample.mapped:
                tooltip += "sample je již namapován"
            else:
                tooltip += "neznámý důvod"
            self.drag_button.setToolTip(tooltip)
        else:
            self.drag_button.setToolTip("Přetáhnout do matice (Drag & Drop)")

    def _update_colors(self):
        """Aktualizuje barvy podle stavu."""
        if self.sample.disabled:
            bg_color = "#ffebee"
            opacity = "opacity: 0.6;"
        elif self.sample.is_filtered:
            bg_color = "#e0e0e0"
            opacity = ""
        elif self.sample.mapped:
            bg_color = "#e8f5e8"
            opacity = ""
        elif self.is_selected:
            bg_color = "#fff3e0"
            opacity = ""
        else:
            bg_color = "#ffffff"
            opacity = ""

        self.setStyleSheet(f"""
            SampleListItem {{
                background-color: {bg_color};
                border: 1px solid #ddd;
                border-radius: 4px;
                {opacity}
            }}
        """)

    def _on_disable_changed(self, state):
        """Handler pro změnu disable stavu."""
        self.sample.disabled = state == Qt.CheckState.Checked.value
        self._update_display()
        self.sample_disabled_changed.emit(self.sample, self.sample.disabled)
        logger.debug(f"Sample {self.sample.filename} disabled: {self.sample.disabled}")

    def _transpose(self, semitones: int):
        """
        KLÍČOVÁ OPRAVA: Transponuje MIDI notu a emituje signál pro session cache aktualizaci.
        """
        if not self.sample or not self.sample.detected_midi:
            logger.warning(f"Cannot transpose {self.sample.filename}: no MIDI data")
            return

        old_midi = self.sample.detected_midi
        new_midi = old_midi + semitones

        # Omezit na piano rozsah
        new_midi = max(MidiUtils.PIANO_MIN_MIDI, min(MidiUtils.PIANO_MAX_MIDI, new_midi))

        if new_midi != old_midi:
            # Aktualizuj sample
            self.sample.detected_midi = new_midi

            # Aktualizuj také frekvenci pro konzistenci
            self.sample.detected_frequency = 440.0 * (2 ** ((new_midi - 69) / 12))

            # Refresh UI
            self._update_display()

            # KLÍČOVÉ: Emit signál pro session cache aktualizaci
            self.midi_changed.emit(self.sample, old_midi, new_midi)

            logger.info(f"Transposed {self.sample.filename}: MIDI {old_midi} -> {new_midi}")
        else:
            logger.debug(f"Transpose for {self.sample.filename} resulted in same MIDI note: {new_midi}")

    def _play_sample(self):
        """Přehraje sample."""
        if self.sample and not self.sample.disabled:
            self.sample_play_requested.emit(self.sample)

    def _show_file_info(self, position):
        """Zobrazí dialog s informacemi o souboru při pravém kliknutí."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Informace o souboru")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Vytvoř detailní info text
        info_text = f"""NÁZEV SOUBORU:
{self.sample.filename}

CESTA:
{self.sample.filepath}

MIDI DETEKCE:
Nota: {MidiUtils.midi_to_note_name(self.sample.detected_midi) if self.sample.detected_midi else 'Nedetekováno'}
MIDI číslo: {self.sample.detected_midi if self.sample.detected_midi else 'N/A'}
Frekvence: {self.sample.detected_frequency:.2f} Hz if self.sample.detected_frequency else 'N/A'
Confidence: {self.sample.pitch_confidence:.3f} if self.sample.pitch_confidence else 'N/A'
Metoda: {self.sample.pitch_method if self.sample.pitch_method else 'N/A'}

AMPLITUDE ANALÝZA:
RMS (500ms): {self.sample.velocity_amplitude:.6f} if self.sample.velocity_amplitude else 'N/A'
RMS dB: {self.sample.velocity_amplitude_db:.2f} dB if self.sample.velocity_amplitude_db else 'N/A'
Peak amplitude: {self.sample.peak_amplitude:.6f} if self.sample.peak_amplitude else 'N/A'

AUDIO INFO:
Délka: {self.sample.duration:.2f}s if self.sample.duration else 'N/A'
Sample rate: {self.sample.sample_rate} Hz if self.sample.sample_rate else 'N/A'
Kanály: {self.sample.channels} if self.sample.channels else 'N/A'

STAV:
Analyzován: {'Ano' if self.sample.analyzed else 'Ne'}
Namapován: {'Ano' if self.sample.mapped else 'Ne'}
Filtrován: {'Ano' if self.sample.is_filtered else 'Ne'}
Zakázán: {'Ano' if self.sample.disabled else 'Ne'}

SESSION CACHE:
Hash: {getattr(self.sample, '_hash', 'N/A')[:8]}... if hasattr(self.sample, '_hash') else 'N/A'
"""

        text_edit = QTextEdit()
        text_edit.setPlainText(info_text)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        # OK button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        dialog.exec()

    def set_selected(self, selected: bool):
        """Nastaví stav výběru."""
        self.is_selected = selected
        self._update_colors()

    def refresh(self):
        """Obnoví zobrazení po změnách."""
        self._update_display()


class InlineMidiEditor(QWidget):
    """
    Kompaktní MIDI editor přímo u každého sample.
    Umožňuje transpozici ±1 půltón a ±12 půltónů (oktáva).
    """

    midi_changed = Signal(object, int, int)  # sample, old_midi, new_midi
    play_sample_requested = Signal(object)  # sample

    def __init__(self, sample: SampleMetadata, parent=None):
        super().__init__(parent)
        self.sample = sample
        self.original_midi = sample.detected_midi if sample.detected_midi else 60
        self.init_ui()

    def init_ui(self):
        """Inicializuje kompaktní UI."""
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        # Current MIDI display
        self.midi_label = QLabel()
        self.midi_label.setMinimumWidth(50)
        self.midi_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #f0f0f0;
                padding: 2px 4px;
                border-radius: 3px;
                border: 1px solid #ccc;
            }
        """)
        layout.addWidget(self.midi_label)

        # Transpozice tlačítka
        self._create_transpose_buttons(layout)

        # Play button
        play_btn = QPushButton("♪")
        play_btn.setMaximumWidth(20)
        play_btn.setToolTip("Přehrát sample")
        play_btn.clicked.connect(self._play_sample)
        play_btn.setStyleSheet("""
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
        layout.addWidget(play_btn)

        self.setLayout(layout)
        self.setMaximumHeight(25)
        self._update_display()

    def _create_transpose_buttons(self, layout):
        """Vytvoří tlačítka pro transpozici."""
        # -12 (oktáva dolů)
        btn_oct_down = self._create_transpose_button("-12", -12, "#c0392b")
        btn_oct_down.setToolTip("Oktáva dolů")
        layout.addWidget(btn_oct_down)

        # -1 (půltón dolů)
        btn_semi_down = self._create_transpose_button("-1", -1, "#e74c3c")
        btn_semi_down.setToolTip("Půltón dolů")
        layout.addWidget(btn_semi_down)

        # +1 (půltón nahoru)
        btn_semi_up = self._create_transpose_button("+1", 1, "#27ae60")
        btn_semi_up.setToolTip("Půltón nahoru")
        layout.addWidget(btn_semi_up)

        # +12 (oktáva nahoru)
        btn_oct_up = self._create_transpose_button("+12", 12, "#2ecc71")
        btn_oct_up.setToolTip("Oktáva nahoru")
        layout.addWidget(btn_oct_up)

    def _create_transpose_button(self, text: str, semitones: int, color: str) -> QPushButton:
        """Vytvoří tlačítko pro transpozici."""
        btn = QPushButton(text)
        btn.setMaximumWidth(25)
        btn.clicked.connect(lambda: self._transpose(semitones))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border-radius: 3px;
                border: none;
                font-size: 10px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        return btn

    def _transpose(self, semitones: int):
        """Transponuje MIDI notu o zadaný počet půltónů s propojením na session cache."""
        if not self.sample or not self.sample.detected_midi:
            return

        old_midi = self.sample.detected_midi
        new_midi = old_midi + semitones

        # Omezit na piano rozsah
        new_midi = max(MidiUtils.PIANO_MIN_MIDI, min(MidiUtils.PIANO_MAX_MIDI, new_midi))

        if new_midi != old_midi:
            self.sample.detected_midi = new_midi
            self.sample.detected_frequency = 440.0 * (2 ** ((new_midi - 69) / 12))
            self._update_display()
            self.midi_changed.emit(self.sample, old_midi, new_midi)
            logger.debug(f"Transposed {self.sample.filename}: MIDI {old_midi} -> {new_midi}")

    def _play_sample(self):
        """Přehraje sample."""
        if self.sample:
            self.play_sample_requested.emit(self.sample)

    def _update_display(self):
        """Aktualizuje zobrazení MIDI noty."""
        if self.sample and self.sample.detected_midi:
            note_name = MidiUtils.midi_to_note_name(self.sample.detected_midi)
            self.midi_label.setText(f"{note_name}({self.sample.detected_midi})")
        else:
            self.midi_label.setText("--")

    def set_sample(self, sample: SampleMetadata):
        """Nastaví nový sample."""
        self.sample = sample
        self._update_display()