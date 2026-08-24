# 🚀 Proservis-Web Implementation Guide

## 📋 Type Definitions (Tamamlandı ✅)

Type tanımlamaları güncellenmiştir: `src/types/index.ts`

### ✅ 1. Device Model - Bakım Anlaşması Alanları Eklendi

```typescript
export interface Device {
    // ... existing fields ...

    // 🔧 Bakım Anlaşması Alanları (YENİ)
    hasMaintenanceContract?: boolean;
    maintenancePeriod?: 'none' | 'monthly' | 'quarterly' | 'semiannual' | 'annual';
    lastMaintenanceDate?: Timestamp;
    nextMaintenanceDate?: Timestamp;
    maintenancePrice?: number;
    maintenanceCurrency?: 'TL' | 'USD' | 'EUR';
}
```

### ✅ 2. StockMovement Model - Müşteri Bilgileri Eklendi

```typescript
export interface StockMovement {
    // ... existing fields ...

    // 👤 Müşteri Bilgileri (YENİ)
    fromCustomerId?: string;
    fromCustomerName?: string;
    toCustomerId?: string;
    toCustomerName?: string;
    referenceType?: 'invoice' | 'service' | 'manual' | 'secondhand';
}
```

---

## 🛠️ Implementation Adımları

### ADIM 1: EditDeviceDialog Güncellemesi

**Dosya:** `src/components/customers/EditDeviceDialog.tsx`

#### 1a. Schema'ya Bakım Alanlarını Ekle

```diff
const deviceSchema = z.object({
    // ... existing fields ...
+   hasMaintenanceContract: z.boolean().default(false),
+   maintenancePeriod: z.enum(['none', 'monthly', 'quarterly', 'semiannual', 'annual']).default('none'),
+   lastMaintenanceDate: z.string().optional(),
+   nextMaintenanceDate: z.string().optional(),
+   maintenancePrice: z.string().optional().transform(v => v ? parseFloat(v) : 0),
+   maintenanceCurrency: z.enum(['TL', 'USD', 'EUR']).default('TL'),
})
```

#### 1b. State ve Form Hook'ları Ekle

```diff
const [hasMaintenanceContract, setHasMaintenanceContract] = useState(device.hasMaintenanceContract || false)
const [maintenancePeriod, setMaintenancePeriod] = useState(device.maintenancePeriod || 'none')

const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors }
} = useForm<DeviceFormData>({
    resolver: zodResolver(deviceSchema),
    defaultValues: {
        // ... existing ...
+       hasMaintenanceContract: device.hasMaintenanceContract,
+       maintenancePeriod: device.maintenancePeriod,
+       lastMaintenanceDate: toDateInput(device.lastMaintenanceDate),
+       nextMaintenanceDate: toDateInput(device.nextMaintenanceDate),
+       maintenancePrice: device.maintenancePrice?.toString() || '',
+       maintenanceCurrency: device.maintenanceCurrency || 'TL',
    }
})
```

#### 1c. JSX'e Bakım Sekmesi Ekle

```jsx
{/* Bakım Anlaşması Bölümü */}
<div className="grid gap-4">
    <h3 className="text-sm font-semibold">🔧 Bakım Anlaşması</h3>

    <label className="flex items-center gap-2">
        <input
            type="checkbox"
            checked={hasMaintenanceContract}
            onChange={(e) => {
                setHasMaintenanceContract(e.target.checked)
                setValue('hasMaintenanceContract', e.target.checked)
            }}
        />
        <span>Bakım Anlaşması Var</span>
    </label>

    {hasMaintenanceContract && (
        <div className="grid gap-4">
            <div>
                <Label>Bakım Periyodu</Label>
                <Controller
                    name="maintenancePeriod"
                    control={control}
                    render={({ field }) => (
                        <Select value={field.value} onValueChange={field.onChange}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="none">Seçim Yapınız</SelectItem>
                                <SelectItem value="monthly">Aylık</SelectItem>
                                <SelectItem value="quarterly">3 Aylık</SelectItem>
                                <SelectItem value="semiannual">6 Aylık</SelectItem>
                                <SelectItem value="annual">Yıllık</SelectItem>
                            </SelectContent>
                        </Select>
                    )}
                />
            </div>

            <div>
                <Label>Son Bakım Tarihi</Label>
                <input type="date" {...register('lastMaintenanceDate')} />
            </div>

            <div>
                <Label>Sonraki Bakım Tarihi</Label>
                <input type="date" {...register('nextMaintenanceDate')} />
            </div>

            <div className="grid grid-cols-[1fr_100px] gap-2">
                <div>
                    <Label>Bakım Bedeli</Label>
                    <input type="number" step="0.01" {...register('maintenancePrice')} />
                </div>
                <div>
                    <Label>Para</Label>
                    <Controller
                        name="maintenanceCurrency"
                        control={control}
                        render={({ field }) => (
                            <Select value={field.value} onValueChange={field.onChange}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="TL">TL</SelectItem>
                                    <SelectItem value="USD">USD</SelectItem>
                                    <SelectItem value="EUR">EUR</SelectItem>
                                </SelectContent>
                            </Select>
                        )}
                    />
                </div>
            </div>
        </div>
    )}
</div>
```

#### 1d. Submit Fonksiyonunu Güncelle

```diff
const onSubmit = async (data: DeviceFormData) => {
    try {
        setIsLoading(true)

        const updates: Partial<Device> = {
            brand: data.brand,
            model: data.model,
            serialNumber: data.serialNumber,
            isCpc: data.isCpc,
            isColor: data.isColor,
            // ... other fields ...
+           hasMaintenanceContract: data.hasMaintenanceContract,
+           maintenancePeriod: data.maintenancePeriod,
+           maintenancePrice: data.maintenancePrice,
+           maintenanceCurrency: data.maintenanceCurrency,
+           lastMaintenanceDate: data.lastMaintenanceDate ?
+               Timestamp.fromDate(new Date(`${data.lastMaintenanceDate}T12:00:00`)) : undefined,
+           nextMaintenanceDate: data.nextMaintenanceDate ?
+               Timestamp.fromDate(new Date(`${data.nextMaintenanceDate}T12:00:00`)) : undefined,
        }
        
        await CustomerService.updateDevice(tenantId, customerId, device.id, updates)
        onSuccess()
        setOpen(false)
    } catch (error) {
        console.error('Error updating device:', error)
    } finally {
        setIsLoading(false)
    }
}
```

> **⚠️ Timezone Notu:** `Timestamp.fromDate(new Date(dateString))` yalnız kullanıldığında saat dilimi kaynaklı bir gün kayması yaşanabilir. `T12:00:00` eklenerek (`new Date(\`${dateString}T12:00:00\`)`) öğlen saatine sabitlemek bu sorunu önler.

---

### ADIM 2: 2. El Cihaz Geçmiş Butonu - stock/page.tsx

**Dosya:** `src/app/dashboard/stock/page.tsx`

Mevcut 2. el cihaz tablosuna "Geçmiş Görüntüle" butonu ekleme:

```diff
// Tablo action sütununda
{
    id: "actions",
    cell: ({ row }) => {
        const stockItem = row.original
        return (
            <div className="flex gap-2">
+               <Button
+                   size="sm"
+                   variant="outline"
+                   onClick={() => showSecondHandHistory(stockItem)}
+               >
+                   📋 Geçmiş
+               </Button>
                <EditStockDialog
                    tenantId={tenantId}
                    stockItem={stockItem}
                    onSuccess={handleSuccess}
                />
            </div>
        )
    }
}
```

Yeni fonksiyon:

```typescript
const showSecondHandHistory = (stockItem: StockItem) => {
    if (!stockItem.secondHandInfo) return

    const {
        brand, model, serialNumber,
        acquiredFrom, acquiredCost, acquiredCostCurrency,
        acquiredAt, acquiredReason,
        temporaryInstalledAt, temporaryReceivedAt, temporaryCustomerName
    } = stockItem.secondHandInfo

    const historyText = `
Model: ${model || 'N/A'} (${brand})
Seri No: ${serialNumber || 'N/A'}

├─ Alındığı Yeri: ${acquiredFrom || 'Belirtilmedi'}
├─ Alış Fiyatı: ${acquiredCost || 0} ${acquiredCostCurrency || 'TL'}
├─ Alınma Tarihi: ${acquiredAt ? new Date(acquiredAt.toDate()).toLocaleDateString('tr-TR') : 'N/A'}
├─ Alım Nedeni: ${acquiredReason || 'Belirtilmedi'}
${temporaryCustomerName ? `├─ Müşteri: ${temporaryCustomerName}` : ''}
${temporaryInstalledAt ? `├─ Kurulum Tarihi: ${new Date(temporaryInstalledAt.toDate()).toLocaleDateString('tr-TR')}` : ''}
${temporaryReceivedAt ? `└─ Alınma Tarihi: ${new Date(temporaryReceivedAt.toDate()).toLocaleDateString('tr-TR')}` : ''}
    `.trim()

    alert(historyText) // Veya Dialog bileşeni kullanın
}
```

---

### ADIM 3: StockMovementDialog - Müşteri Adı Gösterimi

**Dosya:** `src/components/stock/StockMovementDialog.tsx` (veya benzer)

```diff
// Müşteri seçimi kısmında UID yerine ad göster
<Select value={selectedCustomer?.id || ''} onValueChange={(id) => {
    const customer = customers.find(c => c.id === id)
    setSelectedCustomer(customer)
}}>
    <SelectTrigger>
        <SelectValue placeholder="Müşteri seçin" />
    </SelectTrigger>
    <SelectContent>
        {customers.map(customer => (
-           <SelectItem key={customer.id} value={customer.id}>{customer.id}</SelectItem>
+           <SelectItem key={customer.id} value={customer.id}>{customer.name}</SelectItem>
        ))}
    </SelectContent>
</Select>

{/* Hareket geçmişinde */}
<div className="text-sm text-gray-600">
    {movement.type === 'IN' ? (
-       `Kaynak: ${movement.fromCustomerId}`
+       `Kaynak: ${movement.fromCustomerName || movement.fromCustomerId || 'Stok'}`
    ) : (
-       `Hedef: ${movement.toCustomerId}`
+       `Hedef: ${movement.toCustomerName || movement.toCustomerId || 'Satış'}`
    )}
</div>
```

---

### ADIM 4: Dashboard Bakım Kartları

**Dosya:** `src/app/dashboard/page.tsx`

Yeni kart bileşenleri ekle:

```typescript
// Maintenance Cards
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    {/* Bakım Zamanı Geçen Cihazlar */}
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="font-semibold text-red-900">⚠️ Bakım Zamanı Geçen</h3>
        <p className="text-2xl font-bold text-red-600">{expiredMaintenanceDevices}</p>
        <p className="text-sm text-red-600">Bakım gerekiyor</p>
    </div>

    {/* Bakım Zamanı Yaklaşan Cihazlar */}
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-semibold text-yellow-900">⏰ Bakım Zamanı Yaklaşan</h3>
        <p className="text-2xl font-bold text-yellow-600">{upcomingMaintenanceDevices}</p>
        <p className="text-sm text-yellow-600">1 haftaya kalmış</p>
    </div>
</div>
```

İlgili service fonksiyonları:

```typescript
// dashboardService.ts'ye ekle
export const getMaintenanceStats = async (tenantId: string) => {
    const devicesSnapshot = await getDocs(
        query(
            collection(db, `tenants/${tenantId}/customers`),
            where('hasMaintenanceContract', '==', true)
        )
    )

    const now = new Date()
    const oneWeekLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

    let expiredCount = 0
    let upcomingCount = 0

    for (const doc of devicesSnapshot.docs) {
        const customer = doc.data() as Customer
        const devices = await getDocs(
            collection(db, `tenants/${tenantId}/customers/${customer.id}/devices`)
        )

        for (const deviceDoc of devices.docs) {
            const device = deviceDoc.data() as Device
            const nextMaintenance = device.nextMaintenanceDate?.toDate()

            if (!nextMaintenance) continue

            if (nextMaintenance < now) {
                expiredCount++
            } else if (nextMaintenance <= oneWeekLater) {
                upcomingCount++
            }
        }
    }

    return { expiredCount, upcomingCount }
}
```

---

## 📦 Firestore Kuralları (Security Rules)

**Dosya:** `firestore.rules`

Bakım alanlarının güncellenmesi için yeterli izinlerin olduğundan emin olun:

```javascript
// Device updating rule
allow update: if request.auth != null && (
    request.resource.data.tenantId == get(/databases/$(database)/documents/users/$(request.auth.uid)).data.tenantId ||
    get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin'
);
```

---

## 🚀 Deployment Adımları

### 1. Local Test

```bash
cd proservis-web

# Dependencies yükle
npm install

# Type errors kontrolü
npm run type-check

# Dev server'ı başlat
npm run dev
```

**Test Etmeleri Gerekenler:**
- [ ] Cihaz düzenle → Bakım alanları görülüyor mu?
- [ ] Bakım bedeli girilip kaydediliyor mu?
- [ ] 2. El cihaz geçmişi gösteriliyor mu?
- [ ] Stok hareketi → Müşteri adı gösterilip UID gösterilmiyor mu?
- [ ] Dashboard → Bakım kartları görülüyor mu?

### 2. Build ve Deploy

```bash
# Production build
npm run build

# Firebase deploy
firebase deploy --only hosting

# Firestore rules deploy (gerekirse)
firebase deploy --only firestore:rules
```

### 3. Database Migration

**Mevcut cihazlara bakım alanları eklemesi gerekmekse:**

Cloud Functions ile migration script:

```typescript
// functions/migrateMaintenanceFields.ts
import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

export const migrateMaintenanceFields = functions.https.onRequest(
    async (req, res) => {
        const tenantId = req.query.tenantId as string;

        if (!tenantId) {
            return res.status(400).json({ error: 'tenantId required' });
        }

        const db = admin.firestore();
        let migratedCount = 0;

        try {
            const customersSnap = await db
                .collection(`tenants/${tenantId}/customers`)
                .get();

            for (const customerDoc of customersSnap.docs) {
                const devicesSnap = await db
                    .collection(
                        `tenants/${tenantId}/customers/${customerDoc.id}/devices`
                    )
                    .get();

                for (const deviceDoc of devicesSnap.docs) {
                    const data = deviceDoc.data();

                    // Eğer bakım alanları yoksa ekle
                    if (!data.hasMaintenanceContract) {
                        await deviceDoc.ref.update({
                            hasMaintenanceContract: false,
                            maintenancePeriod: 'none',
                            maintenancePrice: 0,
                            maintenanceCurrency: 'TL',
                        });
                        migratedCount++;
                    }
                }
            }

            res.json({
                success: true,
                migratedCount,
                message: `${migratedCount} cihaz güncellendi`
            });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
);
```

---

## ✅ Checklist

- [x] Types güncellenmiştir (`src/types/index.ts`)
- [x] EditDeviceDialog bakım alanlarıyla güncellenmiştir
- [x] Stock movement müşteri adı gösterimi yapılmıştır (`StockMovementsTab`, `StockHistoryDialog`)
- [x] 2. El cihaz yönetimi ayrı sayfaya taşınmıştır (`/dashboard/stock/secondhand`)
- [x] Dashboard bakım kartları eklenmiştir (detay listeleriyle birlikte)
- [x] Firestore rules validate edilmiştir (kapsamlı rules var)
- [ ] Local test tamamlanmıştır
- [ ] Build başarılı (`npm run build`)
- [ ] Firebase deploy hazırlanmıştır (`firebase deploy`)

---

## 🔗 İlgili Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `src/types/index.ts` | ✅ Güncellendi |
| `src/components/customers/EditDeviceDialog.tsx` | ✅ Güncellendi (sözleşmeden otomatik doldurma dahil) |
| `src/app/dashboard/stock/page.tsx` | ✅ Ayrı secondhand sayfasına taşındı |
| `src/components/stock/StockMovementDialog.tsx` | ⚠️ Basit dialog, müşteri adı diğer bileşenlerde gösteriliyor |
| `src/app/dashboard/page.tsx` | ✅ Bakım kartları + detay listeleri eklendi |
| `firestore.rules` | ✅ Kapsamlı rules mevcut |

