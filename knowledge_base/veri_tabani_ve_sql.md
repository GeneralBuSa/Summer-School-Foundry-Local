# Veri Tabanı Yönetim Sistemleri ve İndeksleme

Veri tabanları, verilerin düzenli bir şekilde saklandığı ve yönetildiği sistemlerdir.

## İlişkisel Veri Tabanları (RDBMS)

İlişkisel veri tabanları verileri tablolar, satırlar ve sütunlar halinde organize eder. SQL (Structured Query Language) sorgulama dili kullanılır.

- **ACID Prensipleri:** Atomicity (Bütünlük), Consistency (Tutarlılık), Isolation (İzolasyon), Durability (Kalıcılık).
- **B-Tree İndeksleme:** İndeksler, SQL sorgularının arama performansını (O(log N)) hızlandırmak için kullanılır.

## NoSQL Veri Tabanları

NoSQL veri tabanları esnek şema yapılarına sahiptir. Anahtar-Değer (Redis), Doküman (MongoDB) ve Çizge (Neo4j) türleri bulunur.
# Veri Tabanı ve SQL Rehberi

## İlişkisel veri modeli

İlişkisel veri tabanında bilgiler tablolar, satırlar ve sütunlar halinde tutulur.
Her tablo tek bir kavramı temsil etmeli; örneğin `documents` belgeleri,
`chunks` ise belge parçalarını tutabilir. Primary key her satırı benzersiz
tanımlar. Foreign key tablolar arasındaki ilişkiyi kurar. Bir belgeye ait çok
sayıda parça varsa bu bir-çok ilişkidir.

Normalizasyon, aynı bilginin gereksiz tekrarını azaltır. Birinci normal formda
alanlar bölünmez değerler taşır. İkinci ve üçüncü normal formlar, anahtara bağlı
olmayan veya dolaylı tekrarları azaltır. Ancak raporlama veya performans için
kontrollü denormalizasyon yapılabilir.

## SQL sorguları

`SELECT` veri okur, `INSERT` yeni satır ekler, `UPDATE` mevcut satırı değiştirir,
`DELETE` satır siler. `WHERE` filtreleme, `ORDER BY` sıralama, `LIMIT` sonuç
sayısını sınırlama ve `JOIN` ilişkili tabloları birleştirme amacıyla kullanılır.

```sql
SELECT d.source_path, c.content
FROM documents AS d
JOIN chunks AS c ON c.document_id = d.id
WHERE c.embedding_model = 'qwen3-embedding-0.6b'
ORDER BY c.chunk_index
LIMIT 10;
```

`GROUP BY` gruplama, `COUNT` sayma ve `HAVING` gruplanmış sonuçları filtreleme
için kullanılır. Kullanıcıdan gelen değerler SQL metnine birleştirilmemeli;
parametreli sorgular kullanılmalıdır. Böylece SQL injection riski azaltılır.

## ACID ve transaction

ACID; Atomicity, Consistency, Isolation ve Durability kavramlarından oluşur.
Atomicity işlemin tamamının uygulanmasını veya hiç uygulanmamasını sağlar.
Consistency kısıtların korunmasını, Isolation eş zamanlı işlemlerin birbirini
bozmamasını, Durability commit edilmiş verinin kalıcı olmasını ifade eder.

RAG indekslemede belge kaydı ve parçaları aynı transaction içinde yazılmalıdır.
Embedding üretimi yarıda kalırsa transaction rollback yapılmalı ve yarım indeks
bırakılmamalıdır. SQLite sunucu gerektirmez ve tek dosyalı yapısıyla küçük,
yerel uygulamalar için uygundur.

## İndeksler ve B-Tree

İndeks, arama yapılan sütunlar için yardımcı veri yapısıdır. B-Tree indeksleri
eşitlik ve aralık sorgularını hızlandırabilir. Ancak her indeks ek yazma ve disk
alanı maliyeti getirir. Sık kullanılan `document_id` ve `source_path` alanlarında
indeks yararlı olabilir. Embedding vektörlerini SQLite'ta JSON saklamak küçük
koleksiyonlarda basittir; büyük koleksiyonlarda özel vector index veya pgvector
gibi çözümler düşünülmelidir.

## NoSQL ve seçim ölçütleri

NoSQL ailesinde anahtar-değer, doküman, sütun ailesi ve çizge veri tabanları
bulunur. Redis anahtar-değer, MongoDB doküman tabanlı, Neo4j çizge tabanlı
örnektir. Şema esnekliği, ölçek, transaction ihtiyacı, sorgu biçimi ve işletim
maliyeti seçimi belirler. Bu yerel RAG MVP'sinde küçük veri ve offline çalışma
gereksinimi nedeniyle SQLite daha uygundur.
