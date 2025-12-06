# 🚀 ProServis İlk Kurulum Rehberi

## 📋 İlk Kurulum Senaryosu

ProServis'i ilk kez çalıştırdığınızda otomatik olarak **Kurulum Sihirbazı** açılır.

### ✅ Kurulum Adımları

#### 1️⃣ Hoş Geldiniz Ekranı

**Seçenekler:**
- **🆕 Yeni Müşteriyim:** Tam kurulum yapılır
- **✅ Mevcut Müşteriyim:** Direkt giriş ekranına yönlendirilirsiniz

#### 2️⃣ Firma Bilgileri (Yeni Müşteri)

**Zorunlu Alanlar:**
- Firma Adı
- Vergi Dairesi
- Vergi Numarası
- Telefon
- E-posta

**Opsiyonel:**
- Adres

**Örnek:**
```
Firma Adı: ABC Teknoloji A.Ş.
Vergi Dairesi: Kadıköy
Vergi No: 1234567890
Telefon: 0(212) 123 45 67
E-posta: info@abcteknoloji.com
```

#### 3️⃣ Veritabanı Konumu

**Varsayılan Konum:**
```
C:\Users\[KullanıcıAdı]\ProServisData
```

**Önerilen:**
- Belgelerim klasörü altında
- Yedekleme yapılabilir bir konum
- Yeterli disk alanı olan sürücü

**Gözat Butonu:**
- Farklı bir konum seçebilirsiniz
- Klasör otomatik oluşturulur

#### 4️⃣ İlk Kullanıcı (Admin)

**Zorunlu Alanlar:**
- Kullanıcı Adı (örn: admin)
- Şifre (min. 4 karakter)
- Şifre Tekrar

**Önemli:**
- ⚠️ Bu kullanıcı **tam yetkili admin** olacaktır
- 🔒 Şifrenizi güvenli bir yerde saklayın
- 📝 Unutmayın - şifre kurtarma e-posta ile yapılır

**Örnek:**
```
Kullanıcı Adı: admin
Şifre: ********
Rol: Admin (sabit)
```

#### 5️⃣ Lisans Seçimi

**Seçenekler:**

**A) 🔑 Lisans Anahtarım Var**
- Lisans anahtarınızı girin
- Format: `XXXX-XXXX-XXXX-XXXX`
- Tam sürüm özellikleri aktif olur

**B) 🆓 15 Günlük Demo** (Önerilen)
- Tüm özellikler 15 gün ücretsiz
- Lisans sonra eklenebilir
- Veri kaybı olmaz

**Lisans Satın Alma:**
- E-posta: umitsagdic77@gmail.com

#### 6️⃣ Kurulum Tamamlandı

**Özet Gösterilir:**
- ✅ Firma bilgileri
- ✅ Veritabanı konumu
- ✅ İlk kullanıcı
- ✅ Lisans durumu

**Düzenleme:**
- Her adımı "Düzenle" butonu ile değiştirebilirsiniz

**Bitir:**
- "Bitir ✓" butonuna tıklayın
- Otomatik giriş yapılır
- Ana ekran açılır

---

## 🔄 İlk Kurulumu Sıfırlama

### Test İçin Kurulumu Sıfırlama

Programı ilk kurulum moduna döndürmek için:

**1. Komut Satırından:**
```bash
python main.py --reset-first-run
```

**2. Manuel Olarak:**

**Config Dosyasını Sil:**
```
C:\ProgramData\ProServis\config.json
```
veya
```
[ProgramKlasörü]\data\config.json
```

**İçeriği Düzenle:**
```json
{
  "is_setup_complete": false
}
```

**Veritabanını Sıfırla (Opsiyonel):**
```
C:\Users\[Kullanıcı]\ProServisData\teknik_servis_local.db
```
- Dosyayı silin veya yeniden adlandırın
- Yeni kurulumda otomatik oluşturulur

---

## 🎯 Kurulum Sonrası

### İlk Giriş

**Otomatik Giriş:**
- Kurulum sonrası otomatik giriş yapılır
- Oluşturduğunuz kullanıcı ile

**Manuel Giriş:**
- Kullanıcı adı: [Kurulumda girdiğiniz]
- Şifre: [Kurulumda girdiğiniz]

### Yapılacaklar

**1. Firma Ayarları Kontrolü**
- Ayarlar → Firma Bilgileri
- Logo yükleyin
- Bilgileri güncelleyin

**2. Yapay Zeka API (Opsiyonel)**
- Ayarlar → Yapay Zeka API
- Google Gemini API key ekleyin
- Arıza kodu analizi için

**3. E-posta Ayarları (Opsiyonel)**
- Ayarlar → E-posta Ayarları
- SMTP bilgilerini girin
- Müşterilere otomatik e-posta için

**4. İlk Kayıtlar**
- Müşteri ekleyin
- Cihaz kaydedin
- Servis kaydı oluşturun

---

## ❓ Sık Sorulan Sorular

### Kurulum sırasında hata aldım, ne yapmalıyım?

**Veritabanı Hatası:**
- Seçtiğiniz klasöre yazma izniniz var mı?
- Farklı bir konum deneyin
- Belgelerim klasörünü kullanın

**Kullanıcı Oluşturma Hatası:**
- Kullanıcı adı zaten var mı?
- Farklı bir kullanıcı adı deneyin

### Kurulumu iptal ettim, tekrar başlatabilir miyim?

Evet! Programı kapatıp tekrar açın:
- Kurulum tamamlanmadığı için
- Otomatik olarak Setup Wizard açılır

### Mevcut müşteri seçeneği ne işe yarar?

- Daha önce ProServis kullandıysanız
- Veritabanınız hazırsa
- Direkt giriş ekranına gider
- Kurulum adımları atlanır

### Lisans anahtarı olmadan kullanabilir miyim?

Evet!
- 15 günlük demo seçeneği
- Tüm özellikler aktif
- Süre bitince lisans ekleyebilirsiniz

### Veritabanı konumunu sonra değiştirebilir miyim?

Evet, ama dikkatli:
- Ayarlar → Veritabanı Yönetimi
- Yedek alın
- Yeni konuma taşıyın
- Ayarları güncelleyin

---

## 📞 Destek

**Sorun mu yaşıyorsunuz?**

**E-posta:** umitsagdic77@gmail.com

**Log Dosyaları:**
```
C:\ProgramData\ProServis\logs\app.log
```

**Hata Bildirimi:**
- Hata mesajını kopyalayın
- Log dosyasını ekleyin
- E-posta ile gönderin

---

## ✅ Kurulum Kontrol Listesi

- [ ] Setup Wizard tamamlandı
- [ ] İlk kullanıcı oluşturuldu
- [ ] Veritabanı konumu seçildi
- [ ] Firma bilgileri girildi
- [ ] Lisans durumu belirlendi
- [ ] Başarılı giriş yapıldı
- [ ] Ana ekran açıldı
- [ ] Firma ayarları kontrol edildi
- [ ] İlk müşteri kaydı yapıldı
- [ ] Sistem çalışıyor ✓

---

**ProServis'e hoş geldiniz! 🎉**
