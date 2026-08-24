# Android Teknik Uygulama Promptu (Mevcut ProServis Firebase Yapısına Uyumlu)

Sen kıdemli bir Android (Kotlin) + Firebase (Firestore/Auth/Storage/FCM) geliştiricisisin. VS Code içinde üreteceğin kodlar production’a yakın, okunabilir, modüler ve test edilebilir olacak. Jetpack Compose + MVVM + Repository pattern kullan. Hilt (DI), Kotlin Coroutines + Flow kullan. Firestore offline persistence aktif olacak. UI sade, teknisyen odaklı, büyük butonlu ve minimum tıklama ile ilerleyecek.

## AMAÇ
Web panelde zaten kullanılan Firebase yapısındaki iş kayıtları teknisyen Android uygulamasında görünsün ve sahada adım adım yönetilsin. Ofis tarafı yapılan işlemleri izleyebilsin (event/audit).

## ÇOK ÖNEMLİ KISITLAR
- Multi-tenant zorunlu: tüm veri erişimi `tenantId` scoped.
- Giriş formu: `Firma Kodu (tenantId)` + `Kullanıcı Adı (email)` + `Şifre`.
- Firebase Auth email/password ile login.
- Login sonrası kullanıcı gerçekten o tenant üyesi mi kontrol et: `tenants/{tenantId}/users/{uid}`.
- Tenant izolasyonu kesin: kullanıcı başka tenant verisini göremez.
- Teknisyen sadece açık havuzdaki işleri ve kendi üstündeki işleri görsün.
- Yanlış cihazda işlem yapılmaması için seri no son 4-5 hane doğrulaması zorunlu.

## MEVCUT FIREBASE ŞEMASI (BU PROJE İLE UYUMLU)
Tüm ana koleksiyonlar tenant altında:
`tenants/{tenantId}/...`

Kullanılan koleksiyonlar:
- `users/{uid}` (tenant user kaydı)
- `customers/{customerId}`
- `customers/{customerId}/locations/{locationId}`
- `customers/{customerId}/devices/{deviceId}`
- `service_records/{serviceId}`
- `technician_tasks/{taskId}` (özellikle sayaç toplama görevleri)
- `meter_readings/{readingId}`

Notlar:
- Ayrı top-level `devices` koleksiyonu yok; cihazlar müşteri altında.
- Service durumları mevcut sistemde:
  - `Received | Assigned | In Progress | Waiting Approval | Waiting Part | Repaired | Delivery | Delivered | Cancelled`
- Technician task durumları mevcut sistemde:
  - `unassigned | assigned | in_progress | completed | cancelled`

## UYGULAMA AKIŞI (MVP - MEVCUT YAPIYA GÖRE)

### 1) Login
- Ekran: Firma Kodu (`tenantId`), Kullanıcı Adı (email), Şifre.
- `signInWithEmailAndPassword` ile giriş.
- Giriş sonrası kontrol:
  1. `tenants/{tenantId}/users/{uid}` var mı?
  2. Yoksa hata: "Yetkiniz yok".
- Başarılıysa `tenantId` DataStore’a yaz.

### 2) Ana Ekran (2 Sekme)

#### Sekme A: "Açık Havuz"
İki kaynaktan göster:
1. `service_records` içinde teknisyene atanmamış açık kayıtlar
   - Açık kayıt: status `Delivered` ve `Cancelled` değil
   - Atanmamış: `technicianId` boş/null
2. `technician_tasks` içinde `status == unassigned`

Kartta göster:
- müşteri, lokasyon/cihaz özeti, iş tipi, tarih/öncelik (varsa)

Aksiyon:
- "İşi Sahiplen"
  - Service için: `technicianId`, `technicianName` set et; status `Received` ise `Assigned` yap.
  - Task için: `technicianId`, `technicianName`, `status = assigned`.
  - Event log ekle: `CLAIM`.

#### Sekme B: "Üzerimdeki İşler"
İki kaynaktan göster:
1. Service kayıtları: `technicianId == currentUid` ve status `Delivered/Cancelled` değil
2. Task kayıtları: `technicianId == currentUid` ve status `assigned | in_progress`

Buton davranışları (service odaklı):
- `Assigned`: "Müşteriye Geldim" + "İşi Bırak"
- `In Progress`: "İşi Tamamla"

"İşi Bırak" (sadece `Assigned`):
- Service: `technicianId/technicianName` temizle, status `Received` veya mevcut iş kuralına göre açık havuza dön.
- Task: `technicianId/technicianName` temizle, `status = unassigned`.
- Event: `RELEASE`.

### 3) Müşteriye Geldim
- Service kaydında "Müşteriye Geldim" aksiyonu:
  - Service dokümana `arrivalAt`, `arrivedByUid` gibi alanlar yaz.
  - Event: `ARRIVED`.
  - Status hemen `In Progress` yapılmayacak; önce seri doğrulama ekranı açılacak.

### 4) Seri No Doğrulama (ZORUNLU)
- Input: "Seri No son 4-5 hane"
- Kaynak cihaz:
  - Öncelik: service doc içindeki `deviceSerialNumber`
  - Gerekirse: `customers/{customerId}/devices/{deviceId}` dokümanından `serialNumber`
- Eşleşme kuralı: son hane karşılaştırması (case-insensitive)

Sonuç:
- Eşleştiyse:
  - service status `In Progress`
  - `serialVerifiedAt`, `verifiedDeviceId` (mümkünse) set et
  - Event: `SERIAL_VERIFIED`
- Eşleşme yoksa:
  - Hata: "Seri no eşleşmedi"

Not:
- Güvenlik için ideal: Cloud Function callable doğrulama.
- MVP: client-side doğrulama + rules ile sınırlı update.

### 5) İşlem Tamamlama
- Service için form:
  - Sonuç: `Repaired | Waiting Part | Delivery | Delivered`
  - "Yapılan işlemler" notu
  - Sayaç alanları (iş tipine göre opsiyonel)
- Kaydet:
  - `service_records/{id}` update:
    - `status`
    - `technicianReport` / `actionsTaken`
  - Event: `COMPLETE`

- Meter task için:
  - Sayaç değerleri al
  - `meter_readings` kaydı oluştur/güncelle
  - task status `completed`
  - Event: `COMPLETE`

## EVENT / AUDIT MODELİ (EKLENEBİLİR, MEVCUT YAPIYI BOZMADAN)
Aşağıdaki subcollection’lar eklenebilir:
- `service_records/{serviceId}/events/{eventId}`
- `technician_tasks/{taskId}/events/{eventId}`

Event alanları:
- `type: CLAIM | RELEASE | ARRIVED | SERIAL_VERIFIED | COMPLETE`
- `byUid`
- `timestamp`
- `note?`
- `gps?`

## GÜVENLİK (RULES) BEKLENTİSİ
Mevcut rules tenant seviyesinde geniş izin veriyor. Android için öneri:
- Tenant üyeliği zorunlu kalsın.
- Technician rolü için status transition ve alan bazlı update kısıtları ekle.
- Office rolü tenant içinde full read/write alabilsin.
- Kritik: teknisyen keyfi doküman alanları güncelleyemesin.

## TEKNİK İSTEKLER
- Gradle KTS, Compose, Hilt, Firebase BOM
- Katmanlar:
  - `data/` (firebase datasources, repository impl)
  - `domain/` (models, usecase)
  - `ui/` (screen, viewmodel)
- `UiState` sealed class: Loading/Success/Error
- Navigation Compose
- Snackbar/Toast hata mesajları
- Offline-first:
  - Firestore cache aktif
  - UI’da `Senkron bekliyor / Gonderildi` göstergesi
- Kod içinde açıklayıcı yorumlar + TODO

## ÇIKTI BEKLENTİSİ
1) Proje dosya ağacı
2) Önemli bağımlılıklar (`build.gradle.kts`)
3) Firebase init + login + tenant membership doğrulama kodu
4) Repository fonksiyonları

### Service odaklı
- `observeOpenPoolServices(tenantId)`
- `observeMyServices(tenantId, uid)`
- `claimService(tenantId, serviceId, uid, technicianName)`
- `releaseService(tenantId, serviceId, uid)`
- `markArrived(tenantId, serviceId, uid)`
- `verifySerial(tenantId, serviceId, uid, lastDigits)`
- `completeService(tenantId, serviceId, uid, completionData)`

### Meter task odaklı
- `observeOpenMeterTasks(tenantId)`
- `observeMyMeterTasks(tenantId, uid)`
- `claimMeterTask(...)`
- `releaseMeterTask(...)`
- `completeMeterTaskWithReading(...)`

### Event
- `addServiceEvent(...)`
- `addTaskEvent(...)`

5) Compose ekranları
- `LoginScreen`
- `WorkTabsScreen` (Açık Havuz / Üzerimdeki İşler)
- `SerialVerifyScreen`
- `CompleteServiceScreen`
- (Opsiyonel) `CompleteMeterTaskScreen`

6) Basit navigation graph
7) (Opsiyonel) rules taslağı (mevcut şemaya uyumlu)

## UYGULAMA METİNLERİ (TR)
Butonlar:
- "İşi Sahiplen"
- "İşi Bırak"
- "Müşteriye Geldim"
- "Doğrula"
- "Kaydet ve Tamamla"

Hatalar:
- "Seri no eşleşmedi"
- "Giriş başarısız"
- "Yetkiniz yok"
- "İnternet yok, senkron bekliyor"

## ÇALIŞMA ŞEKLİ
Kodu adım adım üret:
1. Proje yapısı + bağımlılıklar
2. Firebase/Auth/Tenant kontrol
3. Repository + usecase
4. ViewModel
5. Compose ekranları
6. Navigation
7. Rules taslağı

Her adım derlenebilir, çalışır örnek olmalı.
