"""
Test script pro zjištění, proč se nenačítají WAV soubory.
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

test_folder = Path(r"C:\SoundBanks\IthacaPlayer\VintageV-sliced")

logger.info(f"Testing folder: {test_folder}")
logger.info(f"Folder exists: {test_folder.exists()}")
logger.info(f"Folder is directory: {test_folder.is_dir()}")

if test_folder.exists() and test_folder.is_dir():
    # Test glob patterns
    supported_extensions = ['*.wav', '*.mp3', '*.flac', '*.aiff', '*.aif']

    for ext in supported_extensions:
        files = list(test_folder.glob(ext))
        logger.info(f"Extension {ext}: found {len(files)} files")
        if files and len(files) < 5:
            for f in files:
                logger.info(f"  - {f.name}")
        elif files:
            logger.info(f"  - (showing first 3): {[f.name for f in files[:3]]}")

    # Test all files
    all_files = list(test_folder.iterdir())
    logger.info(f"Total files in directory: {len(all_files)}")
    wav_files = [f for f in all_files if f.suffix.lower() == '.wav']
    logger.info(f"WAV files (case-insensitive): {len(wav_files)}")

    if wav_files:
        logger.info("First 5 WAV files:")
        for f in wav_files[:5]:
            logger.info(f"  - {f.name}")
