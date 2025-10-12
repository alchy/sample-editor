"""
audio_config.py - Audio a MIDI konstanty
"""

# =============================================================================
# MIDI KONSTANTY
# =============================================================================

class MIDI:
    """MIDI konstanty a rozsahy."""

    # MIDI rozsahy
    MIN_MIDI = 0
    MAX_MIDI = 127

    # Piano rozsah
    PIANO_MIN_MIDI = 21  # A0
    PIANO_MAX_MIDI = 108  # C8

    # Reference nota
    A4_MIDI = 69
    A4_FREQUENCY = 440.0  # Hz

    # Názvy not
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    # Bílé a černé klávesy (pro vizualizaci)
    WHITE_KEYS = {0, 2, 4, 5, 7, 9, 11}  # C, D, E, F, G, A, B
    BLACK_KEYS = {1, 3, 6, 8, 10}  # C#, D#, F#, G#, A#

    # Standard MIDI velocity
    STANDARD_VELOCITY = 80  # Středně silné úhozu
    MIN_VELOCITY = 0
    MAX_VELOCITY = 127


# =============================================================================
# VELOCITY LAYERS
# =============================================================================

class Velocity:
    """Velocity layers konfigurace."""

    # Počet velocity layers
    MIN_LAYERS = 1
    MAX_LAYERS = 8
    DEFAULT_LAYERS = 4

    # Velocity rozsah pro export (0-7)
    EXPORT_MIN = 0
    EXPORT_MAX = 7

    # Velocity level popisy
    LEVEL_DESCRIPTIONS = {
        0: "pppp - Velmi tichý",
        1: "ppp - Velmi tichý až tichý",
        2: "pp - Tichý",
        3: "p - Piano (měkce)",
        4: "mf - Mezzo-forte (středně silně)",
        5: "f - Forte (silně)",
        6: "ff - Velmi silně",
        7: "fff - Fortissimo (velmi silně)",
    }


# =============================================================================
# AUDIO PARAMETRY
# =============================================================================

class Audio:
    """Audio processing parametry."""

    # Sample rates
    SAMPLE_RATE_44K = 44100
    SAMPLE_RATE_48K = 48000
    SAMPLE_RATE_96K = 96000
    DEFAULT_SAMPLE_RATE = SAMPLE_RATE_44K

    # Volume levels (0.0 - 1.0)
    VOLUME_MIDI_TONE = 0.4  # 40% pro MIDI tóny
    VOLUME_SAMPLE = 0.7  # 70% pro audio samples
    VOLUME_MAX = 1.0

    # Duration parametry
    MIDI_TONE_DURATION = 1.0  # 1 sekunda pro MIDI tóny
    MIN_DURATION = 0.1  # Minimální délka
    MAX_DURATION = 10.0  # Maximální délka

    # Fade parametry
    FADE_DURATION = 0.05  # 50ms fade in/out
    FADE_SAMPLES_RATIO = 0.05  # 5% z sample rate

    # Resampling kvalita
    RESAMPLE_QUALITY = 'kaiser_best'  # librosa resampling

    # Audio format
    EXPORT_SUBTYPE = 'PCM_16'  # 16-bit PCM
    EXPORT_BITDEPTH = 16


# =============================================================================
# TIMEOUTY A INTERVALY
# =============================================================================

class Timing:
    """Timeouty a intervaly pro audio operace."""

    # Playback timeouty
    PLAYBACK_CHECK_INTERVAL = 100  # ms - interval kontroly přehrávání
    AUTO_STOP_BUFFER = 100  # ms - buffer pro auto-stop
    STOP_DELAY = 50  # ms - delay před novým přehráním
    PLAYBACK_CLEANUP_DELAY = 50  # ms - delay pro cleanup

    # Queue timeouty
    QUEUE_TIMEOUT_SHORT = 0.1  # 100ms
    QUEUE_TIMEOUT_MEDIUM = 0.5  # 500ms
    QUEUE_TIMEOUT_LONG = 1.0  # 1s
    QUEUE_MAX_SIZE = 10  # Maximální velikost fronty

    # Thread timeouty
    THREAD_SHUTDOWN_TIMEOUT = 1.0  # s
    THREAD_JOIN_TIMEOUT = 2.0  # s

    # Worker loop
    WORKER_LOOP_SLEEP = 0.05  # 50ms

    # UI timeouty
    UI_TIMER_INTERVAL = 10  # ms - interval pro UI updates
    UI_FOCUS_DELAY = 200  # ms - delay před nastavením fokusu
    UI_HIGHLIGHT_DURATION = 1000  # ms - délka highlight efektu


# =============================================================================
# TRANSPOZICE
# =============================================================================

class Transpose:
    """Transpozice konstanty."""

    # Transpozice hodnoty (v semitónech)
    OCTAVE_DOWN = -12
    SEMITONE_DOWN = -1
    SEMITONE_UP = +1
    OCTAVE_UP = +12

    # Rozsah transpozice
    MIN_TRANSPOSE = -36  # 3 oktávy dolů
    MAX_TRANSPOSE = +36  # 3 oktávy nahoru


# =============================================================================
# CHUNK SIZES
# =============================================================================

class ChunkSizes:
    """Velikosti chunků pro čtení a zpracování."""

    # File reading
    FILE_READ_CHUNK = 8192  # 8KB pro hash výpočty

    # Audio buffer
    AUDIO_BUFFER_SIZE = 1024  # Samples per buffer


# =============================================================================
# SAMPLE RATE MAPPING
# =============================================================================

class SampleRateMapping:
    """Mapování sample rates na suffixy pro export."""

    MAPPINGS = {
        44100: 'f44',
        48000: 'f48',
        96000: 'f96',
    }

    @classmethod
    def get_suffix(cls, sample_rate: int) -> str:
        """Získá suffix pro daný sample rate."""
        return cls.MAPPINGS.get(sample_rate, f'f{sample_rate // 1000}')


# =============================================================================
# ANALYSIS PARAMETRY
# =============================================================================

class Analysis:
    """Parametry pro audio analýzu."""

    # CREPE analýza
    CREPE_MAX_DURATION = 5.0  # Analyzovat max 5 sekund
    CREPE_STEP_SIZE = 10  # ms
    CREPE_MODEL_CAPACITY = 'tiny'  # tiny, small, medium, large, full

    # RMS analýza
    RMS_WINDOW_SIZE = 0.5  # 500ms window
    RMS_HOP_LENGTH = 512  # Samples mezi okny

    # Amplitude range
    RMS_MIN_THRESHOLD = 0.001  # Minimální práh pro RMS
    RMS_MAX_THRESHOLD = 1.0  # Maximální hodnota RMS


# =============================================================================
# FILE PATTERNS
# =============================================================================

class FilePatterns:
    """Vzory pro názvy souborů."""

    # Export pattern
    EXPORT_PATTERN = "m{midi:03d}-vel{velocity}-{sr_suffix}.wav"

    # Cleanup pattern
    CLEANUP_PATTERN = "m*-vel*-f*.wav"

    # MIDI format v názvu
    MIDI_FORMAT_PATTERN = "{:03d}"  # 000-127
