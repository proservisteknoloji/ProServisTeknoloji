# ProServis Teknisyen Android (Sprint-1)

Bu klasor, revize plana gore Android teknisyen uygulamasinin ilk calisan iskeletini icerir.

## Kapsam
- Login (`tenantId + email + sifre`) ve tenant uyelik dogrulamasi
- Session saklama (DataStore)
- Iki sekmeli is ekrani:
  - Acik Havuz (service + technician task birlesik)
  - Uzerimdeki Isler
- Is sahiplen / isi birak aksiyonlari
- Service/task event yazimi (`CLAIM`, `RELEASE`)
- Compose + MVVM + Repository + Hilt + Firebase

## Dosya Yapisi
- `app/src/main/java/com/proservis/technician/data/`
- `app/src/main/java/com/proservis/technician/domain/`
- `app/src/main/java/com/proservis/technician/ui/`
- `app/src/main/java/com/proservis/technician/navigation/`
- `app/src/main/java/com/proservis/technician/di/`

## Kurulum
1. Bu klasoru Android Studio ile ac.
2. Firebase projesi baglantisini yap ve `app/google-services.json` dosyasini koy.
3. Firebase Auth icin Email/Password provider acik olsun.
4. Firestore kurallarinda tenant izolasyonu ve `tenants/{tenantId}/users/{uid}` okuma izni olsun.
5. Gradle sync yapip uygulamayi calistir.

## Not
- Bu ortamda `gradle` araci kurulu olmadigi icin CLI ile derleme komutu calistirilmadi.
- Build/Run Android Studio uzerinden yapilmalidir.

## Sonraki Sprint
- MUSTERIYE_GELDIM ve seri dogrulama ekrani
- Is tamamlama formu
- Meter reading tamamlamasi
- Daha sik rules ve alan bazli update kisitlari

