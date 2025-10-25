"""
Voximplant Manager - Python SDK для управления звонками через Voximplant API.

Этот модуль предоставляет интерфейс для:
- Инициации исходящих звонков
- Управления сценариями
- Получения статистики звонков
- Настройки конфигурации в Application Storage
"""

import os
import json
import logging
import hashlib
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
# Ищем .env в корневой директории проекта
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

# Настройка логирования
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoximplantManager:
    """Класс для управления Voximplant через API."""

    def __init__(self):
        """Инициализация менеджера с учетными данными из .env."""
        self.api_url = "https://api.voximplant.com/platform_api"
        self.account_id = os.getenv('VOXIMPLANT_ACCOUNT_ID')
        self.api_key = os.getenv('VOXIMPLANT_API_KEY')
        self.app_id = os.getenv('VOXIMPLANT_APP_ID')
        self.rule_id = os.getenv('VOXIMPLANT_RULE_ID')
        self.username = os.getenv('VOXIMPLANT_USERNAME')
        self.password = os.getenv('VOXIMPLANT_PASSWORD')
        self.phone_number = os.getenv('VOXIMPLANT_PHONE_NUMBER')

        # Проверяем наличие обязательных переменных
        self._validate_config()

        logger.info("VoximplantManager initialized")

    def _validate_config(self):
        """Проверка наличия обязательных переменных конфигурации."""
        required_vars = [
            'VOXIMPLANT_ACCOUNT_ID',
            'VOXIMPLANT_API_KEY',
            'VOXIMPLANT_APP_ID',
            'VOXIMPLANT_USERNAME',
            'VOXIMPLANT_PASSWORD'
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    def _get_api_signature(self, params: Dict[str, Any]) -> str:
        """
        Генерация подписи для API запроса.

        Args:
            params: Параметры запроса

        Returns:
            Хэш-подпись для авторизации
        """
        # Сортируем параметры по ключу
        sorted_params = sorted(params.items())

        # Формируем строку для подписи
        param_string = ''.join([f"{k}{v}" for k, v in sorted_params])

        # Добавляем API ключ
        signature_string = f"{param_string}{self.api_key}"

        # Генерируем MD5 хэш
        return hashlib.md5(signature_string.encode()).hexdigest()

    def login(self) -> bool:
        """
        Проверка подключения к Voximplant API.

        Returns:
            True если API ключ валиден
        """
        try:
            # Проверяем API ключ, запросив информацию об аккаунте
            params = {
                'account_id': self.account_id,
                'api_key': self.api_key
            }

            response = requests.post(
                f"{self.api_url}/GetAccountInfo",
                data=params
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    logger.info("Successfully connected to Voximplant API")
                    return True
                else:
                    error_msg = data.get('error', {}).get('msg', 'Unknown error')
                    logger.error(f"API connection failed: {error_msg}")
                    return False
            else:
                logger.error(f"API request failed with status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error during API check: {str(e)}")
            return False

    def make_call(self, to_number: str, custom_data: Optional[Dict] = None) -> Optional[str]:
        """
        Инициирует исходящий звонок через Voximplant.

        Args:
            to_number: Номер телефона для звонка (в формате +7XXXXXXXXXX)
            custom_data: Дополнительные данные для передачи в сценарий

        Returns:
            ID сессии звонка или None при ошибке
        """
        try:
            # Подготавливаем custom data
            call_data = {
                'phoneNumber': to_number,
                'timestamp': datetime.now().isoformat(),
                **(custom_data or {})
            }

            # Параметры для StartScenarios
            params = {
                'account_id': self.account_id,
                'api_key': self.api_key,
                'rule_id': self.rule_id,
                'script_custom_data': json.dumps(call_data)
            }

            # Делаем запрос
            response = requests.post(
                f"{self.api_url}/StartScenarios",
                data=params
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 1:
                    media_session_id = data.get('media_session_id')
                    logger.info(f"Call initiated successfully. Session ID: {media_session_id}")
                    return media_session_id
                else:
                    logger.error(f"Failed to start call: {data.get('error', 'Unknown error')}")
                    return None
            else:
                logger.error(f"Call request failed with status {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error making call: {str(e)}")
            return None

    def get_call_history(self, from_date: Optional[datetime] = None,
                        to_date: Optional[datetime] = None,
                        count: int = 100) -> Optional[List[Dict]]:
        """
        Получает историю звонков.

        Args:
            from_date: Начальная дата (по умолчанию - 24 часа назад)
            to_date: Конечная дата (по умолчанию - текущее время)
            count: Количество записей (максимум 1000)

        Returns:
            Список звонков или None при ошибке
        """
        try:
            # Убеждаемся, что мы авторизованы
            if not self.api_key:
                if not self.login():
                    logger.error("Failed to authenticate before getting history")
                    return None

            # Устанавливаем даты по умолчанию
            if not from_date:
                from_date = datetime.now() - timedelta(days=1)
            if not to_date:
                to_date = datetime.now()

            # Параметры запроса
            params = {
                'account_id': self.account_id,
                'api_key': self.api_key,
                'from_date': from_date.strftime('%Y-%m-%d %H:%M:%S'),
                'to_date': to_date.strftime('%Y-%m-%d %H:%M:%S'),
                'count': min(count, 1000),
                'with_records': True,
                'with_other_resources': True
            }

            # Генерируем подпись
            params['hash'] = self._get_api_signature(params)

            # Делаем запрос
            response = requests.post(
                f"{self.api_url}/GetCallHistory",
                data=params
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 1:
                    calls = data.get('sessions', [])
                    logger.info(f"Retrieved {len(calls)} call records")
                    return calls
                else:
                    logger.error(f"Failed to get history: {data.get('error', 'Unknown error')}")
                    return None
            else:
                logger.error(f"History request failed with status {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting call history: {str(e)}")
            return None

    def set_application_variable(self, key: str, value: str) -> bool:
        """
        Устанавливает переменную в Application Storage Voximplant.

        Args:
            key: Ключ переменной
            value: Значение переменной

        Returns:
            True если успешно, False в противном случае
        """
        try:
            # Убеждаемся, что мы авторизованы
            if not self.api_key:
                if not self.login():
                    logger.error("Failed to authenticate before setting variable")
                    return False

            # Параметры запроса
            params = {
                'account_id': self.account_id,
                'api_key': self.api_key,
                'application_id': self.app_id,
                'key': key,
                'value': value
            }

            # Генерируем подпись
            params['hash'] = self._get_api_signature(params)

            # Делаем запрос
            response = requests.post(
                f"{self.api_url}/SetApplicationVariable",
                data=params
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 1:
                    logger.info(f"Successfully set variable '{key}'")
                    return True
                else:
                    logger.error(f"Failed to set variable: {data.get('error', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Set variable request failed with status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error setting application variable: {str(e)}")
            return False

    def configure_openai_settings(self, openai_api_key: str,
                                 taxi_brand_name: str,
                                 recruitment_prompt: Optional[str] = None) -> bool:
        """
        Настраивает параметры OpenAI в Application Storage.

        Args:
            openai_api_key: API ключ OpenAI
            taxi_brand_name: Название такси бренда
            recruitment_prompt: Кастомный промпт для рекрутера

        Returns:
            True если все параметры установлены успешно
        """
        success = True

        # Устанавливаем OpenAI API ключ
        if not self.set_application_variable('openai_api_key', openai_api_key):
            logger.error("Failed to set OpenAI API key")
            success = False

        # Устанавливаем название бренда
        if not self.set_application_variable('taxi_brand_name', taxi_brand_name):
            logger.error("Failed to set taxi brand name")
            success = False

        # Устанавливаем промпт если указан
        if recruitment_prompt:
            if not self.set_application_variable('recruitment_prompt', recruitment_prompt):
                logger.error("Failed to set recruitment prompt")
                success = False

        if success:
            logger.info("OpenAI settings configured successfully")
        else:
            logger.error("Some OpenAI settings failed to configure")

        return success

    def get_statistics(self, period_days: int = 7) -> Optional[Dict]:
        """
        Получает статистику звонков за период.

        Args:
            period_days: Количество дней для анализа

        Returns:
            Словарь со статистикой или None при ошибке
        """
        try:
            # Получаем историю звонков
            from_date = datetime.now() - timedelta(days=period_days)
            calls = self.get_call_history(from_date=from_date)

            if calls is None:
                return None

            # Подсчитываем статистику
            stats = {
                'total_calls': len(calls),
                'successful_calls': 0,
                'failed_calls': 0,
                'average_duration': 0,
                'total_duration': 0,
                'calls_by_day': {},
                'calls_by_status': {}
            }

            total_duration = 0
            successful_count = 0

            for call in calls:
                # Статус звонка
                status = call.get('result_call_status', 'unknown')
                stats['calls_by_status'][status] = stats['calls_by_status'].get(status, 0) + 1

                # Успешные/неуспешные
                if status in ['NORMAL_CLEARING', 'connected']:
                    stats['successful_calls'] += 1
                    successful_count += 1
                else:
                    stats['failed_calls'] += 1

                # Длительность
                duration = call.get('duration', 0)
                total_duration += duration

                # По дням
                start_time = call.get('start_time')
                if start_time:
                    day = start_time.split(' ')[0]
                    stats['calls_by_day'][day] = stats['calls_by_day'].get(day, 0) + 1

            # Средняя длительность
            if successful_count > 0:
                stats['average_duration'] = round(total_duration / successful_count, 2)
            stats['total_duration'] = total_duration

            logger.info(f"Statistics calculated for {stats['total_calls']} calls")
            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return None


# Пример использования
if __name__ == "__main__":
    # Создаем менеджер
    manager = VoximplantManager()

    # Авторизуемся
    if manager.login():
        print("✅ Successfully logged in to Voximplant")

        # Настраиваем OpenAI
        openai_key = os.getenv('OPENAI_API_KEY')
        brand_name = os.getenv('TAXI_BRAND_NAME', 'Наше Такси')

        if openai_key:
            if manager.configure_openai_settings(openai_key, brand_name):
                print("✅ OpenAI settings configured")

        # Получаем статистику
        stats = manager.get_statistics(period_days=7)
        if stats:
            print("\n📊 Statistics for last 7 days:")
            print(f"  Total calls: {stats['total_calls']}")
            print(f"  Successful: {stats['successful_calls']}")
            print(f"  Failed: {stats['failed_calls']}")
            print(f"  Average duration: {stats['average_duration']} seconds")

        # Пример звонка
        # session_id = manager.make_call("+79991234567")
        # if session_id:
        #     print(f"✅ Call initiated with session ID: {session_id}")
    else:
        print("❌ Failed to login to Voximplant")