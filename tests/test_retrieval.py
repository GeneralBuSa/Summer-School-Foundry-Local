import unittest

from app.domain import StoredChunk
from app.retrieval import cosine_similarity, retrieve_top_chunks


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
