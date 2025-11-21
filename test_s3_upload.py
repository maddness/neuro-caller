import boto3
import logging
from dotenv import load_dotenv
import os
from pathlib import Path

# Включаем DEBUG логирование
boto3.set_stream_logger('botocore', logging.DEBUG)

load_dotenv()

# Создаем тестовый файл
test_file = Path("test_upload.txt")
test_file.write_text("Test content for S3 upload")

# Создаем S3 клиент
s3_client = boto3.client(
    service_name='s3',
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
    region_name=os.getenv("S3_REGION_NAME", "ru-central1")
)

print("\n" + "="*80)
print("ЗАГРУЗКА ТЕСТОВОГО ФАЙЛА В S3")
print("="*80)

try:
    s3_client.upload_file(
        str(test_file),
        os.getenv("S3_BUCKET_NAME"),
        "test/test_upload.txt",
        ExtraArgs={
            'StorageClass': 'STANDARD',
            'ACL': 'private',
            'ContentType': 'text/plain'
        }
    )
    print("\n✅ Файл загружен успешно")
except Exception as e:
    print(f"\n❌ Ошибка загрузки: {e}")

# Удаляем тестовый файл
test_file.unlink()
