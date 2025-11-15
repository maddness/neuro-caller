"""
База данных для хранения транскрипций разговоров
"""

import sqlite3
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TranscriptionDatabase:
    """SQLite база данных для хранения транскрипций"""

    def __init__(self, db_path: str = "data/transcriptions.db"):
        """
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = Path(db_path)

        # Создаем директорию если не существует
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Инициализируем БД
        self._init_database()

        logger.info(f"База данных инициализирована: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка БД: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Инициализация структуры базы данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Таблица транскрипций
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE NOT NULL,
                    original_filename TEXT NOT NULL,
                    device_name TEXT,
                    audio_file_path TEXT NOT NULL,
                    transcription_text TEXT NOT NULL,
                    language TEXT DEFAULT 'es',
                    duration_seconds REAL,
                    word_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)

            # Таблица чанков (если файл был разделен)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcription_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcription_id INTEGER NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    start_ms INTEGER,
                    end_ms INTEGER,
                    FOREIGN KEY (transcription_id) REFERENCES transcriptions (id)
                )
            """)

            # Индексы для быстрого поиска
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_hash
                ON transcriptions(file_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_name
                ON transcriptions(device_name)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON transcriptions(created_at)
            """)

            # Таблица для полнотекстового поиска (FTS5)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS transcriptions_fts
                USING fts5(
                    transcription_id UNINDEXED,
                    transcription_text,
                    tokenize = 'unicode61'
                )
            """)

            logger.info("Структура БД создана")

    def add_transcription(
        self,
        file_hash: str,
        original_filename: str,
        audio_file_path: str,
        transcription_text: str,
        device_name: str = None,
        language: str = "es",
        duration_seconds: float = None,
        metadata: Dict = None,
        chunks: List[Dict] = None
    ) -> int:
        """
        Добавление новой транскрипции в БД

        Args:
            file_hash: MD5 хеш аудиофайла
            original_filename: Оригинальное имя файла
            audio_file_path: Путь к аудиофайлу
            transcription_text: Текст транскрипции
            device_name: Имя устройства
            language: Язык аудио
            duration_seconds: Длительность аудио
            metadata: Дополнительные метаданные
            chunks: Список чанков если файл был разделен

        Returns:
            ID созданной записи
        """
        try:
            word_count = len(transcription_text.split())
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Добавляем транскрипцию
                cursor.execute("""
                    INSERT INTO transcriptions (
                        file_hash, original_filename, device_name, audio_file_path,
                        transcription_text, language, duration_seconds, word_count, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_hash, original_filename, device_name, audio_file_path,
                    transcription_text, language, duration_seconds, word_count, metadata_json
                ))

                transcription_id = cursor.lastrowid

                # Добавляем в FTS таблицу для полнотекстового поиска
                cursor.execute("""
                    INSERT INTO transcriptions_fts (transcription_id, transcription_text)
                    VALUES (?, ?)
                """, (transcription_id, transcription_text))

                # Добавляем чанки если есть
                if chunks:
                    for chunk in chunks:
                        cursor.execute("""
                            INSERT INTO transcription_chunks (
                                transcription_id, chunk_number, chunk_text, start_ms, end_ms
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            transcription_id,
                            chunk.get('chunk_number'),
                            chunk.get('text', ''),
                            chunk.get('start_ms'),
                            chunk.get('end_ms')
                        ))

                logger.info(f"✅ Транскрипция добавлена в БД: ID={transcription_id}, файл={original_filename}")

                return transcription_id

        except sqlite3.IntegrityError as e:
            logger.warning(f"Транскрипция уже существует: {file_hash}")
            raise

        except Exception as e:
            logger.error(f"Ошибка добавления транскрипции: {e}")
            raise

    def get_transcription(self, transcription_id: int) -> Optional[Dict]:
        """
        Получение транскрипции по ID

        Args:
            transcription_id: ID транскрипции

        Returns:
            Словарь с данными или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM transcriptions WHERE id = ?
            """, (transcription_id,))

            row = cursor.fetchone()

            if row:
                return dict(row)

            return None

    def search_transcriptions(
        self,
        query: str = None,
        device_name: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Поиск транскрипций

        Args:
            query: Текстовый запрос для полнотекстового поиска
            device_name: Фильтр по устройству
            date_from: Дата начала (ISO формат)
            date_to: Дата окончания (ISO формат)
            limit: Максимальное количество результатов

        Returns:
            Список найденных транскрипций
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Полнотекстовый поиск
            if query:
                sql = """
                    SELECT t.* FROM transcriptions t
                    JOIN transcriptions_fts fts ON t.id = fts.transcription_id
                    WHERE fts.transcription_text MATCH ?
                """
                params = [query]

                if device_name:
                    sql += " AND t.device_name = ?"
                    params.append(device_name)

                if date_from:
                    sql += " AND t.created_at >= ?"
                    params.append(date_from)

                if date_to:
                    sql += " AND t.created_at <= ?"
                    params.append(date_to)

                sql += " ORDER BY t.created_at DESC LIMIT ?"
                params.append(limit)

            # Обычная выборка
            else:
                sql = "SELECT * FROM transcriptions WHERE 1=1"
                params = []

                if device_name:
                    sql += " AND device_name = ?"
                    params.append(device_name)

                if date_from:
                    sql += " AND created_at >= ?"
                    params.append(date_from)

                if date_to:
                    sql += " AND created_at <= ?"
                    params.append(date_to)

                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_statistics(self) -> Dict:
        """
        Получение статистики по транскрипциям

        Returns:
            Словарь со статистикой
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Общая статистика
            cursor.execute("""
                SELECT
                    COUNT(*) as total_transcriptions,
                    SUM(duration_seconds) as total_duration_seconds,
                    SUM(word_count) as total_words,
                    COUNT(DISTINCT device_name) as unique_devices,
                    MIN(created_at) as first_transcription,
                    MAX(created_at) as last_transcription
                FROM transcriptions
            """)

            stats = dict(cursor.fetchone())

            # Статистика по устройствам
            cursor.execute("""
                SELECT
                    device_name,
                    COUNT(*) as count,
                    SUM(duration_seconds) as duration_seconds
                FROM transcriptions
                GROUP BY device_name
                ORDER BY count DESC
            """)

            stats['by_device'] = [dict(row) for row in cursor.fetchall()]

            # Статистика по дням
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count,
                    SUM(duration_seconds) as duration_seconds
                FROM transcriptions
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """)

            stats['by_day'] = [dict(row) for row in cursor.fetchall()]

            return stats

    def delete_old_transcriptions(self, days: int = 90) -> int:
        """
        Удаление старых транскрипций

        Args:
            days: Удалить записи старше N дней

        Returns:
            Количество удаленных записей
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM transcriptions
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,))

            deleted_count = cursor.rowcount

            logger.info(f"Удалено старых транскрипций: {deleted_count}")

            return deleted_count


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    db = TranscriptionDatabase()

    # Пример добавления транскрипции
    try:
        transcription_id = db.add_transcription(
            file_hash="test_hash_12345",
            original_filename="test_recording.mp3",
            audio_file_path="data/audio/test_recording.mp3",
            transcription_text="Esta es una prueba de transcripción en español.",
            device_name="USB_Device_1",
            language="es",
            duration_seconds=120.5
        )
        print(f"\nДобавлена транскрипция: ID={transcription_id}")

    except Exception as e:
        print(f"Ошибка: {e}")

    # Получение статистики
    stats = db.get_statistics()
    print(f"\nСтатистика:")
    print(f"  Всего транскрипций: {stats['total_transcriptions']}")
    print(f"  Общая длительность: {stats['total_duration_seconds']/3600:.1f} часов")
    print(f"  Всего слов: {stats['total_words']}")

    # Поиск
    results = db.search_transcriptions(query="prueba")
    print(f"\nНайдено по запросу 'prueba': {len(results)}")
