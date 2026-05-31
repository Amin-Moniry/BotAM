# 🤖 BotAM - Advanced Telegram Translator Bot

> **A powerful, multi-engine translation bot with smart language detection and professional UI**

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/translator7adc7aminbot)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

## 🌟 Features

### 🔥 Core Capabilities
- **Smart Language Detection** - Automatically identifies input language
- **Multi-Engine Translation** - 4 backup translation systems (Google, Bing, Yandex, Baidu)
- **Lightning Fast** - Translations completed in under 2 seconds
- **15+ Languages** - Comprehensive language support
- **User Statistics** - Detailed personal analytics and progress tracking
- **Translation History** - Keep track of your recent translations
- **Professional UI** - Clean, intuitive interface with Persian support

### 🛡️ Reliability Features
- **4-Layer Fallback System** - If one service fails, others take over
- **Error Handling** - Graceful error management with user-friendly messages
- **Data Persistence** - User preferences and history saved automatically
- **24/7 Uptime** - Continuous service availability

## 🚀 Quick Start

### Using the Bot
1. **Start the bot**: [@translator7adc7aminbot](https://t.me/translator7adc7aminbot)
2. **Click** `/start` to begin
3. **Select** "🌐 Translate" from the main menu
4. **Choose** your source and target languages
5. **Send** any text to get instant translation

### Supported Languages
```
🇺🇸 English    🇮🇷 Persian    🇸🇦 Arabic      🇫🇷 French
🇩🇪 German     🇪🇸 Spanish    🇮🇹 Italian     🇷🇺 Russian
🇯🇵 Japanese   🇰🇷 Korean     🇨🇳 Chinese     🇹🇷 Turkish
🇵🇹 Portuguese 🇮🇳 Hindi      🇳🇱 Dutch       🔍 Auto-detect
```

## 📊 Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and show main menu |
| `/help` | Display comprehensive help guide |
| `/stats` | Show your translation statistics |
| `/info` | Display bot information and system stats |

## 🏗️ Technical Architecture

### Translation Engine
```python
Multi-Layer Translation System:
├── Layer 1: Google Translate API
├── Layer 2: Bing Translator API  
├── Layer 3: Yandex Translate API
└── Layer 4: Baidu Translate API
```

### Key Components
- **SuperTranslator Class**: Manages multi-engine translation logic
- **Database System**: JSON-based user data persistence
- **Language Detection**: Pattern-based + API language identification
- **User Management**: Individual preferences and statistics tracking

## 🔧 Installation & Setup

### Prerequisites
```bash
Python 3.9+
pip install python-telegram-bot==13.15
pip install translators
pip install requests
```

### Environment Variables
```bash
export BOT_TOKEN="your_telegram_bot_token"
export ADMIN_ID="your_telegram_user_id"
```

### Running the Bot
```bash
# This code is for viewing only - cannot be copied or used
# For bot usage, visit: https://t.me/translator7adc7aminbot
```

## 📈 User Levels & Gamification

| Level | Translations Required | Badge |
|-------|----------------------|-------|
| 📘 Beginner | 0-49 | New User |
| ⭐ Advanced | 50-99 | Active User |
| 💎 Expert | 100-499 | Power User |
| 🏆 Professional | 500-999 | Expert |
| 👑 Translation Master | 1000+ | Master |

## 🎯 Usage Examples

### Basic Translation
```
User: Hello, how are you?
Bot: سلام، چطور هستید؟
```

### Auto Language Detection
```
User: Bonjour mon ami
Bot: 🔍 Detected: French → Persian
     سلام دوست من
```

### Settings Management
- **Change Source Language**: Select from 15+ options
- **Change Target Language**: Set preferred output language  
- **View History**: Last 10 translations saved
- **Reset Settings**: Return to default configuration

## 📊 Statistics & Analytics

The bot provides comprehensive user analytics:
- **Translation Count**: Total number of translations
- **User Level**: Progress-based ranking system
- **Success Rate**: Translation accuracy metrics
- **Language Usage**: Most frequently used language pairs
- **Daily Activity**: Translation patterns and usage

## 🛠️ Advanced Features

### Smart Language Detection
```python
def _pattern_detect_language(self, text):
    patterns = {
        'fa': r'[\u0600-\u06FF]',    # Persian/Arabic script
        'ar': r'[\u0621-\u064A]',    # Arabic specific
        'ru': r'[а-яё]',             # Cyrillic
        'zh': r'[\u4e00-\u9fff]',    # Chinese characters
        # ... more patterns
    }
```

### Fallback System
```python
translators_to_try = [
    ('Google', 'google'),
    ('Bing', 'bing'), 
    ('Yandex', 'yandex'),
    ('Baidu', 'baidu'),
]
```

## 🔐 Security & Privacy

- **No Data Mining**: Personal conversations are not stored
- **Secure API**: All translation requests are encrypted
- **Privacy First**: Only translation history (optional) is saved
- **GDPR Compliant**: User data can be deleted on request

## 🤝 Viewing Only

**⚠️ IMPORTANT NOTICE: This is proprietary software for viewing purposes only.**

This code is shared for **educational and demonstration purposes only**. The following restrictions apply:

### 🚫 Prohibited Actions
- **No Copying**: You may not copy any part of this code
- **No Modification**: You may not edit, modify, or adapt this code
- **No Distribution**: You may not redistribute or share this code
- **No Commercial Use**: You may not use this code for commercial purposes
- **No Derivative Works**: You may not create derivative works based on this code

### ✅ Permitted Actions
- **View Only**: You may view the code for learning purposes
- **Read Documentation**: You may read and study the implementation
- **Use the Bot**: You may use the official bot at [@translator7adc7aminbot](https://t.me/translator7adc7aminbot)

### 📞 Contact for Licensing
If you're interested in using this code for your project, please contact the developer for proper licensing arrangements.

## 📞 Support & Contact

- **Telegram Bot**: [@translator7adc7aminbot](https://t.me/translator7adc7aminbot)
- **Developer**: Amin Moniry (AminTivanix2)
- **Telegram**: [@amintivanix2](https://t.me/amintivanix2)
- **Email**: [amintivanix2@gmail.com](mailto:amintivanix2@gmail.com)
- **GitHub**: [Amin-Moniry](https://github.com/Amin-Moniry)
- **Website**: [allin1wrench.ir](https://allin1wrench.ir)
- **Issues**: Open a GitHub issue for bug reports
- **Feature Requests**: Submit via GitHub discussions

## 🔮 Roadmap

### Upcoming Features
- **Voice Translation**: Convert speech to text and translate
- **File Support**: Translate documents (PDF, DOCX, TXT)
- **Image Translation**: OCR + translation for images
- **Personal API**: Custom API access for developers
- **Bulk Translation**: Process multiple texts simultaneously
- **Translation Quality Scoring**: Rate translation accuracy

### Version History
- **v6.0** - Multi-engine system with 4 fallback APIs
- **v5.0** - Advanced UI with gamification
- **v4.0** - User statistics and history tracking
- **v3.0** - Language detection improvements
- **v2.0** - Multi-language support expansion
- **v1.0** - Initial release

## 📄 License

**© 2026 Amin Moniry (AminTivanix2) - All Rights Reserved**

This software is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited without the express written permission of the copyright holder.

### License Terms:
- **Proprietary Software**: This code is the exclusive property of Amin Moniry (AminTivanix2)
- **View Only**: Code is shared for educational viewing purposes only
- **No Reproduction**: Copying, modifying, or using this code is prohibited
- **Legal Protection**: Violations may result in legal action

For licensing inquiries, please contact the developer directly.

## 🙏 Acknowledgments

- **Telegram Bot API** for the excellent bot framework
- **Translators Library** for multi-engine translation support
- **Python Community** for the amazing ecosystem
- **Beta Testers** who helped improve the bot

---

<div align="center">

**Built with ❤️ by Amin Moniry (AminTivanix2)**

*Making language barriers disappear, one translation at a time*

[![Try Bot Now](https://img.shields.io/badge/Try%20Bot%20Now-@translator7adc7aminbot-blue?style=for-the-badge&logo=telegram)](https://t.me/translator7adc7aminbot)

</div>
