# Changelog

## 7.0.0

**Rewritten on an async core.**

### Fixed
- Handlers no longer block: v6 ran a synchronous PTB 13 loop where one slow translation (up to 4 engines × 10 s) stalled the user. Now fully async (`python-telegram-bot` 22) with concurrent updates.
- Language detection: v6 spent a whole translation request on detection and then threw the answer away; its regex mislabeled Arabic as Persian and kanji-Japanese as Chinese. Now engine-reported language + an offline script detector (fa/ar/ur, ja/zh/ko, ru/uk, hi, th, el).
- A correct translation identical to the input (names, numbers, URLs) was treated as a failure and retried on every engine.
- Markdown crash: user text containing backticks or `_`/`*` caused a Telegram parse error, which the bot reported as "translation failed" even though it had succeeded. All output is now HTML-escaped.
- Messages near the 4000-character limit exceeded Telegram's 4096 limit (text was echoed back in the reply). Long results are now split safely.
- The "rank" shown to users was `random.randint`. Rank is now real, computed from the database.
- The level progress bar used `count % 100`; it now shows the real progress toward the next level.
- Unused `ADMIN_ID` — now powers `/admin` and `/broadcast`.
- Bot token could leak through `httpx` INFO logs; those loggers are silenced.

### Added
- **Gemini AI engine** (optional, `GEMINI_API_KEY`) — context-aware LLM translation with automatic fallback to Google, then LibreTranslate / MyMemory.
- Circuit breaker per engine (3 failures → cooldown with back-off), per-engine timeouts, LRU+TTL translation cache.
- Smart target: text already in the target language is translated to English (or Persian when English is the target).
- No "start translating" step — just send text (or a photo caption).
- `/tr [lang] text`, reply-to-message translation (works in groups), `/lang`, `/history`, `/privacy`, `/deleteme`.
- Result buttons: 📋 copy, 🔁 reverse translation, 🌍 translate to another language.
- 28 languages (added Azerbaijani, Kurdish, Ukrainian, Urdu, Polish, Swedish, Czech, Romanian, Hungarian, Greek, Indonesian, Vietnamese, Thai).
- SQLite storage with WAL (auto-imports v6 `bot_data.json`), per-user rate limit.
- Redesigned messages (HTML, blockquotes, clean cards instead of box-drawing frames that broke in RTL).
- `/health` JSON endpoint (status, uptime, engine states) for Render health checks and cron pings.
- Test suite (`pytest`), `.env.example`, `render.yaml`.

### Changed
- Removed the `translators` dependency (heavy, scraping-based, did network I/O at import time).
- Code split into the `botam/` package; `python bot.py` still starts the bot.
