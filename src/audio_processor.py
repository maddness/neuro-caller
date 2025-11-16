"""
Обработка аудио: разделение на части с overlap для транскрибации
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple
from pydub import AudioSegment
from pydub.utils import make_chunks

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Обработка аудиофайлов: разделение на части с overlap"""

    # Ограничение OpenAI Whisper API: 25MB
    MAX_FILE_SIZE_MB = 24  # Оставляем запас
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    def __init__(self, chunk_length_ms: int = 600000, overlap_ms: int = 5000):
        """
        Args:
            chunk_length_ms: Длина каждого сегмента в миллисекундах (по умолчанию 10 минут)
            overlap_ms: Overlap между сегментами в миллисекундах (по умолчанию 5 секунд)
        """
        self.chunk_length_ms = chunk_length_ms
        self.overlap_ms = overlap_ms

        logger.info(f"AudioProcessor инициализирован: chunk={chunk_length_ms}ms, overlap={overlap_ms}ms")

    def convert_with_ffmpeg(self, input_path: Path, output_path: Path = None) -> Path:
        """
        Конвертация аудио через ffmpeg в PCM WAV формат

        Args:
            input_path: Путь к входному файлу
            output_path: Путь к выходному файлу (опционально)

        Returns:
            Путь к сконвертированному файлу
        """
        import subprocess
        import tempfile

        if output_path is None:
            # Создаем временный файл
            temp_dir = Path(tempfile.gettempdir())
            output_path = temp_dir / f"{input_path.stem}_converted.wav"

        try:
            logger.info(f"Конвертирую {input_path.name} через ffmpeg...")

            # Конвертируем в PCM WAV
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-i', str(input_path),
                    '-ar', '48000',  # Sample rate 48kHz
                    '-ac', '1',  # Mono
                    '-c:a', 'pcm_s16le',  # PCM 16-bit
                    '-y',  # Overwrite output file
                    str(output_path)
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5 минут timeout для длинных файлов
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg ошибка: {result.stderr}")
                raise RuntimeError(f"ffmpeg конвертация не удалась: {result.stderr}")

            logger.info(f"✓ Конвертация завершена: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"Ошибка конвертации через ffmpeg: {e}")
            raise

    def load_audio(self, file_path: Path) -> AudioSegment:
        """
        Загрузка аудиофайла через ffmpeg конвертацию

        Args:
            file_path: Путь к аудиофайлу

        Returns:
            AudioSegment объект
        """
        try:
            logger.info(f"Загрузка аудио: {file_path.name}")

            # Конвертируем через ffmpeg в стандартный PCM WAV
            converted_path = self.convert_with_ffmpeg(file_path)

            # Загружаем сконвертированный файл
            audio = AudioSegment.from_file(str(converted_path), format='wav')

            duration_sec = len(audio) / 1000
            logger.info(f"✓ Аудио загружено: длительность {duration_sec:.1f}с")

            return audio

        except Exception as e:
            logger.error(f"Ошибка загрузки аудио {file_path}: {e}")
            raise

    def split_audio_with_overlap(self, audio: AudioSegment) -> List[Tuple[AudioSegment, int, int]]:
        """
        Разделение аудио на части с overlap

        Args:
            audio: AudioSegment объект

        Returns:
            Список кортежей (chunk, start_ms, end_ms)
        """
        chunks = []
        total_length = len(audio)
        current_pos = 0

        chunk_num = 0

        while current_pos < total_length:
            # Вычисляем начало и конец текущего чанка
            start = current_pos
            end = min(current_pos + self.chunk_length_ms, total_length)

            # Извлекаем чанк
            chunk = audio[start:end]

            chunks.append((chunk, start, end))
            chunk_num += 1

            logger.debug(f"Chunk {chunk_num}: {start}ms - {end}ms ({len(chunk)/1000:.1f}s)")

            # Переходим к следующей позиции с учетом overlap
            current_pos = end - self.overlap_ms

            # Если осталось меньше overlap, заканчиваем
            if end >= total_length:
                break

        logger.info(f"Аудио разделено на {len(chunks)} частей с overlap {self.overlap_ms}ms")
        return chunks

    def save_chunk(self, chunk: AudioSegment, output_path: Path, format: str = "mp3") -> Path:
        """
        Сохранение чанка в файл

        Args:
            chunk: AudioSegment чанк
            output_path: Путь для сохранения
            format: Формат выходного файла (mp3, wav и т.д.)

        Returns:
            Путь к сохраненному файлу
        """
        try:
            # Создаем директорию если не существует
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Сохраняем
            chunk.export(str(output_path), format=format)

            file_size = output_path.stat().st_size
            logger.debug(f"Chunk сохранен: {output_path.name} ({file_size/1024:.1f}KB)")

            return output_path

        except Exception as e:
            logger.error(f"Ошибка сохранения chunk {output_path}: {e}")
            raise

    def process_file(self, input_path: Path, output_dir: Path = None) -> List[Path]:
        """
        Полная обработка файла: загрузка, разделение и сохранение чанков

        Args:
            input_path: Путь к входному аудиофайлу
            output_dir: Директория для сохранения чанков (по умолчанию рядом с исходным)

        Returns:
            Список путей к созданным чанкам
        """
        logger.info(f"Начало обработки: {input_path.name}")

        # Загружаем аудио
        audio = self.load_audio(input_path)

        # Разделяем на части
        chunks = self.split_audio_with_overlap(audio)

        # Определяем директорию для выходных файлов
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_chunks"
        else:
            output_dir = Path(output_dir) / input_path.stem

        output_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем чанки
        chunk_paths = []
        for i, (chunk, start_ms, end_ms) in enumerate(chunks, 1):
            # Генерируем имя файла
            chunk_filename = f"{input_path.stem}_chunk_{i:03d}.mp3"
            chunk_path = output_dir / chunk_filename

            # Сохраняем
            saved_path = self.save_chunk(chunk, chunk_path, format="mp3")
            chunk_paths.append(saved_path)

        logger.info(f"✅ Обработка завершена: создано {len(chunk_paths)} чанков в {output_dir}")

        return chunk_paths

    def estimate_chunks_count(self, file_path: Path) -> int:
        """
        Оценка количества чанков без полной загрузки файла

        Args:
            file_path: Путь к аудиофайлу

        Returns:
            Примерное количество чанков
        """
        try:
            audio = self.load_audio(file_path)
            total_length = len(audio)

            # Вычисляем количество чанков
            if total_length <= self.chunk_length_ms:
                return 1

            effective_chunk_length = self.chunk_length_ms - self.overlap_ms
            chunks_count = (total_length - self.chunk_length_ms) // effective_chunk_length + 1

            return chunks_count

        except Exception as e:
            logger.error(f"Ошибка оценки количества чанков для {file_path}: {e}")
            return 0

    @staticmethod
    def get_audio_info(file_path: Path) -> dict:
        """
        Получение информации об аудиофайле через ffprobe

        Args:
            file_path: Путь к аудиофайлу

        Returns:
            Словарь с информацией
        """
        import subprocess

        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries',
                 'format=duration,size', '-of', 'default=noprint_wrappers=1',
                 str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                duration = 0
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('duration='):
                        duration = float(line.split('=')[1])

                info = {
                    "duration_seconds": duration,
                    "duration_minutes": duration / 60,
                    "channels": 1,  # Предполагаем mono
                    "sample_width": 2,
                    "frame_rate": 48000,
                    "file_size_mb": file_path.stat().st_size / (1024 * 1024),
                    "format": file_path.suffix.lstrip('.').lower()
                }
                logger.info(f"✓ Информация получена: {duration:.1f} сек")
                return info
            else:
                logger.error(f"ffprobe ошибка: {result.stderr}")
                return {}

        except Exception as e:
            logger.error(f"Ошибка получения информации: {e}")
            return {}


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Пример использования
    processor = AudioProcessor(chunk_length_ms=600000, overlap_ms=5000)  # 10 минут с 5 сек overlap

    test_file = Path("data/audio/test.mp3")
    if test_file.exists():
        # Получаем информацию
        info = processor.get_audio_info(test_file)
        print(f"\nИнформация о файле:")
        print(f"  Длительность: {info['duration_minutes']:.1f} минут")
        print(f"  Размер: {info['file_size_mb']:.1f} MB")

        # Обрабатываем
        chunks = processor.process_file(test_file)
        print(f"\nСоздано чанков: {len(chunks)}")
    else:
        print(f"Тестовый файл {test_file} не найден")
