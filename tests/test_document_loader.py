import tempfile
import unittest
import csv
from pathlib import Path

from app.document_loader import _read_file_content, discover_documents
from app.domain import SourceDocument


class DocumentLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_read_txt_and_md_files(self) -> None:
        txt_file = self.dir_path / "test.txt"
        txt_file.write_text("Merhaba Dünya", encoding="utf-8")
        self.assertEqual(_read_file_content(txt_file), "Merhaba Dünya")

        md_file = self.dir_path / "test.md"
        md_file.write_text("# Başlık\nİçerik", encoding="utf-8")
        self.assertEqual(_read_file_content(md_file), "# Başlık\nİçerik")

    def test_discover_documents_ignores_unsupported_extensions(self) -> None:
        (self.dir_path / "doc.txt").write_text("Geçerli metin", encoding="utf-8")
        (self.dir_path / "doc.exe").write_text("İkili dosya", encoding="utf-8")
        docs = discover_documents(self.dir_path)
        self.assertEqual(len(docs), 1)
        self.assertTrue(docs[0].source_path.endswith("doc.txt"))

    def test_corrupted_pdf_file_raises_error(self) -> None:
        corrupted_pdf = self.dir_path / "bozuk.pdf"
        corrupted_pdf.write_bytes(b"%PDF-1.4 bozuk icerik veri akisi yok")
        with self.assertRaises(ValueError) as ctx:
            discover_documents(self.dir_path)
        self.assertIn("Belge okuma hatası", str(ctx.exception))

    def test_empty_files_are_skipped(self) -> None:
        empty_file = self.dir_path / "bos.txt"
        empty_file.write_text("   \n  ", encoding="utf-8")
        docs = discover_documents(self.dir_path)
        self.assertEqual(len(docs), 0)

    def test_csv_is_read_as_rows(self) -> None:
        csv_file = self.dir_path / "table.csv"
        with csv_file.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows([["Ad", "Değer"], ["RAG", "yerel"]])
        text = _read_file_content(csv_file)
        self.assertIn("Ad | Değer", text)
        self.assertIn("Ad: RAG", text)
        self.assertIn("Değer: yerel", text)

    def test_xlsx_is_read_as_sheet_rows(self) -> None:
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl kurulu değil")
        xlsx_file = self.dir_path / "table.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Bilgi"
        sheet.append(["Ad", "Değer"])
        sheet.append(["RAG", "yerel"])
        workbook.save(xlsx_file)
        workbook.close()
        text = _read_file_content(xlsx_file)
        self.assertIn("Sayfa: Bilgi", text)
        self.assertIn("RAG | yerel", text)


if __name__ == "__main__":
    unittest.main()
