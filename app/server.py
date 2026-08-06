"""FastAPI tabanlı yerel RAG REST API sunucusu.

Bu modül, istemci (frontend veya diğer servisler) ile yerel RAG (Retrieval-Augment Generation)
motoru arasında köprü kuran RESTful API uç noktalarını (endpoints) barındırır.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import DATABASE_PATH, EMBEDDING_MODEL_ALIAS, KNOWLEDGE_BASE_DIR, MIN_SIMILARITY_SCORE, TOP_K
from app.foundry import FoundryRuntime
from app.repository import SQLiteRepository
from app.ingest import run_ingest
from app.chat import answer_question
from app.document_loader import _read_file_content

# FastAPI uygulama örneğinin başlık ve sürüm bilgisi ile başlatılması
app = FastAPI(title="Yerel RAG Asistanı API", version="1.0.0")

# Next.js ön yüzü ve harici istemciler için Cross-Origin Resource Sharing (CORS) izinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vektör veri veritabanı deposunun başlatılması
repository = SQLiteRepository(DATABASE_PATH)
repository.initialize()

# Foundry çalışma zamanı örneği için singleton önbellek değişkeni
_runtime_instance: Optional[FoundryRuntime] = None


def get_runtime() -> FoundryRuntime:
    """Foundry Runtime örneğini döndürür veya yoksa oluşturup başlatır (Singleton Deseni).

    Returns:
        FoundryRuntime: Başlatılmış Foundry çalışma zamanı nesnesi.
    """
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = FoundryRuntime()
        _runtime_instance.start()
    return _runtime_instance


class ChatMessage(BaseModel):
    """Sohbet geçmişindeki tek bir mesajı temsil eden veri modeli."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Sohbet API uç noktası için istek (request) veri modeli."""
    question: str
    chat_history: Optional[List[ChatMessage]] = None
    top_k: int = TOP_K
    min_similarity_score: float = MIN_SIMILARITY_SCORE
    alpha: float = 0.7


class IngestRequest(BaseModel):
    """İndeksleme API uç noktası için istek parametre modeli."""
    force_reindex: bool = False


@app.get("/api/health")
def health_check():
    """Sunucu ve kullanılan embedding modelinin durumunu kontrol eden uç nokta."""
    return {"status": "ok", "embedding_model": EMBEDDING_MODEL_ALIAS}


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Kullanıcının sorusuna RAG mimarisi üzerinden yanıt üreten uç nokta.

    Args:
        req (ChatRequest): Kullanıcı sorusu, sohbet geçmişi ve arama parametreleri.

    Returns:
        dict: Yanıt metni, yararlanılan kaynaklar ve bilginin doğrulanma (grounded) durumu.
    """
    try:
        runtime = get_runtime()
        history = [m.model_dump() for m in req.chat_history] if req.chat_history else []
        ans = answer_question(
            req.question,
            repository,
            runtime,
            chat_history=history,
            top_k=req.top_k,
            min_similarity_score=req.min_similarity_score,
            alpha=req.alpha,
        )

        sources_data = []
        if ans.sources:
            for s in ans.sources:
                sources_data.append({
                    "source": s.chunk.source_path,
                    "chunk": s.chunk.chunk_index + 1,
                    "score": s.score,
                })

        return {
            "text": ans.text,
            "sources": sources_data,
            "grounded": ans.grounded,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sunucu hatası: {exc}")


@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Bilgi tabanına (knowledge base) yeni belgeler yükleyen uç nokta.

    Args:
        files (List[UploadFile]): Yüklenecek dosya listesi.

    Returns:
        dict: Yüklenen dosya adları ve işlem durum mesajı.
    """
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    saved_files = []
    allowed_extensions = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".csv"}

    for uploaded_file in files:
        safe_name = os.path.basename(uploaded_file.filename or "")
        ext = Path(safe_name).suffix.lower()
        if not safe_name or ext not in allowed_extensions:
            continue

        file_path = KNOWLEDGE_BASE_DIR / safe_name
        content = await uploaded_file.read()
        file_path.write_bytes(content)
        saved_files.append(safe_name)

    return {"message": f"{len(saved_files)} belge eklendi.", "saved_files": saved_files}


@app.post("/api/ingest")
def ingest_endpoint(req: IngestRequest):
    """Bilgi tabanındaki belgeleri okuyup vektör veritabanına indeksleyen uç nokta.

    Args:
        req (IngestRequest): Yeniden indeksleme zorlama parametresi.

    Returns:
        dict: İndekslenen, atlanan belge sayıları ve üretilen chunk sayısı özeti.
    """
    try:
        runtime = get_runtime()
        summary = run_ingest(repository, runtime, force_reindex=req.force_reindex)
        return {
            "indexed_documents": summary.indexed_documents,
            "chunk_count": summary.chunk_count,
            "skipped_documents": summary.skipped_documents,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"İndeksleme hatası: {exc}")


@app.get("/api/documents")
def list_documents():
    """Bilgi tabanında mevcut tüm belgelerin listesini döndüren uç nokta."""
    if not KNOWLEDGE_BASE_DIR.exists():
        return {"documents": []}
    files = sorted([
        f.relative_to(KNOWLEDGE_BASE_DIR).as_posix()
        for f in KNOWLEDGE_BASE_DIR.rglob("*")
        if f.is_file() and not f.name.startswith(".")
    ])
    return {"documents": files}


@app.get("/api/preview")
def preview_document(file_path: str = Query(...)):
    """Seçilen bir belgenin metin içeriğini önizleme amacıyla okuyup döndüren uç nokta.

    Args:
        file_path (str): Önizlenecek belgenin bağıl yolu.

    Returns:
        dict: Belge yolu ve içerik metni.
    """
    target_path = KNOWLEDGE_BASE_DIR / file_path
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
    try:
        content = _read_file_content(target_path)
        return {"file_path": file_path, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Belge okunamadı: {exc}")

