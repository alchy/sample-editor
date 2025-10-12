"""
amplitude_analyzer.py - Peak amplitude analýza pro velocity mapping
"""

import numpy as np
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AmplitudeAnalyzer:
    """Analyzátor RMS amplitude prvních 500ms pro velocity mapping"""

    def __init__(self, window_ms: float = 10.0, percentile: float = 99.5, velocity_duration_ms: float = 500.0):
        self.window_ms = window_ms
        self.percentile = percentile
        self.velocity_duration_ms = velocity_duration_ms  # Nový parametr pro velocity analýzu

    def analyze_peak_amplitude(self, waveform: np.ndarray, sr: int) -> Dict:
        """
        Analyzuje amplitude s RMS prvních 500ms pro velocity mapping

        Returns:
            Dict s peak_amplitude (pro debug), velocity_amplitude (RMS 500ms), atd.
        """
        try:
            # Převod na mono
            if len(waveform.shape) > 1:
                audio = np.mean(waveform, axis=1)
            else:
                audio = waveform.copy()

            if len(audio) == 0:
                return self._empty_result()

            # === VELOCITY AMPLITUDE - RMS prvních 500ms ===
            velocity_samples = int(sr * self.velocity_duration_ms / 1000.0)
            velocity_samples = min(velocity_samples, len(audio))

            if velocity_samples > 0:
                velocity_section = audio[:velocity_samples]
                velocity_amplitude = self._calculate_rms(velocity_section)
            else:
                velocity_amplitude = 0.0

            # === LEGACY PEAK AMPLITUDE - pro kompatibilitu ===
            # Window size v samples
            window_size = int(sr * self.window_ms / 1000.0)
            window_size = max(1, min(window_size, len(audio)))

            # Sliding window pro peak detekci (legacy)
            peak_values = []
            hop_size = max(1, window_size // 4)

            for i in range(0, len(audio) - window_size + 1, hop_size):
                window = audio[i:i + window_size]
                # Percentilová filtrace místo absolutního maxima
                window_peak = np.percentile(np.abs(window), self.percentile)
                peak_values.append(window_peak)

            if not peak_values:
                peak_amplitude = np.percentile(np.abs(audio), self.percentile)
                peak_position = self._find_peak_position_percentile(audio, self.percentile)
            else:
                peak_amplitude = np.max(peak_values)
                peak_position = self._find_peak_position_percentile(audio, self.percentile)

            # === CELKOVÝ RMS pro reference ===
            full_rms_amplitude = self._calculate_rms(audio)

            # === dB konverze ===
            velocity_amplitude_db = 20 * np.log10(velocity_amplitude) if velocity_amplitude > 1e-10 else -np.inf
            peak_db = 20 * np.log10(peak_amplitude) if peak_amplitude > 1e-10 else -np.inf
            full_rms_db = 20 * np.log10(full_rms_amplitude) if full_rms_amplitude > 1e-10 else -np.inf

            # === Dodatečné metriky ===
            abs_max = np.max(np.abs(audio))
            percentile_ratio = peak_amplitude / abs_max if abs_max > 0 else 1.0

            logger.debug(f"Velocity RMS (first {self.velocity_duration_ms}ms): {velocity_amplitude:.6f} ({velocity_amplitude_db:.1f} dB), "
                        f"Peak (P{self.percentile}): {peak_amplitude:.6f} ({peak_db:.1f} dB), "
                        f"Full RMS: {full_rms_amplitude:.6f} ({full_rms_db:.1f} dB)")

            return {
                # HLAVNÍ HODNOTA PRO VELOCITY MAPPING
                'velocity_amplitude': float(velocity_amplitude),  # RMS prvních 500ms
                'velocity_amplitude_db': float(velocity_amplitude_db),
                'velocity_duration_ms': self.velocity_duration_ms,

                # LEGACY HODNOTY (pro kompatibilitu)
                'peak_amplitude': float(peak_amplitude),  # Pro kompatibilitu s existing kódem
                'peak_amplitude_db': float(peak_db),
                'rms_amplitude': float(full_rms_amplitude),
                'rms_amplitude_db': float(full_rms_db),
                'peak_position': int(peak_position),
                'peak_position_seconds': float(peak_position / sr),
                'window_ms': self.window_ms,
                'analysis_windows': len(peak_values) if peak_values else 1,

                # DODATEČNÉ METRIKY
                'percentile_used': self.percentile,
                'absolute_max': float(abs_max),
                'percentile_ratio': float(percentile_ratio),

                # VELOCITY SPECIFICKÉ METRIKY
                'velocity_samples_analyzed': velocity_samples,
                'velocity_coverage_percent': (velocity_samples / len(audio) * 100) if len(audio) > 0 else 0
            }

        except Exception as e:
            logger.error(f"Amplitude analysis failed: {e}")
            return self._empty_result()

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Spočítá RMS hodnotu pro audio segment"""
        if len(audio) == 0:
            return 0.0
        return np.sqrt(np.mean(audio ** 2))

    def _find_peak_position_percentile(self, audio: np.ndarray, percentile: float) -> int:
        """Najde pozici percentilového peaku v audio signálu"""
        if len(audio) == 0:
            return 0

        abs_audio = np.abs(audio)
        percentile_value = np.percentile(abs_audio, percentile)

        # Najdi první pozici, kde amplitude dosahuje percentile hodnoty
        peak_indices = np.where(abs_audio >= percentile_value)[0]

        if len(peak_indices) > 0:
            # Vrati medián pozic pro robustnost
            return int(np.median(peak_indices))
        else:
            # Fallback na absolutní maximum
            return int(np.argmax(abs_audio))

    def _empty_result(self) -> Dict:
        """Prázdný výsledek"""
        return {
            'velocity_amplitude': 0.0,
            'velocity_amplitude_db': -np.inf,
            'velocity_duration_ms': self.velocity_duration_ms,
            'peak_amplitude': 0.0,
            'peak_amplitude_db': -np.inf,
            'rms_amplitude': 0.0,
            'rms_amplitude_db': -np.inf,
            'peak_position': 0,
            'peak_position_seconds': 0.0,
            'window_ms': self.window_ms,
            'analysis_windows': 0,
            'percentile_used': self.percentile,
            'absolute_max': 0.0,
            'percentile_ratio': 1.0,
            'velocity_samples_analyzed': 0,
            'velocity_coverage_percent': 0.0
        }

    def set_velocity_duration(self, duration_ms: float):
        """Nastaví délku analyzovaného úseku pro velocity (100-2000ms)"""
        self.velocity_duration_ms = max(100.0, min(2000.0, duration_ms))

    def analyze_attack_envelope(self, waveform: np.ndarray, sr: int,
                               attack_duration_ms: float = 100.0) -> Dict:
        """
        Analyzuje attack envelope s RMS approach
        """
        try:
            # Převod na mono
            if len(waveform.shape) > 1:
                audio = np.mean(waveform, axis=1)
            else:
                audio = waveform.copy()

            # Attack region
            attack_samples = int(sr * attack_duration_ms / 1000.0)
            attack_samples = min(attack_samples, len(audio))

            if attack_samples < 10:
                return {'attack_peak': 0.0, 'attack_time': 0.0, 'attack_slope': 0.0, 'attack_rms': 0.0}

            attack_section = audio[:attack_samples]

            # RMS approach pro attack
            attack_rms = self._calculate_rms(attack_section)

            # Legacy peak approach pro kompatibilitu
            abs_attack = np.abs(attack_section)
            noise_floor = np.percentile(abs_attack, 10)
            signal_threshold = noise_floor * 3

            signal_start_candidates = np.where(abs_attack > signal_threshold)[0]
            if len(signal_start_candidates) == 0:
                attack_peak = np.percentile(abs_attack, self.percentile)
                return {
                    'attack_peak': float(attack_peak),
                    'attack_time': 0.0,
                    'attack_slope': 0.0,
                    'attack_rms': float(attack_rms)
                }

            signal_start = signal_start_candidates[0]

            # Najdi percentilový peak v attack sekci
            percentile_peak_value = np.percentile(abs_attack[signal_start:], self.percentile)
            peak_candidates = np.where(abs_attack[signal_start:] >= percentile_peak_value)[0]

            if len(peak_candidates) > 0:
                peak_idx = signal_start + int(np.median(peak_candidates))
            else:
                peak_idx = signal_start + np.argmax(abs_attack[signal_start:])

            # Attack time a slope
            attack_time_samples = peak_idx - signal_start
            attack_time = attack_time_samples / sr

            peak_value = abs_attack[peak_idx]
            start_value = abs_attack[signal_start]
            attack_slope = (peak_value - start_value) / attack_time if attack_time > 0 else 0.0

            return {
                'attack_peak': float(peak_value),
                'attack_time': float(attack_time),
                'attack_slope': float(attack_slope),
                'attack_rms': float(attack_rms),  # Nová RMS metrika
                'signal_start_idx': int(signal_start),
                'peak_idx': int(peak_idx),
                'noise_floor': float(noise_floor),
                'percentile_used': self.percentile
            }

        except Exception as e:
            logger.error(f"Attack envelope analysis failed: {e}")
            return {'attack_peak': 0.0, 'attack_time': 0.0, 'attack_slope': 0.0, 'attack_rms': 0.0}


class AmplitudeRangeManager:
    """Manager pro globální rozsah amplitude hodnot"""

    def __init__(self):
        self.global_min = None
        self.global_max = None
        self.all_peak_values = []

    def add_sample_amplitude(self, peak_amplitude: float):
        """Přidá peak amplitude ze sample"""
        if peak_amplitude > 0:  # Ignoruj nulové hodnoty
            self.all_peak_values.append(peak_amplitude)

            if self.global_min is None or peak_amplitude < self.global_min:
                self.global_min = peak_amplitude

            if self.global_max is None or peak_amplitude > self.global_max:
                self.global_max = peak_amplitude

    def get_range_info(self) -> Dict:
        """Vrátí informace o rozsahu"""
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

    def create_velocity_mapping(self, filter_min: float = None,
                              filter_max: float = None, num_levels: int = 8) -> Dict:
        """
        Vytvoří velocity mapping na základě rozsahu

        Args:
            filter_min: Minimální hodnota pro filtraci (None = global_min)
            filter_max: Maximální hodnota pro filtraci (None = global_max)
            num_levels: Počet velocity levelů (0-7 = 8 úrovní)
        """
        if not self.all_peak_values:
            return {
                'thresholds': [0.0] * num_levels,
                'filter_min': 0.0,
                'filter_max': 1.0,
                'valid_samples': 0
            }

        # Použij filtrační rozsah nebo globální
        actual_min = filter_min if filter_min is not None else self.global_min
        actual_max = filter_max if filter_max is not None else self.global_max

        if actual_min is None or actual_max is None or actual_min >= actual_max:
            # Fallback na rozumné hodnoty
            actual_min = 0.0
            actual_max = 1.0

        # Lineární rozdělení rozsahu na num_levels
        thresholds = np.linspace(actual_min, actual_max, num_levels).tolist()

        # Spočítaj kolik samples je v rozsahu
        filtered_values = [v for v in self.all_peak_values
                          if actual_min <= v <= actual_max]

        logger.info(f"Velocity mapping: {actual_min:.6f} - {actual_max:.6f}, "
                   f"valid samples: {len(filtered_values)}/{len(self.all_peak_values)}")

        return {
            'thresholds': thresholds,
            'filter_min': float(actual_min),
            'filter_max': float(actual_max),
            'valid_samples': len(filtered_values),
            'total_samples': len(self.all_peak_values),
            'num_levels': num_levels
        }

    def assign_velocity_level(self, peak_amplitude: float,
                             velocity_mapping: Dict) -> int:
        """Přiřadí velocity level podle mappingu"""
        thresholds = velocity_mapping['thresholds']

        # Kontrola rozsahu
        if (peak_amplitude < velocity_mapping['filter_min'] or
            peak_amplitude > velocity_mapping['filter_max']):
            return -1  # Označuje filtrovaný sample

        # Najdi odpovídající level
        level = 0
        for i, threshold in enumerate(thresholds[1:], 1):
            if peak_amplitude <= threshold:
                level = i - 1
                break
        else:
            level = len(thresholds) - 1

        return min(level, len(thresholds) - 1)

    def reset(self):
        """Reset všech hodnot"""
        self.global_min = None
        self.global_max = None
        self.all_peak_values.clear()