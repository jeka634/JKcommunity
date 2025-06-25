import logging
import random
import re
import datetime
import pytz
import time
import sqlite3
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue
)
from database import Database
from config import *

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь для отслеживания достижений пользователей за день
daily_achievements = {}
# Словарь для отслеживания, был ли порог достигнут сегодня (только 1 раз в день на весь чат)
daily_threshold_achieved = {}  # {threshold: True}
# Словарь для отслеживания временного буста пользователя: {user_id: timestamp_end}
user_boosts = {}  # {user_id: timestamp_end}

class ChatBot:
    def __init__(self, application):
        self.db = Database()
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        self.application = application
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await update.message.reply_text(
            "Привет! Я бот-администратор чата. Я начисляю очки за активность и веду статистику!\n\n"
            "Доступные команды:\n"
            "/stats - твоя статистика\n"
            "/week - топ-10 за неделю\n"
            "/month - топ-10 за месяц\n"
            "/help - справка\n"
            "/JK - приветствие JK Community"
        )
    
    async def jk_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /JK"""
        # Определяем язык пользователя (по умолчанию русский)
        user_language = 'ru'
        
        # Если есть аргументы команды, проверяем язык
        if context.args:
            lang_arg = context.args[0].lower()
            if lang_arg in ['en', 'english']:
                user_language = 'en'
        
        # Отправляем приветственное сообщение на соответствующем языке
        welcome_message = JK_WELCOME_MESSAGE.get(user_language, JK_WELCOME_MESSAGE['ru'])
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = f"""
🤖 *Бот-администратор чата*

*Как работают очки:*
• За каждое осмысленное сообщение (минимум {MIN_WORDS_FOR_POINTS} слов) есть шанс получить +{POINTS_PER_MESSAGE} очков
• Базовая вероятность: {BASE_PROBABILITY*100:.0f}%
• С {BOOST_START_HOUR}:00 до {BOOST_END_HOUR}:00 по МСК: {BOOST_PROBABILITY*100:.0f}% (буст активности!)

*Доступные команды:*
/stats - твоя статистика
/week - топ-{TOP_USERS_LIMIT} за неделю  
/month - топ-{TOP_USERS_LIMIT} за месяц
/help - эта справка
/JK - приветствие JK Community

*Особенности:*
• Ежедневно в {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d} публикуется топ активных пользователей
• При достижении {', '.join(map(str, POINTS_THRESHOLDS))} очков за день - специальные уведомления
• Ежемесячный топ сбрасывается, но сохраняется история победителей

*Общайся активно и зарабатывай очки!* 🎯
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        user_id = update.effective_user.id
        stats = self.db.get_user_stats(user_id)
        
        if not stats:
            await update.message.reply_text("Ты еще не заработал очков. Начни общаться в чате!")
            return
        
        stats_text = f"""
📊 *Статистика пользователя @{stats['username']}*

🏆 *Общие очки:* {stats['total_points']}
📅 *За сегодня:* {stats['today_points']}
📈 *За неделю:* {stats['week_points']}
📊 *За месяц:* {stats['month_points']}

📅 *Дата регистрации:* {stats['created_at'][:10]}
        """
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    def escape_markdown(self, text: str) -> str:
        # Экранирует спецсимволы для MarkdownV2
        for ch in ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'):
            text = text.replace(ch, f'\\{ch}')
        return text
    
    async def week_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            top_users = self.db.get_weekly_top(TOP_USERS_LIMIT)
            if not top_users:
                await update.message.reply_text("Пока нет данных за эту неделю. Будь первым!")
                return
            text = f"🏆 Топ-{TOP_USERS_LIMIT} за неделю:\n\n"
            for i, (username, points) in enumerate(top_users, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                safe_username = self.escape_markdown(username or f'user_{i}')
                text += f"{emoji} {i}. @{safe_username} - {points} очков\n"
            await update.message.reply_text(text)  # Без parse_mode
        except Exception as e:
            logger.error(f"Ошибка в week_command: {e}")
            await update.message.reply_text("Произошла ошибка при формировании топа недели.")
    
    async def month_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            top_users = self.db.get_monthly_top(TOP_USERS_LIMIT)
            if not top_users:
                await update.message.reply_text("Пока нет данных за этот месяц. Будь первым!")
                return
            text = f"🏆 Топ-{TOP_USERS_LIMIT} за месяц:\n\n"
            for i, (username, points) in enumerate(top_users, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                safe_username = self.escape_markdown(username or f'user_{i}')
                text += f"{emoji} {i}. @{safe_username} - {points} очков\n"
            monthly_winners = self.db.get_monthly_winners()
            if monthly_winners:
                text += "\n📜 Победители предыдущих месяцев:\n"
                for username, points, month_start in monthly_winners[:MONTHLY_WINNERS_HISTORY_LIMIT]:
                    month_name = datetime.datetime.strptime(month_start, '%Y-%m-%d').strftime('%B %Y')
                    safe_username = self.escape_markdown(username or 'user')
                    text += f"👑 {month_name}: @{safe_username} ({points} очков)\n"
            await update.message.reply_text(text)  # Без parse_mode
        except Exception as e:
            logger.error(f"Ошибка в month_command: {e}")
            await update.message.reply_text("Произошла ошибка при формировании топа месяца.")
    
    def is_meaningful_message(self, text: str) -> bool:
        """Проверка, является ли сообщение осмысленным (защита от спама)"""
        # Убираем эмодзи и специальные символы
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        # Проверяем количество слов
        if len(words) < MIN_WORDS_FOR_POINTS:
            return False
        
        # Проверяем на повторяющиеся символы (спам типа "аааа", "ввввв")
        for word in words:
            if len(word) > 2 and len(set(word)) <= 2:  # Слова типа "ааа", "вввв"
                return False
        
        # Проверяем на цифры (если сообщение состоит только из цифр)
        if re.match(r'^[\d\s]+$', text):
            return False
        
        # Проверяем на повторяющиеся слова (флуд)
        word_count = {}
        for word in words:
            if len(word) > 2:  # Игнорируем короткие слова
                word_count[word] = word_count.get(word, 0) + 1
                if word_count[word] > 3:  # Если слово повторяется больше 3 раз
                    return False
        
        # Проверяем на слишком короткие слова (спам)
        short_words = sum(1 for word in words if len(word) <= 2)
        if short_words > len(words) * 0.7:  # Если 70% слов короткие
            return False
        
        return True
    
    def get_current_probability(self, user_id=None) -> float:
        """Получение текущей вероятности начисления очков"""
        moscow_time = datetime.datetime.now(self.moscow_tz)
        current_hour = moscow_time.hour
        base = BASE_PROBABILITY
        # Проверяем временный буст пользователя
        now_ts = time.time()
        if user_id and user_id in user_boosts and user_boosts[user_id] > now_ts:
            base += 0.03
        # Если сейчас глобальный буст — он перекрывает временный
        if BOOST_START_HOUR <= current_hour < BOOST_END_HOUR:
            return BOOST_PROBABILITY
        return base
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений"""
        if not update.message or not update.message.text:
            return
        
        user = update.effective_user
        # Проверка на mute
        mute_left = self.db.is_muted(user.id)
        if mute_left > 0:
            mins = mute_left // 60
            secs = mute_left % 60
            await update.message.reply_text(f"Вы в муте ещё {mins} мин {secs} сек.")
            return
        
        message_text = update.message.text
        
        # Добавляем пользователя в базу данных
        self.db.add_user(
            user_id=user.id,
            username=user.username or f"user_{user.id}",
            first_name=user.first_name or "",
            last_name=user.last_name or ""
        )
        
        # Проверяем, является ли сообщение осмысленным
        if not self.is_meaningful_message(message_text):
            return
        
        # Определяем вероятность начисления очков
        probability = self.get_current_probability(user.id)
        
        # Проверяем, начислять ли очки
        if random.random() < probability:
            self.db.add_points(user.id, POINTS_PER_MESSAGE)
            
            # Получаем текущие очки пользователя за день
            stats = self.db.get_user_stats(user.id)
            if stats:
                current_daily_points = stats['today_points']
                
                # Проверяем достижения
                for threshold in POINTS_THRESHOLDS + [10000]:
                    if current_daily_points >= threshold:
                        achievement_key = f"{user.id}_{threshold}"
                        if achievement_key not in daily_achievements:
                            daily_achievements[achievement_key] = True
                            # Если порог ещё не был достигнут сегодня никем — оповещение в чат и буст
                            if not daily_threshold_achieved.get(threshold):
                                daily_threshold_achieved[threshold] = True
                                # Оповещение в чат
                                messages = MOTIVATION_MESSAGES.get(threshold, [
                                    f"🎉 @{user.username or user.first_name} первый достиг {threshold} очков за сегодня! Поздравляем!"
                                ])
                                message = random.choice(messages).format(username=user.username or user.first_name)
                                await context.bot.send_message(chat_id=CHAT_ID, text=message)
                                # Временный буст на 30 минут
                                user_boosts[user.id] = time.time() + 30*60
                            break
    
    async def daily_report(self, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневный отчет в 22:00"""
        try:
            top_users = self.db.get_daily_top(TOP_USERS_LIMIT)
            
            if not top_users:
                report_text = f"📊 *Ежедневный отчет*\n\nСегодня пока нет активных пользователей. Будь первым!"
            else:
                report_text = f"📊 *Ежедневный отчет активности*\n\n🏆 *Топ активных пользователей:*\n\n"
                
                for i, (username, points) in enumerate(top_users, 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                    report_text += f"{emoji} {i}. @{username} - {points} очков\n"
                
                report_text += "\n🎯 *Продолжайте общаться и зарабатывать очки!*"
            
            await context.bot.send_message(chat_id=CHAT_ID, text=report_text, parse_mode='Markdown')
            logger.info("Ежедневный отчет отправлен")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке ежедневного отчета: {e}")
    
    async def boost_announcement(self, context: ContextTypes.DEFAULT_TYPE):
        """Объявление о бусте активности в 20:00"""
        try:
            boost_text = f"""
🚀 *БУСТ АКТИВНОСТИ!*

С {BOOST_START_HOUR}:00 до {BOOST_END_HOUR}:00 по МСК вероятность получения очков повышена с {BASE_PROBABILITY*100:.0f}% до {BOOST_PROBABILITY*100:.0f}%!

💬 Общайся активно и зарабатывай больше очков!
⏰ Буст действует {BOOST_END_HOUR - BOOST_START_HOUR} часа
            """
            await context.bot.send_message(chat_id=CHAT_ID, text=boost_text, parse_mode='Markdown')
            logger.info("Объявление о бусте отправлено")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке объявления о бусте: {e}")
    
    async def reset_daily_achievements(self, context: ContextTypes.DEFAULT_TYPE):
        """Сброс достижений за день"""
        global daily_achievements, daily_threshold_achieved, user_boosts
        daily_achievements.clear()
        daily_threshold_achieved.clear()
        user_boosts.clear()
        logger.info("Достижения, пороги и бусты за день сброшены")
    
    async def check_monthly_winner(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверка и сохранение победителя месяца"""
        try:
            # Получаем победителя предыдущего месяца
            winner = self.db.get_previous_month_winner()
            if winner:
                user_id, username, points = winner
                
                # Проверяем, не сохранен ли уже этот победитель
                previous_month = datetime.datetime.now() - datetime.timedelta(days=30)
                month_start = previous_month.replace(day=1).isoformat()[:10]
                
                # Сохраняем победителя
                self.db.save_monthly_winner(user_id, username, points, month_start)
                
                # Отправляем уведомление о победителе месяца
                winner_text = f"""
👑 *ПОБЕДИТЕЛЬ МЕСЯЦА!*

Поздравляем @{username} с победой в прошлом месяце!
🏆 Набрано очков: {points}

Отличная работа! Продолжайте в том же духе! 🎉
                """
                await context.bot.send_message(chat_id=CHAT_ID, text=winner_text, parse_mode='Markdown')
                
                logger.info(f"Победитель месяца сохранен: {username} с {points} очками")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке победителя месяца: {e}")

    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if len(context.args) != 2:
                await update.message.reply_text("Использование: /send username количество")
                return
            to_username = context.args[0].lstrip('@')
            amount = int(context.args[1])
            if amount <= 0:
                await update.message.reply_text("Количество должно быть положительным!")
                return
            from_user = update.effective_user
            from_stats = self.db.get_user_stats(from_user.id)
            if not from_stats or from_stats['total_points'] < amount:
                await update.message.reply_text("Недостаточно очков для перевода!")
                return
            # Найти user_id по username
            to_user_id = None
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE username = ?", (to_username,))
                row = cursor.fetchone()
                if row:
                    to_user_id = row[0]
            if not to_user_id:
                await update.message.reply_text("Пользователь не найден!")
                return
            # Списать у отправителя, начислить получателю
            self.db.add_points(from_user.id, -amount)
            self.db.add_points(to_user_id, amount)
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"@{from_user.username or from_user.first_name} отправил(а) {amount} очков активности @{to_username}!"
            )
        except Exception as e:
            logger.error(f"Ошибка в send_command: {e}")
            await update.message.reply_text("Ошибка при переводе очков.")

    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if len(context.args) != 2:
                await update.message.reply_text("Использование: /mute username количество_очков (кратно 100)")
                return
            to_username = context.args[0].lstrip('@')
            amount = int(context.args[1])
            if amount < 100 or amount % 100 != 0:
                await update.message.reply_text("Минимум 100 очков и только кратно 100!")
                return
            from_user = update.effective_user
            from_stats = self.db.get_user_stats(from_user.id)
            if not from_stats or from_stats['total_points'] < amount:
                await update.message.reply_text("Недостаточно очков для мута!")
                return
            # Найти user_id по username
            to_user_id = None
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE username = ?", (to_username,))
                row = cursor.fetchone()
                if row:
                    to_user_id = row[0]
            if not to_user_id:
                await update.message.reply_text("Пользователь не найден!")
                return
            # Списать очки у инициатора
            self.db.add_points(from_user.id, -amount)
            # Рассчитать время мута
            mute_minutes = (amount // 100) * 30
            mute_seconds = mute_minutes * 60
            until_ts = int(time.time()) + mute_seconds
            self.db.set_mute(to_user_id, until_ts)
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"@{from_user.username or from_user.first_name} замутил(а) @{to_username} на {mute_minutes} минут! (-{amount} очков)"
            )
        except Exception as e:
            logger.error(f"Ошибка в mute_command: {e}")
            await update.message.reply_text("Ошибка при попытке мута.")

    async def dice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if len(context.args) != 1:
                await update.message.reply_text("Использование: /dice количество_очков")
                return
            amount = int(context.args[0])
            user = update.effective_user
            stats = self.db.get_user_stats(user.id)
            if not stats or stats['total_points'] < amount or amount <= 0:
                await update.message.reply_text("Недостаточно очков для игры!")
                return
            # Случайная вероятность выигрыша 10-20%
            win_chance = random.uniform(0.10, 0.20)
            win = random.random() < win_chance
            if win:
                self.db.add_points(user.id, amount)  # удвоение
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"@{user.username or user.first_name} бросил(а) кости и выиграл(а) {amount} очков! 🎲"
                )
            else:
                self.db.add_points(user.id, -amount)
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"@{user.username or user.first_name} бросил(а) кости и проиграл(а) {amount} очков! 🎲"
                )
        except Exception as e:
            logger.error(f"Ошибка в dice_command: {e}")
            await update.message.reply_text("Ошибка при игре в кости.")

def main():
    """Основная функция"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаем экземпляр бота
    bot = ChatBot(application)
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CommandHandler("week", bot.week_command))
    application.add_handler(CommandHandler("month", bot.month_command))
    application.add_handler(CommandHandler("JK", bot.jk_command))
    application.add_handler(CommandHandler("send", bot.send_command))
    application.add_handler(CommandHandler("mute", bot.mute_command))
    application.add_handler(CommandHandler("dice", bot.dice_command))
    
    # Добавляем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Настраиваем планировщик через JobQueue
    job_queue = application.job_queue
    moscow_tz = pytz.timezone('Europe/Moscow')
    
    # Ежедневный отчет
    job_queue.run_daily(
        bot.daily_report, 
        time=datetime.time(hour=DAILY_REPORT_HOUR, minute=DAILY_REPORT_MINUTE, tzinfo=moscow_tz)
    )
    
    # Объявление о бусте
    job_queue.run_daily(
        bot.boost_announcement, 
        time=datetime.time(hour=BOOST_START_HOUR, minute=0, tzinfo=moscow_tz)
    )
    
    # Сброс достижений
    job_queue.run_daily(
        bot.reset_daily_achievements, 
        time=datetime.time(hour=RESET_ACHIEVEMENTS_HOUR, minute=RESET_ACHIEVEMENTS_MINUTE, tzinfo=moscow_tz)
    )
    
    # Проверка победителя месяца
    job_queue.run_daily(
        bot.check_monthly_winner, 
        time=datetime.time(hour=MONTHLY_WINNER_CHECK_HOUR, minute=MONTHLY_WINNER_CHECK_MINUTE, tzinfo=moscow_tz), 
        days=(1,)
    )
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 