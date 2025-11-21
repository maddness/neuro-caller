import boto3
import logging
from dotenv import load_dotenv
import os

# Включаем DEBUG логирование для boto3
boto3.set_stream_logger('boto3.resources', logging.DEBUG)
boto3.set_stream_logger('botocore', logging.DEBUG)

load_dotenv()

# Создаем S3 клиент
s3_client = boto3.client(
    service_name='s3',
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
    region_name=os.getenv("S3_REGION_NAME", "ru-central1")
)

print("\n" + "="*80)
print("ПРОВЕРКА ДОСТУПА К БАКЕТУ")
print("="*80)

try:
    s3_client.head_bucket(Bucket=os.getenv("S3_BUCKET_NAME"))
    print("\n✅ Доступ к бакету подтвержден")
except Exception as e:
    print(f"\n❌ Ошибка доступа: {e}")
