"""Uygulama katmanları arasında taşınan temel domain (veri modeli) nesneleri.

Bu modül; belgeleri, metin parçalarını, arama sonuçlarını ve üretilen yanıtları temsil eden
değiştirilemez (immutable/frozen) dataclass yapılarını tanımlar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    """Diskte keşfedilen orijinal bir kaynak belgeyi temsil eder."""
    source_path: str  # Belgenin göreceli dosya yolu
    content: str  # Belgenin düz metin içeriği
    content_hash: str  # Belgenin SHA256 içerik özeti


@dataclass(frozen=True)
class StoredChunk:
    """Veritabanında saklanan metin parçasını ve ona ait embedding bilgilerini temsil eder."""
    id: int  # Parçanın veritabanı birincil anahtarı (ID)
    source_path: str  # Ait olduğu belgenin yolu
    chunk_index: int  # Belge içindeki sıralı parça indeksi (0 tabanlı)
    content: str  # Parçanın metin içeriği
    embedding: list[float]  # Parçanın sayısal embedding vektörü
    embedding_model: str  # Embedding üretiminde kullanılan model takma adı


@dataclass(frozen=True)
class RetrievalResult:
    """Arama motorunun getirdiği eşleşen bir metin parçasını ve eşleşme skorunu barındırır."""
    chunk: StoredChunk  # Bulunan veritabanı parçası
    score: float  # Hesaplanan benzerlik skoru (0.0 - 1.0)


@dataclass(frozen=True)
class Answer:
    """Soruya RAG motoru tarafından verilen nihai yanıtı barındırır."""
    text: str  # Üretilen yanıt metni
    sources: list[RetrievalResult]  # Yanıt üretilirken başvurulan kaynak parçalar
    grounded: bool  # Bilginin belgelere dayalı olup olmadığı bilgisi

