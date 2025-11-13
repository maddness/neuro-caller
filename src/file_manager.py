"""
Управление файлами: обнаружение новых аудиофайлов и копирование
"""

import os
import shutil
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Set, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class FileManager:
    """Управление аудиофайлами: обнаружение и копирование"""

    # Поддерживаемые аудио форматы
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}

    def __init__(self, local_storage_path: str = "data/audio", db_path: str = "data/processed_files.json"):
        """
        Args:
            local_storage_path: Путь для хранения скопированных файлов
            db_path: Путь к файлу БД обработанных файлов
        """
        self.local_storage_path = Path(local_storage_path)
        self.db_path = Path(db_path)

        # Создаем директории если не существуют
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Загружаем БД обработанных файлов
        self.processed_files = self._load_processed_files()

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
        Поиск всех аудиофайлов на устройстве

        Args:
            device_path: Путь к устройству

        Returns:
            Список путей к аудиофайлам
        """
        audio_files = []

        try:
            for root, dirs, files in os.walk(device_path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in self.AUDIO_EXTENSIONS:
                        audio_files.append(file_path)

            logger.info(f"Найдено {len(audio_files)} аудиофайлов на {device_path}")

        except Exception as e:
            logger.error(f"Ошибка поиска файлов на {device_path}: {e}")

        return audio_files

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

        for file_path in all_files:
            file_hash = self.calculate_file_hash(file_path)

            if file_hash and file_hash not in self.processed_files:
                new_files.append(file_path)

        logger.info(f"Обнаружено {len(new_files)} новых файлов")
        return new_files

    def copy_file(self, source_path: Path, device_name: str = None) -> Path:
        """
        Копирование файла в локальное хранилище

        Args:
            source_path: Путь к исходному файлу
            device_name: Имя устройства (для организации)

        Returns:
            Путь к скопированному файлу
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

        try:
            shutil.copy2(source_path, destination_path)
            logger.info(f"Файл скопирован: {source_path.name} -> {destination_path}")
            return destination_path

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

        copied_files = []

        for source_file in new_files:
            try:
                # Копируем файл
                destination_path = self.copy_file(source_file, device_name)

                # Вычисляем хеш
                file_hash = self.calculate_file_hash(source_file)

                # Регистрируем в БД
                file_info = {
                    "original_path": str(source_file),
                    "local_path": str(destination_path),
                    "device": device_name,
                    "size_bytes": source_file.stat().st_size,
                    "copied_at": datetime.now().isoformat(),
                    "processed": False
                }

                self.processed_files[file_hash] = file_info
                copied_files.append(file_info)

                logger.info(f"✅ Обработан: {source_file.name}")

            except Exception as e:
                logger.error(f"❌ Ошибка обработки {source_file}: {e}")

        # Сохраняем БД
        self._save_processed_files()

        logger.info(f"Всего скопировано: {len(copied_files)} файлов")
        return copied_files

    def mark_as_processed(self, file_hash: str):
        """
        Отметить файл как обработанный (транскрибированный)

        Args:
            file_hash: MD5 хеш файла
        """
        if file_hash in self.processed_files:
            self.processed_files[file_hash]["processed"] = True
            self.processed_files[file_hash]["processed_at"] = datetime.now().isoformat()
            self._save_processed_files()

    def get_unprocessed_files(self) -> List[Dict]:
        """
        Получить список файлов, которые еще не были транскрибированы

        Returns:
            Список информации о необработанных файлах
        """
        unprocessed = []
        for file_hash, file_info in self.processed_files.items():
            if not file_info.get("processed", False):
                file_info["hash"] = file_hash
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
