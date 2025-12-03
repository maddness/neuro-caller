"""
Telegram уведомления о процессе обработки
Отправляет сообщения в Telegram о всех этапах работы
"""

import logging
from typing import Optional
import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Отправка уведомлений в Telegram о процессе обработки"""

    def __init__(self, bot_token: str = None, chat_id: str = None, enabled: bool = True):
        """
        Args:
            bot_token: Токен Telegram бота
            chat_id: ID чата для отправки сообщений
            enabled: Включены ли уведомления
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bot_token and chat_id

        if self.enabled:
            logger.info("✅ Telegram бот инициализирован")
        else:
            logger.info("ℹ️  Telegram уведомления отключены")

    async def _send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        reply_markup: InlineKeyboardMarkup = None
    ):
        """
        Отправка сообщения в Telegram

        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
            reply_markup: Inline клавиатура с кнопками
        """
        if not self.enabled:
            return

        bot = None
        try:
            # Создаем бота для каждой отправки (чтобы избежать проблем с закрытым event loop)
            bot = Bot(token=self.bot_token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=False
            )
            logger.debug(f"Telegram сообщение отправлено: {text[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram сообщения: {e}")
        finally:
            # Закрываем сессию бота
            if bot:
                await bot.session.close()

    def send_message_sync(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        reply_markup: InlineKeyboardMarkup = None
    ):
        """
        Синхронная отправка сообщения (для использования в обычном коде)

        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга
            reply_markup: Inline клавиатура с кнопками
        """
        if not self.enabled:
            return

        try:
            # asyncio.run() создает новый event loop для каждого вызова
            # Это работает в потоках ThreadPoolExecutor
            asyncio.run(self._send_message(text, parse_mode, reply_markup))
        except Exception as e:
            logger.error(f"Ошибка синхронной отправки сообщения: {e}")

    # ========================================================================
    # Уведомления о различных этапах
    # ========================================================================

    def notify_process_started(self, hostname: str = None):
        """Уведомление о запуске процесса мониторинга"""
        import socket
        hostname = hostname or socket.gethostname()
        text = f"🚀 <b>Мониторинг запущен</b>\n\n💻 Компьютер: <code>{hostname}</code>\nОжидаю подключения USB диктофонов..."
        self.send_message_sync(text)

    def notify_device_connected(self, device_path: str, device_id: str, label: str = None):
        """
        Уведомление о подключении устройства

        Args:
            device_path: Путь к устройству
            device_id: Уникальный ID устройства
            label: Метка устройства
        """
        device_name = label if label else device_id

        text = (
            f"🔌 <b>Устройство подключено</b>\n\n"
            f"📍 Путь: <code>{device_path}</code>\n"
            f"🆔 ID: <code>{device_id}</code>\n"
        )

        if label:
            text += f"🏷 Метка: <b>{label}</b>\n"

        self.send_message_sync(text)

    def notify_copying_started(self, files_count: int, total_size_mb: float, device_path: str = None):
        """
        Уведомление о начале копирования файлов

        Args:
            files_count: Количество файлов
            total_size_mb: Общий размер в MB
            device_path: Путь к устройству
        """
        text = f"📦 <b>Начинаю копирование</b>\n\n"

        if device_path:
            text += f"📍 Путь: <code>{device_path}</code>\n"

        text += f"📁 Файлов: <b>{files_count}</b>\n"
        text += f"💾 Размер: <b>{total_size_mb:.1f} MB</b>"

        self.send_message_sync(text)

    def notify_file_copied(self, file_num: int, total_files: int, filename: str, size_mb: float, device_path: str = None):
        """
        Уведомление о копировании файла

        Args:
            file_num: Номер файла
            total_files: Всего файлов
            filename: Имя файла
            size_mb: Размер в MB
            device_path: Полный путь к файлу на устройстве (опционально)
        """
        text = f"📄 <b>[{file_num}/{total_files}]</b> Копирую...\n\n"

        if device_path:
            text += f"📍 <code>{device_path}</code>\n"
        else:
            text += f"📝 {filename}\n"

        text += f"💾 {size_mb:.1f} MB"

        self.send_message_sync(text)

    def notify_copying_complete(self, files_count: int, device_name: str = None):
        """
        Уведомление об окончании копирования

        Args:
            files_count: Количество скопированных файлов
            device_name: Имя устройства (опционально)
        """
        text = f"✅ <b>ВСЕ ФАЙЛЫ СКОПИРОВАНЫ!</b>\n\n"
        text += f"📁 Скопировано: <b>{files_count}</b> файлов\n"

        if device_name:
            text += f"🆔 Устройство: <code>{device_name}</code>\n"

        text += f"\n🔓 <b>Можно отключить диктофон</b>"

        self.send_message_sync(text)

    def notify_s3_upload(
        self,
        filename: str,
        s3_key: str,
        size_mb: float,
        presigned_url: str = None,
        expiry_days: int = 7
    ):
        """
        Уведомление о загрузке файла в S3 Object Storage

        Args:
            filename: Имя файла
            s3_key: Ключ файла в S3 (путь в бакете)
            size_mb: Размер файла в MB
            presigned_url: Временная ссылка для скачивания (опционально)
            expiry_days: Срок действия ссылки в днях (по умолчанию 7)
        """
        text = (
            f"☁️ <b>Файл загружен в S3</b>\n\n"
            f"📍 <code>{s3_key}</code>\n"
            f"💾 Размер: <b>{size_mb:.1f} MB</b>"
        )

        # Добавляем информацию о сроке действия ссылки
        if presigned_url:
            text += f"\n\n🔗 Ссылка действительна <b>{expiry_days} дней</b>"

        # Создаем inline кнопку для скачивания если есть URL
        reply_markup = None
        if presigned_url:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬇️ Скачать из S3", url=presigned_url)]
                ]
            )
            reply_markup = keyboard

        self.send_message_sync(text, reply_markup=reply_markup)

    def notify_s3_already_exists(self, s3_key: str, size_mb: float):
        """
        Уведомление о том, что файл уже существует в S3

        Args:
            s3_key: Ключ файла в S3 (полный путь)
            size_mb: Размер файла в MB
        """
        text = (
            f"⏩ <b>Файл уже существует в S3</b>\n\n"
            f"📍 <code>{s3_key}</code>\n"
            f"💾 Размер: <b>{size_mb:.1f} MB</b>"
        )

        self.send_message_sync(text)

    def notify_s3_upload_error(self, filename: str, error_message: str):
        """
        Уведомление об ошибке загрузки в S3

        Args:
            filename: Имя файла
            error_message: Текст ошибки
        """
        text = (
            f"⚠️ <b>Ошибка загрузки в S3</b>\n\n"
            f"📝 Файл: <code>{filename}</code>\n"
            f"❌ Ошибка: {error_message}\n"
            f"\n💡 Файл сохранен локально"
        )

        self.send_message_sync(text)

    def notify_tracker_issue_created(self, issue_key: str, s3_key: str, issue_url: str = None):
        """
        Уведомление о создании задачи в Яндекс Трекере

        Args:
            issue_key: Ключ задачи (например, PROJ-123)
            s3_key: Ключ файла в S3 (полный путь)
            issue_url: URL задачи в Трекере (опционально)
        """
        # Формируем ссылку на задачу (если URL API, преобразуем в веб-ссылку)
        if issue_url:
            # Преобразуем API URL в веб URL
            # https://st-api.yandex-team.ru/v2/issues/MICBUDDY-56 -> https://st.yandex-team.ru/MICBUDDY-56
            web_url = f"https://st.yandex-team.ru/{issue_key}"
            task_link = f"<a href=\"{web_url}\">{issue_key}</a>"
        else:
            task_link = f"<code>{issue_key}</code>"

        text = (
            f"📋 Задача {task_link} создана\n\n"
            f"📝 Файл: <code>{s3_key}</code>"
        )

        self.send_message_sync(text)

    def notify_processing_started(self, files_count: int):
        """
        Уведомление о начале обработки файлов

        Args:
            files_count: Количество файлов для обработки
        """
        text = (
            f"🔄 <b>Начинаю обработку</b>\n\n"
            f"📊 Файлов к обработке: <b>{files_count}</b>\n"
            f"⚙️ Транскрибация с определением говорящих"
        )

        self.send_message_sync(text)

    def notify_file_processing(
        self,
        file_num: int,
        total_files: int,
        filename: str,
        duration_min: float,
        size_mb: float
    ):
        """
        Уведомление об обработке файла

        Args:
            file_num: Номер файла
            total_files: Всего файлов
            filename: Имя файла
            duration_min: Длительность в минутах
            size_mb: Размер в MB
        """
        text = (
            f"🎤 <b>[{file_num}/{total_files}]</b> Обрабатываю...\n\n"
            f"📝 {filename}\n"
            f"⏱ {duration_min:.1f} мин\n"
            f"💾 {size_mb:.1f} MB"
        )

        self.send_message_sync(text)

    def notify_transcription_complete(
        self,
        file_num: int,
        total_files: int,
        filename: str,
        word_count: int,
        char_count: int,
        speaker_stats: dict = None,
        transcription_preview: str = None
    ):
        """
        Уведомление об окончании транскрибации файла

        Args:
            file_num: Номер файла
            total_files: Всего файлов
            filename: Имя файла
            word_count: Количество слов
            char_count: Количество символов
            speaker_stats: Статистика по говорящим (опционально)
            transcription_preview: Первые 500 символов транскрипции (опционально)
        """
        text = (
            f"✅ <b>[{file_num}/{total_files}]</b> Готово!\n\n"
            f"📝 {filename}\n"
            f"📊 Слов: <b>{word_count}</b>\n"
            f"📄 Символов: <b>{char_count}</b>"
        )

        # Добавляем статистику по говорящим если есть
        if speaker_stats:
            text += f"\n\n👥 Говорящих: <b>{len(speaker_stats)}</b>"
            for speaker, stats in speaker_stats.items():
                text += (
                    f"\n  • Собеседник {speaker}: "
                    f"{stats['utterances']} реплик, "
                    f"{stats['total_time']:.1f}с"
                )

        # Добавляем превью транскрипции (первые 500 символов)
        if transcription_preview:
            preview = transcription_preview[:500]
            # Если текст обрезан, добавляем многоточие
            if len(transcription_preview) > 500:
                preview += "..."
            text += f"\n\n📄 <b>Текст:</b>\n<i>{preview}</i>"

        self.send_message_sync(text)

    def notify_all_complete(
        self,
        files_count: int,
        total_duration_min: float = None,
        device_name: str = None
    ):
        """
        Уведомление об окончании всей обработки

        Args:
            files_count: Количество обработанных файлов
            total_duration_min: Общая длительность в минутах
            device_name: Имя устройства
        """
        text = (
            f"🎉 <b>ВСЁ ГОТОВО!</b>\n\n"
            f"✅ Обработано файлов: <b>{files_count}</b>\n"
        )

        if total_duration_min:
            text += f"⏱ Общая длительность: <b>{total_duration_min:.1f} мин</b>\n"

        if device_name:
            text += f"🆔 Устройство: <code>{device_name}</code>"

        self.send_message_sync(text)

    def notify_error(self, error_message: str, filename: str = None):
        """
        Уведомление об ошибке

        Args:
            error_message: Текст ошибки
            filename: Имя файла (если применимо)
        """
        text = f"❌ <b>ОШИБКА</b>\n\n"

        if filename:
            text += f"📝 Файл: {filename}\n"

        text += f"⚠️ {error_message}"

        self.send_message_sync(text)

    async def close(self):
        """Закрытие соединения с Telegram (не требуется, т.к. бот создается для каждой отправки)"""
        pass


if __name__ == "__main__":
    # Тестирование модуля
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if bot_token and chat_id:
        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)

        print("\nОтправка тестовых уведомлений...\n")

        notifier.notify_device_connected(
            device_path="/media/usb0",
            device_id="UUID_1a2b3c4d",
            label="AGENT_001"
        )

        notifier.notify_copying_started(files_count=3, total_size_mb=45.5)

        notifier.notify_copying_complete(files_count=3, total_size_mb=45.5)

        notifier.notify_processing_started(files_count=3)

        notifier.notify_file_processing(
            file_num=1,
            total_files=3,
            filename="recording1.mp3",
            duration_min=45.3,
            size_mb=15.2
        )

        notifier.notify_transcription_complete(
            file_num=1,
            total_files=3,
            filename="recording1.mp3",
            word_count=1234,
            char_count=8542
        )

        notifier.notify_all_complete(files_count=3, total_duration_min=120.5)

        print("\n✅ Тестовые уведомления отправлены!")
    else:
        print("❌ Установите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env файле")
