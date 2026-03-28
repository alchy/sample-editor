"""
Spouštěcí skript pro Sample Editor API.

Spustit z kořenového adresáře projektu:
    python api/run.py
"""

import sys
import logging
from pathlib import Path

# Přidat kořen projektu do sys.path, aby fungovaly importy (src/, config/, api/)
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Logování do souboru (rotuje každý restart)
log_file = root / "server.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

import uvicorn

if __name__ == "__main__":
    print(f"Sample Editor API startuje na http://127.0.0.1:8000")
    print(f"Dokumentace API: http://127.0.0.1:8000/docs")
    print(f"Log soubor: {log_file}")
    print("Stiskni Ctrl+C pro zastavení.\n")

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(root / "api"), str(root / "src")],
    )
