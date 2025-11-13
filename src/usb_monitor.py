"""
USB устройства мониторинг и обнаружение
Обнаруживает подключение новых USB диктофонов
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Set, Optional
import psutil

logger = logging.getLogger(__name__)


class USBMonitor:
    """Мониторинг USB устройств и обнаружение диктофонов"""

    def __init__(self, check_interval: int = 5):
        """
        Args:
            check_interval: Интервал проверки новых устройств (секунды)
        """
        self.check_interval = check_interval
        self.known_devices: Set[str] = set()
        self._initialize_known_devices()

    def _initialize_known_devices(self):
        """Инициализация списка известных устройств при старте"""
        devices = self.get_mounted_devices()
        self.known_devices = set(devices)
        logger.info(f"Инициализировано {len(self.known_devices)} известных устройств")

    @staticmethod
    def get_mounted_devices() -> List[str]:
        """Получить список смонтированных USB устройств"""
        devices = []

        for partition in psutil.disk_partitions(all=False):
            # Фильтруем только съемные устройства (обычно /media, /mnt или removable)
            mount_point = partition.mountpoint

            # В Linux USB обычно монтируются в /media или /mnt
            if '/media' in mount_point or '/mnt' in mount_point:
                if os.path.exists(mount_point) and os.path.isdir(mount_point):
                    devices.append(mount_point)
            # Дополнительная проверка для removable устройств
            elif partition.device.startswith('/dev/sd'):
                try:
                    # Проверяем, является ли устройство съемным
                    device_name = partition.device.split('/')[-1].rstrip('0123456789')
                    removable_path = f"/sys/block/{device_name}/removable"
                    if os.path.exists(removable_path):
                        with open(removable_path, 'r') as f:
                            if f.read().strip() == '1':
                                devices.append(mount_point)
                except Exception as e:
                    logger.debug(f"Ошибка проверки устройства {partition.device}: {e}")

        return devices

    def detect_new_devices(self) -> List[str]:
        """
        Обнаружение новых подключенных устройств

        Returns:
            Список путей к новым устройствам
        """
        current_devices = set(self.get_mounted_devices())
        new_devices = list(current_devices - self.known_devices)

        if new_devices:
            logger.info(f"Обнаружено новых устройств: {len(new_devices)}")
            for device in new_devices:
                logger.info(f"  - {device}")

        # Обновляем список известных устройств
        self.known_devices = current_devices

        return new_devices

    def monitor(self, callback=None):
        """
        Непрерывный мониторинг USB устройств

        Args:
            callback: Функция обратного вызова для обработки новых устройств
                     Сигнатура: callback(device_path: str)
        """
        logger.info("Запуск мониторинга USB устройств...")
        logger.info(f"Интервал проверки: {self.check_interval} сек")

        try:
            while True:
                new_devices = self.detect_new_devices()

                if new_devices and callback:
                    for device in new_devices:
                        try:
                            callback(device)
                        except Exception as e:
                            logger.error(f"Ошибка обработки устройства {device}: {e}")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Мониторинг остановлен пользователем")

    @staticmethod
    def is_audio_recorder(device_path: str) -> bool:
        """
        Проверка, является ли устройство аудио диктофоном
        Проверяет наличие аудио файлов

        Args:
            device_path: Путь к устройству

        Returns:
            True если найдены аудио файлы
        """
        audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}

        try:
            for root, dirs, files in os.walk(device_path):
                for file in files:
                    if Path(file).suffix.lower() in audio_extensions:
                        return True
        except Exception as e:
            logger.error(f"Ошибка проверки устройства {device_path}: {e}")

        return False


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_new_device(device_path):
        print(f"\n🔌 Новое устройство подключено: {device_path}")
        if USBMonitor.is_audio_recorder(device_path):
            print(f"✅ Это аудио диктофон!")
        else:
            print(f"❌ Аудио файлы не найдены")

    monitor = USBMonitor(check_interval=3)
    monitor.monitor(callback=on_new_device)
