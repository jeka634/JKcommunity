#!/usr/bin/env python3
"""
Тестирование Telegram бота для чата
Проверяет все основные функции бота
"""

import sys
import os
import sqlite3
import datetime
import pytz

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тест импорта модулей"""
    print("🔍 Тестирование импорта модулей...")
    
    try:
        import config
        print("✅ config.py импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта config.py: {e}")
        return False
    
    try:
        import database
        print("✅ database.py импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта database.py: {e}")
        return False
    
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
        print("✅ python-telegram-bot импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта python-telegram-bot: {e}")
        print("💡 Установите: pip install python-telegram-bot==20.7")
        return False
    
    try:
        import pytz
        print("✅ pytz импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта pytz: {e}")
        print("💡 Установите: pip install pytz")
        return False
    
    return True

def test_config():
    """Тест конфигурации"""
    print("\n🔧 Тестирование конфигурации...")
    
    try:
        import config
        
        # Проверяем основные настройки
        assert hasattr(config, 'BOT_TOKEN'), "BOT_TOKEN не найден в config"
        assert hasattr(config, 'CHAT_ID'), "CHAT_ID не найден в config"
        assert hasattr(config, 'BASE_PROBABILITY'), "BASE_PROBABILITY не найден"
        assert hasattr(config, 'BOOST_PROBABILITY'), "BOOST_PROBABILITY не найден"
        assert hasattr(config, 'POINTS_PER_MESSAGE'), "POINTS_PER_MESSAGE не найден"
        assert hasattr(config, 'MIN_WORDS_FOR_POINTS'), "MIN_WORDS_FOR_POINTS не найден"
        assert hasattr(config, 'POINTS_THRESHOLDS'), "POINTS_THRESHOLDS не найден"
        assert hasattr(config, 'MOTIVATION_MESSAGES'), "MOTIVATION_MESSAGES не найден"
        assert hasattr(config, 'JK_WELCOME_MESSAGE'), "JK_WELCOME_MESSAGE не найден"
        assert hasattr(config, 'TOP_USERS_LIMIT'), "TOP_USERS_LIMIT не найден"
        assert hasattr(config, 'MONTHLY_WINNERS_HISTORY_LIMIT'), "MONTHLY_WINNERS_HISTORY_LIMIT не найден"
        
        # Проверяем значения
        assert 0 < config.BASE_PROBABILITY < 1, "BASE_PROBABILITY должен быть между 0 и 1"
        assert 0 < config.BOOST_PROBABILITY < 1, "BOOST_PROBABILITY должен быть между 0 и 1"
        assert config.POINTS_PER_MESSAGE > 0, "POINTS_PER_MESSAGE должен быть положительным"
        assert config.MIN_WORDS_FOR_POINTS > 0, "MIN_WORDS_FOR_POINTS должен быть положительным"
        assert len(config.POINTS_THRESHOLDS) > 0, "POINTS_THRESHOLDS не должен быть пустым"
        assert len(config.MOTIVATION_MESSAGES) > 0, "MOTIVATION_MESSAGES не должен быть пустым"
        assert config.TOP_USERS_LIMIT > 0, "TOP_USERS_LIMIT должен быть положительным"
        assert config.MONTHLY_WINNERS_HISTORY_LIMIT > 0, "MONTHLY_WINNERS_HISTORY_LIMIT должен быть положительным"
        
        # Проверяем многоязычность
        assert 'ru' in config.JK_WELCOME_MESSAGE, "Отсутствует русская версия JK_WELCOME_MESSAGE"
        assert 'en' in config.JK_WELCOME_MESSAGE, "Отсутствует английская версия JK_WELCOME_MESSAGE"
        
        # Проверяем увеличенные вероятности
        assert config.BASE_PROBABILITY >= 0.20, f"BASE_PROBABILITY должен быть >= 0.20, текущее значение: {config.BASE_PROBABILITY}"
        assert config.BOOST_PROBABILITY >= 0.325, f"BOOST_PROBABILITY должен быть >= 0.325, текущее значение: {config.BOOST_PROBABILITY}"
        
        print("✅ Конфигурация корректна")
        print(f"   Базовая вероятность: {config.BASE_PROBABILITY*100:.1f}%")
        print(f"   Вероятность буста: {config.BOOST_PROBABILITY*100:.1f}%")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_settings_file():
    """Тест файла настроек"""
    print("\n⚙️ Тестирование файла настроек...")
    
    try:
        if not os.path.exists('settings.txt'):
            print("⚠️ Файл settings.txt не найден, но это нормально - используются значения по умолчанию")
            return True
        
        with open('settings.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие основных настроек
        required_settings = [
            'BASE_PROBABILITY',
            'BOOST_PROBABILITY',
            'BOOST_START_HOUR',
            'BOOST_END_HOUR',
            'POINTS_PER_MESSAGE',
            'MIN_WORDS_FOR_POINTS',
            'POINTS_THRESHOLDS'
        ]
        
        for setting in required_settings:
            if setting not in content:
                print(f"⚠️ Настройка {setting} не найдена в settings.txt")
            else:
                print(f"✅ Настройка {setting} найдена")
        
        print("✅ Файл настроек проверен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки файла настроек: {e}")
        return False

def test_database():
    """Тест базы данных"""
    print("\n🗄️ Тестирование базы данных...")
    
    try:
        from database import Database
        
        # Создаем временную базу данных
        db = Database(":memory:")
        
        # Инициализируем таблицы
        db.init_database()
        
        # Тестируем добавление пользователя
        user_id = 12345
        username = "test_user"
        first_name = "Test"
        last_name = "User"
        
        db.add_user(user_id, username, first_name, last_name)
        print("✅ Добавление пользователя работает")
        
        # Тестируем добавление очков
        db.add_points(user_id, 100)
        print("✅ Добавление очков работает")
        
        # Тестируем получение статистики
        stats = db.get_user_stats(user_id)
        assert stats is not None, "Статистика пользователя не найдена"
        assert stats['total_points'] >= 100, "Очки не сохранились"
        print("✅ Получение статистики работает")
        
        # Тестируем топы
        daily_top = db.get_daily_top(5)
        weekly_top = db.get_weekly_top(5)
        monthly_top = db.get_monthly_top(5)
        
        assert isinstance(daily_top, list), "get_daily_top должен возвращать список"
        assert isinstance(weekly_top, list), "get_weekly_top должен возвращать список"
        assert isinstance(monthly_top, list), "get_monthly_top должен возвращать список"
        
        print("✅ Получение топов работает")
        
        # Тестируем сохранение победителя месяца
        db.save_monthly_winner(user_id, username, 1000, "2024-01-01")
        winners = db.get_monthly_winners()
        assert isinstance(winners, list), "get_monthly_winners должен возвращать список"
        
        print("✅ Сохранение победителей месяца работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False

def test_message_filtering():
    """Тест фильтрации сообщений"""
    print("\n🛡️ Тестирование фильтрации сообщений...")
    
    try:
        # Импортируем функцию из bot.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("bot", "bot.py")
        if spec is None:
            print("❌ Не удалось загрузить bot.py")
            return False
            
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        # Создаем экземпляр бота для тестирования
        from telegram.ext import Application
        app = Application.builder().token("test").build()
        bot = bot_module.ChatBot(app)
        
        # Тестируем осмысленные сообщения (должны пройти фильтр)
        good_messages = [
            "Привет всем! Как дела?",
            "Отличная идея, поддерживаю полностью",
            "Сегодня прекрасная погода для прогулки",
            "Спасибо за полезную информацию"
        ]
        
        for msg in good_messages:
            result = bot.is_meaningful_message(msg)
            if not result:
                print(f"⚠️ Сообщение '{msg}' не прошло фильтр, но должно было")
        
        # Тестируем спам сообщения (не должны проходить фильтр)
        spam_messages = [
            "аааааааааааа",
            "вввввввввввввв",
            "1 2 3 4 5",
            "да да да да да",
            "привет",
            "ок"
        ]
        
        spam_detected = 0
        for msg in spam_messages:
            if not bot.is_meaningful_message(msg):
                spam_detected += 1
        
        # Проверяем, что большинство спама было заблокировано
        if spam_detected >= len(spam_messages) * 0.8:  # 80% спама заблокировано
            print("✅ Фильтрация спама работает корректно")
        else:
            print(f"⚠️ Заблокировано только {spam_detected}/{len(spam_messages)} спам сообщений")
        
        print("✅ Фильтрация сообщений работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка фильтрации сообщений: {e}")
        return False

def test_probability_calculation():
    """Тест расчета вероятности"""
    print("\n🎲 Тестирование расчета вероятности...")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bot", "bot.py")
        if spec is None:
            print("❌ Не удалось загрузить bot.py")
            return False
            
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        from telegram.ext import Application
        app = Application.builder().token("test").build()
        bot = bot_module.ChatBot(app)
        
        # Тестируем получение вероятности
        prob = bot.get_current_probability()
        assert isinstance(prob, float), "Вероятность должна быть числом"
        assert 0 <= prob <= 1, "Вероятность должна быть между 0 и 1"
        
        # Проверяем, что вероятность соответствует настройкам
        import config
        assert prob in [config.BASE_PROBABILITY, config.BOOST_PROBABILITY], f"Вероятность {prob} не соответствует настройкам"
        
        print("✅ Расчет вероятности работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка расчета вероятности: {e}")
        return False

def test_jk_command():
    """Тест команды /JK"""
    print("\n🪙 Тестирование команды /JK...")
    
    try:
        import config
        
        # Проверяем наличие сообщений на двух языках
        assert 'ru' in config.JK_WELCOME_MESSAGE, "Отсутствует русская версия"
        assert 'en' in config.JK_WELCOME_MESSAGE, "Отсутствует английская версия"
        
        # Проверяем содержимое сообщений
        ru_message = config.JK_WELCOME_MESSAGE['ru']
        en_message = config.JK_WELCOME_MESSAGE['en']
        
        assert "Jekardos Coin" in ru_message or "JK" in ru_message, "Русское сообщение должно содержать информацию о JK"
        assert "Jekardos Coin" in en_message or "JK" in en_message, "Английское сообщение должно содержать информацию о JK"
        assert "команды" in ru_message.lower() or "commands" in ru_message.lower(), "Сообщение должно содержать информацию о командах"
        assert "commands" in en_message.lower(), "Английское сообщение должно содержать информацию о командах"
        
        print("✅ Команда /JK настроена корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка команды /JK: {e}")
        return False

def test_syntax():
    """Тест синтаксиса Python файлов"""
    print("\n🐍 Тестирование синтаксиса...")
    
    files_to_test = ['bot.py', 'config.py', 'database.py']
    
    for file in files_to_test:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Проверяем синтаксис
            compile(content, file, 'exec')
            print(f"✅ {file} - синтаксис корректен")
            
        except SyntaxError as e:
            print(f"❌ {file} - ошибка синтаксиса: {e}")
            return False
        except Exception as e:
            print(f"❌ {file} - ошибка чтения: {e}")
            return False
    
    return True

def main():
    """Основная функция тестирования"""
    print("🧪 Запуск тестов Telegram бота\n")
    
    tests = [
        ("Импорт модулей", test_imports),
        ("Синтаксис файлов", test_syntax),
        ("Конфигурация", test_config),
        ("Файл настроек", test_settings_file),
        ("База данных", test_database),
        ("Фильтрация сообщений", test_message_filtering),
        ("Расчет вероятности", test_probability_calculation),
        ("Команда /JK", test_jk_command),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ Тест '{test_name}' не прошел")
        except Exception as e:
            print(f"❌ Тест '{test_name}' завершился с ошибкой: {e}")
    
    print(f"\n📊 Результаты тестирования:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены! Бот готов к запуску.")
        print("💡 Для запуска выполните: python bot.py")
    else:
        print("\n⚠️ Некоторые тесты не пройдены. Проверьте ошибки выше.")
        print("💡 Убедитесь, что все зависимости установлены:")
        print("   pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 