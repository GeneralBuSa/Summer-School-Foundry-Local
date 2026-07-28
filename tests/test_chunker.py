import unittest

from app.chunker import chunk_text


class ChunkerTests(unittest.TestCase):
    def test_empty_text_has_no_chunks(self) -> None:
        self.assertEqual(chunk_text("   \n", 100, 10), [])

    def test_chunks_are_non_empty_and_progress(self) -> None:
        text = "Birinci cümle. " * 150
        chunks = chunk_text(text, 120, 20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks[:-1]))

    def test_invalid_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("metin", 10, 10)

    def test_headers_keep_sections_together(self) -> None:
        chunks = chunk_text("# Birinci\n\nİçerik A\n\n# İkinci\n\nİçerik B", 100, 10)
        self.assertEqual(len(chunks), 2)
        self.assertIn("İçerik A", chunks[0])
        self.assertIn("İçerik B", chunks[1])
