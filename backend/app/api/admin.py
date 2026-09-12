"""Admin endpoints — reload / unload models, view stats."""

from __future__ import annotations

from fastapi import APIRouter

from app.logging import get_logger

router = APIRouter()
log = get_logger(__name__)


@router.post("/admin/reload/stt")
async def reload_stt() -> dict:
    """Re-load the STT model on demand (after model swap)."""
    from app.main import get_pipeline

    p = get_pipeline()
    p.stt._model = None  # force reload on next call
    p.stt.warmup()
    return {"status": "reloaded", "target": "stt"}


@router.post("/admin/unload/mt")
async def unload_mt() -> dict:
    """Force-unload the MT model (release ~5 GB RAM)."""
    from app.main import get_pipeline

    p = get_pipeline()
    await p.mt._kill_server()
    return {"status": "unloaded", "target": "mt"}


@router.get("/admin/stats")
async def stats() -> dict:
    from app.main import get_pipeline

    p = get_pipeline()
    import resource

    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # macOS returns bytes
    return {
        "mt_loaded": p.mt.is_loaded,
        "rss_mb": round(rss_mb, 1),
    }
