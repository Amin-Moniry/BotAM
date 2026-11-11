"""Engine chain with timeouts, circuit breaker, LRU+TTL cache and smart target."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass

import httpx

from .detect import guess_language
from .engines import Engine, EngineError
from .languages import normalize_code

log = logging.getLogger("botam.translator")


class TranslationError(Exception):
    pass


@dataclass
class Result:
    text: str
    src: str
    dst: str
    engine: str
    engine_label: str
    cached: bool
    elapsed: float


class Translator:
    FAIL_THRESHOLD = 3
    BASE_COOLDOWN = 60.0
    MAX_COOLDOWN = 600.0

    def __init__(self, engines: list[Engine], client: httpx.AsyncClient, cache_size: int = 2000, cache_ttl: int = 86400):
        self.engines, self.client = engines, client
        self.cache_size, self.cache_ttl = cache_size, cache_ttl
        self._cache: OrderedDict[tuple, tuple[float, Result]] = OrderedDict()
        self._state = {e.name: {"fails": 0, "open_until": 0.0, "cooldown": self.BASE_COOLDOWN, "ok": 0, "err": 0} for e in engines}

    # ── cache ──
    def _cache_get(self, key):
        item = self._cache.get(key)
        if not item:
            return None
        ts, res = item
        if time.monotonic() - ts > self.cache_ttl:
            self._cache.pop(key, None)
            return None
        self._cache.move_to_end(key)
        return res

    def _cache_put(self, key, res):
        self._cache[key] = (time.monotonic(), res)
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    # ── breaker ──
    def _is_open(self, e: Engine) -> bool:
        return self._state[e.name]["open_until"] > time.monotonic()

    def _ok(self, e: Engine):
        s = self._state[e.name]
        s.update(fails=0, open_until=0.0, cooldown=self.BASE_COOLDOWN)
        s["ok"] += 1

    def _fail(self, e: Engine):
        s = self._state[e.name]
        s["fails"] += 1
        s["err"] += 1
        if s["fails"] >= self.FAIL_THRESHOLD:
            s["open_until"] = time.monotonic() + s["cooldown"]
            s["cooldown"] = min(s["cooldown"] * 2, self.MAX_COOLDOWN)
            log.warning("engine %s disabled for %.0fs", e.name, s["open_until"] - time.monotonic())

    def status(self) -> dict[str, str]:
        now = time.monotonic()
        return {
            n: ("cooldown %ds" % (s["open_until"] - now) if s["open_until"] > now else "ok")
            for n, s in self._state.items()
        }

    # ── core ──
    async def translate(self, text: str, src: str, dst: str) -> Result:
        key = (src, dst, text)
        hit = self._cache_get(key)
        if hit:
            return Result(**{**hit.__dict__, "cached": True, "elapsed": 0.0})

        started = time.perf_counter()
        errors: list[str] = []
        live = [e for e in self.engines if not self._is_open(e)]
        # if every engine is cooling down, still try them rather than fail instantly
        for engine in live or self.engines:
            try:
                res = await asyncio.wait_for(engine.run(self.client, text, src, dst), engine.timeout + 2)
            except (EngineError, httpx.HTTPError, asyncio.TimeoutError) as e:
                errors.append(f"{engine.name}: {type(e).__name__} {e}")
                self._fail(engine)
                continue
            except Exception as e:  # never let one engine's bug kill the chain
                log.exception("engine %s crashed", engine.name)
                errors.append(f"{engine.name}: {type(e).__name__}")
                self._fail(engine)
                continue
            self._ok(engine)
            detected = normalize_code(res.detected) or (src if src != "auto" else guess_language(text)) or "auto"
            out = Result(res.text, detected, dst, engine.name, engine.label, False, time.perf_counter() - started)
            self._cache_put(key, out)
            return out
        raise TranslationError("; ".join(errors) or "no engines")

    async def translate_smart(self, text: str, src: str, dst: str) -> Result:
        """If the text is already in the target language, translate to the fallback (en ↔ fa) instead."""
        alt = "en" if dst != "en" else "fa"
        guess = src if src != "auto" else guess_language(text)
        if guess == dst:
            return await self.translate(text, src if src != dst else "auto", alt)
        res = await self.translate(text, src, dst)
        if src == "auto" and res.src == dst:
            return await self.translate(text, "auto", alt)
        return res
