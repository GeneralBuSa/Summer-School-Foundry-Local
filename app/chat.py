"""Yerel indeks üzerinden güvenli, kaynaklı soru-cevap akışı.

Bu modül, kullanıcının sorduğu soruları vektör benzerliği araması, reranking (yeniden sıralama)
ve dil modeli (LLM) entegrasyonu ile yanıtlayan ana iş mantığını içerir.
"""

from __future__ import annotations

from app.config import EMBEDDING_MODEL_ALIAS, MIN_SIMILARITY_SCORE, NO_ANSWER_MESSAGE, TOP_K
from app.domain import Answer
from app.foundry import FoundryRuntime
from app.prompting import build_messages
from app.repository import SQLiteRepository
from app.retrieval import has_confident_match, retrieve_top_chunks
from app.reranker import rerank


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

    return Answer(text=response.choices[0].message.content.strip(), sources=results, grounded=True)


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

