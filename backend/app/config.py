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
    vad_min_silence_ms: int = 500  # tighter: commit end-of-speech faster
    vad_min_speech_ms: int = 200
    vad_threshold: float = 0.5
    vad_speaker_switch_silence_ms: int = 1500  # gap that triggers speaker label rotation

    # --- Streaming partials ---
    enable_streaming_partials: bool = True
    partial_interval_ms: int = 700
    partial_min_audio_ms: int = 1200

    # --- Translation ---
    # Full system prompt is built dynamically in pipeline.py from system_prompt_base
    # + glossary + history. The base lives here for visibility / tunability.
    system_prompt_base: str = """你係一個日文導遊嘅即時翻譯員，向香港旅客講解。

## 場景
日本導遊向香港遊客講解景點、歷史、文化、美食、交通、活動（包括觀星 tour）。
用字要自然粵語口語化繁體中文（香港用法），保留專有名詞同人名。

## 翻譯規則
1. 專有名詞（人名、地名、神社寺廟、星座、星球名）保留原名，加括號粵語讀音
   例：「聖德太子（しょうとくたいし）」
2. 數字、日期、時間、價格保留原文
3. 導遊語氣要保留：熱情、講解、教育性
4. 敬語（です/ます）譯成粵語禮貌（請/多謝/唔該）
5. 避免書面語、大陸用語（例如「巴士」要譯「巴士」唔好譯「公共汽車」）
6. 短句可以直接譯；長句可以拆開
7. 只輸出翻譯結果，唔好加註解或解釋
8. 觀星場景：保留星座原名 + 中文，列明最佳觀賞時間、方位（東西南北）

{glossary_block}

## 對話歷史（用嚟理解上文下理同指代）
{history_block}

## Few-shot 範例
例 1（導遊歡迎）：
日文：「皆さん、今日は京都の清水寺へようこそ。」（語氣：熱情歡迎）
譯文：「各位，今日我哋一齊嚟到京都嘅清水寺。」

例 2（歷史講解）：
日文：「このお寺は778年に建立されました。」（語氣：歷史敘述）
譯文：「呢座寺廟喺公元778年建成。」

例 3（觀星導覽）：
日文：「あそこに明るく光る星がシリウスです。冬の大三角の一つです。」
譯文：「嗰邊嗰粒最光嘅星就係天狼星（シリウス），係冬季大三角嘅一粒星。」

例 4（詢問）：
日文：「写真撮ってもいいですか？」（語氣：禮貌詢問）
譯文：「請問我可唔可以影相？」

例 5（緊急）：
日文：「すみません、トイレはどこですか？」（語氣：禮貌詢問）
譯文：「唔好意思，請問洗手間喺邊度？」

## 現在翻譯
日文：{ja_text}
譯文："""

    # --- TTS ---
    tts_engine: str = "melo"  # or "edge"
    melo_speaker: str = "ZH"
    melo_speed: float = 1.0
    edge_tts_voice_zh_hk: str = "zh-HK-HiuMaanNeural"
    edge_tts_voice_zh_cn: str = "zh-CN-XiaoxiaoNeural"

    # --- Quality check (Improvement #9) ---
    enable_quality_check: bool = False  # adds ~1s latency per segment; off by default
    quality_retry_threshold: int = 7  # 1-10; below this triggers re-translation

    # --- Translation features ---
    enable_history: bool = True  # Improvement #2: include last 3 segments as context
    enable_streaming_tts: bool = True  # Improvement #6: stream MP3 chunks to client
    enable_two_step: bool = False  # Improvement #8: small LLM analyses → big LLM translates
    glossary_max_categories: int | None = None  # None = all; cap for short prompts

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
