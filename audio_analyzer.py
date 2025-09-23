"""
audio_analyzer.py - Worker thread pro batch analýzu s CREPE a amplitude detekci
"""

import sys
from pathlib import Path
from typing import List
import logging
import numpy as np
from PySide6.QtCore import QThread, Signal

from models import SampleMetadata, AnalysisProgress
from pitch_detector import PitchDetector

# Debug import pro amplitude_analyzer
try:
    from amplitude_analyzer import AmplitudeAnalyzer, AmplitudeRangeManager
    logger = logging.getLogger(__name__)
    logger.info("Successfully imported AmplitudeAnalyzer and AmplitudeRangeManager")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import from amplitude_analyzer: {e}")

    # Vytvoříme mock třídy pro fallback
    class AmplitudeAnalyzer:
        def __init__(self, window_ms=10.0):
            self.window_ms = window_ms

        def analyze_peak_amplitude(self, waveform, sr):
            # Fallback implementace
            if len(waveform.shape) > 1:
                audio = np.mean(waveform, axis=1)
            else:
                audio = waveform.copy()

            velocity_amplitude = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0

            return {
                'velocity_amplitude': velocity_amplitude,
                'velocity_amplitude_db': 20 * np.log10(velocity_amplitude) if velocity_amplitude > 1e-10 else -np.inf,
                'velocity_duration_ms': 500.0,
                'peak_amplitude': float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0,
                'peak_amplitude_db': -60.0,
                'rms_amplitude': velocity_amplitude,
                'rms_amplitude_db': -60.0,
                'peak_position': int(np.argmax(np.abs(audio))) if len(audio) > 0 else 0,
                'peak_position_seconds': 0.0,
                'window_ms': self.window_ms,
                'analysis_windows': 1
            }

        def analyze_attack_envelope(self, waveform, sr):
            return {'attack_peak': 0.0, 'attack_time': 0.0, 'attack_slope': 0.0}

    class AmplitudeRangeManager:
        def __init__(self):
            self.global_min = None
            self.global_max = None
            self.all_velocity_values = []  # Změna: velocity values

        def add_sample_amplitude(self, velocity_amplitude):
            if velocity_amplitude > 0:
                self.all_velocity_values.append(velocity_amplitude)
                if self.global_min is None or velocity_amplitude < self.global_min:
                    self.global_min = velocity_amplitude
                if self.global_max is None or velocity_amplitude > self.global_max:
                    self.global_max = velocity_amplitude

        def get_range_info(self):
            if not self.all_velocity_values:
                return {'min': 0.0, 'max': 1.0, 'count': 0, 'mean': 0.0, 'std': 0.0, 'percentile_5': 0.0, 'percentile_95': 1.0}

            values = np.array(self.all_velocity_values)
            return {
                'min': float(self.global_min) if self.global_min else 0.0,
                'max': float(self.global_max) if self.global_max else 1.0,
                'count': len(self.all_velocity_values),
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'percentile_5': float(np.percentile(values, 5)),
                'percentile_95': float(np.percentile(values, 95))
            }

        def reset(self):
            self.global_min = None
            self.global_max = None
            self.all_velocity_values.clear()

logger = logging.getLogger(__name__)

# Audio knihovny
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available")


class BatchAnalyzer(QThread):
    """Worker thread pro batch analýzu s pitch a amplitude detekci"""

    progress_updated = Signal(int, str)  # progress percentage, message
    analysis_completed = Signal(list, dict)  # list of SampleMetadata, amplitude range info

    def __init__(self, input_folder: Path):
        super().__init__()
        self.input_folder = input_folder
        self.samples = []
        self.supported_extensions = ['*.wav', '*.WAV', '*.flac', '*.FLAC', '*.aiff', '*.AIFF', '*.mp3', '*.MP3']

        # Analyzátory
        self.pitch_detector = PitchDetector()
        self.amplitude_analyzer = AmplitudeAnalyzer(window_ms=10.0)
        self.amplitude_range_manager = AmplitudeRangeManager()

        # Progress tracking
        self.progress = None

    def run(self):
        """Spustí batch analýzu"""
        try:
            # Najdi audio soubory
            audio_files = []
            for ext in self.supported_extensions:
                audio_files.extend(list(self.input_folder.glob(ext)))

            if not audio_files:
                self.progress_updated.emit(0, "Žádné audio soubory nenalezeny")
                self.analysis_completed.emit([], {})
                return

            # Inicializace progress
            self.progress = AnalysisProgress(len(audio_files))
            self.progress_updated.emit(0, f"Nalezeno {len(audio_files)} audio souborů")

            # Reset amplitude range manager
            self.amplitude_range_manager.reset()

            self.samples = []

            for i, filepath in enumerate(audio_files):
                try:
                    # Aktualizace progress
                    self.progress.update(filepath.name)
                    progress_percent = self.progress.get_progress_percent()
                    self.progress_updated.emit(progress_percent, self.progress.get_status_message())

                    # Analyzuj sample
                    sample = self._analyze_single_sample(filepath)

                    if sample:
                        self.samples.append(sample)

                        # ZMĚNA: Přidej VELOCITY AMPLITUDE do range manageru místo peak_amplitude
                        if sample.velocity_amplitude is not None:
                            self.amplitude_range_manager.add_sample_amplitude(sample.velocity_amplitude)

                except Exception as e:
                    error_msg = f"Error analyzing {filepath.name}: {str(e)}"
                    logger.error(error_msg)
                    self.progress.add_error(filepath.name, str(e))

            # Finální progress update
            final_message = self.progress.get_status_message()
            self.progress_updated.emit(100, final_message)

            # Získej amplitude range info
            range_info = self.amplitude_range_manager.get_range_info()

            logger.info(f"Analysis completed: {len(self.samples)} samples successfully analyzed")
            logger.info(f"Velocity amplitude range: {range_info['min']:.6f} - {range_info['max']:.6f}")

            # Emit výsledky
            self.analysis_completed.emit(self.samples, range_info)

        except Exception as e:
            logger.error(f"Chyba při batch analýze: {e}")
            self.analysis_completed.emit([], {})

    def _analyze_single_sample(self, filepath: Path) -> SampleMetadata:
        """Analyzuje jeden sample - pitch + amplitude"""
        sample = SampleMetadata(filepath)

        try:
            # Načti audio soubor
            waveform, sr = self._load_audio_file(filepath)

            if waveform is None or len(waveform) == 0:
                logger.warning(f"Could not load audio from {filepath}")
                return None

            # Základní audio info
            sample.sample_rate = sr
            sample.channels = waveform.shape[1] if len(waveform.shape) > 1 else 1
            sample.duration = len(waveform) / sr

            logger.debug(f"Loaded audio: {sample.filename}, "
                        f"duration: {sample.duration:.2f}s, "
                        f"sr: {sr}, channels: {sample.channels}")

            # Pitch detekce
            pitch_result = self.pitch_detector.detect_pitch(waveform, sr)

            sample.detected_frequency = pitch_result.get('frequency')
            sample.detected_midi = pitch_result.get('midi_note')
            sample.pitch_confidence = pitch_result.get('confidence', 0.0)
            sample.pitch_method = pitch_result.get('method', 'unknown')

            # Amplitude analýza - nová RMS approach
            amplitude_result = self.amplitude_analyzer.analyze_peak_amplitude(waveform, sr)

            # HLAVNÍ HODNOTA PRO VELOCITY - RMS prvních 500ms
            sample.velocity_amplitude = amplitude_result.get('velocity_amplitude')
            sample.velocity_amplitude_db = amplitude_result.get('velocity_amplitude_db')
            sample.velocity_duration_ms = amplitude_result.get('velocity_duration_ms')

            # LEGACY HODNOTY (pro kompatibilitu a debug)
            sample.peak_amplitude = amplitude_result.get('peak_amplitude')
            sample.peak_amplitude_db = amplitude_result.get('peak_amplitude_db')
            sample.rms_amplitude = amplitude_result.get('rms_amplitude')
            sample.rms_amplitude_db = amplitude_result.get('rms_amplitude_db')
            sample.peak_position = amplitude_result.get('peak_position')
            sample.peak_position_seconds = amplitude_result.get('peak_position_seconds')

            # Attack envelope analýza
            attack_result = self.amplitude_analyzer.analyze_attack_envelope(waveform, sr)
            sample.attack_peak = attack_result.get('attack_peak')
            sample.attack_time = attack_result.get('attack_time')
            sample.attack_slope = attack_result.get('attack_slope')

            # Označ jako analyzovaný
            sample.analyzed = True

            # Log výsledků - ZMĚNA: používej velocity_amplitude
            pitch_info = f"MIDI {sample.detected_midi}" if sample.detected_midi else "No pitch"
            velocity_info = f"RMS-500ms: {sample.velocity_amplitude:.6f}" if sample.velocity_amplitude else "No velocity amplitude"

            logger.info(f"✓ {sample.filename}: {pitch_info}, {velocity_info} "
                       f"[{sample.pitch_method}, conf: {sample.pitch_confidence:.2f}]")

            return sample

        except Exception as e:
            logger.error(f"Chyba při analýze {filepath}: {e}")
            return None

    def _load_audio_file(self, filepath: Path) -> tuple:
        """Načte audio soubor pomocí dostupných knihoven"""

        # Pokus o soundfile (nejrychlejší)
        if SOUNDFILE_AVAILABLE:
            try:
                waveform, sr = sf.read(str(filepath))
                return waveform, sr
            except Exception as e:
                logger.debug(f"Soundfile failed for {filepath.name}: {e}")

        # Pokus o librosa (spolehlivější pro různé formáty)
        if LIBROSA_AVAILABLE:
            try:
                waveform, sr = librosa.load(str(filepath), sr=None)
                # librosa vrací mono, převedeme na správný tvar
                if len(waveform.shape) == 1:
                    waveform = waveform.reshape(-1, 1)
                return waveform, sr
            except Exception as e:
                logger.debug(f"Librosa failed for {filepath.name}: {e}")

        logger.error(f"Žádná audio knihovna nemůže načíst {filepath.name}")
        return None, None

    def stop_analysis(self):
        """Zastaví analýzu (pro budoucí implementaci)"""
        self.terminate()

    def get_supported_formats(self) -> List[str]:
        """Vrátí seznam podporovaných formátů"""
        formats = []

        if SOUNDFILE_AVAILABLE:
            formats.extend(['WAV', 'FLAC', 'AIFF'])

        if LIBROSA_AVAILABLE:
            formats.extend(['MP3', 'OGG', 'M4A'])

        return list(set(formats))  # Odstraň duplicity