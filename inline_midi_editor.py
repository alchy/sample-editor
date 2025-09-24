"""
inline_midi_editor.py - Kompaktní MIDI editor přímo u každého sample
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import SampleMetadata
from midi_utils import MidiUtils
import logging

logger = logging.getLogger(__name__)


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
        """Transponuje MIDI notu o zadaný počet půltónů."""
        if not self.sample or not self.sample.detected_midi:
            return

        old_midi = self.sample.detected_midi
        new_midi = old_midi + semitones

        # Omezit na piano rozsah
        new_midi = max(MidiUtils.PIANO_MIN_MIDI, min(MidiUtils.PIANO_MAX_MIDI, new_midi))

        if new_midi != old_midi:
            self.sample.detected_midi = new_midi
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


class SampleListItem(QWidget):
    """
    Rozšířený item pro sample list s kompaktním zobrazením a disable možností.
    """

    sample_selected = Signal(object)  # sample
    sample_play_requested = Signal(object)  # sample
    midi_changed = Signal(object, int, int)  # sample, old_midi, new_midi
    sample_disabled_changed = Signal(object, bool)  # sample, disabled

    def __init__(self, sample: SampleMetadata, parent=None):
        super().__init__(parent)
        self.sample = sample
        self.is_selected = False

        # Přidáme disable flag do sample
        if not hasattr(self.sample, 'disabled'):
            self.sample.disabled = False

        self.init_ui()

    def init_ui(self):
        """Inicializuje kompaktní UI pro sample item."""
        layout = QHBoxLayout()
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(5)

        # Disable checkbox
        from PySide6.QtWidgets import QCheckBox
        self.disable_checkbox = QCheckBox()
        self.disable_checkbox.setChecked(self.sample.disabled)
        self.disable_checkbox.setToolTip("Zakázat použití tohoto sample")
        self.disable_checkbox.stateChanged.connect(self._on_disable_changed)
        layout.addWidget(self.disable_checkbox)

        # MIDI info - prioritní informace
        midi_info_layout = QHBoxLayout()
        midi_info_layout.setSpacing(3)

        # MIDI číslo
        self.midi_number_label = QLabel()
        self.midi_number_label.setMinimumWidth(35)
        self.midi_number_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #e3f2fd;
                padding: 2px 4px;
                border-radius: 3px;
                border: 1px solid #1976d2;
                color: #1976d2;
            }
        """)
        midi_info_layout.addWidget(self.midi_number_label)

        # Nota název
        self.note_name_label = QLabel()
        self.note_name_label.setMinimumWidth(30)
        self.note_name_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #f3e5f5;
                padding: 2px 4px;
                border-radius: 3px;
                border: 1px solid #7b1fa2;
                color: #7b1fa2;
            }
        """)
        midi_info_layout.addWidget(self.note_name_label)

        # RMS info
        self.rms_label = QLabel()
        self.rms_label.setMinimumWidth(80)
        self.rms_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                background-color: #e8f5e9;
                padding: 2px 4px;
                border-radius: 3px;
                border: 1px solid #388e3c;
                color: #388e3c;
            }
        """)
        midi_info_layout.addWidget(self.rms_label)

        layout.addLayout(midi_info_layout)

        # Transpozice tlačítka (kompaktní)
        self._create_compact_transpose_buttons(layout)

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

        layout.addStretch()

        self.setLayout(layout)
        self.setMaximumHeight(28)  # Kompaktnější
        self._update_display()

        # Click handling for selection
        self.mousePressEvent = self._on_mouse_press
        # Right click for file info
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_file_info)

    def _create_compact_transpose_buttons(self, layout):
        """Vytvoří kompaktní transpozice tlačítka."""

        transpose_layout = QHBoxLayout()
        transpose_layout.setSpacing(1)

        # -12, -1, +1, +12
        buttons_config = [
            ("-12", -12, "#c0392b", "Oktáva dolů"),
            ("-1", -1, "#e74c3c", "Půltón dolů"),
            ("+1", 1, "#27ae60", "Půltón nahoru"),
            ("+12", 12, "#2ecc71", "Oktáva nahoru")
        ]

        for text, semitones, color, tooltip in buttons_config:
            btn = QPushButton(text)
            btn.setMaximumWidth(20)
            btn.setMaximumHeight(20)
            btn.clicked.connect(lambda checked, s=semitones: self._transpose(s))
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    border-radius: 2px;
                    border: none;
                    font-size: 9px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            transpose_layout.addWidget(btn)

        layout.addLayout(transpose_layout)

    def _on_disable_changed(self, state):
        """Handler pro změnu disable stavu."""
        self.sample.disabled = state == Qt.CheckState.Checked.value
        self._update_display()
        self.sample_disabled_changed.emit(self.sample, self.sample.disabled)
        logger.debug(f"Sample {self.sample.filename} disabled: {self.sample.disabled}")

    def _transpose(self, semitones: int):
        """Transponuje MIDI notu o zadaný počet půltónů."""
        if not self.sample or not self.sample.detected_midi:
            return

        old_midi = self.sample.detected_midi
        new_midi = old_midi + semitones

        # Omezit na piano rozsah
        new_midi = max(MidiUtils.PIANO_MIN_MIDI, min(MidiUtils.PIANO_MAX_MIDI, new_midi))

        if new_midi != old_midi:
            self.sample.detected_midi = new_midi
            self._update_display()
            self.midi_changed.emit(self.sample, old_midi, new_midi)
            logger.debug(f"Transposed {self.sample.filename}: MIDI {old_midi} -> {new_midi}")

    def _play_sample(self):
        """Přehraje sample."""
        if self.sample and not self.sample.disabled:
            self.sample_play_requested.emit(self.sample)

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

        # Update colors based on state
        self._update_colors()

    def _update_colors(self):
        """Aktualizuje barvy podle stavu."""
        if self.sample.disabled:
            bg_color = "#ffebee"  # Světle červená
            opacity = "opacity: 0.6;"
        elif self.sample.is_filtered:
            bg_color = "#e0e0e0"
            opacity = ""
        elif self.sample.mapped:
            bg_color = "#e8f5e8"
            opacity = ""
        elif self.is_selected:
            bg_color = "#fff3e0"  # Světle oranžová pro selection
            opacity = ""
        else:
            bg_color = "#ffffff"
            opacity = ""

        self.setStyleSheet(f"""
            SampleListItem {{
                background-color: {bg_color};
                border: 1px solid #ddd;
                border-radius: 3px;
                {opacity}
            }}
        """)

    def _show_file_info(self, position):
        """Zobrazí dialog s informacemi o souboru při pravém kliknutí."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QTextEdit

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

    def _on_mouse_press(self, event):
        """Obsluha kliknutí na item."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.sample_selected.emit(self.sample)

    def refresh(self):
        """Obnoví zobrazení po změnách."""
        self._update_display()