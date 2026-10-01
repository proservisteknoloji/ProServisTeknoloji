# ProServis Kademeli Lisans, Koltuk Kotası ve Güvenlik — Uygulama Görev Listesi (Task Checklist)

> **Kaynak Doküman:** `TENANT_PAKET_VE_KULLANICI_YETKI_MIMARISI_PLANI.md`  
> **Tarih:** 30 Eylül 2026  
> **Durum:** Planlama Tamamlandı / Uygulama Bekliyor  
> **Not:** Bu liste, geliştirme gününde adım adım ilerleyebilmek için fazlara bölünmüş ve onay kutuları (`[ ]`) ile yapılandırılmıştır.

---

## 📋 Faz 1: Tek Kaynak Lisans Motoru (Single Source of Truth)

- [ ] **1.1 `src/lib/tenantLicense.ts` dosyasını oluştur:**
  - [ ] `TenantPackageTier` tipini tanımla (`'temel' | 'gelismis' | 'platin' | 'custom'`).
  - [ ] `TenantLicense` arayüzünü tanımla (`packageTier`, `allowedModules`, `maxUsers`, `licenseUpdatedAt`, `licenseUpdatedBy`).
  - [ ] `TENANT_PACKAGES` sözlüğünü güncel **30 modül anahtarı** ile oluştur:
    - [ ] `temel`: 12 çekirdek modül + `defaultMaxUsers: 3`
    - [ ] `gelismis`: 25 modül (Gider fişi, CPC, faturalar dahil) + `defaultMaxUsers: 7`
    - [ ] `platin`: 30 modülün tümü + `defaultMaxUsers: 15`
    - [ ] `custom`: Esnek seçim + `defaultMaxUsers: null`
  - [ ] `resolveLicense(tenantDoc)` fonksiyonunu yaz:
    - [ ] Eğer dokümanda lisans bilgisi yoksa geriye dönük uyum için fallback: `{ packageTier: 'platin', allowedModules: [...ALL_KEYS], maxUsers: null }`.
  - [ ] `intersectPermissions(userPermissions, allowedModules)` fonksiyonunu yaz:
    - [ ] **Explicit False Güvencesi:** Pakette olmayan her modülü ve alt modülünü açıkça `false` yaz (parent-child merge tuzağını engelle).
  - [ ] `isBillableSeat(userDoc)` fonksiyonunu yaz:
    - [ ] `active !== false` ve rolü `['admin', 'office', 'viewer']` olanları `true` say.
    - [ ] Teknisyen koleksiyonunu kesinlikle hariç tut.
- [ ] **1.2 `src/types/index.ts` ve `src/lib/modulePermissions.ts` entegrasyonu:**
  - [ ] `Tenant` tipine `packageTier`, `allowedModules`, `maxUsers` alanlarını opsiyonel olarak ekle.
  - [ ] Yeni lisans tiplerini export et.

---

## 📋 Faz 2: Süper Admin Lisans ve Koltuk Kartı (`AdminPanel.tsx`)

- [ ] **2.1 `src/services/adminService.ts` güncellemesi:**
  - [ ] `saveTenantLicense(tenantId: string, license: TenantLicense)` metodunu ekle.
  - [ ] `getTenantLicense(tenantId: string)` metodunu ekle.
  - [ ] `getTenantBillableSeatCount(tenantId: string)` metodunu ekle.
- [ ] **2.2 `src/components/admin/AdminPanel.tsx` UI güncellemesi:**
  - [ ] Kiracı detay ekranına mevcut abonelik kartının yanına **"Lisans Paketi ve Koltuk Kotası"** kartını yerleştir.
  - [ ] Paket Seçim Dropdown'ı ekle: [Temel | Gelişmiş | Platin | Özel].
  - [ ] Paket değiştiğinde modül checkbox'larını ve varsayılan `maxUsers` değerini otomatik senkronize et.
  - [ ] Standart paketten bir kutu değiştirilirse paketi otomatik olarak `'custom'` yap.
  - [ ] Koltuk Limiti (`maxUsers`) sayısal input alanını yerleştir (`null` veya boş girilirse "Sınırsız / ∞" rozeti göster).
  - [ ] Anlık Koltuk Kullanım Rozeti ekle: `"Aktif Koltuk: 3 / 7"` (Kotalı) veya `"3 / ∞"` (Sınırsız).
  - [ ] Kaydet butonunu `AdminService.saveTenantLicense` ile bağla.

---

## 📋 Faz 3: Kullanıcı API'si ve Sunucu Tarafı Güvenliği

- [ ] **3.1 `src/app/api/admin/users/upsert/route.ts` sertleştirmesi:**
  - [ ] Çağıran yetkilendirmesi (Authentication & Authorization):
    - [ ] Firebase ID Token veya Platform Admin Session doğrulaması yap.
    - [ ] Kiracı sadece kendi `tenantId`'sine kullanıcı yazabilsin; başka kiracıya istek atamasın.
  - [ ] `tenantDoc` oku ve `resolveLicense()` ile lisans kuralını çöz.
  - [ ] **Koltuk Kotası Kontrolü (Seat Transaction):**
    - [ ] Yeni kullanıcı oluşturuluyorsa veya mevcut kullanıcı pasiften aktife çekiliyorsa:
      - [ ] Aktif faturalanan kullanıcıları say (`isBillableSeat`).
      - [ ] `maxUsers !== null && count >= maxUsers` ise HTTP 403 `SEAT_LIMIT_REACHED` ile işlemi reddet.
  - [ ] **Yetki Kırpma (Sanitization):**
    - [ ] Gelen `body.permissions` objesini `intersectPermissions(permissions, allowedModules)` ile filtrele.
    - [ ] Kiracının paketinde olmayan yetkileri sil / `false` yap.
- [ ] **3.2 `src/app/api/admin/users/delete/route.ts` sertleştirmesi:**
  - [ ] Çağıran kullanıcının o kiracıya yetkili olduğunu doğrula.
  - [ ] Silinen kullanıcının koltuğu boşalttığını doğrula.

---

## 📋 Faz 4: Firma Ayarlar Sayfası UX Revizyonu (`settings/page.tsx`)

- [ ] **4.1 Lisans ve Koltuk Göstergesi:**
  - [ ] Alt Kullanıcılar tablosunun üstüne şık bir **"Koltuk Lisansı: X / Y Aktif"** ilerleme çubuğu (progress bar) ve rozet ekle.
  - [ ] Eğer aktif koltuk sayısı `maxUsers`'a ulaştıysa:
    - [ ] "Yeni Kullanıcı Ekle" formunu nazikçe kilitle.
    - [ ] Bilgilendirme uyarısı göster: *"Kullanıcı lisans sınırınıza ulaştınız (X/X). Yeni kullanıcı eklemek için paketinizi yükseltin veya pasif personelleri düzenleyin."*
    - [ ] Mevcut kullanıcıları düzenleme, şube değiştirme, şifre güncelleme veya silme işlemlerini açık bırak (asla kilitleme).
- [ ] **4.2 Dinamik İzin Formu:**
  - [ ] Kullanıcı ekleme/düzenleme modülünde `PERMISSION_CATEGORIES` listesini kiracının `allowedModules` listesine göre filtrele.
  - [ ] Firmanın paketinde olmayan hiçbir modül kutusunu açılabilir olarak gösterme.
  - [ ] Lisans dışı modüller için formun altına *"Paketinizde yer almayan modüller gizlenmiştir"* bilgilendirmesi ekle.
  - [ ] `Tümünü Seç` butonunu sadece firmanın izinli modüllerini seçecek şekilde sınırla.
  - [ ] Preset butonları (Ofis, Muhasebe vb.) tıklandığında tavanı aşan izinleri temizle.

---

## 📋 Faz 5: Çalışma Zamanı Kesişimi ve Navigasyon Koruması

- [ ] **5.1 `src/hooks/useTenantUserAccess.ts` güncellemesi:**
  - [ ] Tenant kök dokümanından `packageTier`, `allowedModules` dinleyicisini bağla.
  - [ ] Kullanıcının efektif iznini hesapla: `intersectPermissions(userPermissions, allowedModules)`.
- [ ] **5.2 `src/lib/navigationConfig.ts` & `src/components/SidebarNavigation.tsx`:**
  - [ ] Sol menü ve üst barı efektif izinlere göre filtrele (satın alınmayan modüller gizlensin).
  - [ ] **`expense_entry` (Gider Fişi) Ayrımı:** Gider fişi sayfasını, `financial-reports` ana başlığından bağımsız bir menü öğesi olarak çalışabilecek şekilde bağla.
- [ ] **5.3 `src/app/dashboard/layout.tsx` Rota Koruması:**
  - [ ] Doğrudan URL yazılarak gidilen sayfalarda: `canAccessDashboardPath(pathname, effectivePermissions)`.
  - [ ] Tanımsız veya yetkisiz rotalar için varsayılan olarak ana sayfaya yönlendir ve uyarı fırlat.
  - [ ] Çift eksen kontrolü: `subscription` kısıtlıysa (ödeme bekleniyor vb.) lisans tam olsa dahi kısıtlı kalmasını sağla.

---

## 📋 Faz 6: Veri Katmanı ve Servislerin Sertleştirilmesi (Faz B)

- [ ] **6.1 Ajan ve Telemetri Koruması:**
  - [ ] `api/agent/*` uçlarında tenant lisansında `agents` modülünün olup olmadığını doğrula.
- [ ] **6.2 AI Asistanı Koruması:**
  - [ ] AI asistanı API çağrılarında tenant'ta `ai` iznini doğrula.
- [ ] **6.3 Cloud Functions (Otomatik Sayaç & Mail):**
  - [ ] `mail-counters` işleyicisinde kiracının paketinde bu özellik yoksa sayaç kuyruğunu çalıştırma, log düş.

---

## 📋 Faz 7: Test, Doğrulama ve Devreye Alma (Rollout)

- [ ] **Test 1:** Eski tenant (alanları boş): Tam yetki ve sınırsız koltukla kesintisiz çalıştığını doğrula.
- [ ] **Test 2:** Temel paketli tenant oluştur:
  - [ ] `stock` açıkken `stock_transfers`'ın otomatik AÇILMADIĞINI (explicit false) doğrula.
  - [ ] AI, Kârlılık, Ajanlar menülerinin gizlendiğini doğrula.
- [ ] **Test 3:** 3 koltuklu Temel pakette 3 kullanıcı varken 4. kullanıcı ekleme girişiminin API ve UI tarafından engellendiğini doğrula.
- [ ] **Test 4:** Kullanıcı pasife alındığında koltuğun anında boşa çıktığını ve yeni kullanıcı eklenebildiğini doğrula.
- [ ] **Test 5:** Mobil teknisyen koleksiyonuna (`tenants/.../technicians`) kayıt eklendiğinde web koltuk sayısının ARTMAYIP sabit kaldığını doğrula.
- [ ] **Test 6:** Platin'den Temel'e paket düşürüldüğünde mevcut verilerin (fatura, ajan) silinmediğini, sadece menünün kısıtlandığını doğrula.
- [ ] **Backfill Script:** Mevcut tüm canlı tenant'lara `packageTier: 'platin'`, `maxUsers: null` yazan tek seferlik migrasyon script'ini çalıştır.
- [ ] **Global Yayılım:** `ENTITLEMENTS_ENFORCE` flag'ini `true` yaparak sistemi tüm kullanıcılar için canlıya al.
