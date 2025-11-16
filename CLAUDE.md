# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Проект

**USB Audio Recorder Transcription Pipeline** - автоматическая система для транскрибации аудиозаписей с USB диктофонов через Yandex Eliza API (совместимый с OpenAI Whisper).

## Основные команды

### Установка

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Установка ffmpeg (необходим для pydub)
sudo apt-get install ffmpeg  # Ubuntu/Debian
```

### Настройка

```bash
cp .env.example .env
# Отредактировать .env с вашим Yandex OAuth токеном (SOY_TOKEN)
```

### Запуск

```bash
# Мониторинг USB устройств (основной режим)
python main.py monitor
python main.py monitor --check-interval 5 --language es

# Обработка конкретного устройства или файла
python main.py process /media/usb0
python main.py process /path/to/recording.mp3

# Просмотр статистики
python main.py stats

# Полнотекстовый поиск в транскрипциях
python main.py search "текст запроса"
python main.py search "проблема" --device Agent_001 --limit 20
```

### Флаги командной строки

```bash
--log-level [DEBUG|INFO|WARNING|ERROR]  # Уровень логирования
--log-file путь/к/логам                 # Путь к файлу логов
--api-key токен                         # Yandex OAuth токен (SOY_TOKEN)
--language язык                         # ISO-639-1 код (по умолчанию es)
--chunk-length минуты                   # Длина чанка (по умолчанию 10)
--overlap секунды                       # Overlap между чанками (по умолчанию 5)
--check-interval секунды                # Интервал проверки USB (по умолчанию 5)
--telegram-token токен                  # Telegram бот токен
--telegram-chat ID                      # Telegram чат ID
--telegram-enabled true/false           # Включить Telegram уведомления
```

## Архитектура

### Структура проекта

```
neuro-caller/
├── src/
│   ├── usb_monitor.py       # Мониторинг USB устройств
│   ├── file_manager.py      # Управление файлами
│   ├── audio_processor.py   # Разделение аудио на части
│   ├── transcriber.py       # Транскрибация через Yandex Eliza API
│   ├── database.py          # SQLite база данных
│   └── telegram_notifier.py # Telegram уведомления
├── main.py                  # Главный CLI интерфейс
└── data/                    # Данные и база данных
```

### Компоненты

**USBMonitor (src/usb_monitor.py)**
- Обнаружение подключения USB устройств
- Уникальная идентификация устройств (UUID, Serial, Label)
- Проверка наличия аудиофайлов
- Непрерывный мониторинг с заданным интервалом

**FileManager (src/file_manager.py)**
- Поиск новых аудиофайлов на устройстве
- Вычисление MD5 хеша для отслеживания обработанных файлов
- Копирование файлов в локальное хранилище
- Ведение реестра обработанных файлов (JSON)

**AudioProcessor (src/audio_processor.py)**
- Загрузка аудиофайлов через pydub
- Разделение больших файлов на части (макс 24MB)
- Добавление overlap между частями (по умолчанию 5 секунд)
- Поддержка форматов: MP3, WAV, M4A, FLAC, OGG, AAC, WMA

**WhisperTranscriber (src/transcriber.py)**
- Транскрибация через Yandex Eliza API (совместимый с OpenAI Whisper)
- Поддержка любого языка (по умолчанию русский 'ru')
- Автоматическая обработка больших файлов с разделением
- Объединение результатов из нескольких чанков

**TranscriptionDatabase (src/database.py)**
- SQLite база данных с FTS5 полнотекстовым поиском
- Хранение транскрипций с метаданными
- Статистика по устройствам и датам
- Быстрый поиск по тексту

**TelegramNotifier (src/telegram_notifier.py)**
- Уведомления о подключении устройства
- Отслеживание прогресса копирования и обработки
- Уведомления об ошибках
- Использует aiogram 3.0+ для асинхронной отправки

### Поток данных

Проект использует двухэтапную обработку через класс **TranscriptionPipeline** в main.py:

**ЭТАП 1: Копирование файлов**
```
USB устройство → USBMonitor → FileManager → Локальный диск
```
После этого устройство можно безопасно отключить.

**ЭТАП 2: Обработка и транскрибация**
```
Локальные файлы → AudioProcessor → WhisperTranscriber → TranscriptionDatabase
```
Происходит в фоновом режиме после копирования.

На каждом этапе отправляются Telegram уведомления через TelegramNotifier.

## Переменные окружения (.env)

```env
# Yandex Eliza API Configuration
SOY_TOKEN=y1_...                # Yandex OAuth токен (обязательно)

# Transcription Settings
LANGUAGE=ru                     # Язык аудио (ISO-639-1)
CHUNK_LENGTH_MINUTES=10         # Длина чанка в минутах
OVERLAP_SECONDS=5               # Overlap между чанками

# USB Monitor Settings
CHECK_INTERVAL=5                # Интервал проверки USB устройств

# Telegram Notifications (опционально)
TELEGRAM_BOT_TOKEN=token        # Токен бота
TELEGRAM_CHAT_ID=id            # ID чата
TELEGRAM_ENABLED=true          # Включить уведомления

# Logging
LOG_LEVEL=INFO                  # Уровень логирования
```

## База данных

### Таблицы

**transcriptions**
- Основная таблица с транскрипциями
- Поля: id, file_hash, original_filename, device_name, audio_file_path, transcription_text, language, duration_seconds, word_count, created_at, processed_at, metadata

**transcription_chunks**
- Чанки для файлов, которые были разделены
- Связь с transcriptions через foreign key

**transcriptions_fts**
- FTS5 виртуальная таблица для полнотекстового поиска

## Зависимости

```txt
openai>=1.12.0         # API клиент (совместим с Yandex Eliza)
pydub>=0.25.1          # Обработка аудио файлов
psutil>=5.9.0          # Мониторинг устройств
python-dotenv>=1.0.0   # Загрузка переменных окружения
aiogram>=3.0.0         # Telegram бот (для уведомлений)
```

**Системные зависимости:**
- **ffmpeg** - необходим для pydub:
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - MacOS: `brew install ffmpeg`
  - Windows: скачать с https://ffmpeg.org/

## Ограничения и особенности

- Максимальный размер файла для Whisper API: 25MB (файлы автоматически разделяются)
- Overlap между чанками для плавности транскрипции
- MD5 хеширование для отслеживания обработанных файлов
- Автоматическая организация файлов по дате и устройству
- **Уникальная идентификация устройств**: система различает разные флешки по UUID/Serial/Label, а не по точке монтирования

## Стоимость

Yandex Eliza API: Бесплатно для разработчиков (проверьте актуальные тарифы на yandex.ru/dev/eliza/)

## Разработка

### Тестирование модулей

Каждый модуль можно запустить отдельно для тестирования:

```bash
python -m src.usb_monitor
python -m src.file_manager
python -m src.audio_processor
python -m src.transcriber
python -m src.database
python -m src.telegram_notifier
```

### Логирование

Логи сохраняются в `logs/transcription.log`
Уровень логирования настраивается через `--log-level` флаг

## Использование

### Автоматический режим

```bash
# Запуск мониторинга
python main.py monitor

# Подключите USB диктофон
# Система автоматически обработает все новые файлы
```

### Ручной режим

```bash
# Обработка устройства
python main.py process /media/usb0

# Обработка файла
python main.py process /path/to/recording.mp3

# Просмотр результатов
python main.py stats
python main.py search "ключевое слово"
```

## Типичные сценарии использования

1. **Call-центр**: Агенты вечером подключают диктофоны, система автоматически транскрибирует все разговоры за день
2. **Ручная обработка**: Разовая транскрибация конкретного файла или устройства
3. **Поиск и анализ**: Полнотекстовый поиск по всем транскрипциям в базе данных

## Ключевые особенности архитектуры

1. **Двухэтапная обработка**: Сначала копирование всех файлов (можно отключить устройство), потом обработка в фоне
2. **Уникальная идентификация устройств**: UUID > Serial > Label > точка монтирования
3. **MD5 хеширование**: Предотвращение повторной обработки одинаковых файлов
4. **Overlap между чанками**: 5 секунд перекрытия для плавности транскрипции
5. **FTS5 полнотекстовый поиск**: Быстрый поиск по всем транскрипциям
6. **Асинхронные Telegram уведомления**: Отслеживание процесса в реальном времени

## Дополнительная документация

- **README.md**: Полная документация на русском языке
- **EXAMPLE_OUTPUT.md**: Примеры вывода программы
- **TELEGRAM_SETUP.md**: Инструкция по настройке Telegram бота
- **Комментарии в коде**: Все модули подробно документированы
- **Примеры**: Включены в README.md и в секциях `if __name__ == "__main__"` каждого модуля
