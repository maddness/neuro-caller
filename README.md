# USB Audio Recorder Pipeline

Автоматическая система для обработки аудиозаписей с USB диктофонов: копирование, загрузка в S3, создание задач в Яндекс Трекере. Опционально: транскрибация через AssemblyAI.

## Возможности

- **Автоматическое обнаружение** USB диктофонов
- **Параллельная обработка** файлов (ThreadPoolExecutor)
- **S3 Object Storage** — загрузка в Yandex, AWS, MinIO
- **Яндекс Трекер** — автоматическое создание задач
- **Recovery** — восстановление после перезапуска
- **Telegram уведомления** на каждом этапе
- **Speaker Diarization** через AssemblyAI (опционально)
- **Форматы**: MP3, WAV, M4A, FLAC, OGG, AAC, WMA

## Быстрый старт

### 1. Установка

```bash
git clone <repo>
cd neuro-caller

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ffmpeg для работы с аудио
brew install ffmpeg  # MacOS
sudo apt-get install ffmpeg  # Ubuntu
```

### 2. Настройка

```bash
cp .env.example .env
nano .env
```

Минимальная конфигурация:

```env
# S3 Object Storage
S3_ENABLED=true
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_ACCESS_KEY_ID=your-key
S3_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=your-bucket
S3_REGION_NAME=ru-central1

# Яндекс Трекер
TRACKER_ENABLED=true
TRACKER_OAUTH_TOKEN=your-token
TRACKER_QUEUE=YOUR_QUEUE

# Telegram (опционально)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_ENABLED=true

# Транскрибация (опционально)
TRANSCRIBE_CONVERSATION=false
ASSEMBLYAI_API_KEY=your-key
```

### 3. Запуск

```bash
# Мониторинг USB устройств
python main.py monitor

# Обработка устройства или файла
python main.py process /media/usb0
python main.py process /path/to/audio.wav
```

## Как это работает

```
┌─────────────────┐
│  USB Диктофон   │
└────────┬────────┘
         │ Plug & Play
         ▼
┌─────────────────┐
│  USB Monitor    │  Обнаружение устройств
└────────┬────────┘
         ▼
┌─────────────────────────────────────────┐
│  FileManager (ThreadPoolExecutor × 3)   │
│                                         │
│  copying → copied → s3_uploading →      │
│  s3_uploaded → tracker_creating →       │
│  completed                              │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Telegram       │  Уведомления
└─────────────────┘
```

### Стадии обработки

Каждый файл проходит 6 стадий (сохраняются в `data/processed_files.json`):

1. `copying` — копирование с USB на локальный диск
2. `copied` — файл скопирован
3. `s3_uploading` — загрузка в S3
4. `s3_uploaded` — файл в S3
5. `tracker_creating` — создание задачи в Трекере
6. `completed` — готово

**Recovery**: При перезапуске система автоматически продолжает с прерванной стадии.

### Структура в S3

```
bucket/
├── 2025-11-24/
│   ├── DEVICE_001/
│   │   ├── R20251124-090000.WAV
│   │   └── R20251124-120000.WAV
│   └── DEVICE_002/
│       └── R20251124-150000.WAV
```

Дата извлекается из имени файла: `R20251124-120931.WAV` → `2025-11-24/`

## Структура проекта

```
neuro-caller/
├── src/
│   ├── usb_monitor.py          # Мониторинг USB
│   ├── file_manager.py         # Копирование + S3 + Tracker
│   ├── s3_uploader.py          # S3 клиент
│   ├── tracker_client.py       # Яндекс Трекер API
│   ├── telegram_notifier.py    # Telegram уведомления
│   └── assemblyai_transcriber.py  # Транскрибация
├── test/                       # Тесты
├── data/
│   └── processed_files.json    # Метаданные файлов
├── output/                     # Транскрипции (если включено)
├── logs/                       # Логи
├── main.py                     # CLI
├── requirements.txt
├── .env.example
└── README.md
```

## CLI команды

### monitor — Мониторинг USB

```bash
python main.py monitor [OPTIONS]

Options:
  --check-interval INT          Интервал проверки (сек, default: 5)
  --max-parallel-copies INT     Параллельных потоков (default: 3)
  --language TEXT               Язык для транскрибации (default: ru)
  --s3-enabled BOOL             Загрузка в S3
  --tracker-enabled BOOL        Создание задач в Трекере
  --telegram-enabled BOOL       Telegram уведомления
  --transcribe-conversation BOOL  Транскрибация через AssemblyAI
```

### process — Обработка файла/устройства

```bash
python main.py process PATH [OPTIONS]

Arguments:
  PATH    Путь к устройству или файлу
```

## Переменные окружения

Полный список в `.env.example`:

| Переменная | Описание | Default |
|------------|----------|---------|
| `S3_ENABLED` | Загрузка в S3 | `false` |
| `S3_ENDPOINT_URL` | URL S3 endpoint | — |
| `S3_BUCKET_NAME` | Имя бакета | — |
| `TRACKER_ENABLED` | Создание задач | `false` |
| `TRACKER_QUEUE` | Очередь в Трекере | — |
| `TELEGRAM_ENABLED` | Уведомления | `true` |
| `TRANSCRIBE_CONVERSATION` | Транскрибация | `false` |
| `MAX_PARALLEL_COPIES` | Потоков | `3` |
| `CHECK_INTERVAL` | Интервал проверки USB | `5` |

## Транскрибация (опционально)

Если `TRANSCRIBE_CONVERSATION=true`, после загрузки в S3 файлы транскрибируются через AssemblyAI с разделением по говорящим:

```env
TRANSCRIBE_CONVERSATION=true
ASSEMBLYAI_API_KEY=your-key
DEFAULT_NUM_SPEAKERS=2
LANGUAGE=ru
```

Результат сохраняется в `output/YYYY-MM-DD/DEVICE/filename.txt`

## Зависимости

```txt
pydub>=0.25.1          # Аудио
psutil>=5.9.0          # Системный мониторинг
python-dotenv>=1.0.0   # Переменные окружения
aiogram>=3.0.0         # Telegram
boto3>=1.34.0          # S3
assemblyai>=0.28.0     # Транскрибация
requests>=2.31.0       # HTTP (Трекер)
```

**Системные**: `ffmpeg`

## Лицензия

MIT License
