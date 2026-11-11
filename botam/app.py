from __future__ import annotations

import logging
from pathlib import Path

import httpx
from telegram import BotCommand, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import Application, Defaults

from . import __version__
from .config import Config
from .engines import build_engines
from .handlers import Services, register
from .health import start_health_server
from .storage import Database
from .translator import Translator
from .utils import RateLimiter

log = logging.getLogger("botam")

COMMANDS = [
    ("start", "شروع و منوی اصلی"),
    ("tr", "ترجمه‌ی یک‌باره: /tr en سلام"),
    ("lang", "تنظیم زبان مبدأ و مقصد"),
    ("history", "آخرین ترجمه‌ها"),
    ("stats", "آمار و سطح من"),
    ("help", "راهنما"),
    ("about", "درباره‌ی ربات"),
    ("privacy", "حریم خصوصی"),
    ("deleteme", "حذف اطلاعات من"),
]


def setup_logging(level: str):
    logging.basicConfig(level=getattr(logging, level, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs full request URLs at INFO — for Telegram that URL contains the bot token.
    for noisy in ("httpx", "httpcore", "telegram.ext.Application"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def post_init(app: Application):
    s: Services = app.bot_data["svc"]
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=6.0),
        limits=httpx.Limits(max_connections=40, max_keepalive_connections=10),
        headers={"User-Agent": f"BotAM/{__version__}"},
        follow_redirects=True,
    )
    s.translator = Translator(build_engines(s.cfg), client, s.cfg.cache_size, s.cfg.cache_ttl)
    app.bot_data["http"] = client
    await app.bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])
    me = await app.bot.get_me()
    log.info("BotAM v%s started as @%s — engines: %s", __version__, me.username, ", ".join(e.name for e in s.translator.engines))


async def post_shutdown(app: Application):
    client = app.bot_data.get("http")
    if client:
        await client.aclose()
    app.bot_data["svc"].db.close()


def build_app(cfg: Config) -> Application:
    db = Database(cfg.db_path)
    for legacy in (cfg.data_dir / "bot_data.json", Path("bot_data.json")):
        if db.import_legacy_json(legacy):
            break
    defaults = Defaults(parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))
    builder = (
        Application.builder()
        .token(cfg.token)
        .defaults(defaults)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
    )
    if cfg.api_base:
        builder = builder.base_url(f"{cfg.api_base}/bot").base_file_url(f"{cfg.api_base}/file/bot")
    app = builder.build()
    app.bot_data["svc"] = Services(cfg=cfg, db=db, limiter=RateLimiter(cfg.rate_limit_count, cfg.rate_limit_window))
    register(app)
    return app


def main():
    cfg = Config.from_env()
    setup_logging(cfg.log_level)
    app = build_app(cfg)
    svc = app.bot_data["svc"]
    start_health_server(cfg.port, lambda: svc.translator.status() if svc.translator else {})
    log.info("health endpoint on :%d (/health)", cfg.port)
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
        bootstrap_retries=-1,   # keep retrying if Telegram is briefly unreachable at boot
    )
