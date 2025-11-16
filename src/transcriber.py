"""
Транскрибация аудио через Yandex Eliza API (совместимый с OpenAI Whisper)
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict
from openai import OpenAI, OpenAIError
import json
import httpx

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Транскрибация аудио через Yandex Eliza API (совместимый с OpenAI Whisper)"""

    # Поддерживаемые форматы Whisper API
    SUPPORTED_FORMATS = {'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm'}

    # Максимальный размер файла для Whisper API (25 MB)
    MAX_FILE_SIZE_MB = 25

    def __init__(self, api_key: str = None, language: str = "es", model: str = "whisper-1"):
        """
        Args:
            api_key: Yandex OAuth токен (если None, берется из env SOY_TOKEN)
            language: Язык аудио (ISO-639-1 код, например 'ru' для русского)
            model: Модель Whisper (whisper-1)
        """
        self.api_key = api_key or os.getenv("SOY_TOKEN")
        if not self.api_key:
            raise ValueError("SOY_TOKEN не задан")

        self.language = language
        self.model = model

        # Yandex Eliza API base URL
        self.base_url = "https://api.eliza.yandex.net/raw/openai/v1/"

        # Создаем HTTP клиент с отключенной SSL проверкой (для самоподписанных сертификатов)
        http_client = httpx.Client(verify=False)

        # Инициализируем клиент с Yandex Eliza endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client
        )

        logger.info(f"WhisperTranscriber инициализирован: язык={language}, модель={model}, API=Yandex Eliza")

    def transcribe_file(
        self,
        audio_path: Path,
        prompt: str = None,
        response_format: str = "json",
        temperature: float = 0.0
    ) -> Dict:
        """
        Транскрибация одного аудиофайла

        Args:
            audio_path: Путь к аудиофайлу
            prompt: Опциональный промпт для контекста
            response_format: Формат ответа (json, text, srt, vtt, verbose_json)
            temperature: Температура sampling (0-1)

        Returns:
            Словарь с результатом транскрибации
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Файл не найден: {audio_path}")

        # Проверяем размер файла
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"Файл слишком большой: {file_size_mb:.1f}MB (макс {self.MAX_FILE_SIZE_MB}MB). "
                "Используйте AudioProcessor для разделения на части."
            )

        # Проверяем формат
        file_format = audio_path.suffix.lstrip('.').lower()
        if file_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: {file_format}. Поддерживаются: {self.SUPPORTED_FORMATS}")

        logger.info(f"Начало транскрибации: {audio_path.name} ({file_size_mb:.1f}MB)")

        try:
            start_time = time.time()

            # Открываем файл и отправляем на транскрибацию
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=self.language,
                    prompt=prompt,
                    response_format=response_format,
                    temperature=temperature
                )

            duration = time.time() - start_time

            # Обрабатываем результат в зависимости от формата
            if response_format == "json" or response_format == "verbose_json":
                result = {
                    "text": transcript.text if hasattr(transcript, 'text') else str(transcript),
                    "language": self.language,
                    "duration_seconds": duration,
                    "file": audio_path.name
                }

                # Добавляем дополнительные поля если verbose_json
                if response_format == "verbose_json" and hasattr(transcript, 'segments'):
                    result["segments"] = transcript.segments
                    result["words"] = getattr(transcript, 'words', [])

            else:
                result = {
                    "text": str(transcript),
                    "language": self.language,
                    "duration_seconds": duration,
                    "file": audio_path.name
                }

            logger.info(f"✅ Транскрибация завершена: {audio_path.name} ({duration:.1f}s)")
            logger.debug(f"Текст: {result['text'][:100]}...")

            return result

        except OpenAIError as e:
            logger.error(f"❌ Ошибка Eliza API для {audio_path.name}: {e}")
            raise

        except Exception as e:
            logger.error(f"❌ Ошибка транскрибации {audio_path.name}: {e}")
            raise

    def transcribe_chunks(
        self,
        chunk_paths: List[Path],
        prompt: str = None,
        merge_overlap: bool = True
    ) -> Dict:
        """
        Транскрибация нескольких чанков с объединением результатов

        Args:
            chunk_paths: Список путей к чанкам
            prompt: Опциональный промпт
            merge_overlap: Попытаться объединить текст из overlap областей

        Returns:
            Словарь с объединенной транскрипцией
        """
        logger.info(f"Транскрибация {len(chunk_paths)} чанков...")

        transcripts = []
        total_duration = 0

        for i, chunk_path in enumerate(chunk_paths, 1):
            logger.info(f"Обработка чанка {i}/{len(chunk_paths)}: {chunk_path.name}")

            try:
                result = self.transcribe_file(chunk_path, prompt=prompt)
                transcripts.append(result)
                total_duration += result['duration_seconds']

            except Exception as e:
                logger.error(f"Ошибка транскрибации чанка {chunk_path.name}: {e}")
                # Продолжаем с другими чанками
                transcripts.append({
                    "text": f"[ОШИБКА ТРАНСКРИБАЦИИ: {chunk_path.name}]",
                    "error": str(e)
                })

        # Объединяем все тексты
        full_text = " ".join([t.get("text", "") for t in transcripts])

        result = {
            "text": full_text,
            "chunks": transcripts,
            "total_chunks": len(chunk_paths),
            "language": self.language,
            "total_duration_seconds": total_duration
        }

        logger.info(f"✅ Все чанки обработаны: {len(chunk_paths)} шт за {total_duration:.1f}s")

        return result

    def transcribe_file_with_splitting(
        self,
        audio_path: Path,
        audio_processor=None,
        save_chunks: bool = False
    ) -> Dict:
        """
        Транскрибация большого файла с автоматическим разделением

        Args:
            audio_path: Путь к аудиофайлу
            audio_processor: Экземпляр AudioProcessor (создается автоматически если None)
            save_chunks: Сохранять ли чанки после обработки

        Returns:
            Словарь с транскрипцией
        """
        # Проверяем размер файла
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)

        if file_size_mb <= self.MAX_FILE_SIZE_MB:
            # Файл достаточно маленький, транскрибируем напрямую
            logger.info("Файл достаточно маленький, транскрибация без разделения")
            return self.transcribe_file(audio_path)

        # Файл большой, нужно разделить
        logger.info(f"Файл большой ({file_size_mb:.1f}MB), разделяем на части...")

        if audio_processor is None:
            from src.audio_processor import AudioProcessor
            audio_processor = AudioProcessor()

        # Разделяем на чанки
        chunk_paths = audio_processor.process_file(audio_path)

        try:
            # Транскрибируем все чанки
            result = self.transcribe_chunks(chunk_paths)

            return result

        finally:
            # Удаляем временные чанки если нужно
            if not save_chunks:
                logger.info("Удаление временных чанков...")
                for chunk_path in chunk_paths:
                    try:
                        chunk_path.unlink()
                    except Exception as e:
                        logger.warning(f"Не удалось удалить {chunk_path}: {e}")

                # Удаляем директорию чанков если пустая
                try:
                    chunks_dir = chunk_paths[0].parent
                    if chunks_dir.exists() and not any(chunks_dir.iterdir()):
                        chunks_dir.rmdir()
                except Exception:
                    pass

    def save_transcript(self, transcript: Dict, output_path: Path):
        """
        Сохранение транскрипции в файл

        Args:
            transcript: Словарь с транскрипцией
            output_path: Путь для сохранения (JSON)
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, indent=2, ensure_ascii=False)

            logger.info(f"Транскрипция сохранена: {output_path}")

        except Exception as e:
            logger.error(f"Ошибка сохранения транскрипции {output_path}: {e}")
            raise


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Пример использования
    try:
        transcriber = WhisperTranscriber(language="es")  # Испанский язык

        test_file = Path("data/audio/test.mp3")
        if test_file.exists():
            print(f"\nТранскрибация файла: {test_file.name}")

            # Транскрибируем
            result = transcriber.transcribe_file_with_splitting(test_file)

            print(f"\nРезультат:")
            print(f"  Текст: {result['text'][:200]}...")
            print(f"  Время: {result.get('total_duration_seconds', 0):.1f}s")

            # Сохраняем
            output_path = Path("data/transcriptions/test_transcript.json")
            transcriber.save_transcript(result, output_path)
        else:
            print(f"Тестовый файл {test_file} не найден")

    except Exception as e:
        print(f"Ошибка: {e}")
