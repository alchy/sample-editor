"""
Spouštěcí skript pro Sample Editor API.

Spustit z kořenového adresáře projektu:
    python api/run.py
"""

import sys
from pathlib import Path

# Přidat kořen projektu do sys.path, aby fungovaly importy (src/, config/, api/)
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import uvicorn

if __name__ == "__main__":
    print("Sample Editor API startuje na http://127.0.0.1:8000")
    print("Dokumentace API: http://127.0.0.1:8000/docs")
    print("Stiskni Ctrl+C pro zastavení.\n")

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,          # při změně kódu se server restartuje automaticky
        reload_dirs=[str(root / "api"), str(root / "src")],
    )
