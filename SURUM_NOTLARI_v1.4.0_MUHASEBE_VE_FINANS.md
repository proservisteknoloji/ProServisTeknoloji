# 📢 ProServis v1.4.0 Sürüm Notları: Yeni Nesil Muhasebe, Finans & e-Dönüşüm Paketi

**Sürüm:** `v1.4.0`  
**Yayınlanma Tarihi:** 12 Ekim 2026  
**Kapsam:** Yeni Nesil Muhasebe, Finans, e-Belge (e-Fatura / e-Arşiv / e-İrsaliye), Posta Kutusu ve ERP Entegratörleri  
**Derleme Durumu:** 🟢 Clean Build (TypeScript: 0 Hata)

---

## 📌 Yönetici Özeti

ProServis ekosisteminde işletmelerin mali ve operasyonel süreçlerini tek merkezden yönetebilmesini sağlayan kapsamlı **Muhasebe, Finans ve e-Dönüşüm Paketi (v1.4.0)** yayına alınmıştır. 

Bu sürümle birlikte, giden fatura süreçlerinin yanı sıra **tedarikçilerden gelen faturaların yönetildiği Gelen Posta Kutusu (Inbound Inbox)**, şubeler ve depolar arası transferleri resmiyete kavuşturan **GİB UBL-TR 2.1 e-İrsaliye Motoru**, çoklu vadeli **Çek Portföyü**, **Banka Mutabakatı** ve **ERP Entegratörleri** (QNB e-Finans, DİA Cloud, Akınsoft Wolvox, GİB Portalı) tek bir mimaride birleştirilmiştir.

---

> [!IMPORTANT]
> ### ⚠️ e-Fatura & e-Belge Saha Testi ve Geri Bildirim Bilgilendirmesi
> **e-Fatura, e-Arşiv ve e-İrsaliye modüllerinde yerel testler ve simülasyon ortamı doğrulamaları başarıyla tamamlanmış olup; gerçek saha test aşaması aktif olarak devam etmektedir.**
>
> Gerçek mükellef bilgileri, canlı ERP bağlantıları veya fiili faturalaşma esnasında herhangi bir hata, uyarı ya da tutarsızlık ile karşılaşılması durumunda; **hata mesajı, ekran görüntüsü ve işlem detaylarının sistemdeki Geri Bildirim butonu (veya destek kanalları) üzerinden ivedilikle bildirilmesi gerekmektedir.**

---

## 🚀 Öne Çıkan Yeni Özellikler ve Modüller

### 1. 📬 Gelen e-Fatura / e-Arşiv Posta Kutusu (Inbound Inbox)
* **Otomatik Tedarikçi Faturası Senkronizasyonu:** QNB e-Finans, DİA Cloud, Akınsoft Wolvox veya GİB Portal posta kutularından gelen faturalar tek tıkla sisteme çekilir ve ETTN bazlı mükerrer kontrolünden geçirilerek güvenle kaydedilir.
* **Ticari Fatura Kabul / Red Yönetimi (ApplicationResponse):** Ticari faturası gelen alımlar için yasal 8 günlük süre içerisinde **"Faturayı Kabul Et"** veya **"Gerekçeli Reddet"** yanıtı GİB / entegratör sistemine iletilebilir.
* **Tek Tıkla İşletme Giderine Dönüştürme:** Tedarikçi faturaları incelendikten sonra tek tıkla şirket işletme masraflarına (`OperatingExpense`) aktarılabilir; yakıt, bakım, malzeme vb. gider kategorilerine anında işlenebilir.
* **Resmi Önizleme & UBL XML İndirme:** Gelen faturanın kalem bazlı detayları, KDV oranları ve resmi UBL-TR XML çıktısı görüntülenebilir.
* **Erişim:** `http://localhost:3000/dashboard/e-documents` ➔ **Gelen Kutusu** sekmesi.

---

### 2. 🚚 Resmi UBL-TR 2.1 e-İrsaliye Motoru (Outbound e-Despatch)
* **GİB Standartlarında DespatchAdvice Üretimi:** Şubeler ve merkez depolar arasındaki dahili stok transferleri için GİB UBL-TR 2.1 e-İrsaliye XML motoru (`UblDespatchBuilder`) devreye alındı.
* **Taşıyıcı ve Sevkiyat Bilgi Formu (`SendEDespatchDialog`):** Kargo/nakliyeci ünvanı, taşıyıcı VKN, araç plakası, sürücü adı ve 11 haneli TCKN'si ile fiili sevk tarihi ve saati doğrulanarak resmi belge düzenlenebilir.
* **Entegratörden İmzalı Belge No:** Belgeye anında resmi `IRS2026...` seri numarası ve tekil ETTN (UUID) atanır.
* **Sevk İrsaliyesi Önizleme & Çıktı:** [TransferWaybillDialog](file:///c:/Users/umits/Desktop/ProservisProje_web_compile/proservis-web/src/components/stock/TransferWaybillDialog.tsx) üzerinden hem resmi e-İrsaliye UBL XML indirilebilir hem de A4 formatında sevk irsaliyesi PDF olarak basılabilir.
* **Erişim:** `http://localhost:3000/dashboard/e-documents` ➔ **e-İrsaliyeler** sekmesi veya `/dashboard/stock/transfers`.

---

### 3. 📑 3 Sekmeli Bütünleşik e-Belge Konsolu
`/dashboard/e-documents` sayfası 3 ana operasyon merkezine ayrıldı:
1. **Giden e-Faturalar:** Resmi e-Fatura, e-Arşiv, Tevkifatlı faturalar, canlı VKN sorgulama, resmi XML indirme ve yazdırma.
2. **Gelen Kutusu (Inbox):** Tedarikçi faturaları KPI kartları (Toplam, Onay Bekleyen Ticari, Kabul Edilen, Masrafa İşlenen), filtreler ve onay mekanizması.
3. **e-İrsaliyeler:** Dahili lojistik transferleri, GİB e-İrsaliye durumları, nakliye detayları ve XML ihracı.

---

### 4. 💳 Gelişmiş Çek Portföyü ve Durum Makinesi
* **Müşteri Filtreleme & Arama:** Çek listesinde müşteri bazlı hızlı filtreleme ve durum takibi.
* **Çoklu / Seri Çek Girişi:** Aynı müşteriye ait birden fazla vadeli çek tek seferde sisteme girilebilir.
* **Durum Makinesi:** Çekin tüm yaşam döngüsü (*Portföyde / Cüzdanda*, *Bankada Tahsilde*, *Tahsil Edildi*, *Karşılıksız*, *Ciro Edildi*) adım adım izlenir.
* **Erişim:** `http://localhost:3000/dashboard/finance/cheques`

---

### 5. 🏦 Akıllı Banka Mutabakatı (Reconciliation)
* **CSV Ekstre İçe Aktarımı:** Bankalardan indirilen hesap ekstreleri satır bazında sisteme aktarılır ve tekilleştirilir.
* **Ağırlıklı Aday Puanlama Motoru:**
  * Tutar Eşleşmesi: **+50 Puan**
  * Fatura / Fiş No Eşleşmesi: **+35 Puan**
  * Ünvan / Açıklama Benzerliği: **+25 Puan**
* **Erişim:** `http://localhost:3000/dashboard/finance/bank-reconciliation`

---

### 6. 📄 Taksit & Ödeme Planları A4 PDF ve Sağ Tık Yönetimi
* **Resmi A4 PDF Dökümü:** Taksitli satışlarda müşteriye sunulacak resmi ödeme planı tablosu tek tıkla A4 PDF olarak basılabilir.
* **Sağ Tık (Context Menu) Pratikliği:** Tablolarda buton kalabalığını önlemek amacıyla satıra sağ tıklayarak vade öteleme, tutar güncelleme ve iptal işlemleri eklendi.
* **Vade Farkı Faturası Entegrasyonu:** Geciken taksitler için tek tıkla doğrudan fatura kesme ekranına yönlendirme sağlandı.
* **Erişim:** `http://localhost:3000/dashboard/finance/payment-plans`

---

### 7. 🏛️ Tevkifatlı Fatura Kesimi & Hesaplayıcı
* GİB mevzuatındaki tüm tevkifat kodları (**601..630**) ve oranları (**2/10, 4/10, 5/10, 7/10, 9/10**) sisteme dahil edildi.
* Matrah, Tevkif Edilen KDV ve Tahsil Edilecek KDV tutarları anlık olarak hesaplanır; fatura PDF'inde yasal şablona uygun olarak Türkçeleştirilmiş yazı formatında basılır.
* **Erişim:** `http://localhost:3000/dashboard/invoices/create`

---

### 8. 🌐 Çoklu ERP & Entegratör Mimarisi
* **4 Büyük Sağlayıcı Desteği:**
  * **QNB e-Finans:** Resmi SOAP web servisleri (`ConnectorService`, `UserService`, `EarsivWebService`).
  * **DİA ERP Cloud:** REST / JSON API v2 session login ve fatura/irsaliye aktarım motoru.
  * **Akınsoft Wolvox ERP:** Wolvox Web Servis (Rest/SOAP) & UBL-TR 2.1 e-Dönüşüm köprüsü.
  * **GİB İnteraktif Portal:** 5.000 / 30.000 TL portal entegrasyonu ve anında test hesabı doldurma altyapısı.
* **Varsayılan (Aktif) Entegratör Düzeni:** Karışıklığı engellemek için tek bir aktif entegratör seçimi kurgulandı.
* **Entegratör Kurulum Kılavuzları & A4 PDF:** Her entegratör için port açma, yetkilendirme ve hata çözümü kılavuzu form altlarına eklendi.
* **Erişim:** `http://localhost:3000/dashboard/settings?tab=gib`

---

## 🛠️ Teknik ve Mimari İyileştirmeler
1. **Zero-Trust Sunucu İzolasyonu:** Tüm entegratör şifreleri ve özel API istekleri yalnızca sunucu tarafında (`src/lib/server/eDocument/...`) çalışır; istemciye hiçbir hassas veri sızdırılmaz.
2. **Kuruş Bütünlüğü (Minor Units):** Float yuvarlama hatalarını önlemek adına tüm yeni finansal modeller kuruş (minor unit) tam sayı standardında saklanır.
3. **Modal UI Düzeltmesi:** Diyalog pencerelerinde sağ üstteki kapatma (X) butonu ile "Yazdır/Kaydet" butonlarının üst üste binme sorunu tüm bileşenlerde giderildi.
4. **TypeScript Kontrolü:** Proje genelinde `0 hata` ile temiz derleme garantisi sağlandı.

---

## 📋 Saha Testi Kontrol Listesi

| Modül | Test Edilecek İşlem | Durum |
| :--- | :--- | :--- |
| **Giden e-Fatura** | VKN Mükellef Sorgulama, e-Fatura/e-Arşiv gönderimi ve UBL XML indirme | 🟡 Saha Doğrulamasında |
| **Gelen Kutusu** | Entegratörden fatura çekme, Ticari kabul/ret ve İşletme Gideri yapma | 🟡 Saha Doğrulamasında |
| **e-İrsaliye** | Taşıyıcı ve plaka girerek stok sevk irsaliyesi düzenleme, XML çıktısı | 🟡 Saha Doğrulamasında |
| **Çek Portföyü** | Seri çek kaydı, durum makinesi geçişleri (Portföy ➔ Banka ➔ Tahsil) | 🟢 Hazır |
| **Banka Mutabakatı** | CSV ekstre yükleme ve otomatik aday eşleştirme puanlaması | 🟢 Hazır |
| **Taksit Planları** | Taksit planı oluşturma, sağ tık A4 PDF çıktısı, vade farkı faturası | 🟢 Hazır |
| **Tevkifat** | Tevkifat kodu seçimi, matrah ve net tutar hesaplama | 🟢 Hazır |
| **Entegratörler** | Canlı QNB, DİA Cloud veya Akınsoft kullanıcı/şifre bağlantı testi | 🟡 Canlı Müşteri Şifresi Bekleniyor |

---

*ProServis Teknik & Ürün Yönetimi Ekibi*
