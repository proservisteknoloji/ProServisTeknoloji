# Proservis Finans Modülü — Uygulama ve Karar Planı

**Durum:** Nihai plan taslağı — hafta sonu uygulama öncesi değerlendirme belgesi  
**Tarih:** 6 Ekim 2026  
**Kapsam:** Proservis web uygulamasında operasyonel finans, nakit yönetimi, cari takip, çek/senet, gider yönetimi, kârlılık ve muhasebe programı entegrasyonları  
**Muhasebe sistemi:** Her tenant'ın seçtiği resmî muhasebe programı (örnek: Luca, Logo, Mikro, ETA vb.) ve mali müşavir çalışma alanı  
**Kapsam dışı:** Herhangi bir muhasebe programının yerine genel muhasebe, e-Defter/e-Beyanname üretimi veya mali müşavir sorumluluğundaki yasal kayıtların geçmesi

---

## 1. Yönetici özeti

Mevcut finans ekranı fatura, satın alma faturası, gider fişi ve personel maliyetini bir araya getirerek gelir-gider raporu üretmektedir. Bu, yönetimsel raporlama için değerli bir başlangıçtır; ancak bir şirketin günlük finans kararlarında gereken üç temel soruyu güvenilir biçimde cevaplamaz:

1. **Bugün kullanılabilir nakit ne kadar?**
2. **Kimden, ne zaman ve ne kadar tahsil edilecek?**
3. **Kime, ne zaman ve hangi hesaptan ödeme yapılacak?**

Bu plan, raporlama ağırlıklı mevcut yapıyı; belge, tahakkuk, nakit hareketi ve mahsuplaştırmayı birbirinden ayıran, denetlenebilir bir operasyonel finans modülüne dönüştürür.

Proservis kullanılan her firmada Proservis ile seçilen muhasebe yazılımı birbirinin rakibi değildir: **Proservis operasyonun ve günlük finans takibinin; muhasebe yazılımı resmî muhasebenin ve mali müşavir sürecinin sistemidir.** Entegrasyon, çift veri girişi ve mutabakat riskini azaltmak için tasarlanır. Luca, desteklenecek sağlayıcılardan yalnızca biridir.

Ana ilke şudur:

```text
Ticari belge              Tahakkuk              Nakit hareketi
(fatura/gider/bordro) -> (gelir-maliyet)  <>  (tahsilat-ödeme)
          \                                      /
           \---------- Cari bakiye --------------/
```

### 1.1 Net ürün kararı

Proservis, ikinci bir genel muhasebe programı olmayacaktır. Proservis; teknik servis firmasının günlük finans operasyonunu yöneten, muhasebe programına temiz ve doğrulanabilir veri hazırlayan katmandır.

| Katman | Kullanıcı | Görev | Sistem sahibi |
|---|---|---|---|
| Operasyonel finans | Firma sahibi, finans sorumlusu, tahsilat ekibi | Nakit, banka, alacak/borç, çek/senet, gider, vade, kârlılık | Proservis |
| Muhasebe aktarımı | Finans sorumlusu + mali müşavir | Ön izleme, hata düzeltme, dönemsel paket onayı | Proservis aktarım merkezi |
| Resmî muhasebe | Mali müşavir | Yevmiye, mizan, beyanname, e-Defter, yasal kayıt | Seçilen muhasebe programı |

Bu kararın sonucu:

- Kullanıcı günlük işinde hesap planı veya yevmiye fişi seçmez.
- Muhasebe kodları yalnızca aktarım merkezinde, mali müşavir onayıyla eşlenir.
- Proservis finans özellikleri, hiçbir entegrasyon açılmadan eksiksiz kullanılabilir.
- Entegrasyon, zorunlu menü değil tenant bazında etkinleştirilen isteğe bağlı modüldür.
- İlk sürümde veri akışı yalnızca **Proservis → muhasebe programı** yönündedir.
- Muhasebe programından Proservis'e otomatik iki yönlü kayıt güncellemesi ilk kapsamın dışındadır.

### 1.2 Entegrasyonun kullanıcıya görünümü

Normal kullanıcı finans ekranında yalnızca kendi operasyonunu görür. “Muhasebeye Aktar” ekranı sadece yetkili finans kullanıcısı/mali müşavir için görünür.

```text
Günlük kullanıcı:      Tahsilat kaydeder, çek vadesini takip eder, gider onaylar.
Finans yöneticisi:     Dönem kayıtlarını kontrol eder ve aktarım paketi oluşturur.
Mali müşavir:          Paketi onaylar, muhasebe programına alır, sonucu bildirir.
```

Bu nedenle entegrasyon, gündelik kullanıcıya karmaşa değil; mali müşavire iletilecek verinin eksiksiz ve denetlenebilir olması avantajını sağlar.

Bir kesilmiş fatura gelir ve müşteri alacağı yaratır; tahsil edildiğinde ise nakit artar ve alacak düşer. Bu iki olay aynı değildir. Tüm tasarım, bu ayrımı korur.

---

## 2. Hedef ürün tanımı

Proservis Finans Modülü, teknik servis, cihaz satışı, CPC/sayaç faturalama ve sözleşmeli hizmet veren firmalar için aşağıdaki yönetim ihtiyaçlarını karşılamalıdır:

- Kasa, banka ve POS hesaplarındaki gerçek para pozisyonunu takip etmek.
- Müşteri alacaklarını ve tedarikçi borçlarını vade bazında yönetmek.
- Alınan/verilen çek ve senetleri; portföy, vade, ciro, tahsil ve risk durumlarıyla yönetmek.
- Kısmi tahsilat/ödeme ve bir işlemin birden çok faturaya dağıtımını kaydetmek.
- Giderleri belge, şube, maliyet merkezi, KDV, ödeme durumu ve onay süreciyle yönetmek.
- 7, 30 ve 90 günlük nakit akışını tahmin etmek.
- Gelir, maliyet ve tahsilatı birbirinden ayırarak müşteri/sözleşme/cihaz/şube kârlılığını hesaplamak.
- Finansal verinin nasıl değiştiğini gösterecek, silme yerine iptal/ters kayıt kullanan denetim izi sağlamak.
- İhtiyaç hâlinde mali müşavirin kullanacağı sisteme düzenli dışa aktarılabilecek veri üretmek.

### 2.1 Bilinçli olarak yapılmayacaklar

- Çift taraflı genel muhasebe defteri bu ilk sürümün zorunlu parçası değildir.
- GİB, e-Defter veya beyanname üretimi bu modülün kapsamına alınmayacaktır.
- Banka entegrasyonu doğrulanmadan otomatik banka hareketi yazılmayacaktır.
- “Resmî bilanço” veya “resmî mali tablo” ifadeleri kullanıcı arayüzünde kullanılmayacaktır. Ekranın adı **Yönetimsel Finans Özeti** olacaktır.

Bu sınırlar hem yasal anlam karmaşasını hem de hafta sonu canlıya alma riskini azaltır.

### 2.2 Proservis–muhasebe programı sorumluluk sınırı

| Konu | Proservis sorumluluğu | Muhasebe programı / mali müşavir sorumluluğu |
|---|---|---|
| Servis, satış, CPC ve operasyon verisi | Kaynak kayıt ve ticari bağlam | Aktarılan veriyi muhasebeleştirme |
| Tahsilat, ödeme, çek/senet, vade | Günlük operasyonel takip ve risk görünümü | Resmî kayıt/kontrol ve dönemsel doğrulama |
| Cari görünüm | Operasyonel açık bakiye ve tahsilat aksiyonu | Resmî cari/mizan mutabakatı |
| Gider belgesi | Toplama, onay, ek belge ve ödeme takibi | Hesap kodu, yevmiye ve vergi kaydı |
| Genel muhasebe, mizan, beyanname, e-Defter | Gönderime hazır kaynak ve mutabakat desteği | Tek resmî kaynak ve yasal süreç |
| Hesap planı ve muhasebe kodu | Seçilen programa göre eşleme saklama | Kod planının sahibi ve onayı |

Bu tabloda herhangi bir alanın iki sistemde aynı anda “asıl kayıt” sayılması yasaktır. Her veri sınıfı için bir tane sistem sahibi belirlenir.

---

## 3. Mevcut durum ve çözülmesi gereken riskler

### 3.1 Mevcut güçlü taraflar

- Satış, servis, CPC ve alış faturaları ortak bir veri alanında bulunuyor.
- Fatura üzerinde kısmi ödeme geçmişi desteği var.
- Gider fişi, şube ve kategori bazında girilebiliyor.
- Bordro/personel maliyeti ayrı bir kaynaktan geliyor.
- Fatura anındaki kur bilgisini saklamaya yönelik altyapı var.
- CPC tarafında snapshot, durum modeli, transaction ve idempotency yaklaşımı olgunlaşıyor.

### 3.2 Mevcut kritik riskler

| Risk | Neden kritik? | Planlanan çözüm |
|---|---|---|
| Tahakkuk ile tahsilatın karışması | Kâr olumlu görünürken kasa/banka boş olabilir. | Fatura, ödeme ve ödeme dağıtımı ayrı kayıtlar olur. |
| Brüt/net/KDV belirsizliği | KDV'nin kârlılık hesabına dahil edilmesi yanıltıcı sonuç üretir. | Her finansal belgede net, KDV, brüt alanları ayrılır. |
| Personel maliyetinde çifte sayım | Gider fişindeki `personnel` ile bordro maliyeti birlikte toplanabilir. | Tek kaynak politikası ve doğrulama kuralı uygulanır. |
| Giderin doğrudan silinmesi | Denetim izi ve geçmiş raporların tutarlılığı kaybolur. | Taslak/onay/iptal-ters kayıt yaşam döngüsü kullanılır. |
| Banka/kasa hesabı yok | Ödemelerin hangi kaynaktan çıktığı, tahsilatın nereye girdiği bilinmez. | Finansal hesaplar ve transfer hareketleri eklenir. |
| Ödeme faturaya gömülü | Çoklu fatura mahsuplaştırması ve banka mutabakatı zordur. | Bağımsız `payment` ve `paymentAllocation` koleksiyonları eklenir. |
| Döviz fallback'i | Tarihsel kur bilinmiyorsa güncel kurla eski işlem çevrilmesi gerçeği bozar. | Snapshot zorunluluğu; eksik kur için görünür uyarı uygulanır. |
| Raporun “resmî bilanço” olarak adlandırılması | Yanlış kullanım ve beklenti oluşturur. | Yönetimsel finans terminolojisi uygulanır. |

### 3.3 Önce düzeltilmesi gereken hesaplama kuralı

Mevcut maliyet motoru işletme gideri, alış faturası ve personel maliyetini topluyor. Gider fişi kategorilerindeki `personnel` kaydı ile bordro kaynağından gelen personel maliyeti aynı dönemde kullanılırsa çifte sayım olasılığı vardır.

**Karar:** Bordro kaynaklı personel maliyeti yalnızca `payroll` kaynağından gelir. Manuel gider fişindeki `personnel` kategorisi ilk sürümde ya kaldırılır ya da `personnel_adjustment` olarak adlandırılıp onaya bağlanır. Aynı dönem/personel/kalem için ikinci kayıt uyarı üretir.

---

## 4. Ürün modülleri ve ekranlar

### 4.1 Finans Ana Sayfa — Yönetimsel Finans Özeti

Bu ekran bir rapor ekranı değil, karar kokpitidir.

**Üst KPI alanı**

- Kullanılabilir nakit: aktif kasa + banka + POS hesaplarının güncel bakiyesi.
- Bugün tahsil edilmesi beklenen tutar.
- 7 gün içinde net nakit değişimi.
- Vadesi geçmiş müşteri alacağı.
- Vadesi yaklaşan tedarikçi borcu.
- Dönem tahakkuk kârı ve tahsilat oranı.

**Ana bileşenler**

- 30 günlük nakit akış grafiği: açılış bakiyesi, beklenen giriş, beklenen çıkış, kapanış bakiyesi.
- Alacak yaşlandırma kartları: 0–30, 31–60, 61–90, 90+ gün.
- Borç yaşlandırma kartları: aynı kırılım.
- Tahsilat aksiyon listesi: vadesi geçmiş ve yüksek tutarlı müşteri faturaları.
- Ödeme takvimi: vadesi yaklaşan alış faturaları, bordro ve onaylı giderler.
- Kârlılık özeti: gelir, doğrudan maliyet, ortak gider payı, faaliyet kârı.
- Veri kalitesi uyarıları: kur snapshot'ı eksik, vadesi eksik, eşleşmemiş banka hareketi, mükerrer şüphesi.

**Filtreler**

- Tarih aralığı (bu ay, son 3/6 ay, yıl, özel aralık)
- Şube
- Para birimi / TL karşılığı
- Maliyet merkezi

### 4.2 Nakit, Banka ve POS Hesapları

**Hesap kartı alanları**

- Hesap adı, türü (`cash`, `bank`, `pos`, `credit_card`, `virtual_pos`, `other`)
- Para birimi
- Banka adı, IBAN'ın maskelenmiş gösterimi, hesap sahibi
- Başlangıç bakiyesi ve tarihi
- Aktif/pasif durumu
- Şube/maliyet merkezi bağlantısı

**Hareket türleri**

- Tahsilat
- Tedarikçi ödemesi
- Gider ödemesi
- Maaş/bordro ödemesi
- Hesaplar arası transfer
- Banka masrafı/komisyonu
- POS bloke çözülmesi
- Manuel düzeltme (zorunlu gerekçe ve yetki ile)

**Kurallar**

- Bir hareket yalnızca tek bir para hesabını etkiler; transfer iki karşıt hareketten oluşur.
- Açılış bakiyesi sonradan değiştirilemez; düzeltme hareketi girilir.
- Kesinleşmiş hareket silinemez. İptal için karşıt yönlü reversal hareketi oluşturulur.
- Negatif bakiyeye izin verilip verilmeyeceği hesap kartındaki politika ile belirlenir; izin varsa uyarı üretir.

### 4.3 Alacaklar — Müşteri Cari ve Tahsilat Merkezi

**Liste kolonları**

- Müşteri, açık bakiye, para birimi, en eski vade, vadesi geçmiş tutar, risk seviyesi, son tahsilat tarihi, sorumlu kullanıcı.

**Müşteri detayında**

- Açılış bakiyesi, faturalar, tahsilatlar, iade/iskonto, mahsuplaştırmalar ve koşan bakiye.
- Açık faturaların vade yaşlandırması.
- Tahsilat sözü / hatırlatma kaydı: tarih, not, sorumlu, sonraki aksiyon.
- PDF/Excel cari ekstre üretimi.

**Tahsilat akışı**

1. Kullanıcı müşteri ve tahsilat hesabını seçer.
2. Tahsilat tutarı, tarih, yöntem, referans numarası ve para birimi girilir.
3. Sistem açık faturaları önerilen vade sırasıyla listeler.
4. Kullanıcı tutarı bir veya birden çok faturaya dağıtır; dağıtılmamış tutar varsa müşteri avansı olarak kaydedilir.
5. İşlem kesinleşince nakit hareketi, ödeme kaydı ve allocation kayıtları atomik biçimde oluşur.
6. Fatura ödeme durumu `unpaid`, `partial`, `paid`, `overpaid` olarak güncellenir.

### 4.4 Borçlar — Tedarikçi Cari ve Ödeme Merkezi

Alacaklar ile simetrik çalışır; ancak müşteri yerine tedarikçi/satın alma faturası kullanır.

- Alış faturası ve onaylı giderden doğan borçlar gösterilir.
- Kısmi ödeme, çoklu faturaya ödeme ve avans işlemleri desteklenir.
- Vadesi gelen ödeme önerileri bakiye, son vade, önem seviyesi ve hesap bakiyesine göre sıralanır.
- Onaysız/taslak belge için ödeme yapılamaz.

### 4.5 Çek ve Senet Yönetimi

Çek/senet, bir ödeme yöntemi alanı değil; kendi vade riski, portföyü ve işlem geçmişi olan bağımsız bir finans varlığıdır. Bu nedenle ayrı bir modül olarak tasarlanacaktır.

**Kapsam**

- Alınan çek ve alınan senet.
- Verilen çek ve verilen senet.
- Portföyde bekletme, bankaya tahsile verme, ciro, tahsil/ödeme, iade, karşılıksız/protesto ve iptal.
- Bir evrakın bir veya birden fazla müşteri/tedarikçi belgesine mahsup edilmesi.
- Vade takvimi, yaklaşan vade ve riskli evrak uyarıları.

**Zorunlu alanlar**

- Tür, yön (alınan/verilen), evrak numarası, tutar, para birimi, düzenleme ve vade tarihi.
- Keşideci/borçlu, lehtar, banka/şube, ilişkili müşteri veya tedarikçi.
- Portföy konumu, evraktan sorumlu kullanıcı, ek belge ve açıklama.
- İlişkili faturalar, dağıtılan tutar, kalan avans/emanet tutarı.
- Durum geçmişi, iade/karşılıksız nedeni ve audit kaydı.

**Alınan evrak yaşam döngüsü**

```text
draft -> received -> portfolio
portfolio -> deposited_for_collection -> collected
portfolio -> endorsed -> endorsed_settled
portfolio/deposited_for_collection -> returned | dishonored
```

**Verilen evrak yaşam döngüsü**

```text
draft -> issued -> delivered -> outstanding -> paid
outstanding -> returned_or_cancelled
```

| Olay | Cari etkisi | Nakit/banka etkisi | Portföy etkisi |
|---|---|---|---|
| Alınan çek/senet kabulü | İlişkilendirilen müşteri alacağı kapanır; fazlası avans olur. | Yok | Evrak portföye girer. |
| Bankaya tahsile verme | Yok | Yok | `deposited_for_collection` olur. |
| Tahsil | Yok | Banka/kasa artar. | `collected` olur. |
| Karşılıksız/iade | Müşteri alacağı tekrar açılır veya açık kalır. | Varsa önceki etki terslenir. | Riskli duruma geçer. |
| Verilen çek/senet düzenleme | Tedarikçi borcu kapanır; vadeli yükümlülük doğar. | Yok | Verilen evrak oluşur. |
| Ödeme | Yok | Banka/kasa azalır. | `paid` olur. |

**Kritik kurallar**

- Alınan çek/senet kabulü nakit tahsilat değildir; tahsil edildiği anda banka/kasa hareketi doğar.
- Verilen çek/senet düzenlenmesi banka bakiyesini düşürmez; vade veya fiilî ödeme tarihinde düşürür.
- Evrak silinmez; ciro, tahsile verme, iade, karşılıksız ve iptal durum geçişleri audit kaydı ile saklanır.
- Aynı numara + banka + keşideci bileşimi için mükerrer giriş uyarısı zorunludur.
- Yaklaşan vade, vadesi geçmiş, bankada tahsilde, karşılıksız/iade ve protestolu evraklar dashboard'da ayrı risk olarak görünür.

**Ekranlar**

- Çek/Senet Portföyü: yön, durum, vade, banka, müşteri/tedarikçi, tutar ve sorumlu filtreleri.
- Vade Takvimi: bugün, 7/30/90 gün, gecikmiş ve riskli evraklar.
- Evrak Detayı: bağlı faturalar, cari etkisi, durum geçmişi, dosyalar ve audit.
- Tahsile Verme / Ciro / Tahsil / İade / Karşılıksız işlem akışları.
- Çek/Senet Risk Raporu: portföy toplamı, bankada tahsilde, yaklaşan vade, karşılıksız ve müşteri yoğunlaşması.

### 4.6 Gider Yönetimi

Mevcut gider fişi ekranı aşağıdaki modele yükseltilecektir.

**Gider belgesi alanları**

- Belge numarası ve belge tarihi
- Tedarikçi (opsiyonel ama önerilen)
- Gider kategorisi ve alt kategori
- Şube, maliyet merkezi, proje/servis kaydı (opsiyonel bağlantılar)
- Net tutar, KDV oranı/tutarı, brüt tutar
- Para birimi, kur snapshot'ı ve TL karşılığı
- Vade tarihi
- Açıklama
- Ek dosya: fiş/fatura görseli veya PDF
- Ödeme durumu, ödeme hesabı ve ödeme referansı
- Oluşturan, onaylayan, iptal eden kullanıcılar ile zaman damgaları

**Durum makinesi**

```text
draft -> submitted -> approved -> payable -> partially_paid -> paid
                 \-> rejected
approved/payable/partially_paid/paid -> cancelled (ters kayıt / gerekçe)
```

**Gider iş kuralları**

- Tutarlar negatif girilemez.
- Net + KDV = brüt tutar tolerans sınırı içinde doğrulanır.
- Aynı tedarikçi + belge no tekrarına uyarı verilir; kullanıcı yetkisi olmadan kesinleşmez.
- `paid` durumundaki belge silinemez veya değiştirilemez.
- Aynı personel maliyetinin bordro ve gider fişi olarak iki kez girilmesi engellenir/uyarılanır.
- Gider fişi kaydı, ödeme kaydı değildir. Gideri oluşturmak borç/tahakkuk doğurur; ödeme ayrı işlemdir.

### 4.7 Nakit Akış Tahmini

**Dönemler:** 7 gün, 30 gün, 90 gün ve özel tarih aralığı.

**Tahmin kaynakları**

- Kesilmiş ve açık müşteri faturalarının vade tarihleri.
- Onaylı alış faturaları ve onaylı giderlerin vade tarihleri.
- Bordro takvimi.
- Sözleşmeli kira, internet, lisans gibi planlı/tekrarlı giderler.
- POS blokesi ve bilinen banka masrafı gibi tanımlanmış hareketler.
- Kullanıcının opsiyonel manuel tahmin kalemleri.
- Alınan çek/senet tahsil vadesi, verilen çek/senet ödeme vadesi ve karşılıksız risk senaryosu.

**Senaryolar**

- Beklenen: normal tahsilat varsayımı.
- Temkinli: gecikmiş alacakların yalnızca belirli yüzdesi alınır.
- İyimser: tahsilat sözleri ve bekleyen teklifler dahil edilir.

Manuel tahmin hareketleri gerçekleşen kayıt değildir; açık biçimde `forecast` olarak işaretlenmelidir.

### 4.8 Bütçe ve Gerçekleşen

Bu modül Faz 2'de açılacaktır.

- Aylık/yıllık bütçe sürümü oluşturma.
- Şube, maliyet merkezi ve kategori bazında hedef tanımlama.
- Gerçekleşen gider/gelir ile otomatik karşılaştırma.
- Sapma tutarı, sapma yüzdesi, açıklama ve aksiyon kaydı.
- Onaylanmış bütçe sürümü geçmişe dönük değiştirilemez; yeni revizyon sürümü açılır.

### 4.9 Kârlılık Analizi

Kârlılık, tahsilat değil tahakkuk bazında hesaplanır. Tahsilat durumu ayrıca gösterilir.

**Boyutlar**

- Müşteri
- Sözleşme
- Cihaz
- Şube
- Servis kaydı / iş emri
- Gelir türü: servis, CPC, ürün satışı, kira vb.

**Maliyet katmanları**

1. Doğrudan maliyet: cihaz sarfı, stok çıkışı, servis parçası, doğrudan işçilik, satın alma kalemi.
2. Atanmış maliyet: müşteri/şube/servis kaydıyla doğrudan bağlanan giderler.
3. Ortak gider: kira, yönetim, genel yakıt vb.; tanımlı dağıtım anahtarıyla paylaştırılır.

**Dağıtım anahtarı seçenekleri**

- Ciro oranı
- Servis sayısı
- Cihaz sayısı
- Sayaç/kopya hacmi
- Teknik personel saatleri
- Sabit yüzdelik (istisnai)

Sistem her sonuçta hangi dağıtım anahtarının kullanıldığını açıkça gösterir. “Tahmini ortak gider dağıtımı” ile “doğrudan maliyet” aynı görsel ağırlıkta sunulmaz.

### 4.10 Raporlar ve Dışa Aktarım

- Yönetimsel gelir-gider raporu (net, KDV, brüt ayrı kolonlarla)
- Nakit akış raporu
- Hesap ekstresi
- Müşteri cari ekstresi
- Tedarikçi cari ekstresi
- Alacak/borç yaşlandırma raporu
- Gider kategori/şube/maliyet merkezi raporu
- Kârlılık raporları
- Çek/senet portföy, vade ve risk raporu
- Veri kalitesi ve eşleşmeyen hareketler raporu
- CSV/XLSX dışa aktarım; sonra mali müşavir format adaptörü

Her raporun başlığında tarih aralığı, filtreler, oluşturulma zamanı, para birimi ve “yönetimsel rapor” niteliği gösterilir.

---

## 5. Kavramsal veri modeli

### 5.1 Temel ayrım

| Varlık | Ne ifade eder? | Nakit etkisi | Örnek |
|---|---|---:|---|
| `financialDocument` | Gelir veya maliyet doğuran ticari belge | Doğrudan yok | Kesilmiş satış faturası, alış faturası, gider belgesi |
| `payment` | Tek bir tahsilat veya ödeme olayı | Var | Bankaya gelen 10.000 TL tahsilat |
| `paymentAllocation` | Ödemenin belgeye dağıtımı | Dolaylı | Tahsilatın 7.000 TL'si FAT-1'e, 3.000 TL'si FAT-2'ye |
| `financialAccount` | Paranın tutulduğu hesap | Bakiye taşır | Garanti TL hesabı, kasa, POS |
| `accountTransaction` | Hesap bakiyesini değiştiren hareket | Var | Tahsilat, ödeme, transfer, komisyon |
| `recurringPlan` | Gelecek tahmin veya tekrarlı plan | Gerçekleşene kadar yok | Her ay kira, lisans, bordro tahmini |
| `auditLog` | Değişiklik izi | Yok | Kim, neyi, neden iptal etti |

### 5.2 Firestore koleksiyon tasarımı

```text
tenants/{tenantId}/
  financial_accounts/{accountId}
  account_transactions/{transactionId}
  payments/{paymentId}
  payment_allocations/{allocationId}
  negotiable_instruments/{instrumentId}
  instrument_allocations/{allocationId}
  instrument_events/{eventId}
  expense_documents/{expenseId}
  suppliers/{supplierId}
  recurring_financial_plans/{planId}
  financial_budgets/{budgetId}
  financial_audit_logs/{logId}
  financial_settings/config
```

Mevcut koleksiyonlar korunur:

```text
invoices/{invoiceId}              -> satış / alış / CPC ticari belgeleri
operating_expenses/{expenseId}    -> migration sonuna dek legacy kaynak
payrolls/{payrollId}              -> personel maliyeti kaynağı
```

### 5.3 Kimlik ve para alanı standardı

Her finansal kayıtta aşağıdaki alanlar standarttır:

```ts
type CurrencyCode = 'TRY' | 'USD' | 'EUR';

interface MonetaryAmount {
  amount: number;            // Belgenin kendi para birimindeki değer
  currency: CurrencyCode;
  tryAmount: number;         // Olay anındaki TL karşılığı
  exchangeRateToTry: number; // TRY için 1
  exchangeRateSource: 'snapshot' | 'manual' | 'official' | 'legacy_unknown';
  exchangeRateDate: Timestamp;
}

interface TaxAmounts {
  net: MonetaryAmount;
  taxRate: number;
  tax: MonetaryAmount;
  gross: MonetaryAmount;
}
```

JavaScript kayan nokta hatasını azaltmak için para hesapları merkezî yardımcı fonksiyonla iki ondalık basamakta yuvarlanır. Finansal hesapların saf fonksiyonlarında mümkünse kuruş/minor-unit tamsayı yaklaşımı kullanılır.

### 5.4 Finansal belge örneği

```ts
type FinancialDocumentStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'payable'
  | 'partially_paid'
  | 'paid'
  | 'rejected'
  | 'cancelled';

interface ExpenseDocument {
  id: string;
  tenantId: string;
  documentNo?: string;
  documentDate: Timestamp;
  dueDate?: Timestamp;
  supplierId?: string;
  supplierName?: string;
  categoryId: string;
  costCenterId?: string;
  branchId?: string;
  serviceId?: string;
  taxAmounts: TaxAmounts;
  status: FinancialDocumentStatus;
  outstanding: MonetaryAmount;
  attachments: AttachmentRef[];
  createdBy: ActorRef;
  approvedBy?: ActorRef;
  cancelledBy?: ActorRef;
  cancellationReason?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
  version: number;
}
```

### 5.5 Ödeme ve mahsuplaştırma örneği

```ts
type PaymentDirection = 'inflow' | 'outflow';

interface Payment {
  id: string;
  tenantId: string;
  direction: PaymentDirection;
  counterpartyType: 'customer' | 'supplier' | 'employee' | 'other';
  counterpartyId?: string;
  financialAccountId: string;
  paymentDate: Timestamp;
  amount: MonetaryAmount;
  method: 'cash' | 'bank_transfer' | 'card' | 'pos' | 'check' | 'other';
  referenceNo?: string;
  status: 'draft' | 'posted' | 'reversed';
  reversalOfPaymentId?: string;
  createdBy: ActorRef;
  postedAt?: Timestamp;
}

interface PaymentAllocation {
  id: string;
  tenantId: string;
  paymentId: string;
  documentType: 'invoice' | 'expense_document' | 'opening_balance';
  documentId: string;
  amount: MonetaryAmount;
  allocatedAt: Timestamp;
}
```

### 5.6 Çek/senet veri modeli

```ts
type InstrumentType = 'check' | 'promissory_note';
type InstrumentDirection = 'received' | 'issued';
type InstrumentStatus =
  | 'draft' | 'received' | 'portfolio' | 'deposited_for_collection'
  | 'endorsed' | 'issued' | 'delivered' | 'outstanding'
  | 'collected' | 'paid' | 'returned' | 'dishonored' | 'cancelled';

interface NegotiableInstrument {
  id: string;
  tenantId: string;
  type: InstrumentType;
  direction: InstrumentDirection;
  status: InstrumentStatus;
  instrumentNo: string;
  issueDate?: Timestamp;
  maturityDate: Timestamp;
  amount: MonetaryAmount;
  counterpartyId?: string;
  counterpartyName: string;
  bankName?: string;
  bankBranch?: string;
  portfolioLocation: 'company_portfolio' | 'bank_collection' | 'endorsed' | 'none';
  custodianUserId?: string;
  linkedDocumentIds: string[];
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

interface InstrumentEvent {
  id: string;
  tenantId: string;
  instrumentId: string;
  type: 'received' | 'deposited' | 'endorsed' | 'collected' | 'paid' | 'returned' | 'dishonored' | 'cancelled';
  occurredAt: Timestamp;
  financialAccountId?: string;
  reason?: string;
  actorId: string;
}
```

### 5.7 Zorunlu index ve sorgu planı

Firestore sorguları için uygulamaya başlamadan önce indeksler tanımlanmalıdır:

- `account_transactions`: `financialAccountId + transactionDate desc`
- `payments`: `counterpartyId + paymentDate desc`
- `expense_documents`: `status + dueDate asc`
- `expense_documents`: `branchId + documentDate desc`
- `payment_allocations`: `paymentId`, `documentId`
- `negotiable_instruments`: `direction + status + maturityDate asc`
- `negotiable_instruments`: `counterpartyId + maturityDate desc`
- `instrument_events`: `instrumentId + occurredAt desc`
- `financial_audit_logs`: `entityType + entityId + createdAt desc`

Sorgu ihtiyacı indeks gerektiriyorsa istemci tarafında tüm veriyi çekip filtrelemek kalıcı çözüm olarak kabul edilmez.

---

## 6. İş kuralları ve hesaplama politikaları

### 6.1 Tahakkuk ve nakit politikası

- Kârlılık raporu tahakkuk bazlıdır: onaylanmış/kesinleşmiş belgeler hesaplanır.
- Nakit akışı yalnızca `posted` durumundaki hesap hareketleri ile değişir.
- Tahsil edilmemiş satış faturası nakit değildir; alacak ve tahmin kaynağıdır.
- Ödenmemiş alış faturası nakit çıkışı değildir; borç ve tahmin kaynağıdır.
- Taslak belgeler resmi gerçekleşen rapora dahil edilmez; isteğe bağlı tahmin senaryosuna eklenebilir.

### 6.2 Vergi politikası

- Yönetimsel faaliyet kârı varsayılan olarak KDV hariç net tutarlardan hesaplanır.
- KDV toplamları ayrı raporlanır; kârın parçası olarak görünmez.
- Fatura/gider verisinde net-KDV-brüt ayrımı yoksa kayıt `legacy_incomplete` olarak işaretlenir; kesin analize uyarı verilir.
- Vergi oranı tarihi belgeden snapshot olarak saklanır; sistemdeki güncel oran eski belgeyi değiştirmez.

### 6.3 Döviz politikası

- Her yabancı para belgede olay anı kur snapshot'ı zorunludur.
- Snapshot eksik eski kayıt, güncel kurla sessizce dönüştürülmez; `legacy_unknown` uyarısı ile raporlanır.
- Ayrı para birimleri doğrudan toplanmaz. TL konsolidasyon gerekiyorsa hangi kurun kullanıldığı görünür olmalıdır.
- Kur farkı ilk sürümde bağımsız bir yönetimsel ayarlama kalemi olarak kaydedilir; otomatik muhasebe fişi üretmez.

### 6.4 Vade ve yaşlandırma politikası

- Vade tarihi yoksa belge, belge tarihine göre “vadesi belirsiz” olarak işaretlenir; yaşlandırma hesabına sessizce dahil edilmez.
- Yaşlandırma, rapor tarihi ile açık bakiyeli belgenin vade tarihi arasındaki gün farkından hesaplanır.
- Standart kovalar: vadesi gelmemiş, 0–30, 31–60, 61–90, 90+ gün.

### 6.5 İptal, iade ve silme politikası

- Kesinleşmiş finansal kayıtta fiziksel silme yoktur.
- Yanlış tahsilat/ödeme: ters yönlü reversal ödeme + audit kaydı.
- Yanlış gider: iptal kaydı veya kredi/iade belgesi.
- İptal, ilişkili allocation ve hesap hareketlerini atomik olarak geri alır.
- İptal edilmiş hareketler raporlarda görünür ancak toplam etkisi sıfır olur.

### 6.6 Durum geçişi yetkisi

| İşlem | Taslak | Finans kullanıcısı | Finans yöneticisi | Yönetici |
|---|---:|---:|---:|---:|
| Gider oluşturma | Evet | Evet | Evet | Evet |
| Gider onaylama | Hayır | Politika ile | Evet | Evet |
| Tahsilat/ödeme kesinleştirme | Hayır | Evet | Evet | Evet |
| İptal/ters kayıt | Hayır | Gerekçeyle | Evet | Evet |
| Hesap kartı oluşturma | Hayır | Hayır | Evet | Evet |
| Ayar/devir bakiyesi değiştirme | Hayır | Hayır | Hayır | Evet |

Yetki matrisi tenant kullanıcı izinleriyle ilişkilendirilir; yalnızca menünün gizlenmesi güvenlik sayılmaz. Servis ve Firestore kuralları da yetkiyi doğrular.

---

## 7. Teknik mimari

### 7.1 Katmanlama ilkesi

```text
UI sayfaları / bileşenleri
        ↓
Use-case servisleri (createPayment, approveExpense, reversePayment)
        ↓
Repository / Firestore erişimi
        ↓
Saf domain motorları (hesaplama, doğrulama, durum geçişi)
        ↓
Tipler ve sabitler
```

**UI katmanında yapılmayacaklar:** toplam hesaplama, bakiye güncelleme, durum geçişi kararı, kur fallback'i ve ödeme dağıtımı mantığı.

### 7.2 Önerilen dosya yapısı

```text
src/features/finance/
  domain/
    money.ts
    dates.ts
    financialDocument.ts
    payment.ts
    paymentAllocation.ts
    accountTransaction.ts
    aging.ts
    cashForecast.ts
    profitability.ts
    expenseStatusMachine.ts
  application/
    createPayment.ts
    reversePayment.ts
    allocatePayment.ts
    approveExpense.ts
    cancelExpense.ts
    createAccountTransfer.ts
    calculateFinancialOverview.ts
  infrastructure/
    firebaseFinancialAccountRepository.ts
    firebasePaymentRepository.ts
    firebaseExpenseRepository.ts
    firebaseAuditLogRepository.ts
  queries/
    financeDashboardQuery.ts
    receivablesQuery.ts
    payablesQuery.ts
  ui/
    components/
    hooks/
```

Mevcut `BillingService`, `OperatingExpenseService` ve bordro servisleri ilk etapta adapter ile kullanılacak; doğrudan tüm sistem tek seferde taşınmayacaktır.

### 7.3 Saf domain motorları

Her motor Firebase, React veya UI bağımlılığı olmadan düz nesne alıp düz nesne döndürür.

- `calculateOutstanding(document, allocations)`
- `validatePaymentAllocation(payment, documents, allocations)`
- `calculateAging(asOfDate, openDocuments)`
- `calculateCashForecast(accounts, documents, recurringPlans, scenario)`
- `calculateProfitability(revenue, directCosts, allocatedCosts)`
- `transitionInstrumentStatus(current, event, actorPermission)`
- `calculateInstrumentMaturityRisk(asOfDate, instruments)`
- `transitionExpenseStatus(current, event, actorPermission)`
- `buildReversal(originalPayment, reason)`

Bu ayrım, hesaplama hatalarının ekrandan bağımsız olarak test edilmesini sağlar.

### 7.4 Atomiklik ve idempotency

Aşağıdaki işlemler Firestore transaction ile tek bütün olarak çalışmalıdır:

- Tahsilat/ödeme post edilmesi: payment + account transaction + allocations + belge açık bakiye/durum + audit log.
- Ödeme iptali: reversal payment + karşıt hesap hareketi + allocation geri alma + belge bakiye güncellemesi + audit log.
- Hesaplar arası transfer: çıkış hareketi + giriş hareketi + transfer bağı + audit log.
- Gider onayı: durum güncellemesi + tahakkuk etkisi + audit log.
- Çek/senet tahsil/ödeme: evrak durumu + payment + hesap hareketi + belge bakiyesi/durumu + audit log.

Her dışarıdan tetiklenebilen finans operasyonunda deterministik `idempotencyKey` bulunur. Aynı isteğin tekrarı ikinci kez para hareketi yaratmaz.

### 7.5 Denetim izi

Her kritik işlem için audit kaydı tutulur:

```ts
interface FinancialAuditLog {
  tenantId: string;
  entityType: 'payment' | 'expense_document' | 'financial_account' | 'invoice' | 'allocation';
  entityId: string;
  action: 'created' | 'approved' | 'posted' | 'reversed' | 'cancelled' | 'updated';
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  reason?: string;
  actorId: string;
  createdAt: Timestamp;
}
```

Kişisel veya hassas veri gereksiz biçimde audit kaydına kopyalanmaz; değişen finans alanları özetlenir.

### 7.6 Muhasebe programı entegrasyon mimarisi

Entegrasyon tek tuşla ve doğrulamasız “otomatik muhasebeleştir” yaklaşımıyla başlamaz. İlk sürümde mali müşavirin gözden geçirip onaylayacağı **kontrollü aktarım paketi** kurulur; doğrudan web servis aktarımı ancak ilgili sağlayıcı erişimi, yetkilendirmesi, test ortamı ve alan eşlemesi doğrulandıktan sonra etkinleştirilir.

#### 7.6.1 Entegrasyon hedefi

```text
Proservis operasyon kaydı
        ↓ (doğrulama ve hesap kodu eşleme)
Muhasebe aktarım paketi / aktarım kuyruğu
        ↓ (mali müşavir ön izleme ve onay)
Seçilen muhasebe programı
        ↓ (sonuç, fiş no veya hata)
Proservis mutabakat ekranı ve audit kaydı
```

#### 7.6.2 Sağlayıcıdan bağımsız aktarım sözleşmesi

Proservis çekirdeği Luca, Logo, Mikro, ETA veya başka bir markanın API modelini bilmez. Önce ortak bir muhasebe aktarım sözleşmesi üretir; her sağlayıcı bunu kendi dosya formatına veya API çağrısına çeviren ayrı bir adaptör olur.

```ts
interface AccountingConnector {
  provider: 'luca' | 'logo' | 'mikro' | 'eta' | 'generic_file' | string;
  validate(batch: AccountingExportBatch): ValidationResult;
  export(batch: AccountingExportBatch): Promise<ExportResult>;
  importResult?(reference: string): Promise<ImportResult>;
}
```

Yeni bir muhasebe programı eklemek, finans çekirdeğini değiştirmeyi değil yeni bir `AccountingConnector` adaptörü eklemeyi gerektirir.

#### 7.6.3 Aktarım yöntemleri ve öncelik sırası

1. **Onaylı dosya aktarımı:** Sağlayıcının mali müşavirce kullanılan güncel CSV/Excel/XML/fiş şablonuna göre paket. İlk canlı geçiş için varsayılan yöntemdir.
2. **Sağlayıcı API/web servis entegrasyonu:** Ticari olarak etkinleştirilmiş erişim, teknik dokümantasyon, test hesabı ve yazılı mali müşavir onayı sağlanırsa kullanılır.
3. **Sağlayıcı yardımcı uygulaması/manuel aktarım:** API veya standart şablon doğrulaması tamamlanana kadar kontrollü geçiş çözümü.

Luca için kamuya açık sayfalar diğer yazılımlardan veri aktarımı, Excel ile cari/stok/çek-senet/fatura/yevmiye/banka ekstresi aktarımı ve ücretli web servis aktarım API hizmeti sunduğunu belirtiyor. Luca adaptörü bu olanaklara göre yapılır; diğer sağlayıcıların alanları, API uçları, yetkilendirmesi ve lisans kapsamı ise kendi üreticileri ile mali müşavir tarafından doğrulanmadan teknik taahhüt kabul edilmez.

#### 7.6.4 Aktarım kapsamı

| Proservis kaynağı | Muhasebe programı hedefi | Aktarım zamanı | Zorunlu ön koşul |
|---|---|---|---|
| Satış / servis / CPC faturası | Fatura ve/veya muhasebe fişi | Onaylı belge sonrası | Cari kart + gelir/KDV hesap eşlemesi |
| Alış faturası ve gider belgesi | Alış/gider muhasebe fişi | Onay sonrası | Tedarikçi + gider/KDV hesap eşlemesi |
| Tahsilat ve ödeme | Banka/kasa fişi | Post edildiğinde veya günlük toplu | Hesap ve tahsilat/ödeme kod eşlemesi |
| Alınan/verilen çek-senet | Çek/senet kartı ve/veya fiş | Evrak yaşam döngüsü olayında | Portföy, banka ve cari hesap eşlemesi |
| Banka ekstresi | Banka ekstresi/fişi | Mutabakat sonrası | Banka hesabı eşlemesi |
| Bordro özeti | Muhasebe fişi | Mali müşavirce belirlenen dönem | Bordro hesap kodu şablonu |

#### 7.6.5 Eşleme ve ayar modeli

Her tenant ve muhasebe sağlayıcısı için mali müşavirle birlikte onaylanmış bir `accounting_mapping_profile` tutulur:

```ts
interface AccountingMappingProfile {
  tenantId: string;
  provider: string;
  version: number;
  status: 'draft' | 'approved' | 'retired';
  customerAccountPrefix?: string;
  supplierAccountPrefix?: string;
  incomeAccountsByCategory: Record<string, string>;
  expenseAccountsByCategory: Record<string, string>;
  vatAccountsByRate: Record<string, { inputVat: string; outputVat: string }>;
  cashAccountByFinancialAccountId: Record<string, string>;
  receivedCheckPortfolioAccount?: string;
  issuedCheckPortfolioAccount?: string;
  defaultsApprovedBy: string;
  approvedAt: Timestamp;
}
```

- Eşleme profilini yalnızca finans yöneticisi oluşturur; mali müşavir onayı olmadan `approved` olamaz.
- Aktarım paketi, oluşturulduğu anda kullanılan profil sürümünü snapshot olarak saklar.
- Hesap kodu bulunmayan kayıt aktarım kuyruğuna girmez; görünür hata listesinde bekler.
- Bir hesap kodu değişikliği eski aktarım paketini geriye dönük değiştirmez.

#### 7.6.6 Aktarım durumu ve idempotency

```text
draft -> validated -> awaiting_accountant_approval -> exported -> imported
                                                \-> rejected / failed
imported -> reconciled
```

Her aktarım paketi için aşağıdaki alanlar bulunur: `provider`, `sourceEntityIds`, `mappingProfileVersion`, `period`, `payloadHash`, `idempotencyKey`, `exportedBy`, `approvedBy`, `providerReference`, `errorDetail` ve zaman damgaları.

- Aynı kaynak kaydın aynı profil sürümüyle ikinci kez aktarılması engellenir.
- Sağlayıcıdan başarılı sonuç/fiş numarası gelmeden kayıt `imported` sayılmaz.
- Başarısız paketin kaynak kaydı değiştirilmez; düzeltme sonrası yeni sürüm paketi oluşur.
- Dönem kapandıktan sonra aktarım paketi değiştirilemez; ters/düzeltme paketi açılır.

#### 7.6.7 Mutabakat ekranı

Mali müşavir için ayrı bir **Muhasebe Aktarım Merkezi** ekranı sunulur; ekranda seçili sağlayıcı açıkça gösterilir:

- Aktarılmayı bekleyen belge sayısı ve tutarı.
- Eşleme eksikleri, zorunlu alan eksikleri, mükerrer aktarım şüphesi.
- Ön izleme: borç/alacak satırları, hesap kodları, KDV ve cari kart.
- Onay/red ve red nedeni.
- Dışa aktarılan paketler, sağlayıcı referansı ve durumları.
- Proservis toplamı ile muhasebe programından dönen/ithal edilen sonuç arasındaki dönemsel mutabakat farkı.

#### 7.6.8 Kesinlikle yapılmayacak entegrasyon davranışları

- Muhasebe programındaki resmî kaydı Proservis'in tek taraflı olarak silmesi veya değiştirmesi.
- Hatalı eşleme nedeniyle hesap kodu boş olan kaydın varsayılan hesaba sessizce aktarılması.
- Başarısız API isteğinde aynı fişi otomatik ve sınırsız tekrar gönderme.
- Kullanıcının muhasebe programı parolasını Firestore veya tarayıcıda saklamak.
- Mali müşavir onayı gereken paketleri kullanıcı fark etmeden canlıya aktarmak.

---

## 8. Geçiş ve veri temizliği planı

### 8.1 İlkeler

- Eski faturalar, giderler veya CPC snapshot'ları geriye dönük değiştirilmez.
- Migration idempotent olur; aynı veri ikinci kez taşınmaz.
- Otomatik taşınamayan kayıtlar karantinaya alınır ve görünür hata raporuna düşer.
- Canlı veri üzerinde ilk deneme yapılmaz; önce export/snapshot ve test tenant kullanılır.

### 8.2 Kaynak eşleme

| Mevcut kaynak | Yeni karşılık | Not |
|---|---|---|
| Satış/servis/CPC faturası | `financialDocument` adapter + alacak | Mevcut fatura ID korunur. |
| Alış faturası | borç doğuran belge | KDV ayrımı yoksa işaretlenir. |
| `paymentHistory` | `payment` + `paymentAllocation` | Dönüşümden sonra çift yazım kontrolü gerekir. |
| `operating_expenses` | `expenseDocument` | Legacy kaynağı görünür tutulur. |
| Bordro | personel maliyet adapter'ı | Manuel personel gideriyle çakışma raporu üretir. |
| `financial_reports` | yalnızca legacy rapor referansı | Yeni gerçek kaynak değildir. |

### 8.3 Migration aşamaları

1. Salt-okunur analiz: toplam kayıt, para birimi, vade, KDV, ödeme tarihi ve mükerrer belge raporu.
2. Test tenant'a örnek migration.
3. Eski/yeni toplam karşılaştırması: belge adedi, brüt/net toplam, açık bakiye, tahsilat toplamı.
4. Uyuşmayan kayıtların manuel inceleme listesi.
5. Canlı tenant için yedek/export.
6. Migration dry-run çıktısının onayı.
7. İdempotent canlı migration.
8. Rapor mutabakatı ve sadece-okunur legacy dönemi.
9. Onaydan sonra yeni akışın varsayılan yapılması.

### 8.4 Kabul edilen legacy sınırlamaları

- Tarihsel kayıtta kur snapshot'ı yoksa kesin TL konsolidasyonu garanti edilemez.
- Vade tarihi olmayan eski fatura yaşlandırma raporunda “belirsiz vade”ye düşer.
- Ödeme tarihi olmayan eski tahsilat kaydı belge tarihi ile eşitlenmez; veri kalitesi uyarısı alır.

---

## 9. Uygulama fazları

### Faz 0 — Tasarım dondurma ve güvenlik zemini

**Amaç:** Kodlamadan önce kararları netleştirmek.

- Bu belgedeki açık kararların onaylanması.
- Para birimi standardının (`TRY` yerine mevcut `TL` alanlarıyla uyum stratejisi) seçilmesi.
- Gider onay limitleri ve rollerinin belirlenmesi.
- İlk pilot firmadaki muhasebe programının hesap planı, cari kart standardı, KDV hesapları ve mali müşavir onay akışının çıkarılması.
- İlk sağlayıcı için aktarım yönteminin (onaylı dosya, API/web servis veya yardımcı uygulama) mali müşavir ve yazılım sağlayıcısıyla yazılı olarak doğrulanması; diğer sağlayıcılar için henüz geliştirme taahhüdü verilmemesi.
- Kasa/banka/POS hesaplarının başlangıç listesi ve devir bakiyelerinin hazırlanması.
- Mevcut verinin salt-okunur analizi ve yedek planı.
- Firestore security rules taslağı ve indeks listesi.

**Çıkış kriteri:** Veri sözleşmeleri, durum makineleri ve yetki matrisi yazılı olarak onaylanmıştır.

### Faz 1 — Finans çekirdeği (canlı değer üreten minimum sürüm)

**Amaç:** Güvenilir tahsilat/ödeme, hesap bakiyesi ve açık cari takibi.

- Finansal hesap kartları.
- Payment, allocation ve account transaction domain modelleri.
- Tahsilat girişi ve müşteri faturalarına dağıtım.
- Tedarikçi/alış fatura ödemesi ve dağıtım.
- Hesaplar arası transfer.
- Alınan/verilen çek-senet kartı, portföye alma ve vade takvimi.
- Cari açık bakiye ve yaşlandırma sorguları.
- Ters kayıt/iptal mekanizması.
- Audit log ve transaction/idempotency.
- Finans ana sayfasında nakit, vadesi geçmiş alacak/borç ve temel tahsilat oranı.
- İleride aktarım yapılabilmesi için kaynak kayıtlarda değişmez kimlik, audit ve export uygunluğu; henüz kullanıcıya açık muhasebe entegrasyonu yok.

**Bu fazın sonunda kullanıcı şunları yapabilmelidir:**

1. Banka hesabı oluşturmak ve devir bakiyesi girmek.
2. Bir satış faturası için kısmi tahsilat kaydetmek.
3. Tek tahsilatı birden çok faturaya dağıtmak.
4. Bir alış faturasını bankadan ödemek.
5. Hatalı tahsilatı ters kayıtla iptal etmek.
6. Aynı işlemi tekrar gönderdiğinde mükerrer hareket oluşmadığını görmek.
7. Müşterinin güncel açık bakiyesini ve vadesi geçen tutarını görmek.
8. Alınan çekin tahsile kadar nakit sayılmadığını; tahsil edildiğinde bankaya geçtiğini görmek.

### Faz 2 — Gider yönetimi ve nakit akışı

**Amaç:** Giderin belge yaşam döngüsünü ve ileri nakit görünürlüğünü kurmak.

- Yeni gider belgesi modeli ve ek dosya desteği.
- Taslak/onay/ödeme/iptal durumları.
- KDV/net/brüt doğrulaması.
- Tedarikçi kartları ve mükerrer belge kontrolü.
- Tekrarlı gider planları.
- 7/30/90 gün nakit akış tahmini ve senaryolar.
- Çek/senet tahsile verme, ciro, tahsil, ödeme, iade ve karşılıksız akışları.
- Çek/senet portföyü, vade takvimi ve risk dashboard'u.
- Gider/borç ödeme takvimi.

### Faz 3 — Kârlılık ve bütçe

**Amaç:** İşin nerede para kazandığını göstermek.

- Maliyet merkezi ve dağıtım anahtarı tanımları.
- Müşteri, şube, sözleşme, cihaz ve servis bazlı kârlılık.
- Personel maliyeti çifte sayım koruması.
- Bütçe sürümleri, bütçe-gerçekleşen ve sapma analizi.

### Faz 4 — Muhasebe entegrasyonları, mutabakat ve olgunlaştırma

**Amaç:** Finans operasyonunun kontrol edilebilirliğini artırmak.

- Banka ekstresi içe aktarma (önce CSV, sonra doğrulanmış entegrasyon).
- Otomatik/yarı otomatik eşleştirme önerileri.
- Ortak aktarım paketi ve mali müşavir onay akışı.
- Pilot sağlayıcı adaptörü olarak Luca: önce dosya aktarımı; web servis erişimi doğrulanmışsa idempotent ve izlenebilir doğrudan aktarım.
- Aktarım sonucu/sağlayıcı referansı ile dönemsel mutabakat ekranı.
- Dönem kapama/yeniden açma yetkileri.
- Gelişmiş audit raporları ve izleme metrikleri.

### Faz 5 — Sağlayıcı adaptörlerinin ölçeklenmesi

**Amaç:** Finans çekirdeğini değiştirmeden, yalnızca doğrulanmış müşteri talebine göre yeni muhasebe programlarını desteklemek.

- Her yeni sağlayıcı için talep, kullanım hacmi, teknik erişim, lisans maliyeti ve mali müşavir uygunluğu değerlendirilir.
- Logo, Mikro, ETA ve diğerleri ayrı `AccountingConnector` adaptörleri olarak ele alınır; hiçbirinin özel alanı finans çekirdeğine sızdırılmaz.
- Her adaptör için dosya/API doğrulaması, test hesabı, örnek aktarım paketi, hata sözleşmesi ve mutabakat kabul testleri zorunludur.
- Sağlayıcının API'si yoksa veya erişimi maliyetliyse standart onaylı dosya aktarımı desteklenen çözüm olarak kalır.
- İki yönlü senkronizasyon ancak tek yönlü kullanımın üretimde kanıtlanmış olması, çakışma politikası ve mali müşavir onayı sonrasında ayrı bir ürün kararıyla değerlendirilir.

---

## 10. Hafta sonu uygulama çalışma planı

Tüm fazları aynı hafta sonunda canlıya almak önerilmez. Hafta sonu için güvenli hedef **Faz 0 + Faz 1 çekirdeğinin kontrollü teslimi** olmalıdır. Faz 2–4 için altyapı kararı ve iş listesi tamamlanır.

### Gün 1 — Hazırlık ve çekirdek modeller

- Mevcut finans verisi export/backup kontrolü.
- Veri sözleşmeleri ve TypeScript tipleri.
- Para, tarih, yaşlandırma, allocation ve durum geçişi saf motorları.
- Firestore koleksiyonları, indeks taslağı ve security rule testleri.
- Finansal hesap kartları için temel CRUD.
- Unit test altyapısı ve test senaryoları.

### Gün 2 — Tahsilat, ödeme ve cari görünüm

- Tahsilat use-case'i: transaction + idempotency + allocation.
- Tedarikçi ödeme use-case'i.
- Hesap hareketi ve transfer use-case'i.
- Müşteri alacak ve tedarikçi borç ekranları.
- Yaşlandırma motoru ve finans ana sayfası temel KPI'ları.
- Ters kayıt akışı.

### Gün 3 — Doğrulama, migration denemesi ve sınırlı canlıya alma

- Test tenant migration dry-run.
- Eski/yeni toplam karşılaştırması.
- Yetki, tenant izolasyonu, idempotency ve concurrency testleri.
- Hata izleme ve rollback kontrolü.
- Önce tek iç tenant/canary kullanıcısıyla açılış.
- Onay alınırsa kademeli tenant açılışı.

**Zaman daralırsa kesinlikle ertelenecekler:** banka entegrasyonu, bütçe, otomatik kur alma, dosya OCR, gelişmiş kârlılık dağıtımı ve muhasebe export adaptörleri.

---

## 11. Test stratejisi ve kabul kriterleri

### 11.1 Birim testleri — zorunlu

| Alan | Örnek kabul testi |
|---|---|
| Para | 0,01 kuruş hassasiyetinde toplama/yuvarlama tutarlı. |
| Allocation | Ödeme tutarından fazla dağıtım engellenir. |
| Kısmi tahsilat | 10.000 TL faturaya 4.000 TL tahsilat sonrası açık bakiye 6.000 TL. |
| Çoklu mahsuplaştırma | 10.000 TL tahsilat iki faturaya 7.000 + 3.000 dağıtılabilir. |
| Fazla ödeme | Fazlalık müşteri avansı olur; fatura bakiyesi negatifleşmez. |
| Ters kayıt | İptal sonrası hesap bakiyesi ve açık bakiye önceki duruma döner. |
| Alınan çek | Çek kabulü cari bakiyeyi düşürür ama banka bakiyesini değiştirmez. |
| Çek tahsili | Tahsil günü banka artar, evrak `collected` olur ve ikinci kez cari mahsup oluşmaz. |
| Karşılıksız çek | Evrak `dishonored` olur; müşteri alacağı yeniden açık hâle gelir. |
| Verilen çek | Düzenleme bankayı düşürmez; ödeme gününde banka azalır. |
| Yaşlandırma | 31 gün gecikmiş kayıt doğru kovaya girer. |
| KDV | Net + KDV = brüt doğrulanır. |
| Döviz | Snapshot ile TL karşılığı sabit kalır; güncel kur değişimi eski belgeyi değiştirmez. |
| Durum makinesi | Yetkisiz kullanıcı `approved` veya `paid` geçişi yapamaz. |

### 11.2 Entegrasyon testleri — zorunlu

- Aynı `idempotencyKey` ile eşzamanlı iki tahsilat isteği tek kayıt üretir.
- Bir ödeme post edilirken network retry oluşursa ikinci account transaction oluşmaz.
- Tenant A kullanıcısı Tenant B'nin finans belgesine erişemez/değiştiremez.
- Payment, account transaction, allocation ve belge bakiyesi transaction içinde birlikte güncellenir.
- İptal edilen payment'in allocation'ları tekrar kullanılabilir hâle gelir.
- Eksik indeks nedeniyle hata oluştuğunda UI veri kaybı yaratmaz; kullanıcıya anlaşılır durum gösterilir.

### 11.3 Kullanıcı kabul senaryoları

1. **Kısmi tahsilat:** Müşteri 20.000 TL faturanın 8.000 TL'sini banka yoluyla öder; banka bakiyesi artar, cari açık 12.000 TL olur.
2. **Tek tahsilat/çoklu fatura:** 15.000 TL tahsilat iki açık faturaya dağıtılır; raporlar ve cari ekstre aynı sonucu gösterir.
3. **Tedarikçi ödemesi:** Alış faturası ödeme sonrası borçtan düşer, banka hesabından çıkar.
4. **Hatalı tahsilat:** Yetkili kullanıcı gerekçe ile reversal yapar; geçmiş hareket korunur, toplamlar doğru döner.
5. **Vade raporu:** Bugün itibarıyla 90+ gün alacaklar doğru müşteri ve tutarla görünür.
6. **Çifte personel maliyeti:** Bordrosu bulunan ayda manuel personel gideri girildiğinde sistem uyarır/bloklar.
7. **Şube filtresi:** Şube filtresi sadece ilgili gelir, gider, alacak ve hesap hareketlerini etkiler.
8. **Alınan çek:** Müşteriden alınan çek faturaya mahsup edilir; tahsil olana kadar banka/kasa toplamına eklenmez.
9. **Karşılıksız çek:** Karşılıksız işlemi sonrası müşteri cari bakiyesi, risk ekranı ve audit geçmişi tutarlı kalır.

### 11.4 Yayın öncesi zorunlu kalite kapıları

- `npm run lint`
- `npm run build`
- Finans domain testlerinin tamamı
- Firestore rules emulator veya eşdeğer yetki testi
- Test tenant migration mutabakatı
- Uygulama içi kritik akışların manuel kontrol listesi
- Rollback tatbikatı

Build başarısı, finansal hesaplamanın doğruluğunun kanıtı değildir; unit ve entegrasyon testleri zorunludur.

---

## 12. Güvenlik, yetki ve operasyon

### 12.1 Tenant izolasyonu

- Her sorgu ve yazma tenant yoluyla sınırlandırılır.
- İstemci tarafından gelen `tenantId` tek başına güvenilir kabul edilmez; oturum/claim doğrulaması yapılır.
- Finans yöneticisi izni olmayan kullanıcılar hesap bakiyesi, maliyet ve tahsilat ekranlarını görüntüleyemez.

### 12.2 Hassas veri

- IBAN, banka hesap numarası ve kişisel ödeme bilgileri maskeli gösterilir.
- Dosya eki erişimi tenant/rol ile sınırlandırılır.
- Audit log'da tam kart veya banka bilgisi tutulmaz.

### 12.3 Dönem kapama

- Faz 4'e kadar dönem kapama yalnızca yönetimsel uyarı seviyesinde kalır.
- Sonrasında kapanmış döneme yeni finans hareketi girilmesi engellenir; yönetici gerekçe ile dönemi tekrar açabilir.
- Geçmişe tarihli kayıtların finans dashboard etkisi görünür biçimde işaretlenir.

### 12.4 İzleme

- Transaction hata oranı
- Idempotent tekrar sayısı
- Mükerrer belge uyarıları
- Eşleşmemiş tahsilat/ödeme sayısı
- Kur snapshot'ı eksik kayıt sayısı
- Negatif bakiye uyarıları

---

## 13. Karar listesi — uygulamadan önce onaylanmalı

| # | Karar | Öneri | Etki |
|---:|---|---|---|
| 1 | Para birimi kodu | Yeni modelde ISO `TRY`; eski `TL` adapter ile okunur. | Tüm finans modelleri |
| 2 | Resmî muhasebe iddiası | Yok; yalnızca yönetimsel finans. | Hukuki/ürün dili |
| 3 | Personel maliyet kaynağı | Bordro ana kaynak; manuel düzeltme onaylı istisna. | Kârlılık doğruluğu |
| 4 | Gider onay limiti | Tenant ayarından tanımlanabilir. | Yetki ve süreç |
| 5 | Fazla tahsilat/ödeme | Avans olarak tutulur; otomatik mahsup yapılmaz. | Cari doğruluğu |
| 6 | Vadesiz belgeler | “Belirsiz vade” grubunda görünür. | Yaşlandırma |
| 7 | Negatif banka/kasa | İzin politikası hesap bazlı; uyarı zorunlu. | Nakit kontrolü |
| 8 | Döviz kur kaynağı | Belge snapshot'ı zorunlu; legacy eksik işaretlenir. | Tarihsel rapor |
| 9 | Silme | Kesinleşmiş finansal kayıt silinmez; reversal/iptal. | Audit ve güven |
| 10 | Hafta sonu canlı kapsamı | Faz 1 + canary; Faz 2–4 sonra. | Canlı risk |
| 11 | Resmî muhasebe sistemi | Tenant'ın seçtiği muhasebe programı; Proservis operasyonel finans sistemidir. | Sistem sahipliği |
| 12 | Aktarım yöntemi | Önce mali müşavir onaylı dosya paketi; API/web servis ancak sağlayıcı erişim/test doğrulamasıyla. | Canlı aktarım riski |
| 13 | Hesap kodu eşlemesi | Her sağlayıcının hesap planına göre sürümlü mapping profili. | Yevmiye doğruluğu |
| 14 | Aktarım onayı | Mali müşavir onayı olmadan paket seçili sağlayıcıya gönderilmez. | Kontrol ve sorumluluk |

---

## 14. Artılar, eksiler ve azaltım planı

### Artılar

- Nakit, kârlılık ve cari bakiye birbirine karışmadan görünür.
- Kısmi ödeme ve tahsilat süreçleri operasyonel olarak yönetilir.
- Yanlış işlem silinmediği için denetlenebilirlik artar.
- Kârlılık hesapları daha güvenilir hâle gelir.
- Gelecekte banka entegrasyonu, muhasebe export'u ve bütçe için sağlam temel oluşur.
- Saf domain motorları sayesinde kod okunabilirliği ve test edilebilirliği yükselir.

### Eksiler / maliyetler

- Mevcut basit fatura içi ödeme akışından daha fazla veri modeli ve ekran gerekir.
- Migration sırasında eski veride eksik vade/KDV/kur bilgisi görülebilir.
- Transaction ve idempotency tasarımı geliştirme süresini artırır.
- Kullanıcıların “silme” yerine “iptal/ters kayıt” alışkanlığı edinmesi gerekir.
- Banka entegrasyonu olmadan ilk sürümde hesap hareketleri manuel veya CSV temelli kalır.

### Azaltım stratejisi

- Fazlı geçiş, canary tenant ve rollback ile kapsam kontrolü.
- Legacy veriyi değiştirmeden adapter/migration yaklaşımı.
- Önce manuel banka hesabı + CSV; otomatik entegrasyonu sonra ekleme.
- Kısa ekran içi yardım metinleri ve rol bazlı sadeleştirilmiş akışlar.
- Hesaplama motoru için kapsamlı test seti.

---

## 15. Başarı ölçütleri

Canlıya alımdan sonraki ilk ölçüm döneminde aşağıdaki göstergeler takip edilir:

- Açık müşteri faturalarının %100'ünde ödeme durumu hesaplanabiliyor olması.
- Tahsilat/ödeme sonrası hesap bakiyesi ile cari bakiyenin tutarlı olması.
- Finansal işlemde mükerrer kayıt oranının sıfır olması.
- Kesinleşmiş finans kayıtlarında fiziksel silme olmaması.
- KDV/net/brüt bilgisi tam yeni gider belgelerinin oranı.
- Vadesi geçmiş alacakların kullanıcı tarafından aksiyonlanma oranı.
- Kur snapshot'ı eksik legacy kayıtların sayısı ve çözüm oranı.
- Kârlılık raporundaki personel maliyeti çifte sayım uyarı sayısı.

---

## 16. Uygulamaya başlama kontrol listesi

- [ ] Faz 1 kapsamı onaylandı.
- [ ] Bu belgedeki 10 karar maddesi netleştirildi.
- [ ] Canlı verinin yedeği/export'u doğrulandı.
- [ ] Test tenant hazırlandı.
- [ ] Finansal hesapların başlangıç listesi ve devir bakiyeleri onaylandı.
- [ ] Roller ve onay limitleri belirlendi.
- [ ] Mali müşavirle seçili muhasebe programının hesap kodu eşleme atölyesi yapıldı.
- [ ] İlk sağlayıcının aktarım yöntemi, test hesabı/şablonu ve kabul kriterleri yazılı olarak doğrulandı.
- [ ] İlk aktarım için dönem ve kapsam kilitlendi; çift aktarımı önleyen idempotency kontrolü test edildi.
- [ ] Migration dry-run için örnek veri seçildi.
- [ ] Firestore indeks ve kurallar planlandı.
- [ ] Unit/integration test ortamı çalışıyor.
- [ ] Canary yayın, rollback ve sorumlu kişiler belirlendi.

---

## 17. Nihai öneri

Bu modülün başarısı daha fazla grafik eklemekten değil, **belge → tahakkuk → ödeme → hesap hareketi → cari bakiye** zincirini doğru kurmaktan geçer.

Hafta sonu hedefi; bu zincirin çekirdeğini güvenle canlıya almak, mevcut raporlama ekranını yeni çekirdeğin tüketicisi hâline getirmek ve daha gelişmiş gider/nakit akışı/kârlılık modüllerini bu güvenilir temel üzerinde fazlı olarak tamamlamaktır.

Bu yaklaşım, hem finansal doğruluğu hem de kodun uzun vadede okunabilir, test edilebilir ve spagetti yapıdan uzak kalmasını sağlar.
