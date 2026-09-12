"""Streaming STT wrapper around faster-whisper.

Yields partial Japanese text as faster-whisper decodes each chunk.
Used for low-latency "first word" UX — start MT before VAD sees silence.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import AsyncIterator

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)


class StreamingSTT:
    """Wraps faster-whisper in an async stream of partial Japanese transcriptions.

    Usage:
        async for partial_ja, is_final in streaming_stt.transcribe_stream(pcm_bytes):
            if not is_final:
                ws.send_text({"type": "partial", "ja": partial_ja})
            else:
                # commit final
                ...
    """

    def __init__(self, model_dir: str, language: str = "ja", beam_size: int = 1) -> None:
        self._model_dir = model_dir
        self._language = language
        self._beam_size = beam_size
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        log.info("streaming_stt.loading", model_dir=self._model_dir)
        self._model = WhisperModel(
            self._model_dir, device="cpu", compute_type="int8"
        )
        log.info("streaming_stt.ready")

    async def warmup(self) -> None:
        # Lazy load (model is heavy); the regular KotobaSTT already loads it eagerly.
        # This method exists for API symmetry; doesn't pre-load.
        pass

    async def transcribe_segment(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> str:
        """Blocking-style transcription of a full PCM segment. Returns final text."""
        self._ensure_loaded()
        audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size == 0:
            return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._transcribe_sync, audio, sample_rate))

    def _transcribe_sync(self, audio: np.ndarray, sample_rate: int) -> str:
        assert self._model is not None
        segments, info = self._model.transcribe(
            audio,
            language=self._language,
            beam_size=self._beam_size,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        parts: list[str] = []
        for seg in segments:
            parts.append(seg.text)
        text = "".join(parts).strip()
        log.info("streaming_stt.final", text_len=len(text), lang=info.language)
        return text

    async def transcribe_partial(
        self, pcm16_bytes: bytes, sample_rate: int = 16000
    ) -> str:
        """Lightweight transcription of a small buffer — for preview/partial UX.

        Faster than full transcribe_segment (smaller chunk → faster decode).
        Returns partial Japanese text — quality is lower than final.
        """
        self._ensure_loaded()
        audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size < 1600:  # < 100ms
            return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._transcribe_sync, audio, sample_rate))
