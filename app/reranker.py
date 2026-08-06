"""Hibrit adayları soru-parça ilişkisine göre yeniden sıralayan (re-ranking) modül.

Bu modül, harici bir kütüphaneye bağımlı kalmadan metin örtüşmesi ve ifade eşleşmesi
bonusları ile aday parçaların skorlarını günceller ve yeniden sıralar.
"""

from __future__ import annotations

from app.domain import RetrievalResult
from app.retrieval import _tokenize


def _tokens(text: str) -> set[str]:
    """Metni benzersiz kelime token' kümesine dönüştürür.

    Args:
        text (str): İşlenecek metin.

    Returns:
        set[str]: Kelime token' kümesi.
    """
    return set(_tokenize(text))


def cross_encoder_score(query: str, passage: str, base_score: float) -> float:
    """Temel vektör skoru, kelime örtüşme oranı ve tam ifade bonusunu birleştirerek yeni skor üretir.

    Args:
        query (str): Kullanıcı sorusu.
        passage (str): İncelenen metin parçası (passage).
        base_score (float): Aramadan gelen başlangıç skoru.

    Returns:
        float: 0.0 ile 1.0 arasında yeniden hesaplanan nihai skor.
    """
    query_clean = " ".join(query.casefold().split())
    passage_clean = " ".join(passage.casefold().split())
    query_tokens = _tokens(query_clean)
    passage_tokens = _tokens(passage_clean)
    if not query_tokens or not passage_tokens:
        return max(0.0, min(1.0, base_score))

    overlap = len(query_tokens & passage_tokens) / len(query_tokens)
    phrase_bonus = 0.15 if query_clean in passage_clean else 0.0
    return min(1.0, (0.55 * base_score) + (0.30 * overlap) + phrase_bonus)


def rerank(query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
    """Getirilen arama sonuçlarını yeniden puanlar ve azalan skora göre sıralar.

    Args:
        query (str): Soru metni.
        results (list[RetrievalResult]): İlk aşama arama sonuçları.

    Returns:
        list[RetrievalResult]: Yeniden puanlanıp sıralanmış sonuçlar listesi.
    """
    rescored = [
        RetrievalResult(result.chunk, cross_encoder_score(query, result.chunk.content, result.score))
        for result in results
    ]
    return sorted(rescored, key=lambda result: result.score, reverse=True)

