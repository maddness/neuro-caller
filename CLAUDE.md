# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Проект

**USB Audio Recorder Transcription Pipeline** - автоматическая система для транскрибации аудиозаписей с USB диктофонов через OpenAI Whisper API.

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
# Отредактировать .env с вашим OpenAI API ключом
```

### Запуск

```bash
# Мониторинг USB устройств
python main.py monitor

# Обработка конкретного устройства или файла
python main.py process /path/to/device/or/file

# Просмотр статистики
python main.py stats

# Поиск в транскрипциях
python main.py search "текст запроса"
```

## Архитектура

### Структура проекта

```
neuro-caller/
├── src/
│   ├── usb_monitor.py       # Мониторинг USB устройств
│   ├── file_manager.py      # Управление файлами
│   ├── audio_processor.py   # Разделение аудио на части
│   ├── transcriber.py       # Транскрибация через Whisper API
│   └── database.py          # SQLite база данных
├── main.py                  # Главный CLI интерфейс
└── data/                    # Данные и база данных
```

### Компоненты

**USBMonitor (src/usb_monitor.py)**
- Обнаружение подключения USB устройств
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
- Транскрибация через OpenAI Whisper API
- Поддержка любого языка (по умолчанию испанский 'es')
- Автоматическая обработка больших файлов с разделением
- Объединение результатов из нескольких чанков

**TranscriptionDatabase (src/database.py)**
- SQLite база данных с FTS5 полнотекстовым поиском
- Хранение транскрипций с метаданными
- Статистика по устройствам и датам
- Быстрый поиск по тексту

### Поток данных

```
USB устройство
    ↓
USBMonitor (обнаружение)
    ↓
FileManager (копирование новых файлов)
    ↓
AudioProcessor (разделение на части если нужно)
    ↓
WhisperTranscriber (транскрибация через API)
    ↓
TranscriptionDatabase (сохранение результатов)
```

## Переменные окружения (.env)

```env
OPENAI_API_KEY=sk-...          # OpenAI API ключ
LANGUAGE=es                     # Язык аудио (ISO-639-1)
CHUNK_LENGTH_MINUTES=10         # Длина чанка в минутах
OVERLAP_SECONDS=5               # Overlap между чанками
CHECK_INTERVAL=5                # Интервал проверки USB устройств
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

- **openai**: OpenAI API клиент
- **pydub**: Обработка аудио файлов
- **psutil**: Системные утилиты (мониторинг устройств)
- **python-dotenv**: Загрузка переменных окружения
- **ffmpeg**: Необходим для pydub (устанавливается отдельно)

## Ограничения и особенности

- Максимальный размер файла для Whisper API: 25MB (файлы автоматически разделяются)
- Overlap между чанками для плавности транскрипции
- MD5 хеширование для отслеживания обработанных файлов
- Автоматическая организация файлов по дате и устройству

## Стоимость

OpenAI Whisper API: $0.006 за минуту аудио
- 1 час записи = $0.36
- 8 часов (рабочий день) = $2.88

## Разработка

### Тестирование модулей

Каждый модуль можно запустить отдельно для тестирования:

```bash
python -m src.usb_monitor
python -m src.file_manager
python -m src.audio_processor
python -m src.transcriber
python -m src.database
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

## Документация

- **README.md**: Полная документация на русском языке
- **Комментарии в коде**: Все модули подробно документированы
- **Примеры**: Включены в README.md и в секциях `if __name__ == "__main__"` каждого модуля
