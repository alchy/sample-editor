"""
Test SessionManager.analyze_with_cache
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from session_manager import SessionManager
from models import SampleMetadata

# Create and load existing session
session_mgr = SessionManager()
loaded = session_mgr.load_session("VintageV Electric Piano - verze 1")

logger.info(f"Session loaded: {loaded}")
logger.info(f"Session data: {session_mgr.session_data is not None}")

if loaded:
    # Get test folder from session
    test_folder_str = session_mgr.session_data["folders"]["input"]
    test_folder = Path(test_folder_str)

    logger.info(f"Input folder from session: {test_folder}")
    logger.info(f"Input folder exists: {test_folder.exists()}")

    # Find first 5 WAV files
    wav_files = list(test_folder.glob("*.wav"))[:5]
    logger.info(f"Found {len(wav_files)} test files")

    # Create SampleMetadata objects
    samples = [SampleMetadata(f) for f in wav_files]

    logger.info(f"Created {len(samples)} SampleMetadata objects")

    for s in samples[:2]:
        logger.info(f"  Sample: {s.filename}")
        logger.info(f"    filepath: {s.filepath}")
        logger.info(f"    filepath type: {type(s.filepath)}")
        logger.info(f"    filepath.exists(): {s.filepath.exists()}")

    # Call analyze_with_cache
    logger.info("\n=== CALLING analyze_with_cache ===")
    cached, to_analyze = session_mgr.analyze_with_cache(samples)

    logger.info(f"Result: {len(cached)} cached, {len(to_analyze)} to analyze")
