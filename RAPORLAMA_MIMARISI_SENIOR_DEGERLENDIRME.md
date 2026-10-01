# Servis Performans Raporlama Mimarisi

**Durum:** Planlama
**Kapsam:** Servis performans raporu, yönetim kokpiti, KPI motoru ve dışa aktarma
**İlgili mevcut ekran:** `/dashboard/service`
**Amaç:** Mevcut mesafe odaklı raporu, güvenilir ve gerçek bir yönetim aracına dönüştürmek.

---

## 1. Yönetici Özeti

Mevcut raporun temel problemi görsel değildir; rapor kapsamının yanlış tanımlanmasıdır.

Mevcut akışta bir servis kaydının rapora girebilmesi için müşteri-lokasyon km eşleşmesi bulunması gerekiyor. Bu nedenle rapor, performans raporu olmaktan çıkıp mesafe ve yakıt hesaplayıcısına dönüşüyor. Km bilgisi bulunmayan servisler KPI hesaplarından tamamen siliniyor.

Yeni mimarinin temel ilkeleri:

1. Performans raporu tüm filtrelenmiş servis kayıtları üzerinden hesaplanır.
2. Seyahat ve km maliyeti ayrı bir analiz alanıdır.
3. Ham `ServiceRecord` doğrudan arayüze veya PDF'e verilmez.
4. Önce canonical raporlama modeli oluşturulur, sonra KPI hesaplanır.
5. Eksik veri gizlenmez; veri kalitesi olarak raporlanır.
6. PDF, Excel ve ekran aynı rapor sonuç modelini kullanır.
7. Bir KPI güvenilir biçimde hesaplanamıyorsa tahmini sonuç olarak sunulmaz.

---

## 2. Mevcut Sistemde Tespit Edilen Kritik Sorunlar

### 2.1 Km eşleşmesi ana filtre olarak kullanılıyor

`PerformanceReportDialog` içinde `findEntryForService` başarısız olursa servis `filteredServices` kümesine alınmıyor. Ayrıca rapor üretimi için en az bir müşteri-lokasyon satırı zorunlu tutuluyor.

Sonuç:

- Km tablosuna eklenmemiş servisler rapordan kayboluyor.
- 200 servis kapatılmış olsa bile rapor sıfır kayıt gösterebiliyor.
- Yönetici raporu oluşturmak için önce lojistik verisi hazırlamak zorunda kalıyor.
- KPI sonuçları gerçek servis hacmini temsil etmiyor.

### 2.2 Tarih seçimi belirsiz ve hatalı sonuç üretebilir

Mevcut tarih seçimi `createdAt || closedAt` mantığıyla çalışıyor. `createdAt` çoğu kayıtta bulunduğu için `closedAt` pratikte kullanılmıyor.

Bu iki farklı rapor türünü birbirine karıştırır:

- Bu dönemde açılan servisler
- Bu dönemde kapanan servisler

Rapor ekranında tarih modu açıkça seçilmelidir.

### 2.3 Teknisyen alanları dağınık

`ServiceRecord` içinde aynı bilgiyi temsil eden birden fazla alan bulunuyor:

- `technicianId`
- `technicianUid`
- `assignedTechnicianId`
- `assignedTechnicianUid`
- `assignedToUid`
- `technicianName`
- `assignedTechnicianName`
- `assignedToName`
- Global teknisyen ID alanları

Mevcut rapor yalnızca bazı alanları kullandığı için aynı teknisyen farklı isimlerle veya ayrı kişiler gibi gruplanabilir.

### 2.4 Mevcut PDF gerçek KPI raporu değil

Mevcut PDF ağırlıklı olarak şunları gösteriyor:

- Teknisyen bazlı servis adedi
- Müşteri-lokasyon mesafesi
- Seyahat maliyeti
- Servis detay listesi

Aşağıdaki önemli göstergeler hesaplanmıyor:

- Ortalama çözüm süresi
- Medyan ve P90 çözüm süresi
- SLA başarısı
- Kullanıcı hatası oranı
- Parça kullanım oranı
- Parça maliyeti
- Cihaz/model güvenilirliği
- Teknisyen verimlilik karşılaştırması

---

## 3. Rapor Kapsamı İçin Temel Mimari Karar

Raporlama veri kümeleri ikiye ayrılmalıdır:

```text
allFilteredServices
    -> yönetici özeti
    -> teknisyen performansı
    -> cihaz/model analizi
    -> servis detayları

servicesWithRouteData
    -> lojistik analizi
    -> toplam km
    -> seyahat maliyeti
```

Km bilgisi olmayan kayıtlar ana rapordan çıkarılmamalıdır. Lojistik sekmesinde ayrıca şu bilgiler gösterilmelidir:

- Rota bilgisi bulunan servis sayısı
- Rota bilgisi eksik servis sayısı
- Eksik adres sayısı
- Hesaplanamayan maliyet
- Otomatik ve manuel rota oranı

---

## 4. Raporlama Veri Katmanı

Ham `ServiceRecord` kaydı doğrudan KPI hesaplarına verilmemelidir. Önce ortak bir raporlama modeli oluşturulmalıdır.

### 4.1 Önerilen `ServiceReportFact`

```typescript
type ServiceReportFact = {
    serviceId: string;
    tenantId: string;

    openedAt?: Timestamp;
    closedAt?: Timestamp;
    resolutionDurationMinutes?: number;

    status: ServiceStatus;
    priority: ServiceRecord["priority"];

    technicianId?: string;
    technicianName: string;

    customerId: string;
    customerName: string;
    deviceId?: string;
    deviceModel?: string;
    deviceSerialNumber?: string;

    userError: boolean | null;
    hasParts: boolean;
    partsQuantity: number;
    partsCostByCurrency: Record<string, number>;

    chargeableService: boolean | null;
    slaDueAt?: Timestamp;
    slaResult?: "met" | "breached" | "unknown";

    routeStatus: "available" | "missing" | "invalid";
    routeDistanceKm?: number;

    dataQualityFlags: string[];
};
```

### 4.2 Normalizasyon akışı

```text
ServiceRecord[]
    -> normalizeServiceForReporting()
    -> tarih filtresi
    -> teknisyen/durum/öncelik filtresi
    -> KPI hesaplama
    -> tablo modeli
    -> PDF / XLSX / UI
```

Normalizasyon fonksiyonu şu sorumlulukları taşımalıdır:

- Teknisyen kimliğini çözümlemek
- Teknisyen adını güncel personel kaydından almak
- Tarih alanlarını güvenli biçimde dönüştürmek
- Parça listesini normalize etmek
- Bilinmeyen alanları `unknown` olarak işaretlemek
- Rota bilgilerinin varlığını kontrol etmek
- Eksik verileri `dataQualityFlags` içine yazmak

---

## 5. Canonical Teknisyen Kimliği

Gruplama isimle değil, mümkün olduğunca kimlik ile yapılmalıdır.

### 5.1 Kimlik önceliği

```text
canonicalTechnicianId
    = globalTechnicianId
    || technicianGlobalId
    || assignedGlobalTechnicianId
    || technicianId
    || assignedTechnicianId
    || assignedToUid
```

### 5.2 İsim önceliği

```text
canonicalTechnicianName
    = personel dizininden çözülen güncel isim
    || technicianName
    || assignedTechnicianName
    || assignedToName
    || "Atama Yok"
```

### 5.3 Çözümleme kuralları

- Aynı kişi farklı isim yazımlarıyla tek kişi olarak gruplanmalıdır.
- Kimlik bulunamazsa isim normalizasyonu yalnızca fallback olarak kullanılmalıdır.
- İsim eşleşmesi belirsizse kayıt sessizce birleştirilmemeli, veri kalitesi uyarısı üretilmelidir.
- Atanan teknisyen ile işi tamamlayan teknisyen farklıysa bu iki rol ayrı tutulmalıdır.

---

## 6. KPI Tanımları

### 6.1 Güvenilir biçimde hesaplanabilecek KPI'lar

Mevcut alanlar ve normalizasyonla şu KPI'lar üretilebilir:

- Toplam servis sayısı
- Durum dağılımı
- Açık servis sayısı
- Kapanan servis sayısı
- İptal servis sayısı
- Kapanma oranı
- `closedAt - createdAt` çözüm süresi
- Ortalama çözüm süresi
- Medyan çözüm süresi
- P90 çözüm süresi
- Kullanıcı hatası oranı
- Parça kullanılan servis oranı
- Toplam parça adedi
- Parça maliyeti
- Marka/model bazlı servis sayısı
- Teknisyen bazlı servis sayısı
- Ücretli ve sözleşmeli servis dağılımı

### 6.2 MTTR tanımı

İlk sürümde MTTR şu şekilde tanımlanmalıdır:

```text
closedAt - createdAt
```

Bu değer gerçek teknisyen müdahale süresi değil, toplam çözüm süresidir. Bu nedenle ekranda "Ortalama Çözüm Süresi" olarak gösterilmesi daha doğrudur.

İleride gerçek müdahale süresi için ayrıca şu zamanlar tutulmalıdır:

- Atanma zamanı
- İlk müdahale zamanı
- Teknisyen varış zamanı
- Çözüm zamanı

### 6.3 SLA başarısı

`priority` alanı tek başına SLA hesabı için yeterli değildir. Servis açılırken SLA hedefi snapshot olarak kaydedilmelidir.

```typescript
slaPolicyId?: string;
slaDueAt?: Timestamp;
slaStartedAt?: Timestamp;
slaPausedAt?: Timestamp;
slaResolvedAt?: Timestamp;
slaStatus?: "met" | "breached" | "paused" | "not_applicable";
```

SLA sonucu daha sonra ayarlar değişse bile geçmiş servislerde değişmemelidir.

### 6.4 Kullanıcı hatası

`userError` üç durumlu değerlendirilmelidir:

```text
true      -> Kullanıcı hatası
false     -> Teknik/donanım arızası
undefined -> Sınıflandırılmamış
```

Bilinmeyen kayıtlar doğrudan teknik arıza kabul edilmemelidir.

### 6.5 Parça kullanım oranı

Parça kullanımı için yalnızca `partChanged` alanına güvenilmemelidir. Öncelikli kontrol:

```text
usedParts.length > 0
ve en az bir parçanın quantity > 0 olması
```

Ayrıca şu değerler ayrı hesaplanmalıdır:

- Parça adedi
- Parça çeşidi
- Toplam maliyet
- Ücretsiz parça maliyeti
- Ücretli parça maliyeti
- Para birimi bazlı toplamlar

### 6.6 First-Time Fix

First-Time Fix mevcut alanlardan güvenilir biçimde hesaplanamaz. Aynı servis için ikinci ziyaret, yeniden açılma veya takip işi bilgisi gerekir.

Gerekli minimum veri:

```typescript
visitCount?: number;
reopenedAt?: Timestamp;
reopenReason?: string;
followUpRequired?: boolean;
```

Daha doğru çözüm:

```text
service_visits/{visitId}
    serviceId
    visitNumber
    technicianId
    startedAt
    completedAt
    outcome
```

Bu veri oluşmadan First-Time Fix kesin KPI olarak gösterilmemelidir.

---

## 7. Tarih ve Filtreleme Modeli

Rapor ekranında açık tarih modu bulunmalıdır:

```text
created_at  -> Bu dönemde açılan servisler
closed_at   -> Bu dönemde kapanan servisler
activity    -> Bu dönemde hareket gören servisler
```

Önerilen filtreler:

- Tarih modu
- Başlangıç tarihi
- Bitiş tarihi
- Teknisyen
- Servis durumu
- Öncelik
- Müşteri
- Marka/model
- Kullanıcı hatası
- Parça kullanımı
- SLA durumu
- Rota durumu

Filtre sonucu ve rapor tarihi export dosyasına da yazılmalıdır.

---

## 8. Yönetim Kokpiti Sekmeleri

### 8.1 Yönetici Özeti

KPI kartları:

- Toplam servis
- Açılan servis
- Kapanan servis
- Açık servis
- İptal servis
- Ortalama çözüm süresi
- Medyan çözüm süresi
- P90 çözüm süresi
- SLA başarısı
- Kullanıcı hatası oranı
- Parça kullanım oranı
- Veri kalitesi uyarısı

KPI kartları tıklanabilir olmalı ve ilgili servis detaylarını açmalıdır.

### 8.2 Teknisyen Verimliliği

Kolonlar:

- Teknisyen
- Atanan iş
- Kapatılan iş
- Açık iş
- Ortalama çözüm süresi
- Medyan çözüm süresi
- SLA başarısı
- First-Time Fix
- Kullanılan parça adedi
- Yeniden açılan servis
- Eksik veri uyarısı

Sıralama yalnızca iş adedine göre yapılmamalıdır. Yönetici farklı metriklere göre sıralama yapabilmelidir.

### 8.3 Cihaz ve Model Güvenilirliği

Gruplama seçenekleri:

- Marka
- Model
- Cihaz
- Müşteri
- Arıza türü

Metrikler:

- Servis sayısı
- Benzersiz cihaz sayısı
- Cihaz başına servis sıklığı
- Ortalama çözüm süresi
- Tekrar servis oranı
- Parça maliyeti
- Kullanıcı hatası oranı

Toplam servis sayısı ile cihaz başına servis sıklığı birbirinden ayrılmalıdır. Büyük portföye sahip model otomatik olarak güvenilmez kabul edilmemelidir.

### 8.4 Lojistik ve Seyahat Maliyeti

Bu sekme mevcut rota ve km motorunun yeni yeri olmalıdır.

Gösterilecek bilgiler:

- Rota bulunan servis sayısı
- Rota eksik servis sayısı
- Toplam tek yön km
- Toplam gidiş-dönüş km
- Tahmini maliyet
- Eksik adresler
- Otomatik/manual rota oranı

Her servis kaydı fiziksel ziyaret anlamına gelmeyebilir. Toner teslimi, telefonla çözüm, atölye işlemi ve saha ziyareti ayrıştırılmalıdır.

---

## 9. Ortak Rapor Sonuç Modeli

PDF, Excel ve arayüz aynı sonucu kullanmalıdır.

```typescript
type ServicePerformanceReport = {
    summary: {
        totalServices: number;
        closedServices: number;
        pendingServices: number;
        cancelledServices: number;
        averageResolutionMinutes?: number;
        medianResolutionMinutes?: number;
        p90ResolutionMinutes?: number;
        userErrorRate?: number;
        partUsageRate?: number;
        slaComplianceRate?: number;
        firstTimeFixRate?: number;
    };

    technicianRows: TechnicianPerformanceRow[];
    deviceRows: DeviceReliabilityRow[];
    travelRows: TravelCostRow[];
    detailRows: ServiceReportFact[];

    dataQuality: {
        missingDates: number;
        missingTechnicians: number;
        missingRouteData: number;
        unclassifiedUserErrors: number;
        unknownSla: number;
    };
};
```

---

## 10. Export Stratejisi

### 10.1 PDF

PDF iki bölüme ayrılmalıdır.

**Yönetici özeti:**

- KPI kartları
- Teknisyen başarı tablosu
- Model güvenilirlik özeti
- Veri kalitesi uyarıları

**Detay:**

- Servis satırları
- Tarihler
- Durumlar
- Teknisyen
- Yapılan işlemler
- Kullanılan parçalar
- Rota ve maliyet bilgileri

### 10.2 XLSX

Excel dosyasında şu sayfalar bulunmalıdır:

```text
Özet
Teknisyenler
Cihazlar
Servis Detayları
Parçalar
Seyahat
Veri Kalitesi
```

Ham detaylarda şu alanlar bulunmalıdır:

- Kaynak servis ID'si
- Canonical teknisyen ID'si
- Canonical teknisyen adı
- Kullanılan tarih modu
- Rota durumu
- KPI hesaplama bayrakları
- Veri eksikliği açıklaması

---

## 11. Uygulama Fazları

### Faz 0: Metrik ve veri sözleşmesi

- Tarih kapsamını kesinleştirme
- MTTR/çözüm süresi tanımını yazma
- SLA başlangıç ve bitiş kurallarını yazma
- First-Time Fix tanımını kesinleştirme
- İptal servislerin oranlara etkisini belirleme
- Çoklu para birimi politikasını belirleme
- Fiziksel ziyaret tanımını belirleme

Bu faz tamamlanmadan dashboard geliştirmesine başlanmamalıdır.

### Faz 1: Raporlama normalizer'ı

- Canonical teknisyen kimliği
- Tarih normalizasyonu
- Durum ve öncelik dönüşümü
- Parça normalizasyonu
- Kullanıcı hatası sınıflandırması
- Rota durumu
- Veri kalite bayrakları

### Faz 2: Mevcut raporun kök düzeltmesi

- Km eşleşmesini ana filtreden çıkarma
- Tarih modunu ekleme
- Teknisyen filtresini canonical ID'ye taşıma
- Rota eksik kayıtlarını görünür kılma
- Km bilgisi olmadan rapor üretme

### Faz 3: KPI motoru

İlk sürümde güvenilir biçimde hesaplanabilen KPI'lar:

- Servis toplamları
- Durum dağılımı
- Çözüm süreleri
- Kullanıcı hatası oranı
- Parça kullanım oranı
- Parça maliyeti
- Model bazlı servis sayısı
- Teknisyen bazlı iş sayısı
- Ücretli/sözleşmeli dağılımı

### Faz 4: Eksik olay modelinin eklenmesi

- SLA snapshot alanları
- Atanma ve ilk müdahale zamanları
- Ziyaret kayıtları
- Yeniden açılma olayları
- İşlem aktörü ve olay zamanı

### Faz 5: Yönetim kokpiti

- Dört sekmeli ekran
- Ortak filtre alanı
- KPI'dan detay listeye geçiş
- Teknisyen tablosu
- Cihaz/model tablosu
- Lojistik tablosu
- Veri kalitesi paneli
- Mobil görünüm

### Faz 6: Export

- Ortak sonuç modelinden PDF
- Çok sayfalı XLSX
- Filtre ve tarih modunu export metadata olarak yazma
- Büyük veri için backend export job planı

### Faz 7: Ölçekleme

Veri büyüdüğünde client-side tüm servisleri çekmek yerine:

- Tarih aralığına göre server-side sorgu
- Tenant ve tarih indeksleri
- Günlük/aylık aggregate dokümanları
- Büyük Excel export için backend job
- Cache'lenmiş yönetim metrikleri

kullanılmalıdır.

---

## 12. Kabul Kriterleri

- Km bilgisi olmayan servis ana rapordan silinmemeli.
- Km bilgisi olmayan servisler lojistik sekmesinde görünmeli.
- Açılış ve kapanış tarihine göre ayrı rapor üretilebilmeli.
- Aynı teknisyen farklı alanlarda kayıtlı olsa da tek kişi görünmeli.
- Bilinmeyen kullanıcı hatası teknik arıza sayılmamalı.
- Ortalama, medyan ve P90 çözüm süreleri ayrı gösterilmeli.
- SLA geçmişteki servisler için açılış anındaki hedefle hesaplanmalı.
- First-Time Fix gerekli olay verisi olmadan kesin KPI olarak sunulmamalı.
- PDF ve Excel aynı rapor sonuç modelini kullanmalı.
- Rapor kapsamı ve rota kapsamı birbirinden bağımsız olmalı.
- Eksik veri yöneticiye açıkça gösterilmeli.
- Aynı filtrelerle UI, PDF ve Excel aynı servis sayısını üretmeli.
- Tenant izolasyonu tüm raporlama sorgularında korunmalı.
- Büyük veri kümelerinde arayüz tarayıcı belleğine bağımlı olmamalı.

---

## 13. Önerilen Öncelik Sırası

```text
Metrik sözleşmesi
    -> Canonical raporlama modeli
    -> Km filtresi kök düzeltmesi
    -> Güvenilir KPI motoru
    -> SLA ve ziyaret olayları
    -> Yönetim kokpiti
    -> PDF ve XLSX export
    -> Server-side aggregate ve ölçekleme
```

## Sonuç

Bu çalışma yalnızca mevcut rapora birkaç KPI kartı eklemek olarak ele alınmamalıdır. Önce raporun gerçek veri kapsamı düzeltilmeli, ardından canonical normalizer ve ortak KPI motoru oluşturulmalıdır.

En kritik karar şudur:

> Lojistik verisi eksik olduğu için servis performans verisi kaybedilmemelidir.

Bu ayrım yapılmadan geliştirilecek yeni sekmeler, mevcut eksik sonuçları yalnızca daha profesyonel bir arayüzle göstermiş olur.
