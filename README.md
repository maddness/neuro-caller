# 🤖 Neuro-Caller

AI-powered phone recruitment system for taxi services using OpenAI and Twilio.

## 📋 Описание

Neuro-Caller - это автоматизированная система для телефонного рекрутинга водителей в такси-сервис. Система использует:
- **OpenAI GPT-4** для генерации естественных разговорных ответов
- **Twilio** для совершения телефонных звонков (поддержка российских номеров +7)
- **Amazon Polly** (через Twilio) для синтеза речи на русском языке

## ✨ Возможности

- ✅ Автоматические исходящие звонки на российские номера
- ✅ Естественный диалог на русском языке
- ✅ Контекстно-зависимые ответы с использованием GPT-4
- ✅ Распознавание речи собеседника
- ✅ Логирование всех разговоров
- ✅ Webhook endpoints для интеграции с Twilio

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

# Запустите туннель
ngrok http 3000
```

Скопируйте HTTPS URL (например, `https://abc123.ngrok.io`) и укажите его в `BASE_URL` в `.env`.

### 5. Запуск сервера

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите сервер
./run_server.sh
# или
python src/app.py
```

Сервер запустится на `http://0.0.0.0:3000`

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
│   ├── app.py                    # Flask приложение
│   ├── config.py                 # Конфигурация
│   ├── routes/
│   │   ├── __init__.py
│   │   └── voice_routes.py       # Webhook endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── openai_service.py     # OpenAI интеграция
│   │   └── twilio_service.py     # Twilio интеграция
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── make_call.py          # Скрипт для звонков
│   └── utils/
│       └── __init__.py
├── venv/                         # Виртуальное окружение
├── .env                          # Переменные окружения (не в git)
├── .env.example                  # Шаблон переменных
├── .gitignore
├── requirements.txt              # Python зависимости
├── setup.sh                      # Скрипт установки
├── run_server.sh                 # Скрипт запуска сервера
└── README.md                     # Документация
```

## 🔌 API Endpoints

### Webhook Endpoints (для Twilio)

- `POST /voice/initial` - Начало звонка, приветствие
- `POST /voice/process` - Обработка речи пользователя
- `POST /voice/status` - Обновления статуса звонка

### Служебные Endpoints

- `GET /` - Информация о сервисе
- `GET /health` - Health check
- `GET /voice/health` - Health check voice routes

## 🎯 Как это работает

1. **Инициация звонка**: Скрипт `make_call.py` через Twilio API совершает звонок
2. **Webhook /voice/initial**: Twilio отправляет webhook, получает приветствие
3. **Распознавание речи**: Twilio распознает речь собеседника
4. **Webhook /voice/process**: Текст отправляется в OpenAI GPT-4
5. **Генерация ответа**: GPT-4 генерирует ответ на основе контекста
6. **Синтез речи**: Twilio озвучивает ответ голосом Amazon Polly
7. **Продолжение диалога**: Шаги 3-6 повторяются до завершения разговора

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

- **Twilio**: ~$0.01-0.05 за минуту исходящих звонков в Россию
- **OpenAI GPT-4**: ~$0.01-0.03 за запрос (зависит от длины диалога)
- **Примерная стоимость 1 звонка (3-5 минут)**: $0.10-0.30

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

1. Используйте production WSGI сервер (gunicorn)
2. Настройте HTTPS
3. Используйте переменные окружения для секретов
4. Настройте мониторинг и алертинг
5. Добавьте rate limiting

### Пример с Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:3000 src.app:app
```

---

Made with ❤️ for taxi recruitment automation
