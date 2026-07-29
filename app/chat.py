"""Yerel indeks üzerinden güvenli, kaynaklı soru-cevap akışı."""

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
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Soru boş olamaz.")

    chunks = repository.get_chunks(EMBEDDING_MODEL_ALIAS)
    if not chunks:
        raise ValueError("İndeks bulunamadı. Önce `python -m app ingest` komutunu çalıştırın.")

    embedding_response = runtime.embedding_client().generate_embedding(cleaned_question)
    if not embedding_response.data:
        raise RuntimeError("Soru embedding'i üretilemedi.")
    query_embedding = embedding_response.data[0].embedding
    results = retrieve_top_chunks(
        query_embedding, chunks, top_k, query_text=cleaned_question, alpha=alpha
    )
    results = rerank(cleaned_question, results)

    if not results or results[0].score < min_similarity_score or not has_confident_match(cleaned_question, query_embedding, chunks):
        return Answer(text=NO_ANSWER_MESSAGE, sources=results, grounded=False)

    messages = build_messages(cleaned_question, results, chat_history=chat_history)
    response = runtime.chat_client().complete_chat(messages)
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("Sohbet modeli boş bir yanıt döndürdü.")
    return Answer(text=response.choices[0].message.content.strip(), sources=results, grounded=True)


def print_answer(answer: Answer) -> None:
    print(f"\nYanıt: {answer.text}\n")
    if answer.sources:
        print("Kullanılan kaynaklar:")
        for result in answer.sources:
            print(
                f"- {result.chunk.source_path} (parça {result.chunk.chunk_index + 1}, "
                f"benzerlik: {result.score:.2f})"
            )
