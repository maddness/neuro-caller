# 🤖 Neuro-Caller

AI-powered phone recruitment system for taxi services using OpenAI Realtime API and Twilio.

## 📋 Описание

Neuro-Caller - это автоматизированная система для телефонного рекрутинга водителей в такси-сервис нового поколения. Система использует:
- **OpenAI Realtime API** для мгновенных голосовых разговоров с минимальной задержкой
- **Twilio Media Streams** для двунаправленной передачи аудио в реальном времени
- **WebSocket** для прямой связи между Twilio и OpenAI без промежуточной обработки

## ✨ Возможности

- ⚡ **Ультранизкая задержка** - прямой стрим аудио между Twilio и OpenAI
- ✅ Автоматические исходящие звонки на российские номера (+7)
- 🎙️ Естественный, живой диалог на русском языке
- 🧠 Контекстно-зависимые ответы с использованием GPT-4o Realtime
- 🔊 Нативное распознавание и синтез речи без конвертации в текст
- 📊 Логирование всех разговоров и транскрипций
- 🔄 Real-time audio streaming через WebSocket

## 🔧 Требования

- Python 3.8+
- Twilio аккаунт с возможностью звонков в Россию
- OpenAI API ключ
- Публичный URL для webhook'ов (ngrok, deployed server, etc.)

## 🚀 Быстрый старт

### 1. Клонирование и установка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd neuro-caller

# Запустите скрипт установки
chmod +x setup.sh
./setup.sh
```

### 2. Настройка переменных окружения

Отредактируйте файл `.env`:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Server Configuration
PORT=3000
BASE_URL=https://your-domain.com  # или ngrok URL

# Taxi Brand Configuration
TAXI_BRAND_NAME=Ваше Такси
```

### 3. Получение учетных данных

#### Twilio

1. Зарегистрируйтесь на [twilio.com](https://www.twilio.com)
2. Перейдите в [Console](https://console.twilio.com)
3. Скопируйте `Account SID` и `Auth Token`
4. Купите телефонный номер с возможностью исходящих звонков
5. **Важно**: Убедитесь, что ваш Twilio аккаунт имеет разрешение на звонки в Россию

#### OpenAI

1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
2. Перейдите в [API Keys](https://platform.openai.com/api-keys)
3. Создайте новый API ключ

### 4. Настройка публичного URL

Для локальной разработки используйте [ngrok](https://ngrok.com):

```bash
# Установите ngrok
brew install ngrok  # macOS
# или скачайте с https://ngrok.com/download

# Запустите туннель для HTTP (порт 3000)
ngrok http 3000
```

Скопируйте HTTPS URL (например, `https://abc123.ngrok.io`) и укажите его в `BASE_URL` в `.env`.

**Важно**: Не добавляйте порт в BASE_URL, система автоматически настроит порты для HTTP (3000) и WebSocket (3001).

### 5. Запуск серверов

Система запускает два сервера одновременно:
- **Flask HTTP сервер** (порт 3000) - для webhook'ов и API
- **WebSocket сервер** (порт 3001) - для Media Streams

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите оба сервера
./run_server.sh
# или
python start_servers.py
```

Серверы запустятся:
- HTTP: `http://0.0.0.0:3000`
- WebSocket: `ws://0.0.0.0:3001`

### 6. Совершение звонка

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Позвоните на номер
python src/scripts/make_call.py +79991234567
```

## 📁 Структура проекта

```
neuro-caller/
├── src/
│   ├── __init__.py
│   ├── app.py                          # Flask приложение
│   ├── websocket_server.py             # WebSocket сервер для Media Streams
│   ├── config.py                       # Конфигурация
│   ├── routes/
│   │   ├── __init__.py
│   │   └── voice_routes.py             # Webhook endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── realtime_client.py          # OpenAI Realtime API клиент
│   │   ├── media_stream_handler.py     # Обработчик Media Streams
│   │   ├── openai_service.py           # OpenAI интеграция (legacy)
│   │   └── twilio_service.py           # Twilio интеграция
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── make_call.py                # Скрипт для звонков
│   └── utils/
│       ├── __init__.py
│       └── audio_converter.py          # Конвертация аудио форматов
├── start_servers.py                    # Запуск обоих серверов
├── venv/                               # Виртуальное окружение
├── .env                          # Переменные окружения (не в git)
├── .env.example                  # Шаблон переменных
├── .gitignore
├── requirements.txt              # Python зависимости
├── setup.sh                      # Скрипт установки
├── run_server.sh                 # Скрипт запуска сервера
└── README.md                     # Документация
```

## 🔌 API Endpoints

### HTTP Endpoints (Flask - порт 3000)

- `POST /voice/initial` - Начало звонка, инициация Media Stream
- `POST /voice/status` - Обновления статуса звонка
- `GET /` - Информация о сервисе
- `GET /health` - Health check
- `GET /voice/health` - Health check voice routes

### WebSocket Endpoints (порт 3001)

- `WS /media-stream` - Twilio Media Streams для real-time аудио

## 🎯 Как это работает (Realtime API Architecture)

### Поток данных:

```
[Phone] <--(Audio)--> [Twilio] <--(WebSocket)--> [Media Stream Handler] <--(WebSocket)--> [OpenAI Realtime API]
```

### Пошаговый процесс:

1. **Инициация звонка**: Скрипт `make_call.py` через Twilio API совершает звонок
2. **Webhook /voice/initial**: Twilio отправляет webhook, получает TwiML с инструкцией подключения к WebSocket
3. **Установка WebSocket соединений**:
   - Twilio подключается к нашему WebSocket серверу (порт 3001)
   - Наш сервер подключается к OpenAI Realtime API
4. **Двунаправленный аудио стрим**:
   - Аудио от абонента → Twilio → WebSocket → Конвертация (mulaw→PCM16) → OpenAI
   - OpenAI → PCM16 аудио ответ → Конвертация (PCM16→mulaw) → WebSocket → Twilio → Абонент
5. **Обработка в реальном времени**:
   - OpenAI Realtime API обрабатывает аудио напрямую (без текста)
   - VAD (Voice Activity Detection) автоматически определяет паузы
   - Ответ генерируется и озвучивается мгновенно
6. **Завершение**: При окончании разговора все WebSocket соединения закрываются, ресурсы освобождаются

### Преимущества Realtime API:

- **~300ms задержка** вместо 2-3 секунд (старый подход)
- Нативная обработка аудио (нет потерь при конвертации текст↔аудио)
- Автоматическое определение пауз в речи
- Естественные интонации и эмоции в голосе AI
- Возможность перебивать AI (interrupt support)

## 📊 Логирование

Все события логируются в консоль:
- Инициация звонков
- Распознанная речь пользователя
- Ответы AI
- Статусы звонков
- Ошибки

## 🛠️ Разработка

### Установка зависимостей

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Запуск в режиме разработки

```bash
source venv/bin/activate
python src/app.py
```

Flask запустится в debug режиме с автоперезагрузкой.

### Тестирование webhook'ов локально

1. Запустите ngrok: `ngrok http 3000`
2. Обновите `BASE_URL` в `.env`
3. Перезапустите сервер
4. Совершите тестовый звонок

## 💡 Настройка диалога

Диалог настраивается в файле `src/services/openai_service.py`:

```python
system_prompt = config.RECRUITMENT_PROMPT.format(
    brand=config.TAXI_BRAND_NAME
) + """
Важные правила:
1. Говорите кратко и естественно
2. Представьтесь в начале
3. Узнайте имя собеседника
4. Расскажите о преимуществах:
   - Гибкий график
   - Еженедельные выплаты
   - Бонусы и премии
   - Поддержка 24/7
5. Ответьте на вопросы
6. Предложите оставить контакты
"""
```

## 🌍 Поддержка российских номеров

Twilio поддерживает звонки на российские номера (+7), но:

1. Убедитесь, что ваш аккаунт верифицирован
2. Проверьте наличие разрешений для звонков в Россию
3. Может потребоваться дополнительная верификация номеров
4. Учитывайте стоимость международных звонков

## 💰 Стоимость

### OpenAI Realtime API Pricing

- **Input audio**: $0.06 / minute
- **Output audio**: $0.24 / minute
- **Text input/output**: $5/$20 per 1M tokens

### Twilio Pricing

- **Исходящие звонки в Россию**: ~$0.01-0.05 / минуту

### Примерная стоимость

**1 звонок (3-5 минут)**:
- Twilio: $0.03-0.25
- OpenAI Realtime (3 мин входящего + 2 мин исходящего аудио): ~$0.66
- **Итого**: ~$0.70-0.90 за звонок

**Сравнение с классическим подходом**:
- Старый метод (GPT-4 + TTS): $0.10-0.30
- Realtime API: $0.70-0.90
- **Но**: Значительно лучшее качество разговора и UX!

## 🔒 Безопасность

- Храните `.env` в безопасности, не коммитьте в git
- Используйте HTTPS для webhook URL
- Ограничивайте доступ к API ключам
- Регулярно ротируйте секретные ключи

## 📝 Лицензия

MIT

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи сервера
2. Проверьте Twilio Console на наличие ошибок
3. Убедитесь, что webhook URL доступен публично
4. Проверьте баланс Twilio и OpenAI

## 🚀 Деплой в продакшн

### Рекомендации

1. Используйте production WSGI сервер (gunicorn для Flask)
2. Запускайте WebSocket сервер через systemd или supervisor
3. Настройте HTTPS и WSS (SSL для WebSocket)
4. Используйте переменные окружения для секретов
5. Настройте мониторинг и алертинг
6. Добавьте rate limiting
7. Используйте reverse proxy (nginx) для обоих портов

### Пример конфигурации

**Flask через Gunicorn**:
```bash
gunicorn -w 4 -b 127.0.0.1:3000 src.app:app
```

**WebSocket через systemd**:
```ini
[Unit]
Description=Neuro-Caller WebSocket Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/neuro-caller
Environment="PATH=/var/www/neuro-caller/venv/bin"
ExecStart=/var/www/neuro-caller/venv/bin/python src/websocket_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Nginx reverse proxy**:
```nginx
# HTTP endpoint
location / {
    proxy_pass http://127.0.0.1:3000;
}

# WebSocket endpoint
location /media-stream {
    proxy_pass http://127.0.0.1:3001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
}
```

## 🔧 Технологии

- **Python 3.8+**
- **Flask** - HTTP сервер для webhook'ов
- **WebSockets** - Двунаправленная связь в реальном времени
- **OpenAI Realtime API** - Speech-to-speech AI с низкой задержкой
- **Twilio Media Streams** - Телефония с аудио стримингом
- **audioop** - Конвертация форматов аудио (mulaw ↔ PCM16)

## 📚 Полезные ссылки

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [Twilio Media Streams Documentation](https://www.twilio.com/docs/voice/twiml/stream)
- [Twilio Voice TwiML](https://www.twilio.com/docs/voice/twiml)
- [ngrok Documentation](https://ngrok.com/docs)

---

Made with ❤️ and ⚡ Realtime API for taxi recruitment automation
