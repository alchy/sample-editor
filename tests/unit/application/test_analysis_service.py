"""
Unit testy pro AnalysisService.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock

from src.domain.models.sample import SampleMetadata
from src.domain.interfaces.audio_analyzer import (
    AudioData,
    PitchAnalysisResult,
    AmplitudeAnalysisResult
)
from src.application.services.analysis_service import AnalysisService


@pytest.mark.unit
class TestAnalysisService:
    """Testy pro Analysis Service."""

    def test_initialization(self):
        """Test inicializace service."""
        audio_loader = Mock()
        pitch_analyzer = Mock()
        amplitude_analyzer = Mock()

        service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)
        assert service is not None
        assert service.audio_loader == audio_loader
        assert service.pitch_analyzer == pitch_analyzer
        assert service.amplitude_analyzer == amplitude_analyzer

    def test_analyze_sample_success(self, tmp_path):
        """Test úspěšné analýzy sample."""
        # Setup mocks
        audio_loader = Mock()
        pitch_analyzer = Mock()
        amplitude_analyzer = Mock()

        # Mock audio data
        sample_rate = 44100
        waveform = np.random.randn(44100)  # 1s random audio
        audio_data = AudioData(waveform, sample_rate, channels=1)
        audio_loader.load.return_value = audio_data

        # Mock pitch result
        pitch_result = PitchAnalysisResult(
            detected_midi=60,
            detected_frequency=261.63,
            confidence=0.95,
            method="crepe"
        )
        pitch_analyzer.analyze.return_value = pitch_result

        # Mock amplitude result
        amplitude_result = AmplitudeAnalysisResult(
            velocity_amplitude=0.5,
            velocity_amplitude_db=-6.0,
            velocity_duration_ms=500.0,
            rms_amplitude=0.4,
            peak_amplitude=0.8
        )
        amplitude_analyzer.analyze.return_value = amplitude_result

        # Create service
        service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)

        # Create test sample
        test_file = tmp_path / "test.wav"
        test_file.touch()
        sample = SampleMetadata(test_file)

        # Analyze
        result = service.analyze_sample(sample)

        # Assertions
        assert result is True
        assert sample.analyzed is True
        assert sample.detected_midi == 60
        assert sample.detected_frequency == 261.63
        assert sample.velocity_amplitude == 0.5

        # Verify mocks were called
        audio_loader.load.assert_called_once_with(test_file)
        pitch_analyzer.analyze.assert_called_once()
        amplitude_analyzer.analyze.assert_called_once()

    def test_analyze_sample_audio_load_failure(self, tmp_path):
        """Test chyby při načítání audio."""
        # Setup mocks
        audio_loader = Mock()
        pitch_analyzer = Mock()
        amplitude_analyzer = Mock()

        # Mock audio loader failure
        audio_loader.load.return_value = None

        service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)

        # Create test sample
        test_file = tmp_path / "test.wav"
        test_file.touch()
        sample = SampleMetadata(test_file)

        # Analyze
        result = service.analyze_sample(sample)

        # Should fail
        assert result is False
        assert sample.analyzed is False
        assert sample.detected_midi is None

        # Pitch/amplitude analyzers should NOT be called
        pitch_analyzer.analyze.assert_not_called()
        amplitude_analyzer.analyze.assert_not_called()

    def test_analyze_sample_pitch_detection_failure(self, tmp_path):
        """Test chyby při pitch detekci."""
        # Setup mocks
        audio_loader = Mock()
        pitch_analyzer = Mock()
        amplitude_analyzer = Mock()

        # Mock audio data
        audio_data = AudioData(np.random.randn(44100), 44100, channels=1)
        audio_loader.load.return_value = audio_data

        # Mock pitch detection failure (no MIDI detected)
        pitch_result = PitchAnalysisResult(
            detected_midi=None,
            detected_frequency=None,
            confidence=0.1,
            method="crepe"
        )
        pitch_analyzer.analyze.return_value = pitch_result

        service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)

        # Create test sample
        test_file = tmp_path / "test.wav"
        test_file.touch()
        sample = SampleMetadata(test_file)

        # Analyze
        result = service.analyze_sample(sample)

        # Should fail
        assert result is False
        assert sample.detected_midi is None

        # Amplitude analyzer should NOT be called (failure early)
        amplitude_analyzer.analyze.assert_not_called()

    def test_analyze_batch(self, tmp_path):
        """Test batch analýzy."""
        # Setup mocks
        audio_loader = Mock()
        pitch_analyzer = Mock()
        amplitude_analyzer = Mock()

        # Mock successful analysis
        audio_data = AudioData(np.random.randn(44100), 44100, channels=1)
        audio_loader.load.return_value = audio_data

        pitch_result = PitchAnalysisResult(
            detected_midi=60, detected_frequency=261.63, confidence=0.95, method="crepe"
        )
        pitch_analyzer.analyze.return_value = pitch_result

        amplitude_result = AmplitudeAnalysisResult(
            velocity_amplitude=0.5, velocity_amplitude_db=-6.0,
            velocity_duration_ms=500.0, rms_amplitude=0.4, peak_amplitude=0.8
        )
        amplitude_analyzer.analyze.return_value = amplitude_result

        service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)

        # Create 3 test samples
        samples = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.wav"
            test_file.touch()
            samples.append(SampleMetadata(test_file))

        # Track progress
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        # Analyze batch
        successful, failed = service.analyze_batch(samples, progress_callback)

        # All should succeed
        assert successful == 3
        assert failed == 0

        # Check progress callbacks
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)

    def test_get_audio_info(self, tmp_path):
        """Test získání audio info."""
        audio_loader = Mock()
        pitch_analyzer = Mock()
        amplitude_analyzer = Mock()

        # Mock audio info
        expected_info = {
            "duration": 2.5,
            "sample_rate": 44100,
            "channels": 2,
            "frames": 110250
        }
        audio_loader.get_audio_info.return_value = expected_info

        service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)

        # Get info
        test_file = tmp_path / "test.wav"
        test_file.touch()
        info = service.get_audio_info(test_file)

        # Assertions
        assert info == expected_info
        audio_loader.get_audio_info.assert_called_once_with(test_file)
