# -*- coding: utf-8 -*-
"""Unit tests for SampleMetadata domain model."""
import pytest
from pathlib import Path

@pytest.mark.unit
class TestSampleMetadata:
    def test_initialization(self, tmp_path):
        from src.domain.models import SampleMetadata
        test_file = tmp_path / "test.wav"
        test_file.touch()
        sample = SampleMetadata(test_file)
        assert sample.filename == "test.wav"
        assert sample.analyzed is False

    def test_valid_for_mapping(self, tmp_path):
        from src.domain.models import SampleMetadata
        test_file = tmp_path / "test.wav"
        test_file.touch()
        sample = SampleMetadata(test_file)
        sample.analyzed = True
        sample.detected_midi = 60
        assert sample.is_valid_for_mapping() is True
