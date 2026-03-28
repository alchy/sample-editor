"""
Správa adresářů pro session data (nahrané soubory, exporty).

Struktura:
  data/
    {session_name}/
      samples/   ← nahrané audio soubory
      export/    ← exportované soubory + instrument-definition.json
"""

import re
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac"}

_VALID_SESSION_NAME = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')


def _safe_session_path(session_name: str, subdir: str) -> Path:
    """Vrátí cestu uvnitř DATA_ROOT pro danou session a podsložku.
    Vyhodí ValueError pro neplatný název session."""
    if not _VALID_SESSION_NAME.match(session_name):
        raise ValueError(f"Neplatný název session: '{session_name}'")
    d = DATA_ROOT / session_name / subdir
    # Ověř, že výsledná cesta skutečně leží uvnitř DATA_ROOT (obrana před edge cases)
    try:
        d.resolve().relative_to(DATA_ROOT.resolve())
    except ValueError:
        raise ValueError(f"Cesta uniká z DATA_ROOT: {d}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def samples_dir(session_name: str) -> Path:
    return _safe_session_path(session_name, "samples")


def export_dir(session_name: str) -> Path:
    return _safe_session_path(session_name, "export")
