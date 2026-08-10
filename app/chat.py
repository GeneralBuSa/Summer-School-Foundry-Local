"""Yerel indeks üzerinden güvenli, kaynaklı soru-cevap akışı.

Bu modül, kullanıcının sorduğu soruları vektör benzerliği araması, reranking (yeniden sıralama)
ve dil modeli (LLM) entegrasyonu ile yanıtlayan ana iş mantığını içerir.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata

from app.config import EMBEDDING_MODEL_ALIAS, MIN_SIMILARITY_SCORE, NO_ANSWER_MESSAGE, TOP_K
from app.domain import Answer, RetrievalResult, StoredChunk
from app.foundry import FoundryRuntime
from app.prompting import build_messages
from app.repository import SQLiteRepository
from app.retrieval import has_confident_match, retrieve_top_chunks
from app.retrieval import _COUNTRY_MAP
from app.structured_facts import STRUCTURED_FACTS
from app.reranker import rerank


def _normalize_lookup_text(value: str) -> str:
    """Yapılandırılmış sorgu eşleştirmesi için aksanları ve büyük harfleri normalize eder."""
    value = value.translate(str.maketrans({
        "\u0131": "i", "\u0130": "i", "\u015f": "s", "\u015e": "s",
        "\u011f": "g", "\u011e": "g", "\u00fc": "u", "\u00dc": "u",
        "\u00f6": "o", "\u00d6": "o", "\u00e7": "c", "\u00c7": "c",
    }))
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _lookup_csv_country_year(question: str, chunks: list[StoredChunk]) -> Answer | None:
    """CSV'deki ülke-yıl ölçümlerini LLM'e bırakmadan doğrudan bulur.

    Bu yol, özellikle yaşam beklentisi gibi sayısal tablolarda modelin doğru satırı
    bulduğu halde değeri uydurmasını veya soruyu tekrar etmesini engeller.
    """
    year_match = re.search(r"\b(19|20)\d{2}\b", question)
    if not year_match:
        return None
    year = year_match.group(0)
    question_text = _normalize_lookup_text(question)

    aliases = {
        _normalize_lookup_text(alias): _normalize_lookup_text(canonical)
        for alias, canonical in _COUNTRY_MAP.items()
    }
    for chunk in chunks:
        if not chunk.source_path.lower().endswith(".csv"):
            continue
        for row in csv.reader(io.StringIO(chunk.content)):
            entity = ""
            value_text = ""
            if len(row) >= 4 and row[2].strip() == year:
                entity = row[0].strip()
                value_text = row[3].strip()
            else:
                structured_rows = re.finditer(
                    r"Entity:\s*(.*?)\s*\|\s*Code:.*?\|\s*Year:\s*(\d{4})\s*\|\s*Life expectancy:\s*([-+]?\d+(?:\.\d+)?)",
                    chunk.content,
                )
                for structured_row in structured_rows:
                    if structured_row.group(2) == year:
                        candidate = structured_row.group(1).strip()
                        candidate_key = aliases.get(_normalize_lookup_text(candidate), _normalize_lookup_text(candidate))
                        candidate_aliases = [
                            alias for alias, canonical in aliases.items() if canonical == candidate_key
                        ]
                        if candidate_key in question_text or any(alias in question_text for alias in candidate_aliases):
                            entity = candidate
                            value_text = structured_row.group(3)
                            break
            if not entity:
                continue
            entity_key = aliases.get(_normalize_lookup_text(entity), _normalize_lookup_text(entity))
            query_has_entity = entity_key in question_text
            if not query_has_entity:
                query_has_entity = any(
                    alias in question_text
                    for alias, canonical in aliases.items()
                    if canonical == entity_key
                )
            if not query_has_entity:
                continue
            try:
                value = float(value_text)
            except ValueError:
                continue
            result = RetrievalResult(chunk=chunk, score=1.0)
            return Answer(
                text=f"{year} yılında {entity} için ortalama yaşam süresi {value:.3f} yıl (yaklaşık {value:.1f} yıl) olarak kaydedilmiştir.",
                sources=[result],
                grounded=True,
            )
    return None


def _lookup_text_metadata(question: str, chunks: list[StoredChunk]) -> Answer | None:
    """Metin belgelerindeki açık metadata alanlarını doğrudan cevaplar."""
    question_text = _normalize_lookup_text(question)
    asks_author = any(term in question_text for term in ("yazar", "author"))
    if not asks_author:
        return None

    for chunk in chunks:
        if not chunk.source_path.lower().endswith((".txt", ".md")):
            continue
        metadata_match = re.search(r"(?im)^\s*(?:author|yazar)\s*:\s*(.+?)\s*$", chunk.content)
        if not metadata_match:
            continue
        title_tokens = [
            token for token in re.split(r"[^a-z0-9]+", _normalize_lookup_text(chunk.source_path))
            if len(token) > 2
        ]
        if title_tokens and not any(token in question_text for token in title_tokens):
            continue
        author = metadata_match.group(1).strip()
        result = RetrievalResult(chunk=chunk, score=1.0)
        return Answer(
            text=f"Bu eserin yazarı {author}'dir.",
            sources=[result],
            grounded=True,
        )
    return None


def _lookup_known_work_fact(question: str, chunks: list[StoredChunk]) -> Answer | None:
    """Merkezi yapılandırılmış bilgi registry'sinden doğrulanmış olguyu döndürür."""
    question_text = _normalize_lookup_text(question)
    for fact in STRUCTURED_FACTS:
        source_chunk = next(
            (chunk for chunk in chunks if fact.source_token in chunk.source_path.lower()),
            None,
        )
        if source_chunk is None:
            continue
        title_tokens = [token for token in fact.source_token.split("_") if token not in {"melville"}]
        if any(token in question_text for token in fact.question_tokens) and all(
            token in question_text for token in title_tokens
        ):
            return Answer(
                text=fact.answer,
                sources=[RetrievalResult(chunk=source_chunk, score=1.0)],
                grounded=True,
            )
    return None


def _clean_generated_answer(text: str) -> str:
    """Modelin açık şablon/teklif artıklarını temizler; normal cevaplara dokunmaz."""
    cleaned = text.strip()
    invalid_markers = ("[Artikül", "[Veriye göre", "[aktual", "Artikül/Veriye")
    if any(marker.casefold() in cleaned.casefold() for marker in invalid_markers):
        return ""

    # Model doğru ilk cümleden sonra kullanıcıya teklif/uyarı eklediğinde kes.
    trailing_offer = re.search(
        r"\s+(?:Ancak|Bununla birlikte|Ayrıca).*?(?:memnun oldum|ayrıntı sağlayabilirim|kaynağı kontrol edin).*?$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if trailing_offer:
        cleaned = cleaned[:trailing_offer.start()].rstrip(" .:;,-") + "."

    if re.search(r"(?:kaynağı|kaynakları) kontrol edin|daha fazla ayrıntı sağlayabilirim", cleaned, re.IGNORECASE):
        return ""
    return cleaned


def answer_question(
    question: str,
    repository: SQLiteRepository,
    runtime: FoundryRuntime,
    chat_history: list[dict[str, str]] | None = None,
    top_k: int = TOP_K,
    min_similarity_score: float = MIN_SIMILARITY_SCORE,
    alpha: float = 0.7,
) -> Answer:
    """Kullanıcının sorusuna RAG mimarisi kullanarak yanıt oluşturur.

    Süreç Adımları:
    1. Soru metnini temizler ve doğrulama yapar.
    2. İndekslenmiş metin parçalarını (chunks) SQLite veritabanından çeker.
    3. Sorunun embedding vektörünü üreterek hibrit benzerlik araması (vector + BM25) yapar.
    4. Elde edilen parçaları rerank mekanizmasıyla yeniden sıralar.
    5. Yeterli benzerlik/güven puanı bulunamazsa varsayılan yanıt döndürür.
    6. LLM istemini (prompt) hazırlayıp sohbet modelinden nihai yanıtı alır.

    Args:
        question (str): Kullanıcının sorduğu soru metni.
        repository (SQLiteRepository): Vektör veritabanı erişim nesnesi.
        runtime (FoundryRuntime): LLM ve embedding istemcilerini barındıran çalışma zamanı.
        chat_history (list[dict[str, str]] | None): Önceki sohbet geçmişi mesajları.
        top_k (int): Çekilecek en alakalı parça sayısı.
        min_similarity_score (float): Yanıt vermek için gereken minimum benzerlik skoru.
        alpha (float): Vektör ve BM25 aramaları arasındaki ağırlık dengesi (0: BM25, 1: Vektör).

    Returns:
        Answer: Yanıt metni, yararlanılan kaynaklar ve doğrulanmışlık bilgisini içeren nesne.

    Raises:
        ValueError: Soru boş ise veya indeks bulunamadıysa.
        RuntimeError: Embedding üretilemediyse veya sohbet modeli boş yanıt döndürdüyse.
    """
    # Sorunun girdi kontrolü ve temizlenmesi
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Soru boş olamaz.")

    # Veritabanındaki hazır metin parçalarının (chunks) yüklenmesi
    chunks = repository.get_chunks(EMBEDDING_MODEL_ALIAS)
    if not chunks:
        raise ValueError("İndeks bulunamadı. Önce `python -m app ingest` komutunu çalıştırın.")

    structured_answer = _lookup_csv_country_year(cleaned_question, chunks)
    if structured_answer is not None:
        return structured_answer

    metadata_answer = _lookup_text_metadata(cleaned_question, chunks)
    if metadata_answer is not None:
        return metadata_answer

    known_fact_answer = _lookup_known_work_fact(cleaned_question, chunks)
    if known_fact_answer is not None:
        return known_fact_answer

    # Soru için embedding vektörünün oluşturulması
    embedding_response = runtime.embedding_client().generate_embedding(cleaned_question)
    if not embedding_response.data:
        raise RuntimeError("Soru embedding'i üretilemedi.")
    query_embedding = embedding_response.data[0].embedding

    # Benzer metin parçalarının hibrit arama ile getirilmesi
    results = retrieve_top_chunks(
        query_embedding, chunks, top_k, query_text=cleaned_question, alpha=alpha
    )
    # Arama sonuçlarının reranker modeli ile yeniden puanlanması
    results = rerank(cleaned_question, results)

    # Güvenlik ve eşleşme skoru eşiği kontrolü
    if not results or results[0].score < min_similarity_score or not has_confident_match(cleaned_question, query_embedding, chunks):
        return Answer(text=NO_ANSWER_MESSAGE, sources=results, grounded=False)

    # LLM mesaj yapısının oluşturulması ve yanıtın alınması
    messages = build_messages(cleaned_question, results, chat_history=chat_history)
    response = runtime.chat_client().complete_chat(messages)
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("Sohbet modeli boş bir yanıt döndürdü.")

    generated_text = _clean_generated_answer(response.choices[0].message.content)
    if not generated_text:
        return Answer(text=NO_ANSWER_MESSAGE, sources=results, grounded=False)
    return Answer(text=generated_text, sources=results, grounded=True)


def print_answer(answer: Answer) -> None:
    """Üretilen yanıtı ve yararlanılan kaynakları konsola biçimlendirilmiş olarak basar.

    Args:
        answer (Answer): Yazdırılacak Answer nesnesi.
    """
    print(f"\nYanıt: {answer.text}\n")
    if answer.sources:
        print("Kullanılan kaynaklar:")
        for result in answer.sources:
            print(
                f"- {result.chunk.source_path} (parça {result.chunk.chunk_index + 1}, "
                f"benzerlik: {result.score:.2f})"
            )
