import sqlite3
import datetime
from typing import List, Tuple, Optional, Dict, Any
import time

class Database:
    def __init__(self, db_path: str = "chat_bot.db"):
        """Инициализация базы данных"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация таблиц базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица очков за день
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    points INTEGER,
                    date DATE DEFAULT CURRENT_DATE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, date)
                )
            ''')
            
            # Таблица очков за неделю
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    points INTEGER,
                    week_start DATE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, week_start)
                )
            ''')
            
            # Таблица очков за месяц
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monthly_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    points INTEGER,
                    month_start DATE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, month_start)
                )
            ''')
            
            # Таблица победителей месяцев
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monthly_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    points INTEGER,
                    month_start DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица мутов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mutes (
                    user_id INTEGER PRIMARY KEY,
                    until_timestamp INTEGER
                )
            ''')
            
            conn.commit()
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Добавление пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
    
    def add_points(self, user_id: int, points: int):
        """Добавление очков пользователю"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Добавляем очки за день
            cursor.execute('''
                INSERT OR REPLACE INTO daily_points (user_id, points, date)
                VALUES (?, COALESCE((SELECT points FROM daily_points WHERE user_id = ? AND date = CURRENT_DATE), 0) + ?, CURRENT_DATE)
            ''', (user_id, user_id, points))
            
            # Обновляем очки за неделю
            week_start = self._get_week_start()
            cursor.execute('''
                INSERT OR REPLACE INTO weekly_points (user_id, points, week_start)
                VALUES (?, COALESCE((SELECT points FROM weekly_points WHERE user_id = ? AND week_start = ?), 0) + ?, ?)
            ''', (user_id, user_id, week_start, points, week_start))
            
            # Обновляем очки за месяц
            month_start = self._get_month_start()
            cursor.execute('''
                INSERT OR REPLACE INTO monthly_points (user_id, points, month_start)
                VALUES (?, COALESCE((SELECT points FROM monthly_points WHERE user_id = ? AND month_start = ?), 0) + ?, ?)
            ''', (user_id, user_id, month_start, points, month_start))
            
            conn.commit()
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение статистики пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем общую информацию о пользователе
            cursor.execute('''
                SELECT username, first_name, last_name, created_at,
                       COALESCE((SELECT SUM(points) FROM daily_points WHERE user_id = ?), 0) as total_points,
                       COALESCE((SELECT points FROM daily_points WHERE user_id = ? AND date = CURRENT_DATE), 0) as today_points,
                       COALESCE((SELECT points FROM weekly_points WHERE user_id = ? AND week_start = ?), 0) as week_points,
                       COALESCE((SELECT points FROM monthly_points WHERE user_id = ? AND month_start = ?), 0) as month_points
                FROM users WHERE user_id = ?
            ''', (user_id, user_id, user_id, self._get_week_start(), user_id, self._get_month_start(), user_id))
            
            result = cursor.fetchone()
            if result:
                return {
                    'username': result[0],
                    'first_name': result[1],
                    'last_name': result[2],
                    'created_at': result[3],
                    'total_points': result[4],
                    'today_points': result[5],
                    'week_points': result[6],
                    'month_points': result[7]
                }
            return None
    
    def get_daily_top(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Получение топ пользователей за день"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.username, dp.points
                FROM daily_points dp
                JOIN users u ON dp.user_id = u.user_id
                WHERE dp.date = CURRENT_DATE
                ORDER BY dp.points DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def get_weekly_top(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Получение топ пользователей за неделю"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.username, wp.points
                FROM weekly_points wp
                JOIN users u ON wp.user_id = u.user_id
                WHERE wp.week_start = ?
                ORDER BY wp.points DESC
                LIMIT ?
            ''', (self._get_week_start(), limit))
            return cursor.fetchall()
    
    def get_monthly_top(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Получение топ пользователей за месяц"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.username, mp.points
                FROM monthly_points mp
                JOIN users u ON mp.user_id = u.user_id
                WHERE mp.month_start = ?
                ORDER BY mp.points DESC
                LIMIT ?
            ''', (self._get_month_start(), limit))
            return cursor.fetchall()
    
    def save_monthly_winner(self, user_id: int, username: str, points: int, month_start: str):
        """Сохранение победителя месяца"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO monthly_winners (user_id, username, points, month_start)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, points, month_start))
            conn.commit()
    
    def get_monthly_winners(self) -> List[Tuple[str, int, str]]:
        """Получение истории победителей месяцев"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, points, month_start
                FROM monthly_winners
                ORDER BY month_start DESC
                LIMIT 10
            ''')
            return cursor.fetchall()
    
    def get_previous_month_winner(self) -> Optional[Tuple[int, str, int]]:
        """Получение победителя предыдущего месяца"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем начало предыдущего месяца
            prev_month = self._get_previous_month_start()
            
            cursor.execute('''
                SELECT user_id, username, points
                FROM monthly_winners
                WHERE month_start = ?
                ORDER BY points DESC
                LIMIT 1
            ''', (prev_month,))
            
            result = cursor.fetchone()
            return result if result else None
    
    def _get_week_start(self) -> str:
        """Получение начала текущей недели (понедельник)"""
        today = datetime.date.today()
        days_since_monday = today.weekday()
        week_start = today - datetime.timedelta(days=days_since_monday)
        return week_start.isoformat()
    
    def _get_month_start(self) -> str:
        """Получение начала текущего месяца"""
        today = datetime.date.today()
        month_start = today.replace(day=1)
        return month_start.isoformat()
    
    def _get_previous_month_start(self) -> str:
        """Получение начала предыдущего месяца"""
        today = datetime.date.today()
        if today.month == 1:
            prev_month = today.replace(year=today.year - 1, month=12, day=1)
        else:
            prev_month = today.replace(month=today.month - 1, day=1)
        return prev_month.isoformat()

    def set_mute(self, user_id: int, until_timestamp: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO mutes (user_id, until_timestamp)
                VALUES (?, ?)
            ''', (user_id, until_timestamp))
            conn.commit()

    def get_mute(self, user_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT until_timestamp FROM mutes WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def clear_expired_mutes(self):
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM mutes WHERE until_timestamp <= ?', (now,))
            conn.commit()

    def is_muted(self, user_id: int) -> int:
        # Возвращает оставшееся время мута в секундах, если есть, иначе 0
        until = self.get_mute(user_id)
        now = int(time.time())
        return max(0, until - now) 