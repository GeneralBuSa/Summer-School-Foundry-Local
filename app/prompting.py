"""RAG bağlamını ve model talimatlarını oluşturur."""

from __future__ import annotations

from app.domain import RetrievalResult


SYSTEM_PROMPT = """Sen yerel belge asistanısın. Görevin verilen BAĞLAMDAKİ bilgileri kullanarak Türkçe soruya doğrudan, eksiksiz ve soruya tam odaklı bir yanıt vermektir.

TALİMATLAR:
- Yalnızca verilen bağlamdaki bilgileri kullan.
- Soruda belirli bir yıl, tarih veya sayı geçiyorsa, bağlamdaki TAM olarak o yıla/tarihe ait olan değeri oku.
- Sayısal ve istatistiki değerleri (yaşam süresi, oran vb.) bağlamdaki orijinal tam rakamıyla, yuvarlama veya değiştirme yapmadan aynen aktar.
- Sorunun tam olarak neyi sorduğuna odaklan ve doğrudan sorulan unsurları yanıtla.
- Sorulan kavram belgede açıklanmıyorsa "Bu bilgi yerel bilgi tabanında bulunmuyor." de.
- Yanıtı anlaşılır, düzgün ve öz bir Türkçe ile özetle.

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
