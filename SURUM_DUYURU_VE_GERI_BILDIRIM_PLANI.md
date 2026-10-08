# 📢 ProServis Live - Sürüm Duyuru & Geri Bildirim Sistemi Mimari Tasarım Planı

**Tarih:** 09 Ekim 2026  
**Mimari Yaklaşım:** Tamamen Yalıtılmış (Zero-Side-Effect), Tak-Çıkar (Plug-and-Play) Modüler Mimari  
**Hedef:** Spagetti koddan arındırılmış, mevcut hiçbir sisteme/fonksiyona dokunmayan, temiz, bağımsız ve kolay okunabilir mikro-modül tasarımı.

---

## 🏛️ 1. Temel Mimari Felsefe: "Tak-Çıkar (Plug-and-Play)" Prensibi

Bu özellik mevcut ProServis kod tabanına **bir yama (patch) olarak değil, sisteme dışarıdan takılıp çıkarılabilen bağımsız bir eklenti (isolated plugin)** gibi tasarlanmıştır:

1. **Sıfır Yan Etki (Zero Side-Effects):**
   - Mevcut hiçbir servise (`serviceService`, `billingService`, `adminService` vb.) tek bir satır dahi dokunulmaz.
   - Mevcut hiçbir state, context veya hesaplama fonksiyonu modifiye edilmez.
2. **Kendi Kendine Yeten (Self-Contained) Durum Yönetimi:**
   - Bildirim kontrolü, LocalStorage önbelleklemesi, okunma durumu ve reaksiyon gönderimi tek bir özel React Hook'u (`useAnnouncements`) içinde izole edilir.
   - Dashboard sayfasına sadece `<DashboardWhatsNewButton />` olarak tek satır bırakılır; dışarıdan prop almaz, dışarıya yük bindirmez.
3. **İzole Firestore Koleksiyonları:**
   - Mevcut tenant koleksiyonlarının içine dokunulmaz.
   - Sadece iki adet bağımsız global koleksiyon kullanılır: `system_announcements` ve `announcement_reads`.
4. **Zorunlu Olmayan, Rahatsız Etmeyen UX:**
   - Üst navigasyon barı (`TopBarNavigation`) ve operasyonel çan (🔔) ikonuna kesinlikle dokunulmaz.
   - Otomatik açılan bloklayıcı pop-up YOKTUR.
   - Sadece `/dashboard` ekranında başlığın yanında, okunmadıysa nazikçe yanıp sönen (pulse), okunduysa sakin duran megafon butonu yer alır.
5. **Süper Admin Toolbar İzolasyonu:**
   - Süper Admin Panelindeki (`AdminPanel.tsx`) mükerrer "Sayaç E-postaları" butonunun yerine bağımsız `<AdminAnnouncementsDialog />` bileşeni yerleştirilir.

---

## 🧩 2. Modüler Katman Mimarisi

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KULLANICI DASHBOARD ARAYÜZÜ                            │
│                                                                           │
│   src/app/dashboard/page.tsx                                              │
│        └── <DashboardWhatsNewButton />  <── (Sıfır Prop, Tamamen Bağımsız)│
│                 │                                                         │
│                 ├── hooks/useAnnouncements.ts  (Tüm Mantık Burada İzole) │
│                 └── components/announcements/WhatsNewModal.tsx (Görünüm) │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                    SÜPER ADMİN YÖNETİM ARAYÜZÜ                            │
│                                                                           │
│   src/components/admin/AdminAnnouncementsDialog.tsx (Bağımsız Dialog)     │
│        ├── Sürüm Yayınlama / Düzenleme Formu                              │
│        └── Canlı Müşteri Geri Bildirim Tablosu & Analitiği                │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                    SERVİS VE VERİ KATMANI (İZOLE)                         │
│                                                                           │
│   src/services/announcementService.ts                                     │
│        ├── Firestore: system_announcements  (Duyuru Şablonları)           │
│        └── Firestore: announcement_reads    (Okundu & Müşteri Görüşleri)  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 3. Bağımsız Tip Tanımları (`src/types/announcements.ts`)

Herhangi bir tipe bağımlı olmadan kendi dosyasında yaşayan temiz veri tipleri:

```typescript
export type AnnouncementIconType = 
  | 'mouse' 
  | 'columns' 
  | 'box' 
  | 'file' 
  | 'sparkles' 
  | 'wrench' 
  | 'check';

export type FeedbackRatingType = 'love' | 'good' | 'neutral' | 'bad';

export interface AnnouncementItem {
  id: string;
  icon: AnnouncementIconType;
  title: string;
  description: string;
  imageUrl?: string;
  pageUrl?: string;
  pageLabel?: string;
}

export interface SystemAnnouncement {
  id: string;
  version: string;
  title: string;
  subtitle?: string;
  isActive: boolean;
  publishedAt: any;
  createdAt: any;
  items: AnnouncementItem[];
}

export interface AnnouncementReadReceipt {
  id: string;                  // `${userId}_${announcementId}`
  announcementId: string;
  version: string;
  userId: string;
  userName: string;
  tenantId: string;
  companyName?: string;
  readAt: any;
  feedbackRating?: FeedbackRatingType | null;
  feedbackComment?: string;
}
```

---

## ⚙️ 4. Bağımsız Servis Katmanı (`src/services/announcementService.ts`)

Mevcut hiçbir servisi import etmeyen, sadece Firestore ile konuşan yalın servis:

* `getActiveAnnouncement(): Promise<SystemAnnouncement | null>`: Aktif olan son sürüm duyurusunu çeker.
* `getAllAnnouncements(): Promise<SystemAnnouncement[]>`: Admin için tüm duyuruları listeler.
* `saveAnnouncement(data: Partial<SystemAnnouncement>): Promise<string>`: Yeni sürüm ekler/günceller.
* `toggleAnnouncementActive(id: string, isActive: boolean): Promise<void>`: Sürümü tek tıkla yayına alır / yayından kaldırır.
* `recordReadAndFeedback(receipt: Omit<AnnouncementReadReceipt, 'id' | 'readAt'>): Promise<void>`: Okundu ve geri bildirim bilgisini idempotent (tekil) olarak kaydeder.
* `getFeedbackAnalytics(announcementId?: string): Promise<FeedbackAnalyticsSummary>`: Admin için okunma sayısı, memnuniyet yüzdesi ve kullanıcı yorumlarını raporlar.

---

## 🪝 5. Kendi Kendine Yeten Custom Hook (`src/hooks/useAnnouncements.ts`)

Bileşenlerin içinde kod kalabalığı oluşmaması için tüm durum ve mantık tek bir yerde toplanır:

```typescript
export function useAnnouncements() {
  // 1. State: Aktif duyuru, okunmadı mı?, modal açık mı?, yükleniyor mu?
  // 2. Cache-First Kontrolü:
  //    - LocalStorage kontrol edilir: `read_version_${userId} === active.version` ise hasUnread = false
  // 3. Metodlar:
  //    - openModal(): Modalı açar
  //    - closeModal(): Modalı kapatır
  //    - markAsRead(): Okundu işaretler, LocalStorage'ı günceller, pulse'ı anında durdurur
  //    - sendFeedback(rating, comment): Reaksiyonu kaydeder
  return {
    announcement,
    hasUnread,
    isModalOpen,
    openModal,
    closeModal,
    markAsRead,
    sendFeedback,
  };
}
```

---

## 🎨 6. Arayüz Bileşenleri (Sıfır Bağımlılık)

### A. Dashboard Butonu: `src/components/dashboard/DashboardWhatsNewButton.tsx`
* Sadece `/dashboard` ana ekranında başlık yanında kullanılır.
* Kendi hook'unu çağırır (`useAnnouncements`).
* **Okunmamışsa:** `animate-pulse` ve ışıltılı badge ile `📢 Yenilikler Var (v1.2.0) 🔥` şeklinde dikkat çeker.
* **Okunduysa:** Yanıp sönmesi durur; sakin, zarif `📢 Sürüm Notları` butonuna döner.
* **Aktif duyuru yoksa:** Ekranda hiçbir şey render etmez (`return null;`).
* Dashboard'un mevcut JSX'ine tek satır eklenir:
  ```tsx
  {/* Dashboard Header İçinde: */}
  <DashboardWhatsNewButton />
  ```

### B. Yenilikler Penceresi: `src/components/announcements/WhatsNewModal.tsx`
* Tamamen ayrık bir Dialog/Modal bileşeni.
* Yenilik maddelerini ikon ve yönlendirme butonlarıyla listeler.
* Alt kısmında 4 emojili reaksiyon barı:  
  `😍 Harika` | `👍 Faydalı` | `😐 Geliştirilmeli` | `👎 Beğenmedim`
* Kullanıcı bir emojiye bastığında mikro-teşekkür animasyonu gösterilir.
* Kapatıldığında megafonun yanıp sönmesi anında kesilir.

### C. Süper Admin Modalı: `src/components/admin/AdminAnnouncementsDialog.tsx`
* [AdminPanel.tsx](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/components/admin/AdminPanel.tsx) üst buton çubuğundaki mükerrer "Sayaç E-postaları" butonu yerine tek satırla monte edilir:
  ```tsx
  <AdminAnnouncementsDialog />
  ```
* İçerisinde 2 sekme barındırır:
  1. **📢 Sürüm Yönetimi:** Başlık, maddeler, ikonlar, test linkleri ekleme, tek tıkla yayına alma.
  2. **💬 Müşteri Geri Bildirimleri:** Toplam okunma, % memnuniyet skoru, firma ve personelin bıraktığı yorumların canlı tablosu.

---

## 🛡️ 7. Temiz Kod (Clean Code) Garantileri

| Prensip | Nasıl Sağlanıyor? |
| :--- | :--- |
| **Spagetti Kod Yok** | Tüm fonksiyonlar 20-30 satırı geçmeyen, tek amaçlı küçük fonksiyonlara ayrılır. |
| **Mevcut Koda Dokunulmazlık** | Hiçbir servis veya state fonksiyonu değiştirilmez. Sadece 2 JSX noktasına tek satırlık bileşen çağrısı yapılır. |
| **Kolay Silinebilirlik (Delete-Friendly)** | İleride bu özellik tamamen kaldırılmak istenirse, oluşturulan 4-5 dosya silindiğinde sistem hiçbir hata vermeden eski haline döner. |
| **Test Edilebilirlik** | `announcementService.ts` tamamen saf parametrelerle çalışır; UI'dan bağımsız test edilebilir. |

---

## 🚀 8. Uygulama Adımları (Tamamlandı ✅)

1. [x] **Adım 1 - Tipler:** [`src/types/announcements.ts`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/types/announcements.ts) oluşturuldu.
2. [x] **Adım 2 - Servis:** [`src/services/announcementService.ts`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/services/announcementService.ts) saf veri servisi ve v1.2.0 şablonu kodlandı.
3. [x] **Adım 3 - Hook:** [`src/hooks/useAnnouncements.ts`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/hooks/useAnnouncements.ts) LocalStorage cache-first ve asenkron feedback hook'u hazırlandı.
4. [x] **Adım 4 - Kullanıcı Modalı:** [`src/components/announcements/WhatsNewModal.tsx`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/components/announcements/WhatsNewModal.tsx) 4 emojili mikro-feedback ve doğrudan test yönlendirmeleri ile kodlandı.
5. [x] **Adım 5 - Dashboard Butonu:** [`src/components/dashboard/DashboardWhatsNewButton.tsx`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/components/dashboard/DashboardWhatsNewButton.tsx) yanıp sönen/sakin buton kodlandı ve [`src/app/dashboard/page.tsx`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/app/dashboard/page.tsx) içine tek satırla monte edildi.
6. [x] **Adım 6 - Admin Modalı:** [`src/components/admin/AdminAnnouncementsDialog.tsx`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/components/admin/AdminAnnouncementsDialog.tsx) kodlandı; [`src/components/admin/AdminPanel.tsx`](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/components/admin/AdminPanel.tsx) üst toolbar'ındaki mükerrer "Sayaç E-postaları" butonu kaldırılarak yerine entegre edildi.
7. [x] **Adım 7 - Derleme & Tip Kontrolü:** `tsc --noEmit` ve `npm run build` tam derlemesi başarıyla (0 hata, 85 statik sayfa) doğrulandı.