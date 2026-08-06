"""Uygulamanın tek merkezden yönetilen yapılandırma sabitleri.

Bu modül, dosya yolları, model takma adları (aliases), metin parçalama (chunking) boyutları
ve varsayılan RAG arama eşik değerlerini barındırır.
"""

from pathlib import Path

# Proje ana dizini ve veri yollarının tanımlanması
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "rag.db"

# Foundry Local SDK uygulama adı ve varsayılan model tanımları
APP_NAME = "summer_school_foundry_local_rag"
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"
CHAT_MODEL_ALIAS = "phi-3.5-mini"  # Yüksek başarımlı yerel CPU sohbet modeli

# Metin parçalama (chunking) ve arama ayarları
CHUNK_SIZE = 800  # Parça başı maksimum karakter sayısı
CHUNK_OVERLAP = 120  # Parçalar arası karakter örtüşme miktarı
TOP_K = 3  # Her sorguda getirilecek en alakalı parça sayısı
MIN_SIMILARITY_SCORE = 0.35  # Yanıt üretmek için gereken minimum benzerlik skoru

# Varsayılan bilgi bulunamadı yanıtı ve desteklenen dosya uzantıları
NO_ANSWER_MESSAGE = "Bu bilgi yerel bilgi tabanında bulunmuyor."
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".csv"}

