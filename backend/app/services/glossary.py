"""Tourism + stargazing glossary — context injection for MT.

Loads `data/tourism_glossary.json` and exposes:
- `format_for_prompt()` — produces a markdown section to inject into the
  translation prompt, so the LLM keeps proper nouns in their original
  Japanese with parenthetical Cantonese transliteration.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.logging import get_logger

log = get_logger(__name__)


class Glossary:
    def __init__(self, vocab_path: Path | str | None = None) -> None:
        self._glossary: dict[str, dict[str, str]] = {}
        if vocab_path is None:
            default = Path(__file__).resolve().parents[2] / "data" / "tourism_glossary.json"
            vocab_path = default
        p = Path(vocab_path)
        if p.exists():
            self._glossary = json.loads(p.read_text(encoding="utf-8"))
            # Drop the _comment key
            self._glossary.pop("_comment", None)
            total = sum(len(v) for v in self._glossary.values() if isinstance(v, dict))
            log.info("glossary.loaded", entries=total, categories=list(self._glossary.keys()), path=str(p))
        else:
            log.warning("glossary.missing", path=str(p))

    def format_for_prompt(self, max_categories: int | None = None) -> str:
        """Render as a compact markdown table for the system prompt."""
        if not self._glossary:
            return ""
        lines = ["## 專有名詞對照表（請保留原名+括號內粵語讀音）"]
        cats = list(self._glossary.items())
        if max_categories is not None:
            cats = cats[:max_categories]
        for category, entries in cats:
            if not isinstance(entries, dict) or not entries:
                continue
            lines.append(f"\n### {category}")
            for ja, zh in list(entries.items())[:30]:  # cap per category
                lines.append(f"- {ja} → {zh}")
        return "\n".join(lines)

    def lookup_in_text(self, text_ja: str) -> list[tuple[str, str]]:
        """Find glossary entries present in the given Japanese text.

        Returns list of (japanese_term, cantonese_form) for terms found.
        """
        found = []
        for entries in self._glossary.values():
            if not isinstance(entries, dict):
                continue
            for ja, zh in entries.items():
                if ja in text_ja:
                    found.append((ja, zh))
        return found
