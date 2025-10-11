"""
SamplePresenter - Presentation logic for sample management.

Zodpovědnosti:
- Načítání a analýza samples
- Komunikace s AnalysisService
- Koordinace mezi view a business logic
"""

import logging
from pathlib import Path
from typing import List, Optional, Callable
from PySide6.QtCore import QObject, Signal

from src.domain.models.sample import SampleMetadata
from src.application.services.analysis_service import AnalysisService
from src.infrastructure.audio.audio_file_loader import AudioFileLoader
from src.infrastructure.audio.crepe_analyzer import CrepeAnalyzer
from src.infrastructure.audio.rms_analyzer import RmsAnalyzer

logger = logging.getLogger(__name__)


class SamplePresenter(QObject):
    """
    Prezentér pro správu samples.
    
    Odděluje business logiku od GUI, poskytuje interface pro načítání
    a analýzu audio samples.
    """
    
    # Signály pro komunikaci s view
    samples_loaded = Signal(list)  # List[SampleMetadata]
    loading_progress = Signal(int, str)  # percentage, message
    loading_error = Signal(str)  # error message
    
    def __init__(self, analysis_service: Optional[AnalysisService] = None):
        """
        Args:
            analysis_service: Optional AnalysisService, vytvoří se default pokud None
        """
        super().__init__()
        
        # Dependency injection nebo vytvoření default service
        if analysis_service is None:
            audio_loader = AudioFileLoader()
            pitch_analyzer = CrepeAnalyzer(model_capacity="tiny", max_analysis_duration=5.0)
            amplitude_analyzer = RmsAnalyzer(velocity_duration_ms=500.0)
            self.analysis_service = AnalysisService(audio_loader, pitch_analyzer, amplitude_analyzer)
        else:
            self.analysis_service = analysis_service
        
        self.samples: List[SampleMetadata] = []
        self.input_folder: Optional[Path] = None
    
    def load_samples_from_folder(
        self,
        folder_path: Path,
        file_extensions: tuple = ('.wav', '.mp3', '.flac', '.aiff')
    ) -> bool:
        """
        Načte samples ze složky a analyzuje je.
        
        Args:
            folder_path: Cesta ke složce se samples
            file_extensions: Tuple podporovaných přípon
            
        Returns:
            True pokud se načítání spustilo úspěšně
        """
        try:
            if not folder_path.exists():
                self.loading_error.emit(f"Folder does not exist: {folder_path}")
                return False
            
            # Najdi všechny audio soubory
            audio_files = []
            for ext in file_extensions:
                audio_files.extend(folder_path.glob(f"**/*{ext}"))
            
            if not audio_files:
                self.loading_error.emit(f"No audio files found in {folder_path}")
                return False
            
            logger.info(f"Found {len(audio_files)} audio files in {folder_path}")
            
            # Vytvoř SampleMetadata objekty
            samples_to_analyze = [SampleMetadata(file_path) for file_path in audio_files]
            
            # Analyzuj samples
            self._analyze_samples(samples_to_analyze)
            
            self.input_folder = folder_path
            return True
            
        except Exception as e:
            logger.error(f"Error loading samples from folder: {e}")
            self.loading_error.emit(str(e))
            return False
    
    def _analyze_samples(self, samples: List[SampleMetadata]):
        """
        Analyzuje seznam samples.
        
        Args:
            samples: List SampleMetadata objektů k analýze
        """
        total = len(samples)
        successful = 0
        
        def progress_callback(current: int, total_count: int):
            percentage = int((current / total_count) * 100)
            self.loading_progress.emit(percentage, f"Analyzing: {current}/{total_count}")
        
        # Spustí batch analýzu
        successful, failed = self.analysis_service.analyze_batch(samples, progress_callback)
        
        logger.info(f"Analysis completed: {successful} successful, {failed} failed")
        
        # Filter pouze úspěšně analyzované samples
        self.samples = [s for s in samples if s.analyzed and s.detected_midi is not None]
        
        # Emit signál s načtenými samples
        self.samples_loaded.emit(self.samples)
        
        if failed > 0:
            self.loading_error.emit(f"{failed} samples failed to analyze")
    
    def get_samples(self) -> List[SampleMetadata]:
        """Vrátí seznam načtených samples."""
        return self.samples
    
    def get_sample_by_filename(self, filename: str) -> Optional[SampleMetadata]:
        """
        Najde sample podle jména souboru.
        
        Args:
            filename: Jméno souboru
            
        Returns:
            SampleMetadata nebo None
        """
        for sample in self.samples:
            if sample.filename == filename:
                return sample
        return None
    
    def filter_samples(self, predicate: Callable[[SampleMetadata], bool]) -> List[SampleMetadata]:
        """
        Filtruje samples podle predikátu.
        
        Args:
            predicate: Funkce která vrací True/False pro každý sample
            
        Returns:
            Filtrovaný list samples
        """
        return [s for s in self.samples if predicate(s)]
    
    def get_samples_by_midi_note(self, midi_note: int) -> List[SampleMetadata]:
        """
        Vrátí všechny samples s danou MIDI notou.
        
        Args:
            midi_note: MIDI nota (0-127)
            
        Returns:
            List samples s danou MIDI notou
        """
        return self.filter_samples(lambda s: s.detected_midi == midi_note)
    
    def clear_samples(self):
        """Vyčistí seznam samples."""
        self.samples = []
        self.input_folder = None
        self.samples_loaded.emit([])
