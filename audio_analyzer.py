"""
audio_analyzer.py - Worker thread pro batch analýzu s CREPE a amplitude detekcí - opravená verze
"""

import sys
from pathlib import Path
from typing import List, Set
import logging
import numpy as np
from PySide6.QtCore import QThread, Signal

from models import SampleMetadata, AnalysisProgress
from pitch_detector import PitchDetector
from amplitude_analyzer import AmplitudeAnalyzer, AmplitudeRangeManager

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
    """Worker thread pro batch analýzu s pitch a amplitude detekcí - opravená verze."""

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
        """Spustí batch analýzu."""
        try:
            # Najdi audio soubory - OPRAVENO: eliminace duplicit
            audio_files = self._find_unique_audio_files()

            if not audio_files:
                self.progress_updated.emit(0, "Žádné audio soubory nenalezeny")
                self.analysis_completed.emit([], {})
                return

            logger.info(f"Nalezeno {len(audio_files)} unikátních audio souborů")

            # Inicializace progress
            self.progress = AnalysisProgress(len(audio_files))
            self.progress_updated.emit(0, f"Nalezeno {len(audio_files)} audio souborů")

            # Reset amplitude range manager
            self.amplitude_range_manager.reset()

            # Analýza každého souboru
            successful_analyses = 0
            for i, filepath in enumerate(audio_files):
                try:
                    sample = self._analyze_single_sample(filepath)
                    if sample:
                        self.samples.append(sample)
                        successful_analyses += 1
                        self.progress.pitch_detections += 1 if sample.detected_midi else 0
                        self.progress.amplitude_detections += 1 if sample.velocity_amplitude else 0

                        # Safe amplitude addition
                        if sample.velocity_amplitude is not None and sample.velocity_amplitude > 0:
                            self.amplitude_range_manager.add_sample_amplitude(sample.velocity_amplitude)

                    self.progress.update(filepath.name)

                    percentage = int(((i + 1) / len(audio_files)) * 100)
                    self.progress_updated.emit(percentage, f"Analyzován: {filepath.name}")

                except Exception as e:
                    logger.error(f"Chyba při analýze {filepath}: {e}")
                    self.progress.add_error(filepath.name, str(e))

            # Finální progress update
            final_message = f"Analýza dokončena: {successful_analyses}/{len(audio_files)} úspěšných"
            if self.progress.errors:
                final_message += f", {len(self.progress.errors)} chyb"

            self.progress_updated.emit(100, final_message)

            # Získej amplitude range info
            range_info = self.amplitude_range_manager.get_range_info()

            logger.info(f"Analysis completed: {len(self.samples)} samples successfully analyzed")
            if range_info['count'] > 0:
                logger.info(f"Amplitude range: {range_info['min']:.6f} - {range_info['max']:.6f}")

            # Emit výsledky
            self.analysis_completed.emit(self.samples, range_info)

        except Exception as e:
            logger.error(f"Chyba při batch analýze: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _find_unique_audio_files(self) -> List[Path]:
        """Najde unikátní audio soubory bez duplicit."""
        audio_files_set: Set[Path] = set()  # Použití set pro eliminaci duplicit

        for ext in self.supported_extensions:
            found_files = list(self.input_folder.glob(ext))
            audio_files_set.update(found_files)
            logger.debug(f"Extension {ext}: found {len(found_files)} files")

        # Convert back to sorted list
        audio_files = sorted(list(audio_files_set))

        logger.info(f"Total unique audio files found: {len(audio_files)}")
        return audio_files

    def _analyze_single_sample(self, filepath: Path) -> SampleMetadata:
        """Analyzuje jeden sample - pitch + amplitude."""
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

            # Pitch detekce s error handling
            try:
                pitch_result = self.pitch_detector.detect_pitch(waveform, sr)
                sample.detected_frequency = pitch_result.get('frequency')
                sample.detected_midi = pitch_result.get('midi_note')
                sample.pitch_confidence = pitch_result.get('confidence', 0.0)
                sample.pitch_method = pitch_result.get('method', 'unknown')
            except Exception as e:
                logger.warning(f"Pitch detection failed for {filepath.name}: {e}")
                sample.detected_frequency = None
                sample.detected_midi = None
                sample.pitch_confidence = 0.0
                sample.pitch_method = 'failed'

            # Amplitude analýza - RMS prvních 500ms s error handling
            try:
                amplitude_result = self.amplitude_analyzer.analyze_peak_amplitude(waveform, sr)

                sample.velocity_amplitude = amplitude_result.get('velocity_amplitude')
                sample.velocity_amplitude_db = amplitude_result.get('velocity_amplitude_db')
                sample.velocity_duration_ms = amplitude_result.get('velocity_duration_ms')

                # Legacy hodnoty
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

            except Exception as e:
                logger.warning(f"Amplitude analysis failed for {filepath.name}: {e}")
                # Set safe default values
                sample.velocity_amplitude = 0.0
                sample.velocity_amplitude_db = -float('inf')

            # Označ jako analyzovaný
            sample.analyzed = True

            # Log výsledků
            pitch_info = f"MIDI {sample.detected_midi}" if sample.detected_midi else "No pitch"
            amplitude_info = f"RMS-500ms: {sample.velocity_amplitude:.6f}" if sample.velocity_amplitude else "No amplitude"

            logger.info(f"✓ {sample.filename}: {pitch_info}, {amplitude_info} "
                        f"[{sample.pitch_method}, conf: {sample.pitch_confidence:.2f}]")

            return sample

        except Exception as e:
            logger.error(f"Chyba při analýze {filepath}: {e}", exc_info=True)
            return None

    def _load_audio_file(self, filepath: Path) -> tuple:
        """Načte audio soubor pomocí dostupných knihoven s robustním error handlingem."""
        errors = []

        # Pokus o soundfile
        if SOUNDFILE_AVAILABLE:
            try:
                waveform, sr = sf.read(str(filepath))
                logger.debug(f"Loaded {filepath.name} with soundfile")
                return waveform, sr
            except Exception as e:
                error_msg = f"soundfile: {str(e)[:100]}"
                errors.append(error_msg)
                logger.debug(f"Soundfile failed for {filepath.name}: {e}")

        # Pokus o librosa
        if LIBROSA_AVAILABLE:
            try:
                waveform, sr = librosa.load(str(filepath), sr=None)
                if len(waveform.shape) == 1:
                    waveform = waveform.reshape(-1, 1)
                logger.debug(f"Loaded {filepath.name} with librosa")
                return waveform, sr
            except Exception as e:
                error_msg = f"librosa: {str(e)[:100]}"
                errors.append(error_msg)
                logger.debug(f"Librosa failed for {filepath.name}: {e}")

        # Comprehensive error reporting
        all_errors = "; ".join(errors)
        logger.error(f"Failed to load {filepath.name}. Tried: {all_errors}")
        return None, None

    def stop_analysis(self):
        """Zastaví analýzu."""
        self.terminate()

    def get_supported_formats(self) -> List[str]:
        """Vrátí seznam podporovaných formátů."""
        formats = []

        if SOUNDFILE_AVAILABLE:
            formats.extend(['WAV', 'FLAC', 'AIFF'])

        if LIBROSA_AVAILABLE:
            formats.extend(['MP3', 'OGG', 'M4A'])

        return list(set(formats))  # Odstraň duplicity