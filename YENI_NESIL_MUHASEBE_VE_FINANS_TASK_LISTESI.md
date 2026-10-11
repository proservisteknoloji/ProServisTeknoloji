# ProServis Yeni Nesil Muhasebe ve Finans — Görev Listesi ve İlerleme Takibi

> **Referans Mimari:** [PROSERVIS_YENI_NESIL_MUHASEBE_VE_FINANS_MIMARI_PLANI.md](./PROSERVIS_YENI_NESIL_MUHASEBE_VE_FINANS_MIMARI_PLANI.md)  
> **İnceleme & Düzeltmeler:** [PROSERVIS_YENI_NESIL_MUHASEBE_VE_FINANS_MIMARI_PLANI_INCELEME_NOTLARI.md](./PROSERVIS_YENI_NESIL_MUHASEBE_VE_FINANS_MIMARI_PLANI_INCELEME_NOTLARI.md)  
> **Başlangıç Tarihi:** 11 Ekim 2026  
> **Durum:** 🟢 Tüm Fazlar Başarıyla Tamamlandı (Production-Ready)  
> **Güvenlik Yedek Noktası:** Git Branch/Tag `backup-pre-finance-update` ve `_backup_finance_upgrade_pre/` (32 kritik dosya)  

---

## 📌 Faz Bazlı Görev Listesi

### 🟢 FAZ 0: Temeller, Veri Modeli ve Kuruş Bütünlüğü
- [x] **Task 0.1:** `src/types/index.ts` güncellemesi:
  - `InvoiceItem`: `vatRate`, `unitCode`, `discountAmountMinor`, `withholdingCode`, `withholdingRate`, `exemptionCode`, `exemptionReason` alanları (opsiyonel/geriye uyumlu).
  - `Invoice`: `eDocProvider`, `eDocumentType`, `eInvoiceProfile`, `paymentPlanId`, `isReconciled`, `reconciledTransactionIds`, `logoSyncStatus`, `logoLogicalRef` alanları.
  - Yeni modeller: `PaymentPlan`, `PaymentInstallment`, `Cheque`, `ChequeStatus`, `IntegrationOutboxEvent`.
- [x] **Task 0.2:** Ortak para/kuruş yardımcı modülü (`src/lib/financeMoney.ts`):
  - Kuruş <-> TL dönüşümleri (`minorUnitsToTl`, `tlToMinorUnits`, `formatMinorUnits`).
  - Taksit kuruş bölüştürme algoritması (`distributeMinorUnits` - artık kuruşun son taksite eklenmesi, kuruş kaybını sıfırlama).
  - UTC/saat dilimi kayması yaratmayan takvim vade hesaplayıcısı (`addCalendarMonths`).
- [x] **Task 0.3:** Fatura oluşturan akışların genişletilmesi:
  - `billingService.ts` (`createInvoice`, `updateInvoice`), `SalesPurchaseInvoiceDialog.tsx`, `invoices/create/page.tsx` fatura kalemlerinde varsayılan KDV oranı (%20) ve birim kodu ('C62' - Adet) otomatik atanması.

---

### 🟢 FAZ 1: Core e-Belge Motoru ve Entegratör Katmanı (Server-Only)
- [x] **Task 1.1:** `src/lib/server/eDocument/EDocumentProvider.ts` arayüzü (`checkUser`, `sendInvoice`, `cancelInvoice`, `getDocumentStatus`, `downloadPdf`).
- [x] **Task 1.2:** `src/lib/server/eDocument/GibPortalProvider.ts` (Mevcut GİB Portal akışını adapter olarak sarma - geriye tam uyumluluk).
- [x] **Task 1.3:** `src/lib/server/eDocument/UblBuilder.ts` (UBL-TR 2.1 Schematron uyumlu XML üretici, çoklu KDV satırları, dövizli TRY kuru).
- [x] **Task 1.4:** `src/lib/server/eDocument/QnbIntegratorProvider.ts` (QNBFinansGIB reposundaki `DisServisler.cs`, `XMLIslemleri.cs` ve `app.config` baz alınarak SOAP Login, VKN sorgulama, e-Fatura ve e-Arşiv gönderim/önizleme adaptörü).
- [x] **Task 1.5:** `src/lib/server/eDocument/index.ts` (Provider Factory - Fallback mekanizması).
- [x] **Task 1.6:** `/api/e-document/send` API rotası ve entegratör kullanılan tenant'lar için SMS bypass / doğrudan imzalama mekanizması.

---

### 🟢 FAZ 2: Finans, Taksit ve Çek Motoru
- [x] **Task 2.1:** `src/services/finance/paymentPlanService.ts` (Taksit planı oluşturma, vadeler, ödeme eşleme, kuruş artığı son taksite ekleme).
- [x] **Task 2.2:** `src/services/finance/chequeService.ts` (Çek durum makinesi: PORTFOLIO -> DEPOSITED -> COLLECTED / BOUNCED / ENDORSED, tahsilat entegrasyonu).
- [x] **Task 2.3:** `/dashboard/finance/payment-plans/page.tsx` (Taksit Planları Arayüzü, KPI kartları, tahsilat modalı).
- [x] **Task 2.4:** `/dashboard/finance/cheques/page.tsx` (Çek Portföyü Arayüzü, filtreler, yeni çek girişi ve durum güncelleme diyalogları).
- [x] **Task 2.5:** Navigasyon ve yetkilendirme entegrasyonu (`navigationConfig.ts` - menüye Taksit ve Çek bağlantıları).

---

### 🟢 FAZ 3: Banka Mutabakatı (Reconciliation)
- [x] **Task 3.1:** Ekstre içe aktarma ve tekilleştirme modülü (`src/services/finance/bankReconciliationService.ts` - CSV parser, satır hashleme ile deduplication).
- [x] **Task 3.2:** Ağırlıklı eşleştirme motoru (Tutar tam eşleşme +50, Fatura no +35, Müşteri unvanı +25 puan).
- [x] **Task 3.3:** `/dashboard/finance/bank-reconciliation/page.tsx` (Ekstre yükleme, akıllı aday eşleştirme ve tek tıkla fatura kapatma arayüzü).

---

### 🟢 FAZ 4: Transactional Outbox & Logo Entegrasyonu
- [x] **Task 4.1:** `src/lib/server/outbox/OutboxService.ts` (Firestore `integration_outbox` kuyruk yöneticisi; enqueue, poll, ack, fail).
- [x] **Task 4.2:** `/api/integrations/outbox/poll` API rotası (Logo Connector için olay çekme uç noktası).
- [x] **Task 4.3:** `/api/integrations/outbox/ack` API rotası (İşlem teyidi ve faturaya `logoLogicalRef` yazma).
- [x] **Task 4.4:** Fatura onaylandığında (`/api/e-document/send`) otomatik olarak `INVOICE_APPROVED` outbox olayının tetiklenmesi.
