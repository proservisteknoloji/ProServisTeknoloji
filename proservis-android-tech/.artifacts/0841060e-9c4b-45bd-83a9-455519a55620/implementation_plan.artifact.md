# Emülatör Üzerinde Çalıştırma ve Test Planı

Uygulamayı önce emülatör üzerinde, ardından fiziksel cihazınızda test etmek istediğinizi anladım. Şu anda aktif bir cihaz veya emülatör bulunmadığı için mevcut bir emülatörü başlatıp uygulamayı oraya yükleyeceğiz.

## Kullanıcı İncelemesi Gerekenler

> [!IMPORTANT]
> Bilgisayarınızda `Medium_Phone_API_36.1` isimli bir emülatör kayıtlı. Bu emülatörü arka planda başlatacağım. Başlatma işlemi bilgisayarınızın performansına bağlı olarak birkaç dakika sürebilir.

## Önerilen Adımlar

### [Bileşen] Emülatör Yönetimi

- `Medium_Phone_API_36.1` emülatörünü başlatma.
- Emülatörün tamamen açılmasını (boot) bekleme.

---

### [Bileşen] Uygulama Yayını (Deployment)

- Emülatör hazır olduğunda uygulamayı derleyip yükleme (`app` modülü).
- Uygulama açıldıktan sonra giriş ekranını doğrulama.

## Doğrulama Planı

### Otomatik Kontroller
- Emülatörün hazır olup olmadığını `adb` üzerinden kontrol edeceğim.
- Uygulama yüklendikten sonra ekran görüntüsü alarak arayüzü kontrol edeceğim.

### Manuel Doğrulama
- Uygulama emülatörde açıldığında arayüz üzerinden manuel testler yapabilirsiniz.
- Emülatör testleri bittiğinde fiziksel cihazınızı USB ile bağlayarak benzer adımları fiziksel cihaz için uygulayabiliriz.
