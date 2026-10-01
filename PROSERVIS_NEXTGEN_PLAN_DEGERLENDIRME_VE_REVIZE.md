# ProServis NextGen
## Servis Performans ve Yönetim Analitiği
### Senior Teknik Değerlendirme ve Revize Uygulama Planı

**Belge türü:** Teknik değerlendirme, risk analizi ve uygulama planı  
**Kapsam:** `/dashboard/service`, performans raporu, KPI motoru, PDF/XLSX export  
**Değerlendirme yaklaşımı:** Dürüst veri kapsamı, ölçüm güvenilirliği ve üretim uygulanabilirliği  
**Karar:** Planın yönü onaylanıyor; bazı KPI ve mimari kararlar düzeltilmeden uygulamaya geçilmemeli.

---

## 1. Kısa Karar

Paylaşılan NextGen planı, mevcut raporun temel kusurunu doğru yakalıyor: performans raporu, müşteri-lokasyon km kaydı bulunmadığında servisleri dışarıda bırakmamalıdır.

Aşağıdaki kararlar güçlü ve korunmalıdır:

- Lojistik verisinin performans raporundan ayrılması
- Ham `ServiceRecord` yerine canonical raporlama modeli kullanılması
- Veri kalitesi uyarılarının yöneticiye gösterilmesi
- Sayaç, çoklu cihaz, parça ve teknisyen verisinin birlikte değerlendirilmesi
- PDF ve Excel çıktılarının aynı rapor sonucundan üretilmesi
- Büyük veri için server-side sorgu ve export planlanması

Bununla birlikte planın bazı bölümleri mevcut verinin güvenilirliğini aşan sonuçlar vaat ediyor. Özellikle aşağıdaki konular mevcut haliyle kesin KPI olarak sunulmamalıdır:

- First-Time Fix
- Gerçek SLA başarısı
- Sayaç başına arıza sıklığı
- Geçmiş servislerde gerçek MTTR
- Dövizli maliyetlerin tarihsel ve kesin TL karşılığı
- `fulfillmentItems` kayıtlarının tamamının tüketilmiş parça sayılması

Bu nedenle önerilen uygulama sırası üç aşamadan biraz daha ayrıntılı olmalıdır. Önce veri sözleşmesi ve doğrulama, sonra normalizer ve güvenilir KPI'lar, en son yönetim arayüzü ve export geliştirilmelidir.

---

## 2. Planın Takdir Edilen Güçlü Yönleri

### 2.1 Doğru kök probleme odaklanıyor

Plan, mevcut sorunun modal görünümü olmadığını, rapor kapsamının yanlış tanımlandığını doğru tespit ediyor. Km kaydı olmayan servislerin ana rapordan çıkarılması gerçekten kritik bir mantık hatasıdır.

### 2.2 Raporlama ara modeli doğru bir mimari karardır

`ServiceReportFact` yaklaşımı önemlidir. Çünkü:

- Eski ve yeni alan adları tek yerde normalize edilebilir.
- UI, PDF ve Excel aynı veriyi kullanabilir.
- Eksik veri sessizce kaybolmaz.
- KPI hesapları ekran bileşenlerinin içine dağılmaz.
- Gelecekte server-side raporlamaya geçiş kolaylaşır.

### 2.3 Veri kalitesini görünür yapması doğru

`dataQualityFlags` yaklaşımı özellikle eski Firestore kayıtları için gereklidir. Eski kayıtların yeni alanları taşımaması sistemin bozuk olduğu anlamına gelmez; fakat yöneticinin hangi sonuca ne kadar güvenebileceğini bilmesi gerekir.

### 2.4 Çoklu cihaz ve sayaç dinamiğini dikkate alması sektörel olarak isabetli

Fotokopi servisinde yalnızca servis adedi yeterli değildir. Cihazın baskı hacmi, cihaz sayısı ve sayaç değişimi dikkate alınmalıdır. Planın bu sektörel gerçekliği hesaba katması değerlidir.

### 2.5 Client belleği ve Firestore maliyetini erken düşünmesi olumludur

10.000 veya daha fazla servis kaydını modal açılışında client belleğine almak uzun vadede doğru değildir. Ancak yalnızca `createdAt` sorgusu eklemek yeterli değildir; tarih modu, indeksler, pagination ve export işleminin server-side tasarımı birlikte ele alınmalıdır.

---

## 3. Düzeltilmesi Gereken Kritik Noktalar

### 3.1 Canonical teknisyen kuralı fazla kesin

Plan, kapanmış işte `technicianId` alanının işi fiilen yapan teknisyeni temsil ettiğini varsayıyor. Mevcut veri modelinde bu garanti edilmemektedir. `technicianId` bazı akışlarda atanan teknisyen, bazı akışlarda işi yapan teknisyen olabilir.

Bu nedenle şu varsayım güvenli değildir:

```text
closedAt varsa technicianId kesinlikle işi kapatan kişidir
```

Önerilen yaklaşım:

```text
assignedTechnician
    -> işin kime atandığını gösterir

executingTechnician
    -> işi fiilen kimin yürüttüğünü gösterir

closingTechnician
    -> kaydı kimin kapattığını gösterir
```

Mevcut veri bu rolleri ayırmıyorsa raporda kullanılan alan `canonicalTechnicianName` olarak gösterilebilir; fakat doğruluk seviyesi ayrıca işaretlenmelidir:

```typescript
technicianResolution:
    | "explicit_executing_technician"
    | "assigned_technician_fallback"
    | "legacy_name_fallback"
    | "unknown";
```

Yeni sistemde durum değişikliği olayına `changedByUid` ve `changedByName` yazılmadan “kapatılan teknisyen” metriği güvenilir hale gelmez.

### 3.2 Geçmiş SLA hesabı varsayımsal KPI'dır

Plan geçmiş kayıtlar için şu eşikleri referans alıyor:

- Critical: 4 saat
- High: 24 saat
- Medium/Low: 48 saat

Bu yaklaşım iki sebeple risklidir:

1. Geçmişte bu SLA politikası gerçekten uygulanmış olmayabilir.
2. Önceki planlarda öncelik ve talep türüne göre farklı süreler tanımlanmıştı.

Geçmiş kayıtlar için sonuç şu şekilde adlandırılmalıdır:

```text
historical_sla_result: estimated | unknown
```

Yönetici ekranında gerçek SLA ile tahmini SLA aynı kartta birleştirilmemelidir.

Yeni kayıtlar için servis/talep oluşturma anında snapshot yazılmalıdır:

```typescript
slaPolicyId?: string;
slaTargetMinutes?: number;
slaStartedAt?: Timestamp;
slaDueAt?: Timestamp;
slaPausedMinutes?: number;
slaResolvedAt?: Timestamp;
slaResult?: "met" | "breached" | "paused" | "unknown";
```

### 3.3 First-Time Fix kuralı güvenilir değildir

`statusLogs` içinde `Waiting Part` durumuna düşmemek, ilk seferde çözüm anlamına gelmez. Servis parça beklemeden çözülememiş olabilir veya müşteri daha sonra aynı cihaz için yeni servis açmış olabilir.

`returnedFromService === true` de tek başına First-Time Fix başarısızlığını kanıtlamaz. Bu alan servis atölyeden geri dönmesini ifade edebilir; sahada tekrar ziyaret edildiğini göstermeyebilir.

Önerilen metrik ayrımı:

```text
First-Time Fix: kesin olarak hesaplanamıyor
Callback Rate: aynı cihaz için zaman penceresinde tekrar açılan kayıt oranı
Follow-up Required: açıkça takip işi işaretlenmiş kayıt oranı
```

İlk sürümde ekranda `First-Time Fix` yerine şu gösterilmelidir:

```text
Tekrar Çağrı Oranı
```

Bu da yalnızca yeterli cihaz kimliği olan kayıtlar için hesaplanmalı ve numerator/denominator sayıları gösterilmelidir.

Gerçek First-Time Fix için ziyaret modeli gerekir:

```text
service_visits/{visitId}
    serviceId
    visitNumber
    technicianId
    startedAt
    completedAt
    outcome
    requiresFollowUp
```

### 3.4 14 günlük tekrar çağrı kuralı iş anlamı açısından net değil

Aynı seri numarası için son 14 günde yeni kayıt bulunması her zaman aynı arızanın tekrarı değildir. Farklı arıza, toner teslimi veya periyodik bakım olabilir.

Tekrarlayan çağrı için eşleştirme kriterleri en azından şunları içermelidir:

- Aynı tenant
- Aynı cihaz kimliği veya doğrulanmış seri numarası
- Servis türünün uygun olması
- Aynı veya benzer problem kategorisi
- Önceki kaydın açılış/kapanış durumu
- Tanımlı zaman penceresi

Başlangıçta sonuç şu isimle sunulabilir:

```text
Aynı cihazda 14 günlük tekrar servis göstergesi
```

Bu metrik kesin “arıza tekrarı” olarak adlandırılmamalıdır.

### 3.5 Sayaç başına arıza sıklığı doğrudan hesaplanamaz

`bwCounter` ve `colorCounter` mevcut servis üzerindeki anlık sayaç değerleridir. Sayaç başına arıza sıklığı için şu bilgiler gerekir:

- Önceki doğrulanmış sayaç
- Sayaç değişim zamanı
- Sayaç kaynağı
- Cihaz çalışma dönemi
- Servis olayının sayaç aralığı

Tek bir servis kaydındaki sayaç değeri toplam baskı adedi değildir. `totalPrintedPagesInJob` alanını yalnızca net sayaç farkı gerçekten hesaplanabiliyorsa doldurmak gerekir.

Güvenli model:

```typescript
counterDelta?: number;
counterDeltaStatus: "calculated" | "missing_baseline" | "invalid" | "not_applicable";
counterSource?: "approved_meter" | "telemetry" | "manual" | "unknown";
```

Sayaç baseline'ı yoksa `0` yazılmamalıdır. `0`, gerçek sıfır ile eksik veriyi birbirine karıştırır.

### 3.6 `selectedMeterDeviceIds` cihaz ayrıntısı taşımaz

Çoklu cihaz ID'lerini bilmek cihaz sayısını hesaplamaya yardımcı olabilir; ancak model, seri numarası ve sayaç verisini cihaz bazında çözmeden güvenilir cihaz analizi üretilemez.

Bunun için raporlama aşamasında cihaz snapshot'ı alınmalı veya cihaz kayıtları kontrollü biçimde yüklenmelidir:

```text
job device IDs
    -> tenant/device ownership validation
    -> device model and serial resolution
    -> per-device meter facts
```

`primaryDeviceModel` yalnızca ana cihaz gerçekten belirlenebiliyorsa doldurulmalıdır. Aksi durumda model analizinde “çoklu cihaz / bilinmiyor” kategorisi kullanılmalıdır.

### 3.7 `fulfillmentItems` otomatik olarak tüketilmiş parça değildir

`fulfillmentItems` stoktan ayrılan, teslim edilen veya iş emrine bağlanan kalemleri temsil ediyor olabilir. Her fulfillment kaydı fiilen kullanılan parça olmayabilir.

Maliyet modelinde aşağıdaki ayrım yapılmalıdır:

```text
usedParts
    -> fiilen kullanılmış parça adayı

fulfillmentItems
    -> iş emrine ayrılmış/teslim edilmiş kalem
```

İki kaynak aynı kaydı temsil ediyorsa çift sayım riski vardır. Birleştirme anahtarı olarak stok kalemi ID'si, servis ID'si, hareket ID'si ve miktar kullanılmalıdır.

Önerilen alanlar:

```typescript
partUsageStatus: "used" | "issued" | "returned" | "unknown";
partsCostStatus: "actual" | "estimated" | "missing";
```

### 3.8 `totalCostTRY` maliyet ile satış fiyatını karıştırmamalı

`unitPrice` veya `totalPrice` alanlarının maliyet, liste fiyatı, müşteriye yansıtılan fiyat veya karma değer olup olmadığı kesinleştirilmelidir.

Ayrı alanlar önerilir:

```typescript
partsCostTRY;
partsChargeTRY;
serviceRevenueTRY;
```

Maliyet konsolidasyonu için:

- Kur kaynağı
- Kur tarihi
- Kur tipi
- Orijinal para birimi
- Orijinal tutar
- TL karşılığı
- Kur bulunamadı durumu

saklanmalıdır.

Geçmiş servislerde bugünkü kur ile hesaplanan tutar “gerçek maliyet” değil, “bugünkü kurla tahmini karşılık” olarak etiketlenmelidir.

### 3.9 `ExchangeRateService` browser raporlamasının bağımlılığı olmamalı

Rapor açılırken dış veya merkezi kur servisine yapılan çağrı:

- Rapor sonucunu zamanla değiştirebilir.
- Aynı raporu farklı günlerde farklı üretebilir.
- Kur servisi erişilemezse export'u bozabilir.
- Çok sayıda satırda performansı düşürebilir.

Öneri:

- Servis/parça kaydı oluşurken kur snapshot'ı yazmak.
- Eski kayıtlarda kur yoksa tek seferlik rapor bağlamında kur çözümlemek.
- Çözülen kurun kaynağını ve “estimated” durumunu göstermek.
- Export sırasında her satır için tekrar kur servisi çağırmamak.

### 3.10 Üç aşama üretim uygulaması için fazla geniş

Aşama 1 normalizer, sorgu davranışı ve tarih mantığı; Aşama 2 tüm dashboard ve KPI motoru; Aşama 3 export ve Firestore optimizasyonunu birlikte içeriyor.

Bu yapı test ve geri dönüş noktalarını zayıflatır. Özellikle Aşama 2 sonunda doğrulanmamış KPI'lar canlı yönetim kararlarına girebilir.

Daha güvenli plan altı fazdan oluşmalıdır.

---

## 4. Revize Mimari

### 4.1 Katmanlar

```text
Firestore / ServiceService
        |
        v
ServiceReportSourceQuery
        |
        v
ServiceReportNormalizer
        |
        v
ServiceReportFact[]
        |
        v
ServiceReportCalculator
        |
        v
ServicePerformanceReport
        |
        +--> Yönetim Kokpiti
        +--> PDF Export
        +--> XLSX Export
        +--> Veri Kalitesi Raporu
```

### 4.2 Sorgu katmanı

Sorgu katmanı şunları sağlamalıdır:

- Tenant izolasyonu
- Tarih modu: `createdAt`, `closedAt`, gerekirse `activity`
- Başlangıç/bitiş sınırları
- Şube filtresi
- Teknisyen filtresi
- Pagination veya server-side aggregation
- Kullanılacak Firestore indekslerinin belgelenmesi

`closedAt` sorgusu ile `createdAt` sorgusu aynı sorgu olarak varsayılmamalıdır. `activity` modu birden fazla olay kaynağı gerektirebilir ve ilk fazda ertelenebilir.

### 4.3 Normalizer çıktısı

Önerilen minimum model:

```typescript
interface ServiceReportFact {
    serviceId: string;
    tenantId: string;

    createdAt: Date | null;
    closedAt: Date | null;
    timelineDate: Date | null;
    resolutionDurationMinutes: number | null;

    status: ServiceStatus;
    isCompleted: boolean;
    priority: ServiceRecord["priority"] | "unknown";
    jobType: ServiceJobType | "unknown";

    assignedTechnicianId: string | null;
    assignedTechnicianName: string;
    executingTechnicianId: string | null;
    executingTechnicianName: string;
    technicianResolution: string;

    customerId: string;
    customerName: string;
    locationId: string | null;
    locationName: string;

    deviceIds: string[];
    deviceCountInJob: number;
    deviceRows: Array<{
        deviceId: string;
        model: string | null;
        serialNumber: string | null;
        bwCounter: number | null;
        colorCounter: number | null;
        counterDelta: number | null;
    }>;

    userErrorStatus: "user_error" | "hardware_failure" | "unclassified";
    hasPartsUsed: boolean;
    partsItemCount: number;
    partsCostStatus: "actual" | "estimated" | "missing";
    partsCostTRY: number | null;
    partsCostBreakdown: Record<string, number>;
    isChargeable: boolean | null;

    slaStatus: "met" | "breached" | "estimated" | "untracked";
    repeatCallStatus: "repeat_candidate" | "not_repeat" | "unknown";

    routeStatus: "available" | "missing" | "not_applicable" | "invalid";
    distanceKm: number | null;
    estimatedTravelCostTRY: number | null;

    dataQualityFlags: string[];
}
```

`Date` kullanımı hesaplama katmanında kabul edilebilir; Firestore'a yazılan kaynak alanlar yine `Timestamp` olmalıdır. DTO ve export dönüşümü rapor sonucundan yapılmalıdır.

---

## 5. KPI Güvenilirlik Matrisi

| KPI | İlk sürüm | Güven seviyesi | Not |
|---|---:|---:|---|
| Toplam servis | Evet | Yüksek | Tarih modu açık olmalı |
| Durum dağılımı | Evet | Yüksek | Status mapping belgelenmeli |
| Ortalama çözüm süresi | Evet | Orta | Yalnız createdAt ve closedAt olanlar |
| Medyan çözüm süresi | Evet | Orta | Eksik kapanışlar hariç tutulmalı |
| P90 çözüm süresi | Evet | Orta | Minimum örneklem sayısı gösterilmeli |
| Kullanıcı hatası oranı | Evet | Orta | Unclassified paydadan ayrı tutulmalı |
| Parça kullanım oranı | Evet | Orta | usedParts/fulfillment çift sayımı çözülmeli |
| Parça maliyeti | Evet | Düşük-Orta | actual/estimated ayrımı zorunlu |
| Model servis sayısı | Evet | Orta-Yüksek | Model eksikleri ayrı gösterilmeli |
| Sayaç başına arıza | Hayır | Düşük | Baseline ve cihaz bazlı sayaç gerekir |
| SLA başarısı | Kısmi | Düşük | Yeni kayıtlarda gerçek, eski kayıtlarda estimated |
| Tekrar çağrı oranı | Kısmi | Orta | Aynı cihaz ve problem doğrulaması gerekir |
| First-Time Fix | Hayır | Düşük | Visit/reopen olay modeli gerekir |
| Seyahat maliyeti | Evet | Orta | Rota kapsamı performanstan bağımsız olmalı |

KPI kartlarında güven seviyesi veya veri kapsamı gösterilmelidir. Örneğin:

```text
Ortalama çözüm süresi: 18,4 saat
Hesaplanan kapanan servis: 126 / 184
```

---

## 6. Revize Yönetim Kokpiti

### Sekme 1: Yönetici Özeti

- Toplam servis
- Açılan servis
- Kapanan servis
- Açık servis
- İptal servis
- Ortalama, medyan ve P90 çözüm süresi
- Sınıflandırılmış kullanıcı hatası oranı
- Parça kullanım oranı
- Actual/estimated parça maliyeti
- Gerçek ve tahmini SLA sonuçlarının ayrı görünümü
- Veri kalitesi uyarıları

### Sekme 2: Teknisyen Matrisi

Kolonlar:

- Teknisyen
- Atanan iş
- Yürütülen iş
- Kapatılan iş
- Atama değişikliği
- Medyan çözüm süresi
- SLA sonucu
- Tekrar çağrı adayı
- Kullanılan parça adedi
- Veri güveni

First-Time Fix kolonu, gerekli olay modeli gelmeden eklenmemelidir.

### Sekme 3: Cihaz ve Model Analizi

- Model
- Benzersiz cihaz sayısı
- Toplam servis
- Cihaz başına servis
- Aynı cihazda tekrar servis adayı
- Kullanıcı hatası oranı
- Parça maliyeti
- Sayaç verisi bulunan cihaz oranı

Sayaç başına arıza metriği ancak baseline hazır olduktan sonra ayrı bir fazda açılmalıdır.

### Sekme 4: Lojistik

- Rota mevcut servis
- Rota eksik servis
- Tek yön ve gidiş-dönüş km
- Tahmini maliyet
- Manuel/otomatik rota
- Eksik adresler
- Fiziksel ziyaret olarak sınıflandırılamayan servisler

---

## 7. Revize Uygulama Planı

### Faz 0: İş sözleşmesi ve ölçüm kararları

Çıktılar:

- KPI sözlüğü
- Status/priority mapping tablosu
- Tarih modu kararı
- SLA gerçek/tahmini ayrımı
- Maliyet ve kur politikası
- Parça kullanım ve fulfillment birleştirme kuralı
- Ziyaret ve tekrar çağrı tanımı
- Sayaç baseline politikası

Bu faz tamamlanmadan UI geliştirmesi başlamamalıdır.

### Faz 1: Sorgu ve kapsam düzeltmesi

- Km eşleşmesini ana filtreden çıkarma
- `createdAt` ve `closedAt` modlarını ayırma
- Tenant ve tarih sınırlarını sorgu seviyesine taşıma
- Lojistik kapsamını ayrı dataset yapma
- Kayıt sayısı ve eksik veri sayısını doğrulama

**Kabul:** Km kaydı olmayan servisler yönetici özetinde görünür.

### Faz 2: Normalizer ve veri kalite katmanı

- Canonical teknisyen çözümleme
- Atanan/yürüten/kapatılan rol ayrımı
- Çoklu cihaz çözümleme
- Parça ve fulfillment deduplikasyonu
- User error üçlü sınıflandırması
- Tarih ve status normalizasyonu
- Rota durumları
- Veri kalite flag'leri

**Kabul:** Aynı test fixture için normalizer deterministik sonuç üretir.

### Faz 3: Güvenilir KPI motoru

İlk sürümde:

- Servis ve durum toplamları
- Çözüm süresi dağılımı
- Kullanıcı hatası sınıflandırması
- Parça kullanım ve maliyet kapsamı
- Model/cihaz servis sayıları
- Teknisyen iş hacmi
- Lojistik ayrı hesaplaması

**Kabul:** KPI paydaları, örneklem sayıları ve dışlanan kayıt nedenleri görülebilir.

### Faz 4: Yönetim kokpiti

- Ortak filtre barı
- Dört sekmeli ekran
- KPI kartından detay filtreleme
- Veri kalite paneli
- Güven seviyesi ve sample size görünümü
- Mobil ve masaüstü tablo davranışı

**Kabul:** UI'daki toplamlar KPI motorunun fixture sonuçlarıyla birebir eşleşir.

### Faz 5: Export ve server-side raporlama

- `ServicePerformanceReport` üzerinden PDF
- Çok sayfalı XLSX
- Export metadata
- Büyük veri için server-side job veya paginated export
- Firestore indeksleri ve maliyet ölçümü

**Kabul:** Aynı filtreyle UI, PDF ve XLSX aynı kayıt kapsamını üretir.

### Faz 6: Operasyon olaylarının zenginleştirilmesi

- SLA snapshot alanları
- Durum olayı aktörleri
- Gerçek ziyaret modeli
- Yeniden açılma olayları
- Cihaz bazlı sayaç snapshot'ları
- Gerçek First-Time Fix
- Sayaç başına arıza sıklığı

Bu faz, ilk dashboard sürümünün ön koşulu değil; ikinci ölçüm olgunluğu sürümüdür.

---

## 8. Export Tasarımı

### XLSX çalışma sayfaları

```text
Özet
Teknisyenler
Cihaz Analizi
Servis Fact
Parçalar
Lojistik
Veri Kalitesi
```

Her export'a şu metadata eklenmelidir:

- Tenant
- Oluşturulma zamanı
- Tarih modu
- Tarih aralığı
- Filtre özeti
- Kullanılan veri sürümü
- KPI hesaplama notları

### PDF

İki sayfa hedefi yalnızca yönetici özeti için geçerli olmalıdır. Detay satırları iki sayfaya sığmıyorsa yapay biçimde sıkıştırılmamalı; PDF gerektiğinde çok sayfalı devam etmelidir.

**Özet bölümü:**

- KPI kartları
- Teknisyen özeti
- Model özeti
- Veri kalitesi

**Operasyon bölümü:**

- Servis detayları
- Parça özeti
- Rota ve maliyet

---

## 9. Test Planı

### 9.1 Normalizer testleri

- Farklı teknisyen alanlarının aynı kişiye eşlenmesi
- Atanan ve işi yürüten kişinin farklı olması
- Eksik teknisyen
- Eksik kapanış tarihi
- Geçersiz tarih
- Çoklu cihaz
- Eksik cihaz modeli
- Duplicate fulfillment ve usedParts
- Farklı para birimleri
- Kur bulunamaması
- Eksik sayaç baseline'ı
- Eksik rota

### 9.2 KPI testleri

- Ortalama/medyan/P90 doğruluğu
- Açık kayıtların çözüm süresine dahil edilmemesi
- İptal kayıtlarının kurala göre dahil edilmesi
- Unclassified user error paydasının doğru olması
- Actual ve estimated maliyetin ayrılması
- Tenant izolasyonu
- Tarih modu sınırlarının gün başlangıcı/bitişi
- Aynı filtrede UI/PDF/XLSX kapsam eşitliği

### 9.3 Güvenlik ve veri erişimi

- Kullanıcının başka tenant verisini raporlayamaması
- Export endpoint'inin tenant ve yetki kontrolü
- Hassas müşteri verilerinin export kapsamı
- Rapor cache anahtarında tenant ve filtre izolasyonu

### 9.4 Performans

- 100, 1.000 ve 10.000 kayıt benchmark'ı
- İlk ekran açılış süresi
- Firestore okuma sayısı
- Export süresi
- Client heap kullanımı
- Pagination davranışı

---

## 10. Son Kabul Kriterleri

- Km kaydı olmayan servisler ana performans raporundan çıkarılmaz.
- Lojistik kapsamı performans kapsamından bağımsızdır.
- Tarih modu açıkça seçilebilir ve export'a yazılır.
- Teknisyen rolü belirsiz kayıtlar gizlenmez, veri kalitesi olarak işaretlenir.
- Ortalama, medyan ve P90 yalnızca geçerli kapanış tarihleriyle hesaplanır.
- Gerçek SLA ve tahmini geçmiş SLA birbirine karıştırılmaz.
- `fulfillmentItems` ile `usedParts` çift sayılmaz.
- Maliyet ile müşteriye yansıtılan ücret birbirinden ayrılır.
- Güncel kurla çevrilmiş eski maliyetler tahmini olarak etiketlenir.
- Sayaç baseline'ı olmayan kayıtlarda sayaç farkı `0` kabul edilmez.
- First-Time Fix, ziyaret/yeniden açılma verisi olmadan kesin KPI olarak sunulmaz.
- Aynı cihazdaki farklı servisler otomatik olarak aynı arıza kabul edilmez.
- UI, PDF ve XLSX aynı rapor sonuç modelini kullanır.
- Export işlemleri tenant ve yetki izolasyonunu korur.
- 10.000+ kayıt için client belleğine bağlı tek seferlik veri yükleme yapılmaz.

---

## 11. Sunumda Kullanılacak Dürüst Sonuç

Bu planın ana yönü doğrudur: ProServis'in servis raporu, km bilgisine bağlı bir seyahat raporu olmaktan çıkarılıp gerçek bir yönetim analitiğine dönüştürülmelidir.

Ancak kurumsal raporlama açısından kritik nokta, daha fazla KPI kartı eklemek değil, her KPI'ın ölçüm güvenilirliğini açıkça belirtmektir. Mevcut verilerle ilk sürümde çözüm süresi, servis hacmi, durum dağılımı, kullanıcı hatası sınıflandırması, parça kapsamı ve model bazlı servis sayısı uygulanabilir.

SLA, gerçek First-Time Fix, sayaç başına arıza ve gerçek tarihsel maliyet gibi göstergeler ise gerekli olay ve snapshot verileri toplandıktan sonra kesinleştirilmelidir.

Önerilen nihai sıra:

```text
KPI sözleşmesi
    -> Sorgu/kapsam düzeltmesi
    -> Normalizer ve veri kalitesi
    -> Güvenilir KPI motoru
    -> Yönetim kokpiti
    -> PDF/XLSX export
    -> SLA, ziyaret, baseline ve gerçek FTF olay modeli
```

En önemli yönetim ilkesi:

> Bir raporun güvenilirliği, gösterdiği KPI sayısıyla değil, gösterdiği sonucun hangi veriye dayandığını dürüstçe açıklamasıyla ölçülür.
