"""
audio_player.py - Audio player s dedikovaným worker threadem pro MIDI tóny
"""

import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QLabel

from models import SampleMetadata
from midi_utils import MidiUtils
from audio_worker import get_audio_worker, AUDIO_AVAILABLE
import numpy as np

logger = logging.getLogger(__name__)

# Import audio knihoven pro sample playback
try:
    import sounddevice as sd
    import soundfile as sf
    SAMPLE_PLAYBACK_AVAILABLE = True
except ImportError as e:
    SAMPLE_PLAYBACK_AVAILABLE = False
    logger.warning(f"Sample playback not available: {e}")


class AudioPlayer(QGroupBox):
    """
    Audio přehrávač s dedikovaným worker threadem pro MIDI tóny.

    - MIDI tóny: přehrávány v separátním threadu (audio_worker)
    - Samples: přehrávány v main threadu (sounddevice)
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

        # NOVÉ: Audio worker pro MIDI tóny
        self.audio_worker = get_audio_worker()

        # Timer pro sledování přehrávání samples
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._check_playback_status)

        # Timer pro auto-stop (fallback pro samples)
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
        """
        Přehraje MIDI tón v dedikovaném worker threadu.

        NOVÁ IMPLEMENTACE: Používá AudioWorker pro izolované přehrávání.
        """
        if not AUDIO_AVAILABLE:
            logger.warning("Cannot play MIDI tone - audio not available")
            self.status_label.setText("Audio není k dispozici")
            return

        if not (21 <= midi_note <= 108):
            logger.warning(f"MIDI nota {midi_note} není v piano rozsahu")
            return

        # Callback pro update UI po dokončení
        def on_playback_complete(success, **kwargs):
            if success:
                midi_note = kwargs.get('midi_note')
                frequency = kwargs.get('frequency')
                note_name = MidiUtils.midi_to_note_name(midi_note)
                self.status_label.setText(f"✓ MIDI tón: {note_name} ({frequency:.1f} Hz)")
                self.playback_started.emit(f"MIDI {note_name}")
                logger.debug(f"MIDI tone {midi_note} playback completed")
            else:
                error = kwargs.get('error', 'Unknown error')
                self.status_label.setText(f"Chyba MIDI: {error}")
                self.playback_error.emit(error)
                logger.error(f"MIDI tone playback failed: {error}")

        # Pošli do audio worker threadu
        note_name = MidiUtils.midi_to_note_name(midi_note)
        self.status_label.setText(f"♪ Přehrává MIDI tón: {note_name}...")
        self.audio_worker.play_midi_tone(midi_note, callback=on_playback_complete)
        logger.debug(f"MIDI tone {midi_note} queued for playback in worker thread")

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
        # Stop sample playback
        self.stop_playback()
        if SAMPLE_PLAYBACK_AVAILABLE and hasattr(sd, 'stop'):
            try:
                sd.stop()
            except:
                pass

        # NOVÉ: Stop audio worker (MIDI tones)
        # Worker je singleton, bude stopnut při zavření aplikace
        # Zde jen stopneme aktuální přehrávání
        if self.audio_worker:
            self.audio_worker.stop_playback()

        logger.info("Audio player cleanup completed")