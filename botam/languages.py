from __future__ import annotations

from typing import NamedTuple


class Lang(NamedTuple):
    code: str
    name: str      # Persian display name
    native: str
    flag: str
    english: str   # used in LLM prompts


_DATA = [
    Lang("fa", "فارسی", "فارسی", "🇮🇷", "Persian"),
    Lang("en", "انگلیسی", "English", "🇺🇸", "English"),
    Lang("ar", "عربی", "العربية", "🇸🇦", "Arabic"),
    Lang("az", "آذربایجانی", "Azərbaycanca", "🇦🇿", "Azerbaijani"),
    Lang("tr", "ترکی", "Türkçe", "🇹🇷", "Turkish"),
    Lang("ku", "کردی", "Kurdî", "🏳️", "Kurdish"),
    Lang("ru", "روسی", "Русский", "🇷🇺", "Russian"),
    Lang("uk", "اوکراینی", "Українська", "🇺🇦", "Ukrainian"),
    Lang("fr", "فرانسوی", "Français", "🇫🇷", "French"),
    Lang("de", "آلمانی", "Deutsch", "🇩🇪", "German"),
    Lang("es", "اسپانیایی", "Español", "🇪🇸", "Spanish"),
    Lang("it", "ایتالیایی", "Italiano", "🇮🇹", "Italian"),
    Lang("pt", "پرتغالی", "Português", "🇵🇹", "Portuguese"),
    Lang("nl", "هلندی", "Nederlands", "🇳🇱", "Dutch"),
    Lang("pl", "لهستانی", "Polski", "🇵🇱", "Polish"),
    Lang("sv", "سوئدی", "Svenska", "🇸🇪", "Swedish"),
    Lang("cs", "چکی", "Čeština", "🇨🇿", "Czech"),
    Lang("ro", "رومانیایی", "Română", "🇷🇴", "Romanian"),
    Lang("hu", "مجاری", "Magyar", "🇭🇺", "Hungarian"),
    Lang("el", "یونانی", "Ελληνικά", "🇬🇷", "Greek"),
    Lang("zh", "چینی", "中文", "🇨🇳", "Chinese (Simplified)"),
    Lang("ja", "ژاپنی", "日本語", "🇯🇵", "Japanese"),
    Lang("ko", "کره‌ای", "한국어", "🇰🇷", "Korean"),
    Lang("hi", "هندی", "हिन्दी", "🇮🇳", "Hindi"),
    Lang("ur", "اردو", "اردو", "🇵🇰", "Urdu"),
    Lang("id", "اندونزیایی", "Indonesia", "🇮🇩", "Indonesian"),
    Lang("vi", "ویتنامی", "Tiếng Việt", "🇻🇳", "Vietnamese"),
    Lang("th", "تایلندی", "ไทย", "🇹🇭", "Thai"),
]

AUTO = Lang("auto", "تشخیص خودکار", "Auto Detect", "🔍", "auto-detected language")
LANGUAGES: dict[str, Lang] = {"auto": AUTO, **{l.code: l for l in _DATA}}
TARGET_CODES = [c for c in LANGUAGES if c != "auto"]

_ALIASES = {"zh-cn": "zh", "zh-tw": "zh", "zh-hans": "zh", "zh-hant": "zh", "iw": "he", "jw": "jv"}


def normalize_code(code: str | None) -> str | None:
    if not code:
        return None
    code = code.strip().lower().replace("_", "-")
    code = _ALIASES.get(code, code)
    if code not in LANGUAGES and "-" in code:
        code = code.split("-")[0]
    return code


def get(code: str | None) -> Lang:
    code = normalize_code(code) or "auto"
    return LANGUAGES.get(code) or Lang(code, code, code, "🏳️", code)


def label(code: str | None) -> str:
    l = get(code)
    return f"{l.flag} {l.name}"


def google_code(code: str) -> str:
    return {"zh": "zh-CN"}.get(code, code)
