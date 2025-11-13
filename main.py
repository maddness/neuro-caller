#!/usr/bin/env python3
"""
USB Audio Recorder Transcription Pipeline
Автоматическая транскрибация аудиозаписей с USB диктофонов
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.usb_monitor import USBMonitor
from src.file_manager import FileManager
from src.audio_processor import AudioProcessor
from src.transcriber import WhisperTranscriber
from src.database import TranscriptionDatabase


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


class TranscriptionPipeline:
    """Главный пайплайн для обработки аудиозаписей"""

    def __init__(
        self,
        openai_api_key: str = None,
        language: str = "es",
        chunk_length_minutes: int = 10,
        overlap_seconds: int = 5
    ):
        """
        Args:
            openai_api_key: OpenAI API ключ
            language: Язык аудио (ISO-639-1)
            chunk_length_minutes: Длина чанка в минутах
            overlap_seconds: Overlap между чанками в секундах
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Инициализация компонентов
        self.logger.info("Инициализация компонентов пайплайна...")

        self.file_manager = FileManager()
        self.audio_processor = AudioProcessor(
            chunk_length_ms=chunk_length_minutes * 60 * 1000,
            overlap_ms=overlap_seconds * 1000
        )
        self.transcriber = WhisperTranscriber(
            api_key=openai_api_key,
            language=language
        )
        self.database = TranscriptionDatabase()

        self.logger.info("✅ Пайплайн готов к работе")

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
            self.logger.info(f"Обработка устройства: {device_path}")
            self.logger.info(f"Уникальный ID: {device_name}")
            if device_info['label']:
                self.logger.info(f"Метка: {device_info['label']}")
            if device_info['uuid']:
                self.logger.info(f"UUID: {device_info['uuid'][:16]}...")
            self.logger.info(f"{'='*60}\n")
        else:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Обработка устройства: {device_path}")
            self.logger.info(f"ID устройства: {device_name}")
            self.logger.info(f"{'='*60}\n")

        # ============================================================
        # ЭТАП 1: КОПИРОВАНИЕ ВСЕХ ФАЙЛОВ С ФЛЕШКИ НА ЖЕСТКИЙ ДИСК
        # ============================================================
        self.logger.info("📋 ЭТАП 1: Поиск и копирование новых аудиофайлов...")
        self.logger.info("   (Сначала копируем ВСЕ файлы, потом обрабатываем)")

        copied_files = self.file_manager.process_new_files(device_path, device_name=device_name)

        if not copied_files:
            self.logger.info("✓ Новых файлов не найдено")
            return

        self.logger.info(f"\n✅ ВСЕ ФАЙЛЫ СКОПИРОВАНЫ НА ЖЕСТКИЙ ДИСК: {len(copied_files)} файлов")
        self.logger.info("   Теперь можно безопасно отключить флешку")

        # ============================================================
        # ЭТАП 2: ОБРАБОТКА СКОПИРОВАННЫХ ФАЙЛОВ
        # ============================================================
        self.logger.info(f"\n🔄 ЭТАП 2: Транскрибация файлов ({len(copied_files)} шт)")
        self.logger.info("   (Нарезка на чанки + отправка в Whisper API)")

        for i, file_info in enumerate(copied_files, 1):
            self.logger.info(f"\n{'─'*60}")
            self.logger.info(f"📝 Файл {i}/{len(copied_files)}: {Path(file_info['local_path']).name}")
            self.logger.info(f"{'─'*60}")
            self.process_file(file_info)

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"✅ ВСЁ ГОТОВО! Обработано файлов: {len(copied_files)}")
        self.logger.info(f"{'='*60}")

    def process_file(self, file_info: dict):
        """
        Обработка одного аудиофайла: разделение, транскрибация, сохранение

        Args:
            file_info: Информация о файле из FileManager
        """
        file_path = Path(file_info['local_path'])
        file_hash = next(
            (k for k, v in self.file_manager.processed_files.items()
             if v.get('local_path') == str(file_path)),
            None
        )

        try:
            # Получение информации о файле
            audio_info = self.audio_processor.get_audio_info(file_path)
            self.logger.info(
                f"📊 Файл: {audio_info['duration_minutes']:.1f} мин, "
                f"{audio_info['file_size_mb']:.1f} MB, "
                f"{audio_info['format'].upper()}"
            )

            # Транскрибация (с автоматическим разделением если нужно)
            chunks_needed = audio_info['file_size_mb'] > 24
            if chunks_needed:
                self.logger.info(f"⚠️  Файл большой, будет разделен на части с overlap {self.audio_processor.overlap_ms/1000:.0f}с")

            self.logger.info("🎤 Отправка в Whisper API для транскрибации...")
            transcription = self.transcriber.transcribe_file_with_splitting(
                file_path,
                audio_processor=self.audio_processor,
                save_chunks=False  # Удаляем временные чанки
            )

            # Сохранение в базу данных
            self.logger.info("💾 Сохранение транскрипции в БД...")

            # Подготовка чанков для БД
            chunks_data = None
            if 'chunks' in transcription:
                chunks_data = [
                    {
                        'chunk_number': i,
                        'text': chunk.get('text', ''),
                        'start_ms': None,
                        'end_ms': None
                    }
                    for i, chunk in enumerate(transcription['chunks'], 1)
                ]

            transcription_id = self.database.add_transcription(
                file_hash=file_hash or "",
                original_filename=file_info['original_path'],
                audio_file_path=str(file_path),
                transcription_text=transcription['text'],
                device_name=file_info.get('device'),
                language=transcription.get('language', 'es'),
                duration_seconds=audio_info.get('duration_seconds'),
                metadata={
                    'file_size_mb': audio_info.get('file_size_mb'),
                    'channels': audio_info.get('channels'),
                    'sample_rate': audio_info.get('frame_rate'),
                    'total_chunks': transcription.get('total_chunks', 1)
                },
                chunks=chunks_data
            )

            # Отмечаем файл как обработанный
            if file_hash:
                self.file_manager.mark_as_processed(file_hash)

            word_count = len(transcription['text'].split())
            self.logger.info(f"\n✅ ГОТОВО! ID транскрипции: {transcription_id}")
            self.logger.info(f"   Символов: {len(transcription['text'])}, Слов: {word_count}")
            self.logger.info(f"   Фрагмент: {transcription['text'][:100]}...")

        except Exception as e:
            self.logger.error(f"\n❌ ОШИБКА: {e}", exc_info=True)


def monitor_mode(args):
    """Режим непрерывного мониторинга USB устройств"""
    logger = logging.getLogger("monitor_mode")
    logger.info("Запуск режима мониторинга USB устройств...")

    pipeline = TranscriptionPipeline(
        openai_api_key=args.api_key,
        language=args.language,
        chunk_length_minutes=args.chunk_length,
        overlap_seconds=args.overlap
    )

    usb_monitor = USBMonitor(check_interval=args.check_interval)

    def on_device_connected(device_path):
        """Обработчик подключения нового устройства"""
        logger.info(f"\n🔌 Новое устройство подключено: {device_path}")

        # Получаем информацию об устройстве
        device_info = USBMonitor.get_device_info(device_path)
        logger.info(f"   Уникальный ID: {device_info['unique_id']}")
        if device_info['label']:
            logger.info(f"   Метка: {device_info['label']}")
        if device_info['uuid']:
            logger.info(f"   UUID: {device_info['uuid'][:16]}...")

        # Проверяем, есть ли аудио файлы
        if not USBMonitor.is_audio_recorder(device_path):
            logger.info("⚠️  Аудио файлы не найдены, пропускаем")
            return

        logger.info("✅ Обнаружен аудио диктофон, начинаем обработку...")

        try:
            # Передаем уже полученный device_name
            pipeline.process_device(device_path, device_name=device_info['unique_id'])
        except Exception as e:
            logger.error(f"Ошибка обработки устройства: {e}", exc_info=True)

    # Запускаем мониторинг
    usb_monitor.monitor(callback=on_device_connected)


def process_mode(args):
    """Режим обработки конкретного устройства или файла"""
    logger = logging.getLogger("process_mode")

    pipeline = TranscriptionPipeline(
        openai_api_key=args.api_key,
        language=args.language,
        chunk_length_minutes=args.chunk_length,
        overlap_seconds=args.overlap
    )

    path = Path(args.path)

    if not path.exists():
        logger.error(f"Путь не найден: {path}")
        sys.exit(1)

    if path.is_dir():
        # Обрабатываем как устройство
        logger.info(f"Обработка устройства: {path}")
        pipeline.process_device(str(path))
    else:
        # Обрабатываем как отдельный файл
        logger.info(f"Обработка файла: {path}")
        file_info = {
            'local_path': str(path),
            'original_path': str(path),
            'device': 'manual'
        }
        pipeline.process_file(file_info)


def stats_mode(args):
    """Режим просмотра статистики"""
    logger = logging.getLogger("stats_mode")

    db = TranscriptionDatabase()
    stats = db.get_statistics()

    print("\n" + "="*60)
    print("СТАТИСТИКА ТРАНСКРИПЦИЙ")
    print("="*60)

    print(f"\nОбщая информация:")
    print(f"  Всего транскрипций: {stats['total_transcriptions']}")
    print(f"  Общая длительность: {stats['total_duration_seconds']/3600:.1f} часов")
    print(f"  Всего слов: {stats['total_words']:,}")
    print(f"  Уникальных устройств: {stats['unique_devices']}")

    if stats['by_device']:
        print(f"\nПо устройствам:")
        for device in stats['by_device']:
            print(f"  {device['device_name']}: {device['count']} файлов, "
                  f"{device['duration_seconds']/3600:.1f} часов")

    if stats['by_day']:
        print(f"\nПоследние дни:")
        for day in stats['by_day'][:7]:
            print(f"  {day['date']}: {day['count']} файлов")

    print("\n" + "="*60 + "\n")


def search_mode(args):
    """Режим поиска в транскрипциях"""
    logger = logging.getLogger("search_mode")

    db = TranscriptionDatabase()

    results = db.search_transcriptions(
        query=args.query,
        device_name=args.device,
        date_from=args.date_from,
        date_to=args.date_to,
        limit=args.limit
    )

    print(f"\nНайдено результатов: {len(results)}\n")

    for result in results:
        print(f"ID: {result['id']}")
        print(f"Файл: {result['original_filename']}")
        print(f"Устройство: {result['device_name']}")
        print(f"Дата: {result['created_at']}")
        print(f"Текст: {result['transcription_text'][:200]}...")
        print("-" * 60)


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
        default=5,
        help="Интервал проверки устройств (секунды)"
    )
    monitor_parser.add_argument("--api-key", help="OpenAI API ключ")
    monitor_parser.add_argument("--language", default="es", help="Язык аудио (ISO-639-1)")
    monitor_parser.add_argument("--chunk-length", type=int, default=10, help="Длина чанка (минуты)")
    monitor_parser.add_argument("--overlap", type=int, default=5, help="Overlap (секунды)")

    # Команда: process
    process_parser = subparsers.add_parser("process", help="Обработать устройство или файл")
    process_parser.add_argument("path", help="Путь к устройству или файлу")
    process_parser.add_argument("--api-key", help="OpenAI API ключ")
    process_parser.add_argument("--language", default="es", help="Язык аудио (ISO-639-1)")
    process_parser.add_argument("--chunk-length", type=int, default=10, help="Длина чанка (минуты)")
    process_parser.add_argument("--overlap", type=int, default=5, help="Overlap (секунды)")

    # Команда: stats
    stats_parser = subparsers.add_parser("stats", help="Показать статистику")

    # Команда: search
    search_parser = subparsers.add_parser("search", help="Поиск в транскрипциях")
    search_parser.add_argument("query", nargs="?", help="Поисковый запрос")
    search_parser.add_argument("--device", help="Фильтр по устройству")
    search_parser.add_argument("--date-from", help="Дата начала (YYYY-MM-DD)")
    search_parser.add_argument("--date-to", help="Дата окончания (YYYY-MM-DD)")
    search_parser.add_argument("--limit", type=int, default=20, help="Макс результатов")

    args = parser.parse_args()

    # Настройка логирования
    setup_logging(args.log_level, args.log_file)

    # Выполнение команды
    if args.command == "monitor":
        monitor_mode(args)
    elif args.command == "process":
        process_mode(args)
    elif args.command == "stats":
        stats_mode(args)
    elif args.command == "search":
        search_mode(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
