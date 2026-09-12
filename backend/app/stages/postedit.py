"""Traditional Chinese (HK) post-edit.

Pipeline: Simplified Chinese (Sakura output) → OpenCC ``s2twp`` →
HK-specific idiom substitutions from ``hk-vocab.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.logging import get_logger

log = get_logger(__name__)

# Built-in HK substitutions (Sakura sometimes uses 简体 or 台湾 vocabulary).
# Loaded from hk-vocab.json if present, else falls back to this default set.
DEFAULT_HK_SUBSTITUTIONS: dict[str, str] = {
    "什么": "咩",
    "怎么": "點",
    "这样": "噉",
    "那样": "嗰",
    "没有": "冇",
    "不会": "唔會",
    "不要": "唔好",
    "但是": "但係",
    "所以": "所以",  # already HK, kept for clarity
    "现在": "而家",
    "时候": "時候",
    "东西": "嘢",
    "哪里": "邊度",
    "这里": "呢度",
    "那里": "嗰度",
    "知道": "知",
    "说话": "講嘢",
    "吃饭": "食飯",
    "回家": "返屋企",
    "非常": "好",
    "特别": "特別",
    "喜欢": "鍾意",
    "觉得": "覺得",
    "妈妈": "媽媽",
    "爸爸": "爸爸",
    "朋友": "朋友",
    "谢谢": "多謝",
    "再见": "再見",
    "可以": "可以",
    "手机": "手機",
    "电脑": "電腦",
    "软件": "軟件",
    "网络": "網絡",
    "信息": "訊息",
    "文件": "檔案",
    "质量": "質素",
    "服务": "服務",
    "价格": "價錢",
}


class HkPostEdit:
    def __init__(self, vocab_path: Path | str | None = None) -> None:
        self._opencc = None
        self._vocab: dict[str, str] = {}
        if vocab_path is None:
            # Default location: backend/data/hk-vocab.json
            default = Path(__file__).resolve().parents[2] / "data" / "hk-vocab.json"
            vocab_path = default if default.exists() else None
        if vocab_path is not None and Path(vocab_path).exists():
            self._vocab = json.loads(Path(vocab_path).read_text(encoding="utf-8"))
            log.info("postedit.vocab.loaded", count=len(self._vocab), path=str(vocab_path))
        else:
            self._vocab = DEFAULT_HK_SUBSTITUTIONS
            log.info("postedit.vocab.default", count=len(self._vocab))

    def _ensure_opencc(self) -> None:
        if self._opencc is not None:
            return
        from opencc import OpenCC

        # s2twp: Simplified → Traditional (Taiwan/HK phrases)
        self._opencc = OpenCC("s2twp")
        log.info("postedit.opencc.ready", mode="s2twp")

    def convert(self, zh_simplified: str) -> str:
        if not zh_simplified:
            return zh_simplified
        self._ensure_opencc()
        zh_tw = self._opencc.convert(zh_simplified)
        # Apply HK substitutions (whole-word, case-sensitive)
        for simp, trad in self._vocab.items():
            zh_tw = zh_tw.replace(simp, trad)
        return zh_tw
