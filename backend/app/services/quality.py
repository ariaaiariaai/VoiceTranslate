"""Quality scorer — self-evaluate a translation and decide whether to retry.

Uses the same MT model to score the translation 1-10 on accuracy + fluency.
If below threshold, the pipeline can retransltye with a refined prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.logging import get_logger

log = get_logger(__name__)


@dataclass
class QualityScore:
    accuracy: int  # 1-10
    fluency: int  # 1-10
    overall: int  # 1-10
    issues: list[str]  # e.g. ["missing entity: 聖德太子"]
    should_retry: bool

    @property
    def acceptable(self) -> bool:
        return self.overall >= 7


SCORE_PROMPT = """你係一個翻譯品質審查員。請評估以下日文→繁體中文（香港）翻譯嘅品質。

## 評分標準（1-10）
- **準確度**：意思有冇錯譯、漏譯、加譯
- **自然度**：香港人講嘢嘅語氣（唔好書面語、唔好大陸用語）
- **專名保留**：人名地名星座名要保留原名

## 評估對象
日文原文：{ja_text}
繁體中文譯文：{zh_text}

## 輸出格式（嚴格遵守）
ACCURACY: <1-10>
FLUENCY: <1-10>
ISSUES: <問題列表，逗號分隔，冇就寫 "none">
RETRY: <yes/no>"""


class QualityScorer:
    def __init__(self, mt) -> None:
        self._mt = mt

    async def score(self, ja_text: str, zh_text: str) -> QualityScore:
        """Score the translation. Returns QualityScore with retry recommendation."""
        prompt = SCORE_PROMPT.format(ja_text=ja_text, zh_text=zh_text)
        try:
            response = await self._mt.translate_raw(
                system="你係翻譯品質審查員。請只輸出指定格式嘅評估結果，唔好加其他文字。",
                user=prompt,
                max_tokens=200,
            )
            return self._parse(response)
        except Exception as e:
            log.warning("quality.score.failed", error=str(e))
            # Default to accepting on failure
            return QualityScore(accuracy=8, fluency=8, overall=8, issues=[], should_retry=False)

    def _parse(self, response: str) -> QualityScore:
        accuracy, fluency, overall = 8, 8, 8
        issues: list[str] = []
        retry = False
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("ACCURACY:"):
                try:
                    accuracy = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.startswith("FLUENCY:"):
                try:
                    fluency = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.startswith("ISSUES:"):
                issues_str = line.split(":", 1)[1].strip()
                if issues_str and issues_str.lower() != "none":
                    issues = [i.strip() for i in issues_str.split(",") if i.strip()]
            elif line.startswith("RETRY:"):
                retry = line.split(":", 1)[1].strip().lower() == "yes"
        overall = (accuracy + fluency) // 2
        if overall < 7 or retry:
            should_retry = True
        else:
            should_retry = False
        return QualityScore(
            accuracy=accuracy,
            fluency=fluency,
            overall=overall,
            issues=issues,
            should_retry=should_retry,
        )
