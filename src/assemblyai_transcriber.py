"""
Транскрибация аудио с разделением по говорящим через AssemblyAI
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import assemblyai as aai

logger = logging.getLogger(__name__)


class AssemblyAITranscriber:
    """Транскрибация аудио с speaker diarization через AssemblyAI"""

    def __init__(self, api_key: str = None, language: str = "ru"):
        """
        Args:
            api_key: AssemblyAI API ключ (если None, берется из env)
            language: Язык аудио (ru, en, es и т.д.)
        """
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY не задан")

        self.language = language

        # Настройка AssemblyAI
        aai.settings.api_key = self.api_key

        logger.info(f"AssemblyAITranscriber инициализирован: язык={language}")

    def transcribe_with_speakers(
        self,
        audio_path: Path,
        num_speakers: int = 2
    ) -> Dict:
        """
        Транскрибация аудио с разделением по говорящим

        Args:
            audio_path: Путь к аудиофайлу
            num_speakers: Ожидаемое количество говорящих (2 по умолчанию)

        Returns:
            Словарь с транскрипцией и сегментами говорящих
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Файл не найден: {audio_path}")

        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        logger.info(f"Начало транскрибации: {audio_path.name} ({file_size_mb:.1f}MB)")

        try:
            start_time = time.time()

            # Конфигурация транскрипции
            config = aai.TranscriptionConfig(
                speaker_labels=True,  # Включить diarization
                language_code=self.language
                # НЕ указываем speakers_expected - пусть AssemblyAI определит автоматически
                # Это дает лучшие результаты, чем жесткое указание количества
            )

            # Создаем транскрайбер
            transcriber = aai.Transcriber()

            # Отправляем на транскрипцию
            logger.info("Загрузка файла и запрос транскрипции...")
            transcript = transcriber.transcribe(str(audio_path), config)

            # Ждем завершения
            logger.info(f"Статус: {transcript.status}")

            if transcript.status == aai.TranscriptStatus.error:
                raise RuntimeError(f"Ошибка транскрибации: {transcript.error}")

            duration = time.time() - start_time

            # Формируем результат
            result = self._format_result(transcript, duration, audio_path.name)

            logger.info(f"✅ Транскрибация завершена: {duration:.1f}s")
            logger.info(f"Найдено {result['total_speakers']} говорящих, {result['total_utterances']} реплик")

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка AssemblyAI для {audio_path.name}: {e}")
            raise

    def _format_result(
        self,
        transcript: aai.Transcript,
        duration: float,
        filename: str
    ) -> Dict:
        """
        Форматирование результата транскрипции

        Args:
            transcript: Объект транскрипции от AssemblyAI
            duration: Время обработки
            filename: Имя файла

        Returns:
            Форматированный результат
        """
        # Полный текст
        full_text = transcript.text

        # Сегменты с говорящими
        segments = []
        speaker_stats = {}

        if transcript.utterances:
            for utterance in transcript.utterances:
                speaker = utterance.speaker
                segment = {
                    "speaker": speaker,
                    "start": utterance.start / 1000,  # Конвертируем ms в секунды
                    "end": utterance.end / 1000,
                    "text": utterance.text,
                    "confidence": utterance.confidence
                }
                segments.append(segment)

                # Собираем статистику по говорящим
                if speaker not in speaker_stats:
                    speaker_stats[speaker] = {
                        "utterances": 0,
                        "total_time": 0,
                        "words": 0
                    }

                speaker_stats[speaker]["utterances"] += 1
                speaker_stats[speaker]["total_time"] += (utterance.end - utterance.start) / 1000
                speaker_stats[speaker]["words"] += len(utterance.text.split())

        # Финальный результат
        result = {
            "text": full_text,
            "segments": segments,
            "speaker_stats": speaker_stats,
            "total_speakers": len(speaker_stats),
            "total_utterances": len(segments),
            "language": self.language,
            "duration_seconds": duration,
            "file": filename,
            "confidence": transcript.confidence if hasattr(transcript, 'confidence') else None
        }

        return result

    @staticmethod
    def parse_filename_timestamp(filename: str) -> Optional[datetime]:
        """
        Извлечение времени начала записи из имени файла

        Args:
            filename: Имя файла вида R20251120-120021.WAV

        Returns:
            datetime объект или None если не удалось распарсить
        """
        import re

        # Паттерн: R[YYYYMMDD]-[HHMMSS]
        pattern = r'R(\d{8})-(\d{6})'
        match = re.match(pattern, filename)

        if match:
            date_str = match.group(1)  # 20251120
            time_str = match.group(2)  # 120021

            try:
                # Парсим дату и время
                dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                return dt
            except ValueError:
                return None

        return None

    def format_transcript_text(self, result: Dict, filename: str = None) -> str:
        """
        Форматирование транскрипции в читаемый текст с абсолютными таймстемпами

        Args:
            result: Результат от transcribe_with_speakers()
            filename: Имя файла для извлечения начального времени

        Returns:
            Отформатированный текст с разделением по говорящим и таймстемпами
        """

        output = []

        # Извлекаем начальное время из имени файла
        start_time = None
        if filename:
            start_time = self.parse_filename_timestamp(filename)

        current_speaker = None
        current_text = []
        current_timestamp = None

        for segment in result["segments"]:
            speaker = segment["speaker"]
            start_seconds = segment.get("start", 0)  # Время в секундах

            if speaker != current_speaker:
                # Сохраняем предыдущего говорящего
                if current_text and current_timestamp:
                    speaker_label = f"Собеседник {current_speaker}"
                    output.append(f"{current_timestamp} {speaker_label}: {' '.join(current_text)}")
                    output.append("")  # Пустая строка между репликами

                current_speaker = speaker
                current_text = [segment["text"]]

                # Вычисляем абсолютный таймстемп
                if start_time:
                    absolute_time = start_time + timedelta(seconds=start_seconds)
                    current_timestamp = absolute_time.strftime("[%H:%M:%S]")
                else:
                    # Если не удалось извлечь время из файла, используем относительное
                    seconds = int(start_seconds)
                    minutes = seconds // 60
                    hours = minutes // 60
                    current_timestamp = f"[{hours:02d}:{minutes%60:02d}:{seconds%60:02d}]"
            else:
                current_text.append(segment["text"])

        # Последний говорящий
        if current_text and current_timestamp:
            speaker_label = f"Собеседник {current_speaker}"
            output.append(f"{current_timestamp} {speaker_label}: {' '.join(current_text)}")

        return '\n'.join(output)


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Пример использования
    try:
        transcriber = AssemblyAITranscriber(language="ru")

        test_file = Path("data/audio/test.mp3")
        if test_file.exists():
            print(f"\nТранскрибация файла: {test_file.name}")

            # Транскрибируем с diarization
            result = transcriber.transcribe_with_speakers(test_file, num_speakers=2)

            print(f"\nРезультат:")
            print(f"  Говорящих: {result['total_speakers']}")
            print(f"  Реплик: {result['total_utterances']}")
            print(f"  Время: {result['duration_seconds']:.1f}s")

            print(f"\nСтатистика по говорящим:")
            for speaker, stats in result['speaker_stats'].items():
                print(f"  {speaker}: {stats['utterances']} реплик, {stats['total_time']:.1f}s")

            print(f"\nТекст:")
            formatted_text = transcriber.format_transcript_text(result, filename=test_file.name)
            print(formatted_text[:500] + "...")
        else:
            print(f"Тестовый файл {test_file} не найден")

    except Exception as e:
        print(f"Ошибка: {e}")
