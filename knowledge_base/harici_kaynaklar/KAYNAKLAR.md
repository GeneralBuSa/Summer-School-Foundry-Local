# Harici Test Kaynakları

Bu klasör, yerel RAG uygulamasının farklı dosya türleri ve belge yapılarıyla denenmesi için hazırlanmış açık erişimli bir test paketidir. Her türden **3 dosya** bulunur.

## PDF

| Dosya | Kaynak | Test amacı |
| --- | --- | --- |
| `nist_ai_rmf.pdf` | [NIST AI Risk Management Framework](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) | Teknik başlıklar, tablolar ve resmî rapor düzeni. |
| `nist_genai_profile.pdf` | [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | Üretken yapay zekâ riskleri, kontrol listeleri ve tablo yapıları. |
| `nist_security_controls.pdf` | [NIST SP 800-53 Rev. 5](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf) | Çok uzun (yüzlerce sayfa), yoğun numaralandırma ve kontrol tabloları. |

## DOCX

| Dosya | Kaynak | Test amacı |
| --- | --- | --- |
| `docx_general.docx` | [python-docx test belgesi](https://raw.githubusercontent.com/python-openxml/python-docx/master/tests/test_files/test.docx) | Genel Word yapısı. |
| `docx_images.docx` | [python-docx görüntülü belge](https://raw.githubusercontent.com/python-openxml/python-docx/master/tests/test_files/having-images.docx) | Gömülü görüntülerle DOCX ayrıştırma. |
| `docx_nested_content.docx` | [python-docx iç içe içerik belgesi](https://raw.githubusercontent.com/python-openxml/python-docx/master/tests/test_files/blk-inner-content.docx) | İç içe blok/biçim yapısı. |

DOCX dosyaları format ve yapı testi içindir; uzun içerik yükü için PDF/TXT kaynaklarını kullan. Uzun gerçek DOCX tez için [bu açık erişimli kaynak](https://www.tara.tcd.ie/tara8/server/api/core/bitstreams/4c3a6112-b80d-42e8-bd4d-e98ac7cabf91/content) da tarayıcıdan manuel indirilebilir.

## TXT

| Dosya | Kaynak | Test amacı |
| --- | --- | --- |
| `melville_moby_dick.txt` | [Project Gutenberg: Moby-Dick](https://www.gutenberg.org/ebooks/2701.txt.utf-8) | Başlıklar, dipnot benzeri bölümler ve uzun metin. |

## CSV

| Dosya | Kaynak | Test amacı |
| --- | --- | --- |
| `owid_life_expectancy.csv` | [Our World in Data: Life Expectancy](https://ourworldindata.org/grapher/life-expectancy.csv) | Ülke/yıl zaman serisi. |

## XLSX

| Dosya | Kaynak | Test amacı |
| --- | --- | --- |
| `education_child_count.xlsx` | [U.S. Department of Education: IDEA Section 618](https://data.ed.gov/dataset/6d352536-201c-426e-bce8-135922c7a9e8/resource/247f4fea-ac58-493b-be54-d23b11a83b34/download/1819-bchildcountandedenvironment-18.xlsx) | Açık kamu verisi ve tablo hücreleri. |
| `education_assessment.xlsx` | [U.S. Department of Education: Assessment Table](https://data.ed.gov/dataset/b9a0ca4d-a5ae-423d-a52f-71c020ebfd12/resource/ec1fbc90-822c-462c-83c4-576cd1ea6d35/download/1314-bassessment-2.xlsx) | Farklı eğitim istatistiği şeması. |

## Kullanım notu

- Bu dosyalar İngilizcedir; mevcut Türkçe belgelerle aynı indeks içinde arama yaptığında sonuç havuzu karışır. Format testi için bunları ayrı bir klasörde/ayrı indeks veritabanında denemek daha sağlıklıdır.
- Görüntü tabanlı, taranmış PDF'ler için Tesseract OCR Windows üzerinde ayrıca kurulu olmalıdır. Bu paketteki PDF'ler metin katmanlıdır.
- BLS'nin 550 sayfalık karmaşık PDF'si de iyi bir ek stres testidir: [OIICS Manual](https://www.bls.gov/iif/definitions/oiics-manual-2010.pdf). Sunucu otomatik indirmeyi engellediğinden bunu tarayıcıdan manuel indirmek gerekir.
