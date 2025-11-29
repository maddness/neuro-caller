"""
Управление файлами: обнаружение новых аудиофайлов и копирование
"""

import os
import shutil
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

logger = logging.getLogger(__name__)


class FileManager:
    """Управление аудиофайлами: обнаружение и копирование"""

    # Поддерживаемые аудио форматы
    AUDIO_EXTENSIONS = {'.wav', '.m4a', '.ogg'}

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

        # Lock для потокобезопасной записи метаданных
        self._metadata_lock = Lock()

        # S3 uploader (будет установлен из main.py если S3_ENABLED=true)
        self.s3_uploader = None

        # Telegram notifier (будет установлен из main.py)
        self.telegram_notifier = None

        # Tracker client (будет установлен из main.py)
        self.tracker_client = None
        self.s3_presigned_url_expiry = 7 * 24 * 3600  # 7 дней по умолчанию
        self.transcribe_conversation = False

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
        """Атомарное сохранение БД обработанных файлов через временный файл"""
        try:
            temp_path = self.db_path.with_suffix('.json.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.db_path)  # Атомарная операция
        except Exception as e:
            logger.error(f"Ошибка сохранения БД обработанных файлов: {e}")

    def update_metadata(self, file_key: str, updates: dict):
        """
        Атомарное обновление метаданных файла с потокобезопасностью

        Args:
            file_key: Ключ файла (device_filename)
            updates: Словарь с обновлениями
        """
        with self._metadata_lock:
            if file_key not in self.processed_files:
                self.processed_files[file_key] = {}
            self.processed_files[file_key].update(updates)
            self._save_processed_files()

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

    @staticmethod
    def extract_date_from_filename(filename: str) -> str:
        """
        Извлечь дату из имени файла формата R20251124-120931.WAV

        Args:
            filename: Имя файла

        Returns:
            Дата в формате YYYY-MM-DD или текущая дата если парсинг не удался
        """
        # Паттерн: R + 8 цифр (YYYYMMDD) + - + 6 цифр (HHMMSS)
        match = re.match(r'R(\d{4})(\d{2})(\d{2})-\d{6}', filename)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month}-{day}"

        # Fallback на текущую дату
        return datetime.now().strftime("%Y-%m-%d")

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

                # Проверяем что это файл (не директория) и расширение поддерживается
                if file_path.is_file() and file_path.suffix.lower() in self.AUDIO_EXTENSIONS:
                    audio_files.append(file_path)

            logger.info(f"Найдено {len(audio_files)} аудио файлов в RECORD на {device_path}")

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

        # Формируем ключ файла: device_filename
        file_key = f"{device_name}_{filename}"

        # Проверяем по ключу напрямую (быстро и надёжно)
        if file_key in self.processed_files:
            return True

        # Fallback: проверяем по device + filename в метаданных
        for file_info in self.processed_files.values():
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

    def copy_file(
        self,
        source_path: Path,
        device_name: str = None,
        storage_class: str = "STANDARD",
        file_key: str = None
    ) -> Dict:
        """
        Копирование файла в локальное хранилище и загрузка в S3 (если включено)

        Args:
            source_path: Путь к исходному файлу
            device_name: Имя устройства (для организации)
            storage_class: Класс хранилища S3 (STANDARD, COLD, ICE)
            file_key: Ключ файла для отслеживания stage (опционально)

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
            # STAGE: copying - перед копированием
            if file_key:
                self.update_metadata(file_key, {
                    "stage": "copying",
                    "original_path": str(source_path),
                    "device": device_folder,
                    "size_bytes": source_path.stat().st_size
                })

            # ЭТАП 1: Копируем файл на локальный диск
            shutil.copy2(source_path, destination_path)
            logger.info(f"Файл скопирован: {source_path.name} -> {destination_path}")
            result['local_path'] = destination_path

            # STAGE: copied - после копирования
            if file_key:
                self.update_metadata(file_key, {
                    "stage": "copied",
                    "local_path": str(destination_path),
                    "copied_at": datetime.now().isoformat()
                })

            # ЭТАП 2: Загружаем в S3 (если включено)
            if self.s3_uploader:
                # Формируем S3 ключ: YYYY-MM-DD/device_name/original_filename
                # Дата извлекается из имени файла (R20251124-120931.WAV → 2025-11-24)
                date_folder = self.extract_date_from_filename(source_path.name)
                s3_key = f"{date_folder}/{device_folder}/{source_path.name}"

                # STAGE: s3_uploading - перед проверкой/загрузкой
                if file_key:
                    self.update_metadata(file_key, {"stage": "s3_uploading"})

                # Проверяем существование файла в S3 по оригинальному имени
                if self.s3_uploader.file_exists(s3_key):
                    logger.info(f"⏩ Файл уже существует в S3, пропускаем: {s3_key}")
                    result['s3_key'] = s3_key
                    result['s3_uploaded'] = True
                    result['s3_already_exists'] = True

                    # STAGE: s3_uploaded - файл уже был в S3
                    if file_key:
                        self.update_metadata(file_key, {
                            "stage": "s3_uploaded",
                            "s3_key": s3_key
                        })
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

                        # STAGE: s3_uploaded - файл загружен
                        if file_key:
                            self.update_metadata(file_key, {
                                "stage": "s3_uploaded",
                                "s3_key": s3_key
                            })
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
                total_size_mb=total_size_mb_estimate,
                device_path=device_path
            )

        copied_files = []
        total_size_mb = 0

        # Функция для копирования одного файла (выполняется в отдельном потоке)
        def _copy_single_file(source_file: Path, file_index: int, total_files: int):
            """Копирование одного файла с обработкой ошибок"""
            try:
                file_size_mb = source_file.stat().st_size / (1024 * 1024)
                logger.info(f"   [{file_index}/{total_files}] Копирую: {source_file.name} ({file_size_mb:.1f} MB)")

                # Формируем уникальный ключ ДО копирования: device_filename
                file_key = f"{device_name}_{source_file.name}"

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
                # file_key передаётся для отслеживания stage
                copy_result = self.copy_file(source_file, device_name, file_key=file_key)
                destination_path = copy_result['local_path']

                # Получаем file_info из processed_files (уже сохранено через update_metadata)
                file_info = self.processed_files.get(file_key, {})

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

                # Создание тикета в Tracker (если включен)
                if self.tracker_client and self.tracker_client.enabled:
                    if not copy_result.get('s3_already_exists'):
                        # STAGE: tracker_creating
                        self.update_metadata(file_key, {"stage": "tracker_creating"})

                        presigned_url = self.s3_uploader.generate_presigned_url(
                            s3_key=copy_result['s3_key'],
                            expiration=self.s3_presigned_url_expiry
                        )
                        if presigned_url:
                            from src.tracker_client import TrackerClient
                            summary = TrackerClient.build_summary_from_s3_key(copy_result['s3_key'])
                            issue = self.tracker_client.create_issue(
                                summary=summary,
                                description=presigned_url,
                                transcribe_conversation=self.transcribe_conversation
                            )
                            if issue:
                                issue_key = issue.get('key')
                                issue_url = issue.get('self')
                                logger.info(f"        ✓ Тикет: {issue_key}")

                                # STAGE: completed
                                self.update_metadata(file_key, {
                                    "stage": "completed",
                                    "tracker_issue_key": issue_key,
                                    "tracker_url": issue_url
                                })

                                # Telegram уведомление
                                if self.telegram_notifier:
                                    self.telegram_notifier.notify_tracker_issue_created(
                                        issue_key=issue_key,
                                        s3_key=copy_result['s3_key'],
                                        issue_url=issue_url
                                    )
                    else:
                        # Файл уже был в S3 - ставим completed
                        self.update_metadata(file_key, {"stage": "completed"})

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
                    # update вместо перезаписи, чтобы сохранить stage
                    if file_key in self.processed_files:
                        self.processed_files[file_key].update(file_info)
                    else:
                        self.processed_files[file_key] = file_info
                    copied_files.append(self.processed_files[file_key])
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

    def recover_incomplete_tasks(self) -> List[Dict]:
        """
        Восстановление незавершенных задач после перезапуска.

        Проверяет все файлы в БД и возвращает список тех,
        которые не дошли до стадии 'completed'.

        Returns:
            Список задач для восстановления:
            [{"file_key": str, "meta": dict, "action": str}]

            action может быть:
            - "copy": нужно скопировать заново (stage: copying)
            - "s3_upload": нужно загрузить в S3 (stage: copied, s3_uploading)
            - "tracker": нужно создать тикет (stage: s3_uploaded, tracker_creating)
        """
        incomplete = []

        for file_key, meta in self.processed_files.items():
            stage = meta.get("stage")

            # Пропускаем completed и файлы без stage (старый формат)
            if stage == "completed" or stage is None:
                continue

            if stage == "copying":
                # Копирование прервано - нужно скопировать заново
                incomplete.append({
                    "file_key": file_key,
                    "meta": meta,
                    "action": "copy"
                })

            elif stage in ("copied", "s3_uploading"):
                # Нужна загрузка в S3
                incomplete.append({
                    "file_key": file_key,
                    "meta": meta,
                    "action": "s3_upload"
                })

            elif stage in ("s3_uploaded", "tracker_creating"):
                # Нужно создание тикета
                incomplete.append({
                    "file_key": file_key,
                    "meta": meta,
                    "action": "tracker"
                })

        if incomplete:
            logger.info(f"🔄 Recovery: найдено {len(incomplete)} незавершенных задач")
            for task in incomplete:
                logger.info(f"   - {task['file_key']}: stage={task['meta'].get('stage')}, action={task['action']}")

        return incomplete


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
