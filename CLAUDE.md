# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект

**Neuro-Caller** - AI-powered система телефонного рекрутинга водителей для такси-сервиса. Использует Voximplant для телефонии и OpenAI Realtime API для натуральных голосовых разговоров с минимальной задержкой (~300ms).

## Основные команды

### Установка
```bash
pip install -r requirements.txt
```

### Настройка
```bash
cp .env.example .env
# Отредактировать .env с вашими данными Voximplant и OpenAI
```

### Совершение звонков
```bash
cd voximplant
python make_call_vox.py +79991234567              # Обычный звонок
python make_call_vox.py +79991234567 --test       # Тестовый режим
python make_call_vox.py +79991234567 --configure  # С настройкой OpenAI
python make_call_vox.py +79991234567 --stats      # Со статистикой
```

### Управление через SDK
```bash
cd voximplant
python vox_manager.py  # Настройка OpenAI и просмотр статистики
```

## Архитектура

### Serverless архитектура Voximplant

```
[Телефон] ←→ [Voximplant Cloud + VoxEngine] ←→ [OpenAI Realtime API]
                        ↑
                JavaScript сценарий
              (voximplant/recruitment_bot.js)
```

**Преимущества**:
- Не нужны серверы (полностью облачное решение)
- Встроенная интеграция с OpenAI Realtime API
- Автоматическая конвертация аудио форматов
- Оптимизировано для российского рынка (9 дата-центров в Европе)
- Экономия ~15% на звонках по сравнению с альтернативами

## Ключевые компоненты

**voximplant/recruitment_bot.js**
- VoxEngine сценарий (загружается в Voximplant Cloud IDE)
- Обработка входящих и исходящих звонков
- Интеграция с OpenAI через встроенный клиент `OpenAI.RealtimeAPIClient`
- Настройка диалога через функцию `getSystemInstructions()`

**voximplant/vox_manager.py**
- Python SDK для управления Voximplant API
- Методы: `make_call()`, `get_call_history()`, `get_statistics()`
- Настройка OpenAI параметров в Application Storage
- Авторизация и управление сессиями

**voximplant/make_call_vox.py**
- CLI скрипт для инициации звонков
- Поддержка тестового режима (--test)
- Настройка OpenAI перед звонком (--configure)
- Отображение статистики (--stats)

## Переменные окружения (.env)

```
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
RECRUITMENT_PROMPT=Кастомный промпт (опционально)
```

## Настройка диалога AI рекрутера

Диалог настраивается в `voximplant/recruitment_bot.js`:

```javascript
function getSystemInstructions() {
    return `Вы - Анна, дружелюбный рекрутер такси-сервиса ${config.taxiBrandName}.
    // ... инструкции для AI
    `;
}
```

Параметры хранятся в Voximplant Application Storage:
- `openai_api_key` - API ключ OpenAI
- `taxi_brand_name` - название бренда
- `recruitment_prompt` - кастомный промпт

## Формат аудио

Voximplant автоматически конвертирует аудио между форматами:
- Телефон ↔ Voximplant: автоматическая обработка
- Voximplant ↔ OpenAI: PCM16 формат
- Не требуется ручная конвертация

## Стоимость звонков

| Компонент | Стоимость |
|-----------|-----------|
| Voximplant (РФ) | $0.01-0.03/мин |
| OpenAI Realtime | $0.06/мин (input) + $0.24/мин (output) |
| **Итого за 5 мин** | **~$0.76** |

## Развертывание в продакшн

1. **Настройка Voximplant** - следуйте [VOXIMPLANT_SETUP.md](VOXIMPLANT_SETUP.md)
2. **Загрузка сценария** - скопируйте `recruitment_bot.js` в Cloud IDE
3. **Настройка переменных** - заполните Application Storage
4. **Тестирование** - запустите тестовый звонок
5. **Мониторинг** - используйте панель Voximplant для логов

Код уже выполняется в облаке - не требуется деплой серверов!

## Документация

- **[VOXIMPLANT_SETUP.md](VOXIMPLANT_SETUP.md)** - Подробная инструкция по настройке
- **[README.md](README.md)** - Основная документация проекта
- [Voximplant Docs](https://voximplant.com/docs) - Официальная документация
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) - Документация OpenAI