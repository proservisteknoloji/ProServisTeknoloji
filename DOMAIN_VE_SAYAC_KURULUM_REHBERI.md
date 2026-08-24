# ProServis - Özel Alan Adı ve Sayaç Sistemi Entegrasyon Protokolü

Bu doküman, kullanıcı Hostinger üzerinden alan adı satın alma işlemini tamamladığında doğrudan devreye girecek olan otomatik kurulum adımlarını içerir.

---

## 📌 Tanımlanan Hedefler

1. **Özel Alan Adı (Custom Domain):** `proservis.com.tr` (veya belirlenen alan adı)
2. **Uygulama Adresi:** `pr.[domain]` veya `app.[domain]` -> Firebase Hosting
3. **Kurumsal Web Sitesi:** `www.[domain]` -> Tanıtım / Web
4. **Sayaç Mail Adresi:** `sayac.[domain]` -> Inbound Mail Webhook (Fotokopi sayaç toplama)
5. **Eski Adres Yönetimi:** `proservislive.web.app` -> `https://pr.[domain]` adresine otomatik **301 Redirect**.

---

## 🛠️ Alan Adı Geldiğinde Uygulanacak İşlem Sırası

### 1. Adım: Firebase Hosting Yapılandırması
- `firebase.json` dosyasına custom domain ve redirect kuralları işlenecek:
  ```json
  {
    "hosting": {
      "redirects": [
        {
          "source": "/:path*",
          "type": 301,
          "destination": "https://pr.ALAN_ADI/:path*"
        }
      ]
    }
  }
  ```
- Firebase CLI & Console üzerinden Custom Domain eklenecek, DNS doğrulama kayıtları (`A` ve `TXT`) alınacak.

### 2. Adım: Hostinger DNS Zone Ayarları
Tarayıcı otomasyonu (`browser_subagent`) ile Hostinger paneline bağlanıp şu kayıtlar girilecek:
- **A Kaydı:** `pr` -> Firebase Hosting IP'leri
- **CNAME:** `www` -> Firebase / Web
- **MX Kaydı:** `sayac` -> Sayaç Inbound Webhook Mail Sunucusu (SendGrid / Mailgun)
- **TXT Kaydı:** Firebase ve SPF/DKIM doğrulamaları

### 3. Adım: Firebase Auth Yetkilendirmesi
- Firebase Authentication -> Settings -> Authorized Domains listesine yeni domain eklenecek.
- `proservislive.web.app` listeden çıkarılarak sadece yeni domainden güvenli giriş sağlanacak.

### 4. Adım: Sayaç Webhook & E-Posta Testi
- `sayac@kopier.com` veya `inbound@sayac.[domain]` adresine test sayaç maili gönderilerek `/api/webhooks/email-inbound` üzerinden cihaz ve sayaç eşleşmesi doğrulanacak.
