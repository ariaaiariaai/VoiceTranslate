"""VoiceTranslate FastAPI application entry."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.config import settings
from app.logging import configure_logging, get_logger
from app.pipeline import PipelineOrchestrator
from app.ws.session import WSSession

log = get_logger(__name__)

# Module-level singleton, populated by the lifespan handler.
_pipeline: PipelineOrchestrator | None = None


def get_pipeline() -> PipelineOrchestrator:
    if _pipeline is None:
        raise RuntimeError("Pipeline not initialised — wait for app startup")
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    configure_logging(settings.log_level)
    log.info("startup.begin", host=settings.host, port=settings.port)
    _pipeline = PipelineOrchestrator(settings)
    try:
        await _pipeline.warmup()
    except Exception as e:
        log.warning("startup.warmup.partial", error=str(e))
    log.info("startup.complete")
    try:
        yield
    finally:
        log.info("shutdown.begin")
        if _pipeline is not None:
            await _pipeline.shutdown()
        log.info("shutdown.complete")


app = FastAPI(
    title="VoiceTranslate",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the PWA (deployed on Pages) to call /api/* from a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # PWA + Cloudflare Tunnel both reach us over HTTPS; tightens in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    pipeline = get_pipeline()
    session = WSSession(websocket, pipeline)
    await session.handle()


@app.get("/")
async def root() -> dict:
    return {"service": "VoiceTranslate", "version": "0.1.0", "ws": "/ws"}
