"""
main.py - Sampler Editor - vstupní bod aplikace
"""

import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox

from main_window import MainWindow

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Hlavní funkce aplikace."""
    app = QApplication(sys.argv)

    try:
        window = MainWindow()
        window.show()

        # Zobraz tip při spuštění (volitelné)
        show_startup_info(window)

        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        QMessageBox.critical(None, "Critical Error", f"Application failed:\n{e}")
        sys.exit(1)


def show_startup_info(window):
    """Zobrazí informace při spuštění (volitelné)."""
    try:
        from audio_player import AUDIO_AVAILABLE
        audio_status = "✓ Audio available" if AUDIO_AVAILABLE else "⚠ Audio not available"

        QMessageBox.information(window, "Sampler Editor - Professional Version",
                                f"Sampler Editor - Professional Version\n\n"
                                f"Status: {audio_status}\n\n"
                                "KEY FEATURES:\n"
                                "• Professional menu bar interface\n"
                                "• Hash-based session caching (fast reloading)\n"
                                "• CREPE pitch detection with RMS analysis\n"
                                "• Drag & drop sample mapping\n"
                                "• Asynchronous export with progress\n"
                                "• Multi-format export (44.1/48 kHz)\n\n"
                                "SHORTCUTS:\n"
                                "• Ctrl+N - New Session\n"
                                "• Ctrl+I - Input Folder\n"
                                "• Ctrl+O - Output Folder\n"
                                "• Ctrl+E - Export\n"
                                "• Ctrl+K - Clear Matrix\n"
                                "• F5 - Refresh\n\n"
                                "WORKFLOW:\n"
                                "1. Create/select session\n"
                                "2. Set input folder → analysis\n"
                                "3. Map samples using drag buttons (⋮⋮)\n"
                                "4. Set output folder & export")
    except Exception as e:
        logger.error(f"Error showing startup info: {e}")


if __name__ == "__main__":
    main()