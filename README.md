# USB Audio Recorder Transcription Pipeline

Автоматическая система для транскрибации аудиозаписей с USB диктофонов через OpenAI Whisper API.

## Описание

Система автоматически обнаруживает подключение USB диктофонов, загружает новые аудиофайлы, разбивает их на части (если необходимо), транскрибирует через Whisper API и сохраняет результаты в локальную базу данных.

**Идеально подходит для:**
- Транскрибации разговоров агентов call-центра
- Автоматической обработки записей с диктофонов
- Создания текстовой базы данных из аудиозаписей
- Анализа разговоров на испанском языке (или любом другом)

## Возможности

- ✅ **Автоматическое обнаружение** USB диктофонов
- ✅ **Умное копирование** - только новые файлы
- ✅ **S3 Object Storage** - автоматическая загрузка файлов в облако (Yandex, AWS, MinIO)
- ✅ **Разделение больших файлов** на части с overlap
- ✅ **Транскрибация** через Yandex Eliza API (Whisper-совместимый)
- ✅ **Speaker Diarization** - разделение по говорящим через AssemblyAI
- ✅ **База данных** SQLite с полнотекстовым поиском
- ✅ **Telegram уведомления** о каждом этапе обработки + ссылки на скачивание из S3
- ✅ **Поддержка форматов**: MP3, WAV, M4A, FLAC, OGG, AAC, WMA
- ✅ **Многоязычность** - по умолчанию испанский (es)
- ✅ **CLI интерфейс** для всех операций

## Архитектура

```
┌─────────────────┐
│  USB Диктофон   │
└────────┬────────┘
         │ Plug & Play
         ▼
┌─────────────────┐
│  USB Monitor    │ ← Обнаружение устройств
└────────┬────────┘
         ▼
┌─────────────────┐
│  File Manager   │ ← Копирование новых файлов
└────────┬────────┘
         ▼
┌─────────────────┐
│ Audio Processor │ ← Разделение на части (если нужно)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Transcriber    │ ← OpenAI Whisper API
└────────┬────────┘
         ▼
┌─────────────────┐
│    Database     │ ← SQLite с FTS5 поиском
└─────────────────┘
```

## Быстрый старт

### 1. Установка зависимостей

```bash
# Клонирование репозитория
git clone <your-repo>
cd neuro-caller

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка Python пакетов
pip install -r requirements.txt

# Установка ffmpeg (необходим для pydub)
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# MacOS:
brew install ffmpeg

# Windows:
# Скачайте с https://ffmpeg.org/ и добавьте в PATH
```

### 2. Настройка

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем .env и добавляем ваш OpenAI API ключ
nano .env
```

Содержимое `.env`:
```env
# Yandex Eliza API (Whisper-совместимый)
SOY_TOKEN=y1_your-yandex-oauth-token-here

# AssemblyAI для speaker diarization (опционально)
ASSEMBLYAI_API_KEY=your-assemblyai-api-key-here
USE_ASSEMBLYAI=false  # true для использования AssemblyAI с diarization
DEFAULT_NUM_SPEAKERS=2

LANGUAGE=ru
CHUNK_LENGTH_MINUTES=10
OVERLAP_SECONDS=10
CHECK_INTERVAL=5
LOG_LEVEL=INFO

# Telegram уведомления (опционально)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
TELEGRAM_ENABLED=true

# S3 Object Storage (опционально)
S3_ENABLED=false
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=neuro-caller-audio
S3_REGION_NAME=ru-central1
S3_STORAGE_CLASS=STANDARD
S3_PRESIGNED_URL_EXPIRY=604800
```

**Настройка Telegram уведомлений (опционально):**

Система может отправлять уведомления в Telegram о каждом этапе обработки. Подробная инструкция: [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)

Кратко:
1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите Chat ID через [@userinfobot](https://t.me/userinfobot)
3. Добавьте в `.env` файл

**Настройка S3 Object Storage (опционально):**

Система может автоматически загружать аудиофайлы в S3-совместимое хранилище (Yandex Object Storage, AWS S3, MinIO) сразу после копирования с USB.

Преимущества:
- 📤 **Автоматическая загрузка** файлов в облако
- 🔗 **Ссылки для скачивания** в Telegram уведомлениях (действительны 7 дней)
- ☁️ **Надежное хранение** с резервным копированием
- 💰 **Экономия места** на локальном диске (опционально)

Быстрая настройка для **Yandex Object Storage**:

1. Создайте бакет в [Yandex Object Storage](https://console.cloud.yandex.ru/folders/XXX/storage)
2. Создайте сервисный аккаунт и статический ключ доступа
3. Добавьте параметры в `.env`:

```env
# Включить S3 загрузку
S3_ENABLED=true

# Yandex Object Storage
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_REGION_NAME=ru-central1
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=neuro-caller-audio

# Класс хранилища (STANDARD, COLD, ICE)
S3_STORAGE_CLASS=STANDARD

# Время жизни ссылок для скачивания (7 дней)
S3_PRESIGNED_URL_EXPIRY=604800
```

**Структура файлов в S3:**
```
neuro-caller-audio/
├── 2025_11_20/
│   ├── PERU_003/
│   │   ├── R20251115-162324.WAV
│   │   └── R20251115-165530.WAV
│   └── Agent_001/
│       └── recording_001.WAV
└── 2025_11_21/
    └── PERU_003/
        └── R20251121-090015.WAV
```

**Поддерживаемые S3-провайдеры:**
- ☁️ Yandex Object Storage (рекомендуется)
- ☁️ AWS S3
- ☁️ Selectel Object Storage
- ☁️ VK Cloud Solutions
- 🏠 MinIO (self-hosted)

### 3. Запуск

#### Режим мониторинга (автоматический)

```bash
python main.py monitor
```

Теперь просто подключите USB диктофон - система автоматически обработает все новые файлы!

#### Обработка конкретного устройства

```bash
python main.py process /media/usb0
```

#### Обработка отдельного файла

```bash
python main.py process /path/to/audio.mp3
```

## Команды CLI

### Monitor - Непрерывный мониторинг

```bash
python main.py monitor [OPTIONS]

Options:
  --check-interval INT       Интервал проверки устройств в секундах (по умолчанию: 5)
  --api-key TEXT            Yandex OAuth токен (SOY_TOKEN)
  --assemblyai-api-key TEXT AssemblyAI API ключ
  --use-assemblyai BOOL     Использовать AssemblyAI с diarization (по умолчанию: false)
  --num-speakers INT        Количество говорящих для diarization (по умолчанию: 2)
  --language TEXT           Язык аудио: ru, es, en и т.д. (по умолчанию: ru)
  --chunk-length INT        Длина чанка в минутах (по умолчанию: 10)
  --overlap INT             Overlap между чанками в секундах (по умолчанию: 10)
```

**Примеры:**
```bash
# Базовая транскрипция через Yandex Eliza
python main.py monitor --language ru

# С разделением по говорящим через AssemblyAI
python main.py monitor --use-assemblyai true --num-speakers 2
```

### Process - Обработка файла или устройства

```bash
python main.py process PATH [OPTIONS]

Arguments:
  PATH                      Путь к устройству или аудиофайлу

Options:
  --api-key TEXT            Yandex OAuth токен (SOY_TOKEN)
  --assemblyai-api-key TEXT AssemblyAI API ключ
  --use-assemblyai BOOL     Использовать AssemblyAI с diarization
  --num-speakers INT        Количество говорящих
  --language TEXT           Язык аудио (по умолчанию: ru)
  --chunk-length INT        Длина чанка в минутах
  --overlap INT             Overlap в секундах
```

**Примеры:**
```bash
# Обработка устройства
python main.py process /media/usb0

# Обработка файла с diarization
python main.py process /path/to/audio.mp3 --use-assemblyai true

# Обработка файла
python main.py process /home/user/recording.mp3 --language es
```

### Stats - Статистика

```bash
python main.py stats
```

Показывает:
- Общее количество транскрипций
- Общую длительность записей
- Количество слов
- Статистику по устройствам
- Статистику по дням

### Search - Поиск в транскрипциях

```bash
python main.py search [QUERY] [OPTIONS]

Arguments:
  QUERY                  Текст для поиска (опционально)

Options:
  --device TEXT          Фильтр по устройству
  --date-from TEXT       Дата начала (YYYY-MM-DD)
  --date-to TEXT         Дата окончания (YYYY-MM-DD)
  --limit INT            Максимум результатов (по умолчанию: 20)
```

**Примеры:**
```bash
# Полнотекстовый поиск
python main.py search "problema cliente"

# Поиск по устройству
python main.py search --device USB_Device_1

# Поиск за период
python main.py search --date-from 2024-01-01 --date-to 2024-01-31

# Комбинированный поиск
python main.py search "taxi" --device USB_Device_1 --limit 50
```

## Speaker Diarization - Разделение по говорящим

Система поддерживает два режима работы:

### 1. Базовая транскрипция (Yandex Eliza)
- Быстрая транскрипция без разделения по говорящим
- Использует Yandex Eliza API (Whisper-совместимый)
- Бесплатный или низкая стоимость

### 2. С разделением по говорящим (AssemblyAI)
- Автоматически определяет разных говорящих
- Форматирует текст как диалог: "Собеседник A: ...", "Собеседник B: ..."
- Показывает статистику по каждому говорящему
- Стоимость: ~$0.90 за час аудио

**Пример вывода с diarization:**
```
Собеседник A: Здравствуйте, это служба поддержки. Чем могу помочь?

Собеседник B: Здравствуйте! У меня проблема с заказом номер 12345.

Собеседник A: Сейчас проверю. Один момент, пожалуйста.

Собеседник B: Хорошо, спасибо.
```

**Включение diarization:**

В `.env`:
```env
USE_ASSEMBLYAI=true
ASSEMBLYAI_API_KEY=your-api-key-here
DEFAULT_NUM_SPEAKERS=2
```

Или через CLI:
```bash
python main.py monitor --use-assemblyai true --num-speakers 2
```

## Структура проекта

```
neuro-caller/
├── src/
│   ├── __init__.py
│   ├── usb_monitor.py             # Мониторинг USB устройств
│   ├── file_manager.py            # Управление файлами
│   ├── audio_processor.py         # Обработка аудио
│   ├── transcriber.py             # Транскрибация через Yandex Eliza
│   ├── assemblyai_transcriber.py  # Speaker diarization через AssemblyAI
│   ├── telegram_notifier.py       # Telegram уведомления
│   └── database.py                # База данных SQLite
├── data/
│   ├── audio/                     # Скопированные аудиофайлы
│   ├── transcriptions/            # Текстовые транскрипции
│   ├── transcriptions.db          # База данных
│   └── processed_files.json       # Реестр обработанных файлов
├── output/                        # Текстовые файлы транскрипций
├── logs/
│   └── transcription.log          # Логи
├── main.py                        # Главный CLI
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Как это работает

### 1. Обнаружение устройств

`USBMonitor` отслеживает подключение новых USB устройств:
- Мониторит точки монтирования (`/media`, `/mnt`)
- Проверяет системные флаги removable устройств
- Идентифицирует аудио диктофоны по наличию аудиофайлов

**Уникальная идентификация устройств:**

Система использует уникальные идентификаторы для различения разных флешек, даже если они монтируются в одну и ту же точку монтирования:

- **UUID** - уникальный идентификатор файловой системы (приоритет 1)
- **Serial Number** - серийный номер USB устройства (приоритет 2)
- **Label** - метка тома (приоритет 3)
- **Точка монтирования** - fallback если остальное недоступно

Пример:
```
🔌 Новое устройство подключено: /media/usb0
   Уникальный ID: UUID_1a2b3c4d
   Метка: AGENT_001
   UUID: 1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6
```

Таким образом, файлы с флешки "AGENT_001" будут сохранены отдельно от файлов с флешки "AGENT_002", даже если обе подключаются к `/media/usb0`.

### 2. Управление файлами

`FileManager` обрабатывает аудиофайлы:
- Вычисляет MD5 хеш для каждого файла
- Проверяет, был ли файл обработан ранее
- Копирует только новые файлы в локальное хранилище
- Организует файлы по дате и устройству

### 3. Обработка аудио

`AudioProcessor` подготавливает файлы для транскрибации:
- Загружает аудио через pydub
- Разделяет большие файлы на части (макс 24MB для Whisper)
- Добавляет overlap между частями для плавности
- Сохраняет чанки во временные файлы

### 4. Транскрибация

`WhisperTranscriber` обращается к OpenAI API:
- Отправляет аудио на Whisper API
- Указывает язык для лучшего качества
- Обрабатывает каждый чанк отдельно
- Объединяет результаты в единый текст

### 5. База данных

`TranscriptionDatabase` хранит результаты:
- SQLite база с FTS5 полнотекстовым поиском
- Хранит транскрипции с метаданными
- Поддерживает быстрый поиск по тексту
- Собирает статистику

## Стоимость использования

### OpenAI Whisper API

- **Модель**: whisper-1
- **Стоимость**: $0.006 за минуту аудио
- **Пример**: 1 час записи = $0.36

### Примеры расчета

| Длительность | Стоимость |
|-------------|-----------|
| 5 минут     | $0.03     |
| 1 час       | $0.36     |
| 8 часов     | $2.88     |
| 1 месяц (160ч) | $57.60 |

## Производительность

- **Скорость транскрибации**: ~0.1x от длительности аудио (10 минут аудио = ~1 минута обработки)
- **Точность**: 95%+ для чистого испанского аудио
- **Размер БД**: ~1KB текста на 1 минуту аудио

## Ограничения

- **Максимальный размер файла**: 25MB для Whisper API (автоматически разделяется)
- **Форматы**: MP3, WAV, M4A, FLAC, OGG, AAC, WMA, OPUS
- **Языки**: Все языки поддерживаемые Whisper (60+)

## Устранение неполадок

### USB устройство не обнаруживается

```bash
# Проверьте смонтированные устройства
lsblk

# Проверьте точки монтирования
df -h

# Проверьте права доступа
ls -la /media/
```

### Ошибки ffmpeg

```bash
# Проверьте установку ffmpeg
ffmpeg -version

# Переустановите если нужно
sudo apt-get install --reinstall ffmpeg
```

### Ошибки OpenAI API

- Проверьте баланс на OpenAI
- Проверьте корректность API ключа
- Проверьте интернет соединение

## Примеры использования

### Сценарий 1: Call-центр

Агенты используют USB диктофоны для записи разговоров. Вечером они подключают диктофоны к компьютеру с запущенным monitor режимом:

```bash
python main.py monitor --language es
```

Система автоматически:
1. Обнаруживает подключение диктофона
2. Копирует новые записи
3. Транскрибирует все разговоры
4. Сохраняет в базу данных

Утром менеджер может искать по ключевым словам:

```bash
python main.py search "problema" --date-from 2024-01-10
```

### Сценарий 2: Ручная обработка

Обработка конкретного файла:

```bash
python main.py process ~/Downloads/meeting.mp3 --language es
```

### Сценарий 3: Анализ статистики

```bash
# Общая статистика
python main.py stats

# Поиск конкретного агента
python main.py search --device Agent_001_Device

# Поиск за неделю
python main.py search --date-from 2024-01-01 --date-to 2024-01-07
```

## Лицензия

MIT License

## Поддержка

Для вопросов и предложений создавайте Issues в репозитории.

---

**Made with ❤️ for automated audio transcription**
