import unittest

from app.domain import StoredChunk
from app.retrieval import cosine_similarity, has_confident_match, retrieve_top_chunks


def chunk(identifier: int, embedding: list[float]) -> StoredChunk:
    return StoredChunk(identifier, "knowledge_base/test.md", identifier, "metin", embedding, "model")


class RetrievalTests(unittest.TestCase):
    def test_cosine_similarity(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_retrieval_returns_best_chunks_first(self) -> None:
        results = retrieve_top_chunks(
            [1.0, 0.0], [chunk(1, [0.0, 1.0]), chunk(2, [0.9, 0.1]), chunk(3, [1.0, 0.0])], 2
        )
        self.assertEqual([result.chunk.id for result in results], [3, 2])

    def test_dimension_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            cosine_similarity([1.0], [1.0, 0.0])

    def test_alpha_changes_hybrid_weight(self) -> None:
        chunks = [chunk(1, [1.0, 0.0]), chunk(2, [0.0, 1.0])]
        semantic_first = retrieve_top_chunks([1.0, 0.0], chunks, 2, query_text="model", alpha=1.0)
        keyword_first = retrieve_top_chunks([1.0, 0.0], [
            StoredChunk(1, "a.md", 0, "başka bilgi", [1.0, 0.0], "model"),
            StoredChunk(2, "b.md", 0, "model model", [0.0, 1.0], "model"),
        ], 2, query_text="model", alpha=0.0)
        self.assertEqual(semantic_first[0].chunk.id, 1)
        self.assertEqual(keyword_first[0].chunk.id, 2)

    def test_unrelated_question_has_no_confident_match(self) -> None:
        chunks = [chunk(1, [1.0, 0.0])]
        self.assertFalse(has_confident_match("kuantum bilgisayar", [0.0, 1.0], chunks))
