"""
config - Centrální konfigurace pro Sample Mapping Editor

Použití:
    from config import AUDIO, EXPORT, APP
"""

from .audio_config import (
    MIDI,
    Velocity,
    Audio,
    Timing,
    Transpose,
    ChunkSizes,
    SampleRateMapping,
    Analysis,
    FilePatterns as AudioFilePatterns,
)

from .export_config import (
    ExportFormats,
    ExportProgress,
    ExportValidation,
    ExportErrors,
    ExportFileNaming,
    AudioExportParams,
    BatchProcessing,
    ExportStatistics,
)

from .app_config import (
    AppInfo,
    CacheConfig,
    SessionConfig,
    FileFilters,
    UpdateIntervals,
    BatchConfig,
    LoggingConfig,
    Paths,
    ValidationRules,
    Defaults,
)

class AUDIO:
    """Audio konfigurace - MIDI, audio parametry, timing."""
    MIDI = MIDI
    Velocity = Velocity
    Audio = Audio
    Timing = Timing
    Transpose = Transpose
    ChunkSizes = ChunkSizes
    SampleRateMapping = SampleRateMapping
    Analysis = Analysis
    FilePatterns = AudioFilePatterns


class EXPORT:
    """Export konfigurace - formáty, validace, file naming."""
    Formats = ExportFormats
    Progress = ExportProgress
    Validation = ExportValidation
    Errors = ExportErrors
    FileNaming = ExportFileNaming
    AudioParams = AudioExportParams
    Batch = BatchProcessing
    Statistics = ExportStatistics


class APP:
    """Aplikační konfigurace - cache, sessions, logging."""
    Info = AppInfo
    Cache = CacheConfig
    Session = SessionConfig
    FileFilters = FileFilters
    UpdateIntervals = UpdateIntervals
    Batch = BatchConfig
    Logging = LoggingConfig
    Paths = Paths
    Validation = ValidationRules
    Defaults = Defaults


# Platform-specific sessions directory
import sys
import os
from pathlib import Path
from platformdirs import user_data_dir
import logging

logger = logging.getLogger(__name__)

# Create platform-specific sessions directory
SESSIONS_DIR = Path(user_data_dir(
    appname="IthacaSampleEditorSessions",
    appauthor="LordAudio",
    ensure_exists=True
))

# Log sessions directory configuration
logger.info(f"━━━ Sessions Configuration ━━━")
logger.info(f"Platform: {sys.platform}")
logger.info(f"Sessions directory: {SESSIONS_DIR}")
logger.info(f"Directory exists: {SESSIONS_DIR.exists()}")
if SESSIONS_DIR.exists():
    logger.info(f"Directory writable: {os.access(SESSIONS_DIR, os.W_OK)}")

# Version info
__version__ = AppInfo.VERSION
__all__ = [
    'AUDIO',
    'EXPORT',
    'APP',
    'SESSIONS_DIR',
    'MIDI',
    'Velocity',
    'Audio',
    'Timing',
    'Transpose',
    'ChunkSizes',
    'SampleRateMapping',
    'Analysis',
    'AudioFilePatterns',
    'ExportFormats',
    'ExportProgress',
    'ExportValidation',
    'ExportErrors',
    'ExportFileNaming',
    'AudioExportParams',
    'BatchProcessing',
    'ExportStatistics',
    'AppInfo',
    'CacheConfig',
    'SessionConfig',
    'FileFilters',
    'UpdateIntervals',
    'BatchConfig',
    'LoggingConfig',
    'Paths',
    'ValidationRules',
    'Defaults',
]
