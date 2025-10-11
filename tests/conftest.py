"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
from pathlib import Path
import tempfile
import shutil

# Přidej src do Python path pro importy
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_dir():
    """Vytvoří dočasný adresář pro testy."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_audio_dir():
    """Cesta k test audio samples."""
    return Path(r"C:\SoundBanks\IthacaPlayer\VintageV-sliced")


@pytest.fixture
def mock_wav_file(temp_dir):
    """Vytvoří mock WAV soubor pro testy."""
    import wave
    import numpy as np
    
    wav_path = temp_dir / "test_sample.wav"
    
    # Vytvoř jednoduchý WAV soubor (440Hz sine wave, 1s)
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = np.sin(2 * np.pi * frequency * t)
    samples = (samples * 32767).astype(np.int16)
    
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    return wav_path


@pytest.fixture
def sample_metadata_factory():
    """Factory pro vytváření SampleMetadata objektů v testech."""
    from src.domain.models import SampleMetadata
    
    def create_sample(
        filename: str = "test.wav",
        midi: int = None,
        velocity_amplitude: float = None,
        analyzed: bool = False
    ):
        # Vytvoř dočasný soubor
        temp_path = Path(tempfile.gettempdir()) / filename
        temp_path.touch()
        
        sample = SampleMetadata(temp_path)
        if midi is not None:
            sample.detected_midi = midi
            sample.detected_frequency = 440.0 * (2 ** ((midi - 69) / 12))
            sample.pitch_confidence = 0.95
            sample.pitch_method = "test"
        
        if velocity_amplitude is not None:
            sample.velocity_amplitude = velocity_amplitude
            sample.velocity_amplitude_db = 20 * np.log10(velocity_amplitude) if velocity_amplitude > 0 else -96
        
        sample.analyzed = analyzed
        return sample
    
    return create_sample
