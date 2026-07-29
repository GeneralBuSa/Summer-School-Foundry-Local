"""Retrieval kalite ölçüm scripti.

Golden test veri setindeki sorularla indeksteki parçaları karşılaştırarak
Hit Rate, MRR (Mean Reciprocal Rank) ve anahtar kelime eşleşme oranı raporlar.

Kullanım:
    python -m app eval
    python tests/eval_retrieval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Proje kökünü sys.path'e ekle (doğrudan çalıştırma için)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import DATABASE_PATH, EMBEDDING_MODEL_ALIAS, TOP_K
from app.foundry import FoundryRuntime
from app.repository import SQLiteRepository
from app.retrieval import has_confident_match, retrieve_top_chunks
from app.reranker import rerank

EVAL_DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset.json"


def load_eval_dataset() -> list[dict]:
    """Golden test veri setini yükler."""
    with open(EVAL_DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


def evaluate_retrieval(
    repository: SQLiteRepository, runtime: FoundryRuntime, top_k: int = TOP_K
) -> dict:
    """Tüm test soruları için retrieval metriklerini hesaplar."""
    dataset = load_eval_dataset()
    chunks = repository.get_chunks(EMBEDDING_MODEL_ALIAS)

    if not chunks:
        print("HATA: İndeks boş. Önce 'python -m app ingest' çalıştırın.", file=sys.stderr)
        return {}

    embedding_client = runtime.embedding_client()

    total_questions = 0
    hit_count = 0
    reciprocal_ranks: list[float] = []
    keyword_scores: list[float] = []
    no_answer_correct = 0
    no_answer_total = 0

    results_detail: list[dict] = []

    for item in dataset:
        qid = item["id"]
        question = item["question"]
        expected_source = item.get("expected_source")
        expected_keywords = item.get("expected_keywords", [])
        expect_no_answer = item.get("expect_no_answer", False)

        # Soru embedding'i üret
        embedding_response = embedding_client.generate_embedding(question)
        if not embedding_response.data:
            print(f"  UYARI: {qid} - Embedding üretilemedi, atlanıyor.")
            continue

        query_embedding = embedding_response.data[0].embedding
        retrieval_results = retrieve_top_chunks(
            query_embedding, chunks, top_k, query_text=question
        )
        retrieval_results = rerank(question, retrieval_results)

        total_questions += 1

        # Bilgi tabanı dışı soru kontrolü
        if expect_no_answer:
            no_answer_total += 1
            confident = has_confident_match(question, query_embedding, chunks)
            if not retrieval_results or retrieval_results[0].score < 0.35 or not confident:
                no_answer_correct += 1
                results_detail.append({
                    "id": qid, "question": question, "status": "✅ Doğru RED",
                    "top_score": retrieval_results[0].score if retrieval_results else 0.0,
                })
            else:
                results_detail.append({
                    "id": qid, "question": question, "status": "❌ Yanlış KABUL",
                    "top_score": retrieval_results[0].score,
                    "top_source": retrieval_results[0].chunk.source_path,
                })
            continue

        # Hit Rate: Beklenen kaynak ilk top_k sonuçta mı?
        retrieved_sources = [r.chunk.source_path for r in retrieval_results]
        hit = expected_source in retrieved_sources if expected_source else False
        if hit:
            hit_count += 1

        # MRR: Beklenen kaynağın sıralama konumu
        rr = 0.0
        if expected_source:
            for rank, src in enumerate(retrieved_sources, start=1):
                if src == expected_source:
                    rr = 1.0 / rank
                    break
        reciprocal_ranks.append(rr)

        # Anahtar Kelime Eşleşmesi: Getirilen parçalarda kaç anahtar kelime var?
        combined_text = " ".join(r.chunk.content.lower() for r in retrieval_results)
        if expected_keywords:
            matched = sum(1 for kw in expected_keywords if kw.lower() in combined_text)
            kw_score = matched / len(expected_keywords)
        else:
            kw_score = 1.0
        keyword_scores.append(kw_score)

        status = "✅" if hit else "❌"
        results_detail.append({
            "id": qid, "question": question, "status": status,
            "hit": hit, "rr": rr, "kw_score": kw_score,
            "top_source": retrieved_sources[0] if retrieved_sources else None,
            "top_score": retrieval_results[0].score if retrieval_results else 0.0,
        })

    # Toplam metrikler
    grounded_count = total_questions - no_answer_total
    hit_rate = hit_count / grounded_count if grounded_count > 0 else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    avg_kw = sum(keyword_scores) / len(keyword_scores) if keyword_scores else 0.0
    no_answer_accuracy = no_answer_correct / no_answer_total if no_answer_total > 0 else 0.0

    return {
        "total_questions": total_questions,
        "grounded_questions": grounded_count,
        "no_answer_questions": no_answer_total,
        "hit_rate": hit_rate,
        "mrr": mrr,
        "avg_keyword_score": avg_kw,
        "no_answer_accuracy": no_answer_accuracy,
        "details": results_detail,
    }


def print_eval_report(metrics: dict) -> None:
    """Değerlendirme sonuçlarını terminale raporlar."""
    if not metrics:
        return

    print("\n" + "=" * 70)
    print("  📊 RAG RETRIEVAL KALİTE RAPORU")
    print("=" * 70)
    print(f"  Toplam Soru           : {metrics['total_questions']}")
    print(f"  Bilgi Tabanlı Soru    : {metrics['grounded_questions']}")
    print(f"  Bilgi Dışı Soru       : {metrics['no_answer_questions']}")
    print("-" * 70)
    print(f"  Hit Rate (top-{TOP_K})     : {metrics['hit_rate']:.1%}")
    print(f"  MRR (Mean Reciprocal) : {metrics['mrr']:.3f}")
    print(f"  Anahtar Kelime Eşleş. : {metrics['avg_keyword_score']:.1%}")
    print(f"  Bilgi Dışı Doğruluk   : {metrics['no_answer_accuracy']:.1%}")
    print("=" * 70)

    print("\n  Detaylı Sonuçlar:")
    print("-" * 70)
    for d in metrics["details"]:
        line = f"  {d['id']} {d['status']} | {d['question'][:45]:<45}"
        if "top_source" in d and d["top_source"]:
            line += f" | kaynak: {d['top_source']}"
        if "top_score" in d:
            line += f" ({d['top_score']:.2f})"
        print(line)

    print("-" * 70)

    # Kalite Tavsiyesi
    hr = metrics["hit_rate"]
    if hr >= 0.9 and metrics["no_answer_accuracy"] >= 0.8:
        print("  🟢 Retrieval kalitesi mükemmel.")
    elif hr >= 0.7 and metrics["no_answer_accuracy"] >= 0.6:
        print("  🟡 Retrieval kalitesi iyi, ama iyileştirme alanı var.")
    else:
        print("  🔴 Retrieval kalitesi düşük — chunk boyutu, overlap veya embedding modeli gözden geçirilmeli.")
    print()


def run_eval() -> int:
    """Eval pipeline'ını başlatır."""
    if not EVAL_DATASET_PATH.exists():
        print(f"HATA: Test veri seti bulunamadı: {EVAL_DATASET_PATH}", file=sys.stderr)
        return 1

    repository = SQLiteRepository(DATABASE_PATH)
    try:
        with FoundryRuntime() as runtime:
            metrics = evaluate_retrieval(repository, runtime)
            print_eval_report(metrics)
    except Exception as exc:
        print(f"Değerlendirme hatası: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_eval())
