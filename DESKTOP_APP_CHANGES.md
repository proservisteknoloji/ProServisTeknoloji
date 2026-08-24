# 🖥️ Masaüstü Uygulaması (PyQt6) - Değişiklik Sayfası

## 📋 Yapılan Değişiklikler Özeti

### 1. Veritabanı Şema (utils/database/connection.py)

**Eklenen Alanlar:**

```python
# second_hand_devices tablosuna
- customer_id: INTEGER (müşteri UID'sini saklamak için)

# customer_devices tablosuna
- has_maintenance_contract: INTEGER DEFAULT 0
- maintenance_period: TEXT DEFAULT 'Aylık' (Aylık/3 Aylık/6 Aylık/Yıllık)
- last_maintenance_date: TEXT
- next_maintenance_date: TEXT
- maintenance_price: DECIMAL(12,4) DEFAULT 0
- maintenance_currency: TEXT DEFAULT 'TL'
```

**Otomatik Migration:** Uygulamayı başlattığınızda otomatik migration çalışacak.

---

### 2. Stok Sekmesi (ui/stock_tab.py) - 2. EL CİHAZLAR

#### 2.1 UID Yerine Müşteri Adı Gösterimi

**Satır 1918-1929: SQL JOIN ile güncelleme**

```python
# ÖNCE (UID gösteriyordu):
SELECT id, device_model, serial_number, source_person, ...
FROM second_hand_devices

# SONRA (Müşteri adı gösteriyor):
SELECT shd.id, shd.device_model, shd.serial_number,
       COALESCE(c.name, shd.source_person) as source_person,
       ...
FROM second_hand_devices shd
LEFT JOIN customers c ON c.id = shd.customer_id
```

**Sonuç:** "Alınan Kişi/Kurum" sütununda artık müşteri adı görülecek.

---

#### 2.2 "Düzenle" Butonu Eklendi

**Satır 195: Yeni buton**

```python
self.edit_second_hand_btn = QPushButton("✏️ Düzenle")
```

**Satır 245 & 290: Button layouta ve signal'e eklendi**

```python
btn_layout.addWidget(self.edit_second_hand_btn)
self.edit_second_hand_btn.clicked.connect(self.edit_second_hand_device_from_button)
```

**Fonksiyon (Satır 2369-2379):**

```python
def edit_second_hand_device_from_button(self):
    """Edit butonu tıklandığında seçili cihazı düzenle."""
    selected_row = self.second_hand_table.currentRow()
    if selected_row < 0:
        QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir cihaz seçin.")
        return
    self.edit_second_hand_device(self.second_hand_table.item(selected_row, 0))
```

**Aktivasyon:** Cihaz seçildiğinde otomatik aktif/pasif.

---

#### 2.3 "Geçmiş Görüntüle" Butonu Eklendi

**Satır 196: Yeni buton**

```python
self.history_second_hand_btn = QPushButton("📋 Geçmiş Görüntüle")
```

**Satır 248 & 290: Button layouta ve signal'e eklendi**

```python
btn_layout.addWidget(self.history_second_hand_btn)
self.history_second_hand_btn.clicked.connect(self.show_second_hand_device_history)
```

**Fonksiyon (Satır 2381-2453):**

Aşağıdaki bilgileri gösteren diyalog açar:
- Cihaz Model
- Seri No
- Mevcut Durum
- Alınan Kişi/Kurum (Müşteri Adı!)
- Alınma Tarihi
- Alış Fiyatı
- Satış Fiyatı
- **Tüm Geçmiş & Notlar** (TextEdit'de)

---

#### 2.4 Düzenleme Diyaloğunda Müşteri Adı Gösterimi

**Satır 2203-2230:** SQL ve diyalog güncellendi

```python
# SQL JOIN kullanarak customer_name çekiliyor:
SELECT shd.id, shd.device_model, shd.serial_number, shd.customer_id, ...,
       c.name as customer_name
FROM second_hand_devices shd
LEFT JOIN customers c ON c.id = shd.customer_id

# Diyalogda gösteriliyor:
source_input = QLineEdit(device['customer_name'] or device['source_person'] or "")
```

**Sonuç:** "Alınan Kişi/Kurum" alanında UID yerine müşteri adı gösterilecek.

---

### 3. Müşteri Sekmesi (ui/customer_tab.py) - 2. EL DEPOYA TAŞIMA

**Satır 777 & 789-797:** customer_id kaydediliyor

```python
# customer_id eklendi:
data = {
    'device_model': device_info['device_model'],
    'serial_number': device_info['serial_number'],
    'source_person': device_info['customer_name'],
    'customer_id': device_info.get('customer_id'),  # YENİ
    ...
}

# INSERT query'ye eklendi:
INSERT INTO second_hand_devices
(device_model, serial_number, source_person, customer_id, ...)  # customer_id ekle
VALUES (?, ?, ?, ?, ...)
```

**Sonuç:** Müşteri cihazı 2. el depoya taşırken, müşteri ID'si otomatik kaydedilecek.

---

## 🧪 Test Prosedürü

### Test 1: UID → Müşteri Adı Dönüşümü

```
1. Masaüstü uygulamasını aç
2. Müşteri sekmesine git
3. Bir müşteri seç (örn: "Ahmet Yılmaz")
4. Müşteri cihazlarından bir tane seç
5. Sağ tıkla → "2. El Depoya Taşı"
6. İşlemi tamamla
7. Stok sekmesine git → "2. El Cihazlar" sekmesine git
8. ✅ "Alınan Kişi/Kurum" sütununda "Ahmet Yılmaz" görülmeli (UID değil)
```

### Test 2: Düzenle Butonu

```
1. Stok sekmesi → "2. El Cihazlar" sekmesine git
2. Listede bir cihaz seç
3. ✏️ "Düzenle" butonu aktif olmalı
4. Tıkla → Düzenleme diyaloğu açılmalı
5. "Alınan Kişi/Kurum" alanında müşteri adı görülmek (UID değil)
6. Bilgileri güncelle → Kaydet
7. ✅ Liste yenilenmeli, değişiklikler görülmeli
```

### Test 3: Geçmiş Görüntüle

```
1. Stok sekmesi → "2. El Cihazlar" sekmesine git
2. Listede bir cihaz seç
3. 📋 "Geçmiş Görüntüle" butonu aktif olmalı
4. Tıkla → Diyalog açılmalı
5. ✅ Cihaz detayları ve tüm geçmiş görülmeli:
   - Cihaz Model
   - Seri No
   - Mevcut Durum
   - Alınan Kişi/Kurum
   - Alınma Tarihi
   - Fiyatlar
   - Tüm Geçmiş & Notlar
```

### Test 4: SQL Query Doğrulama

1. SQLite veritabanına bağlan:
   ```bash
   sqlite3 C:\path\to\teknik_servis.db
   ```

2. Query çalıştır:
   ```sql
   SELECT shd.device_model, COALESCE(c.name, shd.source_person) as source_person
   FROM second_hand_devices shd
   LEFT JOIN customers c ON c.id = shd.customer_id
   LIMIT 5;
   ```

3. ✅ `source_person` kolonu müşteri adlarını göstermeli

---

## 📂 Değiştirilen Dosyalar

| Dosya | Satırlar | Değişiklik |
|-------|---------|-----------|
| `utils/database/connection.py` | 622-631 | DB migration - 2 field group |
| `ui/customer_tab.py` | 777, 789-797 | customer_id kaydı |
| `ui/stock_tab.py` | 1918-1943 | SQL JOIN, müşteri adı |
| `ui/stock_tab.py` | 195-250 | Edit + History butonları |
| `ui/stock_tab.py` | 2203-2285 | Düzenleme diyaloğu + JOIN |
| `ui/stock_tab.py` | 2369-2453 | Geçmiş diyaloğu fonksiyonu |
| `ui/stock_tab.py` | 2381-2394 | Button aktivasyon |

---

## 🔧 Bakım Anlaşmaları - Gelecek Fazlar

Veritabanı şeması hazırlandı, UI implementasyonu yapılacaktır:

### Dashboard (TODO)
- Bakım zamanı **geçen** cihazlar kartı (⚠️ Uyarı)
- Bakım zamanı **yaklaşan** cihazlar kartı (⏰ 1 hafta)

### Faturalandırma (TODO)
- Bakım periyoduna göre otomatik fatura oluşturma
- Bakım bedelinin invoices'a eklenmesi

---

## 📊 Git Commit Hazırlığı

Aşağıdaki komutları çalıştırın:

```bash
cd C:\Users\umits\Desktop\ProservisProje_web_compile

# Değişiklikleri kontrol et
git status

# Staging için dosyaları seç
git add ui/stock_tab.py
git add ui/customer_tab.py
git add utils/database/connection.py

# Commit yap
git commit -m "Stok yönetimi üyeleştirmeleri: UID → Müşteri Adı, 2. El Cihaz UI Butonları"

# Push et
git push origin main

# Versiyon tag'ı (opsiyonel)
git tag -a v2.1.0 -m "UID yerine müşteri adı, 2. El cihaz edit/history butonları"
git push origin v2.1.0
```

---

## ✅ Deployment Kontrol Listesi

Üretim ortamında yapmadan önce:

- [ ] Veritabanı backup alındı
- [ ] Local test tamamlandı (tüm test prosedürleri)
- [ ] Kod changeset gözden geçirildi
- [ ] Git commit + push yapıldı
- [ ] Başka geliştirici tarafından onaylanmış

---

## 🚨 Hata Durumunda

### Rollback
```bash
git revert <commit-hash>
# veya
git reset --hard HEAD~1
```

### Veritabanı Geri Dönüş
```bash
cp C:\Backup\teknik_servis_YYYYMMDD.db C:\path\to\teknik_servis.db
```

---

## 📞 Notlar

1. **Migration Otomatik:** Uygulamayı çalıştırdığınızda `_add_column_if_not_exists()` otomatik olarak gerekli alanları ekleyecek.

2. **Backward Compatibility:** Mevcut veriler etkilenmez. Boş alanlar default değerle doldurulur.

3. **Customer ID:** Yeni 2. El cihazlara customer_id otomatik kaydedilir. Eski verilerde NULL olabilir (sorunu yoktur).

4. **SQL JOIN:** LEFT JOIN kullanıldığı için, customer_id NULL olan kayıtlarda source_person değeri gösterilecek (fallback).

