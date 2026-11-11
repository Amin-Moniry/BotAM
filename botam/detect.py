"""Fast offline script-based language guess.

Only used to (a) pick a sane target when the text is already in the target
language and (b) as a fallback when an engine does not report the source.
Latin-script text returns ``None`` — the translation engines detect those.
"""
from __future__ import annotations

import re

_RANGES = {
    "arabic": re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]"),
    "cyrillic": re.compile(r"[\u0400-\u04FF]"),
    "han": re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]"),
    "kana": re.compile(r"[\u3040-\u30FF]"),
    "hangul": re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF]"),
    "devanagari": re.compile(r"[\u0900-\u097F]"),
    "thai": re.compile(r"[\u0E00-\u0E7F]"),
    "greek": re.compile(r"[\u0370-\u03FF]"),
    "latin": re.compile(r"[A-Za-zÀ-ÿĀ-ž]"),
}
_FA_ONLY = re.compile(r"[پچژگکی\u200c]")
_UR_ONLY = re.compile(r"[ٹڈڑںےھ]")
_UK_ONLY = re.compile(r"[іїєґІЇЄҐ]")


def guess_language(text: str) -> str | None:
    counts = {name: len(rx.findall(text)) for name, rx in _RANGES.items()}
    if sum(counts.values()) == 0:
        return None
    if counts["kana"]:
        return "ja"
    top = max(counts, key=counts.get)
    if top == "hangul":
        return "ko"
    if top == "han":
        return "zh"
    if top == "arabic":
        if _UR_ONLY.search(text):
            return "ur"
        if _FA_ONLY.search(text):
            return "fa"
        return "ar"
    if top == "cyrillic":
        return "uk" if _UK_ONLY.search(text) else "ru"
    if top == "devanagari":
        return "hi"
    if top == "thai":
        return "th"
    if top == "greek":
        return "el"
    return None
