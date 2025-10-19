"""
gui_config.py - GUI konstanty (barvy, rozměry, texty, styly)
"""

# =============================================================================
# BARVY - COLOR PALETTE
# =============================================================================

class Colors:
    """Centrální paleta barev pro celou aplikaci."""

    # Modrá škála (primární)
    BLUE_PRIMARY = "#2196F3"
    BLUE_DARK = "#1976D2"
    BLUE_DARKER = "#0D47A1"
    BLUE_LIGHT = "#e3f2fd"
    BLUE_LIGHT_BG = "#f3f8ff"

    # Zelená škála (úspěch, play)
    GREEN_PRIMARY = "#4CAF50"
    GREEN_DARK = "#45a049"
    GREEN_DARKER = "#388e3c"
    GREEN_LIGHT = "#e8f5e9"
    GREEN_SUCCESS = "#27ae60"
    GREEN_SUCCESS_LIGHT = "#2ecc71"

    # Červená škála (varování, delete)
    RED_PRIMARY = "#e74c3c"
    RED_DARK = "#c0392b"
    RED_ERROR = "#f44336"
    RED_ERROR_DARK = "#d32f2f"

    # Fialová škála (MIDI, speciální)
    PURPLE_PRIMARY = "#ab47bc"
    PURPLE_DARK = "#7b1fa2"
    PURPLE_LIGHT = "#f3e5f5"
    PURPLE_PINK = "#ec407a"
    PURPLE_PINK_DARK = "#d81b60"

    # Oranžová škála (assign, transpozice)
    ORANGE_PRIMARY = "#ff9800"
    ORANGE_DARK = "#f57c00"
    ORANGE_LIGHT = "#ffa726"
    ORANGE_BG = "#fff9e6"

    # Šedá škála (neutrální, disabled)
    GRAY_LIGHTEST = "#f8f8f8"
    GRAY_LIGHTER = "#f5f5f5"
    GRAY_LIGHT = "#f0f0f0"
    GRAY_MEDIUM_LIGHT = "#e0e0e0"
    GRAY_MEDIUM = "#cccccc"
    GRAY_MEDIUM_DARK = "#bdc3c7"
    GRAY_DARK = "#7f8c8d"
    GRAY_DARKER = "#666666"
    GRAY_DARKEST = "#2c3e50"

    # Bílá a černá
    WHITE = "#ffffff"
    BLACK = "#000000"

    # Průhlednost (pro drag operations)
    DRAG_OVERLAY_ALPHA = 200  # 0-255


# =============================================================================
# ROZMĚRY - DIMENSIONS
# =============================================================================

class Dimensions:
    """Rozměry widgetů a layoutů."""

    # Hlavní okno
    MAIN_WINDOW_WIDTH = 1600
    MAIN_WINDOW_HEIGHT = 900

    # Panely a sekce
    CONTROL_PANEL_HEIGHT = 60
    STATUS_PANEL_HEIGHT = 120
    AUDIO_PLAYER_HEIGHT = 150

    # Sample list
    SAMPLE_LIST_MIN_WIDTH = 250
    SAMPLE_LIST_MAX_WIDTH = 650

    # Mapping matrix
    MATRIX_MIN_WIDTH = 800
    MATRIX_MIN_HEIGHT = 600

    # Splitter poměry (40/60)
    SPLITTER_LEFT_SIZE = 640
    SPLITTER_RIGHT_SIZE = 960
    SPLITTER_LEFT_FACTOR = 4
    SPLITTER_RIGHT_FACTOR = 6

    # Sample item widget
    ITEM_HEIGHT = 32
    ITEM_HEIGHT_COMPACT = 25

    # Buttony
    BTN_DRAG_WIDTH = 95  # Width for icon + text drag button with padding
    BTN_DRAG_HEIGHT = 30
    BTN_PLAY_WIDTH = 36
    BTN_PLAY_HEIGHT = 24
    BTN_PLAY_COMPACT_WIDTH = 20
    BTN_TRANSPOSE_WIDTH = 28
    BTN_TRANSPOSE_HEIGHT = 24
    BTN_TRANSPOSE_COMPACT_WIDTH = 25
    BTN_EXPORT_WIDTH = 80
    BTN_CANCEL_WIDTH = 80

    # Labely
    LABEL_MIDI_NUMBER_WIDTH = 45
    LABEL_NOTE_NAME_WIDTH = 45
    LABEL_RMS_WIDTH = 100
    LABEL_MIDI_COMPACT_WIDTH = 50

    # Checkbox
    CHECKBOX_WIDTH = 25

    # Transpose frame
    TRANSPOSE_FRAME_WIDTH = 135

    # Play frame
    PLAY_FRAME_WIDTH = 85

    # Inline editor
    INLINE_EDITOR_HEIGHT = 25

    # Drag pixmap
    DRAG_PIXMAP_WIDTH = 280
    DRAG_PIXMAP_HEIGHT = 90

    # Session dialog
    SESSION_DIALOG_WIDTH = 600
    SESSION_DIALOG_HEIGHT = 450
    SESSION_INPUT_MIN_WIDTH = 400


# =============================================================================
# SPACING A MARGINS
# =============================================================================

class Spacing:
    """Spacing a margins pro layouty."""

    # Margins
    MARGIN_TINY = 2
    MARGIN_SMALL = 3
    MARGIN_MEDIUM = 4
    MARGIN_LARGE = 10
    MARGIN_XLARGE = 20

    # Spacing
    SPACING_TINY = 2
    SPACING_SMALL = 3
    SPACING_MEDIUM = 4

    # Padding
    PADDING_SMALL = "8px"
    PADDING_MEDIUM = "10px"
    PADDING_BUTTON = "10px 20px"


# =============================================================================
# FONT VELIKOSTI
# =============================================================================

class Fonts:
    """Font velikosti a styly."""

    # Velikosti
    SIZE_TINY = 9
    SIZE_SMALL = 10
    SIZE_MEDIUM = 11
    SIZE_NORMAL = 12
    SIZE_LARGE = 14
    SIZE_XLARGE = 16

    # Ikony (větší pro lepší čitelnost)
    SIZE_ICON = 14

    # Font rodiny
    FAMILY_MAIN = "Arial"

    # Letter spacing
    LETTER_SPACING_TIGHT = "-1px"


# =============================================================================
# TEXTY - UI STRINGS
# =============================================================================

class Texts:
    """All UI text strings."""

    # Main window
    WINDOW_TITLE = "Sample Mapping Editor for Ithaca Player"
    WINDOW_READY = "Ready"

    # Menu
    MENU_FILE = "&File"
    MENU_EDIT = "&Edit"
    MENU_VIEW = "&View"
    MENU_PLAYBACK = "&Playback"
    MENU_HELP = "&Help"

    # File menu
    ACTION_NEW_SESSION = "&New Session..."
    ACTION_INPUT_FOLDER = "Set &Input Folder..."
    ACTION_OUTPUT_FOLDER = "Set &Output Folder..."
    ACTION_EXPORT = "&Export Samples"
    ACTION_EXIT = "E&xit"

    # Edit menu
    ACTION_CLEAR_MATRIX = "&Clear Matrix"

    # View menu
    ACTION_REFRESH = "&Refresh Samples"
    ACTION_SORT = "Sort by &MIDI and RMS"

    # Playback menu
    ACTION_PLAY_SAMPLE = "&Play Current Sample"
    ACTION_PLAY_MIDI_TONE = "Play Reference &MIDI Tone"
    ACTION_STOP = "&Stop Playback"

    # Help menu
    ACTION_ABOUT = "&About"

    # Status tips
    TIP_NEW_SESSION = "Create a new session"
    TIP_INPUT_FOLDER = "Select folder containing audio samples"
    TIP_OUTPUT_FOLDER = "Select output folder for exported samples"
    TIP_EXPORT = "Export mapped samples to output folder"
    TIP_EXIT = "Exit application"
    TIP_CLEAR_MATRIX = "Clear all mapped samples from matrix"
    TIP_REFRESH = "Refresh sample list"
    TIP_SORT = "Sort samples by MIDI note and RMS amplitude"
    TIP_PLAY_SAMPLE = "Play the currently selected sample"
    TIP_PLAY_MIDI_TONE = "Play reference MIDI tone for comparison"
    TIP_STOP = "Stop audio playback"
    TIP_ABOUT = "About Sample Mapping Editor"

    # Control panel
    CONTROL_PANEL_TITLE = "Session & Export"
    SESSION_LABEL = "Session:"
    SESSION_NO_SESSION = "No session"
    BTN_EXPORT = "Export"
    BTN_CANCEL = "Cancel"

    # Status panel
    STATUS_PANEL_TITLE = "Status"
    STATUS_READY = "Ready. Please select a session to begin."
    STATUS_NO_SAMPLES = "No valid samples found"

    # Sample list
    SAMPLE_LIST_NO_SAMPLES = "No samples loaded"
    SAMPLE_LIST_STATS_PREFIX = "Total:"
    SAMPLE_LIST_STATS_SUFFIX = "samples"

    # Audio player
    AUDIO_PLAYER_TITLE = "Audio Player"
    AUDIO_READY = "Audio ready"
    AUDIO_NOT_AVAILABLE = "Audio not available"
    AUDIO_NO_SAMPLE = "No sample selected"
    BTN_PLAY = "Play (Space)"
    BTN_STOP = "Stop (ESC)"

    # Mapping matrix
    MATRIX_TITLE = "Mapping Matrix"
    MATRIX_RANGE_INFO_TEMPLATE = "Piano range A0-C8 (MIDI {min_midi}-{max_midi})"
    MATRIX_MAPPED_TEMPLATE = "Mapped: {count} samples"
    MATRIX_TITLE_TEMPLATE = "Sample mapping matrix (LMB = play / RMB = remove)"  # Deprecated - kept for compatibility
    MATRIX_INFO_LINE1 = "💡 Tip: Drag sample from left list using ⋮⋮ icon"
    MATRIX_INFO_LINE2 = "or use ⚡ button for automatic assignment"

    # Session dialog
    SESSION_DIALOG_TITLE = "Sample Mapping Editor - Session Management"
    SESSION_HEADER = "Welcome to Sample Mapping Editor"
    SESSION_SUBTITLE = "Select existing session or create a new one"
    SESSION_RECENT_TITLE = "Recent Sessions"
    SESSION_NEW_TITLE = "New Session"
    SESSION_NEW_INSTRUCTION = "Enter name for new session:"
    SESSION_NAME_PLACEHOLDER = "e.g. drums_2024, vocals_project..."
    SESSION_VELOCITY_LABEL = "Number of velocity layers:"
    SESSION_VELOCITY_INFO = "(1 = one layer, 4 = four layers, 8 = eight layers)"
    SESSION_INFO_LABEL = "Session files are stored in 'sessions' folder"
    SESSION_NO_SESSIONS = "No sessions found.\\nCreate a new session on the right."
    BTN_LOAD_SESSION = "Load Session"
    BTN_CREATE_SESSION = "Create Session"
    BTN_EXIT = "Exit"

    # Validation messages
    VALIDATION_INVALID_CHARS = "Name contains invalid characters"
    VALIDATION_SESSION_EXISTS = "Session with this name already exists"
    VALIDATION_CHECK_ERROR = "Error checking existing sessions"

    # Error messages
    ERROR_LOAD_SESSION = "Cannot load session '{name}'"
    ERROR_CREATE_SESSION = "Session '{name}' already exists"
    ERROR_REFRESH_SESSIONS = "Cannot load session list:\\n{error}"
    ERROR_LOADING_SESSION = "Error loading session:\\n{error}"
    ERROR_CREATING_SESSION = "Error creating session:\\n{error}"
    ERROR_OUTPUT_FOLDER = "Output folder is not writable"

    # Tooltips
    TOOLTIP_DISABLE_SAMPLE = "Disable this sample"
    TOOLTIP_DRAG_TO_MATRIX = "Drag to matrix (Drag & Drop)"
    TOOLTIP_PLAY_SAMPLE = "Play audio sample"
    TOOLTIP_PLAY_MIDI_TONE = "Play reference MIDI tone (for comparison)"
    TOOLTIP_TRANSPOSE_TEMPLATE = "Transpose by {semitones} semitones"
    TOOLTIP_PLAY_MAPPED = "Play mapped sample: {filename}"
    TOOLTIP_RESET_CELL = "Remove sample from this position"
    TOOLTIP_ASSIGN_AUTO = "Automatically assign sample to this position"
    # Note: Velocity layers range is defined in AUDIO.Velocity (1-8 by default)
    # Use dynamic formatting: f"...({AUDIO.Velocity.MIN_LAYERS}-{AUDIO.Velocity.MAX_LAYERS})"

    # Icons and symbols
    ICON_DRAG = "⇄ Drag"  # Bidirectional arrows with text for drag & drop
    ICON_PLAY_SAMPLE = "♪"
    ICON_PLAY_MIDI = "♫"
    ICON_RESET = "⌫"
    ICON_ASSIGN = "⚡"

    # About dialog
    ABOUT_TITLE = "About Sample Mapping Editor"
    ABOUT_TEXT = """Sample Mapping Editor v2.0

Professional sample mapping tool with:
• CREPE pitch detection
• RMS velocity analysis
• Hash-based session caching
• Drag & drop interface
• Multi-format export

Built with PySide6 and Python"""

    # Confirm dialogs
    CONFIRM_CLEAR_MATRIX_TITLE = "Clear Matrix"
    CONFIRM_CLEAR_MATRIX_TEXT = "Are you sure you want to clear all mapped samples?"

    # Info dialogs
    INFO_REFRESH_TITLE = "Refresh Samples"
    INFO_REFRESH_TEXT = "Please select an input folder first."
    INFO_EXPORT_TITLE = "Export Completed"

    # Export messages
    EXPORT_PREPARING = "Preparing export..."
    EXPORT_VALIDATING = "Validating samples..."
    EXPORT_CHECKING_FOLDER = "Checking output folder..."
    EXPORT_FOLDER_ERROR = "Output folder is not writable"
    EXPORT_STARTING = "Starting sample export..."
    EXPORT_COMPLETED_TEMPLATE = "Export completed: {exported}/{total} samples"
    EXPORT_CANCELLED = "Export cancelled"
    EXPORT_STATUS_TEMPLATE = "Exporting: {current}/{total} samples"
    EXPORT_INFO_TEMPLATE = """Export completed!

Exported: {exported_count} samples
Total files: {total_files}
Folder: {output_folder}"""
    EXPORT_INFO_WITH_ERRORS = "\\n\\nErrors: {failed_count} samples"

    # Status messages
    STATUS_INPUT_FOLDER = "Input folder: {name}"
    STATUS_OUTPUT_FOLDER = "Output folder: {name}"
    STATUS_MATRIX_CLEARED = "Matrix cleared"
    STATUS_SESSION_LOADED = "Session '{name}' loaded. Cached: {cached} samples."
    STATUS_ANALYSIS_START = "Starting analysis with cache..."
    STATUS_ANALYSIS_COMPLETED = "Analysis completed: {count} samples loaded"
    STATUS_SESSION_RESTORED = "Session restored: {samples} samples, {mappings} mappings"
    STATUS_CACHE_INFO = "Cache: {cached} samples loaded from cache, {analyzed} newly analyzed"

    # Audio messages
    AUDIO_PLAYING = "▶ Playing: {filename}"
    AUDIO_STOPPED = "Stopped"
    AUDIO_MIDI_PLAYING = "♪ Playing MIDI tone: {note_name}..."
    AUDIO_MIDI_SUCCESS = "✓ MIDI tone: {note_name} ({frequency:.1f} Hz)"
    AUDIO_MIDI_ERROR = "MIDI error: {error}"
    AUDIO_SAMPLE_SET = "Set: {filename}"


# =============================================================================
# PRECISION AND FORMATTING
# =============================================================================

class Formatting:
    """Constants for number and text formatting."""

    # RMS precision
    RMS_PRECISION_DISPLAY = 4  # 4 decimal places for display
    RMS_PRECISION_INTERNAL = 6  # 6 decimal places for internal calculations

    # MIDI formatting
    MIDI_FORMAT = "{:03d}"  # 000-127

    # Frequency precision
    FREQUENCY_PRECISION = 1  # 1 decimal place

    # Filename truncation
    FILENAME_MAX_LENGTH = 35  # For drag pixmap

    # Progress formatting
    PROGRESS_FORMAT = "{percentage}% - {message}"


# =============================================================================
# CSS STYLY (jako konstanty pro snadnou údržbu)
# =============================================================================

class Styles:
    """Často používané CSS styly."""

    @staticmethod
    def button_primary(bg_color, hover_color, text_color="white"):
        """Primární button style."""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                padding: {Spacing.PADDING_MEDIUM};
                font-size: {Fonts.SIZE_NORMAL}px;
                font-weight: bold;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_MEDIUM_DARK};
                color: {Colors.GRAY_DARK};
            }}
        """

    @staticmethod
    def label_with_border(bg_color, border_color, text_color):
        """Label s borderem a backgroundem."""
        return f"""
            QLabel {{
                background-color: {bg_color};
                padding: {Spacing.PADDING_SMALL};
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
                font-size: {Fonts.SIZE_MEDIUM}px;
                font-weight: bold;
            }}
        """

    @staticmethod
    def groupbox_styled(border_color, title_color):
        """Stylovaný GroupBox."""
        return f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {Fonts.SIZE_LARGE}px;
                border: 2px solid {border_color};
                border-radius: 8px;
                margin-top: {Spacing.MARGIN_LARGE}px;
                padding-top: {Spacing.MARGIN_LARGE}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.MARGIN_XLARGE}px;
                padding: 0 5px 0 5px;
                color: {title_color};
            }}
        """
