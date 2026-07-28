import tempfile
import unittest
from pathlib import Path

from app.repository import SQLiteRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = SQLiteRepository(Path(self.temp_dir.name) / "rag.db")
        self.repository.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_replace_document_is_current_and_does_not_duplicate(self) -> None:
        self.repository.replace_document(
            "knowledge_base/bilgi.md",
            "hash-v1",
            ["ilk parça", "ikinci parça"],
            [[1.0, 0.0], [0.0, 1.0]],
            "test-model",
        )
        self.assertTrue(self.repository.is_current("knowledge_base/bilgi.md", "hash-v1", "test-model"))
        self.assertEqual(len(self.repository.get_chunks("test-model")), 2)

        self.repository.replace_document(
            "knowledge_base/bilgi.md",
            "hash-v2",
            ["yeni parça"],
            [[0.5, 0.5]],
            "test-model",
        )
        stored = self.repository.get_chunks("test-model")
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].content, "yeni parça")
        self.assertFalse(self.repository.is_current("knowledge_base/bilgi.md", "hash-v1", "test-model"))
