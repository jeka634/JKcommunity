# 🚀 Руководство по развертыванию

## 📋 Подготовка к развертыванию

### 1. Требования к системе

#### Минимальные требования:
- **CPU:** 1 ядро
- **RAM:** 512 MB
- **Storage:** 1 GB
- **OS:** Linux (Ubuntu 18.04+), Windows 10+, macOS 10.14+

#### Рекомендуемые требования:
- **CPU:** 2+ ядра
- **RAM:** 2+ GB
- **Storage:** 5+ GB SSD
- **Network:** Стабильное интернет-соединение

### 2. Необходимые компоненты

#### Обязательно:
- Python 3.8+
- pip (менеджер пакетов Python)
- Git
- SQLite3

#### Дополнительно:
- Nginx (для веб-интерфейса)
- Supervisor (для управления процессами)
- Docker (опционально)

## 🖥️ Локальное развертывание

### 1. Установка на Windows

#### Шаг 1: Установка Python
```bash
# Скачайте Python с официального сайта
# https://www.python.org/downloads/
# Убедитесь, что отмечена опция "Add Python to PATH"
```

#### Шаг 2: Клонирование репозитория
```bash
git clone <repository-url>
cd JKcommunity
```

#### Шаг 3: Установка зависимостей
```bash
pip install -r requirements.txt
```

#### Шаг 4: Настройка конфигурации
```bash
copy config.env.example config.env
# Отредактируйте config.env в любом текстовом редакторе
```

#### Шаг 5: Запуск бота
```bash
python main.py
```

### 2. Установка на macOS

#### Шаг 1: Установка Homebrew (если не установлен)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Шаг 2: Установка Python
```bash
brew install python
```

#### Шаг 3: Клонирование и установка
```bash
git clone <repository-url>
cd JKcommunity
pip3 install -r requirements.txt
cp config.env.example config.env
# Отредактируйте config.env
python3 main.py
```

### 3. Установка на Linux (Ubuntu/Debian)

#### Шаг 1: Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

#### Шаг 2: Установка зависимостей
```bash
sudo apt install python3 python3-pip git sqlite3 -y
```

#### Шаг 3: Клонирование и установка
```bash
git clone <repository-url>
cd JKcommunity
pip3 install -r requirements.txt
cp config.env.example config.env
# Отредактируйте config.env
python3 main.py
```

## ☁️ Развертывание на сервере

### 1. VPS (Virtual Private Server)

#### Рекомендуемые провайдеры:
- **DigitalOcean** - от $5/месяц
- **Linode** - от $5/месяц
- **Vultr** - от $2.50/месяц
- **AWS EC2** - от $3.50/месяц

#### Шаг 1: Создание сервера
1. Выберите Ubuntu 20.04 LTS
2. Минимум 1 GB RAM
3. 20 GB SSD
4. Настройте SSH ключи

#### Шаг 2: Подключение к серверу
```bash
ssh root@your-server-ip
```

#### Шаг 3: Установка зависимостей
```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Python и зависимостей
apt install python3 python3-pip python3-venv git sqlite3 supervisor nginx -y

# Создание пользователя для бота
adduser gasjkbot
usermod -aG sudo gasjkbot
```

#### Шаг 4: Установка бота
```bash
# Переключение на пользователя бота
su - gasjkbot

# Клонирование репозитория
git clone <repository-url>
cd JKcommunity

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp config.env.example config.env
nano config.env
```

#### Шаг 5: Настройка Supervisor

Создайте файл конфигурации:
```bash
sudo nano /etc/supervisor/conf.d/gasjkbot.conf
```

Содержимое файла:
```ini
[program:gasjkbot]
command=/home/gasjkbot/JKcommunity/venv/bin/python /home/gasjkbot/JKcommunity/main.py
directory=/home/gasjkbot/JKcommunity
user=gasjkbot
autostart=true
autorestart=true
stderr_logfile=/var/log/gasjkbot.err.log
stdout_logfile=/var/log/gasjkbot.out.log
environment=PYTHONPATH="/home/gasjkbot/JKcommunity"
```

Запуск Supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start gasjkbot
```

#### Шаг 6: Настройка Nginx (опционально)

Создайте конфигурацию:
```bash
sudo nano /etc/nginx/sites-available/gasjkbot
```

Содержимое:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/gasjkbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. Docker развертывание

#### Шаг 1: Создание Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

#### Шаг 2: Создание docker-compose.yml
```yaml
version: '3.8'

services:
  gasjkbot:
    build: .
    container_name: gasjkbot
    restart: unless-stopped
    volumes:
      - ./database:/app/database
      - ./config.env:/app/config.env
    environment:
      - PYTHONPATH=/app
    networks:
      - gasjkbot-network

networks:
  gasjkbot-network:
    driver: bridge
```

#### Шаг 3: Запуск
```bash
docker-compose up -d
```

### 3. Облачные платформы

#### Heroku
```bash
# Установка Heroku CLI
# Создание Procfile
echo "worker: python main.py" > Procfile

# Создание requirements.txt (уже есть)
# Добавление переменных окружения
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set TELEGRAM_ADMIN_ID=your_id

# Деплой
git add .
git commit -m "Initial deployment"
heroku create your-app-name
git push heroku main
```

#### Railway
```bash
# Подключение GitHub репозитория
# Настройка переменных окружения в веб-интерфейсе
# Автоматический деплой при push
```

#### Render
```bash
# Подключение GitHub репозитория
# Настройка как Web Service
# Добавление переменных окружения
# Автоматический деплой
```

## 🔧 Настройка и конфигурация

### 1. Переменные окружения

#### Обязательные:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_ID=your_admin_id
```

#### Рекомендуемые:
```env
TON_NETWORK=mainnet
DATABASE_PATH=./database/gasjk_bot.db
MESSAGE_REWARD=0.1
MIN_WITHDRAWAL_AMOUNT=25000
```

### 2. Настройка базы данных

#### SQLite (по умолчанию):
```bash
# База данных создается автоматически
# Путь: ./database/gasjk_bot.db
```

#### PostgreSQL (опционально):
```bash
# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib

# Создание базы данных
sudo -u postgres createdb gasjkbot
sudo -u postgres createuser gasjkbot

# Обновление requirements.txt
echo "psycopg2-binary==2.9.5" >> requirements.txt
```

### 3. Настройка логирования

#### Создание директории для логов:
```bash
mkdir -p /var/log/gasjkbot
chown gasjkbot:gasjkbot /var/log/gasjkbot
```

#### Настройка ротации логов:
```bash
sudo nano /etc/logrotate.d/gasjkbot
```

Содержимое:
```
/var/log/gasjkbot/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 gasjkbot gasjkbot
}
```

## 🔍 Мониторинг и обслуживание

### 1. Проверка статуса

#### Проверка процесса:
```bash
# Локально
ps aux | grep python

# На сервере с Supervisor
sudo supervisorctl status gasjkbot
```

#### Проверка логов:
```bash
# Логи приложения
tail -f /var/log/gasjkbot.out.log

# Логи ошибок
tail -f /var/log/gasjkbot.err.log

# Системные логи
journalctl -u supervisor -f
```

### 2. Обновление бота

#### Автоматическое обновление:
```bash
#!/bin/bash
# update_bot.sh

cd /home/gasjkbot/JKcommunity
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart gasjkbot
```

#### Ручное обновление:
```bash
# Остановка бота
sudo supervisorctl stop gasjkbot

# Обновление кода
cd /home/gasjkbot/JKcommunity
git pull origin main

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Запуск бота
sudo supervisorctl start gasjkbot
```

### 3. Резервное копирование

#### Создание скрипта резервного копирования:
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/gasjkbot"
DB_PATH="/home/gasjkbot/JKcommunity/database/gasjk_bot.db"

mkdir -p $BACKUP_DIR
cp $DB_PATH $BACKUP_DIR/gasjk_bot_$DATE.db
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /home/gasjkbot/JKcommunity/config.env

# Удаление старых резервных копий (старше 30 дней)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

#### Настройка автоматического резервного копирования:
```bash
# Добавление в crontab
crontab -e

# Добавить строку для ежедневного резервного копирования в 2:00
0 2 * * * /home/gasjkbot/backup.sh
```

## 🚨 Устранение неполадок

### 1. Частые проблемы

#### Бот не запускается:
```bash
# Проверка токена
echo $TELEGRAM_BOT_TOKEN

# Проверка прав доступа
ls -la /home/gasjkbot/JKcommunity/

# Проверка логов
tail -f /var/log/gasjkbot.err.log
```

#### Ошибки базы данных:
```bash
# Проверка прав доступа к БД
ls -la /home/gasjkbot/JKcommunity/database/

# Проверка целостности SQLite
sqlite3 /home/gasjkbot/JKcommunity/database/gasjk_bot.db "PRAGMA integrity_check;"
```

#### Проблемы с сетью:
```bash
# Проверка подключения к Telegram API
curl -s https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe

# Проверка подключения к TON API
curl -s https://toncenter.com/api/v2/getAddressInfo?address=EQD...
```

### 2. Восстановление после сбоя

#### Восстановление из резервной копии:
```bash
# Остановка бота
sudo supervisorctl stop gasjkbot

# Восстановление базы данных
cp /backup/gasjkbot/gasjk_bot_YYYYMMDD_HHMM.db /home/gasjkbot/JKcommunity/database/gasjk_bot.db

# Восстановление конфигурации
tar -xzf /backup/gasjkbot/config_YYYYMMDD_HHMM.tar.gz

# Запуск бота
sudo supervisorctl start gasjkbot
```

## 📊 Производительность

### 1. Оптимизация

#### Настройка Python:
```bash
# Установка переменных окружения для оптимизации
export PYTHONOPTIMIZE=1
export PYTHONUNBUFFERED=1
```

#### Настройка SQLite:
```bash
# В коде добавьте:
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

### 2. Масштабирование

#### Горизонтальное масштабирование:
- Используйте несколько экземпляров бота
- Настройте балансировщик нагрузки
- Используйте общую базу данных (PostgreSQL)

#### Вертикальное масштабирование:
- Увеличьте RAM и CPU
- Используйте SSD диски
- Оптимизируйте код

## 🔐 Безопасность

### 1. Настройка файрвола
```bash
# Установка UFW
sudo apt install ufw

# Настройка правил
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL сертификат
```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com
```

### 3. Регулярные обновления
```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 📞 Поддержка

### Полезные команды:
```bash
# Статус всех сервисов
sudo systemctl status nginx supervisor

# Перезапуск сервисов
sudo systemctl restart nginx
sudo supervisorctl restart gasjkbot

# Просмотр логов в реальном времени
tail -f /var/log/gasjkbot.out.log
```

### Контакты:
- **GitHub Issues:** Для багов и предложений
- **Telegram:** @your_support_username
- **Email:** support@yourproject.com

**Удачного развертывания! 🚀** 