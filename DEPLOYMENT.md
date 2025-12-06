# 🚀 ProServis Deployment Rehberi

## 📋 İçindekiler
1. [Proje Temizleme](#proje-temizleme)
2. [GitHub'a Yükleme](#githuba-yükleme)
3. [EXE Build](#exe-build)
4. [Installer Oluşturma](#installer-oluşturma)
5. [Dağıtım](#dağıtım)

---

## 1️⃣ Proje Temizleme

### Otomatik Temizlik
```bash
python cleanup_project.py
```

### Manuel Kontrol
```bash
# Silinmesi gerekenler:
- Test dosyaları (test_*.py, *_test.pdf)
- __pycache__ klasörleri
- *.pyc dosyaları
- Geçici dosyalar (*.tmp, *.temp)
- Credentials klasörü
- *.db dosyaları
```

---

## 2️⃣ GitHub'a Yükleme

### İlk Kurulum
```bash
cd c:\Users\TeknikServisPC\Projeler\teknik_servis_projesi_final-main

# Git başlat
git init

# Kullanıcı bilgileri
git config user.name "İsminiz"
git config user.email "email@example.com"

# Remote ekle
git remote add origin https://github.com/KULLANICI_ADI/proservis.git
```

### Yükleme
```bash
# Tüm dosyaları ekle
git add .

# Commit
git commit -m "v2.2: Setup wizard ve build sistemi"

# Push
git push -u origin main
```

**Detaylı bilgi:** `GITHUB_PUSH.md`

---

## 3️⃣ EXE Build

### Gereksinimler
```bash
pip install pyinstaller
pip install -r requirements.txt
```

### Build
```bash
# Otomatik build
python build_exe.py

# Manuel build
pyinstaller --clean ProServis.spec
```

### Çıktı
```
dist/
└── ProServis/
    ├── ProServis.exe          ← Ana uygulama
    ├── resources/             ← Fontlar
    ├── ProServis.ico
    └── [DLL'ler ve bağımlılıklar]
```

**Detaylı bilgi:** `BUILD.md`

---

## 4️⃣ Installer Oluşturma

### Inno Setup Kurulumu
1. İndir: https://jrsoftware.org/isdl.php
2. Kur (varsayılan ayarlar)

### Installer Build
1. `ProServis_Setup.iss` dosyasını aç
2. Build → Compile
3. Çıktı: `installer_output/ProServis_v2.2_Setup.exe`

### Installer Özellikleri
- ✅ Otomatik kurulum
- ✅ Desktop kısayolu (opsiyonel)
- ✅ Start menü kısayolu
- ✅ Kaldırma programı
- ✅ Türkçe arayüz

---

## 5️⃣ Dağıtım

### Portable Versiyon (Zip)
```powershell
# PowerShell
Compress-Archive -Path dist\ProServis -DestinationPath ProServis_v2.2_Portable.zip
```

**İçerik:**
- ProServis.exe
- Tüm DLL'ler
- resources/ klasörü
- README.txt

**Kullanım:**
1. Zip'i aç
2. ProServis.exe'yi çalıştır
3. İlk kurulum sihirbazı açılır

### Installer Versiyonu
```
installer_output/ProServis_v2.2_Setup.exe
```

**Kullanım:**
1. Setup.exe'yi çalıştır
2. Kurulum sihirbazını takip et
3. Kurulum tamamlandığında başlat

---

## 📦 Dağıtım Kontrol Listesi

### Build Öncesi
- [ ] Proje temizlendi (cleanup_project.py)
- [ ] requirements.txt güncel
- [ ] ProServis.spec güncel
- [ ] ProServis_Setup.iss güncel
- [ ] Sürüm numarası güncellendi

### Build
- [ ] build_exe.py başarılı
- [ ] dist/ProServis/ProServis.exe çalışıyor
- [ ] Tüm kaynaklar mevcut (fonts, icons)
- [ ] İlk kurulum sihirbazı test edildi

### Test
- [ ] Temiz bilgisayarda test edildi
- [ ] İlk kurulum çalışıyor
- [ ] Firma bilgileri kaydediliyor
- [ ] PDF oluşturma çalışıyor
- [ ] Veritabanı oluşturuluyor
- [ ] Tüm özellikler çalışıyor

### Installer
- [ ] Inno Setup derlemesi başarılı
- [ ] Installer test edildi
- [ ] Kaldırma test edildi
- [ ] Desktop ikonu çalışıyor

### Dağıtım
- [ ] Portable zip oluşturuldu
- [ ] Installer oluşturuldu
- [ ] README dosyaları eklendi
- [ ] Sürüm notları hazırlandı

---

## 🎯 Hızlı Başlangıç

### Tüm Süreci Tek Seferde
```bash
# 1. Temizle
python cleanup_project.py

# 2. Build
python build_exe.py

# 3. Test
cd dist\ProServis
ProServis.exe

# 4. Installer (Inno Setup'ta)
# ProServis_Setup.iss → Compile

# 5. Dağıt
# installer_output/ProServis_v2.2_Setup.exe
```

---

## 🔧 Sorun Giderme

### Build Hataları
```bash
# ModuleNotFoundError
pip install [eksik_modul]

# DLL Eksik
# Windows System32'den kopyala
```

### Installer Hataları
```bash
# Inno Setup bulunamadı
# PATH'e ekle: C:\Program Files (x86)\Inno Setup 6
```

### Runtime Hataları
```bash
# Terminal açılıyor
# ProServis.spec → console=False

# Font bulunamadı
# resources/ klasörünü kontrol et
```

---

## 📊 Dosya Boyutları

| Dosya | Boyut (yaklaşık) |
|-------|------------------|
| ProServis.exe | ~50 MB |
| dist/ProServis/ | ~150 MB |
| Portable.zip | ~80 MB |
| Setup.exe | ~85 MB |

---

## 📧 Destek

**Sorular için:**
- E-posta: umitsagdic77@gmail.com
- GitHub Issues

**Dokümantasyon:**
- BUILD.md - Detaylı build rehberi
- GITHUB_PUSH.md - Git komutları
- ILKKURULUM.md - Kullanıcı kurulum rehberi

---

## ✅ Son Kontrol

Build tamamlandıktan sonra:

1. ✅ ProServis.exe çalışıyor
2. ✅ İlk kurulum sihirbazı açılıyor
3. ✅ Firma bilgileri kaydediliyor
4. ✅ Ana ekranda firma adı görünüyor
5. ✅ PDF oluşturma çalışıyor
6. ✅ Veritabanı oluşturuluyor
7. ✅ Tüm sekmeler açılıyor
8. ✅ Installer çalışıyor
9. ✅ Kaldırma çalışıyor
10. ✅ Temiz bilgisayarda test edildi

**Hepsi tamam mı? Dağıtıma hazırsınız! 🚀**
