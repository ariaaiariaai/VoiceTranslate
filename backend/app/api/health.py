"""Health and readiness probes."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness — always returns 200 if the process is up."""
    return {"status": "ok", "ts": time.time()}


@router.get("/ready")
async def ready() -> dict:
    """Readiness — returns 200 only when all required models are loadable."""
    r = settings.resolved()
    kotoba_ok = Path(r["kotoba_dir"]).joinpath("model.bin").exists()
    mt_ok = Path(r["mt_gguf"]).exists()
    llama_bin_ok = Path(r["llama_bin"]).exists() and Path(r["llama_bin"]).is_file()
    return {
        "status": "ready" if all([kotoba_ok, mt_ok, llama_bin_ok]) else "degraded",
        "models": {
            "kotoba_stt": kotoba_ok,
            "mt": mt_ok,
            "llama_server": llama_bin_ok,
        },
    }
