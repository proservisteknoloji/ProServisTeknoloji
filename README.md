# ProServis - Teknik Servis Yönetim Sistemi

<div align="center">

**Kyocera Teknik Servis ve Stok Yönetim Yazılımı**

[![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)](https://github.com/umitsagdic77-ai/ProServis_Proje)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-orange.svg)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Last Update](https://img.shields.io/badge/son%20güncelleme-6%20Aralık%202025-red.svg)](#)

</div>

---

## 📖 İçindekiler

- [Hakkında](#-hakkında)
- [Özellikler](#-özellikler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Proje Yapısı](#-proje-yapısı)
- [Teknik Detaylar](#-teknik-detaylar)
- [İletişim](#-iletişim)
- [Lisans](#-lisans)

---

## 🎯 Hakkında

**ProServis**, Kyocera fotokopi ve yazıcı teknik servis firmaları için geliştirilmiş kapsamlı bir yönetim yazılımıdır. Müşteri takibi, cihaz envanteri, servis işlemleri, stok yönetimi, faturalama ve CPC sayaç yönetimi gibi tüm ihtiyaçları tek bir platformda birleştirir.

### ✨ Neden ProServis?

- 🚀 **Tek Dosya EXE** - Kurulum gerektirmez, hemen çalışır
- 💻 **Modern Arayüz** - PyQt6 ile profesyonel kullanıcı deneyimi
- 📊 **Kapsamlı Raporlama** - PDF formatında profesyonel raporlar
- 🔐 **Güvenli** - Bcrypt şifreleme, rol tabanlı yetkilendirme
- 🖨️ **Doğrudan Yazdırma** - PyMuPDF ile yazıcıya direkt çıktı
- 📧 **E-posta Entegrasyonu** - Gmail/SMTP üzerinden otomatik bildirimler
- 💾 **Otomatik Yedekleme** - Veri kaybı yaşamayın
- 🌐 **Çoklu Döviz** - TL, USD, EUR + TCMB güncel kurları

---

## 🚀 Özellikler

### 🏢 Müşteri Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ Firma Profilleri | Detaylı firma bilgileri (ad, adres, vergi no, telefon, e-posta) |
| ✅ Kişi Yönetimi | Her firmaya bağlı yetkili kişi kayıtları |
| ✅ Lokasyon Takibi | Birden fazla adres ve şube yönetimi |
| ✅ Müşteri Geçmişi | Tüm işlemler, servisler ve satışlar tek ekranda |
| ✅ Hızlı Arama | İsim, telefon, vergi no ile anlık arama |
| ✅ CSV Import/Export | Toplu müşteri aktarımı (10x hızlı) |
| ✅ Müşteri Kartı | Detaylı müşteri bilgi kartı görüntüleme |

---

## 🧭 Hızlı Tanıtım (Özet)
ProServis, teknik servis operasyonlarını tek merkezden yönetmek için tasarlanmış bir platformdur. Müşteri, cihaz, servis, stok ve faturalama süreçlerini birbirine bağlı şekilde yönetir. Son güncellemelerle 2. el cihaz akışı, stok senkronu ve satış güvenliği güçlendirildi.

### 🆕 Son Güncellemeler (Kısa)
- 2. el cihaz ekleme ekranında **müşteri cihazı seçimi ve filtreleme**
- Müşteri sekmesinde **“2. El Depoya Taşı”**
- 2. el cihaz listesinde **çift tıklama ile düzenleme**
- 2. el listesinde **arama (model/seri no/kişi)**
- Hurda cihazlar listede kalır, **düzenlenebilir**
- Hurda cihazlar **normal stokta görünür** ve satılabilir
- 2. el cihaz–normal stok **otomatik senkron**
- Bekleyen satışta **seri numarası çakışması** için güvenli kontrol
- OpenAI bağımlılığı **opsiyonel**, uygulama açılışını bloklamaz

Detaylı tanıtım için `GUIDE.md` dosyasına bakabilirsiniz.

### 🖨️ Cihaz Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ Kyocera Cihaz Envanteri | Marka, model, seri no ile detaylı kayıt |
| ✅ Toner Uyumluluk Kontrolü | Otomatik model-toner eşleştirme |
| ✅ Cihaz Lokasyonu | Hangi müşteride, hangi adreste |
| ✅ Sayaç Takibi | Siyah/renkli kopya sayacı kayıtları |
| ✅ Cihaz Geçmişi | Servis, bakım ve sayaç geçmişi |
| ✅ Toplu Cihaz Satışı | Tek müşteriye birden fazla cihaz kaydı |
| ✅ Kyocera Model Veritabanı | 400+ Kyocera model bilgisi |
| ✅ Cihaz Analizi | Cihaz bazlı maliyet ve performans analizi |

### 🔧 Servis Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ Servis Kayıt Sistemi | Arıza kaydı, atama, takip |
| ✅ Durum Yönetimi | 7 farklı durum (Beklemede, Devam Ediyor, Teslim Edildi, vb.) |
| ✅ Teknisyen Atama | Servis sorumlusu belirleme |
| ✅ Gerçek Tamamlanma Süreleri | Oluşturma-teslim arası otomatik hesaplama |
| ✅ Servis Maliyeti | İşçilik + malzeme maliyeti takibi |
| ✅ Servis Notları | Detaylı açıklama ve çözüm notları |
| ✅ Öncelik Sistemi | Düşük/Normal/Yüksek/Acil öncelik seviyeleri |
| ✅ PDF Servis Formu | Profesyonel servis çıktısı (logo, imza alanı) |
| ✅ Servis İş Geçmişi Raporları | Tarih, teknisyen, durum filtreleri ile raporlama |
| ✅ Servis İstatistikleri | Toplam servis, tamamlanan, ortalama süre, toplam maliyet |
| ✅ Doğrudan Yazdırma | PyMuPDF ile yazıcıya direkt çıktı |

### 📦 Stok Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ Toner Stok Takibi | Marka, model, renk, stok miktarı |
| ✅ Yedek Parça Stoku | Genel stok kalemleri yönetimi |
| ✅ Minimum Stok Uyarıları | Otomatik düşük stok bildirimleri |
| ✅ Stok Giriş/Çıkış | Tedarikçi ve fiyat bilgisi ile kayıt |
| ✅ Stok Geçmişi | Tüm stok hareketleri (giriş/çıkış/satış) |
| ✅ Toplu Stok İşlemleri | CSV ile hızlı stok aktarımı |
| ✅ Stok Envanter Raporu | Anlık stok durumu görüntüleme |
| ✅ Öntanımlı Stok Listesi | Kyocera toner/parça veritabanı |

### 💰 Faturalama ve Tahsilat
| Özellik | Açıklama |
|---------|----------|
| ✅ Fatura Oluşturma | Müşteri, tutar, vade, ödeme tipi |
| ✅ Çoklu Döviz Desteği | TL, USD, EUR (TCMB güncel kurlar) |
| ✅ Otomatik Kur Güncellemesi | Günlük TCMB kuru çekme |
| ✅ Vade Takibi | Ödeme tarihi ve vade sonu kontrolü |
| ✅ Ödeme Durumu | Ödenmedi/Kısmi/Ödendi |
| ✅ Kısmi Ödeme | Taksitli ödeme kayıtları |
| ✅ Tahsilat Geçmişi | Tüm ödeme işlemlerini görüntüleme |
| ✅ Fatura PDF | Profesyonel fatura çıktısı |
| ✅ Finansal Raporlar | Tahsilat, alacak, ödeme raporları |
| ✅ Fatura Önizleme | Yazdırma öncesi görüntüleme |

### 📊 CPC Sayaç Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ Sayaç Okuma Kayıtları | Siyah/renkli sayaç değerleri |
| ✅ Otomatik Fark Hesaplama | Önceki okuma ile fark |
| ✅ CPC Fiyatlandırma | Kopya başına maliyet tanımlama |
| ✅ Sayaç Bazlı Faturalama | Otomatik tutar hesaplama |
| ✅ Sayaç Geçmişi | Tüm okuma kayıtları ve grafikler |
| ✅ Toplu Sayaç Okuma | CSV ile hızlı veri girişi |
| ✅ Toner Takibi | CPC ile toner tüketim analizi |

### 📝 Teklif Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ Teklif Oluşturma | Müşteriye özel teklif hazırlama |
| ✅ Teklif PDF | Profesyonel teklif çıktısı |
| ✅ Teklif Onaylama | Teklif durumu takibi |
| ✅ Teklif Kopyalama | Mevcut tekliften yeni teklif |
| ✅ Doğrudan Yazdırma | Teklifi yazıcıya gönderme |

### 📄 PDF ve Raporlama
| Özellik | Açıklama |
|---------|----------|
| ✅ Profesyonel Servis Formları | Şirket logosu, müşteri bilgisi, imza alanı |
| ✅ Fatura PDF | Detaylı fatura çıktısı |
| ✅ Teklif PDF | Profesyonel teklif formatı |
| ✅ Servis İş Geçmişi Raporu | Filtrelenebilir, istatistikli raporlar |
| ✅ Stok Raporu | Anlık envanter durumu |
| ✅ Müşteri Raporu | Tüm işlemler ve geçmiş |
| ✅ Finansal Raporlar | Tahsilat, alacak durum raporları |
| ✅ Aylık Raporlar | Aylık servis/satış özeti |
| ✅ ReportLab + PyMuPDF | Yüksek kaliteli PDF çıktıları ve yazdırma |

### 🔐 Kullanıcı ve Güvenlik
| Özellik | Açıklama |
|---------|----------|
| ✅ Rol Tabanlı Yetkilendirme | Admin ve kullanıcı rolleri |
| ✅ Güvenli Şifre Sistemi | Bcrypt ile hash'lenmiş şifreler |
| ✅ Kullanıcı Yönetimi | Kullanıcı ekleme, düzenleme, silme |
| ✅ Oturum Yönetimi | Güvenli giriş/çıkış |
| ✅ Yetki Kontrolü | Hassas işlemler için admin yetkisi |
| ✅ Şifre Değiştirme | Kullanıcı bazlı şifre güncelleme |
| ✅ İlk Kullanıcı Wizard | Kurulum sırasında admin oluşturma |
| ✅ Demo/Lisans Aktivasyon | Lisans yönetimi ve demo modu |

### ⚙️ Sistem Ayarları
| Özellik | Açıklama |
|---------|----------|
| ✅ Şirket Profili | Logo, adres, vergi bilgileri |
| ✅ Banka Hesapları | Fatura altı banka bilgileri |
| ✅ E-posta Ayarları | SMTP entegrasyonu (Gmail, Outlook, özel) |
| ✅ Otomatik Yedekleme | Zamanlanmış veritabanı yedeği (günlük/haftalık/aylık) |
| ✅ Manuel Yedekleme | Anlık yedek alma ve geri yükleme |
| ✅ Fiyatlandırma Ayarları | Varsayılan KDV oranı, döviz tercihi |
| ✅ Ağ Yolu Ayarları | Ortak ağ yedekleme konumu |
| ✅ Tema Ayarları | Aydınlık/Karanlık mod |
| ✅ API Ayarları | AI sağlayıcı API key yönetimi |
| ✅ Güncelleme Yönetimi | Otomatik güncelleme kontrolü |

### 📧 Bildirim Sistemi
| Özellik | Açıklama |
|---------|----------|
| ✅ E-posta Bildirimleri | Servis durumu değişikliklerinde otomatik mail |
| ✅ Stok Uyarıları | Minimum stok seviyesinde bildirim |
| ✅ Vade Hatırlatmaları | Yaklaşan ödeme tarihleri |
| ✅ Sistem Bildirimleri | Windows toast bildirimleri |
| ✅ Gmail SMTP Entegrasyonu | Gmail App Password ile güvenli gönderim |
| ✅ Demo/Aktivasyon Bildirimleri | Lisans işlemlerinde otomatik e-posta |

### 🤖 AI Asistan (Opsiyonel)
| Özellik | Açıklama |
|---------|----------|
| ✅ OpenAI Entegrasyonu | GPT modellerini kullanma |
| ✅ Google Gemini Entegrasyonu | Gemini Pro ile AI desteği |
| ✅ Veritabanı Sorgu Asistanı | Doğal dil ile veritabanı sorgulama |
| ✅ AI Tab | Yapay zeka destekli yardım |

### 💾 Veri Yönetimi
| Özellik | Açıklama |
|---------|----------|
| ✅ SQLite Veritabanı | Yerel, hızlı ve güvenilir |
| ✅ Otomatik Migrasyon | Versiyon güncellemelerinde otomatik şema güncelleme |
| ✅ CSV Import/Export | Toplu veri aktarımı (müşteri, cihaz, stok, servis) |
| ✅ Veritabanı Yedekleme | Otomatik ve manuel yedekleme |
| ✅ Veri Bütünlüğü | Foreign key kontrolü, transaction yönetimi |
| ✅ Veri Transferi | Sistemler arası veri aktarımı |
| ✅ Azure SQL Desteği | Bulut veritabanı entegrasyonu (opsiyonel) |

### 📱 Dashboard
| Özellik | Açıklama |
|---------|----------|
| ✅ Özet Görünüm | Güncel istatistikler ve grafikler |
| ✅ Bekleyen Servisler | Açık servis listesi |
| ✅ Stok Durumu | Kritik stok uyarıları |
| ✅ Yaklaşan Vadeler | Ödenmemiş faturalar |
| ✅ Hızlı Erişim | Sık kullanılan işlemlere kısayol |

---

## 📋 Gereksinimler

### Sistem Gereksinimleri
| Gereksinim | Minimum | Önerilen |
|------------|---------|----------|
| İşletim Sistemi | Windows 10 (64-bit) | Windows 11 (64-bit) |
| RAM | 4 GB | 8 GB |
| Disk Alanı | 500 MB | 1 GB |
| Ekran Çözünürlüğü | 1366x768 | 1920x1080 |
| İnternet | Opsiyonel | Önerilir (döviz kuru, e-posta) |

### Yazılım Bağımlılıkları (Geliştirme)
```
PyQt6>=6.6.0              # Modern UI framework
PyQt6-Charts>=6.6.0       # Grafik/chart desteği
reportlab>=4.0.0          # PDF oluşturma
PyMuPDF>=1.24.0           # PDF render ve yazdırma
requests>=2.31.0          # HTTP istekleri
bcrypt>=4.1.0             # Şifre hash'leme
Pillow>=10.0.0            # Görüntü işleme
lxml>=4.9.0               # XML/HTML parsing
beautifulsoup4>=4.12.0    # Web scraping
psutil>=5.9.0             # Sistem bilgisi
pandas>=2.1.0             # Veri işleme
openpyxl>=3.1.0           # Excel dosyaları
cryptography>=41.0.0      # Şifreleme
python-dotenv>=1.0.0      # Ortam değişkenleri
pywin32>=306              # Windows API
wmi>=1.5.1                # Windows WMI
```

---

## 🔧 Kurulum

### Hazır EXE Kullanımı (Önerilen)

1. **Setup Dosyasını İndirin**
   - `ProServis_v2.3.0_Setup.exe` dosyasını indirin
   - Kurulum sihirbazını takip edin

2. **Veya Tek Dosya EXE**
   - `ProServis.exe` dosyasını herhangi bir klasöre kopyalayın
   - Çalıştırın

### Kaynak Koddan Kurulum

```bash
# 1. Projeyi klonlayın
git clone https://github.com/umitsagdic77-ai/ProServis_Proje.git
cd ProServis_Proje

# 2. Sanal ortam oluşturun
python -m venv .venv
.venv\Scripts\activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Uygulamayı başlatın
python main.py
```

### EXE Build Oluşturma

```bash
# Tek dosya EXE build
.venv\Scripts\pyinstaller.exe --clean ProServis.spec

# Setup installer (Inno Setup gerekli)
"C:\Program Files\Inno Setup 6\ISCC.exe" ProServis_Setup.iss
```

---

## 🎯 Kullanım

### 🚀 İlk Kullanım

1. **Setup Wizard** - Uygulamayı ilk kez çalıştırdığınızda:
   - Hoş geldiniz ekranı
   - Şirket bilgileri (ad, adres, vergi no, logo)
   - Admin kullanıcısı oluşturma
   - Veritabanı kurulumu
   - Özet ve tamamlama

2. **Giriş Yapın** - Oluşturduğunuz kullanıcı adı/şifre ile

3. **Dashboard** - Ana ekranda istatistikler ve hızlı erişim

### 📊 Test Verisi

Proje hazır test verileri içerir:

| Bilgi | Değer |
|-------|-------|
| Kullanıcı | `kopier` |
| Şifre | `kopier` |
| Müşteri | 50 firma |
| Cihaz | 86 cihaz (24 model) |
| Toner | 10 çeşit |
| Servis | 180 kayıt |

---

## 🗂️ Proje Yapısı

```
ProServis_Proje/
├── 📄 main.py                    # Ana uygulama giriş noktası
├── 📄 requirements.txt           # Python bağımlılıkları
├── 📄 ProServis.spec             # PyInstaller build dosyası
├── 📄 ProServis_Setup.iss        # Inno Setup script
├── 📄 .env                       # SMTP ayarları (gizli)
├── 📄 LICENSE                    # MIT Lisans
├── 📄 README.md                  # Bu dosya
│
├── 📁 ui/                        # Kullanıcı arayüzü
│   ├── main_window.py            # Ana pencere
│   ├── customer_tab.py           # Müşteri yönetimi
│   ├── service_tab.py            # Servis işlemleri
│   ├── stock_tab.py              # Stok yönetimi
│   ├── billing_tab.py            # Faturalama
│   ├── invoicing_tab.py          # Fatura detayları
│   ├── cpc_tab.py                # CPC sayaç yönetimi
│   ├── quotes_tab.py             # Teklif yönetimi
│   ├── dashboard_tab.py          # Ana panel
│   ├── settings_tab.py           # Ayarlar
│   ├── ai_tab.py                 # AI asistan
│   └── 📁 dialogs/               # Dialog pencereleri (45+ dialog)
│       ├── customer_dialog.py
│       ├── service_dialog.py
│       ├── quote_form_dialog.py
│       └── ...
│
├── 📁 utils/                     # Yardımcı modüller
│   ├── config.py                 # Yapılandırma
│   ├── pdf_generator.py          # PDF oluşturma
│   ├── email_generator.py        # E-posta şablonları
│   ├── system_notifier.py        # E-posta gönderimi
│   ├── settings_manager.py       # Ayar yönetimi
│   ├── sync_manager.py           # Senkronizasyon
│   ├── auto_backup.py            # Otomatik yedekleme
│   ├── currency_converter.py     # Döviz kuru
│   ├── validator.py              # Veri doğrulama
│   ├── error_logger.py           # Hata kayıt
│   ├── ai_providers.py           # AI entegrasyonu
│   └── 📁 database/              # Veritabanı işlemleri
│
├── 📁 resources/                 # Kaynaklar
│   ├── 📁 fonts/                 # DejaVu fontları (9 dosya)
│   └── logo.png                  # Uygulama logosu
│
├── 📁 credentials/               # Şifreli kimlik bilgileri
│   └── azure_sql_creds.enc
│
├── 📁 dist/                      # Build çıktıları
│   └── ProServis.exe             # Tek dosya EXE (130 MB)
│
└── 📁 installer_output/          # Installer çıktıları
    └── ProServis_v2.3.0_Setup.exe
```

---

## 🔒 Güvenlik

| Özellik | Açıklama |
|---------|----------|
| 🔐 Şifre Hash | Bcrypt algoritması ile güvenli saklama |
| 👤 Rol Tabanlı | Admin ve kullanıcı yetki ayrımı |
| 💾 Yerel DB | SQLite, internet bağlantısı gerektirmez |
| 🔑 Şifreleme | Hassas bilgiler için AES şifreleme |
| 📧 App Password | Gmail 2FA ile güvenli e-posta |

---

## 🐛 Sorun Giderme

### Veritabanı Hatası
```
Hata: database is locked
Çözüm: Uygulamayı kapatın, gerekirse PC'yi yeniden başlatın
```

### PDF Yazdırma Hatası
```
Hata: PyMuPDF bulunamadı
Çözüm: pip install pymupdf
```

### E-posta Gönderilmiyor
```
Hata: SMTP authentication failed
Çözüm: Gmail App Password kullanın, 2FA aktif olmalı
```

### Font Hatası
```
Hata: Font dosyası bulunamadı
Çözüm: resources/fonts/ klasöründe DejaVu fontlarının olduğunu kontrol edin
```

---

## 📞 İletişim

| Kanal | Bilgi |
|-------|-------|
| 👤 Geliştirici | Ümit Sağdıç |
| 📧 E-posta | proservisteknoloji@gmail.com |
| 🐙 GitHub | [umitsagdic77-ai](https://github.com/umitsagdic77-ai) |
| 📦 Repository | [ProServis_Proje](https://github.com/umitsagdic77-ai/ProServis_Proje) |

---

## 📝 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

| Kütüphane | Kullanım |
|-----------|----------|
| [PyQt6](https://pypi.org/project/PyQt6/) | Modern UI framework |
| [SQLite](https://sqlite.org/) | Veritabanı |
| [ReportLab](https://reportlab.com/) | PDF oluşturma |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF render ve yazdırma |
| [Bcrypt](https://pypi.org/project/bcrypt/) | Şifre güvenliği |
| [Pandas](https://pandas.pydata.org/) | Veri işleme |

---

## 📋 Sürüm Geçmişi

### v2.3.0 (6 Aralık 2025) - Güncel
- ✅ **Tek Dosya EXE Build** - Tüm bağımlılıklar dahil (130 MB)
- ✅ **PyMuPDF Entegrasyonu** - Doğrudan yazıcıya yazdırma
- ✅ **Gömülü E-posta Sistemi** - Gmail SMTP ile otomatik bildirimler
- ✅ **Font Desteği** - DejaVu fontları dahil
- ✅ **Inno Setup Installer** - Windows kurulum paketi
- ✅ **collect_all() ile Build** - PyMuPDF tam entegrasyonu

### v2.2.0 (4 Kasım 2025)
- ✅ Servis iş geçmişi raporlama sistemi
- ✅ Gerçek servis tamamlanma süreleri
- ✅ Dashboard fatura görüntüleme düzeltildi
- ✅ Otomatik yedekleme sistemi
- ✅ CSV import/export optimizasyonu (10x performans)
- ✅ PDF rapor oluşturma hataları düzeltildi
- ✅ Modüler kod yapısı

### v2.0.0 (17 Ekim 2025)
- 🎉 PyQt6 tabanlı modern arayüz
- 🎉 SQLite yerel veritabanı
- 🎉 Müşteri, cihaz, servis, stok yönetimi
- 🎉 Rol tabanlı yetkilendirme
- 🎉 PDF raporlama sistemi

---

<div align="center">

**ProServis** © 2025 Ümit Sağdıç. Tüm hakları saklıdır.

Made with ❤️ in Turkey

</div>

