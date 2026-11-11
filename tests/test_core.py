import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from botam import ui
from botam.config import Config
from botam.detect import guess_language
from botam.engines import EngineError, GeminiEngine, GoogleEngine, MyMemoryEngine
from botam.handlers import Services, do_translate
from botam.storage import Database
from botam.translator import TranslationError, Translator
from botam.utils import RateLimiter, chunk_text


def run(coro):
    return asyncio.run(coro)


def client_with(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def gtx_payload(text, detected):
    return [[[text, "orig", None, None, 10]], None, detected]


# ───────────── detection / chunking ─────────────
@pytest.mark.parametrize("text,expected", [
    ("سلام دنیا، حالت چطوره؟", "fa"),
    ("مرحبا بكم في العالم", "ar"),
    ("こんにちは世界", "ja"),
    ("漢字だけではなく", "ja"),
    ("你好，世界", "zh"),
    ("안녕하세요", "ko"),
    ("Привет, мир", "ru"),
    ("Привіт, їжак", "uk"),
    ("नमस्ते दुनिया", "hi"),
    ("Hello world", None),
    ("12345 !!!", None),
])
def test_guess_language(text, expected):
    assert guess_language(text) == expected


def test_chunk_roundtrip_and_limit():
    text = ("Sentence number one. " * 50 + "\n\n" + "کلمه " * 300 + "\n" + "x" * 500)
    for limit in (100, 450, 1800):
        chunks = chunk_text(text, limit)
        assert "".join(chunks) == text
        assert all(len(c) <= limit for c in chunks)


def test_rate_limiter():
    rl = RateLimiter(3, 0.2)
    assert [rl.allow(1) for _ in range(4)] == [True, True, True, False]
    assert rl.allow(2)
    time.sleep(0.25)
    assert rl.allow(1)


# ───────────── engines (mocked HTTP) ─────────────
def test_google_engine_parses_and_keeps_whitespace():
    def handler(req):
        assert req.url.params["tl"] == "fa"
        return httpx.Response(200, json=gtx_payload("سلام", "en"))
    async def go():
        async with client_with(handler) as c:
            return await GoogleEngine().run(c, "\nHello \n", "auto", "fa")
    res = run(go())
    assert res.text == "\nسلام \n" and res.detected == "en"


def test_google_engine_chunks_long_text_concurrently():
    calls = []
    def handler(req):
        calls.append(1)
        return httpx.Response(200, json=gtx_payload("X", "en"))
    async def go():
        async with client_with(handler) as c:
            return await GoogleEngine().run(c, "word " * 1000, "auto", "fa")
    run(go())
    assert len(calls) >= 3


def test_google_engine_http_error():
    async def go():
        async with client_with(lambda r: httpx.Response(429)) as c:
            await GoogleEngine().run(c, "hi", "auto", "fa")
    with pytest.raises(EngineError):
        run(go())


def test_gemini_engine_json_and_thinking_fallback():
    seen = []
    def handler(req):
        body = json.loads(req.content)
        seen.append("thinkingConfig" in body["generationConfig"])
        if "thinkingConfig" in body["generationConfig"]:
            return httpx.Response(400, json={"error": "no thinking"})
        out = {"source": "en", "translation": "سلام"}
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(out)}]}}]})
    async def go():
        async with client_with(handler) as c:
            return await GeminiEngine("k", "m").run(c, "Hello", "auto", "fa")
    res = run(go())
    assert res.text == "سلام" and res.detected == "en"
    assert seen == [True, False]


def test_gemini_bad_payload():
    async def go():
        async with client_with(lambda r: httpx.Response(200, json={"candidates": []})) as c:
            await GeminiEngine("k", "m").run(c, "Hello", "auto", "fa")
    with pytest.raises(EngineError):
        run(go())


def test_mymemory_quota_warning():
    payload = {"responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS"}, "responseStatus": 429}
    async def go():
        async with client_with(lambda r: httpx.Response(200, json=payload)) as c:
            await MyMemoryEngine().run(c, "hi", "auto", "fa")
    with pytest.raises(EngineError):
        run(go())


# ───────────── translator manager ─────────────
class FakeEngine:
    def __init__(self, name, fail=False, text="T", detected="en"):
        self.name, self.label, self.timeout = name, name.title(), 1
        self.fail, self.text, self.detected, self.calls = fail, text, detected, 0
    async def run(self, client, text, src, dst):
        self.calls += 1
        if self.fail:
            raise EngineError("boom")
        from botam.engines import EngineResult
        return EngineResult(self.text, self.detected)


def test_fallback_cache_and_identical_output_is_ok():
    bad, good = FakeEngine("a", fail=True), FakeEngine("b", text="Hello")  # output == input must be accepted
    t = Translator([bad, good], None)
    r1 = run(t.translate("Hello", "auto", "fa"))
    assert r1.engine == "b" and r1.text == "Hello" and not r1.cached
    r2 = run(t.translate("Hello", "auto", "fa"))
    assert r2.cached and good.calls == 1


def test_circuit_breaker_opens_and_all_fail_raises():
    bad, good = FakeEngine("a", fail=True), FakeEngine("b")
    t = Translator([bad, good], None)
    for i in range(5):
        run(t.translate(f"text {i}", "auto", "fa"))
    assert bad.calls == 3                      # skipped after 3 consecutive failures
    assert "cooldown" in t.status()["a"]
    with pytest.raises(TranslationError):
        run(Translator([FakeEngine("x", fail=True)], None).translate("hi", "auto", "fa"))


def test_smart_target_swaps_when_text_already_in_target():
    eng = FakeEngine("a", text="Hello", detected="fa")
    t = Translator([eng], None)
    res = run(t.translate_smart("سلام", "auto", "fa"))
    assert res.dst == "en"                      # Persian text + Persian target → English
    eng2 = FakeEngine("a", text="x", detected="en")
    res2 = run(Translator([eng2], None).translate_smart("Hello", "auto", "en"))
    assert res2.dst == "fa"


def test_smart_target_after_engine_detection():
    class Eng(FakeEngine):
        async def run(self, client, text, src, dst):
            from botam.engines import EngineResult
            return EngineResult("same" if dst == "fr" else "translated", "fr")
    res = run(Translator([Eng("a")], None).translate_smart("Bonjour", "auto", "fr"))
    assert res.dst == "en" and res.text == "translated"


# ───────────── storage ─────────────
def test_storage_history_rank_delete_and_legacy(tmp_path):
    db = Database(":memory:")
    db.touch_user(1, "A", "a"); db.touch_user(2, "B", "b")
    for i in range(25):
        db.add_translation(1, f"o{i}", f"t{i}", "en", "fa", "google")
    db.add_translation(2, "x", "y", "en", "fa", "google")
    assert len(db.recent(1, 100)) == 20          # trimmed
    assert db.get_user(1)["count"] == 25
    assert db.rank(1) == (1, 2) and db.rank(2) == (2, 2)
    hid = db.recent(1, 1)[0]["id"]
    assert db.get_item(1, hid) and db.get_item(2, hid) is None   # users can't read each other's history
    assert db.stats()["translations"] == 26
    db.delete_user(1)
    assert db.get_user(1) is None and db.recent(1) == []

    legacy = tmp_path / "bot_data.json"
    legacy.write_text(json.dumps({"translations": 7, "users": {"42": {"count": 7, "source_lang": "en", "target_lang": "de",
        "history": [{"original": "hi", "translated": "hallo", "src": "en", "tgt": "de"}]}}}))
    fresh = Database(":memory:")
    assert fresh.import_legacy_json(legacy) == 1
    u = fresh.get_user(42)
    assert u["count"] == 7 and u["target_lang"] == "de" and fresh.recent(42)[0]["translated"] == "hallo"
    assert fresh.import_legacy_json(legacy) == 0   # idempotent


# ───────────── UI ─────────────
def test_result_message_escapes_html_and_splits():
    from botam.translator import Result
    nasty = "<b>x</b> & `code` ```fence```"
    res = Result(nasty, "en", "fa", "google", "Google Translate", False, 0.4)
    msg = ui.result_messages(res)[0]
    assert "&lt;b&gt;x&lt;/b&gt; &amp;" in msg and "<b>x</b>" not in msg
    long = Result("جمله. " * 2000, "en", "fa", "google", "Google", False, 1.0)
    parts = ui.result_messages(long)
    assert len(parts) > 1 and all(len(p) < 4096 for p in parts)


def test_progress_and_levels():
    assert ui.level_of(0).endswith("مبتدی") and ui.level_of(1000).endswith("استاد ترجمه")
    assert ui.progress(75)[0] == 50 and ui.progress(5000)[2] is None


# ───────────── handler flow (fake Telegram objects) ─────────────
def make_ctx(db, translator):
    cfg = Config(token="1:x")
    s = Services(cfg=cfg, db=db, limiter=RateLimiter(5, 60), translator=translator)
    bot = MagicMock(); bot.send_chat_action = AsyncMock()
    return SimpleNamespace(application=SimpleNamespace(bot_data={"svc": s}), bot=bot), s


def make_update(text, uid=7):
    msg = MagicMock(); msg.reply_text = AsyncMock(); msg.chat_id = uid; msg.text = text
    user = SimpleNamespace(id=uid, first_name="Ali <&>", username="ali")
    return SimpleNamespace(effective_message=msg, effective_user=user), msg


def test_full_translate_flow_and_failure_flow():
    db = Database(":memory:")
    ctx, s = make_ctx(db, Translator([FakeEngine("g", text="سلام <دنیا>", detected="en")], None))
    upd, msg = make_update("Hello `world`")
    run(do_translate(upd, ctx, "Hello `world`"))
    args, kwargs = msg.reply_text.call_args
    assert "&lt;دنیا&gt;" in args[0] and kwargs["reply_markup"] is not None
    assert db.get_user(7)["count"] == 1

    # all engines down → friendly error, counter untouched
    ctx2, _ = make_ctx(Database(":memory:"), Translator([FakeEngine("g", fail=True)], None))
    upd2, msg2 = make_update("Hello")
    run(do_translate(upd2, ctx2, "Hello"))
    assert msg2.reply_text.call_args[0][0] == ui.ERR_ALL_FAILED

    # too long + rate limit
    upd3, msg3 = make_update("x")
    run(do_translate(upd3, ctx, "x" * 5000))
    assert "حداکثر" in msg3.reply_text.call_args[0][0]
    for _ in range(6):
        run(do_translate(upd3, ctx, "hello"))
    assert msg3.reply_text.call_args[0][0] == ui.ERR_RATE
