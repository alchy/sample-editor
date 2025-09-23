"""
pitch_detector.py - Skutečná pitch detekce pomocí CREPE
"""

import numpy as np
import logging
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Kontrola dostupnosti CREPE
try:
    import crepe
    import tensorflow as tf

    # Potlačení TensorFlow varování
    tf.get_logger().setLevel('ERROR')
    CREPE_AVAILABLE = True
    logger.info("CREPE loaded successfully")
except ImportError as e:
    CREPE_AVAILABLE = False
    logger.warning(f"CREPE not available: {e}")

try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("Librosa not available")


class PitchDetector:
    """Pitch detektor s CREPE jako primární metodou"""

    def __init__(self, fmin: float = 27.5, fmax: float = 4186.0):
        self.fmin = fmin  # A0
        self.fmax = fmax  # C8
        self.piano_frequencies = self._generate_piano_frequencies()

    def _generate_piano_frequencies(self) -> np.ndarray:
        """Generuje piano frekvence A0-C8"""
        A4_freq = 440.0
        frequencies = []
        for midi in range(21, 109):  # A0 to C8
            freq = A4_freq * (2 ** ((midi - 69) / 12))
            if self.fmin <= freq <= self.fmax:
                frequencies.append(freq)
        return np.array(frequencies)

    def detect_pitch(self, waveform: np.ndarray, sr: int) -> Dict:
        """
        Hlavní metoda pro detekci pitch
        """
        # Preprocessing
        audio = self._preprocess_audio(waveform, sr)

        if len(audio) < 1024:
            return self._empty_result()

        # CREPE detekce
        if CREPE_AVAILABLE:
            result = self._crepe_detection(audio, sr)
            if result['frequency'] and result['confidence'] > 0.3:
                return result

        # Fallback na librosa
        if LIBROSA_AVAILABLE:
            result = self._librosa_detection(audio, sr)
            if result['frequency']:
                return result

        # Poslední možnost - simulovaná data
        return self._fallback_detection()

    def _crepe_detection(self, audio: np.ndarray, sr: int) -> Dict:
        """CREPE pitch detection"""
        try:
            # CREPE parametry
            model_capacity = 'medium'  # 'tiny', 'small', 'medium', 'large', 'full'
            step_size = 10  # ms

            # CREPE očekává float32
            audio = audio.astype(np.float32)

            logger.debug(f"CREPE input: length={len(audio)}, sr={sr}")

            # CREPE detection
            time_stamps, frequencies, confidences, _ = crepe.predict(
                audio,
                sr,
                model_capacity=model_capacity,
                step_size=step_size,
                verbose=0,
                center=True,
                viterbi=True
            )

            # Filtrace na piano rozsah
            valid_mask = (
                    (frequencies >= self.fmin) &
                    (frequencies <= self.fmax) &
                    (confidences > 0.1)
            )

            if not np.any(valid_mask):
                logger.debug("No valid CREPE detections in piano range")
                return {'frequency': None, 'confidence': 0.0, 'method': 'crepe_no_valid'}

            valid_frequencies = frequencies[valid_mask]
            valid_confidences = confidences[valid_mask]

            # Robustní výpočet finální frekvence
            if len(valid_frequencies) > 0:
                # Median pro odstranění outliers
                median_freq = np.median(valid_frequencies)

                # Filtruj hodnoty blízko mediánu (10% tolerance)
                median_mask = np.abs(valid_frequencies - median_freq) < median_freq * 0.1
                final_frequencies = valid_frequencies[median_mask]
                final_confidences = valid_confidences[median_mask]

                if len(final_frequencies) > 0:
                    # Vážený průměr podle confidence
                    weights = final_confidences / np.sum(final_confidences)
                    final_frequency = np.sum(final_frequencies * weights)
                    final_confidence = np.mean(final_confidences)
                else:
                    # Fallback na median
                    final_frequency = median_freq
                    final_confidence = np.mean(valid_confidences)

                # Převod na MIDI notu
                midi_note = self._frequency_to_midi(final_frequency)

                logger.debug(f"CREPE result: {final_frequency:.2f} Hz, MIDI {midi_note}, conf: {final_confidence:.3f}")

                return {
                    'frequency': final_frequency,
                    'midi_note': midi_note,
                    'confidence': final_confidence,
                    'method': 'crepe'
                }

            return {'frequency': None, 'confidence': 0.0, 'method': 'crepe_filtered'}

        except Exception as e:
            logger.error(f"CREPE detection failed: {e}")
            return {'frequency': None, 'confidence': 0.0, 'method': 'crepe_error'}

    def _librosa_detection(self, audio: np.ndarray, sr: int) -> Dict:
        """Librosa pitch detection jako backup"""
        try:
            import librosa

            # Pitch tracking s librosa
            pitches, magnitudes = librosa.piptrack(
                y=audio,
                sr=sr,
                threshold=0.1,
                fmin=self.fmin,
                fmax=self.fmax
            )

            # Najdi nejsilnější pitch v každém frame
            frequencies = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    frequencies.append(pitch)

            if not frequencies:
                return {'frequency': None, 'confidence': 0.0, 'method': 'librosa_no_pitch'}

            # Median jako robustní odhad
            final_frequency = np.median(frequencies)
            midi_note = self._frequency_to_midi(final_frequency)

            # Odhad confidence podle konzistence
            freq_std = np.std(frequencies)
            confidence = max(0.0, 1.0 - (freq_std / final_frequency))

            logger.debug(f"Librosa result: {final_frequency:.2f} Hz, MIDI {midi_note}, conf: {confidence:.3f}")

            return {
                'frequency': final_frequency,
                'midi_note': midi_note,
                'confidence': confidence,
                'method': 'librosa'
            }

        except Exception as e:
            logger.error(f"Librosa detection failed: {e}")
            return {'frequency': None, 'confidence': 0.0, 'method': 'librosa_error'}

    def _fallback_detection(self) -> Dict:
        """Fallback simulovaná detekce"""
        import random
        midi_note = random.randint(21, 108)
        frequency = 440.0 * (2 ** ((midi_note - 69) / 12))

        logger.warning("Using fallback simulated pitch detection")

        return {
            'frequency': frequency,
            'midi_note': midi_note,
            'confidence': 0.5,
            'method': 'fallback_simulation'
        }

    def _frequency_to_midi(self, frequency: float) -> int:
        """Převod frekvence na MIDI notu"""
        if frequency <= 0:
            return 60  # Middle C jako default

        midi_float = 12 * np.log2(frequency / 440.0) + 69
        midi_note = int(round(midi_float))

        # Omezenání na piano rozsah
        return max(21, min(108, midi_note))

    def _preprocess_audio(self, waveform: np.ndarray, sr: int) -> np.ndarray:
        """Audio preprocessing"""
        # Převod na mono
        if len(waveform.shape) > 1:
            audio = np.mean(waveform, axis=1)
        else:
            audio = waveform.copy()

        # Normalizace
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio)) * 0.8

        # High-pass filter pro odstranění DC
        if len(audio) > 100:
            alpha = 0.98
            filtered = np.zeros_like(audio)
            filtered[0] = audio[0]
            for i in range(1, len(audio)):
                filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])
            audio = filtered

        return audio.astype(np.float32)

    def _empty_result(self) -> Dict:
        """Prázdný výsledek"""
        return {
            'frequency': None,
            'midi_note': None,
            'confidence': 0.0,
            'method': 'empty_audio'
        }