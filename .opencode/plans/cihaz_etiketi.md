# Cihaz Etiketi QR ve Cihaz Liste Görünümü Planı

## Amaç
- Cihazlara firma içi kullanım için QR etiket basmak.
- QR etiket müşteri portalına veya müşteri işlem akışına bağlı olmayacak.
- Müşteri portalında, müşterinin listelenen cihazlarında cihaz etiket bilgisi görünür olacak.
- Portal cihaz etiketi; müşterinin cihazı ayırt etmesi için kullanılan `device.label` alanıdır. Örnek: Sekreter, Laboratuar, Muhasebe.
- Müşteri detay ekranındaki cihaz satırlarında garanti ve sözleşme bilgileri daha doğru konumlandırılacak.
- Fiziksel etiket uzun süre cihaz üzerinde kalacağı için yalnızca kalıcı bilgiler basılacak.

## Kapsam Dışı
- QR okutunca müşteri portalı açılması.
- QR ile müşterinin servis/talep oluşturması.
- Portalda QR kod okutma veya etiket üzerinden işlem başlatma.
- Fiziksel etikette cihaz durumu gibi değişken bilgilerin gösterilmesi.
- Barkod basımı. Bu plan QR etikete odaklanır.

## Kararlar
- **Etiket kullanımı:** Firma iç operasyonu.
- **QR içeriği:** Cihazı iç sistemde tanımlayacak kalıcı değer.
- **Önerilen QR değeri:** `deviceIdNumber`.
- **Alternatif QR değeri:** İç dashboard cihaz linki, örn. `/dashboard/customers?deviceId={device.id}`.
- **Etiket formatı:** Termal yazıcı, browser print dialog ve `@page` CSS.
- **Etiket boyutu:** 100x70mm.
- **Fiziksel etiket bilgileri:**
  - Firma adı
  - Cihaz ID no: `deviceIdNumber`
  - Marka / Model
  - Seri no
  - QR kod
- **Portal görünürlüğü:** Müşteri portalında cihaz listesinde cihaz etiket bilgisi (`device.label`) gösterilecek.
- **Dashboard cihaz satırı:** Garanti durumu model yanındaki badge alanına, sözleşme bilgisi ise model altındaki bilgi alanına taşınacak.

## QR İçeriği Önerisi

### Tercih Edilen Basit Model
QR sadece `deviceIdNumber` değerini taşır.

Örnek:
```text
DEV-123456-789
```

Artıları:
- Kalıcıdır.
- Müşteri erişimiyle bağlantılı değildir.
- Ortam değişikliklerinden etkilenmez.
- Yazıcıdan basılan etiket uzun yıllar geçerli kalır.

Eksileri:
- QR okutulunca otomatik web sayfası açılmaz; okutan personel değeri sistemde arar veya ileride iç mobil/teknisyen uygulaması bu değeri yorumlar.

### Alternatif İç Link Modeli
QR iç dashboard linkini taşır.

Örnek:
```text
https://app-domain/dashboard/customers?deviceId=DEVICE_DOC_ID
```

Artıları:
- Personel oturum açmışsa doğrudan cihaz kaydına gidebilir.

Eksileri:
- Domain değişirse fiziksel etiket eskir.
- Personel oturum ve yetki kontrolleri gerekir.
- Müşteri yanlışlıkla okutsa bile dashboard login ekranı görebilir.

Bu nedenle ilk sürüm için QR değerinin `deviceIdNumber` olması önerilir.

## Uygulama Adımları

### 1. Bağımlılıklar
QR üretimi için:
```bash
npm install qrcode
npm install --save-dev @types/qrcode
```

`jsbarcode` gerekli değil; barkod artık kapsam dışı.

### 2. DeviceLabelDialog.tsx (Yeni)
**Dosya:** `proservis-web/src/app/dashboard/customers/devices/DeviceLabelDialog.tsx`

Görevler:
- Props:
  - `devices: DeviceRow[]`
  - `onClose: () => void`
- Her cihaz için 100x70mm etiket önizlemesi üret.
- QR kodu `deviceIdNumber` üzerinden üret.
- `deviceIdNumber` yoksa etiketi basılamaz olarak göster veya yazdırmadan önce uyarı ver.
- Etiket üzerinde yalnızca şu alanlar yer alsın:
  - Firma adı
  - Cihaz ID no
  - Marka / Model
  - Seri no
  - QR kod
- `window.print()` ile yazdır.
- Print CSS:
```css
@page {
  size: 100mm 70mm;
  margin: 2mm;
}
```

Tasarım notları:
- QR kod en az 28-32mm genişlikte olmalı.
- Cihaz ID no büyük ve okunabilir olmalı.
- Marka/model ve seri no kısa satırlara sığmalı; taşarsa kırpılmalı.
- Durum, müşteri adı, portal cihaz etiketi, servis geçmişi ve sayaç bilgisi fiziksel etikete basılmamalı.
- Firma adı tenant/firma ayarlarından alınmalı. Mevcut uygulamada firma adı için kullanılan merkezi ayar/hook varsa aynı kaynak kullanılmalı.

### 3. Cihazlar Sayfası - Tek Cihaz Etiketi
**Dosya:** `proservis-web/src/app/dashboard/customers/devices/columns.tsx`

Görevler:
- Aksiyonlara `Printer` ikonu ekle.
- `getColumns` seçeneklerine `onPrintLabel: (device: DeviceRow) => void` ekle.
- Yazdırma ikonu tek cihaz için `DeviceLabelDialog` açmalı.

### 4. Cihazlar Sayfası - Toplu Etiket Yazdırma
**Dosya:** `proservis-web/src/app/dashboard/customers/devices/page.tsx`

Görevler:
- Cihaz tablosunda row selection aktif edilecek.
- Üst aksiyonlara `Seçililere Etiket Yazdır (X)` butonu eklenecek.
- Seçili cihazlar `DeviceLabelDialog` içine gönderilecek.
- Tek cihaz yazdırma için `columns.tsx` içinden gelen callback state'i kullanılacak.

Not:
- `deviceIdNumber` olmayan cihazlar için toplu yazdırmada uyarı gösterilmeli.
- İdeal davranış: yazdırmadan önce eksik ID'li cihazları listeleyip yazdırma dışında bırakmak.

### 5. Müşteri Portalında Cihaz Etiketi Görünürlüğü
**Mevcut dosya:** `proservis-web/src/app/api/portal/devices/route.ts`

Görev:
- Portal cihaz API cevabına `label` alanı eklenecek.

Beklenen cevap alanı:
```ts
{
  id: string;
  label?: string;
  brand: string;
  model: string;
  serialNumber: string;
  status: string;
  isColor: boolean;
  telemetry: DeviceTelemetrySnapshot | null;
}
```

**Portal cihaz listesi:** `proservis-web/src/app/portal/page.tsx`

Görev:
- Müşteri portalındaki cihaz kartı/listesinde `Etiket` veya `Cihaz etiketi` bilgisi gösterilecek.
- Örnek değerler: Sekreter, Laboratuar, Muhasebe.
- Bu alan müşterinin aynı modelden birden fazla cihazı ayırt etmesi için kullanılacak.
- Alan boşsa `Etiket yok` gibi sade bir fallback gösterilecek veya alan gizlenecek.
- Bu alan sadece bilgi amaçlı olacak; tıklanabilir QR/etiket işlemine dönüşmeyecek.

### 6. Müşteri Detay Sayfası - Garanti ve Sözleşme Bilgisi Yerleşimi
**Mevcut dosya:** `proservis-web/src/app/dashboard/customers/page.tsx`

Ekrandaki işaretli alan müşteri detay ekranındaki cihaz tablosunun `Marka / Model` hücresidir.

Mevcut durum:
- Model satırında cihaz tipi badge'i ve `Renkli / S/B` badge'i yer alıyor.
- Model altında `Etiket: ...` bilgisi yer alıyor.
- Onun altında `Garantili / Ücretli` badge'i yer alıyor.
- `Anlaşma / Fiyat` kolonunda CPC, kiralama, bakım, fiyat ve garanti bitiş bilgileri karışık biçimde gösteriliyor.

Yeni hedef:
- `Garantili / Garanti Bitmiş` bilgisi model satırındaki `Renkli / S/B` badge'inin yerine taşınacak.
- Model altındaki eski `Garantili / Ücretli` badge alanında cihazın sözleşme bilgisi yazacak.
- `Renkli / S/B` bilgisi bu satırdan kaldırılacak ya da ihtiyaç varsa daha az öncelikli başka bir alana taşınacak.
- `Ücretli` metni garanti bilgisi olarak kullanılmayacak; garanti bitmiş cihaz için metin `Garanti Bitmiş` olacak.

Model satırı yeni görünüm:
```text
Konica Minolta C224  [MFP A3 Renkli] [Garantili]
Etiket: Muayene
[Müşteri/Cihaz sözleşmesindeki gerçek sözleşme türü]
```

Garanti bitmiş örnek:
```text
Develop INEO 258+  [MFP A3 Renkli] [Garanti Bitmiş]
Etiket: Laboratuar
[Sözleşmede kayıtlı tür/ad]
```

Sözleşme bilgi etiketi kuralları:
- Sabit sözleşme tipi listesi kullanılmayacak.
- `C.C Kopyabaşı`, `P.H Parça Hariç`, `Kiralama`, `Bakım Anlaşmalı` gibi metinler kod içinde hard-code edilmeyecek.
- Her firmanın kendi tanımladığı sözleşme türü/adı ne ise o gösterilecek.
- Öncelik cihazın bağlı olduğu aktif sözleşme kaydı olmalı:
  1. `CustomerContract.deviceRefs` içinde ilgili `device.id` geçen aktif sözleşme bulunur.
  2. Bulunan sözleşmede önce `contractTypeName`, yoksa `title`, yoksa `templateName` gösterilir.
  3. Cihaz özelinde sözleşme bulunamazsa müşteri üzerindeki `selectedCustomer.contractTypeName` gösterilir.
  4. O da yoksa alan gizlenir veya `Sözleşme yok` gibi düşük öncelikli sade bir fallback gösterilir.
- Böylece örneğin firma sözleşme türünü `C.C Kopyabaşı`, `P.H Parça Hariç`, `Full Servis`, `Sadece İşçilik`, `Toner Dahil` gibi ne adlandırdıysa ekranda aynısı görünür.

Veri erişimi notu:
- Müşteri detay sayfası cihaz satırlarında gerçek sözleşme adını göstermek için aktif müşteri sözleşmeleri yüklenmeli.
- Mevcut servis olarak `ContractService.getContracts(tenantId, selectedCustomer.id)` kullanılabilir.
- Sözleşmeler `status === "active"` olacak şekilde filtrelenmeli.
- Cihaz eşleşmesi `CustomerContract.deviceRefs[].deviceId` üzerinden yapılmalı.
- Müşteri genel sözleşme adı (`Customer.contractTypeName`) sadece cihaz özel sözleşmesi bulunamadığında fallback olmalı.

Önerilen yardımcı fonksiyonlar:
- `getWarrantyMeta(device)`:
  - `Garantili`
  - `Garanti Bitmiş`
  - `Garanti Bilgisi Yok`
- `getDeviceContractLabel(device, activeContracts, selectedCustomer)`:
  - İlgili aktif sözleşmedeki `contractTypeName`
  - Yoksa aktif sözleşmedeki `title`
  - Yoksa aktif sözleşmedeki `templateName`
  - Yoksa müşterinin `contractTypeName`
  - Yoksa boş değer

Renk önerileri:
- `Garantili`: yeşil ton
- `Garanti Bitmiş`: amber/kırmızı ton
- `Garanti Bilgisi Yok`: gri ton
- Sözleşme adı: nötr/mavi ton
- Sözleşme yok: gri ton veya hiç gösterme

`Anlaşma / Fiyat` kolonunda:
- Fiyat ve tarih detayları kalabilir.
- Garanti bitiş satırı burada tekrar gösterilecekse daha düşük öncelikli küçük metin olabilir; ana garanti durumu artık model satırındaki badge'de olmalı.
- Sözleşme tipi burada tekrarlanacaksa görsel karmaşa yaratmayacak şekilde sade tutulmalı.

### 7. Yetki ve Güvenlik
- QR müşteri portalına bağlı olmadığı için yeni portal cihaz detay sayfası açılmayacak.
- Yeni `portal/device/[deviceIdNumber]` route'u oluşturulmayacak.
- Yeni `api/portal/device-by-number` endpoint'i oluşturulmayacak.
- Yeni `api/portal/device-history` endpoint'i oluşturulmayacak.
- Dashboard tarafında etiket basımı zaten personel oturumu ve tenant bağlamı altında çalışmalı.

### 8. Veri Kalitesi
- `deviceIdNumber` fiziksel etikette ana bilgi olduğu için boş olmamalı.
- Cihaz oluşturma/güncelleme akışında `deviceIdNumber` üretimi ve benzersizliği korunmalı.
- Etiket basma ekranı eksik `deviceIdNumber` tespit ederse kullanıcıya açık uyarı vermeli.
- `device.label` müşteri portalı için anlamlı olmalı; aynı modelden çok cihazı olan müşterilerde özellikle doldurulmalı.
- Sözleşme etiketi yalnızca gerçek sözleşme verisinden beslenmeli; sözleşme adı/türü kod içinde sabitlenmemeli.

## Kabul Kriterleri
- Cihazlar sayfasında tek cihaz için etiket yazdırılabilir.
- Cihazlar sayfasında seçili cihazlar için toplu etiket yazdırılabilir.
- Fiziksel etikette sadece Firma adı, Cihaz ID no, Marka / Model, Seri no ve QR kod görünür.
- QR kod `deviceIdNumber` değerini taşır.
- Fiziksel etikette cihaz durumu gösterilmez.
- Müşteri portalındaki cihaz listesinde cihaz etiket bilgisi (`device.label`) görünür.
- Müşteri portalında QR okutma, QR işlem başlatma veya QR detay sayfası yoktur.
- Müşteri detay ekranında model yanındaki `Renkli / S/B` badge'i yerine garanti durumu görünür.
- Garanti durumu `Garantili`, `Garanti Bitmiş` veya gerekiyorsa `Garanti Bilgisi Yok` olarak gösterilir.
- Müşteri detay ekranında eski garanti/ücretli badge alanında cihaz sözleşme bilgisi görünür.
- Sözleşme bilgisi sabit bir listeye göre değil, müşteri/cihaz sözleşmesinde kayıtlı gerçek sözleşme adı/türüne göre gösterilir.
- Cihaz özelinde aktif sözleşme varsa müşteri genel sözleşmesinden önce cihazın bağlı olduğu sözleşme gösterilir.

## Test Notları
- Etiket önizlemesi 100x70mm ölçüye sığmalı.
- Tek etiket yazdırma denenmeli.
- Birden fazla cihaz seçilerek toplu yazdırma denenmeli.
- `deviceIdNumber` eksik cihaz davranışı kontrol edilmeli.
- Portal cihaz API cevabında `label` geldiği doğrulanmalı.
- Portal cihaz listesinde cihaz etiket bilgisi görünürlüğü kontrol edilmeli.
- Müşteri detay sayfasında garantili cihazın model yanında `Garantili` göründüğü kontrol edilmeli.
- Garanti süresi bitmiş cihazın model yanında `Garanti Bitmiş` göründüğü kontrol edilmeli.
- Cihaz aktif bir sözleşmeye bağlıysa sözleşme badge'inde o sözleşmenin `contractTypeName` değerinin göründüğü kontrol edilmeli.
- Cihaz özel sözleşmesi yoksa müşteri üzerindeki `contractTypeName` fallback'inin göründüğü kontrol edilmeli.
- Sözleşme adı firma özelinde değiştirildiğinde ekranda yeni adın hard-code listeye takılmadan göründüğü kontrol edilmeli.
