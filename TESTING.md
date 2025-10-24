# 🧪 Testing Checklist

Краткий чеклист для тестирования системы.

## Перед началом

- [ ] Python 3.8+ установлен
- [ ] Twilio аккаунт создан
- [ ] OpenAI API ключ получен
- [ ] Доступ к Realtime API подтвержден
- [ ] ngrok установлен

## Быстрый запуск (TL;DR)

```bash
# 1. Установка
./setup.sh

# 2. Настройка .env (добавьте API ключи)
nano .env

# 3. Запуск ngrok (отдельный терминал)
ngrok http 3000
# Скопируйте HTTPS URL в BASE_URL в .env

# 4. Запуск серверов
./run_server.sh

# 5. Звонок (другой терминал)
source venv/bin/activate
python src/scripts/make_call.py +79991234567
```

## Проверка работоспособности

### ✅ Шаг 1: Проверка установки

```bash
source venv/bin/activate
python --version  # Python 3.8+
pip list | grep -E "flask|twilio|openai|websockets"
```

**Ожидаемый результат:**
```
flask          3.0.0
twilio         8.11.0
openai         1.6.1
websockets     12.0
```

### ✅ Шаг 2: Проверка конфигурации

```bash
# Проверьте .env
cat .env | grep -v "^#"
```

**Должны быть заполнены:**
- TWILIO_ACCOUNT_SID (начинается с AC)
- TWILIO_AUTH_TOKEN
- TWILIO_PHONE_NUMBER (формат +1234567890)
- OPENAI_API_KEY (начинается с sk-)
- BASE_URL (ngrok HTTPS URL)

### ✅ Шаг 3: Проверка Twilio credentials

```bash
source venv/bin/activate
python << 'EOF'
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()
client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Проверка аккаунта
account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
print(f"✅ Account Status: {account.status}")

# Проверка номера
phone = client.incoming_phone_numbers.list(
    phone_number=os.getenv('TWILIO_PHONE_NUMBER')
)
if phone:
    print(f"✅ Phone Number: {phone[0].phone_number}")
else:
    print("❌ Phone number not found")
EOF
```

### ✅ Шаг 4: Проверка OpenAI API

```bash
source venv/bin/activate
python << 'EOF'
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

try:
    # Проверка доступа к API
    models = client.models.list()
    print("✅ OpenAI API access confirmed")

    # Проверка баланса (если доступно)
    # Note: Realtime API в preview, проверка может не работать
    print("⚠️  Убедитесь что у вас есть доступ к Realtime API")

except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

### ✅ Шаг 5: Проверка ngrok

```bash
# Проверьте что ngrok запущен
ps aux | grep ngrok

# Проверьте туннели
curl -s http://localhost:4040/api/tunnels | python -m json.tool
```

**Ожидаемый результат:**
```json
{
  "tunnels": [
    {
      "public_url": "https://abc123.ngrok.io",
      "config": {
        "addr": "http://localhost:3000"
      }
    }
  ]
}
```

### ✅ Шаг 6: Проверка серверов

После запуска `./run_server.sh` проверьте:

```bash
# В другом терминале:

# Проверка Flask (HTTP)
curl http://localhost:3000/health
# Ожидается: {"status":"ok"}

# Проверка через ngrok
curl https://your-ngrok-url.ngrok.io/health
# Ожидается: {"status":"ok"}

# Проверка открытых портов
lsof -i :3000  # Flask
lsof -i :3001  # WebSocket
```

**Ожидаемый результат в логах:**
```
INFO - Starting WebSocket server on port 3001
INFO - WebSocket server listening on ws://0.0.0.0:3001
INFO - Flask application created successfully
 * Running on http://0.0.0.0:3000
```

### ✅ Шаг 7: Тестовый звонок

```bash
# Убедитесь что номер верифицирован в Twilio (для Trial)
# Затем:
source venv/bin/activate
python src/scripts/make_call.py +79991234567
```

**Ожидаемый результат:**
```
INFO - Initiating call to +79991234567...
INFO - Call initiated successfully!
INFO - Call SID: CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**В логах сервера должно появиться:**
```
INFO - Call CAxxxx connected
INFO - Connecting call CAxxxx to Media Stream
INFO - New Media Stream connection
INFO - Twilio Media Stream connected
INFO - Stream started
INFO - Connected to OpenAI Realtime API
INFO - Session configured
```

## Тестовые сценарии

### 🎯 Сценарий 1: Успешный рекрутинг

**Цель:** Проверить полный цикл разговора

**Шаги:**
1. Совершите звонок
2. Дождитесь приветствия AI
3. Ответьте положительно на предложение
4. Задайте вопросы о условиях
5. Согласитесь на сотрудничество

**Ожидаемый результат:**
- AI говорит естественно
- Понимает ваши вопросы
- Отвечает по контексту
- Предлагает оставить контакты

### 🎯 Сценарий 2: Прерывание AI

**Цель:** Проверить работу Voice Activity Detection

**Шаги:**
1. Дождитесь пока AI начнет говорить
2. Начните говорить не дожидаясь конца фразы
3. AI должен остановиться и слушать вас

**Ожидаемый результат:**
- AI прерывается
- Слушает ваш вопрос
- Отвечает на прерванную тему

### 🎯 Сценарий 3: Отказ от предложения

**Цель:** Проверить обработку отказа

**Шаги:**
1. Совершите звонок
2. Скажите что не заинтересованы
3. AI должен вежливо попрощаться

**Ожидаемый результат:**
- AI благодарит за время
- Вежливо прощается
- Звонок завершается

### 🎯 Сценарий 4: Проблемы со связью

**Цель:** Проверить устойчивость к помехам

**Шаги:**
1. Говорите неразборчиво
2. Делайте длинные паузы
3. Создавайте фоновый шум

**Ожидаемый результат:**
- AI переспрашивает если не понял
- Корректно обрабатывает паузы
- Не зависает

## Метрики для проверки

### Задержка (Latency)

Измерьте время от конца вашей фразы до начала ответа AI:

- ✅ **Отлично**: 300-500ms
- ⚠️ **Приемлемо**: 500-1000ms
- ❌ **Плохо**: >1000ms

### Качество распознавания

Проверьте транскрипции в логах:

```
INFO - User said: [ваша фраза]
```

- ✅ **Отлично**: 95%+ слов распознаны верно
- ⚠️ **Приемлемо**: 80-95%
- ❌ **Плохо**: <80%

### Естественность разговора

Субъективная оценка:

- ✅ Звучит как человек
- ✅ Эмоциональные интонации
- ✅ Естественные паузы
- ✅ Понимает контекст

## Частые проблемы при тестировании

### ❌ Звонок не проходит

**Проверьте:**
```bash
# Twilio Console → Calls → найдите ваш Call SID
# Посмотрите Error Code

# Распространенные ошибки:
# 21608 - Номер не верифицирован (Trial аккаунт)
# 21606 - Номер занят
# 21610 - Номер недоступен
```

### ❌ AI не отвечает

**Проверьте логи:**
```bash
# Должно быть:
INFO - Connected to OpenAI Realtime API
INFO - Session configured

# Если нет, проверьте:
# 1. Правильность OPENAI_API_KEY
# 2. Доступ к Realtime API
# 3. Интернет соединение
```

### ❌ Задержка >1 секунды

**Возможные причины:**
- Медленный интернет
- Удаленность от серверов OpenAI/Twilio
- Проблемы с ngrok

**Решение:**
```bash
# Проверьте пинг до OpenAI
ping api.openai.com

# Проверьте ngrok stats
curl http://localhost:4040/api/requests/http
```

### ❌ Плохое качество аудио

**Проверьте:**
```python
# В логах должны быть сообщения о конвертации аудио
# Если есть ошибки audioop - установите:
pip install --force-reinstall python-dev
```

## Логирование для отладки

Увеличьте уровень логирования:

```python
# В src/app.py и src/websocket_server.py измените:
logging.basicConfig(
    level=logging.DEBUG,  # Было INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Перезапустите серверы и повторите тест.

## Benchmark результаты

**Ожидаемые метрики для успешного теста:**

| Метрика | Значение |
|---------|----------|
| Latency (median) | 300-400ms |
| Latency (p95) | <800ms |
| Speech Recognition | >90% accuracy |
| Call Success Rate | >95% |
| WebSocket Uptime | 100% |
| AI Response Quality | Естественный |

## Экспорт логов для анализа

```bash
# Запустите с перенаправлением логов:
./run_server.sh 2>&1 | tee logs/test_$(date +%Y%m%d_%H%M%S).log

# Анализ логов:
grep "ERROR" logs/*.log
grep "Call.*connected" logs/*.log | wc -l  # Количество звонков
grep "User said:" logs/*.log  # Все транскрипции
```

## Готовность к production

- [ ] Все тесты пройдены
- [ ] Задержка <500ms стабильно
- [ ] Нет ошибок в логах
- [ ] AI отвечает адекватно
- [ ] Прерывания работают
- [ ] Звонок завершается корректно
- [ ] Twilio Console не показывает ошибок
- [ ] OpenAI расходы в пределах ожидаемых
- [ ] Промпт настроен под ваш бренд
- [ ] SSL/TLS настроен (для прода)
- [ ] Monitoring настроен

---

**Следующий шаг:** Если все тесты пройдены → [Production Deployment](README.md#деплой-в-продакшн)