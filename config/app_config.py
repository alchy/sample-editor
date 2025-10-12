"""
app_config.py - Obecné aplikační konstanty (cache, session management, atd.)
"""

from pathlib import Path

# =============================================================================
# APLIKAČNÍ METADATA
# =============================================================================

class AppInfo:
    """Informace o aplikaci."""

    NAME = "Sample Mapping Editor"
    VERSION = "2.0"
    FULL_NAME = "Sample Mapping Editor - Professional Version"

    # Credits
    DESCRIPTION = """Professional sample mapping tool with:
• CREPE pitch detection
• RMS velocity analysis
• Hash-based session caching
• Drag & drop interface
• Multi-format export

Built with PySide6 and Python"""


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

class CacheConfig:
    """Konfigurace pro cache management."""

    # Cache version
    CACHE_VERSION = "2.0"

    # Save interval
    SAVE_INTERVAL = 50  # Ulož cache každých 50 zápisů

    # Chunk sizes
    FILE_CHUNK_SIZE = 8192  # 8KB pro čtení souborů (hash)

    # Cache file naming
    CACHE_FILENAME = "cache.json"
    CACHE_BACKUP_SUFFIX = ".backup"


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

class SessionConfig:
    """Konfigurace pro session management."""

    # Session adresář
    SESSION_DIR_NAME = "sessions"

    # Default parametry
    DEFAULT_VELOCITY_LAYERS = 4
    MIN_VELOCITY_LAYERS = 1
    MAX_VELOCITY_LAYERS = 8

    # Session file format
    SESSION_FILE_EXTENSION = ".json"
    SESSION_BACKUP_EXTENSION = ".json.backup"

    # Invalid characters v názvech sessions
    INVALID_CHARS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']


# =============================================================================
# FILE PATTERNS & FILTERS
# =============================================================================

class FileFilters:
    """File filtry a patterns."""

    # Audio formáty
    AUDIO_EXTENSIONS = ['.wav', '.mp3', '.flac', '.aiff', '.ogg']

    # Hlavní audio formát
    PRIMARY_FORMAT = '.wav'

    # Session file pattern
    SESSION_PATTERN = "*.json"


# =============================================================================
# UI UPDATE INTERVALS
# =============================================================================

class UpdateIntervals:
    """Intervaly pro UI updates."""

    # Sample list batch updates
    SAMPLE_LIST_UPDATE_BATCH = 10  # Update UI každých 10 samples

    # Progress updates
    PROGRESS_UPDATE_INTERVAL = 100  # ms

    # Status updates
    STATUS_UPDATE_THROTTLE = 50  # ms


# =============================================================================
# BATCH PROCESSING
# =============================================================================

class BatchConfig:
    """Konfigurace pro batch processing."""

    # Analysis batch size
    ANALYSIS_BATCH_SIZE = 10

    # Progress reporting
    PROGRESS_REPORT_EVERY = 1  # Report každý sample


# =============================================================================
# LOGGING
# =============================================================================

class LoggingConfig:
    """Logging konfigurace."""

    # Log level (bude použito v main.py)
    DEFAULT_LEVEL = "INFO"

    # Log format
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

    # Log file (pokud je potřeba)
    LOG_FILE = "sample_mapping_editor.log"


# =============================================================================
# PATHS
# =============================================================================

class Paths:
    """Cesty v aplikaci."""

    @staticmethod
    def get_sessions_dir() -> Path:
        """Vrátí cestu k sessions adresáři."""
        return Path.cwd() / SessionConfig.SESSION_DIR_NAME

    @staticmethod
    def get_session_file(session_name: str) -> Path:
        """Vrátí cestu k session souboru."""
        return Paths.get_sessions_dir() / f"{session_name}{SessionConfig.SESSION_FILE_EXTENSION}"

    @staticmethod
    def get_cache_file(session_name: str) -> Path:
        """Vrátí cestu k cache souboru."""
        return Paths.get_sessions_dir() / session_name / CacheConfig.CACHE_FILENAME


# =============================================================================
# VALIDATION
# =============================================================================

class ValidationRules:
    """Validační pravidla."""

    # Session name
    MIN_SESSION_NAME_LENGTH = 1
    MAX_SESSION_NAME_LENGTH = 100

    # File paths
    MAX_PATH_LENGTH = 260  # Windows MAX_PATH

    # Sample validation
    MIN_SAMPLE_DURATION = 0.01  # 10ms minimum
    MAX_SAMPLE_DURATION = 60.0  # 1 minuta maximum


# =============================================================================
# DEFAULT VALUES
# =============================================================================

class Defaults:
    """Default hodnoty pro různé části aplikace."""

    # Sample metadata
    DEFAULT_MIDI = 60  # Middle C
    DEFAULT_RMS = 0.5
    DEFAULT_VELOCITY = 4  # Střední velocity layer

    # Analysis
    DEFAULT_CREPE_CONFIDENCE = 0.0  # Minimální confidence

    # Export
    DEFAULT_SAMPLE_RATE = 44100
