"""
S3 Uploader Module

Модуль для загрузки файлов в S3-совместимые хранилища
(Yandex Object Storage, AWS S3, MinIO и др.)

Основные возможности:
- Загрузка файлов в S3
- Проверка существования файлов
- Генерация временных ссылок для скачивания (presigned URLs)
- Retry при ошибках
- Подробное логирование
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class S3Uploader:
    """
    Класс для загрузки файлов в S3-совместимое хранилище

    Поддерживает:
    - Yandex Object Storage
    - AWS S3
    - MinIO
    - Другие S3-совместимые хранилища
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region_name: str = "ru-central1",
        retry_attempts: int = 3,
        timeout: int = 300
    ):
        """
        Инициализация S3 клиента

        Args:
            endpoint_url: URL S3 endpoint (например https://storage.yandexcloud.net)
            access_key_id: Access Key ID для аутентификации
            secret_access_key: Secret Access Key для аутентификации
            bucket_name: Имя бакета для хранения файлов
            region_name: Регион (для Yandex обычно ru-central1)
            retry_attempts: Количество повторных попыток при ошибке
            timeout: Таймаут операций в секундах
        """
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.retry_attempts = retry_attempts

        # Конфигурация с retry и таймаутом
        config = Config(
            retries={'max_attempts': retry_attempts, 'mode': 'standard'},
            connect_timeout=timeout,
            read_timeout=timeout
        )

        # Создаем S3 клиент
        try:
            self.s3_client = boto3.client(
                service_name='s3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region_name,
                config=config
            )

            logger.info(
                f"S3 клиент инициализирован: {endpoint_url}, "
                f"бакет: {bucket_name}, retry: {retry_attempts}"
            )

            # Проверяем доступ к бакету
            self._verify_bucket_access()

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Ошибка инициализации S3 клиента: {e}")
            raise

    def _verify_bucket_access(self) -> bool:
        """
        Проверка доступа к бакету

        Returns:
            True если доступ есть
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✓ Доступ к бакету {self.bucket_name} подтвержден")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                logger.error(f"✗ Бакет {self.bucket_name} не найден")
            elif error_code == '403':
                logger.error(f"✗ Нет доступа к бакету {self.bucket_name}")
            else:
                logger.error(f"✗ Ошибка доступа к бакету: {e}")
            return False

    def upload_file(
        self,
        file_path: Path,
        s3_key: str,
        storage_class: str = "STANDARD",
        acl: str = "private",
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Загрузка файла в S3

        Args:
            file_path: Путь к локальному файлу
            s3_key: Ключ (путь) в S3 (например: 2025_11_20/PERU_003/file.wav)
            storage_class: Класс хранилища (STANDARD, COLD, ICE)
            acl: Access Control List (private, public-read, etc)
            metadata: Дополнительные метаданные для файла

        Returns:
            True если загрузка успешна, False при ошибке
        """
        if not file_path.exists():
            logger.error(f"✗ Файл не найден: {file_path}")
            return False

        # Размер файла для логирования
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Формируем параметры загрузки
        extra_args = {
            'StorageClass': storage_class,
            'ACL': acl
        }

        # Добавляем метаданные если есть
        if metadata:
            extra_args['Metadata'] = metadata

        # Определяем Content-Type для WAV файлов
        if file_path.suffix.lower() in ['.wav', '.wave']:
            extra_args['ContentType'] = 'audio/wav'

        try:
            logger.info(
                f"Загрузка в S3: {file_path.name} ({file_size_mb:.1f} MB) "
                f"-> s3://{self.bucket_name}/{s3_key}"
            )

            # Загружаем файл
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"✓ Файл загружен в S3: {s3_key}")
            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(
                f"✗ Ошибка загрузки в S3 (код {error_code}): {e}"
            )
            return False
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка при загрузке: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Проверка существования файла в S3

        Args:
            s3_key: Ключ файла в S3

        Returns:
            True если файл существует
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                return False
            logger.error(f"✗ Ошибка проверки существования файла: {e}")
            return False

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 604800
    ) -> Optional[str]:
        """
        Генерация временной ссылки для скачивания файла (presigned URL)

        Args:
            s3_key: Ключ файла в S3
            expiration: Время жизни ссылки в секундах (по умолчанию 7 дней)

        Returns:
            Presigned URL или None при ошибке
        """
        try:
            # Проверяем существование файла
            if not self.file_exists(s3_key):
                logger.warning(f"⚠ Файл не найден в S3: {s3_key}")
                return None

            # Генерируем presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )

            # Вычисляем дату истечения для логирования
            expiry_date = datetime.now() + timedelta(seconds=expiration)
            logger.info(
                f"✓ Presigned URL создан для {s3_key} "
                f"(действителен до {expiry_date.strftime('%Y-%m-%d %H:%M')})"
            )

            return url

        except ClientError as e:
            logger.error(f"✗ Ошибка генерации presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка при генерации URL: {e}")
            return None

    def get_file_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о файле в S3

        Args:
            s3_key: Ключ файла в S3

        Returns:
            Словарь с информацией о файле или None
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType', 'unknown'),
                'metadata': response.get('Metadata', {})
            }

        except ClientError as e:
            logger.error(f"✗ Ошибка получения информации о файле: {e}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Удаление файла из S3

        Args:
            s3_key: Ключ файла в S3

        Returns:
            True если удаление успешно
        """
        try:
            logger.info(f"Удаление из S3: {s3_key}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"✓ Файл удален из S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"✗ Ошибка удаления файла: {e}")
            return False

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        Получение списка файлов в бакете

        Args:
            prefix: Префикс для фильтрации (например "2025_11_20/")
            max_keys: Максимальное количество файлов

        Returns:
            Список ключей файлов
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            files = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Найдено файлов в S3: {len(files)} (префикс: {prefix or 'все'})")
            return files

        except ClientError as e:
            logger.error(f"✗ Ошибка получения списка файлов: {e}")
            return []


# Пример использования
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Загружаем переменные окружения
    load_dotenv()

    # Проверяем что все переменные установлены
    if not all([
        os.getenv("S3_ENDPOINT_URL"),
        os.getenv("S3_ACCESS_KEY_ID"),
        os.getenv("S3_SECRET_ACCESS_KEY"),
        os.getenv("S3_BUCKET_NAME")
    ]):
        logger.error("Не все S3 переменные установлены в .env")
        exit(1)

    # Создаем S3 uploader
    uploader = S3Uploader(
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        bucket_name=os.getenv("S3_BUCKET_NAME"),
        region_name=os.getenv("S3_REGION_NAME", "ru-central1"),
        retry_attempts=int(os.getenv("S3_RETRY_ATTEMPTS", "3"))
    )

    # Пример: загрузка тестового файла
    test_file = Path("test.wav")
    if test_file.exists():
        s3_key = "2025_11_20/TEST_DEVICE/test.wav"

        # Метаданные
        metadata = {
            'device': 'TEST_DEVICE',
            'original_filename': test_file.name,
            'upload_date': datetime.now().isoformat()
        }

        # Загружаем
        success = uploader.upload_file(
            file_path=test_file,
            s3_key=s3_key,
            metadata=metadata
        )

        if success:
            # Генерируем ссылку на скачивание
            url = uploader.generate_presigned_url(s3_key, expiration=604800)
            if url:
                logger.info(f"Ссылка для скачивания: {url}")
    else:
        logger.info("Тестовый файл не найден. Пропускаем пример.")
