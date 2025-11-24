#!/usr/bin/env python3
"""
Клиент для работы с Яндекс Трекером
Создание задач после загрузки аудиофайлов в S3
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TrackerClient:
    """Клиент для Яндекс Трекера"""

    BASE_URL = "https://st-api.yandex-team.ru/v3"

    def __init__(
        self,
        oauth_token: str,
        queue: str = "YANGOSCOUTS",
        enabled: bool = True
    ):
        """
        Args:
            oauth_token: OAuth токен для авторизации
            queue: Ключ очереди для создания задач
            enabled: Включен ли клиент
        """
        self.oauth_token = oauth_token
        self.queue = queue
        self.enabled = enabled

        if not oauth_token and enabled:
            logger.warning("⚠️ TrackerClient: OAuth токен не указан, клиент отключен")
            self.enabled = False

    def _get_headers(self) -> dict:
        """Заголовки для запросов к API"""
        return {
            "Authorization": f"OAuth {self.oauth_token}",
            "Content-Type": "application/json"
        }

    def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "task",
        tags: Optional[list] = None,
        transcribe_conversation: bool = True
    ) -> Optional[dict]:
        """
        Создание задачи в трекере

        Args:
            summary: Заголовок задачи (например: "2025_11_21/PERU_000/R20251121-174442")
            description: Описание задачи (presigned URL)
            issue_type: Тип задачи (по умолчанию Task)
            tags: Список тегов
            transcribe_conversation: Выполнять транскрибацию разговора

        Returns:
            dict с данными созданной задачи или None при ошибке
        """
        if not self.enabled:
            logger.debug("TrackerClient отключен, задача не создана")
            return None

        url = f"{self.BASE_URL}/issues/"

        payload = {
            "summary": summary,
            "queue": {"key": self.queue},
            "type": {"key": issue_type},
            "description": description
        }

        if tags:
            payload["tags"] = tags

        try:
            logger.info(f"📋 Создание задачи в трекере: {summary}")

            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code == 201:
                issue_data = response.json()
                issue_key = issue_data.get("key", "unknown")
                logger.info(f"✅ Задача создана: {issue_key}")
                return issue_data
            else:
                logger.error(
                    f"❌ Ошибка создания задачи: {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут при создании задачи в трекере")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка запроса к трекеру: {e}")
            return None

    @staticmethod
    def build_summary_from_s3_key(s3_key: str) -> str:
        """
        Формирование summary из S3 ключа

        Args:
            s3_key: Ключ файла в S3 (например: "2025-11-21/PERU_000/R20251121-174442.wav")

        Returns:
            Форматированный summary (например: "2025_11_21/PERU_000/R20251121-174442")
        """
        # Убираем расширение файла
        if "." in s3_key:
            s3_key = s3_key.rsplit(".", 1)[0]

        # Заменяем дефисы на подчеркивания в дате (первый сегмент)
        parts = s3_key.split("/")
        if parts and "-" in parts[0]:
            parts[0] = parts[0].replace("-", "_")

        return "/".join(parts)


if __name__ == "__main__":
    # Тестирование
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(level=logging.DEBUG)

    token = os.getenv("TRACKER_OAUTH_TOKEN")
    queue = os.getenv("TRACKER_QUEUE", "YANGOSCOUTS")

    if not token:
        print("❌ TRACKER_OAUTH_TOKEN не задан в .env")
        exit(1)

    client = TrackerClient(oauth_token=token, queue=queue)

    # Тест формирования summary
    test_key = "2025-11-21/PERU_000/R20251121-174442.wav"
    summary = TrackerClient.build_summary_from_s3_key(test_key)
    print(f"S3 key: {test_key}")
    print(f"Summary: {summary}")

    # Тест создания задачи (раскомментировать для реального теста)
    # result = client.create_issue(
    #     summary=summary,
    #     description="https://storage.yandexcloud.net/bucket/test-presigned-url"
    # )
    # print(f"Result: {result}")
