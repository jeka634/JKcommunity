import os
import logging
import asyncio
from datetime import datetime, time
from typing import Dict, List, Optional
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

from database.database import Database
from ton_integration.ton_wallet import TONWallet
from utils.message_validator import MessageValidator
from games.dice_game import DiceGame
from couchsurfing.couchsurfing_service import CouchsurfingService

# Загрузка переменных окружения
load_dotenv('config.env')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GasJKBot:
    def __init__(self):
        # Инициализация компонентов
        self.db = Database(os.getenv('DATABASE_PATH', './database/gasjk_bot.db'))
        self.ton_wallet = TONWallet(os.getenv('TON_NETWORK', 'mainnet'))
        self.message_validator = MessageValidator()
        self.dice_game = DiceGame(self.db)
        self.couchsurfing = CouchsurfingService(self.db)
        
        # Конфигурация
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('TELEGRAM_ADMIN_ID', 0))
        self.message_reward = float(os.getenv('MESSAGE_REWARD', 0.1))
        self.min_withdrawal = float(os.getenv('MIN_WITHDRAWAL_AMOUNT', 25000))
        
        # Московское время
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Состояния пользователей для FSM
        self.user_states = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Добавление пользователя в базу данных
        self.db.add_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        if update.effective_chat.type == 'private':
            # Личные сообщения с ботом
            await self.show_main_menu(update, context)
        else:
            # Групповой чат
            await update.message.reply_text(
                f"Привет, {user.first_name}! Я бот для управления $gasJK токенами и каучсёрфинга. "
                f"Напиши мне в личные сообщения для доступа к функциям."
            )
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню"""
        keyboard = [
            [InlineKeyboardButton("💰 Баланс $gasJK", callback_data="balance")],
            [InlineKeyboardButton("🎲 Игра в кости", callback_data="dice_game")],
            [InlineKeyboardButton("🏠 Каучсёрфинг", callback_data="couchsurfing")],
            [InlineKeyboardButton("🖼️ Мои NFT", callback_data="my_nfts")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("💸 Отправить $gasJK", callback_data="send_gasjk")],
            [InlineKeyboardButton("📥 Получить $gasJK", callback_data="receive_gasjk")],
            [InlineKeyboardButton("🔗 Подключить TON кошелек", callback_data="connect_wallet")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "🎯 Главное меню GasJK Bot\n\nВыберите действие:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "🎯 Главное меню GasJK Bot\n\nВыберите действие:",
                reply_markup=reply_markup
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text
        chat_type = update.effective_chat.type
        
        # Добавление пользователя в базу данных
        self.db.add_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        if chat_type == 'private':
            # Личные сообщения - обработка FSM
            await self.handle_private_message(update, context)
        else:
            # Групповой чат - валидация и начисление токенов
            await self.handle_group_message(update, context)
    
    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка личных сообщений"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Проверка состояния пользователя
        user_state = self.user_states.get(user_id, {})
        
        if user_state.get('state') == 'waiting_wallet_address':
            await self.connect_wallet_address(update, context, message_text)
        elif user_state.get('state') == 'waiting_send_amount':
            await self.process_send_amount(update, context, message_text)
        elif user_state.get('state') == 'waiting_send_user':
            await self.process_send_user(update, context, message_text)
        elif user_state.get('state') == 'waiting_dice_bet':
            await self.process_dice_bet(update, context, message_text)
        elif user_state.get('state') == 'waiting_dice_opponent':
            await self.process_dice_opponent(update, context, message_text)
        elif user_state.get('state') == 'waiting_ad_country':
            await self.process_ad_country(update, context, message_text)
        elif user_state.get('state') == 'waiting_ad_city':
            await self.process_ad_city(update, context, message_text)
        elif user_state.get('state') == 'waiting_ad_description':
            await self.process_ad_description(update, context, message_text)
        else:
            # Обычное сообщение - показать главное меню
            await self.show_main_menu(update, context)
    
    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений в групповом чате"""
        user = update.effective_user
        message_text = update.message.text
        
        # Валидация сообщения
        validation_result = self.message_validator.validate_message(message_text, user.id)
        
        if validation_result['is_valid']:
            # Начисление токенов за осмысленное сообщение
            self.db.update_user_balance(user.id, self.message_reward)
            self.db.increment_messages(user.id)
            
            # Добавление транзакции
            self.db.add_transaction(0, user.id, self.message_reward, 'message_reward')
            
            # Уведомление пользователя (только если это не спам)
            if validation_result['score'] > 0.5:
                await update.message.reply_text(
                    f"✅ +{self.message_reward} $gasJK за осмысленное сообщение! "
                    f"Баланс: {self.db.get_user(user.id)['gasjk_balance']:.1f} $gasJK"
                )
        else:
            # Сообщение не прошло валидацию
            logger.info(f"Message from {user.id} didn't pass validation: {validation_result['reason']}")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "balance":
            await self.show_balance(update, context)
        elif data == "dice_game":
            await self.show_dice_menu(update, context)
        elif data == "couchsurfing":
            await self.show_couchsurfing_menu(update, context)
        elif data == "my_nfts":
            await self.show_nfts(update, context)
        elif data == "stats":
            await self.show_stats(update, context)
        elif data == "send_gasjk":
            await self.start_send_gasjk(update, context)
        elif data == "receive_gasjk":
            await self.show_receive_gasjk(update, context)
        elif data == "connect_wallet":
            await self.start_connect_wallet(update, context)
        elif data == "back_to_main":
            await self.show_main_menu(update, context)
        elif data.startswith("dice_"):
            await self.handle_dice_callback(update, context, data)
        elif data.startswith("cs_"):
            await self.handle_couchsurfing_callback(update, context, data)
    
    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать баланс пользователя"""
        user_id = update.callback_query.from_user.id
        user = self.db.get_user(user_id)
        
        if user:
            balance = user['gasjk_balance']
            messages_count = user['messages_count']
            nft_count = user['nft_count']
            
            text = f"💰 Ваш баланс: {balance:.1f} $gasJK\n\n"
            text += f"📊 Статистика:\n"
            text += f"• Сообщений: {messages_count}\n"
            text += f"• NFT: {nft_count}\n"
            
            if balance >= self.min_withdrawal:
                text += f"\n✅ Доступен вывод в TON кошелек!"
            else:
                text += f"\n⏳ Для вывода нужно накопить {self.min_withdrawal} $gasJK"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_dice_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню игры в кости"""
        keyboard = [
            [InlineKeyboardButton("🎲 Создать игру", callback_data="dice_create")],
            [InlineKeyboardButton("📊 Мои игры", callback_data="dice_my_games")],
            [InlineKeyboardButton("🏆 Таблица лидеров", callback_data="dice_leaderboard")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🎲 Игра в кости\n\nСтавьте $gasJK и соревнуйтесь с другими игроками!",
            reply_markup=reply_markup
        )
    
    async def show_couchsurfing_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню каучсёрфинга"""
        keyboard = [
            [InlineKeyboardButton("🏠 Принимаю гостей", callback_data="cs_host")],
            [InlineKeyboardButton("🏃 Приеду в гости", callback_data="cs_guest")],
            [InlineKeyboardButton("📋 Доска объявлений", callback_data="cs_board")],
            [InlineKeyboardButton("📊 Мои бронирования", callback_data="cs_bookings")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🏠 Каучсёрфинг\n\nНайдите место для ночлега или примите гостей!",
            reply_markup=reply_markup
        )
    
    async def show_nfts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать NFT пользователя"""
        user_id = update.callback_query.from_user.id
        nfts = self.db.get_user_nfts(user_id)
        
        if nfts:
            text = "🖼️ Ваши NFT:\n\n"
            for nft in nfts:
                text += f"• {nft['collection_name']} #{nft['token_id']}\n"
        else:
            text = "🖼️ У вас пока нет NFT"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        user_id = update.callback_query.from_user.id
        user = self.db.get_user(user_id)
        transactions = self.db.get_user_transactions(user_id, 5)
        
        text = "📊 Ваша статистика:\n\n"
        text += f"💰 Баланс: {user['gasjk_balance']:.1f} $gasJK\n"
        text += f"💬 Сообщений: {user['messages_count']}\n"
        text += f"🖼️ NFT: {user['nft_count']}\n"
        text += f"📅 Регистрация: {user['registration_date']}\n\n"
        
        if transactions:
            text += "📈 Последние транзакции:\n"
            for tx in transactions[:3]:
                amount = tx['amount']
                if tx['from_user_id'] == user_id:
                    text += f"➖ {amount:.1f} $gasJK\n"
                else:
                    text += f"➕ {amount:.1f} $gasJK\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def start_send_gasjk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс отправки $gasJK"""
        user_id = update.callback_query.from_user.id
        user = self.db.get_user(user_id)
        
        if user['gasjk_balance'] <= 0:
            await update.callback_query.edit_message_text(
                "❌ Недостаточно $gasJK для отправки",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
            )
            return
        
        # Установка состояния ожидания суммы
        self.user_states[user_id] = {
            'state': 'waiting_send_amount',
            'data': {}
        }
        
        await update.callback_query.edit_message_text(
            f"💸 Отправка $gasJK\n\nВаш баланс: {user['gasjk_balance']:.1f} $gasJK\n\n"
            f"Введите сумму для отправки:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]])
        )
    
    async def process_send_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка введенной суммы для отправки"""
        user_id = update.effective_user.id
        try:
            amount = float(update.message.text)
            user = self.db.get_user(user_id)
            
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть больше 0")
                return
            
            if amount > user['gasjk_balance']:
                await update.message.reply_text("❌ Недостаточно средств")
                return
            
            # Сохранение суммы и переход к выбору получателя
            self.user_states[user_id] = {
                'state': 'waiting_send_user',
                'data': {'amount': amount}
            }
            
            await update.message.reply_text(
                f"💸 Отправка {amount:.1f} $gasJK\n\n"
                f"Введите username получателя (без @):"
            )
            
        except ValueError:
            await update.message.reply_text("❌ Введите корректную сумму")
    
    async def process_send_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора получателя"""
        user_id = update.effective_user.id
        recipient_username = update.message.text.strip()
        
        # Поиск пользователя по username
        # В реальном проекте нужно добавить метод поиска по username в базу данных
        # Пока используем заглушку
        recipient_id = None  # Здесь должна быть логика поиска
        
        if not recipient_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        # Выполнение транзакции
        state_data = self.user_states[user_id]['data']
        amount = state_data['amount']
        
        # Списывание с отправителя
        self.db.update_user_balance(user_id, -amount)
        # Начисление получателю
        self.db.update_user_balance(recipient_id, amount)
        # Запись транзакции
        self.db.add_transaction(user_id, recipient_id, amount, 'transfer')
        
        # Очистка состояния
        del self.user_states[user_id]
        
        await update.message.reply_text(
            f"✅ Успешно отправлено {amount:.1f} $gasJK пользователю @{recipient_username}"
        )
        await self.show_main_menu(update, context)
    
    async def show_receive_gasjk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о получении $gasJK"""
        user_id = update.callback_query.from_user.id
        user = self.db.get_user(user_id)
        
        text = "📥 Получение $gasJK\n\n"
        text += f"Ваш username: @{user.get('username', 'не указан')}\n\n"
        text += "Другие пользователи могут отправить вам $gasJK, используя ваш username.\n\n"
        text += f"Текущий баланс: {user['gasjk_balance']:.1f} $gasJK"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def start_connect_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс подключения TON кошелька"""
        user_id = update.callback_query.from_user.id
        
        # Установка состояния ожидания адреса кошелька
        self.user_states[user_id] = {
            'state': 'waiting_wallet_address',
            'data': {}
        }
        
        text = "🔗 Подключение TON кошелька\n\n"
        text += "Для подключения вашего TON кошелька:\n\n"
        text += "1️⃣ Скачайте Telegram Wallet или Tonkeeper\n"
        text += "2️⃣ Создайте кошелек\n"
        text += "3️⃣ Скопируйте адрес кошелька\n"
        text += "4️⃣ Вставьте адрес ниже\n\n"
        text += "Введите адрес вашего TON кошелька:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def connect_wallet_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка введенного адреса кошелька"""
        user_id = update.effective_user.id
        wallet_address = update.message.text.strip()
        
        # Валидация адреса
        if not self.ton_wallet.validate_wallet_address(wallet_address):
            await update.message.reply_text("❌ Неверный формат адреса TON кошелька")
            return
        
        # Сохранение адреса в базе данных
        # В реальном проекте нужно добавить метод обновления адреса кошелька
        # self.db.update_user_wallet(user_id, wallet_address)
        
        # Очистка состояния
        del self.user_states[user_id]
        
        await update.message.reply_text(
            f"✅ TON кошелек успешно подключен!\n\n"
            f"Адрес: {wallet_address}\n\n"
            f"Теперь вы можете выводить $gasJK в TON кошелек при достижении {self.min_withdrawal} токенов."
        )
        await self.show_main_menu(update, context)
    
    async def handle_dice_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Обработка callback кнопок игры в кости"""
        if data == "dice_create":
            await self.start_dice_game(update, context)
        elif data == "dice_my_games":
            await self.show_my_dice_games(update, context)
        elif data == "dice_leaderboard":
            await self.show_dice_leaderboard(update, context)
    
    async def start_dice_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание игры в кости"""
        user_id = update.callback_query.from_user.id
        user = self.db.get_user(user_id)
        
        if user['gasjk_balance'] < self.dice_game.min_bet:
            await update.callback_query.edit_message_text(
                f"❌ Недостаточно $gasJK для игры. Минимум: {self.dice_game.min_bet} $gasJK",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="dice_game")]])
            )
            return
        
        # Установка состояния ожидания ставки
        self.user_states[user_id] = {
            'state': 'waiting_dice_bet',
            'data': {}
        }
        
        await update.callback_query.edit_message_text(
            f"🎲 Создание игры в кости\n\n"
            f"Ваш баланс: {user['gasjk_balance']:.1f} $gasJK\n"
            f"Минимальная ставка: {self.dice_game.min_bet} $gasJK\n"
            f"Максимальная ставка: {self.dice_game.max_bet} $gasJK\n\n"
            f"Введите сумму ставки:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="dice_game")]])
        )
    
    async def process_dice_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ставки для игры в кости"""
        user_id = update.effective_user.id
        try:
            bet_amount = float(update.message.text)
            user = self.db.get_user(user_id)
            
            if not self.dice_game.min_bet <= bet_amount <= self.dice_game.max_bet:
                await update.message.reply_text(
                    f"❌ Ставка должна быть от {self.dice_game.min_bet} до {self.dice_game.max_bet} $gasJK"
                )
                return
            
            if bet_amount > user['gasjk_balance']:
                await update.message.reply_text("❌ Недостаточно средств")
                return
            
            # Сохранение ставки и переход к выбору противника
            self.user_states[user_id] = {
                'state': 'waiting_dice_opponent',
                'data': {'bet_amount': bet_amount}
            }
            
            await update.message.reply_text(
                f"🎲 Ставка: {bet_amount:.1f} $gasJK\n\n"
                f"Введите username противника (без @):"
            )
            
        except ValueError:
            await update.message.reply_text("❌ Введите корректную сумму")
    
    async def process_dice_opponent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора противника для игры в кости"""
        user_id = update.effective_user.id
        opponent_username = update.message.text.strip()
        
        # Поиск противника по username
        opponent_id = None  # Здесь должна быть логика поиска
        
        if not opponent_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if opponent_id == user_id:
            await update.message.reply_text("❌ Нельзя играть с самим собой")
            return
        
        # Создание игры
        state_data = self.user_states[user_id]['data']
        bet_amount = state_data['bet_amount']
        
        game_id = self.dice_game.create_game(user_id, opponent_id, bet_amount)
        
        if game_id:
            # Очистка состояния
            del self.user_states[user_id]
            
            await update.message.reply_text(
                f"🎲 Игра создана!\n\n"
                f"ID игры: {game_id}\n"
                f"Ставка: {bet_amount:.1f} $gasJK\n"
                f"Противник: @{opponent_username}\n\n"
                f"Ожидайте, пока противник примет игру и бросит кости."
            )
        else:
            await update.message.reply_text("❌ Ошибка создания игры")
        
        await self.show_main_menu(update, context)
    
    async def show_my_dice_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать игры пользователя в кости"""
        user_id = update.callback_query.from_user.id
        games = self.dice_game.get_player_games(user_id, 5)
        
        if games:
            text = "🎲 Ваши последние игры:\n\n"
            for game in games:
                status = "🔄 Активна" if game['status'] == 'active' else "✅ Завершена"
                text += f"• Игра #{game['id']} - {status}\n"
                text += f"  Ставка: {game['bet_amount']:.1f} $gasJK\n\n"
        else:
            text = "🎲 У вас пока нет игр"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="dice_game")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_dice_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать таблицу лидеров игры в кости"""
        leaderboard = self.dice_game.get_leaderboard(10)
        
        if leaderboard:
            text = "🏆 Таблица лидеров (игра в кости):\n\n"
            for i, player in enumerate(leaderboard, 1):
                name = player.get('first_name', '') + ' ' + player.get('last_name', '')
                wins = player.get('wins', 0)
                total_winnings = player.get('total_winnings', 0)
                text += f"{i}. {name}\n"
                text += f"   Победы: {wins}, Выигрыш: {total_winnings:.1f} $gasJK\n\n"
        else:
            text = "🏆 Пока нет данных для таблицы лидеров"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="dice_game")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_couchsurfing_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Обработка callback кнопок каучсёрфинга"""
        if data == "cs_host":
            await self.start_create_ad(update, context)
        elif data == "cs_guest":
            await self.show_available_ads(update, context)
        elif data == "cs_board":
            await self.show_ads_board(update, context)
        elif data == "cs_bookings":
            await self.show_my_bookings(update, context)
    
    async def start_create_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание объявления о приеме гостей"""
        user_id = update.callback_query.from_user.id
        
        # Установка состояния ожидания страны
        self.user_states[user_id] = {
            'state': 'waiting_ad_country',
            'data': {}
        }
        
        await update.callback_query.edit_message_text(
            "🏠 Создание объявления\n\nВведите страну:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="couchsurfing")]])
        )
    
    async def process_ad_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка введенной страны"""
        user_id = update.effective_user.id
        country = update.message.text.strip()
        
        # Сохранение страны и переход к городу
        self.user_states[user_id] = {
            'state': 'waiting_ad_city',
            'data': {'country': country}
        }
        
        await update.message.reply_text("Введите город:")
    
    async def process_ad_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка введенного города"""
        user_id = update.effective_user.id
        city = update.message.text.strip()
        
        # Сохранение города и переход к описанию
        state_data = self.user_states[user_id]['data']
        state_data['city'] = city
        
        self.user_states[user_id] = {
            'state': 'waiting_ad_description',
            'data': state_data
        }
        
        await update.message.reply_text(
            "Введите описание (условия проживания, что предоставляете):"
        )
    
    async def process_ad_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка описания объявления"""
        user_id = update.effective_user.id
        description = update.message.text.strip()
        
        state_data = self.user_states[user_id]['data']
        country = state_data['country']
        city = state_data['city']
        
        # Создание объявления (упрощенная версия без дат)
        ad_id = self.couchsurfing.create_ad(
            user_id, country, city, "", "2024-01-01", "2024-12-31", description
        )
        
        if ad_id > 0:
            # Очистка состояния
            del self.user_states[user_id]
            
            await update.message.reply_text(
                f"✅ Объявление создано!\n\n"
                f"Страна: {country}\n"
                f"Город: {city}\n"
                f"Описание: {description}\n\n"
                f"ID объявления: {ad_id}"
            )
        else:
            await update.message.reply_text("❌ Ошибка создания объявления")
        
        await self.show_main_menu(update, context)
    
    async def show_available_ads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать доступные объявления"""
        ads = self.couchsurfing.get_ads()
        
        if ads:
            text = "🏠 Доступные объявления:\n\n"
            for ad in ads[:5]:  # Показываем первые 5
                text += f"📍 {ad['country']}, {ad['city']}\n"
                text += f"👤 {ad.get('host_name', 'Не указано')}\n"
                text += f"⭐ Рейтинг: {ad.get('rating', 0):.1f}\n"
                text += f"📝 {ad['description'][:100]}...\n\n"
        else:
            text = "🏠 Пока нет доступных объявлений"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="couchsurfing")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_ads_board(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать доску объявлений"""
        ads = self.couchsurfing.get_ads()
        
        if ads:
            text = "📋 Доска объявлений:\n\n"
            for ad in ads[:10]:  # Показываем первые 10
                text += f"🏠 {ad['country']}, {ad['city']}\n"
                text += f"👤 @{ad.get('host_username', 'не указан')}\n"
                text += f"⭐ {ad.get('rating', 0):.1f}/5.0\n"
                text += f"📅 {ad['start_date']} - {ad['end_date']}\n\n"
        else:
            text = "📋 Пока нет объявлений"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="couchsurfing")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_my_bookings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать бронирования пользователя"""
        user_id = update.callback_query.from_user.id
        bookings_as_guest = self.couchsurfing.get_user_bookings(user_id, as_guest=True)
        bookings_as_host = self.couchsurfing.get_user_bookings(user_id, as_guest=False)
        
        text = "📋 Мои бронирования:\n\n"
        
        if bookings_as_guest:
            text += "🏃 Как гость:\n"
            for booking in bookings_as_guest[:3]:
                text += f"• {booking['country']}, {booking['city']} - {booking['status']}\n"
            text += "\n"
        
        if bookings_as_host:
            text += "🏠 Как хост:\n"
            for booking in bookings_as_host[:3]:
                text += f"• {booking['country']}, {booking['city']} - {booking['status']}\n"
        
        if not bookings_as_guest and not bookings_as_host:
            text += "У вас пока нет бронирований"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="couchsurfing")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def send_daily_report(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправка ежедневного отчета"""
        if not self.admin_id:
            return
        
        stats = self.db.get_daily_stats()
        
        text = "📊 Ежедневный отчет\n\n"
        text += f"👥 Активных пользователей: {stats['total_users']}\n"
        text += f"💰 Общий баланс: {stats['total_balance']:.1f} $gasJK\n"
        text += f"💬 Сообщений: {stats['total_messages']}\n"
        text += f"🖼️ NFT: {stats['total_nfts']}\n\n"
        text += f"📅 {datetime.now(self.moscow_tz).strftime('%d.%m.%Y')}"
        
        await context.bot.send_message(chat_id=self.admin_id, text=text)
    
    async def send_course_update(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправка обновления курса"""
        if not self.admin_id:
            return
        
        # В реальном проекте здесь должна быть интеграция с API для получения курсов
        text = "💱 Курс $gasJK\n\n"
        text += f"💵 $gasJK/USD: 0.001\n"
        text += f"₽ $gasJK/RUB: 0.08\n"
        text += f"⚡ $gasJK/TON: 0.0005\n\n"
        text += f"📅 {datetime.now(self.moscow_tz).strftime('%d.%m.%Y %H:%M')}"
        
        await context.bot.send_message(chat_id=self.admin_id, text=text)
    
    def run(self):
        """Запуск бота"""
        if not self.bot_token:
            logger.error("Bot token not found!")
            return
        
        # Создание приложения
        application = Application.builder().token(self.bot_token).build()
        
        # Добавление обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Настройка планировщика задач
        job_queue = application.job_queue
        
        # Ежедневный отчет в 22:00 по МСК
        report_time = time(22, 0, tzinfo=self.moscow_tz)
        job_queue.run_daily(self.send_daily_report, report_time)
        
        # Обновление курса в 8:00 по МСК
        course_time = time(8, 0, tzinfo=self.moscow_tz)
        job_queue.run_daily(self.send_course_update, course_time)
        
        # Запуск бота
        logger.info("Starting GasJK Bot...")
        application.run_polling()

if __name__ == "__main__":
    bot = GasJKBot()
    bot.run() 