"""
session_aware_analyzer_new.py - REFACTORED Batch analyzer s podporou session cache

ZMĚNY:
- Používá nové refaktorované services místo monolitických komponent
- AnalysisService místo BatchAnalyzer
- SessionService místo SessionManager
- Zachovává stejný interface pro main_window.py
"""

import logging
from pathlib import Path
from typing import List, Set, Dict, Any
from datetime import datetime
from PySide6.QtCore import QThread, Signal

from src.domain.models.sample import SampleMetadata
from src.application.services.analysis_service import AnalysisService
from src.application.services.session_service import SessionService
from src.infrastructure.audio.audio_file_loader import AudioFileLoader
from src.infrastructure.audio.crepe_analyzer import CrepeAnalyzer
from src.infrastructure.audio.rms_analyzer import RmsAnalyzer

logger = logging.getLogger(__name__)


class AmplitudeRangeManager:
    """Manager pro globální rozsah amplitude hodnot."""

    def __init__(self):
        self.global_min = None
        self.global_max = None
        self.all_peak_values = []

    def add_sample_amplitude(self, velocity_amplitude: float):
        """Přidá velocity amplitude ze sample."""
        if velocity_amplitude > 0:
            self.all_peak_values.append(velocity_amplitude)

            if self.global_min is None or velocity_amplitude < self.global_min:
                self.global_min = velocity_amplitude

            if self.global_max is None or velocity_amplitude > self.global_max:
                self.global_max = velocity_amplitude

    def get_range_info(self) -> Dict[str, Any]:
        """Vrátí informace o rozsahu."""
        if not self.all_peak_values:
            return {
                'min': 0.0,
                'max': 1.0,
                'count': 0,
                'mean': 0.0,
                'std': 0.0,
                'percentile_5': 0.0,
                'percentile_95': 1.0
            }

        import numpy as np
        values = np.array(self.all_peak_values)

        return {
            'min': float(self.global_min) if self.global_min is not None else 0.0,
            'max': float(self.global_max) if self.global_max is not None else 1.0,
            'count': len(self.all_peak_values),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'percentile_5': float(np.percentile(values, 5)),
            'percentile_95': float(np.percentile(values, 95))
        }

    def reset(self):
        """Reset všech hodnot."""
        self.global_min = None
        self.global_max = None
        self.all_peak_values.clear()


class SessionAwareBatchAnalyzer(QThread):
    """
    REFACTORED BatchAnalyzer s podporou session cache.

    Používá nové refaktorované komponenty:
    - AnalysisService (místo BatchAnalyzer)
    - SessionService (místo SessionManager)

    Zachovává stejný interface pro zpětnou kompatibilitu.
    """

    # Signály (stejné jako původní BatchAnalyzer)
    progress_updated = Signal(int, str)  # percentage, message
    analysis_completed = Signal(list, dict)  # samples, range_info

    # NOVÝ signál pro průběžné přidávání samples
    sample_analyzed = Signal(object, dict)  # sample, current_range_info

    def __init__(self, input_folder: Path, session_manager):
        """
        Args:
            input_folder: Složka se samples
            session_manager: SessionManager (pro kompatibilitu) nebo SessionService
        """
        super().__init__()
        self.input_folder = input_folder

        # Podporujeme oba typy (SessionManager i SessionService)
        # Pro nový kód: předat SessionService
        # Pro starý kód: předat SessionManager (wrapper)
        if hasattr(session_manager, 'session_service'):
            # Je to SessionManager wrapper
            self.session_service = session_manager.session_service
        elif hasattr(session_manager, 'load_session'):
            # Je to přímo SessionService
            self.session_service = session_manager
        else:
            # Fallback - vytvořit nový
            from src.infrastructure.persistence.session_repository_impl import JsonSessionRepository
            from src.infrastructure.persistence.cache_manager import Md5CacheManager
            self.session_service = SessionService(
                JsonSessionRepository(),
                Md5CacheManager()
            )

        # Vytvoř AnalysisService
        audio_loader = AudioFileLoader()
        pitch_analyzer = CrepeAnalyzer(model_capacity="tiny", max_analysis_duration=5.0)
        amplitude_analyzer = RmsAnalyzer(velocity_duration_ms=500.0)
        self.analysis_service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)

        # Podporované extensions
        self.supported_extensions = ['*.wav', '*.mp3', '*.flac', '*.aiff', '*.aif']

        # State
        self.cached_samples = []
        self.samples_to_analyze = []
        self.amplitude_range_manager = AmplitudeRangeManager()
        self._stop_requested = False

    def run(self):
        """Spustí analýzu s využitím cache."""
        try:
            self._stop_requested = False

            # Najdi audio soubory
            audio_files = self._find_unique_audio_files()
            if not audio_files:
                self.progress_updated.emit(0, "No audio files found")
                self.analysis_completed.emit([], {})
                return

            logger.info(f"Found {len(audio_files)} unique audio files")

            # Vytvoř SampleMetadata objekty
            samples = [SampleMetadata(filepath) for filepath in audio_files]

            # Zkontroluj cache
            self.progress_updated.emit(5, "Checking cache...")
            self.cached_samples, self.samples_to_analyze = self.session_service.analyze_with_cache(samples)

            logger.info(f"Cache analysis: {len(self.cached_samples)} cached, {len(self.samples_to_analyze)} to analyze")

            # PRŮBĚŽNĚ: Emituj cached samples okamžitě pro práci s nimi
            if self.cached_samples:
                # Setup amplitude range manager pro cached samples
                for sample in self.cached_samples:
                    if sample.velocity_amplitude and sample.velocity_amplitude > 0:
                        self.amplitude_range_manager.add_sample_amplitude(sample.velocity_amplitude)

                    # Emituj každý cached sample individuálně
                    current_range_info = self.amplitude_range_manager.get_range_info()
                    self.sample_analyzed.emit(sample, current_range_info)

                logger.info(f"Emitted {len(self.cached_samples)} cached samples for immediate use")

            if not self.samples_to_analyze:
                # Vše je v cache - už bylo emitováno výše
                self.progress_updated.emit(100, f"All samples loaded from cache ({len(self.cached_samples)} samples)")
                range_info = self.amplitude_range_manager.get_range_info()
                self.analysis_completed.emit(self.cached_samples, range_info)
                return

            # Analyzuj jen nové samples
            self.progress_updated.emit(10, f"Analyzing {len(self.samples_to_analyze)} new samples...")
            self._analyze_samples_directly(self.samples_to_analyze)

        except Exception as e:
            logger.error(f"SessionAwareBatchAnalyzer failed: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _analyze_samples_directly(self, samples_to_analyze: List[SampleMetadata]):
        """Analyzuje samples pomocí nového AnalysisService."""
        try:
            # Reset amplitude range manager
            self.amplitude_range_manager.reset()

            total_samples = len(samples_to_analyze)
            analyzed_samples = []

            for i, sample in enumerate(samples_to_analyze):
                if self._stop_requested:
                    logger.info("Analysis stopped by user")
                    break

                try:
                    # Update progress
                    percentage = 15 + int(((i + 1) / total_samples) * 80)  # 15-95%
                    self.progress_updated.emit(percentage, f"Analyzing: {sample.filename}")

                    # Analyze single sample using AnalysisService
                    success = self.analysis_service.analyze_sample(sample)

                    if success and sample.analyzed:
                        analyzed_samples.append(sample)

                        # Add to amplitude range manager
                        if sample.velocity_amplitude is not None and sample.velocity_amplitude > 0:
                            self.amplitude_range_manager.add_sample_amplitude(sample.velocity_amplitude)

                        # PRŮBĚŽNĚ: Emituj každý nově analyzovaný sample okamžitě
                        current_range_info = self.amplitude_range_manager.get_range_info()
                        self.sample_analyzed.emit(sample, current_range_info)
                        logger.debug(f"Emitted newly analyzed sample: {sample.filename}")
                    else:
                        logger.warning(f"Failed to analyze {sample.filename}")

                except Exception as e:
                    logger.error(f"Failed to analyze {sample.filepath}: {e}")
                    continue

            # Cache the newly analyzed samples pomocí SessionService
            if analyzed_samples:
                # SessionService má již cache_samples metodu přes analyze_with_cache
                # Zde jen ujistíme, že samples mají hash a ukládáme KOMPLETNÍ data
                for sample in analyzed_samples:
                    if not hasattr(sample, '_hash'):
                        file_hash = self.session_service.cache.calculate_file_hash(sample.filepath)
                        sample._hash = file_hash

                    # OPRAVA: Ulož KOMPLETNÍ cache data (ne jen 4 pole!)
                    # Musíme zahrnout všechna pole která _validate_cached_data() očekává
                    cached_data = {
                        # Basic file info
                        'filename': sample.filename,
                        'file_path': str(sample.filepath),

                        # Pitch detection results (převod na Python typy)
                        'detected_midi': int(sample.detected_midi) if sample.detected_midi is not None else None,
                        'detected_frequency': float(sample.detected_frequency) if sample.detected_frequency is not None else None,
                        'pitch_confidence': float(sample.pitch_confidence) if sample.pitch_confidence is not None else None,
                        'pitch_method': str(sample.pitch_method) if sample.pitch_method else 'crepe',

                        # Amplitude analysis results (primary)
                        'velocity_amplitude': float(sample.velocity_amplitude) if sample.velocity_amplitude is not None else None,
                        'velocity_amplitude_db': float(sample.velocity_amplitude_db) if sample.velocity_amplitude_db is not None else None,
                        'velocity_duration_ms': float(sample.velocity_duration_ms) if sample.velocity_duration_ms is not None else None,

                        # Audio properties
                        'duration': float(sample.duration) if sample.duration is not None else None,
                        'sample_rate': int(sample.sample_rate) if sample.sample_rate is not None else None,
                        'channels': int(sample.channels) if sample.channels is not None else None,

                        # Cache metadata (set_cache() je přidá, ale přidáme zde pro jistotu)
                        'analyzed_timestamp': datetime.now().isoformat(),
                        'cache_version': '2.0'
                    }
                    self.session_service.cache.set_cache(sample._hash, cached_data)

                logger.info(f"Cached {len(analyzed_samples)} newly analyzed samples with complete data")

            # Merge cached and newly analyzed samples
            all_samples = self.cached_samples + analyzed_samples

            # Create final range info with all samples
            final_range_manager = AmplitudeRangeManager()
            for sample in all_samples:
                if sample.velocity_amplitude and sample.velocity_amplitude > 0:
                    final_range_manager.add_sample_amplitude(sample.velocity_amplitude)

            final_range_info = final_range_manager.get_range_info()

            # Final progress update
            self.progress_updated.emit(100, f"Analysis completed: {len(all_samples)} samples")

            # Emit completed signal
            self.analysis_completed.emit(all_samples, final_range_info)

        except Exception as e:
            logger.error(f"Direct analysis failed: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _find_unique_audio_files(self) -> List[Path]:
        """Najde unikátní audio soubory bez duplicit."""
        audio_files_set: Set[Path] = set()

        try:
            for ext in self.supported_extensions:
                found_files = list(self.input_folder.glob(ext))
                audio_files_set.update(found_files)
                logger.debug(f"Extension {ext}: found {len(found_files)} files")

            # Convert back to sorted list
            audio_files = sorted(list(audio_files_set))

            logger.info(f"Total unique audio files found: {len(audio_files)}")
            return audio_files

        except Exception as e:
            logger.error(f"Error finding audio files in {self.input_folder}: {e}")
            return []

    def stop_analysis(self):
        """Zastaví analýzu."""
        self._stop_requested = True
        self.terminate()
        logger.info("SessionAwareBatchAnalyzer analysis stopped")
