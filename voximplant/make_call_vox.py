#!/usr/bin/env python3
"""
Скрипт для совершения исходящих звонков через Voximplant.

Использование:
    python make_call_vox.py +79991234567
    python make_call_vox.py +79991234567 --test
"""

import sys
import os
import argparse
import time
from datetime import datetime

# Добавляем путь к модулю vox_manager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vox_manager import VoximplantManager


def validate_phone_number(phone_number: str) -> bool:
    """
    Проверка формата номера телефона.

    Args:
        phone_number: Номер телефона для проверки

    Returns:
        True если формат корректный
    """
    # Убираем пробелы и дефисы
    cleaned = phone_number.replace(' ', '').replace('-', '')

    # Проверяем формат
    if not cleaned.startswith('+'):
        print("❌ Номер должен начинаться с '+'")
        return False

    if not cleaned[1:].isdigit():
        print("❌ Номер должен содержать только цифры после '+'")
        return False

    if len(cleaned) < 11 or len(cleaned) > 15:
        print("❌ Некорректная длина номера")
        return False

    return True


def format_duration(seconds: int) -> str:
    """
    Форматирует длительность в читаемый вид.

    Args:
        seconds: Количество секунд

    Returns:
        Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} мин {secs} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours} ч {minutes} мин {secs} сек"


def main():
    """Основная функция скрипта."""
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(
        description='Совершить звонок через Voximplant AI рекрутера'
    )
    parser.add_argument(
        'phone_number',
        help='Номер телефона в формате +7XXXXXXXXXX'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Тестовый режим (только проверка подключения)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Показать статистику после звонка'
    )
    parser.add_argument(
        '--configure',
        action='store_true',
        help='Настроить OpenAI параметры перед звонком'
    )

    args = parser.parse_args()

    # Проверяем формат номера
    if not validate_phone_number(args.phone_number):
        sys.exit(1)

    print("🤖 Neuro-Caller (Voximplant Edition)")
    print("=" * 50)

    try:
        # Создаем менеджер
        print("📱 Инициализация Voximplant Manager...")
        manager = VoximplantManager()

        # Авторизуемся
        print("🔐 Авторизация в Voximplant API...")
        if not manager.login():
            print("❌ Не удалось авторизоваться в Voximplant")
            sys.exit(1)
        print("✅ Авторизация успешна")

        # Если нужно настроить OpenAI
        if args.configure:
            print("\n⚙️  Настройка OpenAI параметров...")
            openai_key = os.getenv('OPENAI_API_KEY')
            brand_name = os.getenv('TAXI_BRAND_NAME', 'Наше Такси')
            recruitment_prompt = os.getenv('RECRUITMENT_PROMPT')

            if not openai_key:
                print("❌ Не найден OPENAI_API_KEY в переменных окружения")
                sys.exit(1)

            if manager.configure_openai_settings(openai_key, brand_name, recruitment_prompt):
                print("✅ OpenAI параметры настроены")
            else:
                print("⚠️  Некоторые параметры не удалось настроить")

        # В тестовом режиме только проверяем подключение
        if args.test:
            print("\n🧪 Тестовый режим - проверка подключения")
            print("✅ Все системы работают корректно")
            print("ℹ️  Для реального звонка запустите без флага --test")
            sys.exit(0)

        # Совершаем звонок
        print(f"\n☎️  Звоним на номер: {args.phone_number}")
        print("⏳ Инициализация звонка...")

        session_id = manager.make_call(args.phone_number)

        if session_id:
            print(f"✅ Звонок инициирован!")
            print(f"📞 Session ID: {session_id}")
            print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n🎙️ AI рекрутер Анна начинает разговор...")
            print("💡 Подсказка: Звонок будет автоматически завершен после окончания разговора")

            # Показываем статистику если запрошено
            if args.stats:
                print("\n⏳ Ожидание завершения звонка для сбора статистики...")
                print("   (Нажмите Ctrl+C для пропуска)")

                try:
                    # Ждем немного перед запросом статистики
                    time.sleep(10)

                    # Получаем статистику
                    stats = manager.get_statistics(period_days=1)
                    if stats:
                        print("\n📊 Статистика за сегодня:")
                        print(f"  Всего звонков: {stats['total_calls']}")
                        print(f"  Успешных: {stats['successful_calls']}")
                        print(f"  Неудачных: {stats['failed_calls']}")
                        if stats['average_duration'] > 0:
                            print(f"  Средняя длительность: {format_duration(int(stats['average_duration']))}")
                except KeyboardInterrupt:
                    print("\n⏭️  Пропуск статистики...")

            print("\n✨ Операция завершена успешно!")

        else:
            print("❌ Не удалось инициировать звонок")
            print("📋 Проверьте:")
            print("   - Корректность номера телефона")
            print("   - Баланс Voximplant аккаунта")
            print("   - Настройки правила (rule) в Voximplant")
            print("   - Логи в панели управления Voximplant")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Операция прервана пользователем")
        sys.exit(0)
    except ValueError as e:
        print(f"\n❌ Ошибка конфигурации: {e}")
        print("📋 Проверьте файл .env.voximplant")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()