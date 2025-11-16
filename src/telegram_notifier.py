"""
Telegram уведомления о процессе обработки
Отправляет сообщения в Telegram о всех этапах работы
"""

import logging
from typing import Optional
from datetime import datetime
import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode

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
        self.bot = None

        if self.enabled:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("✅ Telegram бот инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Telegram бота: {e}")
                self.enabled = False
        else:
            logger.info("ℹ️  Telegram уведомления отключены")

    async def _send_message(self, text: str, parse_mode: str = ParseMode.HTML):
        """
        Отправка сообщения в Telegram

        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
        """
        if not self.enabled:
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=False
            )
            logger.debug(f"Telegram сообщение отправлено: {text[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram сообщения: {e}")

    def send_message_sync(self, text: str, parse_mode: str = ParseMode.HTML):
        """
        Синхронная отправка сообщения (для использования в обычном коде)

        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга
        """
        if not self.enabled:
            return

        try:
            # Создаем новый event loop если его нет
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Запускаем асинхронную функцию
            loop.run_until_complete(self._send_message(text, parse_mode))
        except Exception as e:
            logger.error(f"Ошибка синхронной отправки сообщения: {e}")

    # ========================================================================
    # Уведомления о различных этапах
    # ========================================================================

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

        text += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        self.send_message_sync(text)

    def notify_copying_started(self, files_count: int, total_size_mb: float):
        """
        Уведомление о начале копирования файлов

        Args:
            files_count: Количество файлов
            total_size_mb: Общий размер в MB
        """
        text = (
            f"📦 <b>Начинаю копирование</b>\n\n"
            f"📁 Файлов: <b>{files_count}</b>\n"
            f"💾 Размер: <b>{total_size_mb:.1f} MB</b>\n"
            f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        )

        self.send_message_sync(text)

    def notify_file_copied(self, file_num: int, total_files: int, filename: str, size_mb: float):
        """
        Уведомление о копировании файла

        Args:
            file_num: Номер файла
            total_files: Всего файлов
            filename: Имя файла
            size_mb: Размер в MB
        """
        text = (
            f"📄 <b>[{file_num}/{total_files}]</b> Копирую...\n\n"
            f"📝 {filename}\n"
            f"💾 {size_mb:.1f} MB"
        )

        self.send_message_sync(text)

    def notify_copying_complete(self, files_count: int, total_size_mb: float):
        """
        Уведомление об окончании копирования

        Args:
            files_count: Количество скопированных файлов
            total_size_mb: Общий размер
        """
        text = (
            f"✅ <b>ВСЕ ФАЙЛЫ СКОПИРОВАНЫ!</b>\n\n"
            f"📁 Скопировано: <b>{files_count}</b> файлов\n"
            f"💾 Размер: <b>{total_size_mb:.1f} MB</b>\n\n"
            f"🔓 <b>Можно отключить диктофон</b>\n"
            f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
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
            f"⚙️ Нарезка на части + транскрибация\n"
            f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
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

    def notify_file_needs_chunking(self, filename: str, chunks_count: int):
        """
        Уведомление о разделении файла на части

        Args:
            filename: Имя файла
            chunks_count: Количество частей
        """
        text = (
            f"✂️ <b>Разделение на части</b>\n\n"
            f"📝 {filename}\n"
            f"🧩 Частей: <b>{chunks_count}</b>"
        )

        self.send_message_sync(text)

    def notify_transcription_complete(
        self,
        file_num: int,
        total_files: int,
        filename: str,
        word_count: int,
        char_count: int
    ):
        """
        Уведомление об окончании транскрибации файла

        Args:
            file_num: Номер файла
            total_files: Всего файлов
            filename: Имя файла
            word_count: Количество слов
            char_count: Количество символов
        """
        text = (
            f"✅ <b>[{file_num}/{total_files}]</b> Готово!\n\n"
            f"📝 {filename}\n"
            f"📊 Слов: <b>{word_count}</b>\n"
            f"📄 Символов: <b>{char_count}</b>"
        )

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
            text += f"🆔 Устройство: <code>{device_name}</code>\n"

        text += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

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

        text += f"⚠️ {error_message}\n"
        text += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        self.send_message_sync(text)

    async def close(self):
        """Закрытие соединения с Telegram"""
        if self.bot:
            await self.bot.close()


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
