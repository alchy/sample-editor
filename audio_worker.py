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

# MIDI knihovna (preferovaná pro playback)
try:
    import mido
    MIDI_AVAILABLE = True
    logger.info("✓ mido MIDI library available")
except ImportError:
    MIDI_AVAILABLE = False
    logger.info("mido not available - will use audio tone fallback")


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

        # MIDI port management
        self.midi_port = None
        self.midi_available_ports = []
        self._setup_midi()

        if not AUDIO_AVAILABLE and not MIDI_AVAILABLE:
            logger.warning("AudioWorker initialized but no audio/MIDI libraries available")

    def _setup_midi(self):
        """Nastaví MIDI output port (preferovaná metoda pro playback)."""
        if not MIDI_AVAILABLE:
            return

        try:
            self.midi_available_ports = mido.get_output_names()
            if self.midi_available_ports:
                # Zkus otevřít první dostupný port
                self.midi_port = mido.open_output(self.midi_available_ports[0])
                logger.info(f"✓ MIDI port opened: {self.midi_available_ports[0]}")
                logger.info(f"  Available ports: {self.midi_available_ports}")
            else:
                logger.info("No MIDI ports available - will use audio tone fallback")
        except Exception as e:
            logger.warning(f"Could not open MIDI port: {e} - will use audio tone fallback")
            self.midi_port = None

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
        """
        Přehraje MIDI tón - preferuje MIDI port přes mido, fallback na audio tón.

        Metoda 1 (preferovaná): Pošli MIDI message přes mido port
        Metoda 2 (fallback): Generuj sinusový tón přes sounddevice
        """
        midi_note = task.data.get('midi_note')
        callback = task.callback

        # Validace
        if not (21 <= midi_note <= 108):
            error = f"MIDI note {midi_note} out of range"
            logger.warning(error)
            if callback:
                callback(success=False, error=error)
            return

        # METODA 1: MIDI přes mido (PREFEROVANÁ - nejvíce spolehlivá!)
        if self.midi_port:
            try:
                self._play_midi_via_port(midi_note, callback)
                return
            except Exception as e:
                logger.warning(f"MIDI port playback failed: {e}, falling back to audio tone")
                # Fallback na metodu 2

        # METODA 2: Audio tón přes sounddevice (fallback)
        if AUDIO_AVAILABLE:
            try:
                self._play_audio_tone(midi_note, callback)
                return
            except Exception as e:
                logger.error(f"Audio tone playback failed: {e}", exc_info=True)
                if callback:
                    callback(success=False, error=str(e))
        else:
            error = "No playback method available (no MIDI port, no audio)"
            logger.error(error)
            if callback:
                callback(success=False, error=error)

    def _play_midi_via_port(self, midi_note: int, callback=None):
        """Přehraje MIDI notu přes mido port (NEJSPOLEHLIVĚJŠÍ METODA)."""
        velocity = 80  # Standard velocity
        duration = 1.0  # 1 sekunda

        # Send note_on
        msg_on = mido.Message('note_on', note=midi_note, velocity=velocity)
        self.midi_port.send(msg_on)
        self.is_playing = True

        logger.debug(f"MIDI note_on: {midi_note}, velocity={velocity}")

        # Wait for duration
        time.sleep(duration)

        # Send note_off
        msg_off = mido.Message('note_off', note=midi_note, velocity=0)
        self.midi_port.send(msg_off)
        self.is_playing = False

        frequency = 440.0 * (2 ** ((midi_note - 69) / 12))
        logger.info(f"✓ MIDI note {midi_note} ({frequency:.1f} Hz) played via MIDI port")

        if callback:
            callback(success=True, midi_note=midi_note, frequency=frequency, method="MIDI")

    def _play_audio_tone(self, midi_note: int, callback=None):
        """Přehraje audio tón přes sounddevice (fallback metoda)."""
        # Zastaví předchozí přehrávání
        if self.is_playing:
            sd.stop()
            time.sleep(0.05)

        # Generuj tón
        sample_rate = 44100
        duration = 1.0  # Zkráceno z 2.0 na 1.0 pro rychlejší response
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
        sd.play(tone, sample_rate, blocking=True)
        self.is_playing = False

        logger.info(f"✓ MIDI tone {midi_note} ({frequency:.1f} Hz) played via audio")

        if callback:
            callback(success=True, midi_note=midi_note, frequency=frequency, method="Audio")

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
        # Stop audio playback
        try:
            if self.is_playing and AUDIO_AVAILABLE:
                sd.stop()
                self.is_playing = False
        except:
            pass

        # Close MIDI port
        if self.midi_port:
            try:
                # Send all notes off
                all_notes_off = mido.Message('control_change', control=123, value=0)
                self.midi_port.send(all_notes_off)
                self.midi_port.close()
                logger.info("✓ MIDI port closed")
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
