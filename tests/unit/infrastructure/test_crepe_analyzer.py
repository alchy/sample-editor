"""
Unit testy pro CrepeAnalyzer.
"""

import pytest
import numpy as np

from src.domain.interfaces.audio_analyzer import AudioData
from src.infrastructure.audio.crepe_analyzer import CrepeAnalyzer


@pytest.mark.unit
class TestCrepeAnalyzer:
    """Testy pro CREPE pitch analyzer."""

    def test_initialization(self):
        """Test inicializace analyzeru."""
        analyzer = CrepeAnalyzer(model_capacity="tiny", step_size=10)
        assert analyzer is not None
        assert analyzer.model_capacity == "tiny"
        assert analyzer.step_size == 10
        assert analyzer.confidence_threshold == 0.5

    def test_frequency_to_midi_conversion(self):
        """Test převodu frekvence na MIDI notu."""
        analyzer = CrepeAnalyzer()

        # A4 = 440Hz = MIDI 69
        midi = analyzer._frequency_to_midi(440.0)
        assert midi == 69

        # C4 = 261.63Hz = MIDI 60
        midi = analyzer._frequency_to_midi(261.63)
        assert midi == 60

        # A3 = 220Hz = MIDI 57
        midi = analyzer._frequency_to_midi(220.0)
        assert midi == 57

    def test_frequency_to_midi_rounding(self):
        """Test zaokrouhlování MIDI not."""
        analyzer = CrepeAnalyzer()

        # Test hodnoty mezi notami
        midi = analyzer._frequency_to_midi(445.0)  # Mezi A4 a A#4
        assert midi in [69, 70]

        midi = analyzer._frequency_to_midi(435.0)  # Mezi G#4 a A4
        assert midi in [68, 69]

    @pytest.mark.slow
    def test_analyze_sine_wave_a4(self):
        """
        Test analýzy čisté sine wave A4 (440Hz).

        NOTE: Tento test je pomalý (CREPE model loading), označen jako 'slow'.
        """
        # Vygeneruj 1s sine wave @ 440Hz
        sample_rate = 16000  # CREPE preferuje 16kHz
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = 0.5 * np.sin(2 * np.pi * 440.0 * t)

        audio_data = AudioData(waveform, sample_rate, channels=1)

        analyzer = CrepeAnalyzer(model_capacity="tiny")
        result = analyzer.analyze(audio_data)

        # Očekáváme MIDI 69 (A4) s vysokou confidence
        assert result.detected_midi is not None
        assert result.detected_midi == 69
        assert result.detected_frequency is not None
        assert 430 < result.detected_frequency < 450  # Mělo by být blízko 440Hz
        assert result.confidence > 0.8  # Čistá sine wave by měla mít vysokou confidence
        assert result.method == "crepe"

    def test_analyze_empty_audio(self):
        """Test analýzy prázdného audio."""
        waveform = np.array([])
        audio_data = AudioData(waveform, 16000, channels=1)

        analyzer = CrepeAnalyzer()

        # CREPE vrací PitchAnalysisResult s None hodnotami
        result = analyzer.analyze(audio_data)
        assert result is not None
        # Prázdné audio nevede k detekci pitch
        assert result.detected_midi is None or result.method in ["crepe_no_pitch", "crepe_error"]
