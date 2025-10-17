"""
Test error handling - simulace chybějícího modulu
"""
from pathlib import Path
import logging
import sys
from PySide6.QtCore import QCoreApplication

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

# Test jen s prvními 5 soubory
test_files = list(test_folder.glob("*.wav"))[:5]
logger.info(f"Testing with {len(test_files)} files")

# Create temp folder for test
import tempfile
temp_dir = Path(tempfile.mkdtemp())

# Copy files
import shutil
for f in test_files:
    shutil.copy(f, temp_dir / f.name)

logger.info(f"Test folder: {temp_dir}")

# Create analyzer
logger.info("Creating SessionAwareBatchAnalyzer...")
analyzer = SessionAwareBatchAnalyzer(temp_dir, session_mgr)

# Connect signals
def on_progress(percentage, message):
    logger.info(f"Progress: {percentage}% - {message}")

def on_error(error_message):
    logger.info(f"\n{'='*60}")
    logger.info("ERROR SIGNAL RECEIVED:")
    logger.info(f"{'='*60}")
    logger.info(error_message)
    logger.info(f"{'='*60}\n")
    app.quit()

def on_completed(samples, range_info):
    logger.info(f"\nAnalysis completed: {len(samples)} samples")
    if len(samples) > 0:
        logger.info("✓ SUCCESS - samples were analyzed")
    else:
        logger.info("✗ NO SAMPLES - error should have been emitted")
    app.quit()

analyzer.progress_updated.connect(on_progress)
analyzer.analysis_error.connect(on_error)
analyzer.analysis_completed.connect(on_completed)

# Start analysis
logger.info("Starting analysis...")
analyzer.start()

# Run Qt event loop
sys.exit(app.exec())
