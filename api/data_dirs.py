"""
Správa adresářů pro session data (nahrané soubory, exporty).

Struktura:
  data/
    {session_name}/
      samples/   ← nahrané audio soubory
      export/    ← exportované soubory + instrument-definition.json
"""

from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac"}


def samples_dir(session_name: str) -> Path:
    d = DATA_ROOT / session_name / "samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_dir(session_name: str) -> Path:
    d = DATA_ROOT / session_name / "export"
    d.mkdir(parents=True, exist_ok=True)
    return d
