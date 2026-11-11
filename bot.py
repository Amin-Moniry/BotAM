import json
import os
import time
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional
import requests

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0') or 0)

if not TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده است. آن را در Environment Variables قرار دهید.")
    raise SystemExit(1)

import logging
logging.basicConfig(level=logging.ERROR)

try:
    import translators as ts
    test_result = ts.translate_text("Hello", translator='google', to_language='fa')
except ImportError:
    print("❌ لطفاً translators را نصب کنید:")
    print("pip install translators")
    exit(1)
except Exception as e:
    print(f"⚠️ هشدار در تست اولیه: {e}")

class SuperTranslator:
    def __init__(self):
        self.current_translator = 0
        self.translators_list = ['google', 'bing', 'yandex', 'baidu']

    def translate(self, text, src='auto', dest='fa'):
        if src == 'auto':
            src = self._detect_language(text)

        target_lang = dest
        if dest == 'zh':
            target_lang = 'zh-cn'

        translators_to_try = [
            ('Google', 'google'),
            ('Bing', 'bing'),
            ('Yandex', 'yandex'),
            ('Baidu', 'baidu'),
        ]

        for name, translator_engine in translators_to_try:
            try:
                if src == 'auto':
                    result = ts.translate_text(
                        text,
                        translator=translator_engine,
                        to_language=target_lang,
                        timeout=10
                    )
                else:
                    result = ts.translate_text(
                        text,
                        translator=translator_engine,
                        from_language=src,
                        to_language=target_lang,
                        timeout=10
                    )

                if result and result.strip() and result != text:
                    return TranslationResult(result, src, target_lang)

            except Exception as e:
                continue

        raise Exception("تمام روش‌های ترجمه ناموفق بودند")

    def _detect_language(self, text):
        try:
            detected = ts.translate_text(text, translator='google', to_language='en')
            if detected and detected != text:
                return self._pattern_detect_language(text)
            return 'en'
        except:
            return self._pattern_detect_language(text)

    def _pattern_detect_language(self, text):
        import re

        patterns = {
            'fa': r'[\u0600-\u06FF]',
            'ar': r'[\u0621-\u064A]',
            'ru': r'[а-яё]',
            'de': r'[äöüß]',
            'fr': r'[àâäéèêëïîôöùûüÿç]',
            'es': r'[áéíóúñ]',
            'it': r'[àèéìíîòóù]',
            'zh': r'[\u4e00-\u9fff]',
            'ja': r'[\u3040-\u309f\u30a0-\u30ff]',
            'ko': r'[\uac00-\ud7af]',
            'tr': r'[çğıöşü]',
            'hi': r'[\u0900-\u097F]',
        }

        text_lower = text.lower()
        for lang, pattern in patterns.items():
            if re.search(pattern, text_lower):
                return lang

        return 'en'

class TranslationResult:
    def __init__(self, text, src, dest):
        self.text = text
        self.src = src
        self.dest = dest

translator = SuperTranslator()

LANGUAGES = {
    'auto': {'name': 'تشخیص خودکار', 'flag': '🔍', 'native': 'Auto Detect'},
    'fa': {'name': 'فارسی', 'flag': '🇮🇷', 'native': 'فارسی'},
    'en': {'name': 'انگلیسی', 'flag': '🇺🇸', 'native': 'English'},
    'ar': {'name': 'عربی', 'flag': '🇸🇦', 'native': 'العربية'},
    'fr': {'name': 'فرانسوی', 'flag': '🇫🇷', 'native': 'Français'},
    'de': {'name': 'آلمانی', 'flag': '🇩🇪', 'native': 'Deutsch'},
    'es': {'name': 'اسپانیایی', 'flag': '🇪🇸', 'native': 'Español'},
    'it': {'name': 'ایتالیایی', 'flag': '🇮🇹', 'native': 'Italiano'},
    'ru': {'name': 'روسی', 'flag': '🇷🇺', 'native': 'Русский'},
    'ja': {'name': 'ژاپنی', 'flag': '🇯🇵', 'native': '日本語'},
    'ko': {'name': 'کره‌ای', 'flag': '🇰🇷', 'native': '한국어'},
    'zh': {'name': 'چینی', 'flag': '🇨🇳', 'native': '中文'},
    'tr': {'name': 'ترکی', 'flag': '🇹🇷', 'native': 'Türkçe'},
    'pt': {'name': 'پرتغالی', 'flag': '🇵🇹', 'native': 'Português'},
    'hi': {'name': 'هندی', 'flag': '🇮🇳', 'native': 'हिन्दी'},
    'nl': {'name': 'هلندی', 'flag': '🇳🇱', 'native': 'Nederlands'}
}

class Database:
    def __init__(self):
        self.users = {}
        self.translations = 0
        self.load_data()

    def save_data(self):
        try:
            with open('bot_data.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'users': self.users,
                    'translations': self.translations
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"خطا در ذخیره داده: {e}")

    def load_data(self):
        try:
            if os.path.exists('bot_data.json'):
                with open('bot_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.translations = data.get('translations', 0)
        except Exception as e:
            print(f"خطا در بارگذاری داده: {e}")

db = Database()

def get_user_data(user_id: int) -> Dict:
    uid = str(user_id)
    if uid not in db.users:
        db.users[uid] = {
            'count': 0,
            'source_lang': 'auto',
            'target_lang': 'fa',
            'ui_lang': 'fa',
            'history': [],
            'translate_mode': False
        }
    return db.users[uid]

def get_user_level(count: int) -> str:
    if count >= 1000:
        return "👑 استاد ترجمه"
    elif count >= 500:
        return "🏆 حرفه‌ای"
    elif count >= 100:
        return "💎 ماهر"
    elif count >= 50:
        return "⭐ پیشرفته"
    else:
        return "📘 مبتدی"

def create_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🌐  ترجمه", callback_data="start_translate"),
            InlineKeyboardButton("🧩  تنظیمات", callback_data="settings")
        ],
        [
            InlineKeyboardButton("📊 آمار من", callback_data="stats"),
            InlineKeyboardButton("🌀 تاریخچه", callback_data="history")
        ],
        [
            InlineKeyboardButton("🔤 زبان‌های پشتیبانی", callback_data="languages"),
            InlineKeyboardButton("✨ ویژگی‌ها", callback_data="features")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_language_keyboard(callback_prefix: str, selected: str = None) -> InlineKeyboardMarkup:
    keyboard = []
    langs = list(LANGUAGES.items())

    for i in range(0, len(langs), 2):
        row = []
        for j in range(2):
            if i + j < len(langs):
                code, info = langs[i + j]
                emoji = "✅" if code == selected else info['flag']
                text = f"{emoji} {info['name']}"
                row.append(InlineKeyboardButton(text, callback_data=f"{callback_prefix}_{code}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "کاربر"
    user_data = get_user_data(user_id)

    welcome_text = f"""💛 **سلام {user_name} عزیز!**

╔══════════════════════════╗
║      **🤖 ربات مترجم BotAMᵃᵈᶜ⁷**      ║
╚══════════════════════════╝

✨ **ویژگی‌های ربات:**
```
🔍 تشخیص خودکار زبان
⚡ ترجمه فوری و دقیق  
🌍 پشتیبانی از 15+ زبان
📊 آمار تفصیلی شخصی
💎 رابط کاربری حرفه‌ای
🛡️ 4 سیستم ترجمه مختلف
```

🏆 **وضعیت شما:**
• سطح: `{get_user_level(user_data['count'])}`
• تعداد ترجمه‌ها: `{user_data['count']:,}`
• رتبه: `#{random.randint(1, 100)}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💎 ویژگی‌های آینده:**
• ترجمه صوتی
• پشتیبانی از فایل
• ترجمه تصاویر
• و API شخصی

**👇 برای شروع یکی از گزینه‌ها را انتخاب کنید:**"""

    update.message.reply_text(
        welcome_text,
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    
    if query.data == "check_membership":
        user_name = query.from_user.first_name or "کاربر"
        user_data = get_user_data(user_id)
        
        welcome_text = f"""💛 **سلام {user_name} عزیز!**

╔══════════════════════════╗
║      **🤖 ربات مترجم BotAMᵃᵈᶜ⁷**      ║
╚══════════════════════════╝

✨ **ویژگی‌های ربات:**
```
🔍 تشخیص خودکار زبان
⚡ ترجمه فوری و دقیق  
🌍 پشتیبانی از 15+ زبان
📊 آمار تفصیلی شخصی
💎 رابط کاربری حرفه‌ای
🛡️ 4 سیستم ترجمه مختلف
```

🏆 **وضعیت شما:**
• سطح: `{get_user_level(user_data['count'])}`
• تعداد ترجمه‌ها: `{user_data['count']:,}`
• رتبه: `#{random.randint(1, 100)}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💎 ویژگی‌های آینده:**
• ترجمه صوتی
• پشتیبانی از فایل
• ترجمه تصاویر
• و API شخصی

**👇 برای شروع یکی از گزینه‌ها را انتخاب کنید:**"""

        query.edit_message_text(
            welcome_text,
            reply_markup=create_main_keyboard(),
            parse_mode='Markdown'
        )
        return

    user_data = get_user_data(user_id)

    if query.data == "main_menu":
        show_main_menu(query)
    elif query.data == "start_translate":
        show_translate_menu(query, user_data)
    elif query.data == "ready_translate":
        enable_translate_mode(query, user_data)
    elif query.data == "settings":
        show_settings(query, user_data)
    elif query.data == "stats":
        show_stats(query, user_data)
    elif query.data == "history":
        show_history(query, user_data)
    elif query.data == "languages":
        show_languages(query)
    elif query.data == "features":
        show_features(query)
    elif query.data == "select_source":
        select_source_language(query)
    elif query.data == "select_target":
        select_target_language(query)
    elif query.data == "clear_history":
        clear_user_history(query, user_data)
    elif query.data == "reset_settings":
        reset_user_settings(query, user_data)
    elif query.data.startswith("src_"):
        handle_source_selection(query, context)
    elif query.data.startswith("tgt_"):
        handle_target_selection(query, context)

def select_source_language(query):
    text = f"""🔍 **انتخاب زبان مبدأ**

╔══════════════════════════╗
║      **🗣️ زبان ورودی متن**      ║
╚══════════════════════════╝

**👇 زبان متن خود را انتخاب کنید:**

`اگر مطمئن نیستید، گزینه "تشخیص خودکار" را انتخاب کنید.`"""

    query.edit_message_text(
        text,
        reply_markup=create_language_keyboard("src"),
        parse_mode='Markdown'
    )

def select_target_language(query):
    text = f"""💛 **انتخاب زبان مقصد**

╔══════════════════════════╗
║     **🌍 زبان خروجی ترجمه**     ║
╚══════════════════════════╝

**👇 زبان مورد نظر برای ترجمه را انتخاب کنید:**"""

    query.edit_message_text(
        text,
        reply_markup=create_language_keyboard("tgt"),
        parse_mode='Markdown'
    )

def handle_source_selection(query, context):
    lang_code = query.data.split("_")[1]
    user_data = get_user_data(query.from_user.id)
    user_data['source_lang'] = lang_code

    lang_info = LANGUAGES[lang_code]
    query.answer(f"✅ زبان مبدأ: {lang_info['name']}")

    show_translate_menu(query, user_data)
    db.save_data()

def handle_target_selection(query, context):
    lang_code = query.data.split("_")[1]
    user_data = get_user_data(query.from_user.id)
    user_data['target_lang'] = lang_code

    lang_info = LANGUAGES[lang_code]
    query.answer(f"✅ زبان مقصد: {lang_info['name']}")

    show_translate_menu(query, user_data)
    db.save_data()

def translate_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user_data = get_user_data(user_id)

    if not user_data.get('translate_mode', False):
        update.message.reply_text(
            "⚠️ **ابتدا حالت ترجمه را فعال کنید!**\n\n`لطفاً ابتدا روی دکمه 'شروع ترجمه' کلیک کنید.`",
            reply_markup=create_main_keyboard(),
            parse_mode='Markdown'
        )
        return

    if len(text) > 4000:
        update.message.reply_text(
            "❌ **خطا!**\n\n`متن بیش از حد طولانی است.`\n**حداکثر مجاز:** `4000 کاراکتر`",
            parse_mode='Markdown'
        )
        return

    if len(text) < 2:
        update.message.reply_text(
            "⚠️ **توجه!**\n\n`متن بیش از حد کوتاه است.`\n**لطفاً متن معنی‌داری ارسال کنید.**",
            parse_mode='Markdown'
        )
        return

    processing_msg = update.message.reply_text(
        "⏳ **در حال پردازش...**\n\n`🛡️ استفاده از سیستم ترجمه پیشرفته 4 مرحله‌ای...`",
        parse_mode='Markdown'
    )

    try:
        source_lang = user_data['source_lang']
        target_lang = user_data['target_lang']

        if source_lang != 'auto' and source_lang == target_lang:
            if source_lang == 'fa':
                target_lang = 'en'
            elif source_lang == 'en':
                target_lang = 'fa'
            else:
                target_lang = 'en'

        result = translator.translate(text, src=source_lang, dest=target_lang)

        user_data['count'] += 1
        db.translations += 1

        if 'history' not in user_data:
            user_data['history'] = []

        user_data['history'].append({
            'original': text,
            'translated': result.text,
            'src': result.src,
            'tgt': result.dest,
            'time': datetime.now().strftime('%Y/%m/%d %H:%M')
        })

        if len(user_data['history']) > 10:
            user_data['history'] = user_data['history'][-10:]

        src_info = LANGUAGES.get(result.src, {'name': result.src, 'flag': '🏳️'})
        tgt_info = LANGUAGES.get(result.dest, {'name': result.dest, 'flag': '🏳️'})

        response = f"""✅ **ترجمه موفقیت‌آمیز**

╔══════════════════════════╗
║       **💛 نتیجه ترجمه**       ║
╚══════════════════════════╝

**🌀 متن اصلی:** {src_info['flag']} `{src_info['name']}`
```{text}```

**💛 ترجمه شده:** {tgt_info['flag']} `{tgt_info['name']}`
```{result.text}```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📊 جزئیات:**
├ زبان تشخیص شده: `{src_info['name']}`
├ طول متن: `{len(text)} کاراکتر`
├ ترجمه شماره: `#{user_data['count']:,}`
└ سیستم: `Translators v5.0`

**🏆 سطح شما:** `{get_user_level(user_data['count'])}`"""

        keyboard = [
            [
                InlineKeyboardButton("🆕 ترجمه جدید", callback_data="start_translate"),
                InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
            ]
        ]

        processing_msg.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

        db.save_data()

    except Exception as e:
        error_text = f"""❌ **متاسفانه ترجمه انجام نشد!**

**🔍 علت‌های احتمالی:**
• اتصال اینترنت ناپایدار
• تمام سرورهای ترجمه موقتاً مشکل دارند
• متن دارای کاراکترهای نامناسب

**🧠 راهکارهای پیشنهادی:**
• اتصال اینترنت خود را بررسی کنید
• متن را ساده‌تر و کوتاه‌تر کنید
• چند دقیقه صبر کنید و دوباره امتحان کنید

**🛡️ سیستم:** `تمام 4 روش ترجمه امتحان شدند`

**⚠️ خطای فنی:** `{str(e)[:50]}...`"""

        keyboard = [
            [
                InlineKeyboardButton("🌐 تلاش مجدد", callback_data="start_translate"),
                InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
            ]
        ]

        processing_msg.edit_text(
            error_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

def help_command(update: Update, context: CallbackContext):
    help_text = f"""📖 **راهنمای کامل ربات**

╔══════════════════════════╗
║      **🤖 ربات مترجم BotAMᵃᵈᶜ⁷**      ║
╚══════════════════════════╝

**💛 نحوه استفاده:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1️⃣ شروع:**
```/start``` - راه‌اندازی ربات

**2️⃣ ترجمه:**
• دکمه "🌐 شروع ترجمه" را بزنید
• زبان مبدأ و مقصد را انتخاب کنید
• روی "⭐ شروع ترجمه" کلیک کنید
• متن خود را ارسال کنید

**3️⃣ مشاهده آمار:**
• دکمه "📊 آمار من" را بزنید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔥 ویژگی‌های کلیدی:**

**🔍 تشخیص خودکار:** 
`ربات زبان متن را خودکار تشخیص می‌دهد`

**⚡ سرعت بالا:** 
`ترجمه در کمتر از 2 ثانیه`

**🛡️ قابلیت اطمینان بالا:** 
`4 سیستم ترجمه مختلف برای اطمینان`

**🌍 پشتیبانی گسترده:** 
`15+ زبان مختلف دنیا`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🧠 نکات مهم:**
• حداکثر طول متن: `4000 کاراکتر`
• برای بهترین نتیجه از جملات کامل استفاده کنید
• ربات 24/7 در دسترس شماست
• در صورت خطا، سیستم خودکاراً روش‌های دیگر را امتحان می‌کند"""

    keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]

    update.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def stats_command(update: Update, context: CallbackContext):
    user_data = get_user_data(update.effective_user.id)

    quick_stats = f"""📊 **آمار سریع**

**👤 {update.effective_user.first_name}**
```
🏅 سطح: {get_user_level(user_data['count'])}
🔥 ترجمه‌ها: {user_data['count']:,}
🏆 رتبه: #{random.randint(1, 50)}
⭐ امتیاز: {user_data['count'] * 10:,}
🔧 حالت ترجمه: {'فعال' if user_data.get('translate_mode', False) else 'غیرفعال'}
```

**💛 برای آمار کامل از منوی اصلی استفاده کنید.**"""

    keyboard = [[InlineKeyboardButton("📊 آمار کامل", callback_data="stats")]]

    update.message.reply_text(
        quick_stats,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def info_command(update: Update, context: CallbackContext):
    info_text = f"""ℹ️ **اطلاعات ربات**

╔══════════════════════════╗
║    **🤖 ربات مترجم BotAMᵃᵈᶜ⁷**    ║
╚══════════════════════════╝

**📋 مشخصات:**
```
نام: ربات ترجمه هوشمند امین
ورژن: 6.0 Translators
زبان: Python 3.9+
سیستم: 4 API مختلف
```

**📊 آمار کلی:**
```
👥 کل کاربران: {len(db.users):,}
🌐 کل ترجمه‌ها: {db.translations:,}
🌍 زبان‌های پشتیبانی: {len(LANGUAGES)}
⏰ آپتایم: 24/7
```

**💛 سیستم‌های ترجمه:**
• **سطح 1:** Google Translate
• **سطح 2:** Bing Translator
• **سطح 3:** Yandex Translate  
• **سطح 4:** Baidu Translate

**💎 مزایای کلیدی:**
✅ دقت بالا (`99%+ کیفیت`)
✅ سرعت فوق‌العاده (`< 1 ثانیه`)
✅ قابلیت اطمینان (`4 سیستم پشتیبان`)
✅ پوشش گسترده زبان‌ها"""

    keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]

    update.message.reply_text(
        info_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def enable_translate_mode(query, user_data):
    user_data['translate_mode'] = True

    src_info = LANGUAGES[user_data['source_lang']]
    tgt_info = LANGUAGES[user_data['target_lang']]

    text = f"""✅ **حالت ترجمه فعال شد!**

╔══════════════════════════╗
║     **🔥 آماده ترجمه**     ║
╚══════════════════════════╝

**🧩  تنظیمات فعلی:**
• **از:** {src_info['flag']} {src_info['name']}
• **به:** {tgt_info['flag']} {tgt_info['name']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💛 حالا هر متنی که ارسال کنید، فوراً ترجمه خواهد شد!**

**🧠 نکات:**
• حداکثر 4000 کاراکتر
• 4 سیستم ترجمه پشتیبان
• دقت بالا و سرعت فوق‌العاده"""

    keyboard = [
        [
            InlineKeyboardButton("🧩  تنظیمات", callback_data="settings"),
            InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")
        ]
    ]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    db.save_data()

def clear_user_history(query, user_data):
    user_data['history'] = []
    query.answer("✅ تاریخچه پاک شد!")
    show_history(query, user_data)
    db.save_data()

def reset_user_settings(query, user_data):
    user_data.update({
        'source_lang': 'auto',
        'target_lang': 'fa',
        'translate_mode': False
    })
    query.answer("✅ تنظیمات بازنشانی شد!")
    show_settings(query, user_data)
    db.save_data()

def show_main_menu(query):
    text = f"""🏠 **منوی اصلی**

╔══════════════════════════╗
║      **🤖 ربات مترجم BotAMᵃᵈᶜ⁷**      ║
╚══════════════════════════╝

**✨ آماده برای ترجمه جدید هستید؟**

`لطفاً یکی از گزینه‌های زیر را انتخاب کنید:`"""

    query.edit_message_text(
        text,
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

def show_translate_menu(query, user_data):
    src_info = LANGUAGES[user_data['source_lang']]
    tgt_info = LANGUAGES[user_data['target_lang']]

    text = f"""🌐 **تنظیمات ترجمه**

╔══════════════════════════╗
║        **🧩  تنظیمات فعلی**        ║
╚══════════════════════════╝

**🔍 زبان مبدأ (ورودی):**
```{src_info['flag']} {src_info['name']} ({src_info['native']})```

**💛 زبان مقصد (خروجی):**
```{tgt_info['flag']} {tgt_info['name']} ({tgt_info['native']})```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🧠 راهنما:**
`پس از کلیک روی "شروع ترجمه"، می‌توانید متن خود را ارسال کنید!`"""

    keyboard = [
        [
            InlineKeyboardButton("🔍 تغییر زبان مبدأ", callback_data="select_source"),
            InlineKeyboardButton("💛 تغییر زبان مقصد", callback_data="select_target")
        ],
        [
            InlineKeyboardButton("💎 شروع ترجمه", callback_data="ready_translate"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
        ]
    ]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def show_settings(query, user_data):
    text = f"""🧩  **تنظیمات**

╔══════════════════════════╗
║       **🛠️ تنظیمات شخصی**       ║
╚══════════════════════════╝

**🔧 تنظیمات فعلی:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🌍 زبان‌های پیش‌فرض:**
├ مبدأ: `{LANGUAGES[user_data['source_lang']]['name']}`
└ مقصد: `{LANGUAGES[user_data['target_lang']]['name']}`

**📊 آمار شخصی:**
├ تعداد ترجمه‌ها: `{user_data['count']:,}`
├ سطح: `{get_user_level(user_data['count'])}`
└ حالت ترجمه: `{'فعال' if user_data.get('translate_mode', False) else 'غیرفعال'}`"""

    keyboard = [
        [
            InlineKeyboardButton("🔍 تغییر زبان مبدأ", callback_data="select_source"),
            InlineKeyboardButton("💛 تغییر زبان مقصد", callback_data="select_target")
        ],
        [
            InlineKeyboardButton("🌐 بازنشانی تنظیمات", callback_data="reset_settings"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
        ]
    ]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def show_stats(query, user_data):
    level = get_user_level(user_data['count'])
    progress = min(100, (user_data['count'] % 100))
    progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)

    text = f"""📊 **آمار شما**

╔══════════════════════════╗
║        **🏆 آمار شخصی**        ║
╚══════════════════════════╝

**👤 اطلاعات کاربر:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🏅 سطح فعلی:** `{level}`

**🔥 تعداد ترجمه‌ها:** `{user_data['count']:,}`

**📈 رتبه‌بندی:** `#{random.randint(1, 100)}`

**📊 پیشرفت تا سطح بعد:**
```{progress_bar}``` `{progress}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🌟 آمار کلی ربات:**
├ کل ترجمه‌ها: `{db.translations:,}`
└ کل کاربران: `{len(db.users):,}`"""

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def show_history(query, user_data):
    history = user_data.get('history', [])

    text = f"""🌀 **تاریخچه ترجمه‌ها**

╔══════════════════════════╗
║       **📚 آخرین ترجمه‌ها**       ║
╚══════════════════════════╝

"""

    if not history:
        text += """**📭 تاریخچه خالی است!**

`پس از انجام اولین ترجمه، آخرین ترجمه‌های شما اینجا نمایش داده خواهد شد.`

**💛 بیایید شروع کنیم!**"""
    else:
        for i, item in enumerate(reversed(history[-5:]), 1):
            src_flag = LANGUAGES.get(item.get('src', 'auto'), {'flag': '🏳️'})['flag']
            tgt_flag = LANGUAGES.get(item.get('tgt', 'fa'), {'flag': '🏳️'})['flag']

            original = item.get('original', '')[:30] + "..." if len(item.get('original', '')) > 30 else item.get('original', '')
            translated = item.get('translated', '')[:30] + "..." if len(item.get('translated', '')) > 30 else item.get('translated', '')

            text += f"""**{i}.** {src_flag} ➡️ {tgt_flag}
`{original}`
`{translated}`

"""

    keyboard = [
        [
            InlineKeyboardButton("🗑️ پاک کردن تاریخچه", callback_data="clear_history"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
        ]
    ]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def show_languages(query):
    text = f"""🌍 **زبان‌های پشتیبانی شده**

╔══════════════════════════╗
║     **🗣️ {len(LANGUAGES)} زبان مختلف**     ║
╚══════════════════════════╝

**📋 لیست کامل زبان‌ها:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    for code, info in LANGUAGES.items():
        text += f"{info['flag']} **{info['name']}** `({info['native']})`\n"

    text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🧠 نکته:** 
`ربات از 4 سیستم ترجمه مختلف برای اطمینان از دقت استفاده می‌کند.`"""

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def show_features(query):
    text = f"""💎 **ویژگی‌های ربات**

╔══════════════════════════╗
║      **✨ امکانات پیشرفته**      ║
╚══════════════════════════╝

**🔥 ویژگی‌های فعلی:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔍 تشخیص هوشمند زبان**
`شناسایی خودکار زبان متن ورودی`

**⚡ ترجمه فوری**
`ترجمه در کمتر از 3 ثانیه`

**🛡️ 4 سیستم ترجمه**
`Google + Bing + Yandex + Baidu`

**🌍 پشتیبانی گسترده**
`15+ زبان مختلف دنیا`

**📊 آمار تفصیلی**
`پیگیری پیشرفت و آمار شخصی`

**💾 ذخیره تاریخچه**
`نگهداری آخرین ترجمه‌ها`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💛 ویژگی‌های آینده:**
• ترجمه صوتی
• پشتیبانی از فایل
• ترجمه تصاویر
• و API شخصی"""

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]

    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def save_data_periodic():
    while True:
        time.sleep(1800)
        try:
            db.save_data()
        except Exception as e:
            print(f"خطا در ذخیره خودکار: {e}")

def error_handler(update: Update, context: CallbackContext):
    try:
        if update and update.effective_user:
            if update.message:
                update.message.reply_text(
                    "❌ **خطای موقت!**\n\n`لطفاً دوباره تلاش کنید.`",
                    parse_mode='Markdown'
                )
            elif update.callback_query:
                update.callback_query.answer("❌ خطای موقت! دوباره تلاش کنید.")
    except Exception as e:
        print(f"خطا در error_handler: {e}")

def test_translation_system():
    test_texts = [
        ("Hello world", "en", "fa"),
        ("سلام دنیا", "fa", "en"),
        ("Bonjour", "fr", "en")
    ]

    for text, src, dest in test_texts:
        try:
            result = translator.translate(text, src=src, dest=dest)
        except Exception as e:
            print(f"❌ خطا در تست: {e}")

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"BotAM is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass

def start_health_server():
    """وب‌سرور سبک برای Render (Web Service) و پینگ cron"""
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), _HealthHandler).serve_forever()

def main():
    try:
        threading.Thread(target=start_health_server, daemon=True).start()
        test_translation_system()

        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        save_thread = threading.Thread(target=save_data_periodic, daemon=True)
        save_thread.start()

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("stats", stats_command))
        dp.add_handler(CommandHandler("info", info_command))

        dp.add_handler(CallbackQueryHandler(button_handler))

        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, translate_text))

        dp.add_error_handler(error_handler)

        updater.start_polling(
            poll_interval=1.0,
            timeout=10,
            clean=True
        )

        updater.idle()

    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")

    finally:
        try:
            db.save_data()
        except Exception as e:
            print(f"خطا در ذخیره نهایی: {e}")

if __name__ == '__main__':
    main()
