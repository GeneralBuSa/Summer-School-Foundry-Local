import unittest

from app.domain import RetrievalResult, StoredChunk
from app.reranker import cross_encoder_score, rerank


class RerankerTests(unittest.TestCase):
    def test_exact_query_phrase_gets_bonus(self) -> None:
        self.assertGreater(cross_encoder_score("SQLite", "SQLite yerel veritabanıdır", 0.5), 0.5)

    def test_rerank_orders_by_query_overlap(self) -> None:
        weak = StoredChunk(1, "a.md", 0, "model ve sohbet", [1.0, 0.0], "m")
        strong = StoredChunk(2, "b.md", 0, "SQLite tek dosyalı veritabanıdır", [1.0, 0.0], "m")
        results = rerank("SQLite veritabanı", [RetrievalResult(weak, 0.8), RetrievalResult(strong, 0.7)])
        self.assertEqual(results[0].chunk.id, 2)
