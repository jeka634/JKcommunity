import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота и ID чата
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def load_settings():
    """Загрузка настроек из файла settings.txt"""
    settings = {}
    
    try:
        with open('settings.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Преобразуем значения в соответствующие типы
                    if key in ['BASE_PROBABILITY', 'BOOST_PROBABILITY']:
                        settings[key] = float(value)
                    elif key in ['POINTS_THRESHOLDS']:
                        settings[key] = [int(x.strip()) for x in value.split(',')]
                    elif key in ['TOP_USERS_LIMIT', 'MONTHLY_WINNERS_HISTORY_LIMIT']:
                        settings[key] = int(value)
                    else:
                        settings[key] = int(value)
                        
    except FileNotFoundError:
        print("⚠️ Файл settings.txt не найден, используются значения по умолчанию")
        # Значения по умолчанию
        settings = {
            'BASE_PROBABILITY': 0.20,
            'BOOST_PROBABILITY': 0.325,
            'BOOST_START_HOUR': 20,
            'BOOST_END_HOUR': 23,
            'POINTS_PER_MESSAGE': 10,
            'MIN_WORDS_FOR_POINTS': 5,
            'POINTS_THRESHOLDS': [200, 500, 1000, 2000, 5000],
            'DAILY_REPORT_HOUR': 22,
            'DAILY_REPORT_MINUTE': 0,
            'RESET_ACHIEVEMENTS_HOUR': 0,
            'RESET_ACHIEVEMENTS_MINUTE': 0,
            'MONTHLY_WINNER_CHECK_HOUR': 1,
            'MONTHLY_WINNER_CHECK_MINUTE': 0,
            'TOP_USERS_LIMIT': 10,
            'MONTHLY_WINNERS_HISTORY_LIMIT': 10
        }
    except Exception as e:
        print(f"❌ Ошибка чтения settings.txt: {e}")
        return None
    
    return settings

# Загружаем настройки
SETTINGS = load_settings()

if SETTINGS is None:
    print("❌ Не удалось загрузить настройки, используются значения по умолчанию")
    # Значения по умолчанию
    BASE_PROBABILITY = 0.20
    BOOST_PROBABILITY = 0.325
    BOOST_START_HOUR = 20
    BOOST_END_HOUR = 23
    POINTS_PER_MESSAGE = 10
    MIN_WORDS_FOR_POINTS = 5
    POINTS_THRESHOLDS = [200, 500, 1000, 2000, 5000]
    DAILY_REPORT_HOUR = 22
    DAILY_REPORT_MINUTE = 0
    RESET_ACHIEVEMENTS_HOUR = 0
    RESET_ACHIEVEMENTS_MINUTE = 0
    MONTHLY_WINNER_CHECK_HOUR = 1
    MONTHLY_WINNER_CHECK_MINUTE = 0
    TOP_USERS_LIMIT = 10
    MONTHLY_WINNERS_HISTORY_LIMIT = 10
else:
    # Присваиваем значения из файла настроек
    BASE_PROBABILITY = SETTINGS['BASE_PROBABILITY']
    BOOST_PROBABILITY = SETTINGS['BOOST_PROBABILITY']
    BOOST_START_HOUR = SETTINGS['BOOST_START_HOUR']
    BOOST_END_HOUR = SETTINGS['BOOST_END_HOUR']
    POINTS_PER_MESSAGE = SETTINGS['POINTS_PER_MESSAGE']
    MIN_WORDS_FOR_POINTS = SETTINGS['MIN_WORDS_FOR_POINTS']
    POINTS_THRESHOLDS = SETTINGS['POINTS_THRESHOLDS']
    DAILY_REPORT_HOUR = SETTINGS['DAILY_REPORT_HOUR']
    DAILY_REPORT_MINUTE = SETTINGS['DAILY_REPORT_MINUTE']
    RESET_ACHIEVEMENTS_HOUR = SETTINGS['RESET_ACHIEVEMENTS_HOUR']
    RESET_ACHIEVEMENTS_MINUTE = SETTINGS['RESET_ACHIEVEMENTS_MINUTE']
    MONTHLY_WINNER_CHECK_HOUR = SETTINGS['MONTHLY_WINNER_CHECK_HOUR']
    MONTHLY_WINNER_CHECK_MINUTE = SETTINGS['MONTHLY_WINNER_CHECK_MINUTE']
    TOP_USERS_LIMIT = SETTINGS['TOP_USERS_LIMIT']
    MONTHLY_WINNERS_HISTORY_LIMIT = SETTINGS['MONTHLY_WINNERS_HISTORY_LIMIT']

# Мотивационные сообщения для достижений
MOTIVATION_MESSAGES = {
    200: [
        "🎉 Отличное начало, {username}! Ты набрал 200 очков!",
        "🚀 {username} достиг 200 очков! Продолжай в том же духе!"
    ],
    500: [
        "🔥 {username} набрал 500 очков! Ты на верном пути!",
        "⭐ {username} - 500 очков! Отличная активность!"
    ],
    1000: [
        "💎 {username} достиг 1000 очков! Невероятная активность!",
        "👑 {username} - 1000 очков! Ты настоящий лидер!"
    ],
    2000: [
        "🌟 {username} набрал 2000 очков! Феноменальная работа!",
        "🏆 {username} - 2000 очков! Ты легенда чата!"
    ],
    5000: [
        "💫 {username} достиг 5000 очков! Абсолютный рекорд!",
        "🎊 {username} - 5000 очков! Ты непревзойденный чемпион!"
    ]
}

# Приветственное сообщение для команды /JK
JK_WELCOME_MESSAGE = {
    'ru': """
🤖 **Добро пожаловать в JK Community!**

**Jekardos Coin (JK)** — внутренняя валюта нашего чата.
Каждый получает JK пропорционально своему вкладу и активности.

**Команды бота:**
/start — приветствие
/help — справка
/stats — ваша статистика
/week — топ-10 за неделю
/month — топ-10 за месяц
/send username N — перевести N очков другому
/mute username N — замутить пользователя (100 очков = 30 мин)
/dice N — испытать удачу: поставить N очков, шанс удвоить

**JK Coin — это валюта, которую можно зарабатывать, переводить, тратить на mute и мини-игры!**

**Спасибо завсегдатаям и китам JK за вклад в развитие сообщества!** 🚀
    """,
    'en': """
🤖 **Welcome to JK Community!**

**Jekardos Coin (JK)** — our chat's internal currency.
Everyone receives JK proportional to their contribution and activity.

**Bot commands:**
/start — greeting
/help — help
/stats — your statistics
/week — top-10 for the week
/month — top-10 for the month
/send username N — transfer N points to another user
/mute username N — mute a user (100 points = 30 min)
/dice N — try your luck: bet N points, chance to double

**JK Coin is a currency you can earn, transfer, spend on mute and mini-games!**

**Thank you to regulars and JK whales for their great contribution to the community!** 🚀
    """
} 