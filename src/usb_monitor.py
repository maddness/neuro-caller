"""
USB device monitoring and detection
Detects connection of new USB recorders
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
    """USB device monitoring and recorder detection"""

    def __init__(self, check_interval: int = 5):
        """
        Args:
            check_interval: Interval for checking new devices (seconds)
        """
        self.check_interval = check_interval
        self.known_devices: Set[str] = set()
        self.processing_devices: Set[str] = set()
        self._initialize_known_devices()

    def _initialize_known_devices(self):
        """Initialize list of known devices at startup"""
        devices = self.get_mounted_devices()
        self.known_devices = set(devices)
        logger.info(f"Initialized {len(self.known_devices)} known devices")

    @staticmethod
    def get_mounted_devices() -> List[str]:
        """Get list of mounted USB devices filtered by PERU_ label"""
        devices = []

        for partition in psutil.disk_partitions(all=False):
            mount_point = partition.mountpoint

            if '/media' in mount_point or '/mnt' in mount_point or '/Volumes' in mount_point:
                if mount_point not in ['/', '/Volumes/Macintosh HD']:
                    if os.path.exists(mount_point) and os.path.isdir(mount_point):
                        device_info = USBMonitor.get_device_info(mount_point)
                        label = device_info.get('label') or ''
                        if label.startswith('PERU_'):
                            devices.append(mount_point)
                        else:
                            logger.debug(f"Device {mount_point} skipped: label '{label}' does not start with PERU_")
            elif partition.device.startswith('/dev/sd'):
                try:
                    device_name = partition.device.split('/')[-1].rstrip('0123456789')
                    removable_path = f"/sys/block/{device_name}/removable"
                    if os.path.exists(removable_path):
                        with open(removable_path, 'r') as f:
                            if f.read().strip() == '1':
                                device_info = USBMonitor.get_device_info(mount_point)
                                label = device_info.get('label') or ''
                                if label.startswith('PERU_'):
                                    devices.append(mount_point)
                                else:
                                    logger.debug(f"Device {mount_point} skipped: label '{label}' does not start with PERU_")
                except Exception as e:
                    logger.debug(f"Device check error {partition.device}: {e}")

        return devices

    def detect_new_devices(self) -> List[str]:
        """
        Detect newly connected devices

        Returns:
            List of paths to new devices
        """
        current_devices = set(self.get_mounted_devices())
        new_devices = list(current_devices - self.known_devices)

        if new_devices:
            logger.info(f"New devices detected: {len(new_devices)}")
            for device in new_devices:
                logger.info(f"  - {device}")

        self.known_devices = current_devices

        return new_devices

    def detect_disconnected_devices(self) -> List[str]:
        """
        Detect disconnected devices

        Returns:
            List of paths to disconnected devices
        """
        current_devices = set(self.get_mounted_devices())
        disconnected = list(self.known_devices - current_devices)

        if disconnected:
            logger.info(f"Disconnected devices detected: {len(disconnected)}")
            for device in disconnected:
                logger.info(f"  - {device}")

        return disconnected

    def monitor(self, callback=None, on_disconnect=None):
        """
        Continuous USB device monitoring

        Args:
            callback: Callback function for processing new devices
                     Signature: callback(device_path: str)
            on_disconnect: Callback function when device disconnects
                     Signature: on_disconnect(device_path: str)
        """
        logger.info("Starting USB device monitoring...")
        logger.info(f"Check interval: {self.check_interval} sec")

        first_run = True

        try:
            while True:
                current_devices = set(self.get_mounted_devices())
                disconnected = list(self.known_devices - current_devices)

                if disconnected and on_disconnect:
                    for device in disconnected:
                        logger.info(f"Device disconnected: {device}")
                        try:
                            on_disconnect(device)
                        except Exception as e:
                            logger.error(f"Disconnect handling error {device}: {e}")

                new_devices = list(current_devices - self.known_devices)
                if new_devices:
                    logger.info(f"New devices detected: {len(new_devices)}")
                    for device in new_devices:
                        logger.info(f"  - {device}")

                self.known_devices = current_devices

                devices_to_process = []

                if first_run:
                    current_list = list(self.known_devices)
                    if current_list:
                        logger.info(f"First run: checking {len(current_list)} already connected devices...")
                        devices_to_process.extend(current_list)
                    first_run = False

                devices_to_process.extend(new_devices)

                if devices_to_process and callback:
                    for device in devices_to_process:
                        if device in self.processing_devices:
                            logger.info(f"Device {device} already being processed, skipping")
                            continue

                        try:
                            self.processing_devices.add(device)
                            logger.debug(f"Started processing device {device}")

                            callback(device)

                            self.processing_devices.discard(device)
                            logger.debug(f"Finished processing device {device}")

                        except Exception as e:
                            logger.error(f"Device processing error {device}: {e}")
                            self.processing_devices.discard(device)

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")

    @staticmethod
    def get_device_info(mount_point: str) -> Dict[str, str]:
        """
        Get unique device information

        Args:
            mount_point: Device mount point

        Returns:
            Dictionary with device info (uuid, label, serial, unique_id)
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
            for partition in psutil.disk_partitions(all=False):
                if partition.mountpoint == mount_point:
                    info['device'] = partition.device
                    break

            if not info['device']:
                logger.warning(f"Device not found for {mount_point}")
                info['unique_id'] = Path(mount_point).name
                return info

            device = info['device']

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
                logger.debug(f"Failed to get UUID for {device}: {e}")

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
                logger.debug(f"Failed to get LABEL for {device}: {e}")

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
                    logger.debug(f"Failed to get label via diskutil for {device}: {e}")

            if not info['label']:
                mount_name = Path(mount_point).name
                if not mount_name.startswith('System') and mount_name not in ['VM', 'Preboot', 'Update', 'Data', 'Hardware', 'xarts', 'iSCPreboot']:
                    info['label'] = mount_name

            try:
                device_name = device.split('/')[-1].rstrip('0123456789')
                serial_path = f"/sys/block/{device_name}/device/serial"

                if os.path.exists(serial_path):
                    with open(serial_path, 'r') as f:
                        info['serial'] = f.read().strip()
            except Exception as e:
                logger.debug(f"Failed to get serial for {device}: {e}")

            if info['uuid']:
                info['unique_id'] = f"UUID_{info['uuid'][:8]}"
            elif info['serial']:
                info['unique_id'] = f"SN_{info['serial']}"
            elif info['label']:
                info['unique_id'] = info['label']
            else:
                info['unique_id'] = Path(mount_point).name

            logger.debug(f"Device info {mount_point}: {info}")

        except Exception as e:
            logger.error(f"Error getting device info {mount_point}: {e}")
            info['unique_id'] = Path(mount_point).name

        return info

    @staticmethod
    def is_audio_recorder(device_path: str) -> bool:
        """
        Check if device is an audio recorder
        Checks for audio files presence

        Args:
            device_path: Path to device

        Returns:
            True if audio files found
        """
        audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}

        try:
            for root, dirs, files in os.walk(device_path):
                for file in files:
                    if Path(file).suffix.lower() in audio_extensions:
                        return True
        except Exception as e:
            logger.error(f"Device check error {device_path}: {e}")

        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_new_device(device_path):
        print(f"\nNew device connected: {device_path}")

        device_info = USBMonitor.get_device_info(device_path)
        print(f"   Unique ID: {device_info['unique_id']}")
        if device_info['label']:
            print(f"   Label: {device_info['label']}")
        if device_info['uuid']:
            print(f"   UUID: {device_info['uuid']}")
        if device_info['serial']:
            print(f"   Serial: {device_info['serial']}")

        if USBMonitor.is_audio_recorder(device_path):
            print(f"This is an audio recorder!")
        else:
            print(f"No audio files found")

    monitor = USBMonitor(check_interval=3)
    monitor.monitor(callback=on_new_device)
