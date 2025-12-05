#!/usr/bin/env python3
"""
USB Audio Recorder Transcription Pipeline
Автоматическая транскрибация аудиозаписей с USB диктофонов
"""

__version__ = "0.5"

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

import subprocess

from src.usb_monitor import USBMonitor
from src.file_manager import FileManager
from src.assemblyai_transcriber import AssemblyAITranscriber
from src.telegram_notifier import TelegramNotifier
from src.s3_uploader import S3Uploader
from src.tracker_client import TrackerClient


# Настройка логирования
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Настройка системы логирования"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handlers = [logging.StreamHandler()]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )


def get_audio_info(file_path: Path) -> dict:
    """Получение информации об аудиофайле через ffprobe"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'format=duration,size', '-of', 'default=noprint_wrappers=1',
             str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            duration = 0
            for line in result.stdout.strip().split('\n'):
                if line.startswith('duration='):
                    duration = float(line.split('=')[1])

            return {
                "duration_seconds": duration,
                "duration_minutes": duration / 60,
                "file_size_mb": file_path.stat().st_size / (1024 * 1024),
                "format": file_path.suffix.lstrip('.').lower()
            }
    except Exception:
        pass
    return {"duration_seconds": 0, "duration_minutes": 0, "file_size_mb": 0, "format": ""}


class TranscriptionPipeline:
    """Главный пайплайн для обработки аудиозаписей"""

    def __init__(
        self,
        assemblyai_api_key: str = None,
        language: str = "es",
        num_speakers: int = 2,
        telegram_bot_token: str = None,
        telegram_chat_id: str = None,
        telegram_enabled: bool = True,
        s3_enabled: bool = False,
        s3_endpoint_url: str = None,
        s3_access_key_id: str = None,
        s3_secret_access_key: str = None,
        s3_bucket_name: str = None,
        s3_region_name: str = "ru-central1",
        s3_storage_class: str = "STANDARD",
        s3_retry_attempts: int = 3,
        s3_timeout: int = 300,
        s3_presigned_url_expiry: int = 604800,
        tracker_enabled: bool = False,
        tracker_oauth_token: str = None,
        tracker_queue: str = "YANGOSCOUTS",
        transcribe_conversation: bool = True,
        max_parallel_copies: int = 3
    ):
        """
        Args:
            assemblyai_api_key: AssemblyAI API ключ
            language: Язык аудио (ISO-639-1)
            num_speakers: Количество говорящих (для diarization)
            telegram_bot_token: Токен Telegram бота
            telegram_chat_id: ID чата для уведомлений
            telegram_enabled: Включены ли Telegram уведомления
            s3_enabled: Включена ли загрузка в S3
            s3_endpoint_url: URL S3 endpoint
            s3_access_key_id: S3 Access Key ID
            s3_secret_access_key: S3 Secret Access Key
            s3_bucket_name: Имя S3 бакета
            s3_region_name: Регион S3
            s3_storage_class: Класс хранилища S3
            s3_retry_attempts: Количество повторных попыток
            s3_timeout: Таймаут загрузки в секундах
            s3_presigned_url_expiry: Время жизни presigned URL в секундах
            tracker_enabled: Включено ли создание задач в трекере
            tracker_oauth_token: OAuth токен для Яндекс Трекера
            tracker_queue: Очередь для создания задач
            transcribe_conversation: Выполнять транскрибацию разговоров (если False, процесс остановится после создания задач)
            max_parallel_copies: Количество параллельных потоков для копирования файлов
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Инициализация компонентов
        self.logger.info("Initializing pipeline components...")

        self.num_speakers = num_speakers
        self.transcribe_conversation = transcribe_conversation

        # S3 параметры
        self.s3_enabled = s3_enabled
        self.s3_storage_class = s3_storage_class
        self.s3_presigned_url_expiry = s3_presigned_url_expiry

        self.file_manager = FileManager(max_workers=max_parallel_copies)

        # Транскрайбер AssemblyAI (опциональный)
        if transcribe_conversation:
            self.transcriber = AssemblyAITranscriber(
                api_key=assemblyai_api_key,
                language=language
            )
            self.logger.info("Using AssemblyAI (with diarization)")
        else:
            self.transcriber = None
            self.logger.info("Transcription disabled (TRANSCRIBE_CONVERSATION=false)")

        # Telegram уведомления
        self.telegram = TelegramNotifier(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
            enabled=telegram_enabled
        )

        # Передаем TelegramNotifier в FileManager
        self.file_manager.telegram_notifier = self.telegram

        # S3 Object Storage
        self.s3_uploader = None
        if s3_enabled and all([s3_endpoint_url, s3_access_key_id, s3_secret_access_key, s3_bucket_name]):
            try:
                self.s3_uploader = S3Uploader(
                    endpoint_url=s3_endpoint_url,
                    access_key_id=s3_access_key_id,
                    secret_access_key=s3_secret_access_key,
                    bucket_name=s3_bucket_name,
                    region_name=s3_region_name,
                    retry_attempts=s3_retry_attempts,
                    timeout=s3_timeout
                )
                # Передаем S3Uploader в FileManager
                self.file_manager.s3_uploader = self.s3_uploader
                self.logger.info("S3 Object Storage initialized")
            except Exception as e:
                self.logger.error(f"S3 initialization error: {e}")
                self.s3_enabled = False
        elif s3_enabled:
            self.logger.warning("S3 enabled but not all parameters set. S3 will be disabled.")
            self.s3_enabled = False

        # Яндекс Трекер
        self.tracker = TrackerClient(
            oauth_token=tracker_oauth_token,
            queue=tracker_queue,
            enabled=tracker_enabled
        )
        if tracker_enabled and self.tracker.enabled:
            self.logger.info(f"Yandex Tracker initialized (queue: {tracker_queue})")

        # Передаём Tracker в FileManager для создания тикетов в ThreadPoolExecutor
        self.file_manager.tracker_client = self.tracker
        self.file_manager.s3_presigned_url_expiry = self.s3_presigned_url_expiry
        self.file_manager.transcribe_conversation = self.transcribe_conversation

        self.logger.info("Pipeline ready")

    def save_transcription_to_file(
        self,
        transcription_text: str,
        filename: str,
        device_name: str,
        audio_info: dict,
        transcription: dict = None
    ):
        """
        Сохранение транскрипции в текстовый файл

        Args:
            transcription_text: Текст транскрипции
            filename: Имя исходного файла
            device_name: Имя устройства
            audio_info: Информация об аудио
            transcription: Полные данные транскрибации (для diarization)
        """
        import os
        from datetime import datetime

        # Получаем путь из .env или используем дефолт
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))

        # Создаем структуру: output/YYYY-MM-DD/DEVICE_NAME/
        date_folder = datetime.now().strftime("%Y-%m-%d")
        device_folder = device_name or "unknown_device"
        output_path = output_dir / date_folder / device_folder
        output_path.mkdir(parents=True, exist_ok=True)

        # Имя файла: оригинальное_имя.txt
        text_filename = Path(filename).stem + ".txt"
        output_file = output_path / text_filename

        # Формируем заголовок
        content = f"""{'='*80}
ТРАНСКРИПЦИЯ АУДИОЗАПИСИ
{'='*80}

Файл: {filename}
Устройство: {device_name}
Дата обработки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Длительность: {audio_info.get('duration_minutes', 0):.2f} мин ({audio_info.get('duration_seconds', 0):.1f} сек)
Размер файла: {audio_info.get('file_size_mb', 0):.2f} MB
"""

        # Добавляем информацию о говорящих если есть diarization
        if transcription and 'speaker_stats' in transcription:
            content += f"\n{'='*80}\n"
            content += "СТАТИСТИКА ПО ГОВОРЯЩИМ\n"
            content += f"{'='*80}\n\n"

            for speaker, stats in transcription['speaker_stats'].items():
                speaker_label = f"Собеседник {speaker}"
                content += f"{speaker_label}:\n"
                content += f"  Реплик: {stats['utterances']}\n"
                content += f"  Время: {stats['total_time']:.1f} сек ({stats['total_time']/60:.1f} мин)\n"
                content += f"  Слов: {stats['words']}\n\n"

        content += f"\n{'='*80}\n"
        content += "ТЕКСТ\n"
        content += f"{'='*80}\n\n"

        # Форматируем текст с учетом diarization
        if transcription and 'segments' in transcription and transcription.get('segments'):
            # С разделением по говорящим и таймстемпами
            if hasattr(self.transcriber, 'format_transcript_text'):
                formatted_text = self.transcriber.format_transcript_text(transcription, filename=filename)
                content += formatted_text
            else:
                # Fallback: ручное форматирование без таймстемпов
                current_speaker = None
                current_text = []

                for segment in transcription['segments']:
                    speaker = segment['speaker']

                    if speaker != current_speaker:
                        # Сохраняем предыдущего говорящего
                        if current_text:
                            speaker_label = f"Собеседник {current_speaker}"
                            content += f"{speaker_label}: {' '.join(current_text)}\n\n"

                        current_speaker = speaker
                        current_text = [segment['text']]
                    else:
                        current_text.append(segment['text'])

                # Последний говорящий
                if current_text:
                    speaker_label = f"Собеседник {current_speaker}"
                    content += f"{speaker_label}: {' '.join(current_text)}\n"
        else:
            # Без разделения (обычная транскрипция)
            content += transcription_text

        content += f"""

{'='*80}
Количество слов: {len(transcription_text.split())}
Количество символов: {len(transcription_text)}
{'='*80}
"""

        # Сохраняем файл
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Transcription saved to: {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving to file {output_file}: {e}")

    def process_device(self, device_path: str, device_name: str = None):
        """
        Обработка всех новых файлов с устройства

        Args:
            device_path: Путь к подключенному устройству
            device_name: Уникальное имя устройства (получается автоматически если None)
        """
        # Получаем информацию об устройстве
        from src.usb_monitor import USBMonitor

        if device_name is None:
            device_info = USBMonitor.get_device_info(device_path)
            device_name = device_info['unique_id']

            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing device: {device_path}")
            self.logger.info(f"Unique ID: {device_name}")
            if device_info['label']:
                self.logger.info(f"Label: {device_info['label']}")
            if device_info['uuid']:
                self.logger.info(f"UUID: {device_info['uuid'][:16]}...")
            self.logger.info(f"{'='*60}\n")
        else:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing device: {device_path}")
            self.logger.info(f"Device ID: {device_name}")
            self.logger.info(f"{'='*60}\n")

        # ============================================================
        # RECOVERY: ВОССТАНОВЛЕНИЕ НЕЗАВЕРШЁННЫХ ЗАДАЧ
        # ============================================================
        incomplete_tasks = self.file_manager.recover_incomplete_tasks()
        if incomplete_tasks:
            self.logger.info(f"\nRecovering {len(incomplete_tasks)} incomplete tasks...")
            self.process_incomplete_tasks(incomplete_tasks)

        # ============================================================
        # ЭТАП 1: КОПИРОВАНИЕ ВСЕХ ФАЙЛОВ С ФЛЕШКИ НА ЖЕСТКИЙ ДИСК
        # ============================================================
        self.logger.info("STAGE 1: Finding and copying new audio files...")
        self.logger.info("   (First copy ALL files, then process)")

        copied_files = self.file_manager.process_new_files(device_path, device_name=device_name)

        if not copied_files:
            self.logger.info("No new files found")
            return

        self.logger.info(f"\nALL FILES COPIED TO DISK: {len(copied_files)} files")
        self.logger.info("   You can now safely disconnect the flash drive")

        # Telegram: уведомление об окончании копирования
        self.telegram.notify_copying_complete(
            files_count=len(copied_files),
            device_name=device_name
        )

        # ============================================================
        # ПРОВЕРКА: НУЖНА ЛИ ТРАНСКРИБАЦИЯ
        # ============================================================
        if not self.transcribe_conversation:
            self.logger.info("\nTranscription disabled (TRANSCRIBE_CONVERSATION=false)")
            self.logger.info("   Process completed after creating tracker issues")
            return

        # ============================================================
        # ЭТАП 2: ОБРАБОТКА СКОПИРОВАННЫХ ФАЙЛОВ
        # ============================================================
        self.logger.info(f"\nSTAGE 2: Transcribing files ({len(copied_files)} pcs)")
        self.logger.info("   (Transcription with speaker diarization via AssemblyAI)")

        # Telegram: уведомление о начале обработки
        self.telegram.notify_processing_started(files_count=len(copied_files))

        for i, file_info in enumerate(copied_files, 1):
            self.logger.info(f"\n{'─'*60}")
            self.logger.info(f"File {i}/{len(copied_files)}: {Path(file_info['local_path']).name}")
            self.logger.info(f"{'─'*60}")
            self.process_file(file_info, file_num=i, total_files=len(copied_files))

    def process_incomplete_tasks(self, incomplete_tasks: list):
        """
        Обработка незавершённых задач после recovery.

        Args:
            incomplete_tasks: Список задач от recover_incomplete_tasks()
        """
        from pathlib import Path

        for task in incomplete_tasks:
            file_key = task["file_key"]
            meta = task["meta"]
            action = task["action"]

            self.logger.info(f"   🔄 {file_key}: {action}")

            if action == "copy":
                # Копирование прервано - файл возможно повреждён
                # Удаляем из метаданных, чтобы при следующем сканировании
                # он был найден как новый
                original_path = meta.get("original_path")
                if original_path and Path(original_path).exists():
                    # Удаляем запись из метаданных
                    if file_key in self.file_manager.processed_files:
                        del self.file_manager.processed_files[file_key]
                        self.file_manager._save_processed_files()
                    self.logger.info(f"      -> Removed from metadata, will be copied again")
                else:
                    self.logger.warning(f"      -> Original file not found: {original_path}")

            elif action == "s3_upload":
                # Нужна загрузка в S3
                local_path = meta.get("local_path")
                if local_path and Path(local_path).exists():
                    # Get original filename for later use
                    original_filename = Path(meta.get("original_path", local_path)).name

                    # Используем существующий s3_key если есть, иначе формируем новый
                    s3_key = meta.get("s3_key")
                    if not s3_key:
                        # Извлекаем device из file_key (формат: DEVICE_filename.WAV)
                        device = meta.get("device")
                        if not device:
                            # Пробуем извлечь из file_key: PERU_000_R20251126-120130.WAV
                            parts = file_key.rsplit("_R", 1)
                            device = parts[0] if len(parts) == 2 else "unknown"

                        # Формируем S3 ключ с датой из имени файла
                        from src.file_manager import FileManager
                        date_folder = FileManager.extract_date_from_filename(original_filename)
                        s3_key = f"{date_folder}/{device}/{original_filename}"

                    # STAGE: s3_uploading
                    self.file_manager.update_metadata(file_key, {"stage": "s3_uploading"})

                    # Check if file exists in S3
                    exists, exists_error = self.s3_uploader.file_exists(s3_key)

                    if exists_error:
                        self.logger.warning(f"      -> S3 check failed: {exists_error}, will try to upload")

                    if exists and not exists_error:
                        self.logger.info(f"      -> Already in S3: {s3_key}")
                        self.file_manager.update_metadata(file_key, {
                            "stage": "s3_uploaded",
                            "s3_key": s3_key
                        })
                        # Telegram notification
                        if self.telegram:
                            size_mb = meta.get("size_bytes", 0) / (1024 * 1024)
                            self.telegram.notify_s3_already_exists(s3_key=s3_key, size_mb=size_mb)

                        # Create ticket if not exists
                        if self.tracker.enabled and not meta.get("tracker_issue_key"):
                            self.file_manager.update_metadata(file_key, {"stage": "tracker_creating"})
                            presigned_url = self.s3_uploader.generate_presigned_url(
                                s3_key=s3_key,
                                expiration=self.s3_presigned_url_expiry
                            )
                            if presigned_url:
                                from src.tracker_client import TrackerClient
                                summary = TrackerClient.build_summary_from_s3_key(s3_key)
                                issue = self.tracker.create_issue(
                                    summary=summary,
                                    description=presigned_url,
                                    transcribe_conversation=self.transcribe_conversation
                                )
                                if issue:
                                    issue_key = issue.get('key')
                                    issue_url = issue.get('self')
                                    self.logger.info(f"      -> Issue created: {issue_key}")
                                    self.file_manager.update_metadata(file_key, {
                                        "stage": "completed",
                                        "tracker_issue_key": issue_key,
                                        "tracker_url": issue_url
                                    })
                                    if self.telegram:
                                        self.telegram.notify_tracker_issue_created(
                                            issue_key=issue_key,
                                            s3_key=s3_key,
                                            issue_url=issue_url
                                        )
                    else:
                        # Upload file
                        s3_success, s3_error = self.s3_uploader.upload_file(
                            file_path=Path(local_path),
                            s3_key=s3_key
                        )
                        if s3_success:
                            self.logger.info(f"      -> Uploaded to S3: {s3_key}")
                            self.file_manager.update_metadata(file_key, {
                                "stage": "s3_uploaded",
                                "s3_key": s3_key
                            })
                            # Telegram уведомление
                            if self.telegram:
                                size_mb = meta.get("size_bytes", 0) / (1024 * 1024)
                                self.telegram.notify_s3_upload(
                                    filename=original_filename,
                                    s3_key=s3_key,
                                    size_mb=size_mb
                                )

                            # Сразу создаём тикет после загрузки в S3
                            if self.tracker.enabled:
                                self.file_manager.update_metadata(file_key, {"stage": "tracker_creating"})
                                presigned_url = self.s3_uploader.generate_presigned_url(
                                    s3_key=s3_key,
                                    expiration=self.s3_presigned_url_expiry
                                )
                                if presigned_url:
                                    from src.tracker_client import TrackerClient
                                    summary = TrackerClient.build_summary_from_s3_key(s3_key)
                                    issue = self.tracker.create_issue(
                                        summary=summary,
                                        description=presigned_url,
                                        transcribe_conversation=self.transcribe_conversation
                                    )
                                    if issue:
                                        issue_key = issue.get('key')
                                        issue_url = issue.get('self')
                                        self.logger.info(f"      -> Issue created: {issue_key}")
                                        self.file_manager.update_metadata(file_key, {
                                            "stage": "completed",
                                            "tracker_issue_key": issue_key,
                                            "tracker_url": issue_url
                                        })
                                        if self.telegram:
                                            self.telegram.notify_tracker_issue_created(
                                                issue_key=issue_key,
                                                s3_key=s3_key,
                                                issue_url=issue_url
                                            )
                        else:
                            self.logger.error(f"      -> S3 upload error: {s3_error}")
                            if self.telegram:
                                self.telegram.notify_s3_upload_error(
                                    filename=original_filename,
                                    error_message=s3_error or "Upload failed"
                                )
                else:
                    self.logger.warning(f"      -> Local file not found: {local_path}")

            elif action == "tracker":
                # Нужно создание тикета
                s3_key = meta.get("s3_key")
                if s3_key and not meta.get("tracker_issue_key") and self.s3_uploader:
                    # STAGE: tracker_creating
                    self.file_manager.update_metadata(file_key, {"stage": "tracker_creating"})

                    # Генерируем presigned URL
                    presigned_url = self.s3_uploader.generate_presigned_url(
                        s3_key=s3_key,
                        expiration=self.s3_presigned_url_expiry
                    )

                    if presigned_url:
                        from src.tracker_client import TrackerClient
                        summary = TrackerClient.build_summary_from_s3_key(s3_key)
                        issue = self.tracker.create_issue(
                            summary=summary,
                            description=presigned_url,
                            transcribe_conversation=self.transcribe_conversation
                        )
                        if issue:
                            issue_key = issue.get('key')
                            issue_url = issue.get('self')
                            self.logger.info(f"      -> Issue created: {issue_key}")

                            # STAGE: completed
                            self.file_manager.update_metadata(file_key, {
                                "stage": "completed",
                                "tracker_issue_key": issue_key,
                                "tracker_url": issue_url
                            })

                            # Telegram уведомление
                            if self.telegram:
                                self.telegram.notify_tracker_issue_created(
                                    issue_key=issue_key,
                                    s3_key=s3_key,
                                    issue_url=issue_url
                                )
                        else:
                            self.logger.error(f"      -> Issue creation error")
                    else:
                        self.logger.error(f"      -> Failed to generate presigned URL")
                elif meta.get("tracker_issue_key"):
                    # Тикет уже создан, просто обновляем stage
                    self.file_manager.update_metadata(file_key, {"stage": "completed"})
                    self.logger.info(f"      -> Issue already exists: {meta.get('tracker_issue_key')}")

        self.logger.info(f"Recovery completed: {len(incomplete_tasks)} tasks processed")

    def process_file(self, file_info: dict, file_num: int = 1, total_files: int = 1):
        """
        Обработка одного аудиофайла: разделение, транскрибация, сохранение

        Args:
            file_info: Информация о файле из FileManager
            file_num: Номер файла в очереди
            total_files: Всего файлов в очереди
        """
        file_path = Path(file_info['local_path'])
        filename = file_path.name

        # Получаем ключ файла из file_info или из processed_files
        file_key = file_info.get('file_key') or next(
            (k for k, v in self.file_manager.processed_files.items()
             if v.get('local_path') == str(file_path)),
            None
        )

        try:
            # Получение информации о файле
            audio_info = get_audio_info(file_path)
            self.logger.info(
                f"📊 Файл: {audio_info['duration_minutes']:.1f} мин, "
                f"{audio_info['file_size_mb']:.1f} MB, "
                f"{audio_info['format'].upper()}"
            )

            # Telegram: уведомление о начале обработки файла
            self.telegram.notify_file_processing(
                file_num=file_num,
                total_files=total_files,
                filename=filename,
                duration_min=audio_info['duration_minutes'],
                size_mb=audio_info['file_size_mb']
            )

            # ПРОВЕРКА: НУЖНА ЛИ ТРАНСКРИБАЦИЯ
            if not self.transcribe_conversation:
                self.logger.info("Transcription disabled (TRANSCRIBE_CONVERSATION=false)")
                self.logger.info("   File copied, transcription skipped")
                return

            # Транскрибация через AssemblyAI
            self.logger.info("Sending to AssemblyAI for transcription with diarization...")
            transcription = self.transcriber.transcribe_with_speakers(
                file_path,
                num_speakers=self.num_speakers
            )

            # Отмечаем файл как обработанный
            if file_key:
                self.file_manager.mark_as_processed(file_key)

            # Сохраняем транскрипцию в текстовый файл
            self.save_transcription_to_file(
                transcription_text=transcription['text'],
                filename=filename,
                device_name=file_info.get('device', 'unknown'),
                audio_info=audio_info,
                transcription=transcription
            )

            word_count = len(transcription['text'].split())
            char_count = len(transcription['text'])

            self.logger.info(f"\nDONE!")
            self.logger.info(f"   Characters: {char_count}, Words: {word_count}")
            self.logger.info(f"   Preview: {transcription['text'][:100]}...")

            # Telegram: уведомление об окончании транскрибации файла
            speaker_stats = transcription.get('speaker_stats') if transcription else None

            # Форматируем текст с таймстемпами и разбивкой по говорящим для Telegram
            if transcription and 'segments' in transcription:
                transcription_text = self.transcriber.format_transcript_text(transcription, filename=filename)
            else:
                transcription_text = transcription.get('text', '') if transcription else ''

            self.telegram.notify_transcription_complete(
                file_num=file_num,
                total_files=total_files,
                filename=filename,
                word_count=word_count,
                char_count=char_count,
                speaker_stats=speaker_stats,
                transcription_preview=transcription_text
            )

        except Exception as e:
            self.logger.error(f"\nERROR: {e}", exc_info=True)

            # Telegram: уведомление об ошибке
            self.telegram.notify_error(
                error_message=str(e),
                filename=filename
            )


def monitor_mode(args):
    """Режим непрерывного мониторинга USB устройств"""
    import threading
    import time

    logger = logging.getLogger("monitor_mode")
    logger.info("Starting USB device monitoring mode...")

    pipeline = TranscriptionPipeline(
        assemblyai_api_key=getattr(args, 'assemblyai_api_key', None),
        language=args.language,
        num_speakers=getattr(args, 'num_speakers', 2),
        telegram_bot_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat,
        telegram_enabled=args.telegram_enabled,
        s3_enabled=args.s3_enabled,
        s3_endpoint_url=args.s3_endpoint_url,
        s3_access_key_id=args.s3_access_key_id,
        s3_secret_access_key=args.s3_secret_access_key,
        s3_bucket_name=args.s3_bucket_name,
        s3_region_name=args.s3_region_name,
        s3_storage_class=args.s3_storage_class,
        s3_retry_attempts=args.s3_retry_attempts,
        s3_timeout=args.s3_timeout,
        s3_presigned_url_expiry=args.s3_presigned_url_expiry,
        tracker_enabled=args.tracker_enabled,
        tracker_oauth_token=args.tracker_token,
        tracker_queue=args.tracker_queue,
        transcribe_conversation=args.transcribe_conversation,
        max_parallel_copies=args.max_parallel_copies
    )

    usb_monitor = USBMonitor(check_interval=args.check_interval)

    # Периодическая проверка recovery каждые 15 секунд
    recovery_stop_event = threading.Event()

    def recovery_check_loop():
        """Периодическая проверка незавершённых задач"""
        while not recovery_stop_event.is_set():
            try:
                incomplete_tasks = pipeline.file_manager.recover_incomplete_tasks()
                if incomplete_tasks:
                    logger.info(f"\nRecovery: found {len(incomplete_tasks)} incomplete tasks")
                    pipeline.process_incomplete_tasks(incomplete_tasks)
            except Exception as e:
                logger.error(f"Recovery error: {e}")
            recovery_stop_event.wait(15)  # Ждём 15 секунд

    recovery_thread = threading.Thread(target=recovery_check_loop, daemon=True)
    recovery_thread.start()
    logger.info("Recovery check started (every 15 sec)")

    # Уведомление о запуске
    pipeline.telegram.notify_process_started(version=__version__)

    def on_device_connected(device_path):
        """Обработчик подключения нового устройства"""
        logger.info(f"\nNew device connected: {device_path}")

        # Получаем информацию об устройстве
        device_info = USBMonitor.get_device_info(device_path)
        logger.info(f"   Unique ID: {device_info['unique_id']}")
        if device_info['label']:
            logger.info(f"   Label: {device_info['label']}")
        if device_info['uuid']:
            logger.info(f"   UUID: {device_info['uuid'][:16]}...")

        # Уведомление о подключении
        pipeline.telegram.notify_device_connected(
            device_path=device_path,
            device_id=device_info['unique_id'],
            label=device_info.get('label')
        )

        # Проверяем, есть ли аудио файлы
        if not USBMonitor.is_audio_recorder(device_path):
            logger.info("No audio files found, skipping")
            return

        logger.info("Audio recorder detected, starting processing...")

        try:
            # Передаем уже полученный device_name
            pipeline.process_device(device_path, device_name=device_info['unique_id'])
        except Exception as e:
            logger.error(f"Device processing error: {e}", exc_info=True)

    def on_device_disconnected(device_path):
        """Обработчик отключения устройства"""
        logger.info(f"\nDevice disconnected: {device_path}")
        pipeline.telegram.notify_device_disconnected(device_path)

    # Запускаем мониторинг
    usb_monitor.monitor(callback=on_device_connected, on_disconnect=on_device_disconnected)


def process_mode(args):
    """Режим обработки конкретного устройства или файла"""
    logger = logging.getLogger("process_mode")

    pipeline = TranscriptionPipeline(
        assemblyai_api_key=getattr(args, 'assemblyai_api_key', None),
        language=args.language,
        num_speakers=getattr(args, 'num_speakers', 2),
        telegram_bot_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat,
        telegram_enabled=args.telegram_enabled,
        s3_enabled=args.s3_enabled,
        s3_endpoint_url=args.s3_endpoint_url,
        s3_access_key_id=args.s3_access_key_id,
        s3_secret_access_key=args.s3_secret_access_key,
        s3_bucket_name=args.s3_bucket_name,
        s3_region_name=args.s3_region_name,
        s3_storage_class=args.s3_storage_class,
        s3_retry_attempts=args.s3_retry_attempts,
        s3_timeout=args.s3_timeout,
        s3_presigned_url_expiry=args.s3_presigned_url_expiry,
        tracker_enabled=args.tracker_enabled,
        tracker_oauth_token=args.tracker_token,
        tracker_queue=args.tracker_queue,
        transcribe_conversation=args.transcribe_conversation,
        max_parallel_copies=args.max_parallel_copies
    )

    path = Path(args.path)

    if not path.exists():
        logger.error(f"Path not found: {path}")
        sys.exit(1)

    if path.is_dir():
        # Обрабатываем как устройство
        logger.info(f"Processing device: {path}")
        pipeline.process_device(str(path))
    else:
        # Обрабатываем как отдельный файл
        logger.info(f"Processing file: {path}")

        # Формируем ключ файла: manual_filename
        file_key = f"manual_{path.name}"

        file_info = {
            'local_path': str(path),
            'original_path': str(path),
            'device': 'manual',
            'file_key': file_key
        }
        pipeline.process_file(file_info)


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description="USB Audio Recorder Transcription Pipeline"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Уровень логирования"
    )

    parser.add_argument(
        "--log-file",
        default="logs/transcription.log",
        help="Файл для логов"
    )

    subparsers = parser.add_subparsers(dest="command", help="Команды")

    # Команда: monitor
    monitor_parser = subparsers.add_parser("monitor", help="Мониторинг USB устройств")
    monitor_parser.add_argument(
        "--check-interval",
        type=int,
        default=int(os.getenv("CHECK_INTERVAL", "5")),
        help="Интервал проверки устройств (секунды)"
    )
    monitor_parser.add_argument("--assemblyai-api-key", default=os.getenv("ASSEMBLYAI_API_KEY"), help="AssemblyAI API ключ")
    monitor_parser.add_argument("--num-speakers", type=int, default=int(os.getenv("DEFAULT_NUM_SPEAKERS", "2")), help="Количество говорящих")
    monitor_parser.add_argument("--language", default=os.getenv("LANGUAGE", "es"), help="Язык аудио (ISO-639-1)")
    monitor_parser.add_argument("--telegram-token", default=os.getenv("TELEGRAM_BOT_TOKEN"), help="Telegram bot token")
    monitor_parser.add_argument("--telegram-chat", default=os.getenv("TELEGRAM_CHAT_ID"), help="Telegram chat ID")
    monitor_parser.add_argument("--telegram-enabled", type=lambda x: x.lower() == 'true', default=os.getenv("TELEGRAM_ENABLED", "true").lower() == "true", help="Включить Telegram уведомления")
    monitor_parser.add_argument("--s3-enabled", type=lambda x: x.lower() == 'true', default=os.getenv("S3_ENABLED", "false").lower() == "true", help="Включить загрузку в S3")
    monitor_parser.add_argument("--s3-endpoint-url", default=os.getenv("S3_ENDPOINT_URL"), help="S3 endpoint URL")
    monitor_parser.add_argument("--s3-access-key-id", default=os.getenv("S3_ACCESS_KEY_ID"), help="S3 Access Key ID")
    monitor_parser.add_argument("--s3-secret-access-key", default=os.getenv("S3_SECRET_ACCESS_KEY"), help="S3 Secret Access Key")
    monitor_parser.add_argument("--s3-bucket-name", default=os.getenv("S3_BUCKET_NAME"), help="S3 bucket name")
    monitor_parser.add_argument("--s3-region-name", default=os.getenv("S3_REGION_NAME", "ru-central1"), help="S3 region")
    monitor_parser.add_argument("--s3-storage-class", default=os.getenv("S3_STORAGE_CLASS", "STANDARD"), help="S3 storage class")
    monitor_parser.add_argument("--s3-retry-attempts", type=int, default=int(os.getenv("S3_RETRY_ATTEMPTS", "3")), help="S3 retry attempts")
    monitor_parser.add_argument("--s3-timeout", type=int, default=int(os.getenv("S3_UPLOAD_TIMEOUT", "300")), help="S3 upload timeout (секунды)")
    monitor_parser.add_argument("--s3-presigned-url-expiry", type=int, default=int(os.getenv("S3_PRESIGNED_URL_EXPIRY", "604800")), help="Время жизни presigned URL (секунды)")
    monitor_parser.add_argument("--tracker-enabled", type=lambda x: x.lower() == 'true', default=os.getenv("TRACKER_ENABLED", "false").lower() == "true", help="Включить создание задач в трекере")
    monitor_parser.add_argument("--tracker-token", default=os.getenv("TRACKER_OAUTH_TOKEN"), help="OAuth токен для Яндекс Трекера")
    monitor_parser.add_argument("--tracker-queue", default=os.getenv("TRACKER_QUEUE", "YANGOSCOUTS"), help="Очередь для создания задач")
    monitor_parser.add_argument("--transcribe-conversation", type=lambda x: x.lower() == 'true', default=os.getenv("TRANSCRIBE_CONVERSATION", "true").lower() == "true", help="Выполнять транскрибацию разговоров")
    monitor_parser.add_argument("--max-parallel-copies", type=int, default=int(os.getenv("MAX_PARALLEL_COPIES", "3")), help="Количество параллельных потоков для копирования файлов")

    # Команда: process
    process_parser = subparsers.add_parser("process", help="Обработать устройство или файл")
    process_parser.add_argument("path", help="Путь к устройству или файлу")
    process_parser.add_argument("--assemblyai-api-key", default=os.getenv("ASSEMBLYAI_API_KEY"), help="AssemblyAI API ключ")
    process_parser.add_argument("--num-speakers", type=int, default=int(os.getenv("DEFAULT_NUM_SPEAKERS", "2")), help="Количество говорящих")
    process_parser.add_argument("--language", default=os.getenv("LANGUAGE", "es"), help="Язык аудио (ISO-639-1)")
    process_parser.add_argument("--telegram-token", default=os.getenv("TELEGRAM_BOT_TOKEN"), help="Telegram bot token")
    process_parser.add_argument("--telegram-chat", default=os.getenv("TELEGRAM_CHAT_ID"), help="Telegram chat ID")
    process_parser.add_argument("--telegram-enabled", type=lambda x: x.lower() == 'true', default=os.getenv("TELEGRAM_ENABLED", "true").lower() == "true", help="Включить Telegram уведомления")
    process_parser.add_argument("--s3-enabled", type=lambda x: x.lower() == 'true', default=os.getenv("S3_ENABLED", "false").lower() == "true", help="Включить загрузку в S3")
    process_parser.add_argument("--s3-endpoint-url", default=os.getenv("S3_ENDPOINT_URL"), help="S3 endpoint URL")
    process_parser.add_argument("--s3-access-key-id", default=os.getenv("S3_ACCESS_KEY_ID"), help="S3 Access Key ID")
    process_parser.add_argument("--s3-secret-access-key", default=os.getenv("S3_SECRET_ACCESS_KEY"), help="S3 Secret Access Key")
    process_parser.add_argument("--s3-bucket-name", default=os.getenv("S3_BUCKET_NAME"), help="S3 bucket name")
    process_parser.add_argument("--s3-region-name", default=os.getenv("S3_REGION_NAME", "ru-central1"), help="S3 region")
    process_parser.add_argument("--s3-storage-class", default=os.getenv("S3_STORAGE_CLASS", "STANDARD"), help="S3 storage class")
    process_parser.add_argument("--s3-retry-attempts", type=int, default=int(os.getenv("S3_RETRY_ATTEMPTS", "3")), help="S3 retry attempts")
    process_parser.add_argument("--s3-timeout", type=int, default=int(os.getenv("S3_UPLOAD_TIMEOUT", "300")), help="S3 upload timeout (секунды)")
    process_parser.add_argument("--s3-presigned-url-expiry", type=int, default=int(os.getenv("S3_PRESIGNED_URL_EXPIRY", "604800")), help="Время жизни presigned URL (секунды)")
    process_parser.add_argument("--tracker-enabled", type=lambda x: x.lower() == 'true', default=os.getenv("TRACKER_ENABLED", "false").lower() == "true", help="Включить создание задач в трекере")
    process_parser.add_argument("--tracker-token", default=os.getenv("TRACKER_OAUTH_TOKEN"), help="OAuth токен для Яндекс Трекера")
    process_parser.add_argument("--tracker-queue", default=os.getenv("TRACKER_QUEUE", "YANGOSCOUTS"), help="Очередь для создания задач")
    process_parser.add_argument("--transcribe-conversation", type=lambda x: x.lower() == 'true', default=os.getenv("TRANSCRIBE_CONVERSATION", "true").lower() == "true", help="Выполнять транскрибацию разговоров")
    process_parser.add_argument("--max-parallel-copies", type=int, default=int(os.getenv("MAX_PARALLEL_COPIES", "3")), help="Количество параллельных потоков для копирования файлов")

    args = parser.parse_args()

    # Настройка логирования
    setup_logging(args.log_level, args.log_file)

    # Выполнение команды
    if args.command == "monitor":
        monitor_mode(args)
    elif args.command == "process":
        process_mode(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
