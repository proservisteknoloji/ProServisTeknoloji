# İnceleme Notları — PROSERVIS_YENI_NESIL_MUHASEBE_VE_FINANS_MIMARI_PLANI.md (v2.0)

> **Tarih:** 4 Ekim 2026  
> **İnceleme yöntemi:** Plandaki her iddia `proservis-web` kaynak koduna karşı doğrulandı (types, services, api route'ları, mevcut GİB akışı).  
> **Genel karar:** ❌ **Bu haliyle uygulamaya alınamaz.** Plan, incelenen repoların mimarisini ProServis'in kendi mimarisini doğrulamadan taşıyor. 7 engelleyici (blocker), 10 büyük (major) bulgu var.

---

## A. ENGELLEYİCİ BULGULAR (Blocker)

### A1. Yanlış veri katmanı varsayımı: Prisma/PostgreSQL desenleri Firestore'a uygulanmış
- Plan; `tenantScoped()`, `updateMany + count === 1`, `Decimal(19,4)`, `Serializable` transaction gibi **FinansMax (Prisma/PostgreSQL)** desenlerini zorunlu kural olarak yazıyor (Bölüm 4.2, 9. kontrol listesi).
- **Gerçek:** ProServis Firestore kullanıyor. İzolasyon doküman yolu ile sağlanıyor (`tenants/${tenantId}/...` — bkz. `contractService.ts` L31-32). Firestore'da `Decimal` tipi yok, `updateMany` yok.
- **Etki:** Peer-review kontrol listesindeki "Kuruş Bütünlüğü" ve "Multi-Tenant" maddeleri bu sistemde doğrulanamaz.
- **Düzeltme:** Para alanları **tam sayı kuruş** (minor units, `amountMinor: number`) olarak tutulmalı. Bu kural yalnız yeni koleksiyonlara uygulanmalı, mevcut `Invoice.totalAmount` için ayrı bir migrasyon kararı alınmalı. İzolasyon için mevcut yol tabanlı desen + Firestore Security Rules kullanılmalı.

### A2. Güvenlik: Entegratör servisi istemci tarafına konumlandırılmış
- Plan `eInvoiceService.ts`, `qnbIntegrator.ts` ve `uyumsoftIntegrator.ts` dosyalarını `src/services/` altına koyuyor.
- **Gerçek:** `src/services/*` modülleri istemci Firebase SDK'sı ile tarayıcıda çalışıyor (`contractService.ts` L1: `import { db } from '@/lib/firebase'`). Mevcut GİB akışı bu yüzden server tarafında: `api/gib/create-draft/route.ts` + `firebaseAdmin`.
- **Etki:** Entegratör kullanıcı adı/şifresi ve SOAP çağrıları tarayıcıya sızar.
- **Düzeltme:** Tüm e-belge mantığı `src/lib/server/eDocument/**` (server-only) + `src/app/api/e-document/**` route'larında olmalı. Kimlik bilgileri istemcinin okuyabildiği `settings` dokümanında **tutulmamalı**. Bu kural mevcut `GibSettings.password` için de geçerli; ayrıca ele alınmalı.

### A3. Logo bağlantı topolojisi çalışmaz (bulut → ofis LAN push)
- Plan, ProServis'in (Firebase Hosting/bulut) ofisteki Logo sunucusuna **webhook push** yapacağını varsayıyor.
- **Gerçek:** Logo SQL ve Logo Objects çoğunlukla NAT arkasındaki yerel ağda çalışır, buluttan erişilemez. ProServis'in kendi agent mimarisi zaten **pull/pairing** modelinde (`api/agent/pair`, `register`, `status`, `telemetry`).
- Ayrıca kaynak alınan `muhasebe-app/src/lib/webhooks.ts` fire-and-forget çalışıyor: kalıcı kuyruk yok, retry yok. Plan "kuyrukta bekletilir" diyor ama kuyruğu tasarlamıyor.
- **Düzeltme:** **Transactional Outbox** deseni kullanılmalı:
  - `tenants/{t}/integration_outbox/{eventId}` koleksiyonu: `eventType`, `payload`, `idempotencyKey`, `status`, `attempts`, `lastError`, `ackedAt` alanlarıyla.
  - Logo Connector, agent'a benzer şekilde eşleştirilir (pairing token).
  - Connector `GET /api/integrations/outbox?since=` ile veriyi çeker, `POST .../ack` ile onaylar.
  - Webhook (push) yalnızca bulutta çalışan alıcılar (Paraşüt vb.) için opsiyonel kalır.

### A4. Mevcut alanları kıran şema değişikliği
- Plan `gibEttn → gibUuid`, `gibInvoiceNo → gibDocumentNumber` yeniden adlandırması öneriyor ve `gibStatus` değer kümesini değiştiriyor.
- **Gerçek tüketiciler:**
  - `dashboard/invoices/page.tsx` L2592–2621
  - `api/gib/view-html`, `api/gib/verify-sms`, `api/gib/create-draft`
  - `api/portal/invoices/[id]/html` (`gibHtml`)
- **Etki:** Daha önce imzalanmış portal faturaları ve müşteri portalının fatura görüntüleme ekranı bozulur.
- **Düzeltme:** Mevcut alanlar korunmalı, yeni alanlar eklenmeli (ör. `eDoc.provider: 'gib_portal' | 'qnb' | 'uyumsoft'`, `eDoc.uuid`, `eDoc.number`, `eDoc.status`). Okuma katmanında eski alanlara geri dönüş (fallback) olmalı. Portal görüntüleme ekranı sağlayıcıdan bağımsız hale getirilmeli (PDF/HTML).

### A5. Fatura kalem modeli UBL için yetersiz — plan bunu görmüyor
- **Gerçek:** `InvoiceItem` = `{ description, quantity, unitPrice, total, type, inventoryMode }`. Satır bazında KDV oranı, birim kodu, iskonto, tevkifat ve istisna kodu **yok**. KDV yalnızca fatura seviyesinde tek bir `taxAmount` olarak tutuluyor. Mevcut `gibService` oranı `taxAmount/subtotal` oranından tahmin ediyor.
- Plandaki XML şablonu tek bir `TaxSubtotal` içeriyor. Karışık oranlı (%1/%10/%20), istisnalı ya da tevkifatlı faturalarda bu şablon **GİB tarafından reddedilir**.
- **Düzeltme (Faz 0, ön koşul):** `InvoiceItem` şu alanlarla genişletilmeli: `vatRate`, `unitCode` (GİB birim kodu), `discountAmount`, `withholdingCode/Rate`, `exemptionCode`. Bu alanlar fatura oluşturan tüm akışlarda doldurulmalı (CPC, servis, toner, bakım, manuel).

### A6. UBL-TR şablonu eksik ve dövizli faturalar ele alınmamış
Şablonda bulunmayan zorunlu ya da pratikte zorunlu öğeler:
- `cac:Signature`
- `cbc:LineCountNumeric`
- Satır bazında `cac:TaxTotal`
- Alıcı `PartyTaxScheme`
- e-Arşiv için `AdditionalDocumentReference` (gönderim şekli: ELEKTRONIK/KAGIT)
- İrsaliyeli faturada `DespatchDocumentReference`

Dövizle ilgili eksikler:
- ProServis **USD/EUR fatura kesiyor** (`Invoice.currency`, `exchangeRatesSnapshot`). Şablonda `cac:PricingExchangeRate` yok.
- ProServis `'TL'` kullanıyor, UBL `TRY` istiyor. Bu eşleme tanımlanmamış.

**Düzeltme:**
- XML, şablon metniyle değil bir XML builder ile üretilmeli.
- CI'da **GİB XSD + Schematron doğrulaması** zorunlu test olmalı.
- Doğruluk kriteri "QNB repodaki C# kopyalandı" olamaz; ölçüt GİB doğrulayıcısından geçmektir.

### A7. "GİB portalını tamamen kaldır" kararı çok kiracılı SaaS için yanlış
- Entegratör kontör/sözleşme maliyeti gerektirir. Her tenant'ın (bayinin) entegratör sözleşmesi olmayacak.
- **Satıcı tarafı mükellefiyet** atlanmış: e-Fatura gönderebilmek için *faturayı kesen tenant'ın* da e-Fatura mükellefi ve bir entegratöre kayıtlı olması gerekir. Mükellef olmayan tenant yalnız e-Arşiv kesebilir, çoğu zaman da portal üzerinden.
- **Düzeltme:** Sağlayıcı soyutlaması (`EDocumentProvider`) tenant bazında seçilmeli: `gib_portal` (mevcut kod, adapter olarak korunur) | `qnb` | `uyumsoft`. `GibSmsModal` yalnız portal sağlayıcısında kalmalı.

---

## B. BÜYÜK BULGULAR (Major)

### B1. Kaynak repo uygunluğu abartılmış
- `QNBFinansGIB`: .NET 4.5 WinForms, kodda gömülü kimlik bilgileri (`DisServisler.cs` L26–41), QNB'ye özel WSDL Web Reference. 177 KB C# kodunu TypeScript'e taşımak "uyarlama" değil, yeniden yazımdır.
- **Öneri:** Önce entegratör seçimi ve sözleşmesi yapılmalı (Faz 0 kararı). Ardından yalnız o entegratörün güncel resmi API'si (birçoğunda REST/JSON var) için tek adapter yazılmalı. Repolar referans olarak kullanılmalı, kopyalanmamalı.

### B2. Çift e-belge kesme riski (Logo ↔ ProServis)
- Repo 6, Logo'nun **e-Logo** ile e-Fatura kestiği senaryoyu destekliyor. Plan hem ProServis'in GİB'e fatura göndermesini hem de faturanın Logo'ya aktarılmasını öneriyor.
- Logo tarafında e-Fatura otomatik tetikleniyorsa **aynı satış GİB'e iki kez gider.**
- **Düzeltme:** Her tenant için tek bir **"e-belge sahibi" (issuer of record)** kararı alınmalı: ProServis ya da Logo. Logo'ya aktarılan faturada e-belge bayrağı kapalı olmalı (Logo `INVOICE.EINVOICE` alanı) ve GİB numarası/UUID referans olarak taşınmalı.

### B3. Logo eşleme hataları
- `ARP_CODE` Logo cari kodudur, VKN değildir. `customerId ↔ Logo CODE` için bir eşleme tablosu gerekiyor (plan VKN basıyor).
- CPC, kiralama ve servis bedelleri **hizmet** satırıdır (`TRANSACTION TYPE=4`, hizmet kartı), malzeme değildir. Plan tüm satırları malzeme (`TYPE=0`) yazıyor.
- Logo Objects bir COM/UnityObjects kütüphanesidir. Repo 6 ek bir servis katmanı (LObjects service) kullanıyor; bunun lisans ve kurulum bağımlılığı plana yazılmalı.
- SQL'e doğrudan yazma yasak olmalı; SQL yalnız okuma (bakiye, stok) için kullanılmalı.

### B4. Taksit/kiralama motoru mevcut sözleşme yapısını yok sayıyor
- **Gerçek:** `contractService.ts` (761 satır; `CustomerContract`, `RentalPriceEntry`, `ContractType`) ve bakım faturalama (`lib/maintenance`) zaten mevcut.
- Plan bu iki muhasebe modelini birbirine karıştırıyor:
  - **Kiralama:** Her dönem için ayrı fatura kesilir, KDV o döneme aittir.
  - **Taksitli satış:** Satışta tek fatura kesilir (KDV'nin tamamı o faturada), taksitler alacak olarak izlenir.
- **Düzeltme:**
  - `PaymentPlan` yalnız taksitli satış alacağı olmalı ve tek bir `invoiceId`'ye bağlanmalı.
  - Kiralama mevcut `contracts` + periyodik fatura üretimi ile yürümeli.
  - Tahsilatlar mevcut `Invoice.paymentHistory` / `paidAmount` / `CustomerLedgerPanel` hattına yazılmalı; ayrı bir defter açılmamalı.
  - USD sözleşmede TL tahsilat ve **kur farkı faturası** akışı eklenmeli.

### B5. Vade tarihi saat dilimi
- Plan `addMonths` hesabını UTC'de yapıyor. Firestore `Timestamp` ile UTC gece yarısı, İstanbul saatinde 03:00'e denk gelir. Gün hesapları ve "vadesi geçti" kontrolleri kayar.
- **Düzeltme:** Vadeler `YYYY-MM-DD` takvim tarihi (string) olarak saklanmalı, hesaplar `Europe/Istanbul` saat dilimine göre yapılmalı. Mevcut `lib/maintenance.addMonths` incelenip tek bir yardımcı fonksiyonda birleştirilmeli.

### B6. Çek modelinde iç tutarsızlıklar
- Akış şemasında kullanılan `PENDING_CHEQUE` durumu `PaymentInstallment.status` kümesinde tanımlı değil.
- Ciro için bir tedarikçi varlığı gerekiyor; mevcut `purchasePartner` serbest metin.
- Karşılıksız çek durumunda tahsilatın ters kaydı tanımlanmamış.
- **Düzeltme:** Çekin alınması tahsilat sayılmamalı. Çek `COLLECTED` olduğunda tahsilat kaydı oluşmalı. `BOUNCED` durumunda ters kayıt ve uyarı üretilmeli.

### B7. Banka eşleştirme skoru matematiksel olarak hatalı
- Tutar ve isim tam eşleşip tarih 7 günden eskiyse skor 50 + 20 = **70** olur ve 80 eşiğinin altında kalır. Geç ödemeler hiç önerilmez; ödemelerin çoğu da gecikir.
- Kısmi ödeme, tek havale ile birden çok fatura kapatma ve **USD fatura için TL ödeme** (tutar asla tam eşleşmez) ele alınmamış.
- Aynı ekstrenin iki kez yüklenmesine karşı bir tekilleştirme (dedupe) yok.
- "Banka formatlarını otomatik algıla" gerçekçi değil.
- **Düzeltme:**
  - Banka başına sütun eşleme profili + kullanıcı eşlemesi.
  - Satır hash'i ile tekilleştirme: `tarih + tutar + açıklama + bakiye`.
  - Aday kümesi önce müşteriye göre daraltılmalı (VKN/IBAN/unvan); ardından tutar toleransı ve kur dönüşümü uygulanmalı.
  - Bire-çok ve çoğa-çok **dağıtım (allocation)** ekranı eklenmeli.

### B8. e-İrsaliye: yasal iddia abartılmış, mevcut stok akışı yok sayılmış
- e-İrsaliye zorunluluğu mükellefiyet eşiklerine bağlıdır. Mükellef olmayan tenant matbu irsaliye kullanabilir. Modül tenant bazında opsiyonel olmalı.
- **Gerçek:** `stockTransferService.ts`, `warehouseService.ts` ve `ConsignmentDevice` tipi (atölyeye alınan cihaz) zaten var. e-İrsaliye ayrı bir modül olarak değil, **bu akışlardan türetilen belge** olarak tasarlanmalı.
- DespatchAdvice şablonunda eksikler: `DespatchSupplierParty`, `DeliveryCustomerParty`, teslim adresi, `CarrierParty`, irsaliye yanıtı (alıcı kabul/red) akışı.
- Plaka regex'i boşluklu formatı (`34 ABC 123`) kabul etmiyor; doğrulamadan önce normalizasyon gerekli.

### B9. Arayüz konumlandırması
- `invoices/page.tsx` şu an 3.649 satır / 200 KB. Plan buraya üç sekme daha eklemeyi öneriyor.
- **Düzeltme:** Ayrı route'lar açılmalı:
  - `/dashboard/e-documents`
  - `/dashboard/finance/reconciliation`
  - `/dashboard/finance/cheques`
  - `/dashboard/finance/payment-plans`
- Bunlar mevcut `navigationConfig.ts` ve `modulePermissions.ts` dosyalarına kaydedilmeli. FinansMax `catalog.ts` taşınmamalı; mevcut `modulePermissions` + `TENANT_PAKET_VE_KULLANICI_YETKI_MIMARISI_PLANI.md` ile birleştirilmeli.

### B10. Belge numaralandırma
- GİB numarası (3 harfli seri + yıl + 9 hane) tekil ve boşluksuz olmalı. Yıl dönümünde sıfırlanmalı. Bazı entegratörler numarayı kendisi atar.
- **Düzeltme:** Mevcut `counterService.ts` (`runTransaction` kullanıyor) ile tenant + seri + yıl bazında sayaç tutulmalı. Numara atamanın sağlayıcıya mı ProServis'e mi ait olduğu adapter sözleşmesinde belirtilmeli.

---

## C. ORTA SEVİYE / EKSİK KAPSAM

1. **İptal ve iade akışları:**
   - e-Arşiv iptali (süre sınırı)
   - e-Fatura için iade faturası
   - TICARIFATURA için alıcı kabul/red (8 gün)
   - GİB portal itirazı
   Plan yalnız "silinemez" diyor.
2. **Gelen faturalar:** Inbox'tan alış faturası ve stok girişi oluşturma akışı tanımsız (tedarikçi/ürün eşleme).
3. **Test stratejisi:**
   - Entegratör test ortamı
   - XSD/Schematron doğrulaması
   - Kuruş ve ay sonu birim testleri
   - Outbox idempotency testleri
   - Tenant izolasyonu için Security Rules testleri
4. **Geçiş planı:**
   - Mevcut portal ile imzalanmış faturalar
   - Tenant bazında feature flag
   - Paralel çalışma dönemi
   - Geri dönüş (rollback) yolu
5. **Yetki ve denetim:**
   - E-belgeyi kimin kesebileceği, kimin iptal edebileceği
   - `deletionRequestService` (dört göz) ile ilişki
   - Audit log
6. **Maliyet ve işletim:**
   - Kontör takibi
   - Entegratör hata kodlarının kullanıcı mesajlarına eşlenmesi
   - Saklama sorumluluğu (10 yıl — entegratörde mi ProServis'te mi?)
7. **KDV beyan uyarısı:** "Ayın 28'i" sabit kodlanmamalı; mevcut `statutoryRatesService.ts` ile yapılandırılabilir olmalı.

---

## D. v3 İÇİN ÖNERİLEN FAZ SIRASI

| Faz | İçerik | Gerekçe |
| :--- | :--- | :--- |
| **0 — Kararlar & Temel** | Entegratör seçimi; tenant başına e-belge sahibi (ProServis / Logo); `InvoiceItem` genişletme (vatRate, unitCode, iskonto, tevkifat, istisna); kuruş (minor unit) politikası; outbox koleksiyonu; server-only e-belge katmanı iskeleti | A1, A2, A3, A5, B2 olmadan diğer fazlar hatalı temele oturur |
| **1 — e-Belge Sağlayıcı Soyutlaması** | `EDocumentProvider` arayüzü; mevcut GİB portalını adapter olarak sarma (davranış değişmez); geriye uyumlu alanlar | A4, A7 — regresyon olmadan zemin |
| **2 — Entegratör Adapter'ı** | Seçilen tek entegratör; VKN sorgulama; e-Fatura/e-Arşiv; dövizli fatura; iptal/iade; XSD CI | A6, B1, C1 |
| **3 — Taksitli Satış Alacağı & Çek** | Faturaya bağlı `PaymentPlan`; mevcut `paymentHistory` entegrasyonu; çek durum makinesi | B4, B5, B6 |
| **4 — Banka Mutabakatı** | Profil bazlı içe aktarma, tekilleştirme, aday daraltma, dağıtım ekranı | B7 |
| **5 — Logo Connector** | Pull/outbox, cari ve hizmet kartı eşleme, issuer-of-record kontrolü | A3, B2, B3 |
| **6 — e-İrsaliye** | Stok transferi ve konsinye akışlarından türetme, tenant opsiyonel | B8 |

---

## E. İncelemeyi Yapacak İkinci Ajana Sorulması Önerilen Sorular

1. Firestore'da para alanlarını tam sayı kuruşa taşımak mevcut `Invoice` verisi için migrasyon gerektirir mi, yoksa yalnız yeni koleksiyonlara mı uygulanmalı?
2. Outbox + pull modeli, mevcut `proservis-agent-desktop` içine mi eklenmeli, yoksa ayrı bir connector mı olmalı?
3. `InvoiceItem.vatRate` eklendiğinde fatura üreten tüm akışlar (CPC, servis, toner siparişi, bakım, manuel) hangi dosyalarda güncellenmeli? Kapsam listesi çıkarılmalı.
4. Entegratör adapter sözleşmesi numara atama, PDF üretimi ve iptal yeteneklerini nasıl ifade etmeli (capability flags)?
