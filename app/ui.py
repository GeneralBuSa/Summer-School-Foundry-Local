"""Streamlit tabanlı yerel RAG arayüzü."""

from __future__ import annotations

import streamlit as st
from pathlib import Path

from app.config import DATABASE_PATH, EMBEDDING_MODEL_ALIAS, KNOWLEDGE_BASE_DIR
from app.foundry import FoundryRuntime
from app.repository import SQLiteRepository
from app.ingest import run_ingest
from app.chat import answer_question


def main() -> None:
    st.set_page_config(page_title="Yerel RAG Asistanı", page_icon="🤖", layout="wide")
    st.title("🤖 Yerel RAG Belge Asistanı")
    st.markdown("Dokümanlarınızı yerelde indeksleyin, güvenle ve kaynaklı Türkçe yanıtlar alın.")

    repository = SQLiteRepository(DATABASE_PATH)
    repository.initialize()

    # Yan panel: İndeksleme ve Belge Yükleme
    with st.sidebar:
        st.header("⚙️ Belge Yönetimi")
        uploaded_files = st.file_uploader(
            "Yeni Belge Yükle (.md, .txt, .pdf, .docx)",
            type=["md", "txt", "pdf", "docx"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
            for uploaded_file in uploaded_files:
                # Tarayıcıdan gelen dosya adını bilgi tabanı dışına taşmasına
                # izin vermeden normalize et.
                safe_name = Path(uploaded_file.name).name
                if not safe_name or Path(safe_name).suffix.lower() not in {".md", ".txt", ".pdf", ".docx"}:
                    st.error(f"Desteklenmeyen veya geçersiz dosya adı: {uploaded_file.name}")
                    continue
                file_path = KNOWLEDGE_BASE_DIR / safe_name
                file_path.write_bytes(uploaded_file.getbuffer())
            st.success(f"{len(uploaded_files)} belge knowledge_base klasörüne eklendi!")

        # Model/İndeks Uyumluluk Kontrolü
        from app.ingest import check_model_compatibility
        stale_model = check_model_compatibility(repository)
        if stale_model:
            st.error(
                f"⚠️ İndeks uyumsuz embedding modeli içeriyor: **{stale_model}**. "
                f"Aktif model: **{EMBEDDING_MODEL_ALIAS}**. Tüm belgeler yeniden indekslenmelidir."
            )
            if st.button("🔁 Zorunlu Yeniden İndeksle", type="primary"):
                with st.spinner("Tüm belgeler yeniden indeksleniyor..."):
                    try:
                        with FoundryRuntime() as runtime:
                            summary = run_ingest(repository, runtime, force_reindex=True)
                            st.success(
                                f"Yeniden indeksleme tamamlandı: {summary.indexed_documents} belge ({summary.chunk_count} parça)."
                            )
                            st.rerun()
                    except Exception as exc:
                        st.error(f"Yeniden indeksleme hatası: {exc}")
        else:
            # Otomatik Senkronizasyon (Auto-ingest) — model uyumluyken çalışır
            auto_sync = st.checkbox("⚡ Otomatik Senkronizasyon", value=True)
            if auto_sync or st.button("🔄 Bilgi Tabanını Yeniden İndeksle", type="primary"):
                with st.spinner("İndeks kontrol ediliyor..."):
                    try:
                        with FoundryRuntime() as runtime:
                            summary = run_ingest(repository, runtime)
                            if summary.indexed_documents > 0:
                                st.success(
                                    f"Otomatik İndekslendi: {summary.indexed_documents} yeni/güncellenen belge ({summary.chunk_count} parça) işlendi."
                                )
                            else:
                                st.caption("🟢 Bilgi tabanı tamamen güncel.")
                    except Exception as exc:
                        st.error(f"İndeksleme hatası: {exc}")

    # Ana Alan: Sohbet Arayüzü
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 Kullanılan Kaynaklar"):
                    for src in msg["sources"]:
                        st.markdown(f"- **{src['source']}** (Parça {src['chunk']}, Benzerlik: `{src['score']:.2f}`)")

    query = st.chat_input("Belgeleriniz hakkında soru sorun...")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        with st.chat_message("assistant"):
            with st.spinner("Yanıt üretiliyor..."):
                try:
                    with FoundryRuntime() as runtime:
                        history = st.session_state.messages[:-1]
                        answer = answer_question(query, repository, runtime, chat_history=history)
                        st.write(answer.text)
                        
                        sources_data = []
                        if answer.sources:
                            with st.expander("📚 Kullanılan Kaynaklar"):
                                for res in answer.sources:
                                    src_info = {
                                        "source": res.chunk.source_path,
                                        "chunk": res.chunk.chunk_index + 1,
                                        "score": res.score,
                                    }
                                    sources_data.append(src_info)
                                    st.markdown(
                                        f"- **{res.chunk.source_path}** (Parça {res.chunk.chunk_index + 1}, "
                                        f"Benzerlik: `{res.score:.2f}`)"
                                    )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer.text, "sources": sources_data}
                        )
                except Exception as exc:
                    st.error(f"Yanıt üretme hatası: {exc}")


if __name__ == "__main__":
    main()
