import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    ton_wallet TEXT,
                    gasjk_balance REAL DEFAULT 0.0,
                    messages_count INTEGER DEFAULT 0,
                    nft_count INTEGER DEFAULT 0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица транзакций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user_id INTEGER,
                    to_user_id INTEGER,
                    amount REAL,
                    transaction_type TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_user_id) REFERENCES users (user_id),
                    FOREIGN KEY (to_user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица NFT
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nfts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    nft_address TEXT,
                    collection_name TEXT,
                    token_id TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица объявлений (каучсёрфинг)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS couchsurfing_ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    country TEXT,
                    city TEXT,
                    settlement TEXT,
                    start_date DATE,
                    end_date DATE,
                    description TEXT,
                    rating REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица бронирований
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guest_id INTEGER,
                    host_id INTEGER,
                    ad_id INTEGER,
                    start_date DATE,
                    end_date DATE,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guest_id) REFERENCES users (user_id),
                    FOREIGN KEY (host_id) REFERENCES users (user_id),
                    FOREIGN KEY (ad_id) REFERENCES couchsurfing_ads (id)
                )
            ''')
            
            # Таблица игр в кости
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dice_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT UNIQUE,
                    player1_id INTEGER,
                    player2_id INTEGER,
                    bet_amount REAL,
                    player1_dice INTEGER,
                    player2_dice INTEGER,
                    winner_id INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player1_id) REFERENCES users (user_id),
                    FOREIGN KEY (player2_id) REFERENCES users (user_id),
                    FOREIGN KEY (winner_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
    
    def add_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Добавление нового пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logging.error(f"Error getting user: {e}")
            return None
    
    def update_user_balance(self, user_id: int, amount: float) -> bool:
        """Обновление баланса пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET gasjk_balance = gasjk_balance + ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (amount, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating balance: {e}")
            return False
    
    def increment_messages(self, user_id: int) -> bool:
        """Увеличение счетчика сообщений"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET messages_count = messages_count + 1, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error incrementing messages: {e}")
            return False
    
    def add_transaction(self, from_user_id: int, to_user_id: int, amount: float, transaction_type: str) -> int:
        """Добавление транзакции"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type)
                    VALUES (?, ?, ?, ?)
                ''', (from_user_id, to_user_id, amount, transaction_type))
                conn.commit()
                result = cursor.lastrowid
                return result if result is not None else -1
        except Exception as e:
            logging.error(f"Error adding transaction: {e}")
            return -1
    
    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получение транзакций пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM transactions 
                    WHERE from_user_id = ? OR to_user_id = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (user_id, user_id, limit))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error getting transactions: {e}")
            return []
    
    def add_nft(self, user_id: int, nft_address: str, collection_name: str, token_id: str, metadata: str) -> bool:
        """Добавление NFT пользователю"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO nfts (user_id, nft_address, collection_name, token_id, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, nft_address, collection_name, token_id, metadata))
                conn.commit()
                
                # Обновляем счетчик NFT у пользователя
                cursor.execute('''
                    UPDATE users SET nft_count = nft_count + 1 WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding NFT: {e}")
            return False
    
    def get_user_nfts(self, user_id: int) -> List[Dict]:
        """Получение NFT пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM nfts WHERE user_id = ?', (user_id,))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error getting NFTs: {e}")
            return []
    
    def add_couchsurfing_ad(self, user_id: int, country: str, city: str, settlement: str, 
                           start_date: str, end_date: str, description: str) -> int:
        """Добавление объявления о каучсёрфинге"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO couchsurfing_ads (user_id, country, city, settlement, start_date, end_date, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, country, city, settlement, start_date, end_date, description))
                conn.commit()
                result = cursor.lastrowid
                return result if result is not None else -1
        except Exception as e:
            logging.error(f"Error adding ad: {e}")
            return -1
    
    def get_couchsurfing_ads(self, country: Optional[str] = None, city: Optional[str] = None, 
                            settlement: Optional[str] = None, status: str = 'active') -> List[Dict]:
        """Получение объявлений о каучсёрфинге с фильтрацией"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = 'SELECT * FROM couchsurfing_ads WHERE status = ?'
                params = [status]
                
                if country:
                    query += ' AND country = ?'
                    params.append(country)
                if city:
                    query += ' AND city = ?'
                    params.append(city)
                if settlement:
                    query += ' AND settlement = ?'
                    params.append(settlement)
                
                query += ' ORDER BY created_at DESC'
                cursor.execute(query, params)
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error getting ads: {e}")
            return []
    
    def add_dice_game(self, game_id: str, player1_id: int, player2_id: int, bet_amount: float) -> bool:
        """Создание новой игры в кости"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dice_games (game_id, player1_id, player2_id, bet_amount)
                    VALUES (?, ?, ?, ?)
                ''', (game_id, player1_id, player2_id, bet_amount))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding dice game: {e}")
            return False
    
    def update_dice_game_result(self, game_id: str, player1_dice: int, player2_dice: int, winner_id: int) -> bool:
        """Обновление результата игры в кости"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE dice_games 
                    SET player1_dice = ?, player2_dice = ?, winner_id = ?, status = 'completed'
                    WHERE game_id = ?
                ''', (player1_dice, player2_dice, winner_id, game_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating dice game: {e}")
            return False
    
    def get_daily_stats(self) -> Dict:
        """Получение статистики за день"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_users,
                        SUM(gasjk_balance) as total_balance,
                        SUM(messages_count) as total_messages,
                        SUM(nft_count) as total_nfts
                    FROM users
                    WHERE DATE(last_activity) = DATE('now')
                ''')
                row = cursor.fetchone()
                return {
                    'total_users': row[0] or 0,
                    'total_balance': row[1] or 0,
                    'total_messages': row[2] or 0,
                    'total_nfts': row[3] or 0
                }
        except Exception as e:
            logging.error(f"Error getting daily stats: {e}")
            return {'total_users': 0, 'total_balance': 0, 'total_messages': 0, 'total_nfts': 0} 