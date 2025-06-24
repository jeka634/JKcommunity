import re
import logging
from typing import Dict, List, Set, Optional
import json

class MessageValidator:
    def __init__(self):
        self.spam_patterns = [
            r'^[0-9]+$',  # Только цифры
            r'^[a-zA-Z0-9]{20,}$',  # Длинные случайные строки
            r'^[a-z]{2,}\1{3,}$',  # Повторяющиеся символы
            r'^[а-яё]{2,}\1{3,}$',  # Повторяющиеся русские символы
            r'^[a-zA-Z]{1,2}[0-9]{10,}$',  # Короткие буквы + много цифр
            r'^[а-яё]{1,2}[0-9]{10,}$',  # Короткие русские буквы + много цифр
            r'^[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]{5,}$',  # Много спецсимволов
            r'^[а-яё]{1,3}[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]{3,}$',  # Русские буквы + спецсимволы
        ]
        
        self.min_length = 3
        self.max_length = 1000
        
        # Слова-индикаторы осмысленности
        self.meaningful_words = {
            'ru': {
                'вопросы': ['что', 'как', 'где', 'когда', 'почему', 'зачем', 'кто', 'какой', 'какая', 'какие'],
                'действия': ['делаю', 'работаю', 'учусь', 'читаю', 'смотрю', 'слушаю', 'иду', 'еду', 'летаю'],
                'эмоции': ['нравится', 'люблю', 'радуюсь', 'грущу', 'злюсь', 'удивляюсь', 'боюсь'],
                'время': ['сегодня', 'завтра', 'вчера', 'утром', 'вечером', 'ночью', 'днем'],
                'места': ['дом', 'работа', 'университет', 'школа', 'магазин', 'кафе', 'ресторан'],
                'общие': ['хорошо', 'плохо', 'интересно', 'сложно', 'легко', 'быстро', 'медленно']
            },
            'en': {
                'questions': ['what', 'how', 'where', 'when', 'why', 'who', 'which'],
                'actions': ['doing', 'working', 'studying', 'reading', 'watching', 'listening', 'going'],
                'emotions': ['like', 'love', 'happy', 'sad', 'angry', 'surprised', 'afraid'],
                'time': ['today', 'tomorrow', 'yesterday', 'morning', 'evening', 'night'],
                'places': ['home', 'work', 'university', 'school', 'shop', 'cafe', 'restaurant'],
                'general': ['good', 'bad', 'interesting', 'difficult', 'easy', 'fast', 'slow']
            }
        }
        
        # Слова-индикаторы спама
        self.spam_words = {
            'ru': [
                'спам', 'реклама', 'купить', 'продать', 'заработок', 'деньги', 'бонус', 'приз',
                'выигрыш', 'лотерея', 'казино', 'ставки', 'кредит', 'займ', 'микрозайм',
                'работа на дому', 'подработка', 'доход', 'прибыль', 'инвестиции'
            ],
            'en': [
                'spam', 'advertisement', 'buy', 'sell', 'earnings', 'money', 'bonus', 'prize',
                'win', 'lottery', 'casino', 'betting', 'credit', 'loan', 'microloan',
                'work from home', 'part-time', 'income', 'profit', 'investment'
            ]
        }
    
    def validate_message(self, message: str, user_id: Optional[int] = None) -> Dict:
        """
        Валидация сообщения на осмысленность
        
        Returns:
            Dict с ключами:
            - is_valid: bool - прошло ли сообщение валидацию
            - reason: str - причина отклонения (если есть)
            - score: float - оценка осмысленности (0-1)
        """
        try:
            # Проверка длины
            if len(message.strip()) < self.min_length:
                return {
                    'is_valid': False,
                    'reason': f'Сообщение слишком короткое (минимум {self.min_length} символов)',
                    'score': 0.0
                }
            
            if len(message) > self.max_length:
                return {
                    'is_valid': False,
                    'reason': f'Сообщение слишком длинное (максимум {self.max_length} символов)',
                    'score': 0.0
                }
            
            # Проверка на спам-паттерны
            for pattern in self.spam_patterns:
                if re.match(pattern, message.strip()):
                    return {
                        'is_valid': False,
                        'reason': 'Сообщение содержит спам-паттерн',
                        'score': 0.0
                    }
            
            # Проверка на повторяющиеся символы
            if self._has_repeating_chars(message):
                return {
                    'is_valid': False,
                    'reason': 'Сообщение содержит много повторяющихся символов',
                    'score': 0.0
                }
            
            # Проверка на спам-слова
            spam_score = self._check_spam_words(message)
            if spam_score > 0.7:
                return {
                    'is_valid': False,
                    'reason': 'Сообщение содержит спам-слова',
                    'score': 0.0
                }
            
            # Оценка осмысленности
            meaningful_score = self._calculate_meaningful_score(message)
            
            # Финальная оценка
            final_score = meaningful_score * (1 - spam_score)
            
            return {
                'is_valid': final_score > 0.3,
                'reason': None if final_score > 0.3 else 'Сообщение недостаточно осмысленное',
                'score': final_score
            }
            
        except Exception as e:
            logging.error(f"Error validating message: {e}")
            return {
                'is_valid': False,
                'reason': 'Ошибка при валидации сообщения',
                'score': 0.0
            }
    
    def _has_repeating_chars(self, message: str) -> bool:
        """Проверка на повторяющиеся символы"""
        if len(message) < 5:
            return False
        
        # Проверка на повторяющиеся символы подряд
        for i in range(len(message) - 2):
            if message[i] == message[i+1] == message[i+2]:
                return True
        
        # Проверка на повторяющиеся паттерны
        for pattern_length in range(2, 5):
            for i in range(len(message) - pattern_length * 2):
                pattern = message[i:i+pattern_length]
                if pattern in message[i+pattern_length:]:
                    return True
        
        return False
    
    def _check_spam_words(self, message: str) -> float:
        """Проверка на спам-слова"""
        message_lower = message.lower()
        total_spam_count = 0
        
        for lang, words in self.spam_words.items():
            for word in words:
                if word in message_lower:
                    total_spam_count += 1
        
        # Нормализация по длине сообщения
        words_in_message = len(message.split())
        if words_in_message == 0:
            return 0.0
        
        return min(total_spam_count / words_in_message, 1.0)
    
    def _calculate_meaningful_score(self, message: str) -> float:
        """Расчет оценки осмысленности сообщения"""
        message_lower = message.lower()
        meaningful_count = 0
        total_words = len(message.split())
        
        if total_words == 0:
            return 0.0
        
        # Подсчет осмысленных слов
        for lang, categories in self.meaningful_words.items():
            for category, words in categories.items():
                for word in words:
                    if word in message_lower:
                        meaningful_count += 1
        
        # Бонус за наличие знаков препинания
        punctuation_bonus = 0
        if any(char in message for char in '.,!?;:'):
            punctuation_bonus = 0.1
        
        # Бонус за наличие заглавных букв (но не все заглавные)
        if message != message.upper() and any(char.isupper() for char in message):
            punctuation_bonus += 0.05
        
        # Бонус за разнообразие символов
        unique_chars = len(set(message.lower()))
        diversity_bonus = min(unique_chars / len(message), 0.2)
        
        # Базовая оценка
        base_score = meaningful_count / total_words
        
        # Финальная оценка с бонусами
        final_score = min(base_score + punctuation_bonus + diversity_bonus, 1.0)
        
        return final_score
    
    def is_question(self, message: str) -> bool:
        """Проверка, является ли сообщение вопросом"""
        question_indicators = [
            '?', 'что', 'как', 'где', 'когда', 'почему', 'зачем', 'кто', 'какой',
            'what', 'how', 'where', 'when', 'why', 'who', 'which'
        ]
        
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in question_indicators)
    
    def get_message_category(self, message: str) -> str:
        """Определение категории сообщения"""
        message_lower = message.lower()
        
        # Вопросы
        if self.is_question(message):
            return 'question'
        
        # Приветствия
        greetings = ['привет', 'здравствуй', 'добрый день', 'доброе утро', 'добрый вечер',
                    'hello', 'hi', 'good morning', 'good evening', 'good afternoon']
        if any(greeting in message_lower for greeting in greetings):
            return 'greeting'
        
        # Прощания
        farewells = ['пока', 'до свидания', 'до встречи', 'увидимся', 'прощай',
                    'bye', 'goodbye', 'see you', 'farewell']
        if any(farewell in message_lower for farewell in farewells):
            return 'farewell'
        
        # Благодарности
        thanks = ['спасибо', 'благодарю', 'thank you', 'thanks']
        if any(thank in message_lower for thank in thanks):
            return 'thanks'
        
        # Эмоции
        emotions = ['рад', 'счастлив', 'грустно', 'злюсь', 'удивлен', 'боюсь',
                   'happy', 'sad', 'angry', 'surprised', 'afraid']
        if any(emotion in message_lower for emotion in emotions):
            return 'emotion'
        
        return 'general' 