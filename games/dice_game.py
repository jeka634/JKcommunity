import random
import uuid
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class DiceGame:
    def __init__(self, database):
        self.db = database
        self.active_games = {}  # game_id -> game_data
        self.min_bet = 1.0
        self.max_bet = 1000.0
    
    def create_game(self, player1_id: int, player2_id: int, bet_amount: float) -> Optional[str]:
        """Создание новой игры в кости"""
        try:
            # Проверка ставки
            if not self.min_bet <= bet_amount <= self.max_bet:
                return None
            
            # Проверка балансов игроков
            player1 = self.db.get_user(player1_id)
            player2 = self.db.get_user(player2_id)
            
            if not player1 or not player2:
                return None
            
            if player1['gasjk_balance'] < bet_amount or player2['gasjk_balance'] < bet_amount:
                return None
            
            # Создание уникального ID игры
            game_id = str(uuid.uuid4())
            
            # Создание игры в базе данных
            if self.db.add_dice_game(game_id, player1_id, player2_id, bet_amount):
                # Сохранение в активные игры
                self.active_games[game_id] = {
                    'player1_id': player1_id,
                    'player2_id': player2_id,
                    'bet_amount': bet_amount,
                    'player1_dice': None,
                    'player2_dice': None,
                    'status': 'waiting',
                    'created_at': datetime.now()
                }
                
                # Списывание ставок с балансов
                self.db.update_user_balance(player1_id, -bet_amount)
                self.db.update_user_balance(player2_id, -bet_amount)
                
                return game_id
            
            return None
            
        except Exception as e:
            logging.error(f"Error creating dice game: {e}")
            return None
    
    def roll_dice(self, game_id: str, player_id: int) -> Optional[Dict]:
        """Бросок костей игроком"""
        try:
            if game_id not in self.active_games:
                return None
            
            game = self.active_games[game_id]
            
            # Проверка, что игрок участвует в игре
            if player_id not in [game['player1_id'], game['player2_id']]:
                return None
            
            # Проверка, что игра еще активна
            if game['status'] != 'waiting':
                return None
            
            # Бросок костей (1-6)
            dice_result = random.randint(1, 6)
            
            # Сохранение результата
            if player_id == game['player1_id']:
                game['player1_dice'] = dice_result
            else:
                game['player2_dice'] = dice_result
            
            # Проверка, бросили ли оба игрока
            if game['player1_dice'] is not None and game['player2_dice'] is not None:
                return self._finish_game(game_id)
            
            return {
                'game_id': game_id,
                'player_id': player_id,
                'dice_result': dice_result,
                'status': 'waiting_for_opponent'
            }
            
        except Exception as e:
            logging.error(f"Error rolling dice: {e}")
            return None
    
    def _finish_game(self, game_id: str) -> Optional[Dict]:
        """Завершение игры и определение победителя"""
        try:
            game = self.active_games[game_id]
            
            # Определение победителя
            if game['player1_dice'] > game['player2_dice']:
                winner_id = game['player1_id']
                loser_id = game['player2_id']
            elif game['player2_dice'] > game['player1_dice']:
                winner_id = game['player2_id']
                loser_id = game['player1_id']
            else:
                # Ничья - возвращаем ставки
                self.db.update_user_balance(game['player1_id'], game['bet_amount'])
                self.db.update_user_balance(game['player2_id'], game['bet_amount'])
                
                # Обновление статуса игры
                game['status'] = 'draw'
                self.db.update_dice_game_result(game_id, game['player1_dice'], 
                                              game['player2_dice'], None)
                
                return {
                    'game_id': game_id,
                    'status': 'draw',
                    'player1_dice': game['player1_dice'],
                    'player2_dice': game['player2_dice'],
                    'winner_id': None
                }
            
            # Начисление выигрыша победителю
            total_pot = game['bet_amount'] * 2
            self.db.update_user_balance(winner_id, total_pot)
            
            # Обновление статуса игры
            game['status'] = 'completed'
            self.db.update_dice_game_result(game_id, game['player1_dice'], 
                                          game['player2_dice'], winner_id)
            
            # Добавление транзакций
            self.db.add_transaction(game['player1_id'], winner_id, game['bet_amount'], 'dice_game')
            self.db.add_transaction(game['player2_id'], winner_id, game['bet_amount'], 'dice_game')
            
            return {
                'game_id': game_id,
                'status': 'completed',
                'player1_dice': game['player1_dice'],
                'player2_dice': game['player2_dice'],
                'winner_id': winner_id,
                'total_pot': total_pot
            }
            
        except Exception as e:
            logging.error(f"Error finishing game: {e}")
            return None
    
    def get_game_status(self, game_id: str) -> Optional[Dict]:
        """Получение статуса игры"""
        try:
            if game_id not in self.active_games:
                return None
            
            game = self.active_games[game_id]
            return {
                'game_id': game_id,
                'player1_id': game['player1_id'],
                'player2_id': game['player2_id'],
                'bet_amount': game['bet_amount'],
                'player1_dice': game['player1_dice'],
                'player2_dice': game['player2_dice'],
                'status': game['status'],
                'created_at': game['created_at']
            }
        except Exception as e:
            logging.error(f"Error getting game status: {e}")
            return None
    
    def get_player_games(self, player_id: int, limit: int = 10) -> List[Dict]:
        """Получение игр игрока"""
        try:
            # Получение из базы данных
            with self.db.db_path as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM dice_games 
                    WHERE player1_id = ? OR player2_id = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (player_id, player_id, limit))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error getting player games: {e}")
            return []
    
    def cancel_game(self, game_id: str, player_id: int) -> bool:
        """Отмена игры (если второй игрок еще не бросил кости)"""
        try:
            if game_id not in self.active_games:
                return False
            
            game = self.active_games[game_id]
            
            # Проверка, что игрок участвует в игре
            if player_id not in [game['player1_id'], game['player2_id']]:
                return False
            
            # Проверка, что игра еще активна
            if game['status'] != 'waiting':
                return False
            
            # Возврат ставок
            self.db.update_user_balance(game['player1_id'], game['bet_amount'])
            self.db.update_user_balance(game['player2_id'], game['bet_amount'])
            
            # Удаление игры
            del self.active_games[game_id]
            
            return True
            
        except Exception as e:
            logging.error(f"Error canceling game: {e}")
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Получение таблицы лидеров по выигрышам"""
        try:
            with self.db.db_path as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.last_name,
                        COUNT(CASE WHEN dg.winner_id = u.user_id THEN 1 END) as wins,
                        COUNT(CASE WHEN dg.winner_id != u.user_id AND dg.winner_id IS NOT NULL THEN 1 END) as losses,
                        SUM(CASE WHEN dg.winner_id = u.user_id THEN dg.bet_amount ELSE 0 END) as total_winnings
                    FROM users u
                    LEFT JOIN dice_games dg ON (u.user_id = dg.player1_id OR u.user_id = dg.player2_id)
                    WHERE dg.status = 'completed'
                    GROUP BY u.user_id
                    ORDER BY total_winnings DESC, wins DESC
                    LIMIT ?
                ''', (limit,))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Error getting leaderboard: {e}")
            return []
    
    def get_game_statistics(self) -> Dict:
        """Получение статистики игр"""
        try:
            with self.db.db_path as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_games,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_games,
                        COUNT(CASE WHEN status = 'draw' THEN 1 END) as draw_games,
                        SUM(bet_amount) as total_bets
                    FROM dice_games
                ''')
                row = cursor.fetchone()
                
                # Статистика по дням
                cursor.execute('''
                    SELECT 
                        DATE(created_at) as game_date,
                        COUNT(*) as games_count,
                        SUM(bet_amount) as total_bets
                    FROM dice_games
                    WHERE created_at >= DATE('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY game_date DESC
                ''')
                daily_stats = cursor.fetchall()
                
                return {
                    'total_games': row[0] or 0,
                    'completed_games': row[1] or 0,
                    'draw_games': row[2] or 0,
                    'total_bets': row[3] or 0,
                    'daily_stats': daily_stats
                }
        except Exception as e:
            logging.error(f"Error getting game statistics: {e}")
            return {
                'total_games': 0,
                'completed_games': 0,
                'draw_games': 0,
                'total_bets': 0,
                'daily_stats': []
            } 