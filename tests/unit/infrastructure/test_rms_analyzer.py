"""
Unit testy pro RmsAnalyzer.
"""

import pytest
import numpy as np
from pathlib import Path

from src.domain.interfaces.audio_analyzer import AudioData
from src.infrastructure.audio.rms_analyzer import RmsAnalyzer


@pytest.mark.unit
class TestRmsAnalyzer:
    """Testy pro RMS amplitude analyzer."""

    def test_initialization(self):
        """Test inicializace analyzeru."""
        analyzer = RmsAnalyzer(velocity_duration_ms=500.0)
        assert analyzer is not None
        assert analyzer.velocity_duration_ms == 500.0
        assert analyzer.window_ms == 10.0
        assert analyzer.percentile == 99.5

    def test_analyze_sine_wave(self):
        """Test analýzy jednoduché sine wave."""
        # Vytvoř 1s sine wave @ 440Hz s amplitudou 0.5
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0
        amplitude = 0.5

        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = amplitude * np.sin(2 * np.pi * frequency * t)

        audio_data = AudioData(waveform, sample_rate, channels=1)

        # Analyzuj
        analyzer = RmsAnalyzer(velocity_duration_ms=500.0)
        result = analyzer.analyze(audio_data)

        # RMS sine wave = amplitude / sqrt(2) = 0.5 / 1.414 ≈ 0.353
        expected_rms = amplitude / np.sqrt(2)

        assert result.velocity_amplitude is not None
        assert abs(result.velocity_amplitude - expected_rms) < 0.01
        assert result.velocity_amplitude_db is not None
        assert result.velocity_amplitude_db > -10  # Mělo by být okolo -9 dB

    def test_analyze_empty_audio(self):
        """Test analýzy prázdného audio."""
        waveform = np.array([])
        audio_data = AudioData(waveform, 44100, channels=1)

        analyzer = RmsAnalyzer()
        result = analyzer.analyze(audio_data)

        assert result.velocity_amplitude == 0.0
        assert result.velocity_amplitude_db == float('-inf')
        assert result.rms_amplitude == 0.0

    def test_analyze_stereo_audio(self):
        """Test analýzy stereo audio (převod na mono)."""
        sample_rate = 44100
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Stereo: levý kanál = sine, pravý kanál = 0.5 * sine
        left = 0.5 * np.sin(2 * np.pi * 440 * t)
        right = 0.25 * np.sin(2 * np.pi * 440 * t)
        waveform = np.column_stack([left, right])

        audio_data = AudioData(waveform, sample_rate, channels=2)

        analyzer = RmsAnalyzer(velocity_duration_ms=500.0)
        result = analyzer.analyze(audio_data)

        # Mono průměr = (0.5 + 0.25) / 2 = 0.375
        # RMS = 0.375 / sqrt(2) ≈ 0.265
        expected_rms = 0.375 / np.sqrt(2)

        assert result.velocity_amplitude is not None
        assert abs(result.velocity_amplitude - expected_rms) < 0.02

    def test_velocity_duration_setting(self):
        """Test nastavení velocity_duration."""
        analyzer = RmsAnalyzer(velocity_duration_ms=1000.0)
        assert analyzer.velocity_duration_ms == 1000.0

        # Nastavení nové hodnoty
        analyzer.set_velocity_duration(750.0)
        assert analyzer.velocity_duration_ms == 750.0

        # Ošetření rozsahu (min 100ms)
        analyzer.set_velocity_duration(50.0)
        assert analyzer.velocity_duration_ms == 100.0

        # Ošetření rozsahu (max 2000ms)
        analyzer.set_velocity_duration(3000.0)
        assert analyzer.velocity_duration_ms == 2000.0

    def test_calculate_rms(self):
        """Test interní _calculate_rms metody."""
        analyzer = RmsAnalyzer()

        # Test konstantní signál
        signal = np.ones(1000) * 0.5
        rms = analyzer._calculate_rms(signal)
        assert abs(rms - 0.5) < 1e-6

        # Test nulový signál
        signal = np.zeros(1000)
        rms = analyzer._calculate_rms(signal)
        assert rms == 0.0

        # Test prázdný array
        signal = np.array([])
        rms = analyzer._calculate_rms(signal)
        assert rms == 0.0

    def test_to_db_conversion(self):
        """Test převodu amplitude na dB."""
        analyzer = RmsAnalyzer()

        # Test standardních hodnot
        assert abs(analyzer._to_db(1.0) - 0.0) < 1e-6  # 1.0 = 0 dB
        assert abs(analyzer._to_db(0.5) - (-6.02)) < 0.1  # 0.5 ≈ -6 dB
        assert abs(analyzer._to_db(0.1) - (-20.0)) < 0.1  # 0.1 = -20 dB

        # Test velmi malé hodnoty
        assert analyzer._to_db(1e-12) == float('-inf')
        assert analyzer._to_db(0.0) == float('-inf')

    def test_analyze_short_audio(self):
        """Test analýzy velmi krátkého audio (kratšího než velocity_duration)."""
        # 100ms audio při velocity_duration = 500ms
        sample_rate = 44100
        duration = 0.1  # 100ms
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = 0.5 * np.sin(2 * np.pi * 440 * t)

        audio_data = AudioData(waveform, sample_rate, channels=1)

        analyzer = RmsAnalyzer(velocity_duration_ms=500.0)
        result = analyzer.analyze(audio_data)

        # Mělo by analyzovat celých 100ms (vše dostupné)
        assert result.velocity_amplitude is not None
        assert result.velocity_amplitude > 0.0
        expected_rms = 0.5 / np.sqrt(2)
        assert abs(result.velocity_amplitude - expected_rms) < 0.01
