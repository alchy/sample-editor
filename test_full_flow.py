"""
Test celého workflow pro zjištění problému.
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import session manager
from session_manager import SessionManager
from session_aware_analyzer import SessionAwareBatchAnalyzer

# Create session
logger.info("=== CREATING SESSION ===")
session_mgr = SessionManager()
session_mgr.create_new_session("test_session", velocity_layers=4)

# Set input folder
test_folder = Path(r"C:\SoundBanks\IthacaPlayer\VintageV-sliced")
session_mgr.save_folders(input_folder=test_folder)

logger.info(f"Session name: {session_mgr.current_session}")
logger.info(f"Input folder: {test_folder}")

# Create analyzer
logger.info("\n=== CREATING ANALYZER ===")
analyzer = SessionAwareBatchAnalyzer(test_folder, session_mgr)

# Find audio files
logger.info("\n=== FINDING AUDIO FILES ===")
audio_files = analyzer._find_unique_audio_files()
logger.info(f"Found {len(audio_files)} files")

if audio_files:
    # Test cache checking
    logger.info("\n=== TESTING CACHE ===")
    from models import SampleMetadata

    # Create sample metadata for first 5 files
    test_samples = [SampleMetadata(f) for f in audio_files[:5]]

    logger.info(f"Created {len(test_samples)} SampleMetadata objects")

    # Check with cache
    cached, to_analyze = session_mgr.session_service.analyze_with_cache(test_samples)

    logger.info(f"Cache result: {len(cached)} cached, {len(to_analyze)} to analyze")
