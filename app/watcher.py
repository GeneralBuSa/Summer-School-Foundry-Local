"""knowledge_base klasörünü dinamik olarak izleyip dosya değişikliklerinde otomatik indekslemeyi tetikleyen modül.

Bu modül, `watchdog` kütüphanesini kullanarak bilgi tabanına yeni dosya eklendiğinde,
mevcut dosya güncellendiğinde veya silindiğinde otomatik re-index sürecini başlatır.
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Lock

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.config import KNOWLEDGE_BASE_DIR, SUPPORTED_SUFFIXES
from app.foundry import FoundryRuntime
from app.ingest import run_ingest
from app.repository import SQLiteRepository


class KnowledgeBaseHandler(FileSystemEventHandler):
    """Dosya sistemi olaylarını (oluşturma, değiştirme, silme) yakalayan olay işleyici sınıfı.

    Attributes:
        repository (SQLiteRepository): Veritabanı yönetim deposu.
    """

    def __init__(self, repository: SQLiteRepository):
        super().__init__()
        self.repository = repository
        self._lock = Lock()
        self._last_run = 0.0

    def _reindex(self) -> None:
        """Kilit (lock) mekanizması ile sık tetiklemeleri (debounce) önleyerek yeniden indekslemeyi yürütür."""
        with self._lock:
            now = time.monotonic()
            if now - self._last_run < 1.0:
                return
            self._last_run = now

        with FoundryRuntime() as runtime:
            summary = run_ingest(self.repository, runtime)
            print(f"Otomatik indeksleme: {summary.indexed_documents} belge, {summary.chunk_count} parça.")

    def _handle(self, event) -> None:
        """Desteklenen uzantıya sahip dosya olaylarını filtreler ve yeniden indekslemeyi çağırır."""
        if not event.is_directory and Path(event.src_path).suffix.lower() in SUPPORTED_SUFFIXES:
            self._reindex()

    on_created = _handle
    on_modified = _handle
    on_deleted = _handle


def watch_forever(repository: SQLiteRepository) -> None:
    """Bilgi tabanı klasörünü kesintisiz (döngü hâlinde) izleyen ana süreç fonksiyonu.

    Args:
        repository (SQLiteRepository): Kullanılacak veritabanı deposu.
    """
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    repository.initialize()
    observer = Observer()
    observer.schedule(KnowledgeBaseHandler(repository), str(KNOWLEDGE_BASE_DIR), recursive=True)
    observer.start()
    print(f"Klasör izleniyor: {KNOWLEDGE_BASE_DIR}. Durdurmak için Ctrl+C.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()

