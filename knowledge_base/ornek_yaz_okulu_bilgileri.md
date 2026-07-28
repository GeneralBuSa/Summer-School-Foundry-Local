# Yaz Okulu Yerel RAG Projesi

Bu projenin amacı, kullanıcının kendi belgelerine dayanarak cevap veren ve
internet bağlantısı olmadan çalışabilen yerel bir soru-cevap asistanı
oluşturmaktır. Uygulama Microsoft Foundry Local ile yerel modelleri çalıştırır.

## RAG akışı

RAG üç aşamadan oluşur: retrieve, augment ve generate. Önce kullanıcının
sorusuna anlamca en yakın belge parçaları bulunur. Sonra bu parçalar modelin
bağlamına eklenir. Son olarak model yalnızca bu bağlama dayanarak cevap üretir.

## Yerel veri depolama

Belge parçaları ve embedding vektörleri SQLite veritabanında saklanır. SQLite
ayrı bir sunucu gerektirmez; veri tek bir yerel dosyada tutulur. Küçük belge
koleksiyonlarında vektörler Python içinde cosine similarity ile karşılaştırılır.

## Güvenli davranış

Asistan, cevap belgelerde bulunmuyorsa “Bu bilgi yerel bilgi tabanında
bulunmuyor.” yanıtını vermelidir. Model yeni kaynak adı veya belgede olmayan
ayrıntı uydurmamalıdır. Kullanılan kaynaklar uygulama tarafından ayrıca
gösterilir.
