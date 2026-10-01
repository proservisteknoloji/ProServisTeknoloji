# Toner ve Sarf Bilgisi Entegrasyonu
## V2 Planı Değerlendirmesi ve Nihai Uygulama Planı

**Tarih:** 07.09.2026  
**Kapsam:** E-posta, webhook ve agent kaynaklarından toner/sarf bilgisinin alınması; cihaz telemetrisi, müşteri eşleştirme ve cihazlar ekranında gösterim.

---

## 1. Genel Değerlendirme

V2 planının temel yönü doğrudur ve özellik teknik olarak uygulanabilir. Özellikle aşağıdaki kararlar onaylanmıştır:

- Kanonik cihaz alanı olarak `device.telemetry.tonerLevels` kullanılması.
- E-posta, agent ve manuel akışların ortak telemetri standardına alınması.
- Eski tarihli e-postanın güncel cihaz snapshot'ını ezmemesi.
- Sayısal toner yüzdesi ile nitel atık kutusu durumunun ayrıştırılması.
- Gerçek cihaz e-postalarıyla fixture tabanlı parser testleri yapılması.
- Renkli cihazlarda gelmeyen toner bilgisinin "Veri Yok" olarak gösterilmesi.
- Cihazlar ekranında mevcut Sayaçlar ve Servisler sekmelerinin yanına Sarf Bilgisi sekmesi eklenmesi.

Bununla birlikte V2 planındaki "kusursuz", "sıfır veri kaybı" ve "race condition korumalı" ifadeleri mevcut öneriyle tam olarak karşılanmamaktadır. Aşağıdaki düzeltmeler yapılmadan uygulamaya başlanmamalıdır.

---

## 2. Kritik Düzeltmeler

### 2.1 Timestamp kontrolü tek başına yeterli değildir

Şu yaklaşım atomik değildir:

```ts
const existing = await readDevice();
if (isNewer) {
    await updateDevice();
}
```

İki işlem aynı anda cihazı okuyup ikisi de yazabilir. Gerçek yarış koşulu koruması için cihaz snapshot güncellemesi Firestore `runTransaction` içinde yapılmalıdır.

Transaction içinde:

1. Cihaz belgesi okunur.
2. Mevcut `telemetry.lastCollectedAt` değeri kontrol edilir.
3. Gelen veri daha yeni veya eşitse snapshot güncellenir.
4. Eski veri cihaz snapshot'ını değiştirmez.

`device_telemetry` tarihçe kaydı her durumda korunmalıdır. Tarihçe yazımı başarısız olursa işlem yeniden çalıştırılabilir olmalıdır.

### 2.2 Toner ve sayaç aynı veri gibi güncellenmemelidir

Bir e-posta sayaç içerip toner içermeyebilir. Başka bir e-posta toner içerip sayaç içermeyebilir. Bu nedenle toner alanı gelen veri boş olduğunda silinmemelidir.

Doğru yaklaşım:

```ts
const mergedTonerLevels = {
    ...existingTonerLevels,
    ...incomingTonerLevels,
};
```

İleri aşamada aşağıdaki zaman alanları ayrı tutulabilir:

```ts
telemetry.lastCollectedAt
telemetry.lastCounterCollectedAt
telemetry.lastTonerCollectedAt
```

İlk sürümde yalnızca `lastCollectedAt` kullanılabilir; ancak alan bazında merge zorunludur.

### 2.3 Kaynak tipleri güncellenmelidir

Mevcut tipte `device.telemetry.source` için e-posta kaynağı bulunmamaktadır:

```ts
source?: 'agent' | 'manual' | 'imported';
```

Önerilen tip:

```ts
source?: 'agent' | 'email' | 'manual' | 'imported';
```

Ayrıca ayrıntılı kaynak değerleri ile snapshot kaynağı birbirine karıştırılmamalıdır:

- Snapshot: `agent | email | manual | imported`
- Tarihçe: `email_imap | email_webhook | email_manual_assign | agent`

### 2.4 Webhook akışı kapsama alınmalıdır

IMAP dışında aşağıdaki akış da e-posta parser'ı kullanmaktadır:

`proservis-web/src/app/api/webhooks/email-inbound/route.ts`

Sadece IMAP akışı güncellenirse sistemde farklı davranış oluşur. IMAP, webhook ve manuel bağlama aynı ortak telemetri yazma servisini kullanmalıdır.

### 2.5 Manuel bağlama akışı toner taşımamaktadır

`AssignMeterEmailDialog.tsx` aktif olarak kullanılmaktadır; ancak mevcut akış sayaçları taşırken `log.tonerLevels` alanını henüz cihaza yazmamaktadır.

Bu akışta yapılması gerekenler:

- `EmailCounterLog` içine `tonerLevels` eklenmesi.
- Yeni cihaz oluşturulurken toner snapshot'ının yazılması.
- Mevcut cihaz bağlanırken timestamp kontrolü uygulanması.
- Manuel telemetri kaydına toner seviyelerinin eklenmesi.
- E-posta logundaki toner bilgilerinin korunması.

### 2.6 Atık kutusu semantiği netleştirilmelidir

`waste: 10` değerinin doluluk mu, kalan kapasite mi olduğu belirsiz bırakılmamalıdır.

Kısa vadede mevcut yapı korunacaksa anlamı açıkça belgelenmelidir. Daha güvenli model:

```ts
waste?: {
    percent?: number;
    status?: 'ok' | 'near_full' | 'full' | 'unknown';
}
```

Geriye dönük uyumluluk zorunluysa eski sayısal format okunabilir; yeni kayıtlar için tek format tercih edilmelidir.

### 2.7 "Sıfır veri kaybı" yerine yeniden çalıştırılabilirlik hedeflenmelidir

E-posta logu, telemetri geçmişi, cihaz snapshot'ı ve sayaç kaydı ayrı yazıldığı için bir işlem kısmen başarılı olabilir.

Gerçekçi ve ölçülebilir hedefler:

- Ham e-posta logu her zaman korunur.
- Parser sonucu log içinde saklanır.
- Cihaza yazma başarısızlığı görünür hata olarak kaydedilir.
- Aynı e-posta tekrar işlendiğinde duplicate oluşmaz.
- Başarısız işlemler yeniden çalıştırılabilir olur.

---

## 3. Nihai Kanonik Veri Modeli

### 3.1 DeviceTonerLevels

```ts
export interface DeviceTonerLevels {
    black?: number;       // 0-100
    cyan?: number;        // 0-100
    magenta?: number;     // 0-100
    yellow?: number;      // 0-100
    waste?: number;       // Anlamı ayrıca belgelenmeli
    wasteStatus?: 'ok' | 'near_full' | 'full' | 'unknown';
    lowTonerAlert?: boolean;
}
```

### 3.2 Device telemetry snapshot

```ts
device.telemetry = {
    enabled: true,
    source: 'agent' | 'email' | 'manual' | 'imported',
    lastCollectedAt: Timestamp,
    lastSeenAt: Timestamp,
    tonerLevels: DeviceTonerLevels,
};
```

### 3.3 EmailCounterLog

```ts
tonerLevels?: DeviceTonerLevels | null;
```

Yukarıdaki alan gerçek kodda şu şekilde yazılmalıdır:

```ts
tonerLevels?: DeviceTonerLevels | null;
```

Ek olarak aşağıdaki alanlar değerlendirilebilir:

```ts
tonerParsed?: boolean;
tonerParseWarnings?: string[];
```

Yukarıdaki iki alanda da gerçek isimlendirme şu olmalıdır:

```ts
tonerParsed?: boolean;
tonerParseWarnings?: string[];
```

---

## 4. Ortak Telemetri Yazma Servisi

IMAP, webhook ve manuel dialog doğrudan cihaz güncellememelidir. Ortak bir servis oluşturulmalıdır:

```ts
recordEmailTelemetry({
    tenantId,
    customerId,
    deviceId,
    serialNumber,
    collectedAt,
    receivedAt,
    counters,
    tonerLevels,
    source,
    messageId,
});
```

Servisin sorumlulukları:

1. `device_telemetry` tarihçe kaydını oluşturmak.
2. Cihazı Firestore transaction içinde okumak.
3. Gelen verinin tarihini mevcut snapshot ile karşılaştırmak.
4. Eski veri ise cihaz snapshot'ını değiştirmemek.
5. Yeni veri ise sayaç ve toner alanlarını ayrı ayrı merge etmek.
6. `telemetry.source` ve `lastCollectedAt` alanlarını güncellemek.
7. `messageId` ile duplicate işlemi engellemek.
8. İşlem sonucunu `updated`, `historical_only` veya `duplicate` olarak raporlamak.

---

## 5. Parser Uygulama Planı

`parseEmailContent` şu sonucu üretmelidir:

```ts
{
    serialNumber,
    counters,
    tonerLevels
}
```

Parser aşamaları:

1. Subject, plain text, HTML ve desteklenen ekleri normalize et.
2. HTML tablo hücrelerinin etiket-değer ilişkisini mümkün olduğunca koru.
3. XML'i regex yerine XML parser ile oku.
4. CSV'yi gerçek CSV ayrıştırıcısı ile oku.
5. Siyah, cyan, magenta ve yellow sayısal değerlerini çıkar.
6. `%15` ve `15%` formatlarını destekle.
7. Türkçe, İngilizce ve cihaz çıktılarında kullanılan yaygın anahtarları destekle.
8. `Low Toner`, `Nearly Empty`, `Replace Soon` gibi nitel durumları çıkar.
9. Atık kutusunu sayısal veya nitel olarak çıkar.
10. Sayısal değerleri `0-100` aralığında doğrula.
11. Belirsiz değerleri tahmin etmek yerine `undefined` bırak.

İlk sürümde güvenilir şekilde desteklenecek ek türleri:

- `.txt`
- `.csv`
- `.html`
- `.htm`
- `.xml`

PDF ve XLSX desteği ayrı faza bırakılmalıdır. Binary dosyalar düz metin gibi taranmamalıdır.

---

## 6. Güncellenecek Dosya ve Akışlar

### Faz 1: Tipler ve parser

- `proservis-web/src/types/index.ts`
- `proservis-web/src/lib/emailParser.ts`
- `proservis-web/src/services/emailCounterService.ts`

### Faz 2: Ortak veri yazma

- Yeni ortak telemetri servis modülü
- `proservis-web/src/services/imapMailService.ts`
- `proservis-web/src/app/api/webhooks/email-inbound/route.ts`
- `proservis-web/src/components/billing/AssignMeterEmailDialog.tsx`

### Faz 3: Kullanıcı arayüzü

- `proservis-web/src/app/dashboard/customers/devices/page.tsx`
- `proservis-web/src/app/dashboard/customers/devices/columns.tsx`
- `proservis-web/src/app/dashboard/mail-counters/columns.tsx` veya aktif mail sayaç tablosunu oluşturan bileşen

---

## 7. UI / UX Kararı

Cihazlar ekranındaki alt panele üçüncü sekme eklenmelidir:

- Sayaç Geçmişi
- Servisler
- Sarf Bilgisi

### S/B cihaz

- K toner gösterilir.
- Atık kutusu gösterilir.
- C/M/Y gösterilmez.

### Renkli cihaz

- K, C, M, Y gösterilir.
- Gelmeyen renkler `Veri Yok` olarak gösterilir.
- Atık kutusu gösterilir.

Her toner göstergesinde:

- Yüzde veya durum metni.
- Renkli progress bar.
- Kritik / düşük / normal durumu.
- Son okuma zamanı.
- Veri kaynağı: E-posta, Agent veya Manuel.

Başlangıç eşikleri:

- `> 25`: Normal
- `16-25`: Azalıyor
- `<= 15`: Kritik

Ana cihaz tablosunda büyük ve yanıp sönen uyarı yerine kompakt bir sağlık indikatörü kullanılmalıdır. Tooltip içinde tüm toner değerleri gösterilebilir.

---

## 8. Test Planı

### Parser fixture testleri

- Kyocera plain text.
- Kyocera HTML tablo.
- HP metni.
- Canon veya Ricoh metni.
- Türkçe toner etiketleri.
- `%15` ve `15%` formatları.
- `Low Toner`, `Nearly Empty`, `Replace Soon` durumları.
- Atık kutusu sayısal ve nitel durumları.
- Desteklenen ek dosyalar.
- Toner satırlarının sayaç olarak yanlış okunmaması.

### Veri akışı testleri

- Eşleşen e-posta.
- Eşleşmeyen e-posta.
- Manuel dialog ile eşleştirme.
- Webhook e-postası.
- Aynı `messageId` ile tekrar işleme.
- Toner olmayan e-postanın mevcut toner bilgisini silmemesi.
- Sayaç olmayan toner e-postasının sayaçları silmemesi.

### Zaman ve yarış koşulu testleri

- Yeni telemetri varken eski e-postanın snapshot'ı ezmemesi.
- Aynı anda gelen iki telemetriden yalnızca yenisinin snapshot'a yazılması.
- Eşit timestamp durumunda deterministik davranış.
- Tarihçe kaydının snapshot güncellenmese bile korunması.

### UI testleri

- S/B cihaz görünümü.
- Renkli cihaz görünümü.
- Eksik renk bilgisi.
- Atık kutusu durumları.
- Eski okuma uyarısı.
- Kritik toner badge'i.
- Mobil ve dar tablo görünümü.

### Derleme ve kalite kontrolü

```bash
npm run lint
npm run build
```

Ayrıca parser için gerçek bir test script'i veya test runner yapılandırılmalı; yalnızca build başarılı olması parser davranışını doğrulamaz.

---

## 9. Nihai Karar

V2 planı temel alınabilir; ancak aşağıdaki dört şart zorunludur:

1. Timestamp kontrolü Firestore transaction ile atomik hale getirilmeli.
2. IMAP, webhook ve manuel akış ortak telemetri servisine bağlanmalı.
3. Toner ve sayaç snapshot'ları alan bazında merge edilmeli.
4. Kaynak tipleri ve atık kutusu semantiği kesinleştirilmeli.

Bu düzeltmeler tamamlandığında plan üretim için yeterince sağlamdır. Özellik uygulanabilir, mevcut agent telemetri yapısıyla uyumludur ve cihaz müşteriye bağlandığında toner bilgisinin Cihazlar ekranında güvenilir şekilde gösterilmesini sağlar.
