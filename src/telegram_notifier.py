"""
Telegram notifications for the processing pipeline
Sends messages to Telegram about all processing stages
"""

import logging
from typing import Optional
import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send Telegram notifications about the processing pipeline"""

    def __init__(self, bot_token: str = None, chat_id: str = None, enabled: bool = True):
        """
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID for sending messages
            enabled: Whether notifications are enabled
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bot_token and chat_id

        if self.enabled:
            logger.info("Telegram bot initialized")
        else:
            logger.info("Telegram notifications disabled")

    async def _send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        reply_markup: InlineKeyboardMarkup = None
    ):
        """
        Send message to Telegram

        Args:
            text: Message text
            parse_mode: Parse mode (HTML, Markdown)
            reply_markup: Inline keyboard with buttons
        """
        if not self.enabled:
            return

        bot = None
        try:
            bot = Bot(token=self.bot_token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=False
            )
            logger.debug(f"Telegram message sent: {text[:50]}...")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
        finally:
            if bot:
                await bot.session.close()

    def send_message_sync(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        reply_markup: InlineKeyboardMarkup = None
    ):
        """
        Synchronous message sending (for use in regular code)

        Args:
            text: Message text
            parse_mode: Parse mode
            reply_markup: Inline keyboard with buttons
        """
        if not self.enabled:
            return

        try:
            asyncio.run(self._send_message(text, parse_mode, reply_markup))
        except Exception as e:
            logger.error(f"Error sending sync message: {e}")

    # ========================================================================
    # Notifications for various stages
    # ========================================================================

    def notify_process_started(self, hostname: str = None, version: str = None):
        """Notification about monitoring process start"""
        import socket
        hostname = hostname or socket.gethostname()
        version_str = f" v{version}" if version else ""
        text = f"🚀 <b>Monitoring started{version_str}</b>\n\n💻 Computer: <code>{hostname}</code>\nWaiting for USB recorders..."
        self.send_message_sync(text)

    def notify_device_connected(self, device_path: str, device_id: str, label: str = None):
        """
        Notification about device connection

        Args:
            device_path: Path to device
            device_id: Unique device ID
            label: Device label
        """
        import socket
        hostname = socket.gethostname()

        text = (
            f"🔌 <b>Device connected</b>\n\n"
            f"💻 Computer: <code>{hostname}</code>\n"
            f"📍 Path: <code>{device_path}</code>"
        )

        self.send_message_sync(text)

    def notify_device_disconnected(self, device_path: str):
        """
        Notification about device disconnection

        Args:
            device_path: Path to device
        """
        import socket
        hostname = socket.gethostname()
        text = (
            f"⏏️ <b>Device disconnected</b>\n\n"
            f"💻 Computer: <code>{hostname}</code>\n"
            f"📍 Path: <code>{device_path}</code>"
        )
        self.send_message_sync(text)

    def notify_copying_started(self, files_count: int, total_size_mb: float, device_path: str = None):
        """
        Notification about copying start

        Args:
            files_count: Number of files
            total_size_mb: Total size in MB
            device_path: Path to device
        """
        text = f"📦 <b>Starting copy</b>\n\n"

        if device_path:
            text += f"📍 Path: <code>{device_path}</code>\n"

        text += f"📁 Files: <b>{files_count}</b>\n"
        text += f"💾 Size: <b>{total_size_mb:.1f} MB</b>"

        self.send_message_sync(text)

    def notify_file_copied(self, file_num: int, total_files: int, filename: str, size_mb: float, device_path: str = None):
        """
        Notification about file copying

        Args:
            file_num: File number
            total_files: Total files
            filename: File name
            size_mb: Size in MB
            device_path: Full path to file on device (optional)
        """
        text = f"📄 <b>[{file_num}/{total_files}]</b> Copying...\n\n"

        if device_path:
            text += f"📍 <code>{device_path}</code>\n"
        else:
            text += f"📝 {filename}\n"

        text += f"💾 {size_mb:.1f} MB"

        self.send_message_sync(text)

    def notify_copying_complete(self, files_count: int, device_name: str = None):
        """
        Notification about copying completion

        Args:
            files_count: Number of copied files
            device_name: Device name (optional)
        """
        text = f"✅ <b>ALL FILES COPIED!</b>\n\n"
        text += f"📁 Copied: <b>{files_count}</b> files\n"

        if device_name:
            text += f"🆔 Device: <code>{device_name}</code>\n"

        text += f"\n🔓 <b>You can disconnect the recorder</b>"

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
        Notification about S3 upload

        Args:
            filename: File name
            s3_key: S3 key (path in bucket)
            size_mb: File size in MB
            presigned_url: Temporary download link (optional)
            expiry_days: Link expiry in days (default 7)
        """
        text = (
            f"☁️ <b>File uploaded to S3</b>\n\n"
            f"📍 <code>{s3_key}</code>\n"
            f"💾 Size: <b>{size_mb:.1f} MB</b>"
        )

        if presigned_url:
            text += f"\n\n🔗 Link valid for <b>{expiry_days} days</b>"

        reply_markup = None
        if presigned_url:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬇️ Download from S3", url=presigned_url)]
                ]
            )
            reply_markup = keyboard

        self.send_message_sync(text, reply_markup=reply_markup)

    def notify_s3_already_exists(self, s3_key: str, size_mb: float):
        """
        Notification that file already exists in S3

        Args:
            s3_key: S3 key (full path)
            size_mb: File size in MB
        """
        text = (
            f"⏩ <b>File already exists in S3</b>\n\n"
            f"📍 <code>{s3_key}</code>\n"
            f"💾 Size: <b>{size_mb:.1f} MB</b>"
        )

        self.send_message_sync(text)

    def notify_copy_error(self, filename: str, error_message: str):
        """
        Notification about local copy error

        Args:
            filename: File name
            error_message: Error text
        """
        import socket
        hostname = socket.gethostname()
        text = (
            f"❌ <b>Copy error</b>\n\n"
            f"💻 Computer: <code>{hostname}</code>\n"
            f"📝 File: <code>{filename}</code>\n"
            f"⚠️ Error: {error_message}"
        )
        self.send_message_sync(text)

    def notify_s3_upload_error(self, filename: str, error_message: str):
        """
        Notification about S3 upload error

        Args:
            filename: File name
            error_message: Error text
        """
        text = (
            f"⚠️ <b>S3 upload error</b>\n\n"
            f"📝 File: <code>{filename}</code>\n"
            f"❌ Error: {error_message}\n"
            f"\n💡 File saved locally"
        )

        self.send_message_sync(text)

    def notify_tracker_issue_created(self, issue_key: str, s3_key: str, issue_url: str = None):
        """
        Notification about Yandex Tracker issue creation

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            s3_key: S3 key (full path)
            issue_url: Issue URL in Tracker (optional)
        """
        if issue_url:
            web_url = f"https://st.yandex-team.ru/{issue_key}"
            task_link = f"<a href=\"{web_url}\">{issue_key}</a>"
        else:
            task_link = f"<code>{issue_key}</code>"

        text = (
            f"📋 Issue {task_link} created\n\n"
            f"📝 File: <code>{s3_key}</code>"
        )

        self.send_message_sync(text)

    def notify_tracker_error(self, s3_key: str, error_message: str):
        """
        Notification about Tracker issue creation error

        Args:
            s3_key: S3 key (full path)
            error_message: Error text
        """
        text = (
            f"❌ <b>Tracker error</b>\n\n"
            f"📝 File: <code>{s3_key}</code>\n"
            f"⚠️ Error: {error_message}"
        )
        self.send_message_sync(text)

    def notify_processing_started(self, files_count: int):
        """
        Notification about processing start

        Args:
            files_count: Number of files to process
        """
        text = (
            f"🔄 <b>Starting processing</b>\n\n"
            f"📊 Files to process: <b>{files_count}</b>\n"
            f"⚙️ Transcription with speaker diarization"
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
        Notification about file processing

        Args:
            file_num: File number
            total_files: Total files
            filename: File name
            duration_min: Duration in minutes
            size_mb: Size in MB
        """
        text = (
            f"🎤 <b>[{file_num}/{total_files}]</b> Processing...\n\n"
            f"📝 {filename}\n"
            f"⏱ {duration_min:.1f} min\n"
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
        Notification about transcription completion

        Args:
            file_num: File number
            total_files: Total files
            filename: File name
            word_count: Word count
            char_count: Character count
            speaker_stats: Speaker statistics (optional)
            transcription_preview: First 500 characters of transcription (optional)
        """
        text = (
            f"✅ <b>[{file_num}/{total_files}]</b> Done!\n\n"
            f"📝 {filename}\n"
            f"📊 Words: <b>{word_count}</b>\n"
            f"📄 Characters: <b>{char_count}</b>"
        )

        if speaker_stats:
            text += f"\n\n👥 Speakers: <b>{len(speaker_stats)}</b>"
            for speaker, stats in speaker_stats.items():
                text += (
                    f"\n  • Speaker {speaker}: "
                    f"{stats['utterances']} utterances, "
                    f"{stats['total_time']:.1f}s"
                )

        if transcription_preview:
            preview = transcription_preview[:500]
            if len(transcription_preview) > 500:
                preview += "..."
            text += f"\n\n📄 <b>Text:</b>\n<i>{preview}</i>"

        self.send_message_sync(text)

    def notify_all_complete(
        self,
        files_count: int,
        total_duration_min: float = None,
        device_name: str = None
    ):
        """
        Notification about all processing completion

        Args:
            files_count: Number of processed files
            total_duration_min: Total duration in minutes
            device_name: Device name
        """
        text = (
            f"🎉 <b>ALL DONE!</b>\n\n"
            f"✅ Files processed: <b>{files_count}</b>\n"
        )

        if total_duration_min:
            text += f"⏱ Total duration: <b>{total_duration_min:.1f} min</b>\n"

        if device_name:
            text += f"🆔 Device: <code>{device_name}</code>"

        self.send_message_sync(text)

    def notify_error(self, error_message: str, filename: str = None):
        """
        Error notification

        Args:
            error_message: Error text
            filename: File name (if applicable)
        """
        text = f"❌ <b>ERROR</b>\n\n"

        if filename:
            text += f"📝 File: {filename}\n"

        text += f"⚠️ {error_message}"

        self.send_message_sync(text)

    async def close(self):
        """Close Telegram connection (not required as bot is created for each send)"""
        pass


if __name__ == "__main__":
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

        print("\nSending test notifications...\n")

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

        print("\nTest notifications sent!")
    else:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
