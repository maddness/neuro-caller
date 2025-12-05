"""
File management: detection of new audio files and copying
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
    """Audio file management: detection and copying"""

    # Supported audio formats
    AUDIO_EXTENSIONS = {'.wav', '.m4a', '.ogg'}

    def __init__(
        self,
        local_storage_path: str = "data/audio",
        db_path: str = "data/processed_files.json",
        max_workers: int = 3
    ):
        """
        Args:
            local_storage_path: Path for storing copied files
            db_path: Path to processed files DB
            max_workers: Number of parallel threads for copying
        """
        self.local_storage_path = Path(local_storage_path)
        self.db_path = Path(db_path)
        self.max_workers = max_workers

        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Parallel copying: {max_workers} threads")

        self.processed_files = self._load_processed_files()

        self._metadata_lock = Lock()

        self.s3_uploader = None
        self.telegram_notifier = None
        self.tracker_client = None
        self.s3_presigned_url_expiry = 7 * 24 * 3600
        self.transcribe_conversation = False

    def _load_processed_files(self) -> Dict[str, dict]:
        """Load processed files DB"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading processed files DB: {e}")
                return {}
        return {}

    def _save_processed_files(self):
        """Atomic save of processed files DB via temp file"""
        try:
            temp_path = self.db_path.with_suffix('.json.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.db_path)
        except Exception as e:
            logger.error(f"Error saving processed files DB: {e}")

    def update_metadata(self, file_key: str, updates: dict):
        """
        Atomic thread-safe metadata update

        Args:
            file_key: File key (device_filename)
            updates: Dictionary with updates
        """
        with self._metadata_lock:
            if file_key not in self.processed_files:
                self.processed_files[file_key] = {}
            self.processed_files[file_key].update(updates)
            self._save_processed_files()

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """
        Calculate MD5 hash of file for identification

        Args:
            file_path: Path to file

        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash {file_path}: {e}")
            return ""

    @staticmethod
    def extract_date_from_filename(filename: str) -> str:
        """
        Extract date from filename format R20251124-120931.WAV

        Args:
            filename: File name

        Returns:
            Date in YYYY-MM-DD format or current date if parsing failed
        """
        match = re.match(r'R(\d{4})(\d{2})(\d{2})-\d{6}', filename)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month}-{day}"

        return datetime.now().strftime("%Y-%m-%d")

    def find_audio_files(self, device_path: str) -> List[Path]:
        """
        Find WAV files in RECORD folder on device

        Args:
            device_path: Path to device

        Returns:
            List of paths to WAV files from RECORD
        """
        audio_files = []

        try:
            records_path = Path(device_path) / 'RECORD'

            if not records_path.exists():
                logger.info(f"RECORD folder not found on {device_path}")
                return audio_files

            if not records_path.is_dir():
                logger.warning(f"RECORD exists but is not a folder on {device_path}")
                return audio_files

            for file in os.listdir(records_path):
                if file.startswith('._') or file.startswith('.'):
                    continue

                file_path = records_path / file

                if file_path.is_file() and file_path.suffix.lower() in self.AUDIO_EXTENSIONS:
                    audio_files.append(file_path)

            logger.info(f"Found {len(audio_files)} audio files in RECORD on {device_path}")

        except Exception as e:
            logger.error(f"Error searching files on {device_path}: {e}")

        return audio_files

    def _is_duplicate_by_device_and_name(self, file_path: Path, device_name: str) -> bool:
        """
        Check duplicate by device + filename (fast, no MD5)

        Args:
            file_path: Path to file
            device_name: Device name

        Returns:
            True if file with device+name already processed
        """
        filename = file_path.name
        file_key = f"{device_name}_{filename}"

        if file_key in self.processed_files:
            return True

        for file_info in self.processed_files.values():
            if (file_info.get("device") == device_name and
                Path(file_info.get("original_path", "")).name == filename):
                return True

        return False

    def find_new_files(self, device_path: str) -> List[Path]:
        """
        Find only new (unprocessed) files on device

        Args:
            device_path: Path to device

        Returns:
            List of new files
        """
        all_files = self.find_audio_files(device_path)
        new_files = []

        device_name = Path(device_path).name

        for file_path in all_files:
            if not self._is_duplicate_by_device_and_name(file_path, device_name):
                new_files.append(file_path)

        logger.info(f"Found {len(new_files)} new files")
        return new_files

    def copy_file(
        self,
        source_path: Path,
        device_name: str = None,
        storage_class: str = "STANDARD",
        file_key: str = None
    ) -> Dict:
        """
        Copy file to local storage and upload to S3 (if enabled)

        Args:
            source_path: Path to source file
            device_name: Device name (for organization)
            storage_class: S3 storage class (STANDARD, COLD, ICE)
            file_key: File key for stage tracking (optional)

        Returns:
            Dictionary with file info:
            {
                'local_path': Path,
                's3_key': str or None,
                's3_uploaded': bool,
                's3_url': str or None
            }
        """
        date_folder = datetime.now().strftime("%Y-%m-%d")
        device_folder = device_name or "unknown_device"

        destination_dir = self.local_storage_path / date_folder / device_folder
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination_path = destination_dir / source_path.name
        counter = 1
        while destination_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            destination_path = destination_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        result = {
            'local_path': None,
            's3_key': None,
            's3_uploaded': False,
            's3_url': None
        }

        try:
            if file_key:
                self.update_metadata(file_key, {
                    "stage": "copying",
                    "original_path": str(source_path),
                    "device": device_folder,
                    "size_bytes": source_path.stat().st_size
                })

            shutil.copy2(source_path, destination_path)
            logger.info(f"File copied: {source_path.name} -> {destination_path}")
            result['local_path'] = destination_path

            if file_key:
                self.update_metadata(file_key, {
                    "stage": "copied",
                    "local_path": str(destination_path),
                    "copied_at": datetime.now().isoformat()
                })

            if self.s3_uploader:
                date_folder = self.extract_date_from_filename(source_path.name)
                s3_key = f"{date_folder}/{device_folder}/{source_path.name}"

                if file_key:
                    self.update_metadata(file_key, {"stage": "s3_uploading"})

                # Check if file already exists in S3
                exists, exists_error = self.s3_uploader.file_exists(s3_key)

                if exists_error:
                    # Connection error during file check
                    logger.warning(f"S3 check failed: {exists_error}, will try to upload")

                if exists and not exists_error:
                    logger.info(f"File already exists in S3, skipping: {s3_key}")
                    result['s3_key'] = s3_key
                    result['s3_uploaded'] = True
                    result['s3_already_exists'] = True

                    if file_key:
                        self.update_metadata(file_key, {
                            "stage": "s3_uploaded",
                            "s3_key": s3_key
                        })
                else:
                    metadata = {
                        'device': device_folder,
                        'original_filename': source_path.name,
                        'upload_date': datetime.now().isoformat()
                    }

                    logger.info(f"Uploading to S3: {s3_key}")

                    s3_success, s3_error = self.s3_uploader.upload_file(
                        file_path=destination_path,
                        s3_key=s3_key,
                        storage_class=storage_class,
                        metadata=metadata
                    )

                    if s3_success:
                        result['s3_key'] = s3_key
                        result['s3_uploaded'] = True
                        result['s3_already_exists'] = False
                        logger.info(f"File uploaded to S3: {s3_key}")

                        if file_key:
                            self.update_metadata(file_key, {
                                "stage": "s3_uploaded",
                                "s3_key": s3_key
                            })
                    else:
                        logger.warning(f"Failed to upload file to S3: {s3_key} - {s3_error}")
                        if self.telegram_notifier:
                            self.telegram_notifier.notify_s3_upload_error(
                                filename=source_path.name,
                                error_message=s3_error or "Upload failed"
                            )

            return result

        except Exception as e:
            logger.error(f"Error copying file {source_path}: {e}")
            raise

    def process_new_files(self, device_path: str, device_name: str = None) -> List[Dict]:
        """
        Process new files from device: find, copy and register

        Args:
            device_path: Path to device
            device_name: Unique device name (if None, uses path name)

        Returns:
            List of copied files info
        """
        if device_name is None:
            device_name = Path(device_path).name

        new_files = self.find_new_files(device_path)

        if not new_files:
            logger.info("No new files found")
            return []

        logger.info(f"\nStarting copy of {len(new_files)} files from flash drive...")
        logger.info(f"   From: {device_path}")
        logger.info(f"   To: {self.local_storage_path}\n")

        total_size_bytes = sum(f.stat().st_size for f in new_files)
        total_size_mb_estimate = total_size_bytes / (1024 * 1024)

        if self.telegram_notifier:
            self.telegram_notifier.notify_copying_started(
                files_count=len(new_files),
                total_size_mb=total_size_mb_estimate,
                device_path=device_path
            )

        copied_files = []
        total_size_mb = 0

        def _copy_single_file(source_file: Path, file_index: int, total_files: int):
            """Copy single file with error handling"""
            try:
                file_size_mb = source_file.stat().st_size / (1024 * 1024)
                logger.info(f"   [{file_index}/{total_files}] Copying: {source_file.name} ({file_size_mb:.1f} MB)")

                file_key = f"{device_name}_{source_file.name}"

                if self.telegram_notifier:
                    self.telegram_notifier.notify_file_copied(
                        file_num=file_index,
                        total_files=total_files,
                        filename=source_file.name,
                        size_mb=file_size_mb,
                        device_path=str(source_file)
                    )

                copy_result = self.copy_file(source_file, device_name, file_key=file_key)
                destination_path = copy_result['local_path']

                file_info = self.processed_files.get(file_key, {})

                logger.info(f"        -> Copied to: {destination_path.relative_to(self.local_storage_path)}")
                if copy_result.get('s3_uploaded'):
                    if copy_result.get('s3_already_exists'):
                        logger.info(f"        -> Already in S3: {copy_result['s3_key']}")

                        if self.telegram_notifier:
                            self.telegram_notifier.notify_s3_already_exists(
                                s3_key=copy_result['s3_key'],
                                size_mb=file_size_mb
                            )
                    else:
                        logger.info(f"        -> Uploaded to S3: {copy_result['s3_key']}")

                        if self.telegram_notifier:
                            self.telegram_notifier.notify_s3_upload(
                                filename=source_file.name,
                                s3_key=copy_result['s3_key'],
                                size_mb=file_size_mb
                            )

                if self.tracker_client and self.tracker_client.enabled:
                    if not copy_result.get('s3_already_exists'):
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
                                logger.info(f"        -> Issue: {issue_key}")

                                self.update_metadata(file_key, {
                                    "stage": "completed",
                                    "tracker_issue_key": issue_key,
                                    "tracker_url": issue_url
                                })

                                if self.telegram_notifier:
                                    self.telegram_notifier.notify_tracker_issue_created(
                                        issue_key=issue_key,
                                        s3_key=copy_result['s3_key'],
                                        issue_url=issue_url
                                    )
                            else:
                                logger.error(f"        -> Failed to create tracker issue")
                                if self.telegram_notifier:
                                    self.telegram_notifier.notify_tracker_error(
                                        s3_key=copy_result['s3_key'],
                                        error_message="Issue creation failed"
                                    )
                    else:
                        self.update_metadata(file_key, {"stage": "completed"})

                return (file_index, file_key, file_info, file_size_mb, None)

            except Exception as e:
                logger.error(f"        -> Error copying {source_file.name}: {e}")
                if self.telegram_notifier:
                    self.telegram_notifier.notify_copy_error(
                        filename=source_file.name,
                        error_message=str(e)
                    )
                return (file_index, None, None, 0, str(e))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, source_file in enumerate(new_files, 1):
                future = executor.submit(_copy_single_file, source_file, i, len(new_files))
                futures[future] = source_file

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

            results.sort(key=lambda x: x[0])

            errors = []
            for file_index, file_key, file_info, size_mb, error in results:
                if error:
                    errors.append(error)
                else:
                    if file_key in self.processed_files:
                        self.processed_files[file_key].update(file_info)
                    else:
                        self.processed_files[file_key] = file_info
                    copied_files.append(self.processed_files[file_key])
                    total_size_mb += size_mb

        self._save_processed_files()

        if errors:
            logger.warning(f"\nErrors copying {len(errors)} files:")
            for error in errors:
                logger.warning(f"   - {error}")

        logger.info(f"\nTotal copied: {len(copied_files)}/{len(new_files)} files, {total_size_mb:.1f} MB")
        return copied_files

    def mark_as_processed(self, file_key: str):
        """
        Mark file as processed (transcribed)

        Args:
            file_key: File key (device_filename)
        """
        if file_key in self.processed_files:
            self.processed_files[file_key]["processed"] = True
            self.processed_files[file_key]["processed_at"] = datetime.now().isoformat()
            self._save_processed_files()

    def get_unprocessed_files(self) -> List[Dict]:
        """
        Get list of files not yet transcribed

        Returns:
            List of unprocessed files info
        """
        unprocessed = []
        for file_key, file_info in self.processed_files.items():
            if not file_info.get("processed", False):
                file_info["file_key"] = file_key
                unprocessed.append(file_info)

        return unprocessed

    def recover_incomplete_tasks(self) -> List[Dict]:
        """
        Recover incomplete tasks after restart.

        Checks all files in DB and returns those
        that didn't reach 'completed' stage.

        Returns:
            List of tasks for recovery:
            [{"file_key": str, "meta": dict, "action": str}]

            action can be:
            - "copy": need to copy again (stage: copying)
            - "s3_upload": need to upload to S3 (stage: copied, s3_uploading)
            - "tracker": need to create issue (stage: s3_uploaded, tracker_creating)
        """
        incomplete = []

        for file_key, meta in self.processed_files.items():
            stage = meta.get("stage")

            if stage == "completed" or stage is None:
                continue

            if stage == "copying":
                incomplete.append({
                    "file_key": file_key,
                    "meta": meta,
                    "action": "copy"
                })

            elif stage in ("copied", "s3_uploading"):
                incomplete.append({
                    "file_key": file_key,
                    "meta": meta,
                    "action": "s3_upload"
                })

            elif stage in ("s3_uploaded", "tracker_creating"):
                incomplete.append({
                    "file_key": file_key,
                    "meta": meta,
                    "action": "tracker"
                })

        if incomplete:
            logger.info(f"Recovery: found {len(incomplete)} incomplete tasks")
            for task in incomplete:
                logger.info(f"   - {task['file_key']}: stage={task['meta'].get('stage')}, action={task['action']}")

        return incomplete


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    fm = FileManager()

    test_device = "/media/usb0"
    if os.path.exists(test_device):
        copied = fm.process_new_files(test_device)
        print(f"\nCopied files: {len(copied)}")
        for file_info in copied:
            print(f"  - {file_info['local_path']}")
    else:
        print(f"Test device {test_device} not found")
