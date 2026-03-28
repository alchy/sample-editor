"""
Pydantic modely pro API requesty a response.
"""

from typing import Optional, List
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Požadavek na analýzu jednoho souboru."""
    file_path: str
    session_name: Optional[str] = None


class SampleAnalysisResult(BaseModel):
    """Výsledek analýzy jednoho samplu."""
    filename: str
    file_path: str
    detected_midi: Optional[int] = None
    detected_frequency: Optional[float] = None
    pitch_confidence: Optional[float] = None
    pitch_method: Optional[str] = None
    velocity_amplitude: Optional[float] = None
    velocity_amplitude_db: Optional[float] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    analyzed: bool = False
    success: bool = False
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    result: SampleAnalysisResult
    from_cache: bool = False


class BatchAnalyzeRequest(BaseModel):
    """Požadavek na dávkovou analýzu více souborů."""
    file_paths: List[str]
    session_name: Optional[str] = None


class BatchAnalyzeResponse(BaseModel):
    results: List[SampleAnalysisResult]
    successful: int
    failed: int
    from_cache: int


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    """Vytvoření nové session."""
    name: str
    velocity_layers: int = 4
    instrument_name: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    input_folder: Optional[str] = None
    output_folder: Optional[str] = None


class SessionInfo(BaseModel):
    """Informace o session."""
    name: str
    created: Optional[str] = None
    last_modified: Optional[str] = None
    velocity_layers: int
    cached_samples: int = 0
    mapping_entries: int = 0
    input_folder: Optional[str] = None
    output_folder: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[str]


class FolderScanRequest(BaseModel):
    """Skenování složky se soubory."""
    folder_path: str
    extensions: List[str] = [".wav", ".flac", ".aif", ".aiff"]


class FolderScanResponse(BaseModel):
    files: List[str]
    count: int


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------

class MappingEntry(BaseModel):
    """Jedno mapování: MIDI nota + velocity vrstva → soubor."""
    midi_note: int
    velocity: int
    file_path: str


class MappingSaveRequest(BaseModel):
    session_name: str
    mapping: List[MappingEntry]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    """Požadavek na export. output_folder je volitelný — výchozí je data/{session}/export/."""
    session_name: str
    output_folder: Optional[str] = None
    mapping: List[MappingEntry]
    include_instrument_definition: bool = True


class ExportResult(BaseModel):
    exported_count: int
    failed_count: int
    total_files: int
    exported_files: List[str]
    failed_files: List[dict]
    instrument_definition_path: Optional[str] = None


class ExportPreviewItem(BaseModel):
    source_file: str
    output_file: str
    midi_note: int
    note_name: str
    velocity: int
    sample_rate: int
    valid: bool


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

class AudioInfoResponse(BaseModel):
    """Informace o audio souboru."""
    file_path: str
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    frames: Optional[int] = None
