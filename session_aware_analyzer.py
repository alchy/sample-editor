"""
session_aware_analyzer.py - Batch analyzer s podporou session cache
"""

import logging
from pathlib import Path
from typing import List, Set

from audio_analyzer import BatchAnalyzer
from models import SampleMetadata
from session_manager import SessionManager
from amplitude_analyzer import AmplitudeRangeManager

logger = logging.getLogger(__name__)


class SessionAwareBatchAnalyzer(BatchAnalyzer):
    """BatchAnalyzer s podporou session cache."""

    def __init__(self, input_folder: Path, session_manager: SessionManager):
        super().__init__(input_folder)
        self.session_manager = session_manager
        self.cached_samples = []
        self.samples_to_analyze = []

    def run(self):
        """Spustí analýzu s využitím cache."""
        try:
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
            self.cached_samples, self.samples_to_analyze = self.session_manager.analyze_folder_with_cache(
                self.input_folder, samples
            )

            logger.info(f"Cache analysis: {len(self.cached_samples)} cached, {len(self.samples_to_analyze)} to analyze")

            if not self.samples_to_analyze:
                # Vše je v cache
                self.progress_updated.emit(100, f"All samples loaded from cache ({len(self.cached_samples)} samples)")

                # Setup amplitude range manager
                range_manager = AmplitudeRangeManager()
                for sample in self.cached_samples:
                    if sample.velocity_amplitude and sample.velocity_amplitude > 0:
                        range_manager.add_sample_amplitude(sample.velocity_amplitude)

                range_info = range_manager.get_range_info()
                self.analysis_completed.emit(self.cached_samples, range_info)
                return

            # Analyzuj jen nové samples pomocí vlastní logiky
            self.progress_updated.emit(10, f"Analyzing {len(self.samples_to_analyze)} new samples...")
            self._analyze_samples_directly(self.samples_to_analyze)

        except Exception as e:
            logger.error(f"SessionAwareBatchAnalyzer failed: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _analyze_samples_directly(self, samples_to_analyze):
        """Analyzuje samples přímo bez volání parent run()."""
        try:
            # Reset amplitude range manager
            self.amplitude_range_manager.reset()

            total_samples = len(samples_to_analyze)
            analyzed_samples = []

            for i, sample in enumerate(samples_to_analyze):
                try:
                    # Update progress
                    percentage = 15 + int(((i + 1) / total_samples) * 80)  # 15-95%
                    self.progress_updated.emit(percentage, f"Analyzing: {sample.filename}")

                    # Analyze single sample using parent's method
                    analyzed_sample = self._analyze_single_sample(sample.filepath)

                    if analyzed_sample:
                        analyzed_samples.append(analyzed_sample)

                        # Add to amplitude range manager
                        if analyzed_sample.velocity_amplitude is not None and analyzed_sample.velocity_amplitude > 0:
                            self.amplitude_range_manager.add_sample_amplitude(analyzed_sample.velocity_amplitude)

                except Exception as e:
                    logger.error(f"Failed to analyze {sample.filepath}: {e}")
                    continue

            # Cache the newly analyzed samples
            if analyzed_samples:
                self.session_manager.cache_analyzed_samples(analyzed_samples)

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
        audio_files_set: Set[Path] = set()  # Použití set pro eliminaci duplicit

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
        self.terminate()
        logger.info("SessionAwareBatchAnalyzer analysis stopped")