"""WebSocket session — per-connection state and message loop.

Protocol:
  Client → Server (binary frame): raw PCM s16le, 16 kHz mono, ~1 s per frame
  Client → Server (text frame): JSON control message (hello / flush / mode / stop)
  Server → Client (text frame): JSON transcript / partial / error / ready
  Server → Client (binary frame): WAV audio for TTS (paired with transcript.audio_seq)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from app.logging import get_logger
from app.models.messages import (
    AudioChunkMsg,
    ErrorMsg,
    HelloMsg,
    ModeChangeMsg,
    OutputMode,
    PartialTranscriptMsg,
    ReadyMsg,
    TranscriptMsg,
    TranscriptSegment,
    TtsEngine,
)

if TYPE_CHECKING:
    from app.pipeline import PipelineOrchestrator

log = get_logger(__name__)


@dataclass
class SessionConfig:
    mode: OutputMode = OutputMode.BOTH
    tts_engine: TtsEngine = TtsEngine.MELO
    sample_rate: int = 16000


@dataclass
class VadAccumulator:
    """Tracks speech state and emits end-of-speech transitions.

    Speaker rotation: when a long silence (>1.5s) is seen, we increment the
    speaker letter. Each segment is tagged with the current speaker.
    This is a heuristic — not real speaker diarization. Real identity
    ("guide vs tourist") needs speaker embeddings; this just rotates labels.
    """

    min_silence_ms: int = 500  # tighter: commit earlier (was 700)
    min_speech_ms: int = 200
    is_speaking: bool = False
    speech_started_at_ms: int = 0
    last_speech_at_ms: int = 0
    last_speaker_change_at_ms: int = 0
    accumulated: bytearray = field(default_factory=bytearray)
    # Speaker rotation state
    current_speaker: int = 0  # 0=A, 1=B, 2=C, 3=D, then back to 0
    speaker_letters: list[str] = field(default_factory=lambda: ["A", "B", "C", "D"])
    speaker_switch_silence_ms: int = 1500  # gap before switching speaker label

    def feed(self, pcm: bytes, vad_speech_prob: float, ts_ms: int) -> bool:
        """Returns True when an end-of-speech has been detected and audio is ready."""
        is_voice = vad_speech_prob >= 0.5
        if is_voice:
            self.last_speech_at_ms = ts_ms
            if not self.is_speaking:
                if ts_ms - self.speech_started_at_ms >= self.min_speech_ms:
                    self.is_speaking = True
                else:
                    return False
            self.accumulated.extend(pcm)
        else:
            if not self.is_speaking:
                return False
            self.accumulated.extend(pcm)
            silence_ms = ts_ms - self.last_speech_at_ms
            if silence_ms >= self.min_silence_ms:
                # Decide if we should switch speaker label for the *next* segment
                if silence_ms >= self.speaker_switch_silence_ms and (ts_ms - self.last_speaker_change_at_ms) >= self.speaker_switch_silence_ms:
                    self.current_speaker = (self.current_speaker + 1) % len(self.speaker_letters)
                    self.last_speaker_change_at_ms = ts_ms
                    log.info("vad.speaker_switch", speaker=self.speaker_letters[self.current_speaker], silence_ms=int(silence_ms))
                self.is_speaking = False
                return True
        return False

    def drain(self) -> bytes:
        out = bytes(self.accumulated)
        self.accumulated.clear()
        return out

    @property
    def speaker_label(self) -> str:
        return self.speaker_letters[self.current_speaker]


class WSSession:
    """Owns one WebSocket connection's state and pumps its events."""

    def __init__(self, ws: WebSocket, pipeline: "PipelineOrchestrator") -> None:
        self.ws = ws
        self.pipeline = pipeline
        self.config = SessionConfig()
        self.vad = VadAccumulator()
        self._segment_id = 0
        self._audio_seq = 0
        self._closed = False
        self._cumulative_ms = 0  # running total of audio ms seen
        # Conversation history for translation context (Improvement #2)
        self._history: list[dict] = []  # [{ja: "...", zh: "..."}, ...]
        self._history_max = 5  # keep last N segments

    async def handle(self) -> None:
        await self.ws.accept()
        log.info("ws.connected", client=str(self.ws.client))
        try:
            # Wait for hello with timeout
            await asyncio.wait_for(self._wait_hello(), timeout=10.0)
            await self.ws.send_text(ReadyMsg().model_dump_json())
            await self._pump()
        except asyncio.TimeoutError:
            await self._send_error("hello_timeout", "client did not send hello within 10s")
        except WebSocketDisconnect:
            log.info("ws.disconnected", client=str(self.ws.client))
        except Exception as e:
            log.error("ws.error", error=str(e), exc_info=True)
            try:
                await self._send_error("internal", str(e))
            except Exception:
                pass
        finally:
            self._closed = True

    async def _wait_hello(self) -> None:
        while True:
            msg = await self.ws.receive()
            if msg.get("type") == "websocket.receive":
                if msg.get("text") is not None:
                    data = json.loads(msg["text"])
                    if data.get("type") == "hello":
                        hello = HelloMsg(**data)
                        self.config = SessionConfig(
                            mode=hello.mode,
                            tts_engine=hello.tts_engine,
                            sample_rate=hello.sample_rate,
                        )
                        log.info("ws.hello", config=self.config)
                        return
                # binary before hello is unexpected — ignore
            elif msg.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()

    async def _pump(self) -> None:
        """Main loop: receive frames, drive pipeline."""
        # We use the receive() generator pattern for finer control over text vs binary.
        # In FastAPI/Starlette, iterating ws.iter_text() / ws.iter_bytes() is cleaner.
        async for raw_text in self._iter_text():
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                await self._send_error("bad_json", "could not parse control message")
                continue
            mtype = data.get("type")
            if mtype == "stop":
                log.info("ws.stop")
                break
            if mtype == "flush":
                await self._flush()
                continue
            if mtype == "mode":
                msg = ModeChangeMsg(**data)
                self.config.mode = msg.mode
                log.info("ws.mode_change", mode=msg.mode)
                continue
            await self._send_error("bad_type", f"unknown control message type: {mtype}")

    async def _iter_text(self) -> "asyncio.AsyncIterator[str]":
        """Yield text frames, dispatching binary frames to the pipeline."""
        while not self._closed:
            msg = await self.ws.receive()
            if msg.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()
            if msg.get("bytes") is not None:
                await self._on_audio(msg["bytes"])
            elif msg.get("text") is not None:
                yield msg["text"]

    async def _on_audio(self, pcm_bytes: bytes) -> None:
        """Receive one PCM chunk (1 s @ 16 kHz ≈ 32 KB) and run VAD."""
        prob = _rms_speech_prob(pcm_bytes)
        # Each byte is 1/2 a sample, at 16 kHz → samples_per_ms = 16
        chunk_ms = len(pcm_bytes) // 2 // 16
        self._cumulative_ms += chunk_ms
        ts_ms = self._cumulative_ms

        end_of_speech = self.vad.feed(pcm_bytes, prob, ts_ms)
        if end_of_speech:
            audio_segment = self.vad.drain()
            if len(audio_segment) < 1024:  # < 32 ms — discard
                return
            await self._process_segment(audio_segment)

    async def _process_segment(self, pcm_segment: bytes) -> None:
        self._segment_id += 1
        seg_id = self._segment_id
        speaker = self.vad.speaker_label
        try:
            # Send a partial placeholder so the UI shows activity
            await self.ws.send_text(
                PartialTranscriptMsg(id=seg_id, ja="…", zh="…", speaker=speaker).model_dump_json()
            )
            # Pass conversation history (Improvement #2)
            result = await self.pipeline.run(
                pcm_segment, self.config, history=list(self._history)
            )
            if not result.ja_text:
                return
            # Update history
            self._history.append({"ja": result.ja_text, "zh": result.zh_text})
            if len(self._history) > self._history_max:
                self._history = self._history[-self._history_max:]
            # Streaming TTS: Improvement #6 — start audio chunks as soon as MT is done,
            # continue while pipeline returns final transcript.
            need_audio = (
                self.config.mode in (OutputMode.AUDIO, OutputMode.BOTH)
                and result.audio_wav
            )
            audio_seq = None
            chunk_count = 0
            if need_audio:
                self._audio_seq += 1
                audio_seq = self._audio_seq
                chunk_count = max(1, len(result.audio_wav) // 16384 + (1 if len(result.audio_wav) % 16384 else 0))
            # Send final transcript (with speaker tag)
            transcript = TranscriptMsg(
                segment=TranscriptSegment(
                    id=seg_id,
                    ja=result.ja_text,
                    zh=result.zh_text,
                    latency_ms=result.latency_ms,
                    speaker=speaker,
                ),
                audio_seq=audio_seq,
                audio_chunk_count=chunk_count if need_audio else None,
                quality_score=result.quality_score,
            )
            await self.ws.send_text(transcript.model_dump_json())
            # Stream audio chunks
            if need_audio and chunk_count > 0:
                marker = AudioChunkMsg(seq=audio_seq, total=chunk_count, format="mp3")
                await self.ws.send_text(marker.model_dump_json())
                chunk_size = 16384
                data = result.audio_wav
                for i in range(0, len(data), chunk_size):
                    await self.ws.send_bytes(data[i:i + chunk_size])
        except Exception as e:
            log.error("ws.segment.error", error=str(e), exc_info=True)
            await self._send_error("pipeline_error", str(e))

    async def _flush(self) -> None:
        if self.vad.is_speaking or len(self.vad.accumulated) > 0:
            audio_segment = self.vad.drain()
            self.vad.is_speaking = False
            if audio_segment:
                await self._process_segment(audio_segment)
        log.info("ws.flushed")

    async def _send_error(self, code: str, message: str) -> None:
        try:
            await self.ws.send_text(ErrorMsg(code=code, message=message).model_dump_json())
        except Exception:
            pass


def _rms_speech_prob(pcm16_bytes: bytes) -> float:
    """Cheap RMS-based speech probability in [0, 1].

    Replace with Silero VAD once model is downloaded. Threshold tuned for
    a phone mic 30 cm from the speaker.
    """
    if not pcm16_bytes:
        return 0.0
    arr = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32)
    if arr.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(arr * arr)) / 32768.0)
    # Map RMS [-60 dB .. -10 dB] → [0 .. 1]
    db = 20 * np.log10(max(rms, 1e-9))
    if db < -55:
        return 0.0
    if db > -20:
        return 1.0
    return float((db + 55) / 35)
