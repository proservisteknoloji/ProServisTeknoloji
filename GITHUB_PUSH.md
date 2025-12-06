# GitHub'a Yükleme Rehberi

## 🔄 İlk Kurulum (Eğer repo yoksa)

### 1. GitHub'da Yeni Repo Oluştur
- GitHub.com'a git
- "New repository" tıkla
- İsim: `proservis`
- Public veya Private seç
- README ekleme (zaten var)
- .gitignore ekleme (zaten var)

### 2. Local Repo Başlat
```bash
cd c:\Users\TeknikServisPC\Projeler\teknik_servis_projesi_final-main

# Git başlat (eğer yoksa)
git init

# Kullanıcı bilgilerini ayarla
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Remote ekle (GitHub repo URL'inizi kullanın)
git remote add origin https://github.com/KULLANICI_ADI/proservis.git
```

## 📤 Güncellemeleri Yükle

### Adım 1: Değişiklikleri Ekle
```bash
# Tüm değişiklikleri ekle
git add .

# Veya seçici ekle
git add main.py
git add ui/
git add utils/
git add resources/
git add *.md
git add *.spec
git add *.iss
git add requirements.txt
git add .gitignore
```

### Adım 2: Commit
```bash
git commit -m "v2.2: İlk kurulum sihirbazı ve build sistemi eklendi

- Setup wizard ile ilk kurulum
- Firma bilgileri otomatik kaydediliyor
- PyInstaller spec dosyası
- Inno Setup script
- Build otomasyonu
- Proje temizleme
- Gereksiz dosyalar silindi"
```

### Adım 3: Push
```bash
# İlk push (eğer ilk kez yüklüyorsanız)
git push -u origin main

# Sonraki push'lar
git push
```

## 🔍 Durum Kontrolü

```bash
# Değişiklikleri gör
git status

# Commit geçmişi
git log --oneline

# Remote kontrol
git remote -v
```

## 🌿 Branch Yönetimi (Opsiyonel)

```bash
# Yeni branch oluştur
git checkout -b feature/yeni-ozellik

# Branch'ler arası geçiş
git checkout main

# Branch'leri listele
git branch -a

# Branch'i merge et
git checkout main
git merge feature/yeni-ozellik
```

## 🏷️ Tag ve Release

```bash
# Tag oluştur
git tag -a v2.2 -m "ProServis v2.2 - Setup Wizard"

# Tag'i push et
git push origin v2.2

# Tüm tag'leri push et
git push --tags
```

## 📋 .gitignore Kontrolü

Şu dosyalar/klasörler yüklenmeyecek:
- ✅ __pycache__/
- ✅ *.pyc
- ✅ *.db
- ✅ *.log
- ✅ build/
- ✅ dist/
- ✅ credentials/
- ✅ Test dosyaları

Şu dosyalar yüklenecek:
- ✅ main.py
- ✅ ui/
- ✅ utils/
- ✅ resources/
- ✅ ProServis.ico
- ✅ *.md dosyaları
- ✅ requirements.txt
- ✅ ProServis.spec
- ✅ ProServis_Setup.iss

## 🚨 Önemli Notlar

### Hassas Bilgileri Yükleme!
```bash
# Bu dosyaları ASLA yükleme:
# - API anahtarları
# - Şifreler
# - Veritabanı dosyaları
# - Kullanıcı verileri
# - credentials/ klasörü
```

### İlk Push Sorunları

**"Repository not found" hatası:**
```bash
# Remote URL'i kontrol et
git remote -v

# Yanlışsa düzelt
git remote set-url origin https://github.com/KULLANICI_ADI/proservis.git
```

**"Permission denied" hatası:**
```bash
# SSH key kullan veya Personal Access Token
# GitHub Settings → Developer settings → Personal access tokens
```

**"Failed to push" hatası:**
```bash
# Önce pull yap
git pull origin main --allow-unrelated-histories

# Sonra push
git push origin main
```

## 📦 Büyük Dosyalar

Eğer 100MB'dan büyük dosyalar varsa:
```bash
# Git LFS kullan
git lfs install
git lfs track "*.zip"
git lfs track "*.exe"
git add .gitattributes
```

## ✅ Hızlı Komutlar

```bash
# Tek seferde: add + commit + push
git add .
git commit -m "Güncelleme mesajı"
git push

# Veya kısa yol
git add . && git commit -m "Güncelleme" && git push
```

## 🔄 Güncellemeleri Çek

```bash
# GitHub'dan son değişiklikleri al
git pull origin main
```

## 📧 Destek

Git sorunları için:
- https://git-scm.com/doc
- https://docs.github.com/
