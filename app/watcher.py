"""knowledge_base klasörünü izleyip değişikliklerde indekslemeyi tetikler."""

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
    def __init__(self, repository: SQLiteRepository):
        super().__init__()
        self.repository = repository
        self._lock = Lock()
        self._last_run = 0.0

    def _reindex(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now - self._last_run < 1.0:
                return
            self._last_run = now
        with FoundryRuntime() as runtime:
            summary = run_ingest(self.repository, runtime)
            print(f"Otomatik indeksleme: {summary.indexed_documents} belge, {summary.chunk_count} parça.")

    def _handle(self, event) -> None:
        if not event.is_directory and Path(event.src_path).suffix.lower() in SUPPORTED_SUFFIXES:
            self._reindex()

    on_created = _handle
    on_modified = _handle
    on_deleted = _handle


def watch_forever(repository: SQLiteRepository) -> None:
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
