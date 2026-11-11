"""All user-facing texts and keyboards (Persian, HTML parse mode)."""
from __future__ import annotations

from datetime import datetime
from html import escape as esc

from telegram import CopyTextButton, InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

from . import __version__
from .languages import LANGUAGES, TARGET_CODES, label
from .translator import Result
from .utils import chunk_text

LINE = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈"
LEVELS = [(0, "📘 مبتدی"), (50, "⭐ پیشرفته"), (100, "💎 ماهر"), (500, "🏆 حرفه‌ای"), (1000, "👑 استاد ترجمه")]
BOT_LINK = "https://t.me/BotamBotamBotamBot"
GITHUB = "https://github.com/Amin-Moniry/BotAM"
DEV = "https://t.me/amintivanix2"


# ───────────────────────── helpers ─────────────────────────
def level_of(count: int) -> str:
    name = LEVELS[0][1]
    for threshold, lvl in LEVELS:
        if count >= threshold:
            name = lvl
    return name


def progress(count: int) -> tuple[int, str, int | None]:
    """(percent, bar, next_threshold) toward the next level."""
    for i, (threshold, _) in enumerate(LEVELS):
        nxt = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else None
        if nxt is None or count < nxt:
            if nxt is None:
                return 100, "▰" * 10, None
            pct = int((count - threshold) / (nxt - threshold) * 100)
            filled = pct // 10
            return pct, "▰" * filled + "▱" * (10 - filled), nxt
    return 100, "▰" * 10, None


def _short(s: str, n: int = 70) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _fmt_uptime(sec: float) -> str:
    d, r = divmod(int(sec), 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return (f"{d}d " if d else "") + f"{h}h {m}m"


# ───────────────────────── texts ─────────────────────────
def welcome(name: str, user: dict) -> str:
    return (
        f"<b>🌐 BotAM</b>  <i>v{__version__}</i>\n"
        f"<i>مترجم هوشمند چندموتوره</i>\n{LINE}\n\n"
        f"سلام <b>{esc(name)}</b> 👋\n"
        "هر متنی بفرستی، زبانش رو تشخیص می‌دم و همون لحظه ترجمه می‌کنم — بدون هیچ مرحله‌ی اضافه.\n\n"
        f"<b>⚙️ تنظیم فعلی</b>\n"
        f"🔍 مبدأ:  {label(user['source_lang'])}\n"
        f"🎯 مقصد: {label(user['target_lang'])}\n\n"
        f"<b>🏆 وضعیت شما</b>\n"
        f"{level_of(user['count'])}  ·  {user['count']:,} ترجمه\n\n"
        "💡 <i>اگه متن از قبل به زبان مقصد باشه، خودکار به انگلیسی (یا فارسی) برمی‌گردونمش.</i>"
    )


def main_menu_text() -> str:
    return f"<b>🏠 منوی اصلی</b>\n{LINE}\n\nمتنت رو همین‌جا بفرست تا ترجمه کنم، یا از دکمه‌های زیر استفاده کن 👇"


def settings_text(user: dict) -> str:
    return (
        f"<b>⚙️ تنظیمات زبان</b>\n{LINE}\n\n"
        f"🔍 <b>مبدأ</b>\n{label(user['source_lang'])}\n\n"
        f"🎯 <b>مقصد</b>\n{label(user['target_lang'])}\n\n"
        "<i>برای ترجمه فقط متن بفرست. برای یک‌بار ترجمه به زبان دیگه: </i><code>/tr en سلام</code>"
    )


def pick_text(kind: str) -> str:
    if kind == "src":
        return f"<b>🔍 زبان مبدأ</b>\n{LINE}\n\nزبان متنی که می‌فرستی رو انتخاب کن.\n<i>مطمئن نیستی؟ «تشخیص خودکار» رو بزن.</i>"
    return f"<b>🎯 زبان مقصد</b>\n{LINE}\n\nمی‌خوای متن‌ها به چه زبانی ترجمه بشن؟"


def stats_text(user: dict, rank: tuple[int, int], gstats: dict) -> str:
    pct, bar, nxt = progress(user["count"])
    nxt_line = f"{bar}  {pct}%\n<i>تا سطح بعد: {nxt - user['count']:,} ترجمه</i>" if nxt else f"{bar}  حداکثر سطح 🎉"
    since = datetime.fromtimestamp(user["created_at"]).strftime("%Y/%m/%d") if user.get("created_at") else "—"
    return (
        f"<b>📊 آمار شما</b>\n{LINE}\n\n"
        f"🏅 سطح: <b>{level_of(user['count'])}</b>\n"
        f"🔥 ترجمه‌ها: <b>{user['count']:,}</b>\n"
        f"🥇 رتبه: <b>{rank[0]:,}</b> از {rank[1]:,}\n"
        f"📅 عضویت: {since}\n\n"
        f"{nxt_line}\n\n"
        f"{LINE}\n"
        f"🌍 کل ربات: {gstats['translations']:,} ترجمه · {gstats['users']:,} کاربر"
    )


def history_text(items: list[dict]) -> str:
    out = f"<b>🕘 تاریخچه</b>\n{LINE}\n\n"
    if not items:
        return out + "هنوز ترجمه‌ای انجام ندادی. یه متن بفرست تا شروع کنیم ✨"
    for i, it in enumerate(items, 1):
        out += (
            f"<b>{i}.</b> {LANGUAGES.get(it['src'], LANGUAGES['auto']).flag} ➜ {LANGUAGES.get(it['dst'], LANGUAGES['auto']).flag}\n"
            f"<code>{esc(_short(it['original']))}</code>\n"
            f"{esc(_short(it['translated']))}\n\n"
        )
    return out.rstrip()


def languages_text() -> str:
    rows = [f"{l.flag} {l.name} <i>({esc(l.native)})</i>" for l in LANGUAGES.values() if l.code != "auto"]
    return f"<b>🌍 زبان‌های پشتیبانی‌شده ({len(rows)})</b>\n{LINE}\n\n" + "\n".join(rows)


def help_text() -> str:
    return (
        f"<b>📖 راهنما</b>\n{LINE}\n\n"
        "<b>ترجمه</b>\n"
        "فقط متن بفرست (یا یه عکس با کپشن). زبان مبدأ خودکار تشخیص داده می‌شه.\n\n"
        "<b>دستورها</b>\n"
        "/tr <code>[زبان] متن</code> — ترجمه‌ی یک‌باره، مثلاً <code>/tr de سلام</code>\n"
        "روی یک پیام ریپلای کن و <code>/tr</code> بزن تا همون پیام ترجمه بشه (در گروه هم کار می‌کنه)\n"
        "/lang — تنظیم زبان مبدأ و مقصد\n"
        "/history — آخرین ترجمه‌ها\n"
        "/stats — آمار و سطح شما\n"
        "/privacy — داده‌هایی که ذخیره می‌شه\n"
        "/deleteme — حذف کامل اطلاعات شما\n\n"
        "<b>زیر هر ترجمه</b>\n"
        "📋 کپی · 🔁 ترجمه‌ی معکوس · 🌍 ترجمه به زبان دیگه\n\n"
        f"<i>حداکثر طول متن: {4000:,} کاراکتر</i>"
    )


def about_text(engines: list[str], gstats: dict, uptime: float) -> str:
    return (
        f"<b>ℹ️ درباره‌ی BotAM</b>\n{LINE}\n\n"
        f"نسخه: <b>{__version__}</b>\n"
        f"موتورهای ترجمه: {' → '.join(esc(e) for e in engines)}\n"
        f"زبان‌ها: {len(TARGET_CODES)}\n"
        f"آپ‌تایم: {_fmt_uptime(uptime)}\n"
        f"کاربران: {gstats['users']:,} · ترجمه‌ها: {gstats['translations']:,}\n\n"
        f"سازنده: <a href=\"{DEV}\">Amin Moniry</a>  ·  <a href=\"{GITHUB}\">GitHub</a>"
    )


def privacy_text() -> str:
    return (
        f"<b>🔒 حریم خصوصی</b>\n{LINE}\n\n"
        "<b>چی ذخیره می‌شه:</b>\n"
        "• شناسه‌ی تلگرام، نام و نام‌کاربری\n"
        "• زبان‌های انتخابی و تعداد ترجمه‌ها\n"
        "• متن و ترجمه‌ی ۲۰ ترجمه‌ی آخر (برای تاریخچه)\n\n"
        "متن‌ها برای ترجمه به سرویس‌های ترجمه (Gemini / Google / …) فرستاده می‌شن؛ اطلاعات حساس نفرست.\n\n"
        "هر وقت خواستی با /history تاریخچه رو پاک کن، یا با /deleteme همه‌چیز رو برای همیشه حذف کن."
    )


def delete_confirm_text() -> str:
    return "<b>⚠️ حذف کامل اطلاعات</b>\n\nتمام تنظیمات، آمار و تاریخچه‌ی تو برای همیشه پاک می‌شه. مطمئنی؟"


def admin_text(gstats: dict, status: dict, uptime: float) -> str:
    eng = "\n".join(f"• {esc(n)}: {esc(s)}" for n, s in status.items())
    return (
        f"<b>🛠 پنل مدیر</b>\n{LINE}\n\n"
        f"کاربران: {gstats['users']:,} (فعال ۲۴ساعت: {gstats['active_24h']:,})\n"
        f"ترجمه‌ها: {gstats['translations']:,}\n"
        f"آپ‌تایم: {_fmt_uptime(uptime)}\n\n<b>موتورها</b>\n{eng}"
    )


ERR_ALL_FAILED = "😕 الان هیچ‌کدوم از سرویس‌های ترجمه جواب ندادن.\nچند ثانیه بعد دوباره امتحان کن."
ERR_TOO_LONG = "❌ متن خیلی بلنده. حداکثر <b>{max}</b> کاراکتر مجازه (متن تو {n:,} کاراکتر بود)."
ERR_RATE = "⏳ آروم‌تر! چند لحظه صبر کن و دوباره بفرست."
ERR_GENERIC = "❌ مشکلی پیش اومد. دوباره امتحان کن."
HINT_NO_TEXT = "📝 فعلاً فقط متن (یا کپشن عکس) رو ترجمه می‌کنم."


# ───────────────────────── translation result ─────────────────────────
def result_messages(res: Result, show_footer: bool = True) -> list[str]:
    header = f"{label(res.src)}  ➜  {label(res.dst)}"
    parts = chunk_text(res.text, 3300)
    msgs = []
    for i, part in enumerate(parts):
        tag = "<blockquote expandable>" if len(part) > 700 else "<blockquote>"
        msg = (f"<b>{header}</b>\n\n" if i == 0 else "") + f"{tag}{esc(part.strip())}</blockquote>"
        msgs.append(msg)
    if show_footer:
        note = "⚡ از کش" if res.cached else f"⚡ {res.elapsed:.1f}s"
        msgs[-1] += f"\n<i>{note} · {esc(res.engine_label)}</i>"
    return msgs


# ───────────────────────── keyboards ─────────────────────────
def main_menu() -> Markup:
    return Markup([
        [Btn("⚙️ تنظیمات زبان", callback_data="m:settings"), Btn("🕘 تاریخچه", callback_data="m:hist")],
        [Btn("📊 آمار من", callback_data="m:stats"), Btn("🌍 زبان‌ها", callback_data="m:langs")],
        [Btn("📖 راهنما", callback_data="m:help"), Btn("ℹ️ درباره", callback_data="m:about")],
    ])


def back_menu() -> Markup:
    return Markup([[Btn("🏠 منوی اصلی", callback_data="m:main")]])


def settings_menu() -> Markup:
    return Markup([
        [Btn("🔍 زبان مبدأ", callback_data="s:src"), Btn("🎯 زبان مقصد", callback_data="s:dst")],
        [Btn("🔄 جابه‌جایی مبدأ و مقصد", callback_data="swap")],
        [Btn("♻️ بازنشانی", callback_data="reset"), Btn("🏠 منو", callback_data="m:main")],
    ])


def language_grid(prefix: str, selected: str | None = None, include_auto: bool = False, back: str = "m:settings") -> Markup:
    codes = (["auto"] if include_auto else []) + TARGET_CODES
    buttons = []
    for c in codes:
        l = LANGUAGES[c]
        mark = "✅" if c == selected else l.flag
        buttons.append(Btn(f"{mark} {l.name}", callback_data=f"{prefix}:{c}"))
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([Btn("🔙 بازگشت", callback_data=back)])
    return Markup(rows)


def history_menu(has_items: bool) -> Markup:
    row = []
    if has_items:
        row.append(Btn("🗑 پاک کردن", callback_data="h:clear"))
    row.append(Btn("🏠 منو", callback_data="m:main"))
    return Markup([row])


def result_keyboard(hid: int, translated: str) -> Markup:
    row1 = []
    if 0 < len(translated) <= 256:
        row1.append(Btn("📋 کپی", copy_text=CopyTextButton(text=translated)))
    row1.append(Btn("🔁 معکوس", callback_data=f"rv:{hid}"))
    return Markup([row1, [Btn("🌍 زبان دیگه", callback_data=f"pk:{hid}"), Btn("🏠 منو", callback_data="m:main")]])


def delete_confirm_menu() -> Markup:
    return Markup([[Btn("🗑 بله، حذف کن", callback_data="del:yes"), Btn("انصراف", callback_data="m:main")]])
