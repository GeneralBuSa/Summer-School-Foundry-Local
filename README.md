# Summer School Foundry Local — Yerel RAG Belge Asistanı

Microsoft Foundry Local ile çalışan, yerel RAG (Retrieval-Augmented Generation) belge asistanı.

## Özellikler

- **Yerel Çalışma:** Model dosyaları ve gerekli çalışma bileşenleri indirildikten sonra cevap üretimi yerel yapılır. İlk model/katalog kontrolünde internet gerekebilir.
- **Hibrit Arama:** BM25 + vektör araması + yerel deterministic re-ranking.
- **Akıllı Parçalama:** Başlık ve paragraf yapısını koruyan semantic chunking.
- **Çoklu Format:** `.md`, `.txt`, `.pdf`, `.docx`, `.xlsx` ve `.csv` belge desteği. Taranmış PDF'ler için OCR fallback.
- **Sohbet Hafızası:** Önceki soruları hatırlayan çok turlu diyalog.
- **Web Arayüzü:** Streamlit tabanlı yerel web UI (belge yükleme, indeksleme, sohbet).
- **Otomatik Senkronizasyon:** `app watch` veya UI üzerinden belge değişikliklerinde otomatik indeksleme.
- **Kalite Ölçümü:** 25 soruluk golden test seti ile Hit Rate, MRR ve anahtar kelime raporlaması.
- **Model Uyumluluk Kontrolü:** Embedding modeli değiştiğinde kullanıcıya açık uyarı ve zorunlu yeniden indeksleme.

---

## Kurulum

### 1. Python Sanal Ortamı

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Foundry Local

```powershell
winget install Microsoft.FoundryLocal
```

İlk çalıştırmada modeller otomatik indirilir. Sonraki başlangıçlarda önbellekten yüklenir.

### 3. OCR Desteği (Opsiyonel — Taranmış PDF'ler İçin)

Taranmış (görüntü tabanlı) PDF'lerden metin çıkartmak için ek sistem kurulumu gerekir:

- **Tesseract OCR:** [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) adresinden indirin ve PATH'e ekleyin (`tur` dil paketi dahil).
- **Poppler:** [github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases/) adresinden indirin ve PATH'e ekleyin.

Metin katmanlı PDF'lerde OCR gerekmez; `pypdf` doğrudan metin çıkartır.

---

## Kullanım

### Belge İndeksleme

`knowledge_base/` klasörüne `.md`, `.txt`, `.pdf` veya `.docx` dosyaları ekleyin, ardından:

```powershell
python -m app ingest
```

### Klasör Otomatik İzleme (Watcher)

`knowledge_base/` klasöründeki dosya değişikliklerini arka planda anlık izlemek ve otomatik indekslemek için:

```powershell
python -m app watch
```

### Terminal Sohbeti

```powershell
python -m app chat
```

Çıkmak için `quit` veya `exit` yazın. Sohbet hafızası son 6 mesajı modele iletir.

### Web Arayüzü (Streamlit)

```powershell
python -m app ui
```

Web arayüzünden belge yükleyebilir, indeksi yenileyebilir ve kaynaklı sohbet edebilirsiniz.

### Retrieval Kalite Değerlendirmesi

```powershell
python -m app eval
```

`tests/eval_dataset.json` içindeki 25 soruluk golden test seti ile Hit Rate, MRR ve anahtar kelime eşleşme oranını raporlar.

### Birim Testleri

```powershell
python -m unittest discover -s tests -v
```

---

## Kod Yapısı

```
app/
├── __main__.py        # ingest / chat / ui / watch / eval komut yönlendirici
├── config.py          # Tüm sabitler ve yollar
├── foundry.py         # Foundry Local SDK model yaşam döngüsü
├── document_loader.py # .md / .txt / .pdf / .docx metin okuma + OCR fallback
├── chunker.py         # Başlık ve paragraf duyarlı akıllı parçalama
├── repository.py      # SQLite şeması, CRUD ve model uyumluluk kontrolü
├── ingest.py          # İndeksleme orkestrasyonu + model uyumsuzluk koruması
├── retrieval.py       # BM25 + Vektör hibrit arama + RRF Re-ranking
├── watcher.py         # knowledge_base klasörü otomatik izleme
├── prompting.py       # Türkçe sistem promptu + sohbet hafızası
├── chat.py            # Soru-cevap akışı
└── ui.py              # Streamlit web arayüzü

tests/
├── eval_dataset.json  # 25 soruluk golden test veri seti
├── eval_retrieval.py  # Retrieval kalite ölçüm scripti
├── test_chunker.py    # Parçalama birim testleri
├── test_repository.py # SQLite birim testleri
├── test_retrieval.py  # Retrieval birim testleri
└── test_reranker.py   # Re-ranking birim testleri
```

---

## Model Uyumluluk Uyarısı ve Yeniden İndeksleme

`config.py` içindeki `EMBEDDING_MODEL_ALIAS` değiştirildiğinde mevcut indeks geçersiz hale gelir. Uygulama bu durumu otomatik tespit eder:

- **Terminalde:** Açık Türkçe hata mesajı verilir. İndeksi zorunlu yenilemek için:
  ```powershell
  python -m app ingest --force-reindex
  ```
- **Web arayüzünde:** Kırmızı uyarı kutusu ve "Zorunlu Yeniden İndeksle" butonu gösterilir.

---

## Teknik Referanslar

- [Teknik Mimari ve Uygulama Sözleşmesi](ARCHITECTURE.md)
- [Microsoft Foundry Local RAG Öğreticisi](https://learn.microsoft.com/en-us/azure/foundry-local/tutorials/tutorial-build-rag-app)
- [Foundry Local Başlangıç Rehberi](https://learn.microsoft.com/en-us/azure/foundry-local/get-started)
