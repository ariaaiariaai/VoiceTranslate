"""Phrase cache — exact-match lookup for common Japanese phrases.

On hit, returns the pre-translated zh-HK string in <100ms (no STT/MT call).
The cache is loaded once at startup and queried by `lookup(text)`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.logging import get_logger

log = get_logger(__name__)


class PhraseCache:
    """Tiered phrase cache — flat dict for exact match.

    Categories: guide, tour, stargazing, travel, food, emergency.
    """

    def __init__(self, vocab_path: Path | str | None = None) -> None:
        self._cache: dict[str, str] = {}
        if vocab_path is None:
            default = Path(__file__).resolve().parents[2] / "data" / "phrase_cache.json"
            vocab_path = default
        p = Path(vocab_path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            # Flatten nested dict
            for category, phrases in data.items():
                if isinstance(phrases, dict):
                    for ja, zh in phrases.items():
                        self._cache[ja] = zh
            log.info("phrase_cache.loaded", entries=len(self._cache), path=str(p))
        else:
            log.warning("phrase_cache.missing", path=str(p))

    def lookup(self, text_ja: str) -> Optional[str]:
        """Exact match (whitespace-trimmed) → zh-HK string, or None."""
        if not text_ja:
            return None
        s = text_ja.strip()
        return self._cache.get(s)

    def __contains__(self, text_ja: str) -> bool:
        return self.lookup(text_ja) is not None

    def __len__(self) -> int:
        return len(self._cache)
