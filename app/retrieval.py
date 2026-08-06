"""Embedding vektörlerini cosine similarity ile sıralar."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from app.domain import RetrievalResult, StoredChunk

try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


_COUNTRY_MAP = {
    "türkiye": "turkey",
    "türkiyenin": "turkey",
    "türkiyede": "turkey",
    "türkiyedeki": "turkey",
    "turkiye": "turkey",
    "turkiyenin": "turkey",
    "almanya": "germany",
    "almanyanın": "germany",
    "fransa": "france",
    "fransanın": "france",
    "ingiltere": "united kingdom",
    "ingilterenin": "united kingdom",
    "yunanistan": "greece",
    "rusya": "russia",
    "japonya": "japan",
    "çin": "china",
    "abd": "united states",
}


def _tokenize(text: str) -> list[str]:
    """Metni Türkçe duyarlı küçük harfli kelime token'larına ayırır ve İngilizce terimleri eşler."""
    raw_tokens = re.findall(r"\w+", text.lower())
    tokens = list(raw_tokens)
    for t in raw_tokens:
        if t in _COUNTRY_MAP:
            tokens.append(_COUNTRY_MAP[t])
    return tokens


_STOPWORDS = {
    "ve", "veya", "ile", "bir", "bu", "şu", "o", "ne", "nedir", "nasıl", "hangi", "kaç",
    "için", "olan", "olarak", "mi", "mı", "mu", "mü", "de", "da", "den", "dan", "çok",
    "daha", "en", "var", "yok", "hakkında", "ilgili", "kavramı", "kavram", "bilgi",
    "bilgisi", "ver", "veri", "göre", "tarafından", "proje", "projenin", "yönetim",
    "yönetimi", "yönetiminde", "project", "gutenberg", "license", "management", "professional",
}


def compute_bm25_scores(query_text: str, chunks: Sequence[StoredChunk]) -> list[float]:
    """BM25 Okapi algoritması ile kelime anahtarlı arama skorları hesaplar."""
    query_tokens = _tokenize(query_text)
    if not query_tokens or not chunks:
        return [0.0] * len(chunks)

    num_docs = len(chunks)
    doc_tokens = [_tokenize(chunk.content) for chunk in chunks]
    doc_lengths = [len(tokens) for tokens in doc_tokens]
    avgdl = sum(doc_lengths) / num_docs if num_docs > 0 else 1.0

    df: Counter[str] = Counter()
    for tokens in doc_tokens:
        unique_tokens = set(tokens)
        for token in unique_tokens:
            df[token] += 1

    k1 = 1.5
    b = 0.75
    scores: list[float] = []

    for i, tokens in enumerate(doc_tokens):
        doc_len = doc_lengths[i]
        tf_map = Counter(tokens)
        score = 0.0
        for q in query_tokens:
            if q not in tf_map:
                continue
            freq = tf_map[q]
            doc_freq = df.get(q, 0)
            idf = math.log((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            num = freq * (k1 + 1.0)
            den = freq + k1 * (1.0 - b + b * (doc_len / avgdl))
            score += idf * (num / den)
        scores.append(max(0.0, score))

    max_s = max(scores) if scores else 0.0
    if max_s > 0:
        return [s / max_s for s in scores]
    return [0.0] * len(chunks)


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    if len(first) != len(second):
        raise ValueError("Embedding boyutları eşit olmalıdır.")
    if not first:
        return 0.0
    dot_product = sum(left * right for left, right in zip(first, second))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    return dot_product / (first_norm * second_norm) if first_norm and second_norm else 0.0


def reciprocal_rank_fusion(
    vec_scores: list[float], bm25_scores: list[float], rrf_k: int = 60
) -> list[float]:
    """Vektör ve BM25 sıralamalarını Reciprocal Rank Fusion (RRF) ile yeniden sıralar."""
    vec_ranks = {
        idx: rank
        for rank, (idx, _) in enumerate(sorted(enumerate(vec_scores), key=lambda x: x[1], reverse=True))
    }
    bm25_ranks = {
        idx: rank
        for rank, (idx, _) in enumerate(sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True))
    }

    rrf_scores = []
    for idx in range(len(vec_scores)):
        score = (1.0 / (rrf_k + vec_ranks[idx])) + (1.0 / (rrf_k + bm25_ranks[idx]))
        rrf_scores.append(score)

    max_score = max(rrf_scores) if rrf_scores else 1.0
    return [s / max_score for s in rrf_scores]


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [1.0 if high > 0 else 0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def retrieve_top_chunks(
    query_embedding: Sequence[float],
    chunks: Sequence[StoredChunk],
    top_k: int,
    query_text: str | None = None,
    alpha: float = 0.7,
) -> list[RetrievalResult]:
    """Vektör araması ve BM25 kelime aramasını RRF Re-ranking ile harmanlayıp sıralar."""
    if top_k <= 0:
        raise ValueError("top_k pozitif olmalıdır.")
    if not chunks:
        return []

    if _HAS_NUMPY:
        query_vec = np.array(query_embedding, dtype=np.float32)
        matrix = np.array([c.embedding for c in chunks], dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        matrix_norms = np.linalg.norm(matrix, axis=1)

        query_norm = 1e-10 if query_norm == 0 else query_norm
        matrix_norms[matrix_norms == 0] = 1e-10

        vec_scores = np.dot(matrix, query_vec) / (matrix_norms * query_norm)
        vec_scores_list = vec_scores.tolist()
    else:
        vec_scores_list = [cosine_similarity(query_embedding, chunk.embedding) for chunk in chunks]

    if query_text and query_text.strip():
        bm25_scores = compute_bm25_scores(query_text, chunks)
        # Soruda yıl veya özel sayı varsa BM25 kelime eşleşmesine öncelik ver
        if re.search(r"\b(19\d\d|20\d\d|\d{2,4})\b", query_text):
            alpha = min(alpha, 0.4)
        alpha = max(0.0, min(1.0, alpha))
        vec_norm = _normalize(vec_scores_list)
        bm25_norm = _normalize(bm25_scores)
        final_scores = [
            (alpha * vector_score) + ((1.0 - alpha) * keyword_score)
            for vector_score, keyword_score in zip(vec_norm, bm25_norm)
        ]
    else:
        final_scores = vec_scores_list

    ranked = [
        RetrievalResult(chunk=chunk, score=float(score))
        for chunk, score in zip(chunks, final_scores)
    ]
    return sorted(ranked, key=lambda result: result.score, reverse=True)[:top_k]


def has_confident_match(
    query_text: str,
    query_embedding: Sequence[float],
    chunks: Sequence[StoredChunk],
    semantic_threshold: float = 0.45,
) -> bool:
    """Normalize edilmiş RRF skorundan bağımsız olarak gerçek eşleşme arar."""
    query_tokens = set(_tokenize(query_text)) - _STOPWORDS
    if not chunks or not query_tokens:
        return False
    min_required_tokens = min(2, len(query_tokens))
    for chunk in chunks:
        passage_tokens = set(_tokenize(chunk.content)) - _STOPWORDS
        if len(query_tokens & passage_tokens) >= min_required_tokens:
            return True
    return max((cosine_similarity(query_embedding, chunk.embedding) for chunk in chunks), default=0.0) >= semantic_threshold
