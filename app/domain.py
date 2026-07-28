"""Uygulama katmanları arasında kullanılan veri nesneleri."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    source_path: str
    content: str
    content_hash: str


@dataclass(frozen=True)
class StoredChunk:
    id: int
    source_path: str
    chunk_index: int
    content: str
    embedding: list[float]
    embedding_model: str


@dataclass(frozen=True)
class RetrievalResult:
    chunk: StoredChunk
    score: float


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[RetrievalResult]
    grounded: bool
