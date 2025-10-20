"""
Test pro SampleMetadata konstrukci.
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import models
from models import SampleMetadata

test_folder = Path(r"C:\SoundBanks\IthacaPlayer\VintageV-sliced")

# Najdi pár WAV souborů
wav_files = list(test_folder.glob("*.wav"))[:5]

logger.info(f"Testing with {len(wav_files)} WAV files")

for wav_file in wav_files:
    logger.info(f"\nTesting file: {wav_file}")
    logger.info(f"  File exists: {wav_file.exists()}")
    logger.info(f"  Is file: {wav_file.is_file()}")

    # Vytvoř SampleMetadata
    sample = SampleMetadata(wav_file)
    logger.info(f"  Created SampleMetadata:")
    logger.info(f"    filepath: {sample.filepath}")
    logger.info(f"    filepath type: {type(sample.filepath)}")
    logger.info(f"    filepath.exists(): {sample.filepath.exists()}")
    logger.info(f"    filename: {sample.filename}")
