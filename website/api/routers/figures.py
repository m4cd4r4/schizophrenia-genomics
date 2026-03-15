"""Serve pipeline figure PNGs."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from query.config import FIGURES_DIR

router = APIRouter(prefix="/api/figures", tags=["figures"])


@router.get("")
def list_figures():
    """List all available figure files."""
    if not FIGURES_DIR.exists():
        return []
    return [
        {
            "filename": f.name,
            "stem": f.stem,
            "size": f.stat().st_size,
        }
        for f in sorted(FIGURES_DIR.glob("*.png"))
    ]


@router.get("/{filename}")
def get_figure(filename: str):
    """Serve a specific PNG figure."""
    # Sanitize - only allow alphanumeric, underscore, hyphen, dot
    import re
    if not re.match(r"^[\w\-\.]+\.png$", filename):
        raise HTTPException(400, "Invalid filename")

    path = FIGURES_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Figure {filename} not found")

    return FileResponse(str(path), media_type="image/png")
