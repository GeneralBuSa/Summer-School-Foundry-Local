"""Uygulamanın tek merkezden yönetilen yapılandırması."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "rag.db"

APP_NAME = "summer_school_foundry_local_rag"
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"
# Küçük Qwen modeli yalnızca SDK doğrulaması için yeterliydi; RAG cevap
# kalitesi için daha güçlü, CPU uyumlu Phi modeli kullanılır.
CHAT_MODEL_ALIAS = "phi-3.5-mini"  # Katalogda bulunan ve bu makinede doğrulanan CPU modeli

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 3
MIN_SIMILARITY_SCORE = 0.35
NO_ANSWER_MESSAGE = "Bu bilgi yerel bilgi tabanında bulunmuyor."
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".csv"}
