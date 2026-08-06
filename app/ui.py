"""Streamlit tabanlı yerel RAG arayüzü."""

from __future__ import annotations

# pyrefly: ignore [missing-import]
import streamlit as st
from pathlib import Path

from app.config import DATABASE_PATH, EMBEDDING_MODEL_ALIAS, KNOWLEDGE_BASE_DIR
from app.foundry import FoundryRuntime
from app.repository import SQLiteRepository
from app.ingest import run_ingest
from app.chat import answer_question


def main() -> None:
    st.set_page_config(page_title="Yerel RAG Asistanı", page_icon="🤖", layout="wide")

    # Streamlit "Made with Streamlit" footer'ını gizle ve sohbet giriş barına stil uygula
    st.markdown(
        """
        <style>
        footer {visibility: hidden;}

        /* Durdurma widget'ını görünmez yap */
        [data-testid="stStatusWidget"],
        .stStatusWidget {
            opacity: 0 !important;
            visibility: hidden !important;
        }

        /* Sohbet input alanına görece konumlandırma */
        [data-testid="stChatInput"] {
            position: relative !important;
        }

        /* Sohbeti Temizle (Trash) butonunu sağ üst header barına (Deploy butonunun soluna) taşı ve dikeyde ortala */
        .st-key-clear_chat_btn {
            position: fixed !important;
            top: 15px !important;
            right: 120px !important;
            z-index: 999999 !important;
            display: flex !important;
            align-items: center !important;
        }
        .st-key-clear_chat_btn button {
            border-radius: 8px !important;
            padding: 0 !important;
            width: 32px !important;
            height: 32px !important;
            min-height: 32px !important;
            background-color: transparent !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            font-size: 15px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1 !important;
            transition: all 0.2s ease !important;
        }
        .st-key-clear_chat_btn button:hover {
            background-color: rgba(239, 68, 68, 0.2) !important;
            border-color: #ef4444 !important;
            color: #ef4444 !important;
        }

        /* Anlık yanıt iptal butonunu gizli tut */
        .st-key-cancel_current_response_btn {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sağ üst header barına (Deploy yanına) sohbet temizleme butonu ekle
    if st.button("🗑️", key="clear_chat_btn", help="Sohbet geçmişini temizle"):
        st.session_state.messages = []
        st.rerun()

    # Sadece anlık sorunun yanıtını iptal eden gizli buton
    if st.button("durdur", key="cancel_current_response_btn"):
        if st.session_state.get("messages") and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages.pop()
        st.session_state.is_generating = False
        st.rerun()

    # Yanıt üretilirken giriş barının sağına canlı stop (⏹) butonunu ekle
    import streamlit.components.v1 as components
    components.html(
        """
        <script>
        (function() {
            var pdoc = window.parent.document;

            function handleStopBtn() {
                var chatInput = pdoc.querySelector('[data-testid=stChatInput]') || pdoc.querySelector('.stChatInput');
                if (!chatInput) return;

                var nativeSubmit = chatInput.querySelector('button');
                var isGenerating = pdoc.body.innerText.includes('Yanıt üretiliyor...') || 
                                   pdoc.querySelector('[data-testid=stSpinner]') !== null ||
                                   pdoc.querySelector('.stSpinner') !== null;

                var existingBtn = pdoc.getElementById('custom-chat-stop-btn');

                if (isGenerating) {
                    if (nativeSubmit) {
                        nativeSubmit.style.visibility = 'hidden';
                    }

                    var rect = nativeSubmit ? nativeSubmit.getBoundingClientRect() : chatInput.getBoundingClientRect();
                    var rightPos = (pdoc.documentElement.clientWidth - rect.right);
                    var topPos = rect.top;
                    var w = (rect && rect.width > 0) ? rect.width : 34;
                    var h = (rect && rect.height > 0) ? rect.height : 34;
                    var r = nativeSubmit ? window.getComputedStyle(nativeSubmit).borderRadius : '8px';

                    if (!existingBtn) {
                        var btn = pdoc.createElement('button');
                        btn.id = 'custom-chat-stop-btn';
                        btn.innerHTML = '⏹';
                        btn.title = 'Yanıt üretimini durdur';
                        btn.style.cssText = 'position:fixed; right:' + rightPos + 'px; top:' + topPos + 'px; z-index:9999999; width:' + w + 'px; height:' + h + 'px; border-radius:' + r + '; background-color:#ef4444; color:white; border:none; font-size:15px; cursor:pointer; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 4px rgba(0,0,0,0.3); pointer-events:auto;';

                        btn.onmouseover = function() { this.style.backgroundColor = '#dc2626'; };
                        btn.onmouseout = function() { this.style.backgroundColor = '#ef4444'; };

                        function triggerStop(e) {
                            if (e) { e.preventDefault(); e.stopPropagation(); }
                            var nativeStop = pdoc.querySelector('button[aria-label="Stop"]') ||
                                             pdoc.querySelector('button[title="Stop"]') ||
                                             pdoc.querySelector('[data-testid=stStatusWidget] button') ||
                                             pdoc.querySelector('.stStatusWidget button');
                            if (nativeStop) {
                                nativeStop.click();
                            }
                        }

                        btn.onmousedown = triggerStop;
                        btn.onclick = triggerStop;

                        pdoc.body.appendChild(btn);
                    } else {
                        existingBtn.style.right = rightPos + 'px';
                        existingBtn.style.top = topPos + 'px';
                    }
                } else {
                    if (nativeSubmit) {
                        nativeSubmit.style.visibility = 'visible';
                    }
                    if (existingBtn) {
                        existingBtn.remove();
                    }
                }
            }

            setInterval(handleStopBtn, 150);
            handleStopBtn();
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    # Streamlit "Clear cache" pop-up penceresindeki İngilizce metinleri Türkçe'ye çevir
    st.markdown(
        """
        <img src="data:," onerror="
            function translateModal() {
                var dialogs = document.querySelectorAll('div[role=\\'dialog\\'], [data-testid=\\'stDialog\\']');
                dialogs.forEach(function(dialog) {
                    var html = dialog.innerHTML;
                    if (html.includes('Clear cache') || html.includes('caches')) {
                        dialog.querySelectorAll('h2, h3, div, p, span, button').forEach(function(el) {
                            if (el.children.length === 0) {
                                var txt = el.textContent.trim();
                                if (txt === 'Clear cache' || txt === 'Clear cache?') el.textContent = 'Önbelleği Temizle';
                                else if (txt.includes('Are you sure you want to clear')) el.textContent = 'Uygulama önbelleğini temizlemek istediğinizden emin misiniz?';
                                else if (txt === 'Cancel') el.textContent = 'İptal';
                            }
                        });
                    }
                });
            }
            new MutationObserver(translateModal).observe(document.body, {childList: true, subtree: true});
        " style="display:none">
        """,
        unsafe_allow_html=True,
    )

    st.title("🤖 Yerel RAG Belge Asistanı")
    st.markdown("Dokümanlarınızı yerelde indeksleyin, güvenle Türkçe yanıtlar alın.")

    repository = SQLiteRepository(DATABASE_PATH)
    repository.initialize()

    # Yan panel: İndeksleme ve Belge Yükleme
    with st.sidebar:
        st.header("Belge Yönetimi")
        uploaded_files = st.file_uploader(
            "Yeni Belge Yükle (.md, .txt, .pdf, .docx)",
            type=["md", "txt", "pdf", "docx", "xlsx", "csv"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
            for uploaded_file in uploaded_files:
                # Tarayıcıdan gelen dosya adını bilgi tabanı dışına taşmasına
                # izin vermeden normalize et.
                if not safe_name or Path(safe_name).suffix.lower() not in {".md", ".txt", ".pdf", ".docx", ".xlsx", ".csv"}:
                    st.error(f"Desteklenmeyen veya geçersiz dosya adı: {uploaded_file.name}")
                    continue
                file_path = KNOWLEDGE_BASE_DIR / safe_name
                file_path.write_bytes(uploaded_file.getbuffer())
            st.session_state.new_files_uploaded = True
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
        # İndeksleme Tetikleme
        sync_needed = "new_files_uploaded" in st.session_state and st.session_state.new_files_uploaded
        if sync_needed or st.button("Bilgi Tabanını İndeksle / Güncelle", type="primary"):
            with st.spinner("İndeks kontrol ediliyor..."):
                try:
                    with FoundryRuntime() as runtime:
                        summary = run_ingest(repository, runtime)
                        if summary.indexed_documents > 0:
                            st.success(
                                f"İndekslendi: {summary.indexed_documents} yeni/güncellenen belge ({summary.chunk_count} parça) işlendi."
                            )
                        else:
                            st.info("🟢 Bilgi tabanı tamamen güncel, yeni belge yok.")
                        st.session_state.new_files_uploaded = False
                except Exception as exc:
                    st.error(f"İndeksleme hatası: {exc}")

        st.divider()
        st.header("Arama Ayarları")
        top_k_param = st.slider("Top-K Parça Sayısı", min_value=1, max_value=10, value=3, step=1)
        min_score_param = st.slider("Min Benzerlik Eşiği", min_value=0.0, max_value=1.0, value=0.35, step=0.05)
        alpha_param = st.slider("Vektör Ağırlığı (Alpha)", min_value=0.0, max_value=1.0, value=0.7, step=0.05, help="1.0 = Sadece Vektör, 0.0 = Sadece BM25")

        st.divider()
        st.header("Belge Önizleme")
        is_generating = st.session_state.get("is_generating", False)
        btn_help = (
            "⚠️ Yanıt üretimi devam ederken belge önizlemesi kullanılamaz."
            if is_generating
            else "Seçilen belgenin metnini görüntüle."
        )

        if KNOWLEDGE_BASE_DIR.exists():
            kb_files = sorted([f.relative_to(KNOWLEDGE_BASE_DIR).as_posix() for f in KNOWLEDGE_BASE_DIR.rglob("*") if f.is_file() and not f.name.startswith(".")])
            if kb_files:
                selected_rel_path = st.selectbox("İçeriğini İncele", kb_files)
                if selected_rel_path:
                    file_path = KNOWLEDGE_BASE_DIR / selected_rel_path
                    if not file_path.exists():
                        st.error("Belge artık mevcut değil; listeyi yenileyin.")
                    else:
                        if st.button("Belgeyi Gör", disabled=is_generating, help=btn_help):
                            try:
                                from app.document_loader import _read_file_content
                                st.session_state.preview_content = _read_file_content(file_path)
                                st.session_state.preview_file = selected_rel_path
                            except Exception as exc:
                                st.error(f"Belge okunamadı: {exc}")

                if st.session_state.get("preview_content"):
                    st.text_area(f"{st.session_state.get('preview_file')} Metni", st.session_state.preview_content, height=280)
                    if st.button("❌ Önizlemeyi Kapat"):
                        st.session_state.preview_content = None
                        st.session_state.preview_file = None
                        st.rerun()

        # Sohbet Raporu Dışa Aktarma
        if "messages" in st.session_state and st.session_state.messages:
            st.divider()
            st.header("📥 Rapor Dışa Aktar")
            report_md = "# Yerel RAG Sohbet Raporu\n\n"
            for m in st.session_state.messages:
                role_title = "👤 Kullanıcı" if m["role"] == "user" else "🤖 Asistan"
                report_md += f"### {role_title}\n{m['content']}\n\n"
                if "sources" in m and m["sources"]:
                    report_md += "**Kullanılan Kaynaklar:**\n"
                    for s in m["sources"]:
                        report_md += f"- {s['source']} (Parça {s['chunk']}, Skor: {s['score']:.2f})\n"
                    report_md += "\n"

            st.download_button(
                label="📥 Sohbet Raporunu İndir (.md)",
                data=report_md,
                file_name="rag_sohbet_raporu.md",
                mime="text/markdown",
            )

        # Açılır menülerin ekran altında kesilmesini önlemek için alt boşluk
        st.markdown("<div style='height: 250px;'></div>", unsafe_allow_html=True)

    # Ana Alan: Sohbet Arayüzü
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("Kullanılan Kaynaklar"):
                    for src in msg["sources"]:
                        st.markdown(f"- **{src['source']}** (Parça {src['chunk']}, Benzerlik: `{src['score']:.2f}`)")

    query = st.chat_input("Belgeleriniz hakkında soru sorun...", disabled=st.session_state.get("is_generating", False))

    if query:
        st.session_state.is_generating = True
        st.session_state.messages.append({"role": "user", "content": query})
        st.rerun()

    if st.session_state.get("is_generating", False) and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        latest_query = st.session_state.messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.status("Yanıt üretiliyor...", expanded=True):
                try:
                    runtime = _get_runtime()
                    history = st.session_state.messages[:-1]
                    answer = answer_question(
                        latest_query,
                        repository,
                        runtime,
                        chat_history=history,
                        top_k=top_k_param,
                        min_similarity_score=min_score_param,
                        alpha=alpha_param,
                    )
                    st.write(answer.text)

                    sources_data = []
                    if answer.sources:
                        with st.expander("Kullanılan Kaynaklar"):
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
                finally:
                    st.session_state.is_generating = False
                    st.rerun()


# Modelleri bellekte kalıcı tut; her soruda yeniden yüklenmesini engelle
@st.cache_resource(show_spinner=False)
def _get_runtime() -> FoundryRuntime:
    """FoundryRuntime'ı bir kez oluştur ve bellekte tut."""
    rt = FoundryRuntime()
    rt.start()
    return rt


if __name__ == "__main__":
    main()

