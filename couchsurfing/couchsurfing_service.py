import logging
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
import sqlite3

class CouchsurfingService:
    def __init__(self, database):
        self.db = database
    
    def create_ad(self, user_id: int, country: str, city: str, settlement: str, 
                  start_date: str, end_date: str, description: str) -> int:
        """Создание объявления о приеме гостей"""
        try:
            # Валидация дат
            if not self._validate_dates(start_date, end_date):
                return -1
            
            # Создание объявления
            ad_id = self.db.add_couchsurfing_ad(
                user_id, country, city, settlement, start_date, end_date, description
            )
            
            return ad_id
            
        except Exception as e:
            logging.error(f"Error creating ad: {e}")
            return -1
    
    def get_ads(self, country: Optional[str] = None, city: Optional[str] = None, 
                settlement: Optional[str] = None, date_from: Optional[str] = None,
                date_to: Optional[str] = None) -> List[Dict]:
        """Получение объявлений с фильтрацией"""
        try:
            ads = self.db.get_couchsurfing_ads(country, city, settlement)
            
            # Фильтрация по датам
            if date_from or date_to:
                filtered_ads = []
                for ad in ads:
                    if self._is_ad_available_in_period(ad, date_from, date_to):
                        filtered_ads.append(ad)
                ads = filtered_ads
            
            # Добавление информации о пользователе
            for ad in ads:
                user = self.db.get_user(ad['user_id'])
                if user:
                    ad['host_name'] = user.get('first_name', '') + ' ' + user.get('last_name', '')
                    ad['host_username'] = user.get('username', '')
            
            return ads
            
        except Exception as e:
            logging.error(f"Error getting ads: {e}")
            return []
    
    def create_booking(self, guest_id: int, ad_id: int, start_date: str, end_date: str) -> int:
        """Создание бронирования"""
        try:
            # Получение объявления
            ads = self.db.get_couchsurfing_ads()
            ad = next((a for a in ads if a['id'] == ad_id), None)
            
            if not ad:
                return -1
            
            # Проверка доступности
            if not self._is_ad_available_in_period(ad, start_date, end_date):
                return -1
            
            # Проверка, что гость не бронирует у себя
            if guest_id == ad['user_id']:
                return -1
            
            # Создание бронирования
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bookings (guest_id, host_id, ad_id, start_date, end_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (guest_id, ad['user_id'], ad_id, start_date, end_date))
                conn.commit()
                result = cursor.lastrowid
                return result if result is not None else -1
                
        except Exception as e:
            logging.error(f"Error creating booking: {e}")
            return -1
    
    def get_user_bookings(self, user_id: int, as_guest: bool = True) -> List[Dict]:
        """Получение бронирований пользователя"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                if as_guest:
                    cursor.execute('''
                        SELECT b.*, ca.country, ca.city, ca.settlement, ca.description,
                               u.first_name, u.last_name, u.username
                        FROM bookings b
                        JOIN couchsurfing_ads ca ON b.ad_id = ca.id
                        JOIN users u ON b.host_id = u.user_id
                        WHERE b.guest_id = ?
                        ORDER BY b.created_at DESC
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        SELECT b.*, ca.country, ca.city, ca.settlement, ca.description,
                               u.first_name, u.last_name, u.username
                        FROM bookings b
                        JOIN couchsurfing_ads ca ON b.ad_id = ca.id
                        JOIN users u ON b.guest_id = u.user_id
                        WHERE b.host_id = ?
                        ORDER BY b.created_at DESC
                    ''', (user_id,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logging.error(f"Error getting user bookings: {e}")
            return []
    
    def update_booking_status(self, booking_id: int, status: str) -> bool:
        """Обновление статуса бронирования"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE bookings SET status = ? WHERE id = ?
                ''', (status, booking_id))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logging.error(f"Error updating booking status: {e}")
            return False
    
    def rate_host(self, booking_id: int, rating: float, comment: str = "") -> bool:
        """Оценка хоста после пребывания"""
        try:
            if not 1.0 <= rating <= 5.0:
                return False
            
            # Получение бронирования
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT host_id, ad_id FROM bookings WHERE id = ?', (booking_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                host_id, ad_id = row
                
                # Обновление рейтинга объявления
                cursor.execute('''
                    UPDATE couchsurfing_ads 
                    SET rating = (rating + ?) / 2 
                    WHERE id = ?
                ''', (rating, ad_id))
                
                # Добавление комментария (можно создать отдельную таблицу для отзывов)
                conn.commit()
                return True
                
        except Exception as e:
            logging.error(f"Error rating host: {e}")
            return False
    
    def get_popular_destinations(self, limit: int = 10) -> List[Dict]:
        """Получение популярных направлений"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        country,
                        city,
                        COUNT(*) as ads_count,
                        AVG(rating) as avg_rating
                    FROM couchsurfing_ads
                    WHERE status = 'active'
                    GROUP BY country, city
                    ORDER BY ads_count DESC, avg_rating DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logging.error(f"Error getting popular destinations: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Статистика как хост
                cursor.execute('''
                    SELECT 
                        COUNT(*) as ads_count,
                        AVG(rating) as avg_rating,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_ads
                    FROM couchsurfing_ads
                    WHERE user_id = ?
                ''', (user_id,))
                host_stats = cursor.fetchone()
                
                # Статистика как гость
                cursor.execute('''
                    SELECT COUNT(*) as bookings_count
                    FROM bookings
                    WHERE guest_id = ?
                ''', (user_id,))
                guest_stats = cursor.fetchone()
                
                return {
                    'host_ads_count': host_stats[0] or 0,
                    'host_avg_rating': host_stats[1] or 0.0,
                    'host_active_ads': host_stats[2] or 0,
                    'guest_bookings_count': guest_stats[0] or 0
                }
                
        except Exception as e:
            logging.error(f"Error getting user stats: {e}")
            return {
                'host_ads_count': 0,
                'host_avg_rating': 0.0,
                'host_active_ads': 0,
                'guest_bookings_count': 0
            }
    
    def _validate_dates(self, start_date: str, end_date: str) -> bool:
        """Валидация дат"""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Проверка, что даты в будущем
            if start < date.today():
                return False
            
            # Проверка, что конечная дата после начальной
            if end <= start:
                return False
            
            # Проверка, что период не слишком длинный (например, не более года)
            if (end - start).days > 365:
                return False
            
            return True
            
        except ValueError:
            return False
    
    def _is_ad_available_in_period(self, ad: Dict, date_from: Optional[str] = None, 
                                  date_to: Optional[str] = None) -> bool:
        """Проверка доступности объявления в указанный период"""
        try:
            ad_start = datetime.strptime(ad['start_date'], '%Y-%m-%d').date()
            ad_end = datetime.strptime(ad['end_date'], '%Y-%m-%d').date()
            
            if date_from:
                requested_start = datetime.strptime(date_from, '%Y-%m-%d').date()
                if requested_start < ad_start:
                    return False
            
            if date_to:
                requested_end = datetime.strptime(date_to, '%Y-%m-%d').date()
                if requested_end > ad_end:
                    return False
            
            # Проверка существующих бронирований
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM bookings 
                    WHERE ad_id = ? AND status IN ('pending', 'confirmed')
                ''', (ad['id'],))
                existing_bookings = cursor.fetchone()[0]
                
                # Простая проверка - если есть бронирования, считаем недоступным
                # В реальном проекте нужно проверять пересечения дат
                return existing_bookings == 0
                
        except Exception as e:
            logging.error(f"Error checking ad availability: {e}")
            return False
    
    def search_ads(self, query: str) -> List[Dict]:
        """Поиск объявлений по тексту"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM couchsurfing_ads
                    WHERE status = 'active' AND (
                        country LIKE ? OR 
                        city LIKE ? OR 
                        settlement LIKE ? OR 
                        description LIKE ?
                    )
                    ORDER BY created_at DESC
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logging.error(f"Error searching ads: {e}")
            return [] 