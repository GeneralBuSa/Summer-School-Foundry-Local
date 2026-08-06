"""SQLite şeması, transaction işlemleri ve indeks kayıtları.

Bu modül, belge metinlerinin ve bunlara ait embedding vektörlerinin SQLite veritabanı
üzerinde güvenli (ACID uyumlu) saklanmasını ve yönetilmesini sağlar.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

from app.domain import StoredChunk


# Veritabanı şema tanımı: belgeler (documents) ve parçalar (chunks) tabloları
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY,
    source_path   TEXT NOT NULL UNIQUE,
    content_hash  TEXT NOT NULL,
    indexed_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id               INTEGER PRIMARY KEY,
    document_id      INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index      INTEGER NOT NULL,
    content          TEXT NOT NULL,
    embedding_json   TEXT NOT NULL,
    embedding_model  TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
"""


class RepositoryError(RuntimeError):
    """Bozuk veya beklenmeyen kalıcı indeks verisi oluştuğunda fırlatılan özel istisna."""


class SQLiteRepository:
    """SQLite veritabanı işlemlerini yöneten depo sınıfı.

    Attributes:
        database_path (Path): SQLite veritabanı dosyasının disk yolu.
    """

    def __init__(self, database_path: Path):
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Güvenli veritabanı bağlantısı oluşturan ve otomatik kapatan bağlam yöneticisi (context manager).

        Yields:
            sqlite3.Connection: Yapılandırılmış SQLite bağlantı nesnesi.
        """
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Veritabanı tablolarını ve indekslerini şemaya uygun olarak oluşturur."""
        with self._connection() as connection:
            connection.executescript(SCHEMA)

    def get_indexed_embedding_models(self) -> set[str]:
        """İndekste kayıtlı tüm farklı embedding model adlarını döndürür.

        Returns:
            set[str]: Kullanılan model isimlerinin kümesi.
        """
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT embedding_model FROM chunks"
            ).fetchall()
            return {row["embedding_model"] for row in rows}

    def is_current(self, source_path: str, content_hash: str, embedding_model: str) -> bool:
        """Belgenin mevcut indekste güncel olup olmadığını kontrol eder.

        Args:
            source_path (str): Belgenin dosya yolu.
            content_hash (str): Belge içeriğinin SHA256 özeti.
            embedding_model (str): Kullanılan embedding modelinin adı.

        Returns:
            bool: Belge değişmediyse ve aynı model ile indekslendiysse True, aksi halde False.
        """
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM documents WHERE source_path = ? AND content_hash = ?",
                (source_path, content_hash),
            ).fetchone()
            if row is None:
                return False
            counts = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN embedding_model = ? THEN 1 ELSE 0 END) AS matching
                FROM chunks WHERE document_id = ?
                """,
                (embedding_model, row["id"]),
            ).fetchone()
            return bool(counts["total"]) and counts["total"] == counts["matching"]

    def replace_document(
        self,
        source_path: str,
        content_hash: str,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        embedding_model: str,
    ) -> None:
        """Bir belgenin parçalarını ve embedding'lerini atomik bir işlemle (transaction) günceller veya ekler.

        Args:
            source_path (str): Belgenin dosya yolu.
            content_hash (str): İçerik özeti (hash).
            chunks (Sequence[str]): Metin parçaları dizisi.
            embeddings (Sequence[Sequence[float]]): Parçalara karşılık gelen embedding vektörleri.
            embedding_model (str): Kullanılan embedding model adı.

        Raises:
            ValueError: Parça ve embedding sayıları eşleşmiyorsa veya liste boşsa.
            RepositoryError: SQLite kayıt işlemi esnasında hata meydana gelirse.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Parça ve embedding sayıları eşit olmalıdır.")
        if not chunks:
            raise ValueError("Boş belge SQLite'a indekslenemez.")

        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            try:
                connection.execute("BEGIN")
                existing = connection.execute(
                    "SELECT id FROM documents WHERE source_path = ?", (source_path,)
                ).fetchone()
                if existing is None:
                    cursor = connection.execute(
                        "INSERT INTO documents(source_path, content_hash, indexed_at) VALUES (?, ?, ?)",
                        (source_path, content_hash, timestamp),
                    )
                    document_id = cursor.lastrowid
                else:
                    document_id = existing["id"]
                    connection.execute(
                        "UPDATE documents SET content_hash = ?, indexed_at = ? WHERE id = ?",
                        (content_hash, timestamp, document_id),
                    )
                    connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

                records = [
                    (
                        document_id,
                        index,
                        content,
                        json.dumps(list(embedding), separators=(",", ":")),
                        embedding_model,
                        timestamp,
                    )
                    for index, (content, embedding) in enumerate(zip(chunks, embeddings))
                ]
                connection.executemany(
                    """
                    INSERT INTO chunks(document_id, chunk_index, content, embedding_json, embedding_model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise RepositoryError("SQLite indeks yazımı başarısız oldu.") from exc

    def get_chunks(self, embedding_model: str) -> list[StoredChunk]:
        """Belirtilen embedding modeli ile indekslenmiş tüm metin parçalarını çeker.

        Args:
            embedding_model (str): Aranan embedding modeli.

        Returns:
            list[StoredChunk]: Kayıtlı parçalar ve vektör bilgileri listesi.

        Raises:
            RepositoryError: Kayıtlı embedding JSON verisi bozuksa.
        """
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT chunks.id, documents.source_path, chunks.chunk_index, chunks.content,
                       chunks.embedding_json, chunks.embedding_model
                FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                WHERE chunks.embedding_model = ?
                ORDER BY documents.source_path, chunks.chunk_index
                """,
                (embedding_model,),
            ).fetchall()

        stored_chunks: list[StoredChunk] = []
        for row in rows:
            try:
                embedding = json.loads(row["embedding_json"])
                if not isinstance(embedding, list) or not all(
                    isinstance(value, (int, float)) for value in embedding
                ):
                    raise ValueError("Embedding JSON dizisi sayısal değil.")
            except (json.JSONDecodeError, ValueError) as exc:
                raise RepositoryError(f"Bozuk embedding kaydı: chunks.id={row['id']}") from exc
            stored_chunks.append(
                StoredChunk(
                    id=row["id"],
                    source_path=row["source_path"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    embedding=[float(value) for value in embedding],
                    embedding_model=row["embedding_model"],
                )
            )
        return stored_chunks

    def remove_missing_documents(self, existing_source_paths: set[str]) -> int:
        """Diskte artık bulunmayan belgelere ait veritabanı kayıtlarını temizler.

        Args:
            existing_source_paths (set[str]): Diskte mevcut olan geçerli dosya yolları kümesi.

        Returns:
            int: Veritabanından silinen belge sayısı.
        """
        with self._connection() as connection:
            rows = connection.execute("SELECT id, source_path FROM documents").fetchall()
            stale_ids = [row["id"] for row in rows if row["source_path"] not in existing_source_paths]
            if stale_ids:
                connection.executemany("DELETE FROM documents WHERE id = ?", [(doc_id,) for doc_id in stale_ids])
                connection.commit()
            return len(stale_ids)

