"""
clear_matrix_thread.py - Worker thread for asynchronous Clear Matrix operation
"""

import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class ClearMatrixWorker(QThread):
    """Worker thread for asynchronous Clear Matrix operation with progress bar."""

    progress_updated = Signal(int, str)  # progress percentage, message
    clear_bulk_requested = Signal()  # request bulk clear in GUI thread
    clear_completed = Signal(int)  # number of cleared samples
    clear_failed = Signal(str)  # error message

    def __init__(self, mapping_matrix):
        super().__init__()
        self.mapping_matrix = mapping_matrix
        self._is_cancelled = False

    def run(self):
        """Execute asynchronous Clear Matrix operation."""
        try:
            logger.info("Starting Clear Matrix thread")

            # Get current mapping count
            total_samples = len(self.mapping_matrix.mapping)

            if total_samples == 0:
                logger.info("Matrix is already empty")
                self.clear_completed.emit(0)
                return

            self.progress_updated.emit(50, f"Clearing {total_samples} mapped samples...")

            # Request bulk clear in GUI thread via signal
            # This avoids threading issues with QMetaObject.invokeMethod
            self.clear_bulk_requested.emit()

            # Give GUI time to process (the actual clear will be done by the signal handler)
            import time
            time.sleep(0.1)

            self.progress_updated.emit(100, f"Cleared {total_samples} samples")
            logger.info(f"Clear Matrix completed: {total_samples} samples cleared")
            self.clear_completed.emit(total_samples)

        except Exception as e:
            logger.error(f"Clear Matrix thread failed: {e}", exc_info=True)
            self.clear_failed.emit(f"Error during Clear Matrix: {e}")

    def cancel_clear(self):
        """Cancel ongoing Clear Matrix operation."""
        self._is_cancelled = True
        logger.info("Clear Matrix cancellation requested")
        self.progress_updated.emit(0, "Cancelling Clear Matrix...")
