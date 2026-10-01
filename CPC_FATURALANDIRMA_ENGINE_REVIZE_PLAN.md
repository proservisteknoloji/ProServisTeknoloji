# Sayaç Faturalandırma ve CPC Hesaplama Motoru
## Plan Değerlendirmesi ve Revize Uygulama Planı

**Tarih:** 08.09.2026  
**Kapsam:** Sayaç baseline çözümleme, CPC kullanım hesabı, canlı sözleşme fiyatları, fatura oluşturma ve ara okumalar.

---

## 1. Genel Değerlendirme

Planın ana teşhisi doğrudur. Mevcut sistemde özellikle iki gerçek hata bulunmaktadır:

- Kurulum sayacı `0` olduğunda ilk okuma güncel sayaca eşitlenebilmektedir.
- Daha önce faturalandırılmamış ara okumalar baseline olarak kullanılabilmektedir.

Mevcut [meterReadingBaseline.ts](proservis-web/src/lib/meterReadingBaseline.ts) içinde bu davranış doğrudan görülmektedir. Ayrıca aynı hesaplama mantığının billing sayfası, cihaz gruplu tablo, kolonlar ve çeşitli fatura ekranlarında tekrarlandığı tespit edilmiştir.

Planın mimari yönü doğrudur; ancak uygulamaya başlamadan önce aşağıdaki düzeltmeler zorunludur.

---

## 2. Kritik Düzeltmeler

### 2.1 `currentCounters` kurulum baseline'ı olamaz

Plan `installCounters ?? meters ?? 0` yaklaşımını öneriyor. Bu doğrudur. Ancak mevcut yardımcı fonksiyon eksik kurulum sayacında `currentCounters` alanına fallback yapmaktadır.

Doğru kural:

```ts
installCounters.bw ?? meters.bw ?? 0
```

- Açıkça `0` verilmişse `0` geçerli bir kurulum sayacıdır.
- `currentCounters` hiçbir zaman kurulum baseline'ı olarak kullanılmamalıdır.
- `meters` yalnızca legacy sistemde kurulum sayacını temsil ettiği doğrulanırsa kullanılmalıdır.

### 2.2 Canlı fiyat ile kesinleşmiş fatura ayrılmalıdır

Sözleşme veya cihaz fiyatı değiştiğinde açık faturalama ekranında güncel fiyatın görünmesi istenebilir. Ancak fatura oluşturulduktan sonra fatura tekrar cihazdaki fiyatlardan hesaplanmamalıdır.

Kurallar:

- Taslak/önizleme: güncel cihaz ve sözleşme fiyatları kullanılır.
- Fatura oluşturma anı: fiyat, kota, para birimi ve kira bedeli fatura satırına snapshot olarak yazılır.
- Kesinleşmiş fatura: cihazdaki sonraki fiyat değişikliklerinden etkilenmez.
- Eski faturalar yeniden hesaplanmaz.

### 2.3 Para birimleri açıkça yönetilmelidir

S/B, renkli ve kira alanlarının farklı para birimleri olabilir:

```ts
cpcBwCurrency
cpcColorCurrency
rentalCurrency
```

TL, EUR ve USD değerleri tek bir `grandTotal` içinde toplanamaz.

İlk sürüm için öneri:

- Farklı para birimlerinin aynı faturada toplanmasına izin verilmemesi.
- Kullanıcıya açık hata gösterilmesi.
- İleri aşamada kur dönüşümü veya para birimi bazlı ayrı toplamlar eklenmesi.

### 2.4 Kota formülü kesinleştirilmelidir

Mevcut kodda mantık şu şekildedir:

```ts
netUsage = Math.max(0, usage - freeAllowance);
billableUsage = Math.max(minQuota, netUsage);
```

Burada `minQuota`, minimum faturalandırılabilir adet gibi kullanılmaktadır. `minQuota` ile `freeBwCopies`/`freeColorCopies` farklı iş anlamlarına sahipse formül dokümante edilmeli ve test edilmelidir.

### 2.5 Sayaç düşüşü sessizce sıfırlanmamalıdır

Mevcut `Math.max(0, current - baseline)` yaklaşımı sayaç düşüşünü görünmez yapabilir. Sayaç düşüşü şu nedenlerden kaynaklanabilir:

- Cihaz resetlenmesi.
- Sayaç değişimi.
- Yanlış okuma.
- Cihazın değiştirilmesi.

Bu durum sıfır çekim olarak gösterilmemeli, `counterReset` veya `reviewRequired` uyarısı üretmelidir.

### 2.6 Ara okumalar ile fatura kullanımı ayrılmalıdır

Ara okumaların fatura baseline'ını değiştirmemesi doğrudur. Ancak UI'da iki farklı hesap ayrı gösterilmelidir:

- **Fatura hesabı:** Son faturalandırılan sayaç veya kurulum sayacı ile son geçerli sayaç arasındaki kümülatif fark.
- **Denetim görünümü:** Ara okumalar arasındaki kronolojik farklar.
- **Fatura kullanım miktarı:** Ara okumaların toplamı değil, baseline ile güncel sayaç arasındaki fark.

### 2.7 Fatura oluşturma idempotent olmalıdır

Fatura oluşturma ve okumaları `isBilled: true` yapma ayrı işlemler olarak kalırsa kısmi başarısızlık oluşabilir:

- Fatura oluşur, okumalar işaretlenmez.
- Okumalar işaretlenir, fatura oluşmaz.
- Aynı okumalar ikinci kez faturalanır.

Fatura akışı idempotency anahtarı ve işlem durumu kullanmalıdır:

```text
draft -> creating -> created -> readings_marked
```

---

## 3. Revize Domain Motoru

Yeni dosya:

```text
proservis-web/src/lib/cpcBillingEngine.ts
```

Motorun sorumlulukları:

```ts
resolveMeterBaseline(...)
resolveLiveContractPricing(...)
calculateCpcBillingItem(...)
detectCounterAnomaly(...)
```

### 3.1 Baseline önceliği

```text
1. Target tarihinden önceki en son isBilled=true okuma
2. Device.installCounters
3. Legacy device.meters
4. Kesin olarak 0
```

Baseline olamayacak değerler:

- Faturalandırılmamış ara okuma.
- `currentCounters`.
- Servis kaydı.
- Target reading'in kendisi.
- Target tarihinden sonraki faturalandırılmış okuma.

### 3.2 Fiyat çözümleme sonucu

`resolveLiveContractPricing` şu alanları çözmelidir:

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
    rentalFee,
    rentalCurrency,
    source: 'device' | 'contract' | 'default'
}
```

Sözleşme bilgisi ile cihaz ayarı çelişirse öncelik sırası açıkça tanımlanmalıdır. Önerilen sıra:

```text
Aktif sözleşme -> cihaz ayarı -> güvenli varsayılan
```

Sözleşme geçerlilik tarihleri de hesaba katılmalıdır.

### 3.3 Motor çıktısı

```ts
{
    baselineBw,
    baselineColor,
    currentBw,
    currentColor,
    bwUsage,
    colorUsage,
    billableBwUsage,
    billableColorUsage,
    bwTotal,
    colorTotal,
    rentalFee,
    currency,
    baselineSource,
    counterAnomaly,
    warnings
}
```

Farklı para birimleri varsa tek bir `grandTotal` üretilmemeli; hata veya ayrı para birimi toplamı dönülmelidir.

---

## 4. Uygulama Fazları

### Faz 1: Domain motoru ve tipler

- `cpcBillingEngine.ts` oluşturulması.
- `meterReadingBaseline.ts` içindeki eski mantığın motoru kullanması.
- `currentCounters` fallback'inin kaldırılması.
- `MeterReading.baselineSource` tipinin gerekirse `zero` desteğiyle güncellenmesi.
- Kota ve fiyat çözümleme tiplerinin tanımlanması.

### Faz 2: Tüm ekranların motoru kullanması

Aşağıdaki ekranlarda bağımsız baseline ve fiyat hesapları kaldırılmalıdır:

- [billing-page/page.tsx](proservis-web/src/app/dashboard/billing/billing-page/page.tsx)
- [DeviceGroupedBillingTable.tsx](proservis-web/src/components/billing/DeviceGroupedBillingTable.tsx)
- [billing/columns.tsx](proservis-web/src/app/dashboard/billing/columns.tsx)
- `invoices/page.tsx`
- `billing/history/page.tsx`
- `invoices/pending/page.tsx`

Özellikle `rawBaseBw > 0`, `latestReading` fallback'leri ve ekran bazlı `Math.max` hesapları tek motora taşınmalıdır.

### Faz 3: Faturalama akışı

1. Motor güncel fiyat ve sözleşme bilgisiyle taslak hesaplar.
2. Fatura satırlarına fiyat, kota, para birimi ve baseline snapshot yazılır.
3. Fatura oluşturma idempotency anahtarıyla korunur.
4. Başarılı fatura sonrası ilgili okumalar `billingId` ile işaretlenir.
5. Aynı okumaların ikinci kez faturalanması engellenir.
6. Fatura iptalinde okumalar kontrollü biçimde serbest bırakılır.

### Faz 4: Legacy veri uyumluluğu

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

### Fiyat ve kota

1. Güncel sözleşme fiyatı açık taslakta görünür.
2. Fatura oluşturulunca fiyat snapshot olarak saklanır.
3. Sonraki fiyat değişikliği oluşturulmuş faturayı değiştirmez.
4. Farklı para birimleri güvenli biçimde reddedilir veya ayrı toplanır.
5. Kota formülü için sınır senaryoları test edilir.

### Sayaç anomalileri

1. Sayaç düşüşü warning üretir.
2. Sayaç reseti sessizce sıfır çekim olarak kaybolmaz.
3. Cihaz değişikliği açıkça işaretlenir.

### Fatura işlemi

1. Aynı faturalama isteği duplicate fatura oluşturmaz.
2. Fatura ve `isBilled` güncellemesi arasında kısmi hata yönetilir.
3. Fatura iptali sonrası okumalar tekrar güvenli biçimde bekleyen duruma alınır.

### Kalite kontrolü

```bash
npm run lint
npm run build
```

Ayrıca `cpcBillingEngine` için gerçek bir unit test veya test runner kullanılmalıdır. Sadece build başarılı olması hesaplama doğruluğunu kanıtlamaz.

---

## 6. Nihai Karar

Planın yönü doğrudur ve `cpcBillingEngine` mevcut dağınık hesaplama kodlarını merkezileştirmek için uygun bir çözümdür. Ancak aşağıdaki dört madde eklenmeden uygulamaya başlanmamalıdır:

1. `currentCounters` fallback'i tamamen kaldırılmalı.
2. Taslak fiyat ile kesinleşmiş fatura fiyatı ayrılmalı.
3. Para birimi ve kota formülleri açıkça tanımlanmalı.
4. Fatura oluşturma ve sayaçları faturalandı olarak işaretleme idempotent hale getirilmeli.

Bu düzeltmeler yapıldığında 0 kurulum sayacı, ara okuma, sözleşme fiyatı değişikliği, sayaç reseti ve tekrar faturalandırma sorunları tek bir tutarlı hesaplama modeliyle yönetilebilir.
