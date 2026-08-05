"""RAG bağlamını ve model talimatlarını oluşturur."""

from __future__ import annotations

from app.domain import RetrievalResult


SYSTEM_PROMPT = """Sen yerel belge asistanısın. Görevin bağlamdaki bilgiyi kullanarak Türkçe soruya 1-2 cümlelik kısa ve doğrudan bir yanıt vermektir.

TALİMATLAR:
- Yalnızca bağlamda verilen bilgiyi kullan.
- Sorulan kavram belgede açıklanmıyorsa doğrudan "Bu bilgi yerel bilgi tabanında bulunmuyor." de.
- Yanıtına kaynak ekle: [Kaynak: dosya_adı, Parça: X]
- Liste, numara, madde işareti, "0:" öneki veya özet başlıkları kesinlikle ekleme. Doğrudan tek paragraf halinde kısa yanıt ver.

BAĞLAM:
{context}"""


def build_messages(
    question: str,
    results: list[RetrievalResult],
    chat_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    context = "\n\n".join(
        (
            f"[Kaynak: {result.chunk.source_path} | Parça: {result.chunk.chunk_index + 1}]\n"
            f"{result.chunk.content}"
        )
        for result in results
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)}
    ]
    if chat_history:
        # Son sohbet geçmişinden en fazla son 6 mesajı dahil et
        for msg in chat_history[-6:]:
            if msg.get("role") in {"user", "assistant"} and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})
    return messages
