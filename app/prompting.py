"""RAG bağlamını ve model talimatlarını oluşturur."""

from __future__ import annotations

from app.domain import RetrievalResult


SYSTEM_PROMPT = """Sen yerel belge asistanısın. Yalnızca aşağıdaki BAĞLAM içinde bulunan
bilgiye dayanarak akıcı ve doğal bir Türkçe ile cevap ver.

Kurallar:
1. Yanıtında bağlamdaki bilgileri kullan ve kullandığın bilginin kaynağını metin içinde [Kaynak: dosya_adı, Parça: X] şeklinde açıkça belirt.
2. Bağlam soruyu cevaplamak için yeterli değilse tam olarak “Bu bilgi yerel bilgi tabanında bulunmuyor.” de.
3. Bağlamda olmayan ayrıntıları tahmin etme veya uydurma.

BAĞLAM:
{context}"""


def build_messages(
    question: str,
    results: list[RetrievalResult],
    chat_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    context = "\n\n".join(
        (
            f"[Kaynak: {result.chunk.source_path} | Parça: {result.chunk.chunk_index + 1} "
            f"| Skor: {result.score:.2f}]\n{result.chunk.content}"
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
