# ProServis Tanıtım Rehberi

Bu rehber, ProServis'in temel amacını, öne çıkan özelliklerini ve son güncellemelerle gelen yenilikleri kısa ve net şekilde anlatır.

## Nedir?
ProServis; teknik servis, cihaz envanteri, stok, faturalama ve CPC sayaç yönetimini tek bir platformda birleştiren bir servis yönetim yazılımıdır.

## Kimler İçin?
- Teknik servis firmaları
- Cihaz bakım ve onarım ekipleri
- Stok ve müşteri takibini tek ekranda yapmak isteyen işletmeler

## Öne Çıkan Özellikler
- Müşteri, lokasyon ve cihaz envanteri yönetimi
- Servis kayıtları ve durum takibi
- Stok giriş/çıkış ve hareket geçmişi
- Fatura ve PDF çıktıları
- CPC sayaç yönetimi ve raporlama
- E-posta bildirimleri

## Son Güncellemeler (Özet)
Bu sürümde 2. el cihaz akışları ve stok senkronu iyileştirildi:

- 2. el cihaz ekleme ekranında **müşteri cihazı seçimi ve filtreleme**
- Müşteri sekmesinde **“2. El Depoya Taşı”** aksiyonu
- 2. el cihaz listesinde **çift tıklama ile düzenleme**
- 2. el listesinde **arama (model/seri no/kişi)**
- Hurda cihazlar **listede kalır**, düzenlenebilir
- Hurda cihazlar **normal stokta görünür** ve satılabilir
- 2. el cihaz–normal stok **otomatik senkron**
- Bekleyen satışlarda **seri numarası çakışması** için güvenli kontrol
- OpenAI bağımlılığı **opsiyonel**, uygulama açılışını bloklamaz

## Kısa Kullanım Akışı
1. Müşteri ve lokasyon ekle.
2. Cihazları müşteriye tanımla.
3. Servis kaydı aç, teknisyen ata, durumları güncelle.
4. Stoktan satış yap veya 2. el cihaz ekle.
5. PDF çıktıları ve raporları oluştur.

## 2. El Cihaz Akışı
- **Müşteri cihazını** 2. el depoya taşıyabilirsin.
- 2. el listesinde cihazı düzenleyebilir, **hurda** işaretleyebilirsin.
- Hurda olsa bile cihaz **stokta görünür** ve satılabilir.

## Notlar
- Build ve setup süreçleri için `DEPLOYMENT.md` dosyasını inceleyin.
- Uygulama çalıştırma: `python main.py`

