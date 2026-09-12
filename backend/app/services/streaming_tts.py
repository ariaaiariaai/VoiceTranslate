"""Streaming TTS wrapper around edge-tts.

Yields MP3 chunks as they arrive from edge-tts so the pipeline can forward
them to the WebSocket without waiting for the full utterance.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from app.logging import get_logger

log = get_logger(__name__)


class StreamingEdgeTTS:
    """Streaming MP3 generator using edge-tts."""

    async def stream_synth(self, text: str, voice: str) -> AsyncIterator[bytes]:
        """Yield raw MP3 byte chunks as they're produced.

        Edge TTS sends audio frames as they become available; we forward
        each chunk to the caller (typically the WebSocket session) so the
        client can start playback before the full sentence is ready.
        """
        if not text.strip():
            return
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, voice=voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and chunk["data"]:
                    yield chunk["data"]
        except Exception as e:
            log.error("streaming_tts.error", error=str(e), text_len=len(text))


class BufferingEdgeTTS:
    """Non-streaming variant — collects all chunks then returns one bytes blob.

    Used as a fallback when streaming isn't desired (e.g. testing).
    """

    def __init__(self) -> None:
        self._streaming = StreamingEdgeTTS()

    async def synth(self, text: str, voice: str) -> bytes:
        buf = bytearray()
        async for chunk in self._streaming.stream_synth(text, voice):
            buf.extend(chunk)
        return bytes(buf)
