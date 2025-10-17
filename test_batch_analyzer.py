"""
Test SessionAwareBatchAnalyzer - simulace GUI flow
"""
from pathlib import Path
import logging
import sys
from PySide6.QtCore import QCoreApplication

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from session_manager import SessionManager
from session_aware_analyzer import SessionAwareBatchAnalyzer

# Qt application (needed for QThread)
app = QCoreApplication(sys.argv)

# Load session
session_mgr = SessionManager()
loaded = session_mgr.load_session("VintageV Electric Piano - verze 1")

if not loaded:
    logger.error("Failed to load session")
    sys.exit(1)

logger.info("Session loaded successfully")

# Get input folder
test_folder_str = session_mgr.session_data["folders"]["input"]
test_folder = Path(test_folder_str)

logger.info(f"Input folder: {test_folder}")

# Create analyzer
logger.info("Creating SessionAwareBatchAnalyzer...")
analyzer = SessionAwareBatchAnalyzer(test_folder, session_mgr)

# Connect signals
def on_progress(percentage, message):
    logger.info(f"Progress: {percentage}% - {message}")

def on_sample_analyzed(sample, range_info):
    logger.info(f"Sample analyzed: {sample.filename}")
    logger.info(f"  - detected_midi: {sample.detected_midi}")
    logger.info(f"  - detected_frequency: {sample.detected_frequency}")
    logger.info(f"  - velocity_amplitude: {sample.velocity_amplitude}")

def on_completed(samples, range_info):
    logger.info(f"\n=== ANALYSIS COMPLETED ===")
    logger.info(f"Total samples: {len(samples)}")
    logger.info(f"Range info: {range_info}")

    # Quit app
    app.quit()

analyzer.progress_updated.connect(on_progress)
analyzer.sample_analyzed.connect(on_sample_analyzed)
analyzer.analysis_completed.connect(on_completed)

# Start analysis
logger.info("Starting analysis...")
analyzer.start()

# Run Qt event loop
sys.exit(app.exec())
