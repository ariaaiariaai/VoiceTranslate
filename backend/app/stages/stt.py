"""faster-whisper wrapper for Japanese STT.

Loads kotoba-tech/kotoba-whisper-v2.2 (converted to CTranslate2 int8)
on first call. Models directory defaults to ``~/Models/kotoba-whisper-v2.2-ct2-int8``.
"""

from __future__ import annotations

import asyncio
import threading
from functools import partial
from pathlib import Path
from typing import Sequence

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)


class KotobaSTT:
    """Lazy-loaded Japanese STT using faster-whisper (CTranslate2 backend).

    Thread-safe. Synchronous transcription runs in a worker thread to
    keep the asyncio loop unblocked.
    """

    def __init__(self, model_dir: Path | str, device: str = "cpu", compute_type: str = "int8") -> None:
        self._model_dir = str(model_dir)
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            log.info("stt.loading", model_dir=self._model_dir, device=self._device)
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._model_dir,
                device=self._device,
                compute_type=self._compute_type,
            )
            log.info("stt.ready")

    async def transcribe(
        self,
        pcm16_bytes: bytes,
        sample_rate: int = 16000,
        language: str = "ja",
    ) -> str:
        """Transcribe a PCM s16le mono chunk. Returns concatenated text.

        The input may span a complete utterance or several seconds; faster-whisper
        handles segmentation internally.
        """
        self._ensure_loaded()
        # PCM s16le bytes → float32 [-1, 1]
        audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size == 0:
            return ""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._transcribe_sync, audio, sample_rate, language))

    def _transcribe_sync(self, audio: np.ndarray, sample_rate: int, language: str) -> str:
        assert self._model is not None
        segments, info = self._model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=False,  # we did VAD ourselves
            condition_on_previous_text=False,
        )
        parts: list[str] = []
        for seg in segments:
            parts.append(seg.text)
        text = "".join(parts).strip()
        log.info("stt.transcribed", text_len=len(text), lang=info.language, prob=info.language_probability)
        return text

    def warmup(self) -> None:
        """Load the model eagerly. Safe to call from startup."""
        self._ensure_loaded()
