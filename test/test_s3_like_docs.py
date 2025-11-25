import boto3
import logging
from dotenv import load_dotenv
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Создаем тестовый файл
test_file = Path("test_upload.txt")
test_file.write_text("Test content for S3 upload")

print("="*80)
print("ТОЧНО КАК В ДОКУМЕНТАЦИИ YANDEX CLOUD")
print("="*80)

# Создаем клиент ТОЧНО как в документации
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
    endpoint_url="https://storage.yandexcloud.net/",  # С trailing slash!
    # БЕЗ region_name!
)

try:
    # Проверка доступа к бакету
    print("\n1. Проверка доступа к бакету...")
    s3_client.head_bucket(Bucket=os.getenv("S3_BUCKET_NAME"))
    print(f"   ✅ Доступ к бакету {os.getenv('S3_BUCKET_NAME')} подтвержден")
except Exception as e:
    print(f"   ❌ Ошибка доступа к бакету: {e}")

try:
    # Загрузка файла
    print("\n2. Загрузка тестового файла...")
    s3_client.upload_file(
        str(test_file),
        os.getenv("S3_BUCKET_NAME"),
        "test/test_like_docs.txt"
    )
    print("   ✅ Файл загружен успешно")
    
    # Генерация presigned URL
    print("\n3. Генерация presigned URL...")
    presigned = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": os.getenv("S3_BUCKET_NAME"),
            "Key": "test/test_like_docs.txt",
        },
        ExpiresIn=3600,
    )
    print(f"   ✅ Presigned URL создан")
    print(f"   URL: {presigned[:100]}...")
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Удаляем тестовый файл
test_file.unlink()
