"""
main.py - Sampler Editor - vstupní bod aplikace s graceful shutdown
"""

import sys
import signal
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from main_window import MainWindow

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_signal_handlers(app, window):
    """
    Nastaví signal handlers pro graceful shutdown.

    Zachycuje SIGTERM (kill) a SIGINT (Ctrl+C) pro správné uložení dat.
    """
    def signal_handler(signum, frame):
        """Handler pro system signály - zajistí graceful shutdown."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name} ({signum}) - initiating graceful shutdown...")

        # Qt vyžaduje aby GUI operace běžely v main threadu
        # Použijeme QTimer.singleShot pro bezpečné volání closeEvent
        QTimer.singleShot(0, window.close)

    # Registruj handlery pro Windows i Unix
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command

    # Windows má navíc SIGBREAK (Ctrl+Break)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

    logger.info("✓ Signal handlers registered (SIGINT, SIGTERM)")


def main():
    """Hlavní funkce aplikace."""
    app = QApplication(sys.argv)

    try:
        window = MainWindow()

        # NOVÉ: Nastav signal handlers pro graceful shutdown
        setup_signal_handlers(app, window)

        window.show()

        # Zobraz tip při spuštění (volitelné)
        show_startup_info(window)

        exit_code = app.exec()

        # NOVÉ: Shutdown audio worker před ukončením
        logger.info("Shutting down audio worker...")
        from audio_worker import shutdown_audio_worker
        shutdown_audio_worker()
        logger.info("✓ Audio worker shutdown complete")

        sys.exit(exit_code)

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