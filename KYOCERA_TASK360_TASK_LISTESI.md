# Kyocera Yetkili Servis (Task360 / icibot) Entegrasyonu - Görev Listesi (Task Tracker)

**Doküman Tarihi:** 03.10.2026  
**Referans Plan:** `KYOCERA_TASK360_ENTEGRASYON_PLANI.md` (v2.0.0)  
**Tasarım Prensibi:** Sıfır Hata (Zero Defect), Sıfır Regresyon (Zero Regression), Tam İzolasyon (Sandbox), Sıfır Cloud Deploy (Lokal Doğrulama)

---

## 📌 Faz 1: Bağımsız Modül Lisanslama & Güvenlik Duvarı
- [x] **Task 1.1:** `src/lib/modulePermissions.ts` dosyasına `kyocera_task360` modül iznini ekle (`TENANT_PERMISSION_KEYS`, `PERMISSION_CATEGORIES`, varsayılanlar ve rota eşleşmeleri).
- [x] **Task 1.2:** `src/types/index.ts` ve `src/types/kyocera.ts` dosyalarında Kyocera veri tiplerini ve şube bağlantı sözleşmesini tanımla.
- [x] **Task 1.3:** `src/lib/navigationConfig.ts` menüsüne `kyocera_task360` iznine bağlı "Kyocera İş Havuzu" menü öğesini ekle (İzin kapalıysa menüde asla görünmez).
- [x] **Task 1.4:** `src/components/admin/AdminPanel.tsx` içerisinde kiracı detayında Kyocera modülünü açıp/kapatma (Feature Flag) yetkisini sağla.
- [x] **Task 1.5:** TypeScript tip kontrolü (`npx tsc --noEmit`) ile sıfır hata doğrula. (Başarıyla tamamlandı - Sıfır hata)

---

## 📌 Faz 2: Şube & Kimlik Eşleştirme Kasası (Settings > Kyocera)
- [x] **Task 2.1:** Task360 API istemcisi ve kimlik doğrulama servisini oluştur (`src/services/kyoceraService.ts` ve backend API yardımcıları).
- [x] **Task 2.2:** `/api/kyocera/test-connection` ve `/api/kyocera/settings` API rotalarını oluştur (Kimlik testi ve şube eşleştirme kayıtları).
- [x] **Task 2.3:** Ayarlar sekmesine (`/dashboard/settings?tab=kyocera`) çoklu şube eşleştirme arayüzünü entegre et (Şube kodu, kullanıcı adı, şifre, varsayılan depo ve "Bağlantıyı Test Et" butonu).
- [x] **Task 2.4:** TypeScript tip kontrolü (`npx tsc --noEmit`) ile sıfır hata doğrula. (Başarıyla tamamlandı - Sıfır hata)

---

## 📌 Faz 3: Kyocera İş Emirleri Havuzu (Read-Only & Dashboard)
- [x] **Task 3.1:** `/api/kyocera/jobs` endpoint'ini oluştur (icibot `new_login`, token cache, `v2requests` çekme, `asset` detaylarını birleştirme).
- [x] **Task 3.2:** `src/app/dashboard/kyocera-jobs/page.tsx` sayfasını geliştir:
  - Şube filtresi (Antalya, Isparta, Burdur veya Tüm Şubeler),
  - Durum filtreleri (Açık, İşlemde, Tamamlandı),
  - Arama (İş Emri No, Müşteri Adı, Seri No),
  - İkiz durum rozeti (`[ Kyocera: ... ]` / `[ ProServis: ... ]`).
- [x] **Task 3.3:** İş emri detay modalı/drawer'ı (Arıza bildirimi, cihaz modeli, müşteri adresi, Kyocera notları).
- [x] **Task 3.4:** TypeScript tip kontrolü (`npx tsc --noEmit`) ile sıfır hata doğrula. (Başarıyla tamamlandı - Sıfır hata)

---

## 📌 Faz 4: Tek Tıkla Servis Fişine Dönüştürme
- [x] **Task 4.1:** Dönüştürme API'si veya akışı (`/dashboard/service/create` entegrasyonu):
  - Seri numarasına göre ProServis'te mevcut cihazı ve müşteriyi bulma; yoksa otomatik eşleştirme/yaratma desteği.
  - İdempotency koruması: Aynı `SMWO-...` iş emrine mükerrer servis açılmasını engelleme (`externalReference` kilidi).
- [x] **Task 4.2:** Servis fişi açıldığında Task360'ta iş emri durumunu `In Progress / İşlemde` olarak güncelleme (`/api/kyocera/update-status`).
- [x] **Task 4.3:** TypeScript tip kontrolü (`npx tsc --noEmit`) ile sıfır hata doğrula. (Başarıyla tamamlandı - Sıfır hata)

---

## 📌 Faz 5: Çift Yönlü Kapatma & Form Gönderimi
- [x] **Task 5.1:** Servis tamamlandığında imzalı servis formunu (PDF) Task360 `/uploaddocument` uç noktasına iletme (`/api/kyocera/close-job`).
- [x] **Task 5.2:** Task360 durumunu `Completed / Tamamlandı` yapma ve kapanış notunu iletme (`EditServiceDialog.tsx` & `/api/kyocera/close-job`).
- [x] **Task 5.3:** TypeScript tip kontrolü (`npx tsc --noEmit`) ile sıfır hata doğrula. (Başarıyla tamamlandı - Sıfır hata)

---

## 📌 Faz 6: Test & Lokal Derleme Doğrulaması
- [x] **Task 6.1:** `npm run build` ile tüm sayfaların (82 sayfa ve API rotası) hatasız derlendiğini doğrula. (Başarıyla tamamlandı - Sıfır hata, 82/82 sayfa oluşturuldu)
- [x] **Task 6.2:** Sıfır deployment kontrolü ve kullanıcı için yerel test senaryolarının hazırlanması. (Tamamlandı)
