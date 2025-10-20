"""
models.py - COMPATIBILITY SHIM

This file provides backward compatibility by re-exporting classes from the new structure.
All new code should import from src.domain.models instead.

DEPRECATED: This file will be removed in future versions.
"""

import sys
from pathlib import Path

# Add src to path if not already there
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import from new location and re-export
from src.domain.models import SampleMetadata, AnalysisProgress

__all__ = ["SampleMetadata", "AnalysisProgress"]
