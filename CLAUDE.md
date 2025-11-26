# CLAUDE.md

Инструкции для Claude Code при работе с этим репозиторием.

## Проект

**USB Audio Recorder Pipeline** — система для копирования аудиофайлов с USB диктофонов, загрузки в S3 и создания задач в Яндекс Трекере. Опционально: транскрибация через AssemblyAI.

## Основные команды

```bash
# Установка
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка
cp .env.example .env
# Отредактировать .env

# Запуск мониторинга USB
python main.py monitor

# Обработка устройства/файла
python main.py process /media/usb0
python main.py process /path/to/file.wav
```

## Архитектура

```
neuro-caller/
├── src/
│   ├── usb_monitor.py          # Мониторинг USB устройств
│   ├── file_manager.py         # Копирование + S3 + Tracker (ThreadPoolExecutor)
│   ├── assemblyai_transcriber.py  # Транскрибация (опционально)
│   ├── telegram_notifier.py    # Telegram уведомления
│   ├── s3_uploader.py          # Загрузка в S3
│   └── tracker_client.py       # Яндекс Трекер API
├── test/                       # Тестовые скрипты
├── main.py                     # CLI интерфейс
└── data/
    └── processed_files.json    # Метаданные и стадии обработки
```

## Поток данных

```
USB → FileManager (ThreadPoolExecutor, 3 потока):
  → copy (copying → copied)
  → S3 upload (s3_uploading → s3_uploaded)
  → Tracker issue (tracker_creating → completed)
→ [Опционально] AssemblyAI транскрибация → output/*.txt
```

**Recovery**: При перезапуске система автоматически восстанавливает незавершённые задачи по стадиям в `processed_files.json`.

## Стадии обработки (stage)

1. `copying` — копирование с USB
2. `copied` — скопировано локально
3. `s3_uploading` — загрузка в S3
4. `s3_uploaded` — загружено в S3
5. `tracker_creating` — создание тикета
6. `completed` — готово

## Переменные окружения (.env)

```env
# AssemblyAI (транскрибация)
ASSEMBLYAI_API_KEY=...
DEFAULT_NUM_SPEAKERS=2
LANGUAGE=ru
TRANSCRIBE_CONVERSATION=false

# USB мониторинг
CHECK_INTERVAL=5
MAX_PARALLEL_COPIES=3

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_ENABLED=true

# S3 Object Storage
S3_ENABLED=true
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
S3_REGION_NAME=ru-central1
S3_PRESIGNED_URL_EXPIRY=604800

# Яндекс Трекер
TRACKER_ENABLED=true
TRACKER_OAUTH_TOKEN=...
TRACKER_QUEUE=YANGOSCOUTS

# Результаты
OUTPUT_DIR=output
LOG_LEVEL=INFO
```

## Ключевые особенности

1. **Параллельная обработка** — ThreadPoolExecutor (3 потока): copy → S3 → Tracker в одном потоке
2. **Recovery** — восстановление незавершённых задач по стадиям при перезапуске
3. **Уникальная идентификация устройств** — UUID > Serial > Label
4. **Атомарное сохранение** — `processed_files.json` через temp file + `os.replace()`
5. **Дата из имени файла** — `R20251124-120931.WAV` → S3 ключ `2025-11-24/device/...`

## Зависимости

```txt
pydub>=0.25.1          # Аудио (для транскрибации)
psutil>=5.9.0          # Мониторинг устройств
python-dotenv>=1.0.0   # Переменные окружения
aiogram>=3.0.0         # Telegram
boto3>=1.34.0          # S3
assemblyai>=0.28.0     # Транскрибация
requests>=2.31.0       # Яндекс Трекер
```

**Системные**: `ffmpeg` (для ffprobe и транскрибации)

## Правила разработки

- При добавлении переменных — обновлять `.env` и `.env.example`
- Тесты в папке `test/`
- Логи в `logs/transcription.log`
