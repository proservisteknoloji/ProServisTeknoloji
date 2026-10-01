# Müşteri Talepleri ve Portal Mimarisi Güncelleme Planı

**Durum:** Planlama
**Kapsam:** `/dashboard/customer-requests` operasyon ekranı ve `/portal` müşteri portalı
**Amaç:** Müşteri taleplerinin kayıpsız, izlenebilir, güvenli ve operasyon ekibinin günlük kullanımına uygun şekilde yönetilmesi.

---

## 1. Hedefler

- Müşteri taleplerini operasyon merkezi haline getirmek.
- Talep ile servis kaydı arasında kalıcı ve güvenilir ilişki kurmak.
- Aynı talebin iki kez servise dönüştürülmesini engellemek.
- İç operasyon notlarını müşteri görünümünden kesin olarak ayırmak.
- Müşteriye talep, servis, cihaz ve planlama süreci hakkında yeterli görünürlük sağlamak.
- Filtre, seçili talep ve drawer durumunu URL üzerinden paylaşılabilir hale getirmek.
- Mevcut eski kayıtları kaybetmeden yeni veri modeline geçirmek.

---

## 2. Mevcut Durum ve Tespitler

### Yönetim ekranı

Mevcut `/dashboard/customer-requests` ekranında:

- Talep istatistikleri bulunuyor.
- Aktif, tamamlanmış ve tüm talepler ayrımı var.
- Durum değiştirme işlemi var.
- Talebi servis oluşturma akışına yönlendirme var.
- Portal hesabı oluşturma ve yönetme işlemleri aynı sayfada bulunuyor.

Eksik kalan başlıklar:

- Talep numarası
- Öncelik
- SLA takibi
- Gelişmiş arama ve filtreler
- Teknisyen atama
- Planlanan ziyaret
- Talep-servis ilişkisinin görünür ve kalıcı olması
- İç not/müşteri notu ayrımı
- Talep detayının sayfadan ayrılmadan incelenmesi
- Eşzamanlı işlemlerde veri kaybını önleme

### Müşteri portalı

Mevcut portal:

- Yeni toner veya arıza talebi oluşturabiliyor.
- Müşterinin cihazlarını gösteriyor.
- Talep geçmişini gösteriyor.
- Son durum notunu gösteriyor.

Eksik kalan başlıklar:

- Talep detay zaman akışı
- Planlanan ziyaret tarihi
- Atanan teknisyen veya teknik ekip bilgisi
- Servis geçmişi
- Cihaz detayları
- Sayaç ve toner bilgileri
- Garanti ve bakım bilgileri
- Sözleşme görünümü
- Dosya ve servis raporları
- İsteğe bağlı fatura ve cari görünümü

---

## 3. Temel Mimari Kararlar

### 3.1 Talep numarası

Talep numarası kullanıcıya gösterilen takip numarasıdır. Firestore document ID ile aynı şey değildir.

Format:

```text
TLP-2026-000001
```

Üretim kuralları:

- Yalnızca backend tarafından üretilir.
- İstemci tarafında rastgele numara üretilemez.
- Firestore transaction ile atomik sayaç artırılır.
- Sayaç tenant ve yıl bazında tutulur:

```text
tenants/{tenantId}/counters/customer_requests_2026
```

- Aynı anda açılan taleplerde numara çakışmamalıdır.
- Portal ve personel tarafından açılan talepler aynı ortak backend oluşturma akışını kullanmalıdır.

> Firestore otomatik document ID'si UUID olarak kabul edilmemelidir. Şema açıklamasında yalnızca `Firestore document ID` denmelidir.

### 3.2 Tarih ve saatler

Veritabanında tarih alanları yalnızca Firestore `Timestamp` olarak tutulacaktır.

Önerilen alanlar:

```typescript
plannedVisitAt?: Timestamp;
slaDueAt?: Timestamp;
```

`string` dönüşümü yalnızca API DTO veya UI gösterim katmanında yapılacaktır.

### 3.3 Servise dönüşüm

Talebin servise dönüştürülmesi gerçek anlamda idempotent olmalıdır. Sadece `conversionStatus` okumak yeterli değildir.

Dönüşüm durumu:

```typescript
conversionStatus: 'not_converted' | 'converting' | 'converted' | 'failed';
```

Ek işlem alanları:

```typescript
conversionStartedAt?: Timestamp;
conversionAttemptId?: string;
conversionError?: string;
```

Dönüşüm akışı:

1. Firestore transaction ile talep okunur.
2. Talep zaten `converted` ve `linkedServiceId` içeriyorsa mevcut servis döndürülür.
3. Talep `converting` ise aktif işlem kontrol edilir.
4. Talep atomik olarak `converting` durumuna alınır.
5. Servis kaydı `customerRequestId` ile oluşturulur.
6. Talep `linkedServiceId` ile güncellenir.
7. Talep `converted` durumuna alınır.
8. Hata oluşursa `failed` durumuna geçilir ve tekrar denenebilir.

İki ayrı kullanıcı aynı anda dönüşüm başlatsa bile yalnızca bir servis kaydı oluşmalıdır.

### 3.4 İlişkinin gerçek kaynağı

İki yönde referans tutulabilir:

```typescript
CustomerRequest.linkedServiceId
ServiceRecord.customerRequestId
```

Ancak servis kaydı ilişki için ana kaynak kabul edilmelidir. Talep üzerindeki servis bilgileri hızlı listeleme için cache/reference olarak kullanılmalıdır.

`linkedServiceStatus` gerçek kaynak değildir. Servis durumu değiştiğinde cache güncellenemese bile detay ekranı gerçek `ServiceRecord` üzerinden doğrulama yapmalıdır.

### 3.5 İç not ve müşteri notu

Tek bir not alanı hem personel hem müşteri için kullanılmayacaktır.

Yeni event kayıtlarında görünürlük zorunlu olmalıdır:

```typescript
visibility: 'customer' | 'internal';
```

Müşteri portalı hiçbir koşulda `internal` kayıtları almamalıdır.

İç ve müşteri çözüm notları da ayrılmalıdır:

```typescript
customerResolutionNote?: string;
internalResolutionNote?: string;
```

`resolutionNote` tek başına portal DTO'suna aktarılmamalıdır.

---

## 4. Önerilen Veri Modeli

### 4.1 CustomerRequest

```typescript
export type CustomerRequestPriority = 'low' | 'normal' | 'high' | 'urgent';

export type CustomerRequestConversionStatus =
    | 'not_converted'
    | 'converting'
    | 'converted'
    | 'failed';

export interface CustomerRequest {
    id: string;
    requestNumber: string;
    tenantId: string;
    customerId: string;
    customerName: string;
    deviceId?: string;
    deviceSerialNumber?: string;
    deviceModel?: string;
    type: 'toner' | 'fault';
    status: 'pending' | 'in_progress' | 'resolved' | 'cancelled';
    priority: CustomerRequestPriority;
    subject: string;
    description: string;
    tonerColors?: string[];

    assignedTechnicianId?: string;
    assignedTechnicianName?: string;
    plannedVisitAt?: Timestamp;
    slaDueAt?: Timestamp;

    conversionStatus: CustomerRequestConversionStatus;
    conversionStartedAt?: Timestamp;
    conversionAttemptId?: string;
    conversionError?: string;
    linkedServiceId?: string;
    linkedServiceNumber?: string;
    linkedServiceStatus?: string;

    customerResolutionNote?: string;
    internalResolutionNote?: string;
    createdBy: 'portal' | 'staff';
    createdAt: Timestamp;
    updatedAt: Timestamp;
    resolvedAt?: Timestamp;
}
```

Yeni zorunlu alanlar eski kayıtlarda bulunmayabilir. Okuma katmanı migration tamamlanana kadar güvenli varsayılan değerler kullanmalıdır.

### 4.2 ServiceRecord

```typescript
customerRequestId?: string;
customerRequestNumber?: string;
```

Servis oluşturulduğunda bu alanlar kaydın parçası olarak yazılmalıdır.

### 4.3 Talep olayları

Kısa vadede mevcut `statusLogs` okunabilir. Yeni sistemde tercih edilen yapı:

```text
tenants/{tenantId}/customer_requests/{requestId}/events/{eventId}
```

Event modeli:

```typescript
export interface CustomerRequestEvent {
    id: string;
    requestId: string;
    actionType:
        | 'request_created'
        | 'status_changed'
        | 'note_added'
        | 'technician_assigned'
        | 'visit_scheduled'
        | 'converted_to_service'
        | 'attachment_added'
        | 'request_resolved';
    status?: CustomerRequestStatus;
    note?: string;
    visibility: 'customer' | 'internal';
    changedAt: Timestamp;
    changedByUid?: string;
    changedByName?: string;
    source: 'portal' | 'staff' | 'system';
}
```

Bunun avantajları:

- Eşzamanlı notlarda array ezilmesi önlenir.
- Timeline sayfalanabilir.
- Event geçmişi sınırsız büyüyebilir.
- Portal ve operasyon görünürlüğü sorgu seviyesinde ayrılabilir.

---

## 5. SLA Kuralları

İlk aşamada basit takvim saati hesabı kullanılabilir.

| Talep | Öncelik | SLA |
|---|---|---:|
| Her tür | Urgent | 4 saat |
| Her tür | High | 8 saat |
| Arıza | Normal | 24 saat |
| Toner | Normal | 48 saat |
| Her tür | Low | 72 saat |

Öncelik türden önce gelir:

```text
Urgent toner talebi = 4 saat
High toner talebi = 8 saat
Normal toner talebi = 48 saat
```

İlk aşama dışında ayrıca şu konular kararlaştırılmalıdır:

- Mesai saatleri
- Hafta sonu ve resmi tatiller
- Müşteri yanıtı beklenirken SLA'nın durması
- İptal durumunda SLA'nın kapanması
- Yeniden açılan taleplerde SLA davranışı

SLA aşımı:

```text
slaDueAt < now && status !== 'resolved' && status !== 'cancelled'
```

SLA kartı ve tablo satırı aynı hesaplama yardımcı fonksiyonunu kullanmalıdır.

---

## 6. Portal API Güvenliği

Portal endpoint'leri ham Firestore dokümanı döndürmeyecektir.

### 6.1 Portal DTO

```typescript
export interface PortalCustomerRequestDTO {
    id: string;
    requestNumber: string;
    subject: string;
    description: string;
    type: 'toner' | 'fault';
    status: CustomerRequestStatus;
    priority: CustomerRequestPriority;
    deviceSerialNumber?: string;
    deviceModel?: string;
    plannedVisitAt?: string;
    linkedServiceNumber?: string;
    linkedServiceStatus?: string;
    customerResolutionNote?: string;
    events: Array<{
        actionType: string;
        status?: CustomerRequestStatus;
        note?: string;
        changedAt: string;
        actorLabel?: string;
    }>;
    createdAt: string;
    updatedAt: string;
}
```

Portal DTO'suna şu alanlar aktarılmamalıdır:

- İç notlar
- İç çözüm notları
- Maliyet bilgileri
- Personel UID bilgileri
- Depo ve parça maliyetleri
- Dahili hata detayları
- Müşteriye açık olmayan ekler

`changedByName` doğrudan müşteriye gönderilmemeli; müşteri görünümü için gerekirse `actorLabel` üretilmelidir:

```text
Müşteri
Teknik Servis Ekibi
Sistem
```

### 6.2 Cihaz sahipliği

`POST /api/portal/requests` içinde gelen `deviceId` ve seri numarası mutlaka oturumdaki `customerId` ile doğrulanmalıdır.

Aşağıdaki durumlar reddedilmelidir:

- Cihaz başka müşteriye aitse
- Cihaz bulunamıyorsa
- `deviceId` ile `deviceSerialNumber` eşleşmiyorsa
- Portal oturumundaki tenant ile cihaz tenant'ı farklıysa

Talep oluştururken cihaz bilgileri istemciden güvenilmemeli, backend tarafından doğrulanmış cihaz kaydından alınmalıdır.

### 6.3 Event filtreleme

Portal API yalnızca:

```text
visibility === 'customer'
```

olan event kayıtlarını döndürmelidir. Eksik visibility alanı güvenlik nedeniyle `internal` kabul edilmelidir.

---

## 7. Yönetim Ekranı Mimarisi

Mevcut monolitik sayfa tek yerde büyütülmeyecektir. İlk aşamada mantıksal sınırlar:

```text
src/app/dashboard/customer-requests/page.tsx
src/components/customer-requests/
    useCustomerRequests.ts
    CustomerRequestStats.tsx
    CustomerRequestFilters.tsx
    CustomerRequestTable.tsx
    CustomerRequestDetailDrawer.tsx
    CustomerPortalAccountsTab.tsx
```

`page.tsx` yalnızca sayfa orkestrasyonu ve üst seviye sekmeleri yönetmelidir.

### 7.1 KPI kartları

- Açık talepler
- Bekleyen talepler
- İşlemdeki talepler
- SLA aşan talepler
- Bugün gelen talepler
- Atama bekleyen talepler
- Bugün planlanan ziyaretler
- Son 7 günde tamamlananlar

KPI kartları yalnızca bilgi göstermemeli, tıklandığında ilgili URL filtresini uygulamalıdır.

### 7.2 Filtreler

Filtreler URL query parametreleriyle tutulmalıdır:

```text
/dashboard/customer-requests
    ?tab=active
    &status=pending
    &priority=urgent
    &technician=uid
    &dateFrom=2026-09-01
    &dateTo=2026-09-06
    &search=kyocera
    &requestId=firestore-document-id
```

Filtreler:

- Serbest arama
- Talep numarası
- Müşteri
- Cihaz/model/seri numarası
- Talep türü
- Öncelik
- Durum
- Teknisyen
- Tarih aralığı
- SLA durumu

Arama debounce edilebilir. Kayıt sayısı büyüdüğünde istemci tarafı filtreleme yerine backend sorgulama veya arama altyapısı planlanmalıdır.

### 7.3 Tablo

Sütunlar:

- Talep no
- Müşteri
- Cihaz ve seri no
- Talep türü
- Öncelik
- Bekleme süresi/SLA
- Durum
- Teknisyen
- Planlanan ziyaret
- Bağlı servis
- Aksiyonlar

Masaüstünde yoğun tablo, mobilde aynı veri kaynağını kullanan kart görünümü kullanılmalıdır.

### 7.4 Detay drawer

Drawer sekmeleri:

```text
Özet
Zaman Akışı
Notlar
Servis
Cihaz
Dosyalar
```

Drawer URL ile açılmalıdır:

```text
?requestId=<firestore-document-id>
```

Talep numarası ile paylaşım gerekiyorsa ayrı parametre kullanılmalıdır:

```text
?requestNumber=TLP-2026-000001
```

İşlemler:

- Durum değiştir
- İç not ekle
- Müşteriye açık not ekle
- Teknisyen ata
- Ziyaret tarihi planla
- Servise dönüştür
- Bağlı servise git
- Dosya ekle
- Talebi tamamla veya iptal et

---

## 8. Portal Ekranı

Portal ana ekranı yalnızca talep formu olmaktan çıkarılmalıdır.

Önerilen menü:

```text
Genel Bakış
Taleplerim
Servislerim
Cihazlarım
Bakım ve Sözleşmeler
Belgeler
Faturalar
Profil ve İletişim
```

İlk portal sürümünde öncelik:

1. Açık talep sayısı
2. İşlemdeki servisler
3. Yaklaşan ziyaret
4. Cihaz sayısı
5. Son durum güncellemeleri
6. Yeni talep oluşturma

Cihaz detayında:

- Marka/model/seri no
- Durum
- Son iletişim zamanı
- Toner seviyeleri
- Son sayaç
- Garanti bilgisi
- Bakım tarihi
- Servis geçmişi

Finansal bilgiler ilk sürüme dahil edilmemelidir. Fatura ve cari görünümü firma ayarıyla ayrıca açılmalıdır.

---

## 9. Migration ve Geriye Dönük Uyumluluk

Yeni alanlar eski kayıtlar için otomatik varsayılanlarla okunmalıdır.

| Alan | Eski kayıtlardaki varsayılan |
|---|---|
| `requestNumber` | Kontrollü migration ile üretilir |
| `priority` | `normal` |
| `conversionStatus` | `not_converted` |
| `updatedAt` | `createdAt` |
| `customerName` | Müşteri kaydından tamamlanır |
| `description` | Boş string |
| `statusLogs.visibility` eksik | `internal` kabul edilir |
| `statusLogs.actionType` eksik | `status_changed` veya migration kuralı |

Migration özellikleri:

- Tekrar çalıştırılabilir olmalıdır.
- Yarım kaldığında kaldığı yerden devam edebilmelidir.
- Önce dry-run raporu üretmelidir.
- Değiştirilen kayıt sayısını loglamalıdır.
- Geri dönüş/backup stratejisi bulunmalıdır.

Eski kayıtlara geçmişe dönük sahte müşteri notu eklenmemelidir.

---

## 10. Faz Bazlı Uygulama Planı

### Faz 0: Veri sözleşmesi ve kararlar

- Durum, öncelik ve SLA kurallarını kesinleştirme
- İç/müşteri görünürlük kurallarını belirleme
- Portal DTO sözleşmesini yazma
- Migration planını ve varsayılanları belirleme
- `requestId` ve `requestNumber` URL kullanımını ayırma

### Faz 1: Backend talep altyapısı

- Ortak server-side talep oluşturma akışı
- Transaction tabanlı talep numarası
- Varsayılan priority ve SLA üretimi
- `plannedVisitAt` ve conversion alanları
- Event yazma altyapısı
- ServiceRecord ilişki alanları

### Faz 2: Yönetim ekranı

- Hook ve veri orkestrasyonu
- KPI kartları
- URL tabanlı filtreler
- Operasyon tablosu
- Mobil görünüm
- Detay drawer
- İç/müşteri not ayrımı

### Faz 3: İdempotent servis dönüşümü

- Transaction tabanlı dönüşüm kilidi
- Tekrar çalıştırılabilir servis oluşturma
- `customerRequestId` bağlantısı
- Başarısız dönüşüm ve yeniden deneme
- Bağlı servis durumunun gösterimi
- Tutarlılık kontrolü

### Faz 4: Portal güvenliği ve talep detayları

- Cihaz sahipliği doğrulaması
- Portal DTO izolasyonu
- Müşteri görünür event filtrelemesi
- Portal talep detay ekranı
- Ziyaret ve servis durumu görünürlüğü

### Faz 5: Cihaz ve servis geçmişi

- Cihaz detay sayfası
- Toner ve telemetry bilgileri
- Sayaç geçmişi
- Garanti ve bakım bilgileri
- Servis raporları ve ekler

### Faz 6: Sözleşme ve finans

- Sözleşme görünümü
- Bakım kapsamı
- Fatura görünümü
- Cari/bakiye görünümü
- Firma bazlı portal görünürlük ayarları

---

## 11. Test Planı

### Backend testleri

- Aynı anda iki talep açıldığında request number çakışmaması
- Aynı talebin iki kez servise dönüştürülmesinde tek servis oluşması
- Dönüşüm ortada başarısız olduğunda yeniden denenebilmesi
- Sayaç transaction yarışlarının doğru sonuçlanması
- Tenant izolasyonu
- Portal cihaz sahipliği kontrolü
- Internal event kayıtlarının portal API'den dönmemesi
- Eski kayıtların varsayılanlarla okunabilmesi

### Frontend testleri

- URL filtresi sayfa yenilemeden sonra korunması
- Drawer linkiyle doğrudan doğru talebin açılması
- KPI tıklamasının doğru filtreyi uygulaması
- SLA durum renginin doğru gösterilmesi
- Mobil kart ve masaüstü tablonun aynı kayıtları göstermesi
- İç notun portal ekranında görünmemesi
- Başarısız dönüşümün kullanıcıya tekrar deneme seçeneği sunması

### Kabul kriterleri

- Aynı talep için mükerrer servis kaydı oluşmamalı.
- Portal hiçbir internal notu almamalı.
- Talep numarası tüm tenant içinde ve ilgili yılda benzersiz olmalı.
- Filtre ve drawer URL ile tekrar açılabilmeli.
- Eski talepler yeni ekranı bozmayacak şekilde görüntülenmeli.
- SLA hesabı KPI ve tablo arasında aynı sonucu üretmeli.

---

## 12. Nihai Kararlar

1. Talep numarası `TLP-YYYY-000001` formatında backend transaction ile üretilecek.
2. Firestore document ID, request number yerine geçmeyecek.
3. Tarih alanları veritabanında yalnızca `Timestamp` tutulacak.
4. `conversionStatus` yanında gerçek transaction/lock ve `failed` recovery bulunacak.
5. Servis kaydındaki `customerRequestId` ilişki için ana kaynak kabul edilecek.
6. İç notlar ve müşteri notları kesin olarak ayrılacak.
7. Yeni event kayıtları subcollection yapısına taşınacak; eski `statusLogs` geriye dönük okunabilecek.
8. Eksik visibility alanı güvenlik gereği `internal` kabul edilecek.
9. SLA'da öncelik, talep türünden önce değerlendirilecek.
10. Portal API ham Firestore kaydı döndürmeyecek.
11. Portal talep oluştururken cihaz sahipliği backend'de doğrulanacak.
12. Finansal ve sözleşme bilgileri ayrı fazda ve firma ayarıyla açılacak.
13. Migration ve test planı tamamlanmadan üretim geçişi yapılmayacak.

---

## Sonuç

Planın uygulanabilir ve güvenilir hale gelmesi için yalnızca yeni alanlar eklemek yeterli değildir. Veri üretiminin tek merkezden yapılması, event geçmişinin güvenli tutulması, servis dönüşümünün gerçekten idempotent olması, eski kayıtların migration ile ele alınması ve portal DTO izolasyonu birlikte uygulanmalıdır.

Önerilen uygulama sırası:

```text
Veri sözleşmesi ve migration
→ Ortak backend talep oluşturma
→ Güvenlik ve DTO katmanı
→ İdempotent servis bağlantısı
→ Yönetim tablosu ve drawer
→ Portal talep detayları
→ Cihaz ve servis geçmişi
→ Sözleşme ve finans
```
