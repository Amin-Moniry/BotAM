from __future__ import annotations

import time
from collections import deque


def _best_cut(s: str, limit: int) -> int:
    window = s[:limit]
    for seps in (".!?؟۔。！？", "،,;؛", " "):
        idx = max(window.rfind(ch) for ch in seps)
        if idx > limit * 0.4:
            return idx + 1
    return limit


def chunk_text(text: str, limit: int) -> list[str]:
    """Split on line / sentence / word boundaries; ``"".join(chunks) == text``."""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            cut = _best_cut(line, limit)
            pieces.append(line[:cut])
            line = line[cut:]
        if line:
            pieces.append(line)
    chunks: list[str] = []
    buf = ""
    for p in pieces:
        if buf and len(buf) + len(p) > limit:
            chunks.append(buf)
            buf = ""
        buf += p
    if buf:
        chunks.append(buf)
    return chunks


class RateLimiter:
    """Sliding-window limiter: at most ``count`` hits per ``window`` seconds per key."""

    def __init__(self, count: int, window: float):
        self.count, self.window = count, window
        self._hits: dict[int, deque[float]] = {}

    def allow(self, key: int) -> bool:
        now = time.monotonic()
        dq = self._hits.setdefault(key, deque())
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= self.count:
            return False
        dq.append(now)
        if len(self._hits) > 5000:
            self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] <= self.window}
        return True
