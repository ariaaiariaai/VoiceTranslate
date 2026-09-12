"""TTS stage — uses edge-tts (cloud) as the primary engine.

Edge TTS is free (Microsoft Azure Speech service, no API key needed for
the public endpoint) and supports both Mandarin (zh-CN) and Cantonese
(zh-HK) voices natively. Returns MP3 bytes that the browser plays
directly via the <audio> element.

If MeloTTS is installed and selected via settings, we fall back to a
local synth path.
"""

from __future__ import annotations

import asyncio
import io
import struct
from typing import Any

from app.logging import get_logger

log = get_logger(__name__)


class EdgeTTS:
    """Microsoft Edge TTS wrapper — async streaming → MP3 bytes."""

    def __init__(self) -> None:
        pass

    async def synth(self, text: str, voice: str = "zh-HK-HiuMaanNeural") -> bytes:
        if not text.strip():
            return b""
        try:
            import edge_tts
        except ImportError as e:
            log.error("tts.edge_tts.missing", error=str(e))
            return b""

        communicate = edge_tts.Communicate(text, voice=voice)
        buf = bytearray()
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
        except Exception as e:
            log.error("tts.edge_tts.error", error=str(e))
            return b""
        log.info("tts.edge.synth", voice=voice, text_len=len(text), audio_bytes=len(buf))
        return bytes(buf)


def _wav_wrap(pcm16_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit PCM in a minimal WAV header (for MeloTTS path)."""
    n = len(pcm16_bytes)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + n))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))   # PCM
    buf.write(struct.pack("<H", 1))   # mono
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * 2))
    buf.write(struct.pack("<H", 2))
    buf.write(struct.pack("<H", 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", n))
    buf.write(pcm16_bytes)
    return buf.getvalue()


class MeloTTS:
    """Optional local TTS — only used if melotts is importable."""

    def __init__(self, language: str = "ZH", speaker: str = "ZH", speed: float = 1.0) -> None:
        self._language = language
        self._speaker = speaker
        self._speed = speed
        self._model: Any = None

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        try:
            from melo.api import TTS  # noqa: F401
        except ImportError:
            log.warning("tts.melotts.unavailable; falling back to edge")
            return False
        try:
            from melo.api import TTS

            self._model = TTS(language=self._language, device="cpu")
            return True
        except Exception as e:
            log.warning("tts.melotts.load.failed", error=str(e))
            return False

    async def synth(self, text: str) -> bytes:
        if not text.strip():
            return b""
        if not self._ensure_loaded():
            return b""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._synth_sync, text)

    def _synth_sync(self, text: str) -> bytes:
        from functools import partial

        assert self._model is not None
        speaker_ids = self._model.hps.data.spk2id
        sid = speaker_ids.get(self._speaker, speaker_ids.get("ZH", 0))
        audio = self._model.tts_to_file(
            text,
            sid=sid,
            speed=self._speed,
            quiet=True,
            output=None,
        )
        import numpy as np

        if not isinstance(audio, np.ndarray):
            audio = np.array(audio, dtype=np.float32)
        sr = self._model.hps.data.sampling_rate
        pcm16 = np.clip(audio, -1.0, 1.0)
        pcm16 = (pcm16 * 32767.0).astype(np.int16).tobytes()
        return _wav_wrap(pcm16, sr)
