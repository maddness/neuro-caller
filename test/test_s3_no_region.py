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
print("Тест 1: БЕЗ region_name")
print("="*80)

try:
    s3_client = boto3.client(
        service_name='s3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY")
        # region_name НЕ передаем!
    )
    
    s3_client.upload_file(
        str(test_file),
        os.getenv("S3_BUCKET_NAME"),
        "test/test_no_region.txt"
    )
    print("✅ Загрузка БЕЗ region_name успешна")
except Exception as e:
    print(f"❌ Ошибка БЕЗ region_name: {e}")

print("\n" + "="*80)
print("Тест 2: region_name = us-east-1")
print("="*80)

try:
    s3_client = boto3.client(
        service_name='s3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        region_name='us-east-1'
    )
    
    s3_client.upload_file(
        str(test_file),
        os.getenv("S3_BUCKET_NAME"),
        "test/test_us_east_1.txt"
    )
    print("✅ Загрузка с region_name=us-east-1 успешна")
except Exception as e:
    print(f"❌ Ошибка с region_name=us-east-1: {e}")

# Удаляем тестовый файл
test_file.unlink()
