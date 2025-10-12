"""
export_config.py - Export konstanty a parametry
"""

from typing import List, Tuple

# =============================================================================
# EXPORT FORMÁTY
# =============================================================================

class ExportFormats:
    """Podporované export formáty a sample rates."""

    # Sample rate formáty: (sample_rate, suffix)
    FORMATS: List[Tuple[int, str]] = [
        (44100, 'f44'),
        (48000, 'f48'),
    ]

    # Default formát
    DEFAULT_FORMAT = (44100, 'f44')

    # Dostupné sample rates
    SAMPLE_RATES = [fmt[0] for fmt in FORMATS]

    @classmethod
    def get_suffix(cls, sample_rate: int) -> str:
        """Získá suffix pro daný sample rate."""
        for sr, suffix in cls.FORMATS:
            if sr == sample_rate:
                return suffix
        return f'f{sample_rate // 1000}'


# =============================================================================
# EXPORT PROGRESS
# =============================================================================

class ExportProgress:
    """Progress hodnoty pro export operace."""

    # Progress milníky (0-100%)
    INITIAL = 0
    VALIDATION = 5
    FOLDER_CHECK = 10
    START_EXPORT = 15
    COMPLETED = 100

    # Export progress rozsah
    EXPORT_RANGE = 80  # 15% až 95% (80% rozpětí)


# =============================================================================
# EXPORT VALIDACE
# =============================================================================

class ExportValidation:
    """Validační konstanty pro export."""

    # Velocity rozsah
    MIN_VELOCITY = 0
    MAX_VELOCITY = 7

    # MIDI rozsah
    MIN_MIDI = 0
    MAX_MIDI = 127

    # Minimální počet samples pro export
    MIN_SAMPLES = 1


# =============================================================================
# ERROR ZPRÁVY
# =============================================================================

class ExportErrors:
    """Error zprávy pro export operace."""

    NO_SAMPLES = "Žádné samples k exportu"
    INVALID_MAPPING = "Neplatné mapování: {error}"
    FOLDER_NOT_WRITABLE = "Výstupní složka není dostupná pro zápis"
    FOLDER_CREATE_ERROR = "Nelze vytvořit výstupní složku: {error}"
    EXPORT_FAILED = "Export selhal: {error}"
    NO_MAPPED_SAMPLES = "Žádné samples nejsou namapované"
    MISSING_LIBRARIES = "Chybí požadované knihovny pro export: {library}"


# =============================================================================
# FILE NAMING
# =============================================================================

class ExportFileNaming:
    """Vzory pro názvy exportovaných souborů."""

    # Pattern pro názvy souborů
    # Formát: m{MIDI}-vel{velocity}-{sample_rate_suffix}.wav
    # Příklad: m060-vel4-f44.wav
    FILENAME_PATTERN = "m{midi:03d}-vel{velocity}-{sr_suffix}.wav"

    # Pattern pro cleanup (wildcards)
    CLEANUP_PATTERN = "m*-vel*-f*.wav"

    # Separátory
    SEPARATOR_MIDI = "m"
    SEPARATOR_VEL = "-vel"
    SEPARATOR_SR = "-"

    # Formát MIDI čísla v názvu
    MIDI_DIGITS = 3  # 000-127


# =============================================================================
# AUDIO EXPORT PARAMETRY
# =============================================================================

class AudioExportParams:
    """Audio parametry pro export."""

    # Resampling
    RESAMPLE_QUALITY = 'kaiser_best'  # librosa kvalita

    # Audio formát
    FORMAT_WAV = 'WAV'
    SUBTYPE_PCM16 = 'PCM_16'
    BITDEPTH = 16

    # Normalizace
    NORMALIZE = True
    NORMALIZE_LEVEL = 0.95  # 95% maximální amplitudy


# =============================================================================
# BATCH PROCESSING
# =============================================================================

class BatchProcessing:
    """Parametry pro batch zpracování při exportu."""

    # Chunk size pro batch processing
    BATCH_SIZE = 10  # Zpracovat 10 samples najednou

    # Update interval pro progress
    PROGRESS_UPDATE_INTERVAL = 1  # Update každý sample

    # Retry parametry
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # sekundy mezi retry


# =============================================================================
# EXPORT STATISTICS
# =============================================================================

class ExportStatistics:
    """Formátování statistik exportu."""

    TEMPLATE_BASIC = "Export dokončen: {exported}/{total} samples"
    TEMPLATE_DETAILED = """Export completed!

Exported: {exported_count} samples
Total files: {total_files}
Folder: {output_folder}"""
    TEMPLATE_WITH_ERRORS = "\n\nErrors: {failed_count} samples"
    TEMPLATE_STATUS = "Exportuji: {current}/{total} samples ({percentage}%)"
