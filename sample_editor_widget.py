"""
sample_editor_widget.py - MIDI editor s automatickým přehráváním transponovaných tónů
"""

from typing import Optional
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QSpinBox)  # Přidán QSpinBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import SampleMetadata
from midi_utils import MidiUtils


class SampleMidiEditor(QGroupBox):
    """MIDI editor pro úpravu parametrů sample s automatickým přehráváním tónů."""

    midi_note_changed = Signal(object, int, int)  # sample, old_midi, new_midi
    play_transposed_tone = Signal(int)  # midi_note - nový signál pro přehrání transponovaného tónu

    def __init__(self):
        super().__init__("MIDI Editor - Úprava parametrů sample")
        self.current_sample = None
        self.auto_play_enabled = True  # Povolení automatického přehrávání
        self.init_ui()

    def init_ui(self):
        """Inicializace MIDI editoru."""
        layout = QVBoxLayout()

        # Info o aktuálním sample
        self._create_sample_info_section(layout)

        # MIDI nota editor
        self._create_midi_editor_section(layout)

        # Amplitude info (nahradí velocity, protože velocity_level odebráno)
        self._create_amplitude_section(layout)

        # Auto-play kontrola
        self._create_autoplay_section(layout)

        self.setLayout(layout)
        self.setMaximumHeight(350)  # Zvětšeno pro větší prvky
        self._update_display()

    def _create_sample_info_section(self, layout):
        """Vytvoří sekci s informacemi o sample."""
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; }")
        info_layout = QVBoxLayout()

        self.sample_filename_label = QLabel("Žádný sample vybrán")
        self.sample_filename_label.setStyleSheet("font-weight: bold; color: #333; font-size: 13px;")
        info_layout.addWidget(self.sample_filename_label)

        self.sample_confidence_label = QLabel("")
        self.sample_confidence_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.sample_confidence_label)

        info_frame.setLayout(info_layout)
        layout.addWidget(info_frame)

    def _create_midi_editor_section(self, layout):
        """Vytvoří sekci pro úpravu MIDI noty."""
        midi_frame = QFrame()
        midi_frame.setStyleSheet("QFrame { background-color: #fff; border: 1px solid #dee2e6; border-radius: 5px; }")
        midi_layout = QVBoxLayout()

        # Nadpis s MIDI notou na stejném řádku
        title_layout = QHBoxLayout()

        midi_title = QLabel("MIDI Nota:")
        midi_title.setStyleSheet("font-weight: bold; color: #333; font-size: 18px;")
        title_layout.addWidget(midi_title)

        # MIDI nota přímo za nadpisem
        self.midi_display_label = QLabel("C4 (60)")
        self.midi_display_label.setStyleSheet("""
            QLabel {
                font-size: 18px; 
                font-weight: bold; 
                color: #2c3e50; 
                background-color: #ecf0f1; 
                padding: 8px 12px; 
                border-radius: 4px;
                border: 1px solid #bdc3c7;
                margin-left: 10px;
            }
        """)
        title_layout.addWidget(self.midi_display_label)
        title_layout.addStretch()

        midi_layout.addLayout(title_layout)
        midi_layout.addSpacing(15)

        # Tlačítka pro transpozici
        self._create_transpose_buttons(midi_layout)

        midi_frame.setLayout(midi_layout)
        layout.addWidget(midi_frame)

    def _create_transpose_buttons(self, layout):
        """Vytvoří tlačítka pro transpozici."""
        # Řádek 1: Půltóny
        semitone_layout = QHBoxLayout()

        btn_minus_1 = QPushButton("-1")
        btn_minus_1.clicked.connect(lambda: self._transpose(-1))
        btn_minus_1.setToolTip("Snížit o půltón")
        btn_minus_1.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; }")
        semitone_layout.addWidget(btn_minus_1)

        semitone_layout.addWidget(QLabel("půltón"))

        btn_plus_1 = QPushButton("+1")
        btn_plus_1.clicked.connect(lambda: self._transpose(1))
        btn_plus_1.setToolTip("Zvýšit o půltón")
        btn_plus_1.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        semitone_layout.addWidget(btn_plus_1)

        layout.addLayout(semitone_layout)

        # Řádek 2: Oktávy
        octave_layout = QHBoxLayout()

        btn_minus_12 = QPushButton("-12")
        btn_minus_12.clicked.connect(lambda: self._transpose(-12))
        btn_minus_12.setToolTip("Snížit o oktávu")
        btn_minus_12.setStyleSheet("QPushButton { background-color: #c0392b; color: white; font-weight: bold; }")
        octave_layout.addWidget(btn_minus_12)

        octave_layout.addWidget(QLabel("oktáva"))

        btn_plus_12 = QPushButton("+12")
        btn_plus_12.clicked.connect(lambda: self._transpose(12))
        btn_plus_12.setToolTip("Zvýšit o oktávu")
        btn_plus_12.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; font-weight: bold; }")
        octave_layout.addWidget(btn_plus_12)

        layout.addLayout(octave_layout)

        # Řádek 3: Ruční MIDI input
        manual_layout = QHBoxLayout()

        manual_label = QLabel("Ruční MIDI:")
        manual_label.setStyleSheet("font-weight: bold; color: #333;")
        manual_layout.addWidget(manual_label)

        self.midi_spinbox = QSpinBox()
        self.midi_spinbox.setMinimum(MidiUtils.PIANO_MIN_MIDI)
        self.midi_spinbox.setMaximum(MidiUtils.PIANO_MAX_MIDI)
        self.midi_spinbox.setValue(60)  # Default C4
        manual_layout.addWidget(self.midi_spinbox)

        btn_set_midi = QPushButton("Nastavit")
        btn_set_midi.clicked.connect(self._set_manual_midi)
        btn_set_midi.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        manual_layout.addWidget(btn_set_midi)

        layout.addLayout(manual_layout)

    def _create_amplitude_section(self, layout):
        """Vytvoří sekci pro zobrazení amplitude info (nahradí velocity)."""
        amplitude_frame = QFrame()
        amplitude_frame.setStyleSheet("QFrame { background-color: #fff; border: 1px solid #dee2e6; border-radius: 5px; }")
        amplitude_layout = QVBoxLayout()

        amplitude_title = QLabel("Amplitude RMS (500ms):")
        amplitude_title.setStyleSheet("font-weight: bold; color: #333; font-size: 18px;")
        amplitude_layout.addWidget(amplitude_title)

        self.amplitude_display_label = QLabel("--")
        self.amplitude_display_label.setStyleSheet("""
            QLabel {
                font-size: 18px; 
                font-weight: bold; 
                color: #2c3e50; 
                background-color: #ecf0f1; 
                padding: 8px 12px; 
                border-radius: 4px;
                border: 1px solid #bdc3c7;
                margin-left: 10px;
            }
        """)
        amplitude_layout.addWidget(self.amplitude_display_label)

        amplitude_frame.setLayout(amplitude_layout)
        layout.addWidget(amplitude_frame)

    def _create_autoplay_section(self, layout):
        """Vytvoří sekci pro auto-play."""
        autoplay_layout = QHBoxLayout()

        self.autoplay_button = QPushButton("Auto-přehrávání: ZAP")
        self.autoplay_button.clicked.connect(self._toggle_autoplay)
        self.autoplay_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db; 
                color: white; 
                font-weight: bold; 
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.autoplay_button.setToolTip("Zapne/vypne automatické přehrávání tónu při transpozici")
        autoplay_layout.addWidget(self.autoplay_button)

        autoplay_layout.addStretch()

        manual_play_button = QPushButton("Přehrát tón")
        manual_play_button.clicked.connect(self._manual_play_tone)
        manual_play_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6; 
                color: white; 
                font-weight: bold; 
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        manual_play_button.setToolTip("Ručně přehraje aktuální MIDI tón")
        autoplay_layout.addWidget(manual_play_button)

        layout.addLayout(autoplay_layout)

    def set_current_sample(self, sample: SampleMetadata):
        """Nastaví aktuální sample pro editaci."""
        self.current_sample = sample
        self._update_display()

    def _transpose(self, semitones: int):
        """Transponuje MIDI notu o zadaný počet půltónů."""
        if not self.current_sample:
            return

        old_midi = self.current_sample.detected_midi
        new_midi = old_midi + semitones

        # Omezit na piano rozsah
        new_midi = max(MidiUtils.PIANO_MIN_MIDI, min(MidiUtils.PIANO_MAX_MIDI, new_midi))

        if new_midi != old_midi:
            self._change_midi_note(old_midi, new_midi)

    def _change_midi_note(self, old_midi: int, new_midi: int):
        """Provede změnu MIDI noty a přehraje nový tón."""
        if not self.current_sample:
            return

        # Aktualizuj sample
        self.current_sample.detected_midi = new_midi

        # Aktualizuj UI
        self._update_display()

        # Přehraj nový tón pokud je auto-play zapnutý
        if self.auto_play_enabled:
            self.play_transposed_tone.emit(new_midi)

        # Emit signál o změně
        self.midi_note_changed.emit(self.current_sample, old_midi, new_midi)

    def _manual_play_tone(self):
        """Ručně přehraje aktuální MIDI tón."""
        if self.current_sample:
            self.play_transposed_tone.emit(self.current_sample.detected_midi)

    def _toggle_autoplay(self):
        """Přepne automatické přehrávání."""
        self.auto_play_enabled = not self.auto_play_enabled
        self._update_autoplay_button()

    def _update_autoplay_button(self):
        """Aktualizuje vzhled auto-play tlačítka."""
        if self.auto_play_enabled:
            self.autoplay_button.setText("Auto-přehrávání: ZAP")
            self.autoplay_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db; 
                    color: white; 
                    font-weight: bold; 
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
        else:
            self.autoplay_button.setText("Auto-přehrávání: VYP")
            self.autoplay_button.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6; 
                    color: white; 
                    font-weight: bold; 
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)

    def _update_display(self):
        """Aktualizuje zobrazení editoru."""
        if self.current_sample:
            # Aktualizace MIDI noty
            note_name = MidiUtils.midi_to_note_name(self.current_sample.detected_midi)
            midi_text = f"{note_name} ({self.current_sample.detected_midi})"

            print(f"Nastavuji MIDI text: '{midi_text}'")

            self.midi_display_label.setText(midi_text)

            # Nahrazení velocity RMS hodnotou (odebráno velocity_level)
            amplitude_text = f"{self.current_sample.velocity_amplitude:.6f}" if self.current_sample.velocity_amplitude is not None else "--"
            self.amplitude_display_label.setText(amplitude_text)

            self.sample_filename_label.setText(f"Sample: {self.current_sample.filename}")
            self.sample_confidence_label.setText(f"Pitch confidence: {self.current_sample.pitch_confidence:.2f}")

            self.setEnabled(True)
        else:
            print("Žádný sample není vybrán")
            self.midi_display_label.setText("--")
            self.amplitude_display_label.setText("--")
            self.sample_filename_label.setText("Žádný sample vybrán")
            self.sample_confidence_label.setText("")
            self.setEnabled(False)

        self._update_autoplay_button()

    def _set_manual_midi(self):
        """Nastaví ručně zadanou MIDI notu."""
        if not self.current_sample:
            return

        old_midi = self.current_sample.detected_midi
        new_midi = self.midi_spinbox.value()

        if new_midi != old_midi:
            self._change_midi_note(old_midi, new_midi)