"""Foundry Local SDK model yaşam döngüsü sarmalayıcısı.

Bu modül, Foundry Local SDK aracılığıyla LLM sohbet modellerinin ve embedding modellerinin
yüklenmesi, GPU/CPU varyant seçimi ve bellekten çıkarılması (load/unload) süreçlerini yönetir.
"""

from __future__ import annotations

import time
from typing import Any

from foundry_local_sdk import Configuration, FoundryLocalManager

from app.config import APP_NAME, CHAT_MODEL_ALIAS, EMBEDDING_MODEL_ALIAS


class FoundryRuntimeError(RuntimeError):
    """Foundry Local çalışma zamanında (SDK, model yükleme vb.) oluşan hataları temsil eden özel sınıf."""


class FoundryRuntime:
    """Foundry Local model istemcilerini (Embedding ve Chat) yöneten çalışma zamanı sınıfı."""

    def __init__(self) -> None:
        self._manager: Any | None = None
        self._embedding_model: Any | None = None
        self._chat_model: Any | None = None

    def start(self) -> None:
        """SDK yöneticisini (FoundryLocalManager) uygulama başına bir kez başlatır.

        Raises:
            FoundryRuntimeError: SDK başlatma esnasında beklenmeyen bir hata meydana gelirse.
        """
        if self._manager is not None:
            return
        try:
            if getattr(FoundryLocalManager, "instance", None) is None:
                FoundryLocalManager.initialize(Configuration(app_name=APP_NAME))
            self._manager = FoundryLocalManager.instance
            # İndirilmiş execution provider'lar için kaydı çevrimdışı modda günceller
            try:
                self._manager.download_and_register_eps()
            except Exception:
                pass
        except Exception as exc:
            raise FoundryRuntimeError(
                "Foundry Local başlatılamadı. SDK kurulumunu kontrol edin."
            ) from exc

    def _get_and_load_model(self, alias: str) -> Any:
        """Katalogdan takma ada (alias) göre modeli bulur, en uygun (GPU/önbellek) varyantı seçer ve yükler.

        Args:
            alias (str): Yüklenecek modelin takma adı (örn. 'bge-m3' veya 'phi-4').

        Returns:
            Any: Yüklenmiş ve kullanıma hazır model nesnesi.

        Raises:
            FoundryRuntimeError: Model bulunamazsa veya yükleme başarısız olursa.
        """
        self.start()
        assert self._manager is not None
        last_error: Exception | None = None

        # Geçici SDK bağlantı hatalarına karşı maksimum 2 deneme
        for attempt in range(2):
            try:
                model = self._manager.catalog.get_model(alias)
                if model is None:
                    raise FoundryRuntimeError(
                        f"Model katalogda bulunamadı: {alias}. Kullanılabilir model alias'larını kontrol edin."
                    )
                # İndirilmemiş GPU varyantı yerine yerel önbellekteki (cached) GPU veya CPU varyantını öncelikle seç
                cached_gpu = next(
                    (
                        variant
                        for variant in model.variants
                        if variant.info.cached
                        and variant.info.runtime is not None
                        and str(variant.info.runtime.device_type).upper() in {"GPU", "CUDA", "DIRECTML", "DML"}
                    ),
                    None,
                )
                cached_any = next(
                    (variant for variant in model.variants if variant.info.cached),
                    None,
                )

                selected_variant = cached_gpu or cached_any
                if selected_variant is not None:
                    model.select_variant(selected_variant)

                # Yalnızca önbellekte yoksa indirmeyi dene
                if selected_variant is not None and not getattr(selected_variant.info, "cached", False):
                    try:
                        model.download()
                    except Exception:
                        pass
                model.load()
                return model
            except FoundryRuntimeError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(2)
        raise FoundryRuntimeError(f"Model indirilemedi veya yüklenemedi: {alias}") from last_error

    def embedding_client(self) -> Any:
        """Embedding modeli istemci nesnesini temin eder (gerekirse tembel yükler).

        Returns:
            Any: Embedding üretimi için istemci nesnesi.
        """
        if self._embedding_model is None:
            self._embedding_model = self._get_and_load_model(EMBEDDING_MODEL_ALIAS)
        return self._embedding_model.get_embedding_client()

    def chat_client(self) -> Any:
        """Sohbet (Chat LLM) modeli istemci nesnesini temin eder (gerekirse tembel yükler).

        Returns:
            Any: Metin tamamlama/sohbet için istemci nesnesi.
        """
        if self._chat_model is None:
            self._chat_model = self._get_and_load_model(CHAT_MODEL_ALIAS)
        return self._chat_model.get_chat_client()

    def close(self) -> None:
        """Yüklenmiş tüm modelleri bellekten güvenle çıkarır ve kaynakları serbest bırakır."""
        for attribute in ("_chat_model", "_embedding_model"):
            model = getattr(self, attribute)
            if model is None:
                continue
            try:
                model.unload()
            finally:
                setattr(self, attribute, None)

    def __enter__(self) -> "FoundryRuntime":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

