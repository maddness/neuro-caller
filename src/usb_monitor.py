"""
USB устройства мониторинг и обнаружение
Обнаруживает подключение новых USB диктофонов
"""

import os
import time
import logging
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Dict
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
        self.processing_devices: Set[str] = set()  # Устройства в процессе обработки
        self._initialize_known_devices()

    def _initialize_known_devices(self):
        """Инициализация списка известных устройств при старте"""
        devices = self.get_mounted_devices()
        self.known_devices = set(devices)
        logger.info(f"Инициализировано {len(self.known_devices)} известных устройств")

    @staticmethod
    def get_mounted_devices() -> List[str]:
        """Получить список смонтированных USB устройств с фильтрацией по label PERU_"""
        devices = []

        for partition in psutil.disk_partitions(all=False):
            # Фильтруем только съемные устройства (обычно /media, /mnt или removable)
            mount_point = partition.mountpoint

            # В Linux USB обычно монтируются в /media или /mnt
            # В macOS USB монтируются в /Volumes
            if '/media' in mount_point or '/mnt' in mount_point or '/Volumes' in mount_point:
                # Исключаем системный диск macOS
                if mount_point not in ['/', '/Volumes/Macintosh HD']:
                    if os.path.exists(mount_point) and os.path.isdir(mount_point):
                        # Проверяем label устройства - только PERU_*
                        device_info = USBMonitor.get_device_info(mount_point)
                        label = device_info.get('label') or ''
                        if label.startswith('PERU_'):
                            devices.append(mount_point)
                        else:
                            logger.debug(f"Устройство {mount_point} пропущено: label '{label}' не начинается с PERU_")
            # Дополнительная проверка для removable устройств
            elif partition.device.startswith('/dev/sd'):
                try:
                    # Проверяем, является ли устройство съемным
                    device_name = partition.device.split('/')[-1].rstrip('0123456789')
                    removable_path = f"/sys/block/{device_name}/removable"
                    if os.path.exists(removable_path):
                        with open(removable_path, 'r') as f:
                            if f.read().strip() == '1':
                                # Проверяем label устройства - только PERU_*
                                device_info = USBMonitor.get_device_info(mount_point)
                                label = device_info.get('label') or ''
                                if label.startswith('PERU_'):
                                    devices.append(mount_point)
                                else:
                                    logger.debug(f"Устройство {mount_point} пропущено: label '{label}' не начинается с PERU_")
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

    def detect_disconnected_devices(self) -> List[str]:
        """
        Обнаружение отключенных устройств

        Returns:
            Список путей к отключенным устройствам
        """
        current_devices = set(self.get_mounted_devices())
        disconnected = list(self.known_devices - current_devices)

        if disconnected:
            logger.info(f"Обнаружено отключенных устройств: {len(disconnected)}")
            for device in disconnected:
                logger.info(f"  - {device}")

        return disconnected

    def monitor(self, callback=None, on_disconnect=None):
        """
        Непрерывный мониторинг USB устройств

        Args:
            callback: Функция обратного вызова для обработки новых устройств
                     Сигнатура: callback(device_path: str)
            on_disconnect: Функция обратного вызова при отключении устройства
                     Сигнатура: on_disconnect(device_path: str)
        """
        logger.info("Запуск мониторинга USB устройств...")
        logger.info(f"Интервал проверки: {self.check_interval} сек")

        # Флаг первого запуска - проверяем уже подключенные устройства
        first_run = True

        try:
            while True:
                # Сначала проверяем отключенные устройства
                current_devices = set(self.get_mounted_devices())
                disconnected = list(self.known_devices - current_devices)

                if disconnected and on_disconnect:
                    for device in disconnected:
                        logger.info(f"⏏️ Устройство отключено: {device}")
                        try:
                            on_disconnect(device)
                        except Exception as e:
                            logger.error(f"Ошибка обработки отключения {device}: {e}")

                # Обновляем known_devices после проверки отключений
                new_devices = list(current_devices - self.known_devices)
                if new_devices:
                    logger.info(f"Обнаружено новых устройств: {len(new_devices)}")
                    for device in new_devices:
                        logger.info(f"  - {device}")

                self.known_devices = current_devices

                # Устройства для обработки
                devices_to_process = []

                # При первом запуске обрабатываем все уже подключенные устройства
                if first_run:
                    current_list = list(self.known_devices)
                    if current_list:
                        logger.info(f"Первый запуск: проверка {len(current_list)} уже подключенных устройств...")
                        devices_to_process.extend(current_list)
                    first_run = False

                # Добавляем новые устройства
                devices_to_process.extend(new_devices)

                if devices_to_process and callback:
                    for device in devices_to_process:
                        # Проверяем что устройство не обрабатывается в данный момент
                        if device in self.processing_devices:
                            logger.info(f"⚠️  Устройство {device} уже обрабатывается, пропускаем")
                            continue

                        try:
                            # Добавляем устройство в список обрабатываемых
                            self.processing_devices.add(device)
                            logger.debug(f"Начата обработка устройства {device}")

                            # Вызываем callback для обработки устройства
                            callback(device)

                            # Удаляем из списка обрабатываемых после завершения
                            self.processing_devices.discard(device)
                            logger.debug(f"Завершена обработка устройства {device}")

                        except Exception as e:
                            logger.error(f"Ошибка обработки устройства {device}: {e}")
                            # Обязательно удаляем из списка обрабатываемых при ошибке
                            self.processing_devices.discard(device)

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Мониторинг остановлен пользователем")

    @staticmethod
    def get_device_info(mount_point: str) -> Dict[str, str]:
        """
        Получить уникальную информацию об устройстве

        Args:
            mount_point: Точка монтирования устройства

        Returns:
            Словарь с информацией об устройстве (uuid, label, serial, unique_id)
        """
        info = {
            'mount_point': mount_point,
            'uuid': None,
            'label': None,
            'serial': None,
            'device': None,
            'unique_id': None
        }

        try:
            # Получаем устройство для точки монтирования
            for partition in psutil.disk_partitions(all=False):
                if partition.mountpoint == mount_point:
                    info['device'] = partition.device
                    break

            if not info['device']:
                logger.warning(f"Не найдено устройство для {mount_point}")
                # Используем имя точки монтирования как fallback
                info['unique_id'] = Path(mount_point).name
                return info

            device = info['device']

            # Получаем UUID устройства
            try:
                result = subprocess.run(
                    ['blkid', '-s', 'UUID', '-o', 'value', device],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    info['uuid'] = result.stdout.strip()
            except Exception as e:
                logger.debug(f"Не удалось получить UUID для {device}: {e}")

            # Получаем LABEL устройства
            try:
                result = subprocess.run(
                    ['blkid', '-s', 'LABEL', '-o', 'value', device],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    info['label'] = result.stdout.strip()
            except Exception as e:
                logger.debug(f"Не удалось получить LABEL для {device}: {e}")

            # На macOS используем diskutil для получения label
            if not info['label'] and device:
                try:
                    result = subprocess.run(
                        ['diskutil', 'info', device],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Volume Name:' in line:
                                label = line.split(':', 1)[1].strip()
                                if label and label != 'Not applicable (no file system)':
                                    info['label'] = label
                                break
                except Exception as e:
                    logger.debug(f"Не удалось получить label через diskutil для {device}: {e}")

            # Fallback: если label всё ещё не найден, используем имя точки монтирования
            if not info['label']:
                mount_name = Path(mount_point).name
                # Исключаем системные директории
                if not mount_name.startswith('System') and mount_name not in ['VM', 'Preboot', 'Update', 'Data', 'Hardware', 'xarts', 'iSCPreboot']:
                    info['label'] = mount_name

            # Получаем serial number (если доступен)
            try:
                # Извлекаем имя устройства без номера раздела (sdb1 -> sdb)
                device_name = device.split('/')[-1].rstrip('0123456789')
                serial_path = f"/sys/block/{device_name}/device/serial"

                if os.path.exists(serial_path):
                    with open(serial_path, 'r') as f:
                        info['serial'] = f.read().strip()
            except Exception as e:
                logger.debug(f"Не удалось получить serial для {device}: {e}")

            # Формируем уникальный ID
            # Приоритет: UUID > Serial > Label > имя точки монтирования
            if info['uuid']:
                info['unique_id'] = f"UUID_{info['uuid'][:8]}"
            elif info['serial']:
                info['unique_id'] = f"SN_{info['serial']}"
            elif info['label']:
                info['unique_id'] = info['label']
            else:
                # Последний вариант - используем имя точки монтирования
                info['unique_id'] = Path(mount_point).name

            logger.debug(f"Информация об устройстве {mount_point}: {info}")

        except Exception as e:
            logger.error(f"Ошибка получения информации об устройстве {mount_point}: {e}")
            # Fallback - используем имя точки монтирования
            info['unique_id'] = Path(mount_point).name

        return info

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

        # Получаем информацию об устройстве
        device_info = USBMonitor.get_device_info(device_path)
        print(f"   Уникальный ID: {device_info['unique_id']}")
        if device_info['label']:
            print(f"   Метка: {device_info['label']}")
        if device_info['uuid']:
            print(f"   UUID: {device_info['uuid']}")
        if device_info['serial']:
            print(f"   Serial: {device_info['serial']}")

        if USBMonitor.is_audio_recorder(device_path):
            print(f"✅ Это аудио диктофон!")
        else:
            print(f"❌ Аудио файлы не найдены")

    monitor = USBMonitor(check_interval=3)
    monitor.monitor(callback=on_new_device)
