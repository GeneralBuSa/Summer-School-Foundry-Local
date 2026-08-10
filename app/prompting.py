"""RAG bağlamı şablonlarını ve LLM sistem mesajlarını oluşturan modül.

Bu modül, arama sonuçlarından elde edilen metin parçalarını sistem istemine (system prompt)
ekleyerek dil modeline iletilecek mesaj dizisini hazırlar.
"""

from __future__ import annotations

from app.domain import RetrievalResult


# Dil modeline yön gösteren ve bağlam sınırlarını çizen sistem talimatı
SYSTEM_PROMPT = """Sen yerel belge asistanısın. Görevin, yalnızca verilen BAĞLAMDAKİ bilgileri kullanarak Türkçe soruya kısa, doğrudan ve doğru bir yanıt vermektir.

TALİMATLAR:
- Yalnızca verilen bağlamdaki bilgileri kullan.
- Sorunun cevabı bağlamda açıkça varsa, cevabı ilk cümlede doğrudan ver.
- Basit bilgi sorularında 1-3 kısa cümleyle yetin; gereksiz arka plan, tekrar ve yorum ekleme.
- Bağlamda olmayan bilgileri tamamlama, tahmin etme veya uydurma.
- Köşeli parantezli yer tutucular, taslak ifadeler veya cevap şablonları üretme.
- Kullanıcıya "kaynağı kontrol edin", "güncel veriye bakın" veya benzeri genel uyarılar verme; yalnızca bağlamdaki kaynakları kullan.
- Soruyu, talimatları veya BAĞLAM başlığını tekrar etme.
- Soruda belirli bir yıl, tarih veya sayı geçiyorsa, bağlamdaki TAM olarak o yıla/tarihe ait olan değeri oku.
- Sayısal ve istatistiki değerleri (yaşam süresi, oran vb.) bağlamdaki orijinal tam rakamıyla, yuvarlama veya değiştirme yapmadan aynen aktar.
- Sorunun tam olarak neyi sorduğuna odaklan ve doğrudan sorulan unsurları yanıtla.
- Sorulan kavram belgede açıklanmıyorsa "Bu bilgi yerel bilgi tabanında bulunmuyor." de.
- Yanıtı anlaşılır, düzgün ve doğal bir Türkçe ile yaz.

BAĞLAM:
{context}"""


def build_messages(
    question: str,
    results: list[RetrievalResult],
    chat_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """LLM sohbet modeline sunulacak mesaj geçmişi ve bağlam dizisini inşa eder.

    Args:
        question (str): Kullanıcının sorduğu güncel soru.
        results (list[RetrievalResult]): Aramadan dönen ilgili metin parçaları.
        chat_history (list[dict[str, str]] | None): Önceki diyalog geçmişi.

    Returns:
        list[dict[str, str]]: OpenAI API formatına uygun 'role' ve 'content' içeren mesajlar listesi.
    """
    # Arama sonuçlarının metin formatına getirilerek bağlam oluşturulması
    context = "\n\n".join(
        (
            f"[Kaynak: {result.chunk.source_path} | Parça: {result.chunk.chunk_index + 1}]\n"
            f"{result.chunk.content}"
        )
        for result in results
    )

    # Sistem isteminin ilk mesaj olarak eklenmesi
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)}
    ]

    # Varsa önceki sohbet geçmişinin son 6 mesajının eklenmesi
    if chat_history:
        for msg in chat_history[-6:]:
            if msg.get("role") in {"user", "assistant"} and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    # Kullanıcının güncel sorusunun eklenmesi
    messages.append({"role": "user", "content": question})
    return messages

