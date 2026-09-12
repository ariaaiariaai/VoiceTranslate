"""Sakura-7B machine translation via llama.cpp HTTP server.

Manages a llama-server subprocess on demand (lazy + idle unload).
The server exposes an OpenAI-compatible ``/v1/chat/completions`` endpoint,
which we call to translate Japanese to Simplified Chinese. A separate
post-edit step (OpenCC + HK vocab) converts to Traditional Chinese (HK).
"""

from __future__ import annotations

import asyncio
import shutil
import signal
import subprocess
import time
from pathlib import Path

import httpx

from app.logging import get_logger

log = get_logger(__name__)


class SakuraMT:
    """Lifecycle-managed llama-server client for Sakura-7B Q4_K_M GGUF."""

    def __init__(
        self,
        llama_bin: Path | str,
        gguf_path: Path | str,
        host: str = "127.0.0.1",
        port: int = 8089,
        ctx_size: int = 4096,
        idle_unload_s: int = 600,
        n_gpu_layers: int = 99,
    ) -> None:
        self._llama_bin = Path(llama_bin)
        self._gguf_path = Path(gguf_path)
        self._host = host
        self._port = port
        self._ctx_size = ctx_size
        self._idle_unload_s = idle_unload_s
        self._n_gpu_layers = n_gpu_layers
        self._proc: subprocess.Popen | None = None
        self._last_used: float = time.monotonic()  # start the idle clock NOW
        self._watcher_task: asyncio.Task | None = None
        self._http = httpx.AsyncClient(base_url=f"http://{host}:{port}", timeout=60.0)

    async def start(self) -> None:
        """Start the idle-unload watcher (does not load the model)."""
        if self._watcher_task is None:
            self._watcher_task = asyncio.create_task(self._idle_watcher())
            log.info("mt.watcher.started", idle_unload_s=self._idle_unload_s)

    async def stop(self) -> None:
        if self._watcher_task:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass
            self._watcher_task = None
        await self._kill_server()
        await self._http.aclose()

    async def _idle_watcher(self) -> None:
        """SIGTERM llama-server after ``idle_unload_s`` of inactivity."""
        try:
            while True:
                await asyncio.sleep(30)
                if self._proc is None:
                    continue
                if time.monotonic() - self._last_used > self._idle_unload_s:
                    log.info("mt.idle.unloading", idle_for_s=int(time.monotonic() - self._last_used))
                    await self._kill_server()
        except asyncio.CancelledError:
            raise

    async def _ensure_loaded(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        await self._spawn_server()

    async def _spawn_server(self) -> None:
        if not self._llama_bin.exists():
            raise FileNotFoundError(
                f"llama-server not found at {self._llama_bin}. Build it from ~/Models/llama.cpp first."
            )
        if not self._gguf_path.exists():
            raise FileNotFoundError(
                f"Sakura GGUF not found at {self._gguf_path}. Run scripts/quantize_sakura.sh."
            )

        cmd = [
            str(self._llama_bin),
            "--model", str(self._gguf_path),
            "--host", self._host,
            "--port", str(self._port),
            "--ctx-size", str(self._ctx_size),
            "--n-gpu-layers", str(self._n_gpu_layers),
            "--no-warmup",  # faster startup; first request will be slow
            "--chat-template", "chatml",
        ]
        log.info("mt.spawn", cmd=" ".join(cmd))
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,  # so we can SIGTERM the whole group
        )
        # Wait for /health
        for attempt in range(120):  # up to 60 s
            try:
                r = await self._http.get("/health", timeout=1.0)
                if r.status_code == 200:
                    log.info("mt.ready", after_s=attempt * 0.5)
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)
        # Failed
        await self._kill_server()
        raise RuntimeError("llama-server failed to start within 60 s")

    async def _kill_server(self) -> None:
        if self._proc is None:
            return
        if self._proc.poll() is None:
            try:
                # Terminate the whole process group (mlock blocks if killed too early)
                import os

                try:
                    os.killpg(self._proc.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    self._proc.terminate()
                try:
                    self._proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    import os

                    try:
                        os.killpg(self._proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        self._proc.kill()
            except Exception as e:
                log.warning("mt.kill.error", error=str(e))
        self._proc = None

    def _touch(self) -> None:
        self._last_used = time.monotonic()

    async def translate(
        self,
        text_ja: str,
        system_prompt: str,
        max_tokens: int = 128,
    ) -> str:
        """Translate Japanese text to Simplified Chinese using Sakura."""
        if not text_ja.strip():
            return ""
        await self._ensure_loaded()
        self._touch()
        payload = {
            "model": "sakura",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_ja},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "top_p": 0.9,
            "stop": ["<|im_end|>", "<|endoftext|>"],
            "stream": False,
        }
        try:
            r = await self._http.post("/v1/chat/completions", json=payload, timeout=60.0)
            r.raise_for_status()
            data = r.json()
            zh = data["choices"][0]["message"]["content"].strip()
            log.info("mt.translated", ja_len=len(text_ja), zh_len=len(zh))
            return zh
        except Exception as e:
            log.error("mt.error", error=str(e))
            raise

    @property
    def is_loaded(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
