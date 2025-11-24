"""
Управление файлами: обнаружение новых аудиофайлов и копирование
"""

import os
import shutil
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class FileManager:
    """Управление аудиофайлами: обнаружение и копирование"""

    # Поддерживаемые аудио форматы
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}

    def __init__(
        self,
        local_storage_path: str = "data/audio",
        db_path: str = "data/processed_files.json",
        max_workers: int = 3
    ):
        """
        Args:
            local_storage_path: Путь для хранения скопированных файлов
            db_path: Путь к файлу БД обработанных файлов
            max_workers: Количество параллельных потоков для копирования файлов
        """
        self.local_storage_path = Path(local_storage_path)
        self.db_path = Path(db_path)
        self.max_workers = max_workers

        # Создаем директории если не существуют
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Логируем настройки параллелизма
        logger.info(f"📦 Параллельное копирование: {max_workers} потоков")

        # Загружаем БД обработанных файлов
        self.processed_files = self._load_processed_files()

        # S3 uploader (будет установлен из main.py если S3_ENABLED=true)
        self.s3_uploader = None

        # Telegram notifier (будет установлен из main.py)
        self.telegram_notifier = None

    def _load_processed_files(self) -> Dict[str, dict]:
        """Загрузка БД обработанных файлов"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки БД обработанных файлов: {e}")
                return {}
        return {}

    def _save_processed_files(self):
        """Сохранение БД обработанных файлов"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения БД обработанных файлов: {e}")

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """
        Вычисление MD5 хеша файла для идентификации

        Args:
            file_path: Путь к файлу

        Returns:
            MD5 хеш строка
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # Читаем файл частями для экономии памяти
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Ошибка вычисления хеша {file_path}: {e}")
            return ""

    def find_audio_files(self, device_path: str) -> List[Path]:
        """
        Поиск WAV файлов в папке RECORD на устройстве

        Args:
            device_path: Путь к устройству

        Returns:
            Список путей к WAV файлам из RECORD
        """
        audio_files = []

        try:
            # Проверяем наличие папки RECORD в корне устройства
            records_path = Path(device_path) / 'RECORD'

            if not records_path.exists():
                logger.info(f"Папка RECORD не найдена на {device_path}")
                return audio_files

            if not records_path.is_dir():
                logger.warning(f"RECORD существует, но это не папка на {device_path}")
                return audio_files

            # Читаем только файлы из RECORD (без рекурсии)
            for file in os.listdir(records_path):
                # Пропускаем macOS служебные файлы и скрытые
                if file.startswith('._') or file.startswith('.'):
                    continue

                file_path = records_path / file

                # Проверяем что это файл (не директория) и расширение .wav
                if file_path.is_file() and file_path.suffix.lower() == '.wav':
                    audio_files.append(file_path)

            logger.info(f"Найдено {len(audio_files)} WAV файлов в RECORD на {device_path}")

        except Exception as e:
            logger.error(f"Ошибка поиска файлов на {device_path}: {e}")

        return audio_files

    def _is_duplicate_by_device_and_name(self, file_path: Path, device_name: str) -> bool:
        """
        Проверка дубликата по устройству + имени файла (быстро, без MD5)

        Args:
            file_path: Путь к файлу
            device_name: Имя устройства

        Returns:
            True если файл с device+name уже обработан
        """
        filename = file_path.name

        for file_info in self.processed_files.values():
            # Проверяем: то же устройство + то же имя файла
            if (file_info.get("device") == device_name and
                Path(file_info.get("original_path", "")).name == filename):
                return True

        return False

    def find_new_files(self, device_path: str) -> List[Path]:
        """
        Найти только новые (необработанные) файлы на устройстве

        Args:
            device_path: Путь к устройству

        Returns:
            Список новых файлов
        """
        all_files = self.find_audio_files(device_path)
        new_files = []

        # Получаем имя устройства
        device_name = Path(device_path).name

        for file_path in all_files:
            # Быстрая проверка по device + filename (БЕЗ вычисления MD5!)
            if not self._is_duplicate_by_device_and_name(file_path, device_name):
                new_files.append(file_path)

        logger.info(f"Обнаружено {len(new_files)} новых файлов")
        return new_files

    def copy_file(self, source_path: Path, device_name: str = None, storage_class: str = "STANDARD") -> Dict:
        """
        Копирование файла в локальное хранилище и загрузка в S3 (если включено)

        Args:
            source_path: Путь к исходному файлу
            device_name: Имя устройства (для организации)
            storage_class: Класс хранилища S3 (STANDARD, COLD, ICE)

        Returns:
            Словарь с информацией о файле:
            {
                'local_path': Path,
                's3_key': str или None,
                's3_uploaded': bool,
                's3_url': str или None
            }
        """
        # Создаем структуру директорий: YYYY-MM-DD/device_name/
        date_folder = datetime.now().strftime("%Y-%m-%d")
        device_folder = device_name or "unknown_device"

        destination_dir = self.local_storage_path / date_folder / device_folder
        destination_dir.mkdir(parents=True, exist_ok=True)

        # Генерируем уникальное имя файла если уже существует
        destination_path = destination_dir / source_path.name
        counter = 1
        while destination_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            destination_path = destination_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        # Результат
        result = {
            'local_path': None,
            's3_key': None,
            's3_uploaded': False,
            's3_url': None
        }

        try:
            # ЭТАП 1: Копируем файл на локальный диск
            shutil.copy2(source_path, destination_path)
            logger.info(f"Файл скопирован: {source_path.name} -> {destination_path}")
            result['local_path'] = destination_path

            # ЭТАП 2: Загружаем в S3 (если включено)
            if self.s3_uploader:
                # Формируем S3 ключ: YYYY_MM_DD/device_name/original_filename
                # ВАЖНО: Используем оригинальное имя файла БЕЗ суффиксов (_1, _2 и т.д.)
                # Дата с подчеркиваниями, не дефисами!
                date_underscored = datetime.now().strftime("%Y_%m_%d")
                s3_key = f"{date_underscored}/{device_folder}/{source_path.name}"

                # Проверяем существование файла в S3 по оригинальному имени
                if self.s3_uploader.file_exists(s3_key):
                    logger.info(f"⏩ Файл уже существует в S3, пропускаем: {s3_key}")
                    result['s3_key'] = s3_key
                    result['s3_uploaded'] = True
                    result['s3_already_exists'] = True
                else:
                    # Метаданные для файла в S3
                    metadata = {
                        'device': device_folder,
                        'original_filename': source_path.name,
                        'upload_date': datetime.now().isoformat()
                    }

                    logger.info(f"Загрузка в S3: {s3_key}")

                    # Загружаем файл в S3
                    s3_success = self.s3_uploader.upload_file(
                        file_path=destination_path,
                        s3_key=s3_key,
                        storage_class=storage_class,
                        metadata=metadata
                    )

                    if s3_success:
                        result['s3_key'] = s3_key
                        result['s3_uploaded'] = True
                        result['s3_already_exists'] = False
                        logger.info(f"✓ Файл загружен в S3: {s3_key}")
                    else:
                        logger.warning(f"⚠ Не удалось загрузить файл в S3: {s3_key}")

            return result

        except Exception as e:
            logger.error(f"Ошибка копирования файла {source_path}: {e}")
            raise

    def process_new_files(self, device_path: str, device_name: str = None) -> List[Dict]:
        """
        Обработка новых файлов с устройства: поиск, копирование и регистрация

        Args:
            device_path: Путь к устройству
            device_name: Уникальное имя устройства (если None, используется имя из пути)

        Returns:
            Список информации о скопированных файлах
        """
        if device_name is None:
            device_name = Path(device_path).name

        new_files = self.find_new_files(device_path)

        if not new_files:
            logger.info("Новых файлов не найдено")
            return []

        logger.info(f"\n📦 Начинаем копирование {len(new_files)} файлов с флешки...")
        logger.info(f"   С флешки: {device_path}")
        logger.info(f"   На диск: {self.local_storage_path}\n")

        # Вычисляем общий размер для уведомления
        total_size_bytes = sum(f.stat().st_size for f in new_files)
        total_size_mb_estimate = total_size_bytes / (1024 * 1024)

        # Telegram: уведомление о начале копирования
        if self.telegram_notifier:
            self.telegram_notifier.notify_copying_started(
                files_count=len(new_files),
                total_size_mb=total_size_mb_estimate
            )

        copied_files = []
        total_size_mb = 0

        # Функция для копирования одного файла (выполняется в отдельном потоке)
        def _copy_single_file(source_file: Path, file_index: int, total_files: int):
            """Копирование одного файла с обработкой ошибок"""
            try:
                file_size_mb = source_file.stat().st_size / (1024 * 1024)
                logger.info(f"   [{file_index}/{total_files}] Копирую: {source_file.name} ({file_size_mb:.1f} MB)")

                # Telegram: уведомление о начале копирования файла
                if self.telegram_notifier:
                    self.telegram_notifier.notify_file_copied(
                        file_num=file_index,
                        total_files=total_files,
                        filename=source_file.name,
                        size_mb=file_size_mb,
                        device_path=str(source_file)
                    )

                # Копируем файл (и загружаем в S3 если включено)
                copy_result = self.copy_file(source_file, device_name)
                destination_path = copy_result['local_path']

                # Формируем уникальный ключ: device_filename
                file_key = f"{device_name}_{source_file.name}"

                # Регистрируем в БД
                file_info = {
                    "original_path": str(source_file),
                    "local_path": str(destination_path),
                    "device": device_name,
                    "size_bytes": source_file.stat().st_size,
                    "copied_at": datetime.now().isoformat(),
                    "processed": False,
                    # S3 информация
                    "s3_key": copy_result.get('s3_key'),
                    "s3_uploaded": copy_result.get('s3_uploaded', False),
                    "s3_already_exists": copy_result.get('s3_already_exists', False)
                }

                logger.info(f"        ✓ Скопирован в: {destination_path.relative_to(self.local_storage_path)}")
                if copy_result.get('s3_uploaded'):
                    if copy_result.get('s3_already_exists'):
                        logger.info(f"        ⏩ Уже в S3: {copy_result['s3_key']}")

                        # Отправляем Telegram уведомление о существующем файле в S3
                        if self.telegram_notifier:
                            self.telegram_notifier.notify_s3_already_exists(
                                s3_key=copy_result['s3_key'],
                                size_mb=file_size_mb
                            )
                    else:
                        logger.info(f"        ✓ Загружен в S3: {copy_result['s3_key']}")

                        # Отправляем Telegram уведомление о загрузке в S3
                        if self.telegram_notifier:
                            self.telegram_notifier.notify_s3_upload(
                                filename=source_file.name,
                                s3_key=copy_result['s3_key'],
                                size_mb=file_size_mb
                            )

                # Возвращаем результат: (индекс, file_key, file_info, размер, ошибка)
                return (file_index, file_key, file_info, file_size_mb, None)

            except Exception as e:
                logger.error(f"        ✗ Ошибка при копировании {source_file.name}: {e}")
                return (file_index, None, None, 0, str(e))

        # Запускаем параллельное копирование через ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Создаем задачи для всех файлов
            futures = {}
            for i, source_file in enumerate(new_files, 1):
                future = executor.submit(_copy_single_file, source_file, i, len(new_files))
                futures[future] = source_file

            # Собираем результаты по мере завершения
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

            # Сортируем результаты по индексу для сохранения порядка
            results.sort(key=lambda x: x[0])

            # Обрабатываем результаты
            errors = []
            for file_index, file_key, file_info, size_mb, error in results:
                if error:
                    errors.append(error)
                else:
                    self.processed_files[file_key] = file_info
                    copied_files.append(file_info)
                    total_size_mb += size_mb

        # Сохраняем БД
        self._save_processed_files()

        # Логируем ошибки если были
        if errors:
            logger.warning(f"\n⚠️  Ошибки при копировании {len(errors)} файлов:")
            for error in errors:
                logger.warning(f"   - {error}")

        logger.info(f"\n📊 Итого скопировано: {len(copied_files)}/{len(new_files)} файлов, {total_size_mb:.1f} MB")
        return copied_files

    def mark_as_processed(self, file_key: str):
        """
        Отметить файл как обработанный (транскрибированный)

        Args:
            file_key: Ключ файла (device_filename)
        """
        if file_key in self.processed_files:
            self.processed_files[file_key]["processed"] = True
            self.processed_files[file_key]["processed_at"] = datetime.now().isoformat()
            self._save_processed_files()

    def get_unprocessed_files(self) -> List[Dict]:
        """
        Получить список файлов, которые еще не были транскрибированы

        Returns:
            Список информации о необработанных файлах
        """
        unprocessed = []
        for file_key, file_info in self.processed_files.items():
            if not file_info.get("processed", False):
                file_info["file_key"] = file_key
                unprocessed.append(file_info)

        return unprocessed


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    fm = FileManager()

    # Пример использования
    test_device = "/media/usb0"
    if os.path.exists(test_device):
        copied = fm.process_new_files(test_device)
        print(f"\nСкопировано файлов: {len(copied)}")
        for file_info in copied:
            print(f"  - {file_info['local_path']}")
    else:
        print(f"Тестовое устройство {test_device} не найдено")
