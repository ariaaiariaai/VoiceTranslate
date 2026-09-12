"""Runtime configuration loaded from environment variables.

All settings are read from env vars prefixed with ``VOICETRANSLATE_``.
A ``.env`` file in the backend directory is loaded automatically by
``pydantic-settings``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VOICETRANSLATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Models ---
    models_dir: Path = Field(default=Path.home() / "Models")
    kotoba_dirname: str = "kotoba-whisper-v2.2-ct2-int8"
    # Sakura-7B is gated on HuggingFace; default to Qwen2.5-7B-Instruct (open).
    # Set VOICETRANSLATE_MT_DIRNAME=sakura-gguf to switch back after accepting
    # Sakura's license and running scripts/quantize_sakura.sh.
    mt_dirname: str = "qwen2.5-7b-instruct-gguf"
    mt_quant: str = "q4_k_m"

    # --- Backend server ---
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    # --- llama.cpp lifecycle ---
    llama_bin: Path | None = None
    llama_host: str = "127.0.0.1"
    llama_port: int = 8089
    mt_idle_unload_s: int = 600  # 10 min
    mt_ctx_size: int = 4096
    mt_max_tokens: int = 128
    mt_n_gpu_layers: int = 99  # offload everything on Metal

    # --- Audio ---
    sample_rate: int = 16000
    channels: int = 1
    chunk_ms: int = 1000  # client sends 1 s chunks

    # --- VAD ---
    vad_min_silence_ms: int = 700  # trigger end-of-speech
    vad_min_speech_ms: int = 250
    vad_threshold: float = 0.5

    # --- Translation ---
    system_prompt_ja_to_zh: str = (
        "你係一個專業嘅日文到繁體中文（香港）翻譯。請將以下日文準確翻譯成自然嘅繁體中文（香港用法），保留專有名詞同數字。"
        "只輸出翻譯結果，唔好加註解或者解釋。"
    )

    # --- TTS ---
    tts_engine: str = "melo"  # or "edge"
    melo_speaker: str = "ZH"
    melo_speed: float = 1.0
    edge_tts_voice_zh_hk: str = "zh-HK-HiuMaanNeural"
    edge_tts_voice_zh_cn: str = "zh-CN-XiaoxiaoNeural"

    def resolved(self) -> dict[str, str]:
        return {
            "kotoba_dir": str(self.models_dir / self.kotoba_dirname),
            "mt_gguf": str(self.models_dir / self.mt_dirname / f"{self.mt_quant}.gguf"),
            "llama_bin": str(
                self.llama_bin
                or (self.models_dir / "llama.cpp" / "build" / "bin" / "llama-server")
            ),
        }


settings = Settings()
