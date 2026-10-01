# Sayaç Faturalandırma ve CPC Hesaplama Motoru
## V3 Planı Teknik Değerlendirmesi ve Revize Uygulama Planı

**Tarih:** 08.09.2026  
**Kapsam:** Sayaç baseline çözümleme, CPC kullanım hesabı, canlı sözleşme hiyerarşisi, transaction güvenliği, vergi ayrımı ve modüler mimari.

---

## 1. Genel Değerlendirme

V3 planı önceki sürümlere göre oldukça olgunlaşmıştır ve ana mimari onaylanabilir durumdadır.

Doğru kararlar:

- `0` kurulum sayacının geçerli kabul edilmesi.
- `currentCounters` alanının baseline'dan çıkarılması.
- Aktif sözleşme -> cihaz kartı -> fallback fiyat hiyerarşisi.
- Vergi hesabının CPC domain motorundan ayrılması.
- Sayaç düşüşünün faturayı bloklaması.
- Firestore transaction kullanılması.
- Fatura snapshot'ının oluşturulması.

Bununla birlikte V3 henüz tamamen uygulamaya hazır değildir. Aşağıdaki maddeler kodlamadan önce plana eklenmelidir.

---

## 2. Kritik Eksikler ve Düzeltmeler

### 2.1 500 işlem sınırında chunk kullanılmamalıdır

Plan, 500 yazma sınırı için chunk kontrolünden bahsediyor. Ancak işlemi parçalara bölmek atomikliği bozar:

- İlk parça fatura ve bazı okumaları yazar.
- İkinci parça başarısız olur.
- Fatura kısmen kilitlenmiş olur.

İlk sürüm için doğru davranış:

```text
Fatura + reading güncellemeleri 500 işlem sınırını aşarsa işlem reddedilir.
```

Bir fatura dokümanı da yazıldığı için tek işlemde pratik sınır en fazla 499 reading güncellemesidir.

Daha büyük işlemler için ileride `reservation` tabanlı çok aşamalı bir akış tasarlanabilir.

### 2.2 Idempotency anahtarı tüm faturayı kapsamalıdır

Şu anahtar yetersizdir:

```text
tenantId_customerId_deviceId_readingIdsSorted
```

Çünkü tek fatura birden fazla cihaz içerebilir. Önerilen anahtar:

```text
tenantId_customerId_allReadingIdsSorted_operationType
```

Ayrıca deterministik bir işlem dokümanı kullanılmalıdır:

```text
tenants/{tenantId}/billing_operations/{idempotencyKey}
```

Transaction içinde bu belge okunmalı; mevcutsa işlem `duplicate` sonucu döndürmelidir.

### 2.3 `billingId` ve `invoiceId` tek standarda indirilmeli

Mevcut projede sayaç kayıtlarında `billingId` kullanılmaktadır. V3 planında ise `invoiceId` öneriliyor.

İki farklı alanın farklı anlamlarda kullanılmasına izin verilmemelidir. En düşük riskli seçenek mevcut alanı korumaktır:

```ts
billingId
```

Yeni `invoiceId` eklenecekse migration, sorgular ve iptal akışları birlikte güncellenmelidir.

### 2.4 Taslak fatura ile kesin fatura ayrılmalı

Taslak fatura oluşturulurken okumaları doğrudan `isBilled: true` yapmak semantik olarak sorunludur. Taslak henüz kesin fatura değildir.

Önerilen durum modeli:

```ts
billingStatus: 'unbilled' | 'reserved' | 'billed' | 'released'
```

Davranış:

- Taslak oluşturulunca: `reserved`.
- Fatura kesinleşince: `billed` ve `isBilled: true`.
- Taslak iptal edilince: `released` ve tekrar bekleyen duruma dönüş.

Mevcut `isBilled` alanı geriye dönük uyumluluk için korunabilir.

### 2.5 Çoklu para birimi sonucu veri modelinde gösterilmeli

V3 metninde `totalsByCurrency` üretilmesi öneriliyor; fakat `CpcDeviceCalculationResult` içinde tek bir `currency` ve toplam alanı bulunuyor.

İlk sürüm için öneri:

- Aynı faturadaki CPC ve kira kalemleri aynı para biriminde olmalıdır.
- Farklı para birimi tespit edilirse fatura oluşturma bloklanmalıdır.
- Kur dönüşümü ayrı bir faz olarak uygulanmalıdır.

Alternatif olarak sonuç modelinde şu alan bulunmalıdır:

```ts
totalsByCurrency: Record<'TL' | 'USD' | 'EUR', number>;
```

Tek para birimi netleşmeden farklı para birimleri tek `grandTotal` içinde toplanmamalıdır.

### 2.6 Eksik fiyat sıfır fiyat olarak kabul edilmemeli

Fiyat hiyerarşisindeki `FALLBACK` sonucu sessizce `0` fiyat üretiyorsa ücretsiz fatura oluşabilir.

Fiyat bulunamadığında:

```ts
status: 'blocked'
anomaly: 'MISSING_PRICING'
```

üretilmelidir. Sıfır fiyat yalnızca açıkça ücretsiz CPC sözleşmesi olarak tanımlanmışsa geçerli olmalıdır.

### 2.7 Pure engine ile sözleşme yükleme katmanı ayrılmalı

`cpcBillingEngine.ts` Firebase veya servis import etmemelidir.

Doğru akış:

```text
Service Layer / Firebase
    -> aktif sözleşme ve cihaz verisini yükler
    -> plain object olarak engine'e verir
    -> engine saf hesaplama yapar
```

`activeContracts` motorun içine hazır veri olarak verilmelidir.

### 2.8 Sayaç düşüşü kanal bazında raporlanmalı

S/B sayaç düşerken renkli sayaç artabilir. Motor tüm cihazı bloklasa bile hangi kanalın düştüğü kullanıcıya gösterilmelidir.

Önerilen sonuç:

```ts
{
    bw: { status: 'ok' | 'decreased', baseline, current },
    color: { status: 'ok' | 'decreased', baseline, current }
}
```

İlk sürümde kanallardan herhangi biri düşerse cihaz faturası bloklanabilir; ancak uyarı S/B veya renkli kanal bazında olmalıdır.

---

## 3. Revize Transaction Akışı

`BillingService.createCpcInvoiceWithReadings` aşağıdaki sırayı izlemelidir:

1. Deterministik idempotency anahtarı üret.
2. Idempotency dokümanını transaction içinde oku.
3. Fatura ve tüm reading dokümanlarını transaction içinde oku.
4. Tenant, müşteri ve cihaz ilişkilerini doğrula.
5. Reading'lerin başka faturaya bağlı olmadığını doğrula.
6. Toplam okuma ve yazma sayısının 500 sınırını aşmadığını doğrula.
7. Domain motoruyla hesaplamayı üret.
8. Eksik fiyat veya sayaç anomalisi varsa işlemi durdur.
9. Fatura snapshot'ını yaz.
10. Reading kayıtlarını `reserved` veya `billed` olarak güncelle.
11. Idempotency dokümanını tamamlandı olarak yaz.
12. `created`, `duplicate`, `blocked` veya `conflict` sonucu döndür.

Transaction içinde tüm okumalar yazılmadan önce okunmuş olmalıdır. Otomatik Firestore ID kullanılmamalıdır.

---

## 4. Revize Domain Motoru

Yeni dosya:

```text
proservis-web/src/lib/cpcBillingEngine.ts
```

Saf motor fonksiyonları:

```ts
resolveDeviceMeterBaseline(...)
resolveDeviceLivePricing(...)
calculateDeviceCpcBilling(...)
detectCounterAnomaly(...)
```

### Baseline önceliği

```text
1. Target tarihinden önceki en son isBilled=true okuma
2. Device.installCounters
3. Legacy device.meters
4. Kesin olarak 0
```

Baseline olamayacaklar:

- Faturalandırılmamış ara okuma.
- `currentCounters`.
- Servis kaydı.
- Target reading'in kendisi.
- Target tarihinden sonraki faturalandırılmış okuma.

Kurulum sayacı açıkça `0` ise `0` korunmalıdır.

### Fiyat çözümleme

Önce gerçek sözleşme veri kaynağı ve geçerlilik tarihleri doğrulanmalıdır. Sonuç şu bilgileri içermelidir:

```ts
{
    bwUnitPrice,
    colorUnitPrice,
    bwCurrency,
    colorCurrency,
    bwAllowance,
    colorAllowance,
    bwMinQuota,
    colorMinQuota,
    hasRentalFee,
    rentalFee,
    rentalCurrency,
    pricingSource,
    contractId
}
```

Öncelik:

```text
Geçerli aktif sözleşme
-> cihaz kartı
-> açıkça tanımlanmış varsayılan
-> MISSING_PRICING ile bloklama
```

### Hesaplama sonucu

Sonuç en az şu bilgileri içermelidir:

```ts
{
    status: 'calculable' | 'blocked',
    baseline,
    current,
    usage,
    pricing,
    financialsBeforeTax,
    anomaly,
    warnings
}
```

Sayaç düşüşü veya fiyat eksikliği varsa `blocked` dönmelidir.

---

## 5. Fatura Snapshot'ı

Fatura oluşturulduğu anda aşağıdaki bilgiler saklanmalıdır:

- Baseline sayaçları.
- Güncel sayaçlar.
- Kullanılan meter reading ID'leri.
- Brüt ve faturalanabilir kullanım.
- Birim fiyatlar.
- Kotalar.
- Para birimleri.
- Kira bedeli.
- Vergi oranı.
- Kur bilgisi.
- Fiyatlandırma kaynağı.
- Sözleşme ID'si.
- Engine version.
- Hesaplama zamanı.

Sonraki cihaz veya sözleşme değişiklikleri oluşturulmuş faturayı değiştirmemelidir.

---

## 6. Uygulama Fazları

### Faz 1: Domain motoru

- `cpcBillingEngine.ts` oluştur.
- `meterReadingBaseline.ts` içindeki eski mantığı motora delege et.
- `currentCounters` fallback'ini kaldır.
- Baseline kaynak tiplerini güncelle.
- Kota, fiyat ve anomaly tiplerini tanımla.

### Faz 2: Servis katmanı

- Transaction tabanlı `createCpcInvoiceWithReadings` ekle.
- Idempotency dokümanı ekle.
- `billingId`/`invoiceId` standardını kesinleştir.
- Taslak için `reserved`, kesin fatura için `billed` durumunu uygula.
- İptal akışında okumaları güvenli biçimde serbest bırak.

### Faz 3: Tüketici ekranları

Aşağıdaki ekranlarda bağımsız baseline ve fiyat hesapları kaldırılmalıdır:

- `billing-page/page.tsx`
- `DeviceGroupedBillingTable.tsx`
- `billing/columns.tsx`
- `invoices/page.tsx`
- `billing/history/page.tsx`
- `invoices/pending/page.tsx`

Özellikle `rawBaseBw > 0`, faturasız `latestReading` fallback'leri ve ekran bazlı `Math.max` hesapları tek motora taşınmalıdır.

### Faz 4: Legacy uyumluluk

- Eski `latest_reading` baseline kayıtları yeni motorla yeniden hesaplanmalıdır.
- Eski `baseBwCounter` ve `baseColorCounter` alanları audit amacıyla korunabilir.
- Eski faturalar değiştirilmemelidir.
- Açık ve faturasız kayıtlar yeni motorla yeniden hesaplanmalıdır.

---

## 7. Test Kabul Kriterleri

### Baseline

1. Kurulum `0`, güncel `5000` -> kullanım `5000`.
2. Kurulum `1500`, güncel `5000` -> kullanım `3500`.
3. Son fatura `5000`, güncel `7200` -> kullanım `2200`.
4. Kurulum eksik, güncel `5000` -> baseline `0`, kullanım `5000`.
5. Ara okumalar baseline'ı değiştirmez.
6. Gelecek tarihli faturalandırılmış okuma baseline'a alınmaz.
7. `currentCounters` baseline olarak kullanılmaz.

### Fiyat ve kota

1. Aktif sözleşme fiyatı açık taslakta görünür.
2. Fiyat bulunamazsa işlem `MISSING_PRICING` ile bloklanır.
3. Fatura oluşturulunca fiyat snapshot olarak saklanır.
4. Sonraki fiyat değişikliği oluşturulmuş faturayı değiştirmez.
5. Farklı para birimleri aynı toplamda birleştirilmez.
6. Sözleşme yoksa kullanılan kaynak veya bloklama nedeni görünür.

### Anomali

1. S/B sayaç düşüşü fatura oluşturmayı bloklar.
2. Renkli sayaç düşüşü kanal bazında raporlanır.
3. Sayaç reseti sessizce sıfır çekim olarak kaybolmaz.
4. Cihaz değişikliği açıkça işaretlenir.

### Transaction ve idempotency

1. Aynı idempotency key ile iki eşzamanlı istek duplicate fatura oluşturmaz.
2. Reading başka faturaya bağlıysa işlem conflict döndürür.
3. 500 işlem sınırı aşılırsa işlem kontrollü biçimde reddedilir.
4. Transaction retry duplicate tarihçe veya fatura üretmez.
5. Taslak iptali reading'leri güvenli biçimde serbest bırakır.
6. Fatura ve reading güncellemeleri kısmi kalmaz.

### Kalite kontrolü

```bash
npm run lint
npm run build
```

Ayrıca `cpcBillingEngine` için gerçek bir unit test veya test runner kullanılmalıdır. Sadece build başarısı hesaplama doğruluğunu kanıtlamaz.

---

## 8. Nihai Karar

V3 planı teknik olarak doğru yöndedir ve koşullu olarak onaylanabilir.

Uygulamadan önce mutlaka:

1. 500 işlem aşılırsa chunk yerine kontrollü red uygulanmalı.
2. Idempotency anahtarı tüm reading ID'lerini kapsamalı.
3. `billingId` ve `invoiceId` arasında tek standart seçilmeli.
4. Taslak fatura ile kesinleşmiş fatura ayrılmalı.
5. Çoklu para birimi sonucu modelde açıkça tanımlanmalı.
6. Eksik fiyat sıfır fiyat değil, bloklanmış işlem olmalı.
7. Pure engine ile sözleşme yükleme katmanı ayrılmalı.
8. Transaction ve idempotency testleri genişletilmeli.

Bu düzeltmelerle V3, üretim ortamında uygulanabilecek güvenilir bir CPC faturalandırma mimarisi seviyesine gelir.
