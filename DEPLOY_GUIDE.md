# 📦 ProServis Projesi - Deploy Kılavuzu

## 📊 Yapılan Değişikliklerin Özeti

### 🖥️ Masaüstü Uygulaması (PyQt6)
**Konum:** `c:\Users\umits\Desktop\ProservisProje_web_compile\` (Ana klasör)

| Dosya | Değişiklik | Durum |
|-------|-----------|------|
| `utils/database/connection.py` | Bakım + 2. El cihaz DB şeması | ✅ Yapıldı |
| `ui/stock_tab.py` | 2. El cihaz UI (Edit/History butonu) | ✅ Yapıldı |
| `ui/customer_tab.py` | customer_id kaydı | ✅ Yapıldı |
| `ui/dialogs/stock_dialogs.py` | Stok hareket diyaloğu | ✅ İncelenecek |

**Özellikler:**
- ✅ UID yerine müşteri adı gösterimi
- ✅ 2. El cihaz "Düzenle" butonu
- ✅ 2. El cihaz "Geçmiş Görüntüle" diyaloğu
- ✅ Bakım anlaşması database alanları
- 🔄 Bakım Dashboard kartları (TODO)

---

### 🌐 Web Uygulaması (Next.js/Firebase)
**Konum:** `c:\Users\umits\Desktop\ProservisProje_web_compile\proservis-web\`

| Dosya | Değişiklik | Durum |
|-------|-----------|------|
| `src/types/index.ts` | Device + StockMovement modelleri | ✅ Yapıldı |
| `src/components/customers/EditDeviceDialog.tsx` | Bakım alanları formu | 📝 TODO |
| `src/app/dashboard/stock/page.tsx` | 2. El geçmiş butonu | 📝 TODO |
| `src/components/stock/StockMovementDialog.tsx` | Müşteri adı gösterimi | 📝 TODO |
| `src/app/dashboard/page.tsx` | Bakım kartları | 📝 TODO |
| `WEB_IMPLEMENTATION_GUIDE.md` | Detaylı Impl. Guide | ✅ Yapıldı |

---

## 🚀 Deploy Prosedürü

### AŞAMA 1: Masaüstü Uygulaması (SQLite)

#### 1.1 Veritabanı Backup
```bash
# Masaüstü uygulamasının veritabanını yedekle
cp C:\Users\umits\Desktop\ProservisProje_web_compile\*.db C:\Backup\teknik_servis_$(date +%Y%m%d).db
```

#### 1.2 Kodları Deploy Et
```bash
cd C:\Users\umits\Desktop\ProservisProje_web_compile

# Masaüstü uygulamasını başlat
# → Otomatik migration yapılacak (schema güncellenmesi)
# → Uygulamada çalışabilir hale gelecek
```

#### 1.3 Test Kontrol Listesi

- [ ] **Stok Sekmesi - 2. El Cihazlar:**
  - [ ] Cihaz listesinde "Alınan Kişi/Kurum" sütununda UID yerine müşteri adı görülüyor
  - [ ] ✏️ "Düzenle" butonu seçerken aktif
  - [ ] 📋 "Geçmiş Görüntüle" diyaloğu açılıyor
  - [ ] Geçmiş diyaloğunda cihaz detayları gösteriliyou

- [ ] **Müşteri Sekmesi:**
  - [ ] Müşteri cihazı "2. El Depoya Taşı" işlemi çalışıyor
  - [ ] Customer_id otomatik kaydediliyor

- [ ] **Stok Hareketleri:**
  - [ ] "Alındığı/Verildiği Yer" kısmında UID yerine müşteri adı

#### 1.4 Git Commit ve Push
```bash
cd C:\Users\umits\Desktop\ProservisProje_web_compile

# Değişiklikleri stage et
git add ui/stock_tab.py ui/customer_tab.py utils/database/connection.py

# Commit yap
git commit -m "Stok yönetimi: UID yerine müşteri adı, Edit/History butonu, bakım DB şeması"

# Push et
git push origin main
```

---

### AŞAMA 2: Web Uygulaması (Firebase)

#### 2.1 Type Definitions Kontrol
```bash
cd C:\Users\umits\Desktop\ProservisProje_web_compile\proservis-web

# TypeScript hataları kontrol et
npm run type-check

# Beklenen sonuç: Hata yok
```

#### 2.2 Implementation Adımları

1. **EditDeviceDialog.tsx güncelle** (WEB_IMPLEMENTATION_GUIDE.md'den copy-paste)
2. **stock/page.tsx'e geçmiş butonu ekle**
3. **StockMovementDialog.tsx'de müşteri adı göster**
4. **dashboard/page.tsx'e bakım kartları ekle**

#### 2.3 Build Test
```bash
npm run build

# Başarılı build kontrolü:
# → .next klasörü oluşmuş
# → Hata yok
```

#### 2.4 Local Test
```bash
npm run dev

# Localhost:3000'de açıp test et
# Kontrol listesi:
# ✓ Cihaz İşlemleri → Bakım Alanları görülüyor
# ✓ 2. El Cihazlar → Geçmiş Butonu görülüyor
# ✓ Stok Hareketleri → Müşteri Adı görülüyor
# ✓ Dashboard → Bakım Kartları görülüyor
```

#### 2.5 Firebase Deploy
```bash
# Ortamı kontrol et
firebase projects:list

# Deploy et
firebase deploy --only hosting

# Firestore rules deploy (gerekirse)
firebase deploy --only firestore:rules

# Cloud Functions deploy (migration script) - Opsiyonel
firebase deploy --only functions:migrateMaintenanceFields
```

#### 2.6 Production Test
- [ ] Web uygulamasını aç (firebase hosting URL)
- [ ] Tüm testler tekrarla
- [ ] Cihaz düzenleme → Bakım alanları kaydediliyor
- [ ] Stok hareketleri → Müşteri adı gösterilmiyor UID gösterilmiyorum
- [ ] 2. El geçmiş → Diyalog açılıyor

---

## 📝 Deployment Checklist

### Masaüstü Uygulaması
- [ ] Backup alındı
- [ ] Kod güncellemeleri yapıldı
- [ ] Test tüm senaryolar başarılı
- [ ] Git commit + push yapıldı
- [ ] Versiyon tag'ı oluşturuldu

### Web Uygulaması
- [ ] Type definitions güncellenmiş
- [ ] EditDeviceDialog güncellenmiş
- [ ] 2. El geçmiş butonu eklenmmiş
- [ ] Stok hareket müşteri adı güncellenmiş
- [ ] Dashboard bakım kartları eklenmmiş
- [ ] npm run type-check: Hata yok
- [ ] npm run build: Başarılı
- [ ] Local test: Tüm features çalışıyor
- [ ] Firebase deploy yapıldı
- [ ] Production test tamamlandı

---

## ⚡ Rollback Prosedürü

### Masaüstü'ye Dönüş
```bash
git revert <commit-hash>
# veya
git reset --hard origin/main
```

### Web'e Dönüş
```bash
# Önceki Firebase hosting sürümü restore et
firebase hosting:clone
```

---

## 📞 Sorun Giderme

### Masaüstü Uygulaması

**Problem:** Migration başarısız
```
→ Çözüm: utils/database/connection.py'de _add_column_if_not_exists kontrolü
→ Veritabanı dosyası bozuk ise backup'dan restore et
```

**Problem:** UID yerine müşteri adı görülmüyor
```
→ Çözüm: SQL JOIN kontrol et (stock_tab.py:1928)
→ Customer ID veritabanında mevcut mi kontrol et
```

### Web Uygulaması

**Problem:** TypeScript error
```bash
→ npm run type-check çıktısını kontrol et
→ Device/StockMovement interface'leri kontrol et
```

**Problem:** Firebase deploy başarısız
```bash
firebase login
firebase projects:list
firebase use <project-id>
firebase deploy
```

**Problem:** Bakım alanları Firestore'da kaydedilmiyor
```
→ EditDeviceDialog'da setValue çağrıları kontrol et
→ CustomerService.updateDevice() methodu kontrol et
→ Firestore security rules kuralları kontrol et
```

---

## 📚 Dokümantasyon

Generated Kılavuzlar:
- `WEB_IMPLEMENTATION_GUIDE.md` - Web app implementation steps
- `web_db_schema.md` - Firestore schema documentation
- `DEPLOY_GUIDE.md` - Bu dosya

