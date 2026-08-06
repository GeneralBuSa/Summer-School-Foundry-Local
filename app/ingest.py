"""Belge keşfi, embedding üretimi ve kalıcı indeksleme orkestrasyonu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.chunker import chunk_text
from app.config import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL_ALIAS, KNOWLEDGE_BASE_DIR
from app.document_loader import discover_documents
from app.foundry import FoundryRuntime
from app.repository import SQLiteRepository

# CPU embedding modeli büyük toplu isteklerde zaman aşımına uğrayabiliyor;
# chunk'ları küçük gruplar halinde gönderiyoruz.
EMBEDDING_BATCH_SIZE = 32


@dataclass(frozen=True)
class IngestSummary:
    indexed_documents: int
    skipped_documents: int
    chunk_count: int


def check_model_compatibility(repository: SQLiteRepository) -> str | None:
    """İndeksteki embedding modeli ile aktif model arasındaki uyumsuzluğu kontrol eder.
    Uyumsuz model adı varsa döndürür, yoksa None döndürür."""
    indexed_models = repository.get_indexed_embedding_models()
    if indexed_models and EMBEDDING_MODEL_ALIAS not in indexed_models:
        stale = ", ".join(sorted(indexed_models))
        return stale
    return None


def _safe_generate_embeddings(embedding_client: Any, batch: list[str]) -> list[list[float]]:
    """Zaman aşımı veya SDK hatası durumunda batch'i otomatik küçük parçalara bölerek güvenle işler."""
    try:
        response = embedding_client.generate_embeddings(batch)
        return [item.embedding for item in response.data]
    except Exception:
        if len(batch) <= 4:
            res_embeddings: list[list[float]] = []
            for text in batch:
                single_res = embedding_client.generate_embeddings([text])
                res_embeddings.extend(item.embedding for item in single_res.data)
            return res_embeddings
        mid = len(batch) // 2
        return _safe_generate_embeddings(embedding_client, batch[:mid]) + _safe_generate_embeddings(embedding_client, batch[mid:])


def run_ingest(
    repository: SQLiteRepository, runtime: FoundryRuntime, force_reindex: bool = False
) -> IngestSummary:
    repository.initialize()

    # Model uyumluluk kontrolü
    stale_model = check_model_compatibility(repository)
    if stale_model and not force_reindex:
        raise ValueError(
            f"⚠️ İndeks uyumsuz embedding modeli içeriyor: '{stale_model}' (aktif: '{EMBEDDING_MODEL_ALIAS}'). "
            f"Yeniden indekslemek için --force-reindex bayrağını kullanın veya arayüzden 'Yeniden İndeksle' butonuna basın."
        )

    documents = discover_documents(KNOWLEDGE_BASE_DIR)
    if not documents:
        repository.remove_missing_documents(set())
        raise ValueError(
            "İndekslenecek belge yok. knowledge_base/ klasörüne UTF-8 .md veya .txt dosyası ekleyin."
        )
    repository.remove_missing_documents({document.source_path for document in documents})

    indexed_documents = 0
    skipped_documents = 0
    chunk_count = 0
    embedding_client = None

    for document in documents:
        if repository.is_current(document.source_path, document.content_hash, EMBEDDING_MODEL_ALIAS):
            skipped_documents += 1
            continue

        chunks = chunk_text(document.content, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            skipped_documents += 1
            continue

        print(f"\nİşleniyor: {document.source_path} (Toplam {len(chunks)} parça)", flush=True)

        if embedding_client is None:
            embedding_client = runtime.embedding_client()

        # Büyük belgelerde timeout'u önlemek için batch'ler halinde gönder
        embeddings: list[list[float]] = []
        for batch_start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch = chunks[batch_start:batch_start + EMBEDDING_BATCH_SIZE]
            embeddings.extend(_safe_generate_embeddings(embedding_client, batch))
            done = len(embeddings)
            pct = int((done / len(chunks)) * 100)
            status_line = f"{document.source_path} | {done}/{len(chunks)} parça tamamlandı (%{pct})"
            print(f"  -> {status_line}", flush=True)
            try:
                with open("data/progress.txt", "w", encoding="utf-8") as pf:
                    pf.write(f"{status_line}\n")
            except Exception:
                pass
        if len(embeddings) != len(chunks):
            raise RuntimeError(
                f"Embedding yanıtı eksik: {document.source_path} için {len(chunks)} parça, "
                f"{len(embeddings)} embedding döndü."
            )
        repository.replace_document(
            document.source_path,
            document.content_hash,
            chunks,
            embeddings,
            EMBEDDING_MODEL_ALIAS,
        )
        indexed_documents += 1
        chunk_count += len(chunks)

    return IngestSummary(indexed_documents, skipped_documents, chunk_count)
