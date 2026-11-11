from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

from telegram import Message, Update
from telegram.constants import ChatAction, ChatType
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from . import ui
from .config import Config
from .languages import LANGUAGES, TARGET_CODES
from .storage import Database
from .translator import TranslationError, Translator
from .utils import RateLimiter

log = logging.getLogger("botam.handlers")


@dataclass
class Services:
    cfg: Config
    db: Database
    limiter: RateLimiter
    translator: Translator | None = None
    started_at: float = field(default_factory=time.time)
    last_admin_alert: float = 0.0

    @property
    def uptime(self) -> float:
        return time.time() - self.started_at


def svc(context: ContextTypes.DEFAULT_TYPE) -> Services:
    return context.application.bot_data["svc"]


def _user(update: Update, context) -> dict:
    u = update.effective_user
    return svc(context).db.touch_user(u.id, u.first_name or "", u.username or "")


async def safe_edit(query, text: str, markup=None):
    try:
        await query.edit_message_text(text, reply_markup=markup)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


# ───────────────────────── commands ─────────────────────────
async def cmd_start(update: Update, context):
    user = _user(update, context)
    await update.effective_message.reply_text(ui.welcome(update.effective_user.first_name or "دوست من", user), reply_markup=ui.main_menu())


async def cmd_help(update: Update, context):
    await update.effective_message.reply_text(ui.help_text(), reply_markup=ui.back_menu())


async def cmd_about(update: Update, context):
    s = svc(context)
    names = [e.label for e in s.translator.engines] if s.translator else []
    await update.effective_message.reply_text(ui.about_text(names, s.db.stats(), s.uptime), reply_markup=ui.back_menu())


async def cmd_privacy(update: Update, context):
    await update.effective_message.reply_text(ui.privacy_text(), reply_markup=ui.back_menu())


async def cmd_lang(update: Update, context):
    user = _user(update, context)
    await update.effective_message.reply_text(ui.settings_text(user), reply_markup=ui.settings_menu())


async def cmd_stats(update: Update, context):
    s = svc(context)
    user = _user(update, context)
    await update.effective_message.reply_text(
        ui.stats_text(user, s.db.rank(user["id"]), s.db.stats()), reply_markup=ui.back_menu()
    )


async def cmd_history(update: Update, context):
    s = svc(context)
    user = _user(update, context)
    items = s.db.recent(user["id"], 5)
    await update.effective_message.reply_text(ui.history_text(items), reply_markup=ui.history_menu(bool(items)))


async def cmd_deleteme(update: Update, context):
    await update.effective_message.reply_text(ui.delete_confirm_text(), reply_markup=ui.delete_confirm_menu())


_TR_ARGS = re.compile(r"^([A-Za-z]{2}(?:-[A-Za-z]{2})?)(?:\s+(.*))?$", re.S)


async def cmd_tr(update: Update, context):
    """/tr [lang] text  — or reply to a message with /tr [lang]."""
    msg = update.effective_message
    rest = (msg.text or "").split(None, 1)
    rest = rest[1] if len(rest) > 1 else ""
    dst = None
    m = _TR_ARGS.match(rest.strip())
    if m and m.group(1).lower() in TARGET_CODES:
        dst, rest = m.group(1).lower(), (m.group(2) or "")
    text = rest.strip()
    if not text and msg.reply_to_message:
        text = (msg.reply_to_message.text or msg.reply_to_message.caption or "").strip()
    if not text:
        await msg.reply_text("✍️ مثال:\n<code>/tr en سلام دنیا</code>\nیا روی یه پیام ریپلای کن و <code>/tr</code> بزن.")
        return
    await do_translate(update, context, text, dst=dst)


async def cmd_admin(update: Update, context):
    s = svc(context)
    if update.effective_user.id not in s.cfg.admin_ids:
        return
    status = s.translator.status() if s.translator else {}
    await update.effective_message.reply_text(ui.admin_text(s.db.stats(), status, s.uptime))


async def cmd_broadcast(update: Update, context):
    s = svc(context)
    if update.effective_user.id not in s.cfg.admin_ids:
        return
    parts = (update.effective_message.text or "").split(None, 1)
    if len(parts) < 2:
        await update.effective_message.reply_text("استفاده: <code>/broadcast متن پیام</code>")
        return
    text, sent, failed = parts[1], 0, 0
    status = await update.effective_message.reply_text("📣 در حال ارسال…")
    for uid in s.db.all_user_ids():
        try:
            await context.bot.send_message(uid, text, parse_mode=None)
            sent += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                await context.bot.send_message(uid, text, parse_mode=None)
                sent += 1
            except TelegramError:
                failed += 1
        except (Forbidden, BadRequest):
            failed += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)  # ≈20 msg/s, well under Telegram's limit
    await status.edit_text(f"✅ ارسال شد: {sent:,}\n❌ ناموفق: {failed:,}")


# ───────────────────────── translation flow ─────────────────────────
async def send_result(message: Message, res, hid: int):
    parts = ui.result_messages(res)
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        await message.reply_text(part, reply_markup=ui.result_keyboard(hid, res.text) if last else None)


async def do_translate(update: Update, context, text: str, dst: str | None = None):
    s = svc(context)
    msg = update.effective_message
    user = _user(update, context)

    if len(text) > s.cfg.max_chars:
        await msg.reply_text(ui.ERR_TOO_LONG.format(max=f"{s.cfg.max_chars:,}", n=len(text)))
        return
    if not s.limiter.allow(user["id"]):
        await msg.reply_text(ui.ERR_RATE)
        return
    if s.translator is None:
        await msg.reply_text(ui.ERR_GENERIC)
        return

    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    src, target = user["source_lang"], dst or user["target_lang"]
    try:
        res = await s.translator.translate_smart(text, src, target)
    except TranslationError as e:
        log.warning("all engines failed: %s", e)
        await msg.reply_text(ui.ERR_ALL_FAILED)
        return

    hid = s.db.add_translation(user["id"], text, res.text, res.src, res.dst, res.engine)
    await send_result(msg, res, hid)


async def on_text(update: Update, context):
    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()
    if text:
        await do_translate(update, context, text)


async def on_other(update: Update, context):
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.effective_message.reply_text(ui.HINT_NO_TEXT)


# ───────────────────────── inline buttons ─────────────────────────
async def cb_menu(update: Update, context):
    q = update.callback_query
    await q.answer()
    s, user = svc(context), _user(update, context)
    page = q.data.split(":")[1]
    if page == "main":
        await safe_edit(q, ui.main_menu_text(), ui.main_menu())
    elif page == "settings":
        await safe_edit(q, ui.settings_text(user), ui.settings_menu())
    elif page == "stats":
        await safe_edit(q, ui.stats_text(user, s.db.rank(user["id"]), s.db.stats()), ui.back_menu())
    elif page == "hist":
        items = s.db.recent(user["id"], 5)
        await safe_edit(q, ui.history_text(items), ui.history_menu(bool(items)))
    elif page == "langs":
        await safe_edit(q, ui.languages_text(), ui.back_menu())
    elif page == "help":
        await safe_edit(q, ui.help_text(), ui.back_menu())
    elif page == "about":
        names = [e.label for e in s.translator.engines] if s.translator else []
        await safe_edit(q, ui.about_text(names, s.db.stats(), s.uptime), ui.back_menu())


async def cb_pick(update: Update, context):
    q = update.callback_query
    await q.answer()
    user = _user(update, context)
    kind = q.data.split(":")[1]
    sel = user["source_lang"] if kind == "src" else user["target_lang"]
    await safe_edit(q, ui.pick_text(kind), ui.language_grid(kind, sel, include_auto=(kind == "src")))


async def cb_set_lang(update: Update, context):
    q = update.callback_query
    kind, code = q.data.split(":")
    if code not in LANGUAGES or (kind == "dst" and code == "auto"):
        await q.answer()
        return
    s, user = svc(context), _user(update, context)
    s.db.set_langs(user["id"], source=code if kind == "src" else None, target=code if kind == "dst" else None)
    await q.answer(f"✅ {LANGUAGES[code].name}")
    await safe_edit(q, ui.settings_text(s.db.get_user(user["id"])), ui.settings_menu())


async def cb_swap(update: Update, context):
    q = update.callback_query
    s, user = svc(context), _user(update, context)
    if user["source_lang"] == "auto":
        await q.answer("اول زبان مبدأ رو مشخص کن (نه «تشخیص خودکار»).", show_alert=True)
        return
    s.db.set_langs(user["id"], source=user["target_lang"], target=user["source_lang"])
    await q.answer("🔄 جابه‌جا شد")
    await safe_edit(q, ui.settings_text(s.db.get_user(user["id"])), ui.settings_menu())


async def cb_reset(update: Update, context):
    q = update.callback_query
    s, user = svc(context), _user(update, context)
    s.db.set_langs(user["id"], source="auto", target="fa")
    await q.answer("♻️ بازنشانی شد")
    await safe_edit(q, ui.settings_text(s.db.get_user(user["id"])), ui.settings_menu())


async def cb_history_clear(update: Update, context):
    q = update.callback_query
    s, user = svc(context), _user(update, context)
    s.db.clear_history(user["id"])
    await q.answer("🗑 تاریخچه پاک شد")
    await safe_edit(q, ui.history_text([]), ui.history_menu(False))


async def cb_delete(update: Update, context):
    q = update.callback_query
    s = svc(context)
    s.db.delete_user(update.effective_user.id)
    await q.answer("حذف شد")
    await safe_edit(q, "🗑 همه‌ی اطلاعات تو حذف شد. هر وقت خواستی با /start دوباره شروع کن.", None)


async def cb_pick_for_item(update: Update, context):
    q = update.callback_query
    await q.answer()
    hid = int(q.data.split(":")[1])
    await q.edit_message_reply_markup(ui.language_grid(f"rt:{hid}", back=f"bk:{hid}"))


async def cb_back_to_result(update: Update, context):
    q = update.callback_query
    await q.answer()
    s = svc(context)
    hid = int(q.data.split(":")[1])
    item = s.db.get_item(update.effective_user.id, hid)
    if item:
        await q.edit_message_reply_markup(ui.result_keyboard(hid, item["translated"]))


async def _retranslate(update: Update, context, text: str, src: str, dst: str):
    q = update.callback_query
    s = svc(context)
    if not s.limiter.allow(update.effective_user.id):
        await q.answer(ui.ERR_RATE, show_alert=True)
        return
    await q.answer("⏳")
    try:
        res = await s.translator.translate(text, src, dst)
    except TranslationError:
        await q.message.reply_text(ui.ERR_ALL_FAILED)
        return
    user = _user(update, context)
    hid = s.db.add_translation(user["id"], text, res.text, res.src, res.dst, res.engine)
    await send_result(q.message, res, hid)


async def cb_retranslate(update: Update, context):
    q = update.callback_query
    _, hid, dst = q.data.split(":")
    item = svc(context).db.get_item(update.effective_user.id, int(hid))
    if not item or dst not in TARGET_CODES:
        await q.answer("این ترجمه دیگه در تاریخچه نیست.", show_alert=True)
        return
    await _retranslate(update, context, item["original"], "auto", dst)


async def cb_reverse(update: Update, context):
    q = update.callback_query
    item = svc(context).db.get_item(update.effective_user.id, int(q.data.split(":")[1]))
    if not item:
        await q.answer("این ترجمه دیگه در تاریخچه نیست.", show_alert=True)
        return
    back_to = item["src"] if item["src"] in TARGET_CODES else "fa"
    await _retranslate(update, context, item["translated"], item["dst"], back_to)


# ───────────────────────── errors ─────────────────────────
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    log.error("unhandled error", exc_info=err)
    s: Services | None = context.application.bot_data.get("svc")
    try:
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.answer(ui.ERR_GENERIC, show_alert=True)
            elif update.effective_message:
                await update.effective_message.reply_text(ui.ERR_GENERIC)
    except TelegramError:
        pass
    if s and s.cfg.admin_ids and time.time() - s.last_admin_alert > 600:
        s.last_admin_alert = time.time()
        for admin in s.cfg.admin_ids:
            try:
                await context.bot.send_message(admin, f"⚠️ BotAM error: {type(err).__name__}: {str(err)[:200]}", parse_mode=None)
            except TelegramError:
                pass


# ───────────────────────── wiring ─────────────────────────
def register(app: Application):
    cmds = {
        "start": cmd_start, "help": cmd_help, "about": cmd_about, "info": cmd_about, "privacy": cmd_privacy,
        "lang": cmd_lang, "settings": cmd_lang, "stats": cmd_stats, "history": cmd_history,
        "deleteme": cmd_deleteme, "tr": cmd_tr, "admin": cmd_admin, "broadcast": cmd_broadcast,
    }
    for name, fn in cmds.items():
        app.add_handler(CommandHandler(name, fn))

    cb = CallbackQueryHandler
    app.add_handler(cb(cb_menu, pattern=r"^m:\w+$"))
    app.add_handler(cb(cb_pick, pattern=r"^s:(src|dst)$"))
    app.add_handler(cb(cb_set_lang, pattern=r"^(src|dst):[\w-]+$"))
    app.add_handler(cb(cb_swap, pattern=r"^swap$"))
    app.add_handler(cb(cb_reset, pattern=r"^reset$"))
    app.add_handler(cb(cb_history_clear, pattern=r"^h:clear$"))
    app.add_handler(cb(cb_delete, pattern=r"^del:yes$"))
    app.add_handler(cb(cb_pick_for_item, pattern=r"^pk:\d+$"))
    app.add_handler(cb(cb_back_to_result, pattern=r"^bk:\d+$"))
    app.add_handler(cb(cb_retranslate, pattern=r"^rt:\d+:[\w-]+$"))
    app.add_handler(cb(cb_reverse, pattern=r"^rv:\d+$"))

    private = filters.ChatType.PRIVATE
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND & private, on_text))
    app.add_handler(MessageHandler(~filters.COMMAND & private & ~(filters.TEXT | filters.CAPTION) & ~filters.StatusUpdate.ALL, on_other))
    app.add_error_handler(on_error)
