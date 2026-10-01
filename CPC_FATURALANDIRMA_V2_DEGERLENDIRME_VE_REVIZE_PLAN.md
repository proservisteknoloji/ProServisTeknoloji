# Sayaç Faturalandırma ve CPC Hesaplama Motoru
## V2 Planı Teknik Değerlendirmesi ve Revize Uygulama Planı

**Tarih:** 08.09.2026  
**Kapsam:** Sayaç baseline çözümleme, CPC kullanım hesabı, canlı sözleşme fiyatları, atomik faturalama ve ara okumalar.

---

## 1. Genel Değerlendirme

V2 planı önceki plana göre daha sağlamdır ve ana yönü doğrudur. Özellikle aşağıdaki kararlar mevcut kodla uyumludur:

- `0` kurulum sayacının geçerli kabul edilmesi.
- Faturalandırılmamış ara okumaların baseline olmaması.
- Hesaplamanın tek bir saf domain motoruna taşınması.
- Fatura ve sayaç güncellemelerinin atomik ele alınması.

Mevcut [meterReadingBaseline.ts](proservis-web/src/lib/meterReadingBaseline.ts) içinde hem `0` kurulum sayacını güncel okumaya eşitleyen hem de faturasız ara okumayı baseline yapabilen mantık bulunmaktadır. Benzer hesaplamalar billing sayfası, cihaz gruplu tablo, kolonlar ve fatura ekranlarında tekrar edilmektedir.

Plan uygulanabilir; ancak aşağıdaki düzeltmeler yapılmadan doğrudan kodlamaya başlanmamalıdır.

---

## 2. Kritik Sorunlar ve Düzeltmeler

### 2.1 `writeBatch` tek başına duplicate faturayı engellemez

`writeBatch` işlemleri atomik yapar; ancak aynı anda iki kullanıcı aynı okumalar için farklı fatura oluşturabilir.

Gerekli kurallar:

1. Seçili okumalar transaction içinde tekrar okunmalıdır.
2. Hepsinin hâlâ `isBilled === false` olduğu doğrulanmalıdır.
3. Deterministik bir idempotency anahtarı kullanılmalıdır.
4. Fatura ve okumalar aynı işlemde yazılmalıdır.
5. Daha önce oluşturulmuş işlem varsa aynı fatura döndürülmelidir.

Firestore batch sınırı olan 500 yazma işlemi de hesaba katılmalıdır. Çok cihazlı faturalar için limit kontrolü yapılmalıdır.

### 2.2 Fatura ve `isBilled` güncellemesi tek servis olmalıdır

Mevcut [billing-page/page.tsx](proservis-web/src/app/dashboard/billing/billing-page/page.tsx) önce faturayı oluşturup sonra okumaları tek tek güncellemektedir. Tarayıcı kapanırsa fatura oluşup okumalar açık kalabilir.

Yeni servis önerisi:

```ts
BillingService.createCpcInvoiceWithReadings(...)
```

Bu servis:

- Seçili okumaları tekrar doğrulamalı.
- Fatura snapshot'ını oluşturmalı.
- Okumaları `billingId`, `isBilled`, `billedAt` ile işaretlemeli.
- Aynı okumaların ikinci kez faturalanmasını engellemeli.
- `created`, `duplicate`, `blocked` veya `conflict` sonucu döndürmelidir.

### 2.3 `activeContracts` mevcut veri modeliyle doğrulanmalıdır

Plan şu tipi varsayıyor:

```ts
resolveDeviceLivePricing(device, activeContracts?: CustomerContract[])
```

Ancak projede gerçek aktif sözleşme kaynağı ve `CustomerContract` modeli net değildir. Önce şu sorular cevaplanmalıdır:

- Aktif sözleşme hangi koleksiyondan okunacak?
- Fiyat sözleşmede mi, cihaz kartında mı tutuluyor?
- Sözleşme müşteri bazlı mı, cihaz bazlı mı?
- Başlangıç ve bitiş tarihleri var mı?
- Değişiklik geriye dönük mü, yalnızca ileriye dönük mü uygulanacak?

Mevcut olmayan bir sözleşme tipine göre motor yazılmamalıdır.

### 2.4 `cpcSinglePrice` ve `merged` modu doğrulanmalıdır

Plan şu alanları varsayıyor:

```ts
cpcSinglePrice
mode: 'separate' | 'merged'
```

Mevcut `Device` tipinde bu alanların bulunup bulunmadığı doğrulanmalıdır. Gerçek Firestore şemasında yoksa iki seçenek vardır:

- Motor yalnızca mevcut `cpcBwPrice` ve `cpcColorPrice` alanlarını kullanır.
- Yeni fiyatlandırma modu için açık bir veri migration'ı yapılır.

Olmayan alanlar sessizce okunmamalıdır.

### 2.5 Vergi hesabı CPC domain motorundan ayrılmalıdır

Planın `CpcCalculationResult` tipinde `taxAmount` ve `grandTotal` bulunuyor; ancak vergi oranı motor girdisi olarak tanımlanmamış. Mevcut kodda vergi oranı doğrudan `%20` olarak hesaplanmaktadır.

Daha doğru ayrım:

- `cpcBillingEngine`: Sayaç kullanımı, kota ve vergi öncesi CPC tutarı.
- `invoicePricingService`: Vergi oranı, vergi tutarı ve fatura toplamı.
- Vergi oranı tenant veya fatura ayarlarından okunmalıdır.
- `%20` sabit değeri domain motoruna gömülmemelidir.

### 2.6 Sayaç düşüşü faturayı bloklamalıdır

Truth table'de sayaç düşüşü için `0 + kritik uyarı` yazıyor. Bu, faturanın sessizce sıfırla oluşturulması anlamına gelmemelidir.

Önerilen sonuç:

```ts
status: 'blocked'
reason: 'COUNTER_DECREASED'
```

Kullanıcı uyarıyı onaylamadan fatura oluşturulmamalıdır.

### 2.7 Ara okumaların tamamını faturalandı yapma kararı korunarak sınırlandırılmalıdır

Son ve ara okumaların tamamının `isBilled: true` yapılması uygulanabilir; fakat:

- Ara okumalar başka bir faturaya bağlı olmamalıdır.
- Tüm okumalar aynı tenant, müşteri ve cihaza ait olmalıdır.
- Fatura iptal edilirse ilişkili okumalar geri açılmalıdır.
- Aynı okumalar başka bir işlem tarafından rezerve edilmişse işlem durmalıdır.

Mevcut `isBilled` alanı korunabilir; ancak `billingId` ve işlem durumu da kullanılmalıdır:

```ts
billingStatus: 'unbilled' | 'reserved' | 'billed' | 'released'
```

---

## 3. Revize Domain Motoru

Yeni dosya:

```text
proservis-web/src/lib/cpcBillingEngine.ts
```

Motor yalnızca saf iş mantığını içermelidir:

```ts
resolveDeviceMeterBaseline(...)
resolveDeviceLivePricing(...)
calculateDeviceCpcBilling(...)
detectCounterAnomaly(...)
```

### 3.1 Baseline önceliği

```text
1. Target tarihinden önceki en son isBilled=true okuma
2. Device.installCounters
3. Legacy device.meters
4. Kesin olarak 0
```

Şunlar baseline olamaz:

- Faturalandırılmamış ara okuma.
- `currentCounters`.
- Servis kaydı.
- Target reading'in kendisi.
- Target tarihinden sonraki faturalandırılmış okuma.

Kurulum sayacında açıkça `0` varsa `0` korunmalıdır. `currentCounters` kesinlikle kurulum baseline'ı olarak kullanılmamalıdır.

### 3.2 Fiyat çözümleme

Önce gerçek sözleşme veri kaynağı belirlenmelidir. Ardından resolver şu sonucu üretmelidir:

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

Önerilen öncelik:

```text
Geçerli aktif sözleşme
-> cihaz kartı
-> açıkça tanımlanmış varsayılan
-> güvenli sıfır değer
```

Sözleşme geçerlilik tarihleri hesaba katılmalıdır. Varsayılan fiyat sessizce uygulanmamalı, kaynak bilgisi sonuçta görünmelidir.

### 3.3 Motor çıktısı

```ts
{
    baseline,
    current,
    usage,
    pricing,
    financialsBeforeTax,
    baselineSource,
    counterAnomaly,
    warnings
}
```

Farklı para birimleri varsa tek bir `grandTotal` üretilmemelidir. İşlem hata vermeli veya para birimine göre ayrı toplam üretmelidir.

---

## 4. Revize Uygulama Fazları

### Faz 1: Domain motoru ve tipler

- `cpcBillingEngine.ts` oluşturulması.
- `meterReadingBaseline.ts` içindeki eski mantığın motora delege edilmesi.
- `currentCounters` fallback'inin kaldırılması.
- Baseline kaynak tiplerinin gerekirse `zero` desteğiyle güncellenmesi.
- Kota ve fiyat çözümleme tiplerinin tanımlanması.

### Faz 2: Tüm ekranların motora bağlanması

Aşağıdaki ekranlarda bağımsız baseline ve fiyat hesapları kaldırılmalıdır:

- `billing-page/page.tsx`
- `DeviceGroupedBillingTable.tsx`
- `billing/columns.tsx`
- `invoices/page.tsx`
- `billing/history/page.tsx`
- `invoices/pending/page.tsx`

Özellikle `rawBaseBw > 0`, faturasız `latestReading` fallback'leri ve ekran bazlı `Math.max` hesapları tek motora taşınmalıdır.

### Faz 3: Atomik fatura oluşturma

1. İdempotency anahtarı üret.
2. Seçili okumaları transaction içinde oku.
3. Tenant, müşteri ve cihaz uyumluluğunu doğrula.
4. Okumaların hâlâ faturalandırılmamış olduğunu doğrula.
5. Negatif fark veya başka anomaly varsa işlemi durdur.
6. Domain motoruyla hesaplamayı üret.
7. Fatura satırlarına fiyat ve hesaplama snapshot'ını yaz.
8. İlgili okumaları aynı işlemde işaretle.
9. İşlem sonucunu açık biçimde döndür.

### Faz 4: Fatura snapshot'ı

Fatura oluşturulduğu anda şu bilgiler saklanmalıdır:

- Baseline sayaçları.
- Güncel sayaçları.
- Brüt kullanım.
- Faturalanabilir kullanım.
- Birim fiyatlar.
- Kotalar.
- Para birimleri.
- Kira bedeli.
- Vergi oranı.
- Kur bilgisi.
- Fiyatlandırma kaynağı.
- Kullanılan meter reading ID'leri.
- Engine version.

Sonraki sözleşme veya cihaz fiyat değişiklikleri oluşturulmuş faturayı değiştirmemelidir.

### Faz 5: Legacy veri uyumluluğu

- Eski `latest_reading` baseline kayıtları yeni motorla yeniden hesaplanmalıdır.
- Eski `baseBwCounter` ve `baseColorCounter` alanları audit amacıyla korunabilir.
- Yeni hesaplama önceliği domain motorunda olmalıdır.
- Eski faturalar değiştirilmemelidir.
- Açık ve faturasız kayıtlar yeni motorla yeniden hesaplanmalıdır.

---

## 5. Test Kabul Kriterleri

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
2. Fatura oluşturulunca fiyat snapshot olarak saklanır.
3. Sonraki fiyat değişikliği oluşturulmuş faturayı değiştirmez.
4. Farklı para birimleri güvenli biçimde reddedilir veya ayrı toplanır.
5. Kota formülü için sınır senaryoları test edilir.
6. Sözleşme yoksa kullanılan fiyat kaynağı görünür.

### Sayaç anomalileri

1. Sayaç düşüşü fatura oluşturmayı bloklar.
2. Sayaç reseti sessizce sıfır çekim olarak kaybolmaz.
3. Cihaz değişikliği açıkça işaretlenir.

### Fatura işlemi

1. Aynı faturalama isteği duplicate fatura oluşturmaz.
2. Fatura ve reading güncellemeleri kısmi kalmaz.
3. Fatura iptali ilişkili okumaları güvenli biçimde serbest bırakır.
4. 500 yazma sınırı aşılınca kontrollü hata verilir.
5. Aynı reading başka fatura tarafından rezerve edilmişse işlem durur.

### Kalite kontrolü

```bash
npm run lint
npm run build
```

`cpcBillingEngine` için gerçek bir unit test veya test runner kullanılmalıdır. Sadece build başarılı olması hesaplama doğruluğunu kanıtlamaz.

---

## 6. Nihai Karar

V2 planı teknik olarak doğru yöndedir ve uygulanabilir. Ancak **koşullu onaylanmalıdır**.

Uygulamadan önce mutlaka:

1. `writeBatch` yanına idempotency ve reading doğrulaması eklenmeli.
2. Gerçek sözleşme veri modeli kesinleştirilmeli.
3. Mevcut olmayan `CustomerContract`, `cpcSinglePrice` ve `merged` alanları doğrulanmalı veya kaldırılmalı.
4. Vergi hesabı CPC motorundan ayrılmalı.
5. Sayaç düşüşü faturayı bloklayan anomaly durumuna dönüştürülmeli.
6. Fatura snapshot'ı ve işlem durumu eklenmeli.
7. Firestore batch/transaction limitleri hesaba katılmalı.

Bu düzeltmelerle `cpcBillingEngine`, mevcut dağınık hesaplamaları güvenilir biçimde merkezileştirebilir ve 0 baseline, ara okuma, sözleşme fiyatı, sayaç reseti ve duplicate fatura sorunlarını kontrol altına alabilir.
