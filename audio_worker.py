"""
audio_worker.py - Dedikovaný audio worker thread s message queue pro sounddevice

Řeší problém blokování Qt event loop při přehrávání MIDI tónů.
Používá threading + queue.Queue pro asynchronní audio processing.
"""

import logging
import threading
import queue
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Audio knihovny
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError as e:
    AUDIO_AVAILABLE = False
    logger.warning(f"Audio libraries not available: {e}")


class AudioCommand(Enum):
    """Typy příkazů pro audio worker."""
    PLAY_TONE = "play_tone"
    PLAY_SAMPLE = "play_sample"
    STOP = "stop"
    SHUTDOWN = "shutdown"


@dataclass
class AudioTask:
    """Task pro audio worker."""
    command: AudioCommand
    data: dict
    callback: Optional[callable] = None


class AudioWorker:
    """
    Dedikovaný worker thread pro audio přehrávání.

    Běží v separátním threadu a zpracovává audio tasks z fronty.
    Zabraňuje blokování Qt event loop při přehrávání sounddevice.
    """

    def __init__(self):
        self.task_queue = queue.Queue(maxsize=10)
        self.worker_thread = None
        self.running = False
        self.is_playing = False

        # Current playback state
        self.current_stream = None
        self.auto_stop_event = threading.Event()

        if not AUDIO_AVAILABLE:
            logger.warning("AudioWorker initialized but audio libraries not available")

    def start(self):
        """Spustí worker thread."""
        if not AUDIO_AVAILABLE:
            logger.error("Cannot start AudioWorker - audio libraries not available")
            return False

        if self.running:
            logger.warning("AudioWorker already running")
            return True

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("✓ AudioWorker thread started")
        return True

    def stop(self):
        """Zastaví worker thread."""
        if not self.running:
            return

        logger.info("Stopping AudioWorker...")
        self.running = False

        # Pošli shutdown command
        try:
            self.task_queue.put(AudioTask(AudioCommand.SHUTDOWN, {}), timeout=1.0)
        except queue.Full:
            pass

        # Počkej na dokončení threadu
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)

        logger.info("✓ AudioWorker stopped")

    def play_midi_tone(self, midi_note: int, callback=None):
        """
        Přidá MIDI tón do fronty pro přehrání.

        Args:
            midi_note: MIDI nota (21-108)
            callback: Callback funkce volaná po dokončení (optional)
        """
        if not AUDIO_AVAILABLE:
            logger.warning("Cannot play MIDI tone - audio not available")
            if callback:
                callback(success=False, error="Audio not available")
            return

        task = AudioTask(
            command=AudioCommand.PLAY_TONE,
            data={'midi_note': midi_note},
            callback=callback
        )

        try:
            # Non-blocking put s timeoutem
            self.task_queue.put(task, timeout=0.1)
            logger.debug(f"MIDI tone {midi_note} queued for playback")
        except queue.Full:
            logger.warning(f"Audio queue full, dropping MIDI tone {midi_note}")
            if callback:
                callback(success=False, error="Queue full")

    def play_sample(self, filepath, callback=None):
        """
        Přidá audio sample do fronty pro přehrání.

        Args:
            filepath: Cesta k audio souboru
            callback: Callback funkce volaná po dokončení (optional)
        """
        if not AUDIO_AVAILABLE:
            logger.warning("Cannot play sample - audio not available")
            if callback:
                callback(success=False, error="Audio not available")
            return

        task = AudioTask(
            command=AudioCommand.PLAY_SAMPLE,
            data={'filepath': filepath},
            callback=callback
        )

        try:
            self.task_queue.put(task, timeout=0.1)
            logger.debug(f"Sample {filepath} queued for playback")
        except queue.Full:
            logger.warning(f"Audio queue full, dropping sample {filepath}")
            if callback:
                callback(success=False, error="Queue full")

    def stop_playback(self):
        """Okamžitě zastaví aktuální přehrávání."""
        task = AudioTask(
            command=AudioCommand.STOP,
            data={}
        )

        try:
            # Put na začátek fronty (priorita)
            # Nejdřív vyprázdni frontu
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                except queue.Empty:
                    break

            self.task_queue.put(task, timeout=0.1)
            logger.debug("Stop command queued")
        except queue.Full:
            logger.warning("Cannot queue stop command - queue full")

    def _worker_loop(self):
        """Hlavní smyčka worker threadu."""
        logger.info("AudioWorker loop started")

        while self.running:
            try:
                # Čekej na task s timeoutem
                task = self.task_queue.get(timeout=0.5)

                if task.command == AudioCommand.SHUTDOWN:
                    logger.info("Shutdown command received")
                    break

                elif task.command == AudioCommand.STOP:
                    self._handle_stop()

                elif task.command == AudioCommand.PLAY_TONE:
                    self._handle_play_tone(task)

                elif task.command == AudioCommand.PLAY_SAMPLE:
                    self._handle_play_sample(task)

                self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)

        # Cleanup při ukončení
        self._cleanup()
        logger.info("AudioWorker loop ended")

    def _handle_stop(self):
        """Zastaví aktuální přehrávání."""
        try:
            if self.is_playing:
                sd.stop()
                self.is_playing = False
                self.auto_stop_event.set()
                logger.debug("Playback stopped")
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    def _handle_play_tone(self, task: AudioTask):
        """Přehraje MIDI tón."""
        midi_note = task.data.get('midi_note')
        callback = task.callback

        try:
            # Zastaví předchozí přehrávání
            if self.is_playing:
                sd.stop()
                time.sleep(0.05)  # Krátká pauza pro uvolnění

            # Validace
            if not (21 <= midi_note <= 108):
                error = f"MIDI note {midi_note} out of range"
                logger.warning(error)
                if callback:
                    callback(success=False, error=error)
                return

            # Generuj tón
            sample_rate = 44100
            duration = 2.0
            frequency = 440.0 * (2 ** ((midi_note - 69) / 12))

            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = np.sin(2 * np.pi * frequency * t)

            # Envelope
            fade_samples = int(sample_rate * 0.05)
            if len(tone) > 2 * fade_samples:
                tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
                tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)

            tone *= 0.4  # Volume

            # Přehraj (blocking v worker threadu je OK!)
            self.is_playing = True
            sd.play(tone, sample_rate, blocking=True)  # BLOCKING je OK v worker threadu!
            self.is_playing = False

            logger.info(f"✓ MIDI tone {midi_note} ({frequency:.1f} Hz) played successfully")

            if callback:
                callback(success=True, midi_note=midi_note, frequency=frequency)

        except Exception as e:
            logger.error(f"Error playing MIDI tone {midi_note}: {e}", exc_info=True)
            self.is_playing = False
            if callback:
                callback(success=False, error=str(e))

    def _handle_play_sample(self, task: AudioTask):
        """Přehraje audio sample."""
        filepath = task.data.get('filepath')
        callback = task.callback

        try:
            # Zastaví předchozí přehrávání
            if self.is_playing:
                sd.stop()
                time.sleep(0.05)

            # Načti audio
            audio_data, sample_rate = sf.read(str(filepath))

            # Mono conversion
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Normalizace
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.7

            # Přehraj (blocking v worker threadu je OK!)
            self.is_playing = True
            sd.play(audio_data, sample_rate, blocking=True)
            self.is_playing = False

            logger.info(f"✓ Sample {filepath} played successfully")

            if callback:
                callback(success=True, filepath=filepath)

        except Exception as e:
            logger.error(f"Error playing sample {filepath}: {e}", exc_info=True)
            self.is_playing = False
            if callback:
                callback(success=False, error=str(e))

    def _cleanup(self):
        """Cleanup při ukončení workeru."""
        try:
            if self.is_playing:
                sd.stop()
                self.is_playing = False
        except:
            pass


# Globální singleton instance
_audio_worker_instance = None


def get_audio_worker() -> AudioWorker:
    """Vrátí globální AudioWorker instanci (singleton pattern)."""
    global _audio_worker_instance

    if _audio_worker_instance is None:
        _audio_worker_instance = AudioWorker()
        _audio_worker_instance.start()

    return _audio_worker_instance


def shutdown_audio_worker():
    """Ukončí globální AudioWorker."""
    global _audio_worker_instance

    if _audio_worker_instance is not None:
        _audio_worker_instance.stop()
        _audio_worker_instance = None
