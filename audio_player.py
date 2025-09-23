"""
audio_player.py - Komponenta pro přehrávání audio sampleů
"""

import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox

from models import SampleMetadata
from midi_utils import MidiUtils  # Přidaný import

logger = logging.getLogger(__name__)

# Import audio knihoven
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    AUDIO_AVAILABLE = True
    logger.info("Audio knihovny načteny úspěšně")
except ImportError as e:
    AUDIO_AVAILABLE = False
    logger.warning(f"Audio knihovny nejsou k dispozici: {e}")


class AudioPlayer(QObject):
    """Audio přehrávač pro samples s podporou klávesových zkratek"""

    playback_started = Signal(str)    # filename
    playback_stopped = Signal()
    playback_error = Signal(str)      # error message
    compare_started = Signal(str)     # filename - nový signál pro srovnávací přehrávání

    def __init__(self):
        super().__init__()
        self.current_sample: Optional[SampleMetadata] = None
        self.is_playing = False
        self.is_comparing = False  # Nový flag pro srovnávací přehrávání
        self.audio_data = None
        self.sample_rate = None

        # Timer pro sledování přehrávání
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._check_playback_status)

        # Timer pro srovnávací přehrávání
        self.compare_timer = QTimer()
        self.compare_timer.timeout.connect(self._continue_compare_playback)

        if not AUDIO_AVAILABLE:
            logger.warning("Audio přehrávač není k dispozici - chybí sounddevice nebo soundfile")

    def set_current_sample(self, sample: SampleMetadata):
        """Nastaví aktuální sample pro přehrávání"""
        self.current_sample = sample
        logger.debug(f"Nastaven sample pro přehrávání: {sample.filename}")

    def play_current_sample(self):
        """Přehraje aktuálně vybraný sample"""
        if not AUDIO_AVAILABLE:
            self.playback_error.emit("Audio knihovny nejsou k dispozici")
            return

        if not self.current_sample:
            self.playback_error.emit("Žádný sample není vybrán")
            return

        if self.is_playing or self.is_comparing:
            self.stop_playback()
            return

        try:
            self._load_and_play_sample(self.current_sample)
        except Exception as e:
            logger.error(f"Chyba při přehrávání {self.current_sample.filename}: {e}")
            self.playback_error.emit(f"Chyba přehrávání: {e}")

    def play_sample(self, sample: SampleMetadata):
        """Přehraje konkrétní sample"""
        self.set_current_sample(sample)
        self.play_current_sample()

    def compare_sample(self, sample: SampleMetadata):
        """Srovnávací přehrávání: sine tón + pauza + sample"""
        if not AUDIO_AVAILABLE:
            self.playback_error.emit("Audio knihovny nejsou k dispozici")
            return

        if self.is_playing or self.is_comparing:
            self.stop_playback()
            return

        try:
            self._start_compare_playback(sample)
        except Exception as e:
            logger.error(f"Chyba při srovnávacím přehrávání {sample.filename}: {e}")
            self.playback_error.emit(f"Chyba srovnávacího přehrávání: {e}")

    def compare_sample_simultaneous(self, sample: SampleMetadata):
        """Současné přehrávání: sine tón + sample najednou"""
        if not AUDIO_AVAILABLE:
            self.playback_error.emit("Audio knihovny nejsou k dispozici")
            return

        if self.is_playing or self.is_comparing:
            self.stop_playback()
            return

        try:
            self._start_simultaneous_playback(sample)
        except Exception as e:
            logger.error(f"Chyba při současném přehrávání {sample.filename}: {e}")
            self.playback_error.emit(f"Chyba současného přehrávání: {e}")

    def _start_simultaneous_playback(self, sample: SampleMetadata):
        """Spustí současné přehrávání - sine tón + sample současně"""
        self.current_sample = sample
        self.is_comparing = True

        # Načti sample
        audio_data, sample_rate = sf.read(str(sample.filepath))

        # Konverze na mono pokud je stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Generuj sine tón pro detekovanou frekvenci
        frequency = sample.detected_frequency
        sample_duration = len(audio_data) / sample_rate

        # Sine tón stejné délky jako sample
        t = np.linspace(0, sample_duration, len(audio_data))
        tone = np.sin(2 * np.pi * frequency * t)

        # Envelope pro plynulý začátek a konec
        fade_samples = int(sample_rate * 0.05)  # 50ms fade
        if len(tone) > 2 * fade_samples:
            tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
            tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        # Mix sine tónu a sample (50:50)
        tone *= 0.3  # Snížit hlasitość sine tónu
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.5 if np.max(np.abs(audio_data)) > 0 else audio_data

        mixed_audio = tone + audio_data

        # Normalizace aby nedošlo k clippingu
        if np.max(np.abs(mixed_audio)) > 0:
            mixed_audio = mixed_audio / np.max(np.abs(mixed_audio)) * 0.8

        # Přehraj mix
        sd.play(mixed_audio, sample_rate)

        # Nastav timer pro ukončení
        duration_ms = int(sample_duration * 1000) + 100
        self.playback_timer.start(duration_ms)

        note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
        self.compare_started.emit(f"{sample.filename} | Současně: {note_name} ({frequency:.1f} Hz) + sample")

        logger.info(f"Současné přehrávání spuštěno: sine {frequency:.1f} Hz + {sample.filename}")

    def _start_compare_playback(self, sample: SampleMetadata):
        """Spustí srovnávací přehrávání - fáze 1: sine tón"""
        self.current_sample = sample
        self.is_comparing = True

        # Generuj sine tón pro detekovanou frekvenci
        frequency = sample.detected_frequency
        duration = 2.0  # 2 sekundy
        sample_rate = 44100

        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * frequency * t)

        # Envelope pro plynulý začátek a konec
        fade_samples = int(sample_rate * 0.05)  # 50ms fade
        if len(tone) > 2 * fade_samples:
            tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
            tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        # Snížit hlasitost
        tone *= 0.4

        # Přehraj sine tón
        sd.play(tone, sample_rate)

        # Nastav timer pro pokračování (2s tón + 250ms pauza)
        self.compare_timer.start(2250)  # 2000ms + 250ms

        note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
        self.compare_started.emit(f"{sample.filename} | Sine tón: {note_name} ({frequency:.1f} Hz)")

        logger.info(f"Srovnávací přehrávání spuštěno: sine tón {frequency:.1f} Hz pro {sample.filename}")

    def _continue_compare_playback(self):
        """Pokračuje srovnávacím přehráváním - fáze 2: sample"""
        self.compare_timer.stop()

        if not self.current_sample or not self.is_comparing:
            return

        try:
            # Zastaví případné přehrávání sine tónu
            sd.stop()

            # Načti a přehraj sample
            audio_data, sample_rate = sf.read(str(self.current_sample.filepath))

            # Konverze na mono pokud je stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Normalizace hlasitosti
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.7

            # Přehraj sample
            sd.play(audio_data, sample_rate)

            # Nastav timer pro ukončení
            duration_ms = int(len(audio_data) / sample_rate * 1000) + 100
            self.playback_timer.start(duration_ms)

            self.playback_started.emit(f"Sample: {self.current_sample.filename}")

        except Exception as e:
            logger.error(f"Chyba při přehrávání sample v compare módu: {e}")
            self.is_comparing = False
            self.playback_error.emit(f"Chyba při přehrávání sample: {e}")

    def stop_playback(self):
        """Zastaví přehrávání"""
        if self.is_playing or self.is_comparing:
            try:
                sd.stop()
                self.is_playing = False
                self.is_comparing = False
                self.playback_timer.stop()
                self.compare_timer.stop()
                self.playback_stopped.emit()
                logger.debug("Přehrávání zastaveno")
            except Exception as e:
                logger.error(f"Chyba při zastavování přehrávání: {e}")

    def _load_and_play_sample(self, sample: SampleMetadata):
        """Načte a přehraje sample"""
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

        # Spusť přehrávání
        sd.play(audio_data, sample_rate)
        self.is_playing = True

        # Spusť timer pro sledování
        duration_ms = int(len(audio_data) / sample_rate * 1000) + 100  # +100ms buffer
        self.playback_timer.start(duration_ms)

        self.playback_started.emit(sample.filename)
        logger.info(f"Přehrávání spuštěno: {sample.filename} ({len(audio_data)/sample_rate:.1f}s)")

    def _check_playback_status(self):
        """Kontroluje stav přehrávání"""
        if (self.is_playing or self.is_comparing) and not sd.get_stream().active:
            self.is_playing = False
            self.is_comparing = False
            self.playback_timer.stop()
            self.playback_stopped.emit()
            logger.debug("Přehrávání dokončeno")

    def get_playback_info(self) -> dict:
        """Vrátí informace o aktuálním přehrávání"""
        return {
            'is_playing': self.is_playing,
            'is_comparing': self.is_comparing,
            'current_sample': self.current_sample.filename if self.current_sample else None,
            'audio_available': AUDIO_AVAILABLE
        }


class ReferencePlayer(QObject):
    """Přehrávač referenčních tónů pro MIDI noty"""

    tone_played = Signal(int)  # MIDI note

    def __init__(self):
        super().__init__()
        self.is_playing = False

    def play_midi_note(self, midi_note: int, duration: float = 1.0):
        """Přehraje čistý tón pro MIDI notu"""
        if not AUDIO_AVAILABLE:
            return

        if not (21 <= midi_note <= 108):  # Piano rozsah
            logger.warning(f"MIDI nota {midi_note} není v piano rozsahu")
            return

        try:
            # Generuj čistý sinusový tón
            sample_rate = 44100
            frequency = 440.0 * (2 ** ((midi_note - 69) / 12))

            t = np.linspace(0, duration, int(sample_rate * duration))

            # Sinusový tón s envelope (fade in/out)
            tone = np.sin(2 * np.pi * frequency * t)

            # Envelope pro plynulý začátek a konec
            fade_samples = int(sample_rate * 0.05)  # 50ms fade
            if len(tone) > 2 * fade_samples:
                # Fade in
                tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
                # Fade out
                tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)

            # Snížit hlasitost
            tone *= 0.3

            # Přehraj
            sd.play(tone, sample_rate)
            self.tone_played.emit(midi_note)

            logger.debug(f"Přehrán referenční tón: MIDI {midi_note} ({frequency:.1f} Hz)")

        except Exception as e:
            logger.error(f"Chyba při přehrávání referenčního tónu: {e}")


class AudioPlayerStatus(QObject):
    """Status indikátor pro audio přehrávání"""

    def __init__(self, player: AudioPlayer):
        super().__init__()
        self.player = player
        self.status_message = "Audio připraven"

        # Připoj signály
        self.player.playback_started.connect(self._on_playback_started)
        self.player.playback_stopped.connect(self._on_playback_stopped)
        self.player.playback_error.connect(self._on_playback_error)

    def _on_playback_started(self, filename: str):
        """Obsluha spuštění přehrávání"""
        self.status_message = f"▶ Přehrává: {filename}"

    def _on_playback_stopped(self):
        """Obsluha zastavení přehrávání"""
        self.status_message = "⏹ Přehrávání zastaveno"

    def _on_playback_error(self, error: str):
        """Obsluha chyby přehrávání"""
        self.status_message = f"❌ Chyba: {error}"

    def get_status(self) -> str:
        """Vrátí aktuální status"""
        return self.status_message


def show_audio_requirements_dialog():
    """Zobrazí dialog s požadavky na audio knihovny"""
    msg = QMessageBox()
    msg.setWindowTitle("Audio knihovny")
    msg.setIcon(QMessageBox.Information)

    if AUDIO_AVAILABLE:
        msg.setText("Audio knihovny jsou k dispozici")
        msg.setInformativeText("Můžete přehrávat samples pomocí mezerníku")
    else:
        msg.setText("Audio knihovny nejsou k dispozici")
        msg.setInformativeText(
            "Pro přehrávání samples nainstalujte:\n\n"
            "pip install sounddevice soundfile\n\n"
            "Pak restartujte aplikaci."
        )

    msg.exec()