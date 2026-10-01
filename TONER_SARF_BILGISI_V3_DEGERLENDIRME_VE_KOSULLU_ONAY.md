# Toner ve Sarf Bilgisi Entegrasyonu
## V3 Planı Teknik Değerlendirmesi ve Koşullu Onay

**Tarih:** 07.09.2026  
**Kapsam:** IMAP, webhook ve manuel e-posta eşleştirme akışlarından toner/sarf telemetrisi alınması; cihaz snapshot'ı, telemetri geçmişi ve kullanıcı arayüzü.

---

## 1. Genel Görüş

V3 planı önceki sürümlere göre belirgin biçimde olgunlaşmıştır. Kanonik veri modeli, ortak telemetri yazma servisi, Firestore transaction, alan bazlı merge ve fixture tabanlı test yaklaşımı doğrudur.

Planın mimari yönünü onaylıyorum. Ancak doğrudan "kusursuz" veya "sıfır yarış koşulu" olarak adlandırılması teknik olarak doğru değildir. Uygulamaya başlamadan önce aşağıdaki noktalar netleştirilmelidir.

---

## 2. Doğru Kararlar

- Kanonik cihaz alanı olarak `device.telemetry.tonerLevels` kullanılması.
- IMAP, webhook ve manuel bağlamanın ortak yazma servisine alınması.
- Cihaz snapshot güncellemesinde Firestore `runTransaction` kullanılması.
- Sayaç ve toner alanlarının field-level merge edilmesi.
- Eski verinin canlı snapshot'ı ezmemesi.
- `device_telemetry` geçmişinin korunması.
- Gerçek cihaz e-postalarıyla fixture tabanlı parser testi yapılması.
- Renkli cihazlarda gelmeyen toner bilgilerinin `Veri Yok` olarak gösterilmesi.
- Cihazlar ekranında Sarf Bilgisi sekmesi eklenmesi.

---

## 3. Uygulama Öncesi Zorunlu Düzeltmeler

### 3.1 Idempotency transaction ile birlikte tasarlanmalıdır

`runTransaction` tek başına duplicate geçmiş kaydını engellemez. Otomatik Firestore document ID kullanılır ve önce sorgu sonra yazma yapılırsa aynı e-posta iki kez işlenebilir.

Deterministik kayıt kimliği kullanılmalıdır:

```ts
const eventId = messageId || generatedIdempotencyKey;
const telemetryRef = db.doc(`.../device_telemetry/${eventId}`);
```

Transaction içinde:

1. Cihaz belgesi okunur.
2. Telemetri belge kimliği kontrol edilir.
3. Daha önce varsa `duplicate` sonucu dönülür.
4. Yoksa tarihçe kaydı oluşturulur.
5. Gerekli durumda cihaz snapshot'ı güncellenir.

Manuel işlemlerde `messageId` bulunmayabilir. Bu durumda tenant, cihaz, kaynak ve olay zamanı üzerinden idempotency anahtarı üretilmelidir.

Fonksiyonun sonucu da planla uyumlu olmalıdır:

```ts
status: 'updated' | 'historical_only' | 'duplicate' | 'error'
```

### 3.2 Timestamp kontrolü alan bazında düşünülmelidir

V3 alan bazında merge öneriyor; ancak tek bir `lastCollectedAt` alanı sayaç ve toner güncelliğini tamamen temsil etmeyebilir.

Örneğin:

- Bir e-posta yeni toner, eski sayaç gönderebilir.
- Başka bir e-posta eski toner, yeni sayaç gönderebilir.

İdeal model:

```ts
lastCollectedAt
lastCounterCollectedAt
lastTonerCollectedAt
```

İlk sürümde yalnızca `lastCollectedAt` kullanılacaksa bile servis şu kurala uymalıdır:

- Gelen event içinde toner yoksa toner zamanı ve toner snapshot'ı değiştirilmez.
- Gelen event içinde sayaç yoksa sayaç zamanı ve sayaç snapshot'ı değiştirilmez.

### 3.3 Server/client Firestore sınırı netleştirilmelidir

IMAP ve webhook akışları Admin SDK ile çalışırken `AssignMeterEmailDialog.tsx` client component ve Firebase client SDK kullanmaktadır.

Admin SDK kullanan ortak bir modül doğrudan client dialog'dan import edilemez. İki geçerli çözüm vardır:

1. Saf merge/karar fonksiyonları ortak tutulur; server ve client için ayrı Firestore adaptörleri yazılır.
2. Manuel dialog bir API route çağırır; transaction ve tüm veri yazma işlemi server tarafında yapılır.

Tercih edilen çözüm ikinci seçenektir. Böylece yetkilendirme, transaction, idempotency ve veri bütünlüğü tek server tarafında toplanır.

### 3.4 Transaction retry sırasında duplicate tarihçe kaydı oluşmamalıdır

`device_telemetry` tarihçe kaydı transaction içinde tutulacaksa document ID deterministik olmalıdır. Transaction retry olduğunda otomatik ID ile yeni bir tarihçe kaydı oluşturulmamalıdır.

Tarihçe kaydı snapshot güncellenmese bile korunmalıdır; ancak aynı olay için yalnızca bir tarihçe kaydı bulunmalıdır.

### 3.5 E-posta kaydı `lastSeenAt` olarak kullanılmamalıdır

E-posta alınması cihazın o anda çevrimiçi olduğunu kanıtlamaz.

E-posta akışında:

- `lastCollectedAt` güncellenebilir.
- `lastTonerCollectedAt` güncellenebilir.
- `lastSeenAt` yalnızca agent veya gerçek cihaz erişimi ile güncellenmelidir.

Aksi durumda çevrimdışı bir cihaz, e-posta gönderdiği için yanlışlıkla çevrimiçi görünebilir.

### 3.6 Billing işlemleri telemetri işleminden ayrılmalıdır

Mevcut projede sayaç baseline ve faturalama kuralları hassastır. Ortak telemetri servisi:

- Operasyonel cihaz sayaç snapshot'ını güncelleyebilir.
- `device_telemetry` geçmişi oluşturabilir.
- Ancak billing baseline alanlarını değiştirmemelidir.

`meter_readings` kaydı ayrı ve idempotent bir işlem olmalıdır. İlk faturalamada kurulum sayacı, sonraki faturalamalarda son onaylı sayaç kullanılmaya devam etmelidir.

### 3.7 UI dosya yolları uygulama öncesi doğrulanmalıdır

V3 planında `mail-counters/columns.tsx` dosyası belirtilmiştir. Gerçek projede mail sayaç tablosunu oluşturan bileşen bu dosyadan farklı olabilir.

Uygulama başlamadan önce gerçek tablo bileşeni kesinleştirilmeli ve plan dosya yolu buna göre güncellenmelidir.

---

## 4. Parser İçin Ek Kabul Kriterleri

"İki aşamalı tokenizer" yaklaşımı doğru bir yönlendirmedir; ancak aşağıdaki teknik kriterler açıkça uygulanmalıdır:

- XML gerçek XML parser ile okunmalıdır.
- CSV gerçek CSV parser ile okunmalıdır.
- HTML tablo hücrelerinin etiket-değer ilişkisi korunmalıdır.
- PDF ve XLSX binary içerikleri düz metin gibi taranmamalıdır.
- Ek dosyalarda encoding ve boyut sınırı uygulanmalıdır.
- Sayaç değerleri toner yüzdeleriyle karıştırılmamalıdır.
- Çelişkili toner değerlerinde tahmin yapılmamalıdır.
- Belirsiz değerler `undefined` bırakılmalı ve gerekirse parse uyarısı saklanmalıdır.

---

## 5. Önerilen Ortak Servis Sözleşmesi

```ts
export async function recordDeviceTelemetry(params: {
    tenantId: string;
    customerId: string;
    deviceId: string;
    serialNumber: string;
    eventTimestamp: Timestamp;
    receivedAt: Timestamp;
    counters?: {
        bw?: number;
        color?: number;
        total?: number;
    } | null;
    tonerLevels?: DeviceTonerLevels | null;
    source: 'email_imap' | 'email_webhook' | 'email_manual_assign';
    messageId?: string | null;
}): Promise<{
    status: 'updated' | 'historical_only' | 'duplicate' | 'error';
    message?: string;
}>;
```

Bu servis:

1. Idempotency kontrolü yapmalıdır.
2. Telemetri geçmişini deterministik ID ile kaydetmelidir.
3. Cihazı transaction içinde okumalıdır.
4. Olay tarihini mevcut alanlarla karşılaştırmalıdır.
5. Sayaç ve toner snapshot'larını ayrı ayrı merge etmelidir.
6. Eski olayı yalnızca tarihçeye yazmalıdır.
7. Billing baseline alanlarını değiştirmemelidir.
8. İşlem sonucunu çağıran akışa açıkça bildirmelidir.

---

## 6. Son Test Kapsamı

### Parser

- Kyocera plain text.
- Kyocera HTML tablo.
- HP ve generic metin.
- Türkçe, İngilizce ve yaygın üretici etiketleri.
- `%15` ve `15%` formatları.
- `Low Toner`, `Nearly Empty`, `Replace Soon` durumları.
- Atık kutusu sayısal ve nitel durumları.
- Sayaç ve toner regex çakışması.
- Desteklenen ek dosya türleri.

### Veri akışı

- Eşleşen e-posta.
- Eşleşmeyen e-posta.
- Manuel eşleştirme.
- Webhook e-postası.
- Aynı `messageId` ile tekrar işleme.
- Aynı anda gelen iki olay.
- Eski olayın snapshot'ı ezmemesi.
- Tonersiz olayın mevcut toneri silmemesi.
- Sayaçsız olayın mevcut sayaçları silmemesi.
- Transaction retry sırasında duplicate oluşmaması.

### UI

- S/B cihaz.
- Renkli cihaz.
- Eksik renk bilgisi.
- Atık kutusu durumları.
- Eski okuma uyarısı.
- Kritik toner indikatörü.
- Mobil ve dar tablo görünümü.

### Komutlar

```bash
npm run lint
npm run build
```

Build başarılı olsa bile parser davranışını doğrulamaz. Bu nedenle parser için gerçek bir test script'i veya test runner yapılandırılmalıdır.

---

## 7. Nihai Karar

V3 planı mimari olarak doğrudur ve koşullu olarak onaylanabilir.

Uygulamaya başlamadan önce aşağıdaki maddeler plana eklenmelidir:

1. Deterministik `messageId` veya idempotency key kullanılmalı.
2. Sonuç tipine `duplicate` eklenmeli.
3. Server/client Firestore sınırı açıkça tasarlanmalı.
4. Sayaç ve toner için ayrı güncellik alanları değerlendirilmeli.
5. E-posta akışında `lastSeenAt` güncellenmemeli.
6. Billing `meter_readings` işlemi telemetri snapshot'ından ayrılmalı.
7. Transaction retry sırasında duplicate tarihçe kaydı oluşması engellenmeli.
8. Gerçek UI bileşen dosya yolları uygulama öncesi doğrulanmalı.

Bu düzeltmeler yapıldıktan sonra V3, üretim uygulaması için yeterince sağlam bir temel oluşturur.
