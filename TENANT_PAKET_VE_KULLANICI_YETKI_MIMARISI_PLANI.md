# ProServis Çok Kiracılı Paketleme, Koltuk Kotası ve Yetki Güvenlik Mimarisi
## Nihai ve Onaylanmış Mimari Şartname (Authoritative RFC)

> **Doküman Türü:** Üretim Seviyesi Mimari Şartname & Tasarım Belgesi (Production Architecture RFC)  
> **Tarih:** 30 Eylül 2026  
> **Durum:** Konsensüs Sağlandı / Uygulamaya Hazır (Planlama Tamamlandı)  
> **Kapsam Kod Kökü:** `proservis-web/`  
> **Amaç:** Çok kiracılı (multi-tenant) sistemde paket bazlı lisanslama (Temel, Gelişmiş, Platin, Özel), koltuk kotası (seat limits), yetki aşımını engelleme ve Ayarlar sayfası kullanıcı yönetimini sıfır kesinti ve sıfır hata ile hayata geçirmek.

---

## 0. Temel Mimari Formül ve Değişmez İlkeler

Sistem genelinde geçerli olacak temel güvenlik ve lisans formülü:

$$\text{Efektif Modül İzni} = \text{kullanıcı.permissions} \cap \text{tenant.allowedModules} \cap (\text{abonelik aktif mi?})$$

$$\text{Faturalanan Koltuk (Billable Seats)} = \text{COUNT}(\text{tenants/\{id\}/users WHERE active != false AND rol } \in [\text{'admin', 'office', 'viewer'}]) \quad (\text{teknisyenler hariç})$$

---

## 1. Faz 0 — Kilitlenmiş Karar Protokolü

Uygulama öncesinde tüm teknik ve ürün kararları aşağıdaki şekilde kesinleştirilmiştir:

| # | Karar Maddesi | Kilitlenen Nihai Karar |
| :-: | :--- | :--- |
| **1** | **Platin Koltuk Kotası** | Standart Platin pakette varsayılan `maxUsers: 15`. Kurumsal / özel anlaşmalı kiracılarda `maxUsers: null` (Sınırsız). Asla `999` sentineli kullanılmayacaktır. |
| **2** | **Eski/Mevcut Kiracılar (Grandfathering)** | Mevcut tüm kayıtlı firmalar `packageTier: 'platin'`, `allowedModules: [...30 anahtar]`, `maxUsers: null` olarak backfill edilir. Mevcut müşterilerin hiçbir ekranı kapanmaz, sıfır kesinti garanti edilir. |
| **3** | **Menü UX Davranışı** | **Doğrudan Gizleme (Clean UX).** Firmanın paketinde olmayan sayfalar sol navigasyonda gösterilmez. Ayarlar sayfasındaki yetki formunda yöneticiye *"Bu modül lisans paketinizde yer almamaktadır"* kilit satırı gösterilir. |
| **4** | **`expense_entry` (Gider Fişi)** | Gelişmiş Pakette yer alacaktır. Üst başlığı olan `financial-reports` (şirket kârlılığı/mali rapor) kapalı tutularak, gider fişi bağımsız rota olarak çalıştırılacaktır. |
| **5** | **Feature Flag & Canary** | `ENTITLEMENTS_ENFORCE` (Varsayılan: `false`). Önce canary tenant'ta test edilecek, backfill script çalıştırıldıktan sonra global olarak aktif edilecektir. |

---

## 2. Paket Matrisi (30 Modül - Single Source of Truth)

Sistemdeki güncel 30 anahtarın (`TENANT_PERMISSION_KEYS`) paket dağılımı:

| Modül / İzin Anahtarı | 🥉 Temel Paket | 🥈 Gelişmiş Paket | 🥇 Platin Paket | ⚙️ Özel (Custom) |
| :--- | :---: | :---: | :---: | :---: |
| **Varsayılan Koltuk Kotası (`maxUsers`)** | **3 Koltuk** | **7 Koltuk** | **15 Koltuk (veya `null`)** | Süper Admin Belirler |
| `dashboard` | ✅ | ✅ | ✅ | Seçilebilir |
| `customers` | ✅ | ✅ | ✅ | Seçilebilir |
| `customers_potential` | ✅ | ✅ | ✅ | Seçilebilir |
| `customers_devices` | ✅ | ✅ | ✅ | Seçilebilir |
| `customers_contracts` | ✅ | ✅ | ✅ | Seçilebilir |
| `service` | ✅ | ✅ | ✅ | Seçilebilir |
| `service_create` | ✅ | ✅ | ✅ | Seçilebilir |
| `technicians` | ✅ | ✅ | ✅ | Seçilebilir |
| `stock` | ✅ | ✅ | ✅ | Seçilebilir |
| `stock_movements` | ✅ | ✅ | ✅ | Seçilebilir |
| `billing` | ✅ | ✅ | ✅ | Seçilebilir |
| `settings` | ✅ | ✅ | ✅ | Seçilebilir |
| `customer-requests` | ❌ | ✅ | ✅ | Seçilebilir |
| `stock_transfers` | ❌ | ✅ | ✅ | Seçilebilir |
| `stock_consignment` | ❌ | ✅ | ✅ | Seçilebilir |
| `stock_new_devices` | ❌ | ✅ | ✅ | Seçilebilir |
| `stock_secondhand` | ❌ | ✅ | ✅ | Seçilebilir |
| `cpc` | ❌ | ✅ | ✅ | Seçilebilir |
| `billing_invoicing` | ❌ | ✅ | ✅ | Seçilebilir |
| `mail-counters` | ❌ | ✅ | ✅ | Seçilebilir |
| `invoices` | ❌ | ✅ | ✅ | Seçilebilir |
| `invoices_create` | ❌ | ✅ | ✅ | Seçilebilir |
| `invoices_pending` | ❌ | ✅ | ✅ | Seçilebilir |
| `invoices_statement` | ❌ | ✅ | ✅ | Seçilebilir |
| `expense_entry` | ❌ | ✅ | ✅ | Seçilebilir |
| `financial-reports` | ❌ | ❌ | ✅ | Seçilebilir |
| `branch_profitability` | ❌ | ❌ | ✅ | Seçilebilir |
| `personnel` | ❌ | ❌ | ✅ | Seçilebilir |
| `ai` | ❌ | ❌ | ✅ | Seçilebilir |
| `agents` | ❌ | ❌ | ✅ | Seçilebilir |

---

## 3. Güvenlik ve Mimari Tasarım Esasları

### 3.1 `mergeTenantPermissions` Tuzağı ve Explicit False
Mevcut kod tabanındaki `mergeTenantPermissions` fonksiyonu üst izin açık olduğunda alt izni otomatik `true` yapmaktadır.
Örneğin Temel pakette `stock: true` olduğunda, `stock_transfers` tanımsız bırakılırsa `true`'ya dönüşür.
**Mimari Kural:** `intersectPermissions` fonksiyonu, paket tavanında yer almayan alt modülleri açıkça (`explicitly`) `false` olarak damgalayacaktır.

### 3.2 İki Eksenli Lisanslama (Ortogonalite)
- **Eksen 1:** `SubscriptionSettings` (Zaman / Tahsilat): `trial`, `active`, `payment_pending`, `inactive`.
- **Eksen 2:** `TenantLicense` (Özellik / Koltuk): `packageTier`, `allowedModules`, `maxUsers`.
- İki eksen birbirini ezmez. Ödeme bekleyen bir kiracının Platin paketi olsa bile paneli abonelik kuralı gereği kısıtlanır.

### 3.3 Koltuk Sayımı ve Yarış Durumu (Race Condition) Koruması
- `active: false` durumundaki kullanıcılar koltuk kotasını işgal etmez.
- Pasiften aktife alma işlemi, yeni kullanıcı oluşturma işlemiyle aynı kota denetimine tabidir.
- Eşzamanlı iki isteğin kotayı delmesini önlemek için `/api/admin/users/upsert` endpoint'i sayım ve yazma işlemini **Firestore Transaction** içerisinde atomik olarak yürütür.

### 3.4 Güvenlik Katmanları (Defense-in-Depth)
1. **İstemci Arayüzü (UI):** Firmanın lisansında olmayan modüller menüden gizlenir; Ayarlar sayfasında yetki verilemez.
2. **Runtime Guard:** `useTenantUserAccess` ve `dashboard/layout.tsx` doğrudan linkle erişimi engeller.
3. **API Kalkanı:** `/api/admin/users/upsert` ve `/delete` çağıran kimliğini doğrular, kotayı denetler ve yetkileri filtreler.
4. **Veri Katmanı (Faz B):** Kritik koleksiyonlar ve Functions/Webhook seviyesinde tenant lisans kontrolleri uygulanır.

---

## 4. Veri Modeli ve Tipler (`src/lib/tenantLicense.ts`)

```typescript
import { TenantModulePermissionKey } from '@/lib/modulePermissions';
import { Timestamp } from 'firebase/firestore';

export type TenantPackageTier = 'temel' | 'gelismis' | 'platin' | 'custom';

export interface TenantLicense {
    packageTier: TenantPackageTier;
    allowedModules: TenantModulePermissionKey[];
    maxUsers: number | null; // null = sınırsız (asla 999 sentinel kullanılmaz)
    licenseUpdatedAt?: Timestamp | string;
    licenseUpdatedBy?: string;
}

export interface PackageDefinition {
    id: TenantPackageTier;
    name: string;
    description: string;
    badgeColor: string;
    defaultMaxUsers: number | null;
    modules: TenantModulePermissionKey[];
}
```

---

## 5. Uygulama Fazları

- **Faz 1:** Tek Kaynak Lisans Motoru (`src/lib/tenantLicense.ts` ve `src/lib/modulePermissions.ts`)
- **Faz 2:** Süper Admin Lisans & Koltuk Kartı (`AdminPanel.tsx` ve `adminService.ts`)
- **Faz 3:** Kullanıcı API'si Sertleştirmesi (`/api/admin/users/upsert` ve `/delete`)
- **Faz 4:** Firma Ayarlar Sayfası UX Revizyonu (`dashboard/settings/page.tsx`)
- **Faz 5:** Çalışma Zamanı Kesişimi & Rota Koruması (`useTenantUserAccess.ts`, `layout.tsx`, `navigationConfig.ts`)
- **Faz 6:** Veri Katmanı Kalkanı (Cloud Functions, Webhook, Ajan Telemetri API)
- **Faz 7:** Canary Testi, Backfill ve Global Devreye Alma

---

## 6. Onay Durumu

Bu doküman, kıdemli mühendislik ekibinin karşılıklı incelemesi sonucunda onaylanmış ve uygulanmak üzere dondurulmuştur. 

Detaylı görev adımları için [TENANT_PAKET_VE_KULLANICI_YETKI_TASK_LISTESI.md](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/TENANT_PAKET_VE_KULLANICI_YETKI_TASK_LISTESI.md) dosyasını takip ediniz.
