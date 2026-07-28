"""Foundry Local SDK model yaşam döngüsü için ince sarmalayıcı."""

from __future__ import annotations

import time
from typing import Any

from foundry_local_sdk import Configuration, FoundryLocalManager

from app.config import APP_NAME, CHAT_MODEL_ALIAS, EMBEDDING_MODEL_ALIAS


class FoundryRuntimeError(RuntimeError):
    """Kullanıcıya anlaşılır Foundry Local çalışma zamanı hatası verir."""


class FoundryRuntime:
    def __init__(self) -> None:
        self._manager: Any | None = None
        self._embedding_model: Any | None = None
        self._chat_model: Any | None = None

    def start(self) -> None:
        """Çalışma sağlayıcılarını ve SDK yöneticisini uygulama başına bir kez hazırlar."""
        if self._manager is not None:
            return
        try:
            FoundryLocalManager.initialize(Configuration(app_name=APP_NAME))
            self._manager = FoundryLocalManager.instance
            # SDK, indirilmiş sağlayıcılar için bu çağrıyı güvenle atlar.
            self._manager.download_and_register_eps()
        except Exception as exc:  # SDK farklı platform hatası türleri döndürebilir.
            raise FoundryRuntimeError(
                "Foundry Local başlatılamadı. İnternet bağlantısını ve SDK kurulumunu kontrol edin."
            ) from exc

    def _get_and_load_model(self, alias: str) -> Any:
        self.start()
        assert self._manager is not None
        last_error: Exception | None = None
        # Katalog isteği veya model önbelleği geçici olarak başarısız olursa bir
        # kez kısa beklemeyle tekrar dene. Sürekli döngüye girme.
        for attempt in range(2):
            try:
                model = self._manager.catalog.get_model(alias)
                if model is None:
                    raise FoundryRuntimeError(
                        f"Model katalogda bulunamadı: {alias}. Kullanılabilir model alias'larını kontrol edin."
                    )
                # Bu bilgisayarda güvenilir biçimde kullanılabilir sağlayıcı CPU'dur.
                # SDK bazen kullanılabilir olmayan GPU varyantını öncelikli seçebildiği
                # için, katalog CPU varyantı sunuyorsa onu açıkça seçiyoruz.
                cpu_variant = next(
                    (
                        variant
                        for variant in model.variants
                        if variant.info.runtime is not None
                        and str(variant.info.runtime.device_type).upper() == "CPU"
                    ),
                    None,
                )
                if cpu_variant is not None:
                    model.select_variant(cpu_variant)
                # Her başlangıçta çağrılır; internet yoksa veya önbellek mevcutsa çevrimdışı yükler.
                try:
                    model.download()
                except Exception:
                    pass  # Çevrimdışı durumda önbellekteki model doğrudan yüklenir.
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
        if self._embedding_model is None:
            self._embedding_model = self._get_and_load_model(EMBEDDING_MODEL_ALIAS)
        return self._embedding_model.get_embedding_client()

    def chat_client(self) -> Any:
        if self._chat_model is None:
            self._chat_model = self._get_and_load_model(CHAT_MODEL_ALIAS)
        return self._chat_model.get_chat_client()

    def close(self) -> None:
        """Yüklenmiş modelleri ters sırayla güvenle bellekten çıkarır."""
        for attribute in ("_chat_model", "_embedding_model"):
            model = getattr(self, attribute)
            if model is None:
                continue
            try:
                model.unload()
            finally:
                setattr(self, attribute, None)

    def __enter__(self) -> "FoundryRuntime":
        # Model ve execution provider yüklemesi lazy'dir. Böylece değişmemiş
        # belgelerin indekslemesinde veya boş indekste gereksiz başlangıç yoktur.
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
