"""
Analysis Service - Orchestrace audio analýzy (pitch + amplitude).
"""

import logging
from typing import Optional, Tuple
from pathlib import Path

from src.domain.models.sample import SampleMetadata
from src.domain.interfaces.audio_analyzer import (
    IPitchAnalyzer,
    IAmplitudeAnalyzer,
    IAudioFileLoader,
    AudioData
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Application service pro orchestraci audio analýzy.

    Kombinuje:
    - AudioFileLoader: Načtení audio souboru
    - PitchAnalyzer: Detekce MIDI noty (CREPE)
    - AmplitudeAnalyzer: Měření velocity (RMS)
    """

    def __init__(
        self,
        audio_loader: IAudioFileLoader,
        pitch_analyzer: IPitchAnalyzer,
        amplitude_analyzer: IAmplitudeAnalyzer
    ):
        """
        Args:
            audio_loader: Instance AudioFileLoader
            pitch_analyzer: Instance CrepeAnalyzer
            amplitude_analyzer: Instance RmsAnalyzer
        """
        self.audio_loader = audio_loader
        self.pitch_analyzer = pitch_analyzer
        self.amplitude_analyzer = amplitude_analyzer

    def analyze_sample(self, sample: SampleMetadata) -> bool:
        """
        Kompletní analýza sample: pitch + amplitude.

        Args:
            sample: SampleMetadata objekt k analýze

        Returns:
            True pokud analýza byla úspěšná, False jinak
        """
        try:
            # 1. Načtení audio souboru
            audio_data = self.audio_loader.load(sample.filepath)
            if audio_data is None:
                logger.error(f"Failed to load audio file: {sample.filepath}")
                return False

            logger.debug(
                f"Loaded audio: {sample.filename}, "
                f"duration={audio_data.duration:.2f}s, "
                f"sr={audio_data.sample_rate}Hz"
            )

            # 2. Pitch detection
            pitch_result = self.pitch_analyzer.analyze(audio_data)
            if pitch_result.detected_midi is not None:
                sample.detected_midi = pitch_result.detected_midi
                sample.detected_frequency = pitch_result.detected_frequency
                logger.debug(
                    f"Pitch detected: MIDI={pitch_result.detected_midi}, "
                    f"freq={pitch_result.detected_frequency:.1f}Hz, "
                    f"confidence={pitch_result.confidence:.2f}"
                )
            else:
                logger.warning(f"No pitch detected for {sample.filename}")
                return False

            # 3. Amplitude analysis
            amplitude_result = self.amplitude_analyzer.analyze(audio_data)
            if amplitude_result.velocity_amplitude is not None:
                sample.velocity_amplitude = amplitude_result.velocity_amplitude
                logger.debug(
                    f"Amplitude: velocity={amplitude_result.velocity_amplitude:.6f}, "
                    f"velocity_db={amplitude_result.velocity_amplitude_db:.1f}dB"
                )
            else:
                logger.warning(f"Amplitude analysis failed for {sample.filename}")
                return False

            # 4. Označit jako analyzovaný
            sample.mark_as_analyzed()
            logger.info(
                f"✓ Analyzed: {sample.filename} -> "
                f"MIDI {sample.detected_midi}, "
                f"velocity {sample.velocity_amplitude:.6f}"
            )

            return True

        except Exception as e:
            logger.error(f"Analysis failed for {sample.filepath}: {e}")
            return False

    def analyze_batch(
        self,
        samples: list[SampleMetadata],
        progress_callback: Optional[callable] = None
    ) -> Tuple[int, int]:
        """
        Analyzuje batch samples s optional progress callback.

        Args:
            samples: List SampleMetadata objektů
            progress_callback: Optional callback(current, total) pro progress reporting

        Returns:
            Tuple (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        total = len(samples)

        for i, sample in enumerate(samples, 1):
            if self.analyze_sample(sample):
                successful += 1
            else:
                failed += 1

            if progress_callback:
                progress_callback(i, total)

        logger.info(
            f"Batch analysis complete: {successful} successful, "
            f"{failed} failed out of {total}"
        )

        return successful, failed

    def get_audio_info(self, file_path: Path) -> Optional[dict]:
        """
        Získá základní info o audio souboru bez plné analýzy.

        Args:
            file_path: Cesta k souboru

        Returns:
            Dictionary s info (duration, sample_rate, channels) nebo None
        """
        return self.audio_loader.get_audio_info(file_path)
