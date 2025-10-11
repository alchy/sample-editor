"""
RMS Analyzer - Amplitude analysis pro velocity mapping.
"""

import numpy as np
import logging
from typing import Optional

from src.domain.interfaces.audio_analyzer import (
    IAmplitudeAnalyzer,
    AudioData,
    AmplitudeAnalysisResult
)

logger = logging.getLogger(__name__)


class RmsAnalyzer(IAmplitudeAnalyzer):
    """
    RMS amplitude analyzer pro velocity mapping.

    Analyzuje prvních N milisekund audio pro určení velocity amplitude.
    Používá RMS (Root Mean Square) pro robustní měření energie signálu.
    """

    def __init__(
        self,
        velocity_duration_ms: float = 500.0,
        window_ms: float = 10.0,
        percentile: float = 99.5
    ):
        """
        Args:
            velocity_duration_ms: Délka analyzovaného úseku pro velocity (100-2000ms)
            window_ms: Velikost okna pro legacy peak detection
            percentile: Percentil pro legacy peak detection
        """
        self.velocity_duration_ms = velocity_duration_ms
        self.window_ms = window_ms
        self.percentile = percentile

    def analyze(self, audio_data: AudioData) -> AmplitudeAnalysisResult:
        """
        Analyzuje amplitude s RMS prvních N ms pro velocity mapping.

        Args:
            audio_data: Audio data k analýze

        Returns:
            AmplitudeAnalysisResult s velocity_amplitude (hlavní), RMS a peak hodnotami
        """
        try:
            # Převod na mono
            waveform = audio_data.samples
            sr = audio_data.sample_rate

            if len(waveform.shape) > 1:
                audio = np.mean(waveform, axis=1)
            else:
                audio = waveform.copy()

            if len(audio) == 0:
                return self._empty_result()

            # === VELOCITY AMPLITUDE - RMS prvních N ms ===
            velocity_samples = int(sr * self.velocity_duration_ms / 1000.0)
            velocity_samples = min(velocity_samples, len(audio))

            if velocity_samples > 0:
                velocity_section = audio[:velocity_samples]
                velocity_amplitude = self._calculate_rms(velocity_section)
            else:
                velocity_amplitude = 0.0

            # === CELKOVÝ RMS pro reference ===
            full_rms_amplitude = self._calculate_rms(audio)

            # === LEGACY PEAK AMPLITUDE - pro kompatibilitu ===
            peak_amplitude = self._calculate_percentile_peak(audio, sr)

            # === dB konverze ===
            velocity_amplitude_db = self._to_db(velocity_amplitude)
            peak_db = self._to_db(peak_amplitude)
            full_rms_db = self._to_db(full_rms_amplitude)

            logger.debug(
                f"Velocity RMS (first {self.velocity_duration_ms}ms): "
                f"{velocity_amplitude:.6f} ({velocity_amplitude_db:.1f} dB), "
                f"Peak (P{self.percentile}): {peak_amplitude:.6f} ({peak_db:.1f} dB), "
                f"Full RMS: {full_rms_amplitude:.6f} ({full_rms_db:.1f} dB)"
            )

            return AmplitudeAnalysisResult(
                velocity_amplitude=float(velocity_amplitude),
                velocity_amplitude_db=float(velocity_amplitude_db),
                velocity_duration_ms=self.velocity_duration_ms,
                rms_amplitude=float(full_rms_amplitude),
                peak_amplitude=float(peak_amplitude)
            )

        except Exception as e:
            logger.error(f"RMS amplitude analysis failed: {e}")
            return self._empty_result()

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """
        Spočítá RMS (Root Mean Square) hodnotu pro audio segment.

        RMS = sqrt(mean(x^2)) - měří energii signálu.
        """
        if len(audio) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio ** 2)))

    def _calculate_percentile_peak(self, audio: np.ndarray, sr: int) -> float:
        """
        Vypočítá percentilový peak pro legacy kompatibilitu.
        Používá sliding window approach s percentilovou filtrací.
        """
        if len(audio) == 0:
            return 0.0

        # Window size v samples
        window_size = int(sr * self.window_ms / 1000.0)
        window_size = max(1, min(window_size, len(audio)))

        # Sliding window pro peak detekci
        peak_values = []
        hop_size = max(1, window_size // 4)

        for i in range(0, len(audio) - window_size + 1, hop_size):
            window = audio[i:i + window_size]
            # Percentilová filtrace místo absolutního maxima
            window_peak = np.percentile(np.abs(window), self.percentile)
            peak_values.append(window_peak)

        if not peak_values:
            # Fallback na globální percentil
            return float(np.percentile(np.abs(audio), self.percentile))
        else:
            return float(np.max(peak_values))

    def _to_db(self, amplitude: float) -> float:
        """Převede amplitudu na dB."""
        if amplitude > 1e-10:
            return float(20 * np.log10(amplitude))
        else:
            return float(-np.inf)

    def _empty_result(self) -> AmplitudeAnalysisResult:
        """Vrátí prázdný výsledek při chybě."""
        return AmplitudeAnalysisResult(
            velocity_amplitude=0.0,
            velocity_amplitude_db=-np.inf,
            velocity_duration_ms=self.velocity_duration_ms,
            rms_amplitude=0.0,
            peak_amplitude=0.0
        )

    def set_velocity_duration(self, duration_ms: float):
        """
        Nastaví délku analyzovaného úseku pro velocity.

        Args:
            duration_ms: Délka v milisekundách (omezeno na 100-2000ms)
        """
        self.velocity_duration_ms = max(100.0, min(2000.0, duration_ms))
