"""
File management endpoints:
  POST /files/{name}/upload          — nahrání audio souborů do session
  GET  /files/{name}/samples         — seznam nahraných souborů
  GET  /files/{name}/export          — seznam exportovaných souborů
  GET  /files/{name}/export/zip      — stažení celého exportu jako ZIP
  GET  /files/{name}/export/{fname}  — stažení jednoho exportního souboru
"""

import io
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse

from api.data_dirs import samples_dir, export_dir, AUDIO_EXTENSIONS

router = APIRouter()


@router.post("/files/{name}/upload")
async def upload_files(
    name: str,
    files: List[UploadFile] = File(...),
):
    """Nahraje jeden nebo více audio souborů do session."""
    dest_dir = samples_dir(name)
    saved, skipped = [], []

    for f in files:
        suffix = Path(f.filename).suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            skipped.append(f.filename)
            continue
        dest = dest_dir / Path(f.filename).name
        content = await f.read()
        dest.write_bytes(content)
        saved.append(str(dest))

    return {
        "uploaded": len(saved),
        "skipped": len(skipped),
        "files": saved,
    }


@router.get("/files/{name}/samples")
def list_samples(name: str):
    """Vrátí seznam nahraných souborů v session."""
    d = samples_dir(name)
    files = sorted(
        str(f) for f in d.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )
    return {"files": files, "count": len(files)}


@router.get("/files/{name}/export")
def list_export(name: str):
    """Vrátí seznam souborů v export složce."""
    d = export_dir(name)
    files = sorted(
        {"name": f.name, "size": f.stat().st_size, "path": str(f)}
        for f in d.iterdir()
        if f.is_file()
    )
    return {"files": files, "count": len(files)}


@router.get("/files/{name}/export/zip")
def download_export_zip(name: str):
    """Stáhne celý export jako ZIP archiv."""
    d = export_dir(name)
    file_list = [f for f in d.iterdir() if f.is_file()]
    if not file_list:
        raise HTTPException(status_code=404, detail="Export složka je prázdná.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in file_list:
            zf.write(f, f.name)
    buf.seek(0)

    zip_name = f"{name}_export.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


@router.get("/files/{name}/export/{filename}")
def download_export_file(name: str, filename: str):
    """Stáhne jeden soubor z exportu."""
    d = export_dir(name)
    path = (d / filename).resolve()
    # Bezpečnostní kontrola — nesmí vyjít z export dir
    if not str(path).startswith(str(d.resolve())):
        raise HTTPException(status_code=400, detail="Neplatná cesta.")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Soubor '{filename}' nenalezen.")
    return FileResponse(str(path), filename=filename)
