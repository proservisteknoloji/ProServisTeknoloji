# Android Technician App Prompt (TR)

Sen kıdemli bir Android (Kotlin) + Firebase (Firestore/Auth/Storage/FCM) geliştiricisisin. VS Code içinde üreteceğin kodlar production’a yakın, okunabilir, modüler ve test edilebilir olacak. Jetpack Compose + MVVM + Repository pattern kullan. Hilt (DI), Kotlin Coroutines + Flow kullan. Firestore offline persistence aktif olacak. UI sade, teknisyen odaklı, büyük butonlu ve minimum tıklama ile ilerleyecek.

AMAÇ
Ofis personelinin web panelinden Firebase’e düştüğü işleri, teknisyen Android uygulamasında görsün ve sahada adım adım tamamlasın. Tüm yapılan işlemler ofis tarafından izlenebilsin (audit log).

ÇOK ÖNEMLİ KISITLAR
- Multi-tenant yapı var: her firma ayrı tenantId.
- Teknisyen giriş yapmak için firmanın verdiği “kullanıcı adı + şifre”yi kullanmak zorunda.
- Kullanıcı başka firmanın verisini asla görememeli (tenant izolasyonu).
- Teknisyen sadece “Bekleyen” işleri ve “kendi üzerine aldığı” işleri görebilmeli.
- Göreve gidildiğinde yanlış cihaza servis verilmesini engellemek için seri numarasının son 4–5 hanesi ile doğrulama zorunlu.

UYGULAMA AKIŞI (MVP)
1) Login
   - Ekran 1: “Firma Kodu (tenantId)” + “Kullanıcı adı” + “Şifre”
   - Firebase Authentication ile giriş yap (email/password tercih; kullanıcı adı email değilse mapping yaklaşımı öner ama MVP’de email/password kabul edilebilir).
   - Login sonrası tenantId uygulama oturumunda saklansın (DataStore).

2) Ana Ekran: 2 sekmeli sayfa (Tabs)
   - Sekme A: “Bekleyen İşler”
     - Liste: status=BEKLEYEN olan işler
     - Her kartta: müşteri, lokasyon kısa, iş tipi (SERVIS/ARIZA/SAYAC), tarih/öncelik (varsa)
     - Buton: “İşi Sahiplen”
       - Basınca: task.assignedToUid = currentUid, task.status = UZERIMDE
       - Ayrıca task’in altına audit event ekle: type=CLAIM

   - Sekme B: “Üzerimdeki İşler”
     - Liste: assignedToUid == currentUid ve status in (UZERIMDE, MUSTERIYE_GELDIM, ISLEMDE)
     - Duruma göre butonlar:
       - UZERIMDE: “Müşteriye Geldim” + “İşi Bırak”
       - MUSTERIYE_GELDIM: “Seri No Doğrula ve İşleme Başla” (İşi Bırak kapalı)
       - ISLEMDE: “İşi Tamamla”
     - “İşi Bırak” (sadece UZERIMDE durumunda):
       - task.assignedToUid = null, task.status = BEKLEYEN
       - event: RELEASE

3) Müşteriye Geldim
   - Üzerimdeki işte “Müşteriye Geldim” basınca:
     - task.status = MUSTERIYE_GELDIM
     - event: ARRIVED (timestamp, opsiyonel gps)

4) Seri No Doğrulama (zorunlu)
   - MUSTERIYE_GELDIM sonrası açılan ekranda:
     - Input: “Seri No (son 4–5 hane)”
     - Buton: “Doğrula”
   - Doğrulama mantığı:
     - task.deviceIds[] içindeki cihazlar içinde eşleşen device.serialLastDigits bulunmalı
     - Tek eşleşme → task.verifiedDeviceId set et, task.status = ISLEMDE, event: SERIAL_VERIFIED
     - Eşleşme yok → hata: “Seri no eşleşmedi”
     - Birden fazla eşleşme (nadir) → kullanıcıya cihaz seçtir ve ardından doğrula
   - Bu doğrulama işlemi güvenli olsun: mümkünse Cloud Function callable ile doğrula (MVP’de client-side + rules ile de yapılabilir ama güvenlik notu ekle).

5) İşlem Tamamlama
   - ISLEMDE ekranı:
     - Arıza/Servis için sonuç seçimi: ONARILDI / PARCA_BEKLIYOR / ONARILMADI (büyük butonlar)
     - Metin alanı: “Yapılan işlemler”
     - Sayaç girişi: numeric (iş tipine göre zorunlu/opsiyonel)
     - Buton: “Kaydet ve Tamamla”
   - Kaydet:
     - tasks/{taskId}/reports altına rapor dokümanı ekle (report)
     - task.status = TAMAMLANDI
     - event: COMPLETE

FIREBASE VERİ MODELİ (Firestore)
Tüm koleksiyonlar tenant altında:
tenants/{tenantId}/
  users/{uid} (role: office/technician vb.)
  devices/{deviceId} (serialLastDigits, serialFull? maskeli, locationId, customerId, lastCounter, vb.)
  tasks/{taskId}:
    - type: SERVIS|ARIZA|SAYAC
    - status: BEKLEYEN|UZERIMDE|MUSTERIYE_GELDIM|ISLEMDE|TAMAMLANDI
    - assignedToUid: nullable
    - customerName / customerId
    - locationText / locationId
    - deviceIds: array
    - verifiedDeviceId: nullable
    - createdAt, updatedAt
  tasks/{taskId}/events/{eventId}:
    - type: CLAIM|RELEASE|ARRIVED|SERIAL_VERIFIED|COMPLETE
    - byUid
    - timestamp
    - note? gps?
  tasks/{taskId}/reports/{reportId}:
    - verifiedDeviceId
    - resultStatus
    - workNotes
    - counterValue
    - createdAt

GÜVENLİK (Rules) BEKLENTİSİ
- Kullanıcı sadece kendi tenantId altını okuyup yazabilsin.
- Technician:
  - Bekleyen işleri okuyabilir (status=BEKLEYEN)
  - Kendi işleri okuyabilir (assignedToUid == request.auth.uid)
  - Claim/release/arrived/verify/complete için sadece izinli alanları ve izinli status geçişlerini yapabilsin.
- Office rolü tenant içindeki her şeyi görebilsin.
Not: Rules’u tam yazmak karmaşıkysa, en azından taslak + kritik kontrolleri çıkar.

TEKNİK İSTEKLER
- Proje kurulumu: Gradle (KTS), Compose, Hilt, Firebase BOM
- Katmanlar:
  - data/ (firebase datasources, repositories)
  - domain/ (usecases, models)
  - ui/ (compose screens, viewmodels)
- State yönetimi: UiState sealed class (Loading/Success/Error)
- Navigation: Jetpack Navigation Compose
- Error handling: kullanıcı dostu toast/snackbar
- Offline: Firestore persistence + UI’da “Senkron bekliyor / Gönderildi” göstergesi (en azından skeleton)
- Kod içinde açıklayıcı yorumlar ve TODO’lar.

ÇIKTI BEKLENTİSİ
1) Proje dosya ağacı önerisi
2) Önemli bağımlılıklar (build.gradle.kts)
3) Firebase init + Auth login kodu
4) Firestore repository fonksiyonları:
   - observeWaitingTasks(tenantId)
   - observeMyTasks(tenantId, uid)
   - claimTask(tenantId, taskId, uid)
   - releaseTask(tenantId, taskId, uid)
   - markArrived(tenantId, taskId, uid)
   - verifySerial(tenantId, taskId, uid, lastDigits)
   - completeTask(tenantId, taskId, uid, reportData)
   - addEvent(...)
5) Compose ekranları:
   - LoginScreen
   - TasksScreen (2 tab)
   - TaskDetail/Actions (isteğe bağlı)
   - SerialVerifyScreen
   - CompleteTaskScreen
6) Basit Navigation graph
7) (Opsiyonel) Firestore Security Rules taslağı

UYGULAMA METİNLERİ (TR)
Butonlar: “İşi Sahiplen”, “İşi Bırak”, “Müşteriye Geldim”, “Doğrula”, “Kaydet ve Tamamla”
Hatalar: “Seri no eşleşmedi”, “Giriş başarısız”, “Yetkiniz yok”, “İnternet yok, senkron bekliyor”

Şimdi bu gereksinimlere göre kodu üret. Önce proje yapısını ve bağımlılıkları ver, sonra adım adım repository + viewmodel + compose ekranları + navigation gelecek şekilde ilerle. Her adımda çalışır, derlenebilir örnekler yaz.
