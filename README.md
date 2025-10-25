# 🤖 Neuro-Caller

AI-powered система телефонного рекрутинга водителей для такси-сервисов с использованием **Voximplant** и **OpenAI Realtime API**.

## ✨ Ключевые возможности

- **📍 Оптимизация для России**: 9 дата-центров в Европе для минимальной задержки
- **⚡ Встроенная интеграция с OpenAI**: Нативная поддержка Realtime API
- **💰 Экономичность**: Оптимальные тарифы для российских звонков
- **🎯 Простота**: Весь код в облаке, не нужны серверы
- **🔧 Serverless**: VoxEngine JavaScript сценарии
- **🌐 Поддержка русского языка**: Интеграция с Yandex и Tinkoff TTS/STT

## 📋 Возможности

- ⚡ **Ультранизкая задержка** (~300ms) благодаря OpenAI Realtime API
- ✅ Автоматические исходящие звонки на российские номера (+7)
- 🎙️ Натуральный диалог на русском языке с AI рекрутером Анной
- 🧠 Контекстно-зависимые ответы с использованием GPT-4o Realtime
- 🔊 Прямая передача аудио без конвертации в текст
- 📊 Детальная статистика и логирование звонков
- ☁️ Полностью облачное решение без необходимости в серверах

## 🏗️ Архитектура

```
[Телефон] ←→ [Voximplant Cloud + VoxEngine] ←→ [OpenAI Realtime API]
                        ↑
                 Всё в облаке (serverless)
```

Система полностью работает в облаке без необходимости в собственных серверах.

## 🔧 Требования

- Python 3.8+ (только для управляющих скриптов)
- Voximplant аккаунт
- OpenAI API ключ с доступом к Realtime API
- ~$10 на балансе Voximplant для тестов

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd neuro-caller
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Voximplant
VOXIMPLANT_ACCOUNT_ID=12345
VOXIMPLANT_API_KEY=your_api_key
VOXIMPLANT_APP_ID=67890
VOXIMPLANT_RULE_ID=11111
VOXIMPLANT_USERNAME=user@app.account.voximplant.com
VOXIMPLANT_PASSWORD=your_password
VOXIMPLANT_PHONE_NUMBER=+7XXXXXXXXXX

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# Taxi Brand
TAXI_BRAND_NAME=Ваше Такси
```

### 4. Настройка Voximplant

Следуйте инструкции в [VOXIMPLANT_SETUP.md](VOXIMPLANT_SETUP.md) для:
- Создания аккаунта и приложения
- Загрузки сценария в Cloud IDE
- Получения номера телефона
- Настройки правил маршрутизации

### 5. Настройка OpenAI в Application Storage

```bash
cd voximplant
python vox_manager.py
```

### 6. Совершение тестового звонка

```bash
# Проверка подключения
python make_call_vox.py +79991234567 --test

# Реальный звонок
python make_call_vox.py +79991234567
```

## 📁 Структура проекта

```
neuro-caller/
├── voximplant/
│   ├── recruitment_bot.js       # VoxEngine сценарий (загружается в Cloud IDE)
│   ├── vox_manager.py           # Python SDK для управления Voximplant
│   └── make_call_vox.py         # Скрипт для совершения звонков
├── .env.example                  # Шаблон переменных окружения
├── requirements.txt              # Python зависимости
├── VOXIMPLANT_SETUP.md          # Подробная инструкция настройки Voximplant
├── README.md                    # Этот файл
└── CLAUDE.md                    # Инструкции для Claude Code
```

## 💼 Как это работает

### 1. Инициация звонка
```python
manager = VoximplantManager()
session_id = manager.make_call("+79991234567")
```

### 2. Обработка в облаке Voximplant
- VoxEngine выполняет сценарий `recruitment_bot.js`
- Устанавливается соединение с OpenAI Realtime API
- Медиа передается напрямую между Voximplant и OpenAI

### 3. AI разговор
- OpenAI обрабатывает аудио в реальном времени
- AI рекрутер Анна ведет естественный диалог
- Автоматическое определение пауз (VAD)
- Завершение при прощании

### 4. Результат
- Логи доступны в панели Voximplant
- Статистика через API
- Транскрипции разговоров

## 📊 Управление и мониторинг

### Python SDK (vox_manager.py)

```python
from voximplant.vox_manager import VoximplantManager

# Инициализация
manager = VoximplantManager()
manager.login()

# Настройка OpenAI
manager.configure_openai_settings(
    openai_api_key="sk-xxx",
    taxi_brand_name="Ваше Такси"
)

# Совершение звонка
session_id = manager.make_call("+79991234567")

# Получение статистики
stats = manager.get_statistics(period_days=7)
print(f"Всего звонков: {stats['total_calls']}")
print(f"Успешных: {stats['successful_calls']}")
```

### Командная строка

```bash
# Звонок с настройкой
python make_call_vox.py +79991234567 --configure

# Звонок со статистикой
python make_call_vox.py +79991234567 --stats
```

## 💰 Стоимость

### Стоимость за звонок (5 минут)

| Компонент | Стоимость |
|-----------|-----------|
| Voximplant (звонки в РФ) | $0.05-0.15 |
| OpenAI Realtime API | $0.66 |
| **Итого** | **~$0.76** |

### Месячная стоимость (100 звонков)

- Телефония Voximplant: ~$15
- OpenAI API: ~$66
- Номер телефона: ~$3
- **Итого: ~$84/месяц**

## 🎯 Настройка диалога

Диалог настраивается в `voximplant/recruitment_bot.js`:

```javascript
function getSystemInstructions() {
    return `Вы - Анна, дружелюбный рекрутер такси-сервиса ${config.taxiBrandName}.

    Важные правила:
    1. Представьтесь в начале
    2. Узнайте имя собеседника
    3. Расскажите о преимуществах:
       - Гибкий график
       - Еженедельные выплаты
       - Бонусы до 50,000 рублей
    ...`;
}
```

## 🔒 Безопасность

- API ключи хранятся в `.env.voximplant` (не коммитить!)
- OpenAI ключ хранится в Voximplant Application Storage
- Все звонки логируются в защищенной панели Voximplant
- Используйте разные учетные данные для dev/prod

## 🐛 Troubleshooting

### Ошибка авторизации
```
❌ Failed to authenticate
```
**Решение**: Проверьте `VOXIMPLANT_API_KEY` и `VOXIMPLANT_ACCOUNT_ID`

### Звонок не инициируется
```
❌ Failed to start call
```
**Решение**:
- Проверьте баланс Voximplant
- Убедитесь, что правило (Rule ID) настроено правильно
- Проверьте привязку номера к приложению

### Нет звука при звонке
**Решение**:
- Проверьте OpenAI API ключ в Application Storage
- Убедитесь, что сценарий загружен и сохранен
- Проверьте логи в панели Voximplant

## 📚 Документация

- [VOXIMPLANT_SETUP.md](VOXIMPLANT_SETUP.md) - Подробная инструкция по настройке
- [Voximplant Docs](https://voximplant.com/docs) - Официальная документация
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) - Документация OpenAI
- [VoxEngine Reference](https://voximplant.com/docs/references/voxengine) - Справочник VoxEngine


## 📝 Лицензия

MIT

## 🎉 Готово!

Теперь у вас есть полностью облачная система AI-рекрутинга на базе Voximplant с минимальной инфраструктурой и оптимизированная для российского рынка!

---

Made with ❤️ using Voximplant Cloud & OpenAI Realtime API