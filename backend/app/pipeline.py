"""Pipeline orchestrator — runs VAD → STT → MT → TTS for one segment."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.logging import get_logger
from app.models.messages import OutputMode, TtsEngine
from app.stages.mt import SakuraMT
from app.stages.postedit import HkPostEdit
from app.stages.stt import KotobaSTT
from app.stages.tts import EdgeTTS, MeloTTS

if False:  # TYPE_CHECKING
    from app.ws.session import SessionConfig  # noqa: F401
else:
    SessionConfig = None  # placeholder; we re-import below in a guarded way

log = get_logger(__name__)


@dataclass
class PipelineResult:
    ja_text: str
    zh_text: str
    audio_wav: bytes | None  # MP3 (edge-tts) or WAV (MeloTTS) bytes
    latency_ms: float


def _get_session_config_cls():
    """Avoid circular import: ws.session imports this module for type hints."""
    from app.ws.session import SessionConfig as _SessionConfig

    return _SessionConfig


class PipelineOrchestrator:
    """Owns long-lived singletons (STT, MT, TTS, postedit)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        r = settings.resolved()
        log.info("pipeline.init", kotoba=r["kotoba_dir"], mt=r["mt_gguf"], llama=r["llama_bin"])

        self.stt = KotobaSTT(model_dir=r["kotoba_dir"])
        self.mt = SakuraMT(
            llama_bin=r["llama_bin"],
            gguf_path=r["mt_gguf"],
            host=settings.llama_host,
            port=settings.llama_port,
            ctx_size=settings.mt_ctx_size,
            idle_unload_s=settings.mt_idle_unload_s,
            n_gpu_layers=settings.mt_n_gpu_layers,
        )
        self.postedit = HkPostEdit()
        self.edge_tts = EdgeTTS()
        self.melo_tts = MeloTTS(
            language="ZH",
            speaker=settings.melo_speaker,
            speed=settings.melo_speed,
        )

    async def warmup(self) -> None:
        try:
            self.stt.warmup()
        except Exception as e:
            log.warning("pipeline.stt.warmup.failed", error=str(e))
        await self.mt.start()

    async def shutdown(self) -> None:
        await self.mt.stop()

    async def run(self, pcm_segment: bytes, cfg) -> PipelineResult:
        t0 = time.monotonic()
        ja_text = await self.stt.transcribe(
            pcm_segment,
            sample_rate=self.settings.sample_rate,
            language="ja",
        )
        if not ja_text.strip():
            return PipelineResult(ja_text="", zh_text="", audio_wav=None, latency_ms=(time.monotonic() - t0) * 1000)
        zh_simp = await self.mt.translate(
            ja_text,
            self.settings.system_prompt_ja_to_zh,
            max_tokens=self.settings.mt_max_tokens,
        )
        zh_hk = self.postedit.convert(zh_simp)
        audio_wav: bytes | None = None
        if cfg.mode in (OutputMode.AUDIO, OutputMode.BOTH):
            try:
                audio_wav = await self._synth(cfg, zh_hk)
            except Exception as e:
                log.warning("pipeline.tts.failed", error=str(e))
                audio_wav = None
        latency_ms = (time.monotonic() - t0) * 1000
        log.info("pipeline.done", ja=ja_text[:40], zh=zh_hk[:40], latency_ms=round(latency_ms, 1))
        return PipelineResult(ja_text=ja_text, zh_text=zh_hk, audio_wav=audio_wav, latency_ms=latency_ms)

    async def _synth(self, cfg, text: str) -> bytes:
        if cfg.tts_engine == TtsEngine.MELO:
            wav = await self.melo_tts.synth(text)
            if wav:
                return wav
            # fall through to edge if MeloTTS missing
            log.info("pipeline.tts.fallback_to_edge")
        # edge-tts path
        if cfg.tts_engine == TtsEngine.EDGE_HK:
            voice = self.settings.edge_tts_voice_zh_hk
        else:
            voice = self.settings.edge_tts_voice_zh_cn
        return await self.edge_tts.synth(text, voice=voice)
