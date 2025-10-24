# 🚀 Quick Start Guide

Пошаговая инструкция для запуска и тестирования Neuro-Caller.

## Шаг 1: Установка зависимостей

```bash
# Перейдите в директорию проекта
cd /home/user/neuro-caller

# Запустите скрипт установки
chmod +x setup.sh
./setup.sh
```

Скрипт автоматически:
- Создаст виртуальное окружение
- Установит все зависимости из requirements.txt
- Создаст файл .env из шаблона

## Шаг 2: Получение API ключей

### 2.1. Twilio

1. Зарегистрируйтесь на https://www.twilio.com/try-twilio
2. После регистрации перейдите в Console: https://console.twilio.com
3. Скопируйте:
   - **Account SID** (начинается с AC...)
   - **Auth Token** (нажмите "Show" чтобы увидеть)
4. Купите номер телефона:
   - Phone Numbers → Buy a Number
   - Выберите номер с Voice capabilities
   - Скопируйте номер (формат: +1234567890)

**Важно для звонков в Россию:**
- Убедитесь что ваш аккаунт верифицирован
- Может потребоваться апгрейд с Trial на Paid аккаунт
- Проверьте GEO Permissions: Settings → Voice & Video → Geo Permissions
- Включите Russia в списке разрешенных стран

### 2.2. OpenAI

1. Зарегистрируйтесь на https://platform.openai.com
2. Перейдите в API Keys: https://platform.openai.com/api-keys
3. Нажмите "Create new secret key"
4. Скопируйте ключ (начинается с sk-...)
5. **Важно**: Добавьте деньги на баланс ($5-10 для тестирования)
6. **Проверьте**: Realtime API доступен не всем аккаунтам, возможно нужно запросить доступ

### 2.3. Проверка доступа к Realtime API

```bash
# Активируйте venv
source venv/bin/activate

# Проверьте доступ через curl
curl -i -N \
  -H "Authorization: Bearer YOUR_OPENAI_API_KEY" \
  -H "OpenAI-Beta: realtime=v1" \
  "https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

# Если получите "Switching Protocols" - доступ есть
# Если 403/401 - проверьте ключ или запросите доступ
```

## Шаг 3: Настройка .env файла

```bash
# Откройте .env файл
nano .env
# или
vim .env
```

Заполните все переменные:

```env
# Twilio Configuration (замените на ваши данные)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+12345678901

# OpenAI Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Server Configuration (пока оставьте как есть)
PORT=3000
BASE_URL=http://localhost:3000

# Taxi Brand Configuration (можете изменить)
TAXI_BRAND_NAME=Яндекс Такси
```

## Шаг 4: Настройка ngrok для локального тестирования

### 4.1. Установка ngrok

**macOS:**
```bash
brew install ngrok
```

**Linux:**
```bash
# Скачайте и установите
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok
```

**Или скачайте с:**
https://ngrok.com/download

### 4.2. Регистрация и аутентификация

```bash
# Зарегистрируйтесь на ngrok.com и получите authtoken
ngrok authtoken YOUR_AUTH_TOKEN
```

### 4.3. Запуск ngrok

```bash
# В отдельном терминале запустите:
ngrok http 3000
```

Вы увидите что-то вроде:
```
Forwarding   https://abc123def456.ngrok.io -> http://localhost:3000
```

**Скопируйте HTTPS URL** (например: `https://abc123def456.ngrok.io`)

### 4.4. Обновите .env

```bash
# Откройте .env и обновите BASE_URL
nano .env

# Измените:
BASE_URL=https://abc123def456.ngrok.io
```

**Важно:**
- Используйте HTTPS URL (не HTTP)
- Не добавляйте порт в конце
- Каждый раз при перезапуске ngrok URL меняется!

## Шаг 5: Запуск серверов

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите оба сервера (Flask + WebSocket)
./run_server.sh
```

Вы должны увидеть:
```
🚀 Starting Neuro-Caller servers...
   - Flask server (HTTP): port 3000
   - WebSocket server (WS): port 3001

INFO - Starting WebSocket server on port 3001
INFO - Flask application created successfully
INFO - WebSocket server listening on ws://0.0.0.0:3001
 * Running on http://0.0.0.0:3000
```

**Проверка работы серверов:**

В другом терминале:
```bash
# Проверьте Flask
curl http://localhost:3000/health
# Ответ: {"status":"ok"}

# Проверьте публичный URL
curl https://your-ngrok-url.ngrok.io/health
```

## Шаг 6: Тестовый звонок

### 6.1. Подготовка тестового номера

**Для Trial аккаунта Twilio:**
- Можно звонить только на верифицированные номера
- Добавьте свой номер: Console → Phone Numbers → Verified Caller IDs
- Нажмите "Add a new Caller ID"
- Twilio позвонит/отправит SMS для подтверждения

**Формат номера:**
- Российский: +79991234567 (с + и кодом страны 7)
- США: +12025551234

### 6.2. Совершение звонка

```bash
# В терминале с активным venv:
source venv/bin/activate

# Позвоните на ваш номер (замените на реальный)
python src/scripts/make_call.py +79991234567
```

Вы должны увидеть:
```
INFO - Initiating call to +79991234567...
INFO - Call initiated successfully!
INFO - Call SID: CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
INFO - Monitor the call at: https://console.twilio.com
```

### 6.3. Что должно произойти

1. **Ваш телефон зазвонит** (через 5-10 секунд)
2. **Ответьте на звонок**
3. **AI начнет говорить**:
   - "Здравствуйте! Меня зовут Анна..."
4. **Говорите в ответ** (на русском)
5. **AI ответит** естественным голосом
6. **Продолжайте диалог**

## Шаг 7: Мониторинг и отладка

### 7.1. Логи в консоли

Следите за терминалом где запущены серверы:
```
INFO - Call CAxxxx connected: +12345678901 -> +79991234567
INFO - Connecting call CAxxxx to Media Stream: wss://...
INFO - New Media Stream connection from ('x.x.x.x', port)
INFO - Twilio Media Stream connected
INFO - Stream started - StreamSID: MZxxxx, CallSID: CAxxxx
INFO - Connected to OpenAI Realtime API
INFO - Session configured with recruitment instructions
INFO - User said: Здравствуйте
INFO - Stream stopped by Twilio
INFO - Cleaned up media stream handler for call CAxxxx
```

### 7.2. Twilio Console

Откройте: https://console.twilio.com/us1/monitor/logs/calls

- Найдите ваш звонок по Call SID
- Проверьте статус (completed, busy, failed)
- Посмотрите длительность
- Проверьте ошибки если есть

### 7.3. Проверка WebSocket соединений

```bash
# В другом терминале проверьте открытые порты
lsof -i :3000
lsof -i :3001

# Или через ss
ss -tulpn | grep 3000
ss -tulpn | grep 3001
```

## Типичные проблемы и решения

### ❌ "Failed to connect to OpenAI"

**Причины:**
- Неверный API ключ
- Нет доступа к Realtime API
- Проблемы с сетью

**Решение:**
```bash
# Проверьте ключ
echo $OPENAI_API_KEY

# Проверьте доступ
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### ❌ "Webhook URL not accessible"

**Причины:**
- ngrok не запущен
- Неверный BASE_URL в .env
- Firewall блокирует

**Решение:**
```bash
# Проверьте ngrok
curl -s http://localhost:4040/api/tunnels | python -m json.tool

# Проверьте доступность
curl https://your-ngrok-url.ngrok.io/health
```

### ❌ "Call failed immediately"

**Причины:**
- Неверные Twilio credentials
- Номер не верифицирован (Trial аккаунт)
- Недостаточно средств

**Решение:**
- Проверьте Console → Calls → Error logs
- Верифицируйте номер получателя
- Пополните баланс Twilio

### ❌ "No audio / robot doesn't speak"

**Причины:**
- WebSocket не подключился к OpenAI
- Проблемы с конвертацией аудио
- Неверная конфигурация Media Stream

**Решение:**
- Проверьте логи: "Connected to OpenAI Realtime API"
- Проверьте: "Session configured"
- Убедитесь что порт 3001 открыт через ngrok

### ❌ "WebSocket port 3001 not accessible"

**Причина:**
- ngrok работает только для 3000, нужен отдельный туннель для 3001

**Решение (два варианта):**

**Вариант 1: Nginx reverse proxy (рекомендуется для прода)**
```nginx
location /media-stream {
    proxy_pass http://127.0.0.1:3001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
}
```

**Вариант 2: Два ngrok туннеля**
```bash
# Terminal 1
ngrok http 3000

# Terminal 2
ngrok http 3001
```

Затем обновите код в `voice_routes.py`:
```python
# Используйте отдельный URL для WebSocket
stream_url = "wss://your-ws-ngrok-url.ngrok.io"
```

## Шаг 8: Тестирование диалога

### Примерный диалог:

**AI**: Здравствуйте! Меня зовут Анна, я звоню из Яндекс Такси. У вас есть минутка? Я хотела бы рассказать о возможности работы водителем в нашем сервисе.

**Вы**: Здравствуйте, да, слушаю вас.

**AI**: Отлично! Скажите, вы сейчас работаете водителем или рассматриваете такую возможность?

**Вы**: Да, интересно. Какие условия?

**AI**: У нас очень гибкие условия! Вы можете работать когда удобно - строите свой график сами. Выплаты еженедельные, без задержек. Плюс для новых водителей бонусы до 50 тысяч рублей...

### Тестируйте разные сценарии:

1. **Заинтересованный водитель**
2. **Скептически настроенный**
3. **Прерывание AI** (попробуйте перебить)
4. **Вопросы о деталях**
5. **Отказ от предложения**

## Шаг 9: Остановка серверов

```bash
# В терминале где запущены серверы:
# Нажмите Ctrl+C

# Остановите ngrok:
# В терминале ngrok нажмите Ctrl+C
```

## Дополнительные команды

### Просмотр логов детально

```bash
# Запустите с увеличенным уровнем логирования
python start_servers.py

# Или через gunicorn (production)
gunicorn --log-level debug src.app:app
```

### Тестирование компонентов отдельно

```bash
# Только Flask
python src/app.py

# Только WebSocket
python src/websocket_server.py
```

### Проверка зависимостей

```bash
source venv/bin/activate
pip list

# Обновление зависимостей
pip install -r requirements.txt --upgrade
```

## Следующие шаги

1. ✅ Протестируйте базовый звонок
2. ✅ Попробуйте разные сценарии диалога
3. ✅ Настройте промпт в `realtime_client.py` под ваш бренд
4. ✅ Добавьте логику записи заинтересованных кандидатов
5. ✅ Интегрируйте с CRM системой
6. ✅ Настройте production deployment

## Полезные ссылки

- **Twilio Console**: https://console.twilio.com
- **OpenAI Platform**: https://platform.openai.com
- **ngrok Dashboard**: https://dashboard.ngrok.com
- **Документация проекта**: README.md, REALTIME_API.md

---

Удачи с тестированием! 🚀📞
