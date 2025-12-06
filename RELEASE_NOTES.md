# 📝 ProServis v2.2 Release Notes

## 🎉 Yeni Özellikler

### İlk Kurulum Sihirbazı
- ✅ 6 adımlı kurulum süreci
- ✅ Firma bilgileri otomatik kaydediliyor
- ✅ Veritabanı konumu seçimi
- ✅ İlk admin kullanıcısı oluşturma
- ✅ Lisans veya 15 günlük demo seçeneği
- ✅ Kurulum özeti ve düzenleme imkanı

### Kullanıcı Arayüzü İyileştirmeleri
- ✅ Sade ve modern setup wizard
- ✅ Uygulama ikonu entegrasyonu
- ✅ Sabit pencere boyutu (resize sorunu çözüldü)
- ✅ Minimal progress bar
- ✅ Profesyonel görünüm

### Firma Bilgileri Düzeltmesi
- ✅ Setup wizard'dan girilen bilgiler ana ekranda görünüyor
- ✅ Hem company_info hem settings tablosuna kayıt
- ✅ Ayarlar sekmesinden güncelleme çalışıyor

### Build ve Dağıtım Sistemi
- ✅ PyInstaller spec dosyası
- ✅ Inno Setup script
- ✅ Otomatik build scripti
- ✅ Proje temizleme scripti
- ✅ GitHub hazırlığı
- ✅ Detaylı dokümantasyon

## 🔧 Düzeltmeler

### Kritik Hatalar
- ✅ Firma bilgileri ana ekranda görünmeme sorunu
- ✅ Setup wizard pencere boyutu sorunu
- ✅ Emoji encoding hataları
- ✅ API key validasyon hataları

### Performans
- ✅ Gereksiz dosyalar temizlendi
- ✅ __pycache__ klasörleri silindi
- ✅ Test dosyaları kaldırıldı

## 📦 Dağıtım

### Paket İçeriği
```
ProServis v2.2/
├── ProServis.exe              # Ana uygulama
├── resources/                 # Fontlar (DejaVu Sans)
│   └── fonts/
├── ProServis.ico              # Uygulama ikonu
├── kopier_logo.png            # Firma logosu
├── kyocera logo.png           # Marka logosu
├── README.txt                 # Kullanım kılavuzu
└── [DLL ve bağımlılıklar]
```

### Sistem Gereksinimleri
- **OS:** Windows 10/11 (64-bit)
- **RAM:** 4 GB (minimum)
- **Disk:** 500 MB boş alan
- **Ekran:** 1366x768 (minimum)

### Kurulum Seçenekleri

**1. Installer (Önerilen)**
```
ProServis_v2.2_Setup.exe
- Otomatik kurulum
- Start menü kısayolu
- Desktop ikonu (opsiyonel)
- Kaldırma programı
```

**2. Portable**
```
ProServis_v2.2_Portable.zip
- Kurulum gerektirmez
- USB'den çalıştırılabilir
- Ayarlar yerel klasörde
```

## 🚀 İlk Kullanım

### 1. Kurulum
- Setup.exe'yi çalıştır
- Kurulum sihirbazını takip et

### 2. İlk Çalıştırma
- ProServis'i başlat
- Setup Wizard otomatik açılır

### 3. Firma Bilgileri
- Firma adı, vergi dairesi, vergi no
- Telefon, e-posta, adres

### 4. Veritabanı
- Varsayılan: `C:\Users\[Kullanıcı]\ProServisData`
- Veya özel konum seç

### 5. İlk Kullanıcı
- Admin kullanıcı adı ve şifre
- Güvenli bir şifre seç

### 6. Lisans
- Lisans anahtarı gir
- Veya 15 günlük demo kullan

### 7. Başla!
- Kurulum tamamlandı
- Otomatik giriş yapılır
- Ana ekran açılır

## 📊 Teknik Detaylar

### Teknolojiler
- **Framework:** PyQt6
- **Database:** SQLite3
- **PDF:** ReportLab
- **Security:** bcrypt
- **Build:** PyInstaller
- **Installer:** Inno Setup

### Veritabanı
- **Konum:** Kullanıcı seçimine göre
- **Format:** SQLite (.db)
- **Yedekleme:** Otomatik (6 saatte bir)
- **Migration:** Otomatik

### Güvenlik
- ✅ Şifre hash (bcrypt)
- ✅ SQL injection koruması
- ✅ Input validasyonu
- ✅ Güvenli dosya işlemleri

## 🔄 Güncelleme

### v2.1'den v2.2'ye
1. Mevcut veritabanını yedekle
2. v2.2'yi kur
3. İlk açılışta migration otomatik çalışır
4. Firma bilgilerini kontrol et

### Veri Taşıma
- Veritabanı dosyası: `teknik_servis_local.db`
- Yedekler: `backups/` klasörü
- Ayarlar: `app_config.json`

## 📝 Bilinen Sorunlar

### Düşük Öncelikli
- [ ] PDF'de bazı Türkçe karakterler (font sorunu)
- [ ] Büyük veritabanlarında yavaşlama (>10000 kayıt)

### Çözümler
- Font: DejaVu Sans kullanılıyor
- Performans: Sayfalama eklendi

## 🎯 Gelecek Sürümler

### v2.3 (Planlanan)
- [ ] Cloud backup (Google Drive, Dropbox)
- [ ] Mobil uygulama (Android)
- [ ] WhatsApp entegrasyonu
- [ ] QR kod ile cihaz takibi
- [ ] Gelişmiş raporlama

### v3.0 (Uzun Vadeli)
- [ ] Multi-tenant (çoklu firma)
- [ ] Web arayüzü
- [ ] API desteği
- [ ] Otomatik güncelleme

## 📞 Destek

### İletişim
- **E-posta:** umitsagdic77@gmail.com
- **GitHub:** [Repository URL]

### Dokümantasyon
- `README.md` - Genel bilgi
- `ILKKURULUM.md` - İlk kurulum rehberi
- `BUILD.md` - Build rehberi
- `DEPLOYMENT.md` - Dağıtım rehberi

### Sorun Bildirme
1. GitHub Issues kullanın
2. Hata mesajını ekleyin
3. Log dosyasını paylaşın (`logs/app.log`)
4. Adımları açıklayın

## 📄 Lisans

Bu yazılım lisanslıdır. Kullanım koşulları için `LICENSE` dosyasına bakınız.

## 🙏 Teşekkürler

ProServis'i kullandığınız için teşekkürler!

---

**Sürüm:** 2.2  
**Tarih:** 27 Ekim 2025  
**Build:** 2025.10.27
