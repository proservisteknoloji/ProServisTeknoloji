# Kyocera Yetkili Servis (Task360 / icibot) Entegrasyon Mimarisi ve Uygulama Planı
**Sürüm:** v2.0.0 (Kapsamlı Mimari & Çok Şubeli Bağımsız Modül Spesifikasyonu)  
**Tarih:** 03.10.2026  
**Durum:** Onay Bekliyor (Son Kontrol Aşaması)  
**Tasarım Prensibi:** Sıfır Hata (Zero Defect), Sıfır Regresyon (Zero Regression), Tam İzolasyon (Sandbox)

---

## 1. Yönetici Özeti & Stratejik Değer (Executive Summary)

Kyocera Mita Türkiye, yetkili servislerine (örneğin Kopier Bilişim vb.) arıza ve sarf malzeme işlerini **Task360 (`https://manage.task360.app`)** platformu üzerinden atamaktadır.

Bu proje ile ProServis Web paneline **tamamen bağımsız, lisansla açılıp kapatılabilen, çok şubeli bir Kyocera Entegrasyon Modülü** kazandırılacaktır:
- **Çift Veri Girişi Biter:** Kyocera'dan düşen çağrılar tek tıkla ProServis'te servis fişine dönüşür.
- **Kyocera Tarafı %100 Olağan Görür:** Kyocera Genel Merkezi kendi ekranında yetkili servisin Task360 web sitesine girip elle form yüklemiş ve kapatmış gibi eksiksiz ve nizami bir akış görür.
- **Platform Kontrolü Sizde:** Modül ProServis'in diğer müşterilerine tamamen kapalıdır; siz (Süper Admin) istediğiniz firmaya tek tıkla açıp kapatabilirsiniz.
- **Çok Şubeli Yapı:** Antalya, Isparta, Burdur gibi farklı şehirlerdeki şube kodları otomatik eşleştirilir.

---

## 2. Canlı Tersine Mühendislik ve Kesinleşen API Protokolü

Sistem canlı ortamda test edilmiş ve tüm protokoller %100 doğrulanmıştır:

| İşlem | Metot & Uç Nokta (icibot REST Engine) | Açıklama / Parametreler |
| :--- | :--- | :--- |
| **Giriş / Token** | `POST https://api.icibot.net/exapi/task360/user/new_login` | `{ email, password }` alır. 1 yıl geçerli JWT döner. SMS/Captcha yoktur. |
| **İş Emri Havuzu** | `GET https://api.icibot.net/v2/api/v2requests` | `start_date`, `end_date`, `is_reduced=true`, `with_asset_dimension=true` |
| **Cihaz & Adres** | `GET https://api.icibot.net/v2/api/asset/{asset_id}` | `serial_no`, `title`, `address` bilgilerini döner. |
| **İş Detayı** | `GET https://api.icibot.net/v2/api/request/{id}` | Talep detayları ve notları döner. |
| **Durum Güncelleme** | `PUT https://api.icibot.net/v2/api/request_set_status/{id}` | `{ user_name, status, staff_note, place_code }` alır. |
| **Servis Formu Yükleme**| `POST https://api.icibot.net/v2/api/uploaddocument` | AWS S3 `b1development` bucket'ına imzalı PDF formunu yükler. |

> **Canlıda Doğrulanan Gerçek Test Verisi:**
> - İş Emri No: `SMWO-2934124` / `SMOR-2997438`
> - Müşteri: `THY DO CO İKRAM HİZMETLERİ A.Ş.`
> - Cihaz / Model: `KYOCERA MA3500cix` (Seri No: `H7R3802772`)
> - Atanan Şube Kodu: `12460` (`KOPİER BİLİŞİM - ANTALYA`)
> - İş Türü: `SARF MALZEME TESLİMAT`

---

## 3. Bağımsız Modül ve Lisanslama Mimarisi (Feature Flag)

ProServis'in mevcut `TenantModulePermissions` (`src/lib/modulePermissions.ts`) sistemine entegre bağımsız lisans anahtarı:
🔑 **`kyocera_task360`**

### Güvenlik & İzolasyon Kuralları:
1. **Modül Kapalıysa:**
   - Menüde `Kyocera İş Havuzu` görünmez.
   - Ayarlarda `Kyocera Bağlantısı` görünmez.
   - Backend API istekleri `403 Modül Yetkiniz Bulunmamaktadır` ile anında kesilir.
   - Diğer kullanıcılar ve firmalar bu modülün varlığından dahi haberdar olmaz.
2. **Modül Açıkken (Lisanslı Firma):**
   - Menüde `Kyocera İş Emirleri` aktifleşir.
   - Ayarlar panelinde `Kyocera Şube Bağlantıları` açılır.

---

## 4. Çok Şubeli Yapı ve Şube Kodları (Multi-Branch Routing)

Her şubenin Task360'ta ayrı bir kodu (`assigned_person_id`) veya ayrı bir login bilgisi bulunur:

### Şube Eşleştirme Tablosu (Settings > Kyocera):
| ProServis Şubesi | Task360 Şube Kodu / Giriş | Varsayılan Depo | Durum |
| :--- | :--- | :--- | :--- |
| **Antalya Merkez** | `12460` (`antalya@kopier.com`) | Antalya Merkez Depo | 🟢 Bağlı |
| **Isparta Şube** | `12461` (`isparta@kopier.com`) | Isparta Şube Deposu | 🟢 Bağlı |
| **Burdur Şube** | `12462` (`burdur@kopier.com`) | Burdur Şube Deposu | 🟢 Bağlı |

### Operasyonel Davranış:
- **Isparta Teknisyeni / Sorumlusu:** Sadece Isparta'ya atanan işleri görür.
- **Genel Müdür / Merkez Yöneticisi:** `[ Tüm Şubeler ]` açılır menüsüyle Antalya, Isparta ve Burdur işlerini tek ekranda konsolide görür.
- **Servise Dönüştürürken:** Şubenin deposu ve teknisyen listesi otomatik filtrelenir.

---

## 5. İki Sistemin Birbiriyle Yaşam Döngüsü (State Machine)

### A. Kyocera Genel Merkezi Kendi Sisteminde Ne Görür?
1. **İlk Atama:** Task360'ta durum `Readed / Okundu` veya `Assigned`.
2. **ProServis'te Servis Açılınca:** Task360'ta durum anında `In Progress / İşlemde` olur.
3. **Parça Talep Edilince:** Task360 altına standart `request_line` yedek parça satırı açılır.
4. **Teknisyen İşi Kapatınca:** 
   - ProServis mobil uygulamada müşteriden alınan imzalı servis formu PDF olarak Task360'a yüklenir (`/uploaddocument`).
   - Task360 durumu `Completed / Tamamlandı` yapılır.
   - **Sonuç:** Kyocera yetkilisi için sıradan bir web kullanıcısının elle yaptığı işlemden hiçbir farkı yoktur.

### B. ProServis Ekranında Biz Ne Görürüz?
- İkiz Durum Rozeti (Twin Status):
  - `[ Kyocera: In Progress ]` & `[ ProServis: Servis Açıldı #SRV-1049 ]`
- Mükerrer Açma Koruması (İdempotency):
  - `SMWO-2934124` iş emri numarası kilit anahtarıdır; aynı işe 2 kez servis açılamaz.

---

## 6. Sıfır Hata & Sıfır Regresyon Zırhı

1. **Firestore Şeması Korunur:** `services`, `customers`, `devices` ana koleksiyonları değişmez. Kyocera verisi `externalReference: { provider: 'kyocera_task360', workOrderNo: '...', serviceCallId: '...' }` alanında tutulur.
2. **Devre Kesici (Circuit Breaker):** Task360 yavaşlasa veya erişilemese bile ProServis'in diğer tüm işlevleri kesintisiz çalışır.
3. **Şifre Güvenliği (Vault):** Kullanıcı şifreleri sunucu tarafında güvenle tutulur, istemciye asla sızmaz.

---

## 7. Aşama Aşama Uygulama Yol Haritası (Implementation Phases)

- [ ] **Faz 1: Bağımsız Modül Lisanslama & Güvenlik Duvarı**
  - `src/lib/modulePermissions.ts` -> `kyocera_task360` anahtarının eklenmesi.
  - Admin panelinde firma bazlı açıp kapatma yetkisi.
- [ ] **Faz 2: Şube & Kimlik Eşleştirme Kasası**
  - `src/app/dashboard/settings/kyocera/page.tsx`
  - Çoklu şube eşleştirme ve canlı test butonu.
- [ ] **Faz 3: Kyocera İş Emirleri Havuzu (Read-Only)**
  - `src/app/dashboard/kyocera-jobs/page.tsx`
  - Şube filtresi, durum filtreleri, zenginleştirilmiş cihaz ve adres bilgileri.
- [ ] **Faz 4: Tek Tıkla Servis Fişine Dönüştürme**
  - Müşteri/Cihaz otomatik eşleştirme ve teknisyene yönlendirme.
- [ ] **Faz 5: Çift Yönlü Kapatma & Form Gönderimi**
  - Sahadaki formun Task360'a otomatik aktarımı ve işi kapatma.
