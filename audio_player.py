"""
audio_player.py - Konsolidovaná finální verze audio playeru
"""

import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QLabel

from models import SampleMetadata
from midi_utils import MidiUtils
import numpy as np

logger = logging.getLogger(__name__)

# Import audio knihoven podle funkční verze
try:
    import sounddevice as sd
    import soundfile as sf

    AUDIO_AVAILABLE = True
    logger.info("Audio knihovny načteny úspěšně (sounddevice + soundfile)")
except ImportError as e:
    AUDIO_AVAILABLE = False
    logger.warning(f"Audio knihovny nejsou k dispozici: {e}")


class AudioPlayer(QGroupBox):
    """
    Audio přehrávač pro samples s podporou klávesových zkratek - KONSOLIDOVANÁ VERZE
    Založeno na funkční implementaci se sounddevice
    """

    playback_started = Signal(str)  # filename
    playback_stopped = Signal()
    playback_error = Signal(str)  # error message
    status_changed = Signal(int)  # compatibility

    def __init__(self):
        super().__init__("Audio Player")
        self.current_sample: Optional[SampleMetadata] = None
        self.is_playing = False
        self.is_comparing = False
        self.audio_data = None
        self.sample_rate = None

        # Timer pro sledování přehrávání
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._check_playback_status)

        # Timer pro auto-stop (fallback)
        self.auto_stop_timer = QTimer()
        self.auto_stop_timer.setSingleShot(True)
        self.auto_stop_timer.timeout.connect(self.force_stop)

        self.init_ui()

        if not AUDIO_AVAILABLE:
            logger.warning("Audio přehrávač není k dispozici - chybí sounddevice nebo soundfile")

    def init_ui(self):
        """Inicializuje UI komponenty."""
        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Audio připraven" if AUDIO_AVAILABLE else "Audio není k dispozici")
        layout.addWidget(self.status_label)

        # Control buttons
        button_layout = QVBoxLayout()

        self.play_button = QPushButton("Přehrát (Mezerník)")
        self.play_button.clicked.connect(self.play_current_sample)
        self.play_button.setEnabled(False)
        button_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop (ESC)")
        self.stop_button.clicked.connect(self.stop_playback)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setMaximumHeight(150)

    def set_current_sample(self, sample: SampleMetadata):
        """Nastaví aktuální sample pro přehrávání."""
        self.current_sample = sample
        self.play_button.setEnabled(sample is not None and AUDIO_AVAILABLE)
        if sample:
            self.status_label.setText(f"Nastaven: {sample.filename}")
        else:
            self.status_label.setText("Žádný sample vybrán")
        logger.debug(f"Nastaven sample: {sample.filename if sample else 'None'}")

    def play_current_sample(self):
        """Přehraje aktuálně vybraný sample."""
        if not AUDIO_AVAILABLE:
            self.status_label.setText("Audio knihovny nejsou k dispozici")
            return

        if not self.current_sample:
            self.status_label.setText("Žádný sample není vybrán")
            return

        # Zastaví předchozí přehrávání bez duplicitního spuštění
        if self.is_playing or self.is_comparing:
            self.stop_playback()
            # Krátké zpoždění pro čisté zastavení
            QTimer.singleShot(50, self._delayed_play_current)
            return

        self._delayed_play_current()

    def _delayed_play_current(self):
        """Zpožděné spuštění přehrávání pro čisté zastavení."""
        try:
            self._load_and_play_sample(self.current_sample)
        except Exception as e:
            logger.error(f"Chyba při přehrávání {self.current_sample.filename}: {e}")
            self.status_label.setText(f"Chyba: {e}")

    def play_sample(self, sample: SampleMetadata):
        """Přehraje konkrétní sample."""
        logger.debug(f"Play sample request: {sample.filename}")
        self.set_current_sample(sample)
        self.play_current_sample()

    def play_midi_tone(self, midi_note: int):
        """Přehraje MIDI tón pomocí sounddevice."""
        if not AUDIO_AVAILABLE:
            logger.warning("Cannot play MIDI tone - audio not available")
            return

        if not (21 <= midi_note <= 108):  # Piano rozsah
            logger.warning(f"MIDI nota {midi_note} není v piano rozsahu")
            return

        # Zastaví současné přehrávání
        self.stop_playback()

        try:
            # Generuj čistý sinusový tón
            sample_rate = 44100
            duration = 2.0  # 2 sekundy
            frequency = 440.0 * (2 ** ((midi_note - 69) / 12))

            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = np.sin(2 * np.pi * frequency * t)

            # Envelope pro plynulý začátek a konec
            fade_samples = int(sample_rate * 0.05)  # 50ms fade
            if len(tone) > 2 * fade_samples:
                tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
                tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)

            # Snížit hlasitost
            tone *= 0.4

            # Přehraj
            sd.play(tone, sample_rate)
            self.is_playing = True
            self.stop_button.setEnabled(True)

            # Auto-stop timer
            self.auto_stop_timer.start(int(duration * 1000) + 100)

            note_name = MidiUtils.midi_to_note_name(midi_note)
            self.status_label.setText(f"♪ Přehrává MIDI tón: {note_name} ({frequency:.1f} Hz)")
            self.playback_started.emit(f"MIDI {note_name}")

            logger.info(f"Přehrán MIDI tón: {note_name} (MIDI {midi_note}, {frequency:.1f} Hz)")

        except Exception as e:
            logger.error(f"Chyba při přehrávání MIDI tónu {midi_note}: {e}")
            self.status_label.setText(f"Chyba MIDI tónu: {e}")

    def play_transposed_tone(self, midi_note: int):
        """Přehraje transponovaný MIDI tón."""
        self.play_midi_tone(midi_note)

    def stop_playback(self):
        """Zastaví přehrávání."""
        if self.is_playing or self.is_comparing:
            try:
                sd.stop()
                self.is_playing = False
                self.is_comparing = False
                self.playback_timer.stop()
                self.auto_stop_timer.stop()
                self.stop_button.setEnabled(False)
                self.status_label.setText("Zastaveno")
                self.playback_stopped.emit()
                logger.debug("Přehrávání zastaveno")
            except Exception as e:
                logger.error(f"Chyba při zastavování: {e}")

    def force_stop(self):
        """Force stop pro auto-stop timer."""
        logger.debug("Auto-stopping playback")
        self.stop_playback()

    def compare_play(self, sample: SampleMetadata):
        """Srovnávací přehrávání."""
        logger.info(f"Compare play: {sample.filename}")
        self.play_sample(sample)  # Pro jednoduchost stejné jako play

    def simultaneous_play(self, sample: SampleMetadata):
        """Současné přehrávání."""
        logger.info(f"Simultaneous play: {sample.filename}")
        self.play_sample(sample)  # Pro jednoduchost stejné jako play

    def _load_and_play_sample(self, sample: SampleMetadata):
        """Načte a přehraje sample pomocí sounddevice."""
        if not sample.filepath.exists():
            raise FileNotFoundError(f"Soubor neexistuje: {sample.filepath}")

        # Načti audio data
        audio_data, sample_rate = sf.read(str(sample.filepath))

        # Konverze na mono pokud je stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Normalizace hlasitosti
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data)) * 0.7  # 70% max volume

        self.audio_data = audio_data
        self.sample_rate = sample_rate

        # Přehraj pouze jednou
        sd.play(audio_data, sample_rate)
        self.is_playing = True
        self.stop_button.setEnabled(True)

        # Auto-stop timer
        duration_ms = int(len(audio_data) / sample_rate * 1000) + 100
        self.auto_stop_timer.start(duration_ms)

        self.status_label.setText(f"▶ Přehrává: {sample.filename}")
        self.playback_started.emit(sample.filename)
        logger.info(f"Přehrávání spuštěno: {sample.filename} ({len(audio_data) / sample_rate:.1f}s)")

    def _check_playback_status(self):
        """Kontroluje stav přehrávání."""
        try:
            if (self.is_playing or self.is_comparing):
                # Kontrola zda sounddevice skutečně přehrává
                if hasattr(sd, 'get_stream') and sd.get_stream() and not sd.get_stream().active:
                    self.stop_playback()
                elif not hasattr(sd, 'get_stream'):
                    # Fallback pro starší verze sounddevice
                    pass
        except Exception as e:
            logger.debug(f"Error checking playback status: {e}")

    def cleanup(self):
        """Cleanup method for proper shutdown."""
        self.stop_playback()
        if hasattr(sd, 'stop'):
            try:
                sd.stop()
            except:
                pass
        logger.info("Audio player cleanup completed")