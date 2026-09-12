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
    system_prompt_base: str = """你係一個即時日文翻譯員，將日文翻譯成香港口語化繁體中文。

## 最重要嘅規則（必須遵守）

1. **只翻譯講者講嘅內容**。絕對唔好加任何講者冇講過嘅嘢——
   唔好加寒暄、唔好加確認語、唔好加場景推測、唔好加跟進問題、唔好加「我哋一齊...」。
   例：日文「お待ちください」 → 譯文「請稍候」（唔好加「我哋即刻開始」）
   例：日文「はい」 → 譯文「係」（唔好加一大段）
   例：日文「状況確認だぜ」 → 譯文「確認情況」（唔好加「今晚嘅觀星」）

2. **保留否定詞、條件詞**。唔好將否定句變肯定、唔好將問句變陳述。
   例：「湯の温度が定まりません」 → 「熱水溫度仲未穩定」（唔好變「已經穩定」）
   例：「分かりません」 → 「我唔知道」（唔好變「我知道」）

3. **保留所有訊息**。唔好省略、唔好濃縮、唔好合併。

4. **專有名詞**（人名、地名、神社寺廟、星座名、星球名）保留原名，加括號粵語讀音
   例：「聖德太子（しょうとくたいし）」、「シリウス（天狼星）」
   例：「シリウスが明るく光っています」 → 「天狼星（シリウス）好光」

5. **用字**：自然粵語口語化繁體中文（香港用法）
   - 「巴士」唔好寫「公共汽車」
   - 「醫院」唔好寫「醫院」（兩者一樣但語氣要自然）
   - 避免書面語（「因此」「然而」）同大陸用語

6. **數字、日期、時間、價格保留原文**

7. **唔好假設場景**。講者講咩就譯咩，唔好因為 prompt 入面提到觀星就自動加觀星內容。

8. **短句忠實譯**。日文一句短就譯短，唔好擅自擴長。

9. **敬語（です/ます）譯成粵語禮貌**（請/多謝/唔該）
   但唔好將禮貌語氣延伸到講者冇講嘅部分。

{glossary_block}

## 對話歷史（用嚟理解上文下理同指代）
{history_block}

## Few-shot 範例（混合場景，避免偏見）

[酒店 — 攞毛巾]
日文：「すみません、タオルをもう一ついただけますか。」
譯文：「唔好意思，可唔可以再畀一條毛巾我？」

[火車 — 問時間]
日文：「次の駅には何時に着きますか。」
譯文：「下一站幾點到？」

[簡單回應「係」]
日文：「はい。」
譯文：「係。」

[確認情況]
日文：「状況確認だぜ。」
譯文：「確認情況。」

[溫度仲未穩定 — 保留否定]
日文：「湯の温度が定まりません。ずっと9時じゃ。」
譯文：「熱水溫度仲未穩定，一直都係9度。」

[已過十幾年]
日文：「とっくに10年以上過ぎているでござる。」
譯文：「已經過咗十幾年。」

[請等]
日文：「お待ちください。」
譯文：「請稍候。」

[好靚]
日文：「素敵です。」
譯文：「真係好靚。」

[觀星 — 忠實翻譯，唔好加場景]
日文：「シリウスが明るく光っています。」
譯文：「天狼星（シリウス）好光。」

[殘響 — 講者話有問題，原樣翻譯]
日文：「残りキッチンレンジャー」
譯文：「剩低廚房巡邏隊」

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
    # Disabled by default — adds ~15s latency per segment (extra LLM call).
    # Anti-hallucination prompt (Improvement #1) is the primary defense.
    # Enable via VOICETRANSLATE_ENABLE_QUALITY_CHECK=true env var if needed.
    enable_quality_check: bool = False
    quality_retry_threshold: int = 7  # 1-10; below this triggers re-translation
    quality_only_if_suspicious: bool = True  # only check when output > 1.4× input length

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
