"""
CrepeAnalyzer - CREPE-based pitch detection analyzer.
"""
import logging
import numpy as np
from typing import Dict, Any

from src.domain.interfaces.audio_analyzer import IPitchAnalyzer, PitchAnalysisResult, AudioData

logger = logging.getLogger(__name__)

try:
    import crepe
    CREPE_AVAILABLE = True
except ImportError:
    CREPE_AVAILABLE = False
    logger.warning("CREPE not available")


class CrepeAnalyzer(IPitchAnalyzer):
    """Pitch analyzer using CREPE neural network."""
    
    def __init__(
        self,
        model_capacity: str = "tiny",
        step_size: int = 10,
        max_analysis_duration: float = 5.0
    ):
        """
        Inicializuje CREPE analyzer.

        Args:
            model_capacity: Model size (tiny, small, medium, large, full)
            step_size: Step size in milliseconds
            max_analysis_duration: Max délka audio k analýze v sekundách (default 5s)
        """
        self.model_capacity = model_capacity
        self.step_size = step_size
        self.confidence_threshold = 0.5
        self.max_analysis_duration = max_analysis_duration
        
    def analyze(self, audio_data: AudioData) -> PitchAnalysisResult:
        """
        Detekuje pitch pomocí CREPE.

        Analyzuje pouze prvních N sekund audio pro rychlost.

        Args:
            audio_data: Audio data k analýze

        Returns:
            PitchAnalysisResult s detekovanou MIDI notou
        """
        if not CREPE_AVAILABLE:
            logger.warning("CREPE not available, using fallback")
            return self._fallback_detection(audio_data)

        try:
            waveform = audio_data.samples
            sr = audio_data.sample_rate

            # Ensure mono
            if len(waveform.shape) > 1:
                waveform = np.mean(waveform, axis=1)

            # Analyzuj pouze prvních max_analysis_duration sekund
            max_samples = int(sr * self.max_analysis_duration)
            if len(waveform) > max_samples:
                original_duration = len(waveform) / sr
                waveform = waveform[:max_samples]
                logger.debug(
                    f"Truncated audio from {original_duration:.1f}s to "
                    f"{self.max_analysis_duration}s for CREPE analysis"
                )
            
            # Run CREPE
            time, frequency, confidence, _ = crepe.predict(
                waveform,
                sr,
                model_capacity=self.model_capacity,
                step_size=self.step_size,
                viterbi=True
            )
            
            # Filter by confidence
            valid_freq = frequency[confidence > self.confidence_threshold]
            valid_conf = confidence[confidence > self.confidence_threshold]
            
            if len(valid_freq) == 0:
                logger.debug("No confident pitch detected")
                return PitchAnalysisResult(method="crepe_no_pitch")
            
            # Use median of confident predictions
            detected_frequency = float(np.median(valid_freq))
            avg_confidence = float(np.mean(valid_conf))
            
            # Convert to MIDI
            midi_note = self._frequency_to_midi(detected_frequency)
            
            logger.debug(f"CREPE detected: {detected_frequency:.1f}Hz (MIDI {midi_note}), conf: {avg_confidence:.2f}")
            
            return PitchAnalysisResult(
                detected_midi=midi_note,
                detected_frequency=detected_frequency,
                confidence=avg_confidence,
                method="crepe"
            )
            
        except Exception as e:
            logger.error(f"CREPE analysis failed: {e}")
            return PitchAnalysisResult(method="crepe_error")
    
    def _fallback_detection(self, audio_data: AudioData) -> PitchAnalysisResult:
        """Fallback když CREPE není dostupný."""
        return PitchAnalysisResult(method="crepe_unavailable")
    
    @staticmethod
    def _frequency_to_midi(frequency: float) -> int:
        """Převede frekvenci na MIDI notu."""
        if frequency <= 0:
            return 0
        midi = 69 + 12 * np.log2(frequency / 440.0)
        return int(round(midi))
