# Sayaç Sistemi Task Listesi

Bu dosya, sayaç sistemini temiz ve hatasiz calisacak hale getirmek icin uygulamaya donuk görev listesi ve kod duzeltme planidir.

## Hedef Kurallar

- Servis tarafinda cihaz sayaç guncellense bile faturalama yapilmadikca ilk faturalama baz alinsin.
- Telemetri okunsa bile sayaç faturalanirken son faturalama baz alinsin.
- Manuel giriste hatali sayaç kaydini azaltmak icin dogrulama ve ikinci onay mekanizmasi olsun.
- Operasyonel cihaz sayaci ile faturalama bazini birbirine karistirma.

## Kod Duzeltme Gorevleri

- [ ] Sayaç veri modelini ayir.
   - `Device.currentCounters` sadece en son cihaz durumunu tutsun.
   - `MeterReading` faturalama kaydi olsun.
   - `TelemetrySnapshot` ham veri olarak kalsin.
   - `ReadingBaseline` fark hesabinda kullanilsin.

- [ ] Faturalama baz secimini tek servise tasi.
   - Ilk faturalama: kurulum sayaci veya ilk onayli okuma.
   - Sonraki faturalamalar: son onayli faturalama baz alinsin.
   - Telemetri veya servis guncellemesi baseline'i otomatik degistirmesin.

- [ ] Telemetri yazimini ayri bir islem olarak kilitle.
   - BW/Renkli/Total alanlarini tek noktada normalize et.
   - Cihaz tipine gore renkli sayaç kurallarini ayir.
   - Yanlis seri eslesmesinde cihaz kaydini ezme.

- [ ] Manuel sayaç giris ekranina iki asamali onay ekle.
   - Ilk asamada alan dogrulama yap.
   - Ikinci asamada mevcut sayac, son faturalama baz ve hesaplanan farki gosteren onay modalı ac.
   - Onay yoksa kaydetme.

- [ ] Geriye giden veya asiri sican sayaclari isaretle.
   - Sayaç azalmasini otomatik kabul etme.
   - Negatif, bos veya tutarsiz degerleri hata olarak isaretle.
   - Otomatik duzeltme yerine inceleme kuyuguna gonder.

- [ ] Audit log ekle.
   - Kim degistirdi, hangi ekrandan degistirdi, eski/yeni deger neydi, neden degisti bilgisi tutulmali.
   - Faturalama baz degisimi ayrica loglansin.

## Dokunulacak Dosyalar

- [ ] [proservis-web/src/services/customerService.ts](proservis-web/src/services/customerService.ts)
   - Telemetri kaydini standardize et.
   - `currentCounters` ve `meterSnapshot` yazim kurallarini ayir.
   - Fallback mantigini sadeleştir.

- [ ] [proservis-web/src/app/api/agent/telemetry/upload/route.ts](proservis-web/src/app/api/agent/telemetry/upload/route.ts)
   - `totalCounter` ile BW/Renkli yorumunu tek kurala bagla.
   - Eslestirme kafasini netlestir.
   - Yanlis cihaz secimi durumunda otomatik ezmeyi engelle.

- [ ] [proservis-web/src/services/billingService.ts](proservis-web/src/services/billingService.ts)
   - `addMeterReading` icinde baseline secimini tek fonksiyona cikar.
   - `updateMeterReading` ve yeni ekleme arasinda faturalama bazini koru.
   - Son faturalama bazini kayda bagla.

- [ ] [proservis-web/src/components/billing/MeterReadingDialog.tsx](proservis-web/src/components/billing/MeterReadingDialog.tsx)
   - Manuel giris validation kurallari ekle.
   - Onay adimi ve uyari ozeti ekle.
   - Kullanici onayi olmadan submit etme.

- [ ] [proservis-web/src/components/billing/EditMeterReadingDialog.tsx](proservis-web/src/components/billing/EditMeterReadingDialog.tsx)
   - Duzenlemede eski ve yeni farki gosteren onizleme ekle.
   - Baseline degistiren alanlari korumali yap.

- [ ] [proservis-web/src/app/dashboard/customers/devices/QuickCounterDialog.tsx](proservis-web/src/app/dashboard/customers/devices/QuickCounterDialog.tsx)
   - Hızli sayaç guncellemede onay ve tutarlilik kontrolu ekle.
   - Bu ekranin faturalama bazini degistirmedigini net ayir.

- [ ] [proservis-web/src/components/technicians/TaskMeterReadingDialog.tsx](proservis-web/src/components/technicians/TaskMeterReadingDialog.tsx)
   - Teknisyen sayac girislerinde ayni validation kurallarini uygula.
   - Task kaydi ile faturalama kaydini birbirinden ayir.

- [ ] [proservis-web/src/services/technicianTrackingService.ts](proservis-web/src/services/technicianTrackingService.ts)
   - Teknisyen kaydini faturalama bazina dogrudan baglama.
   - Görev kaydi ile sayaç kaydini ayrik tut.

## Uygulama Sirasi

1. Baseline servis katmanini yaz.
2. Telemetri yazimini bu servise bagla.
3. Manuel giris ekranina validation ve onay ekle.
4. Faturalama dialoglarinda son baz bilgisini zorunlu goster.
5. Audit log ve inceleme kuyugunu ekle.
6. Geçmis kayitlari tarayip supheli cihazlari raporla.

## Kabul Kriterleri

- Cihaz telemetri ile guncellense bile faturalama bazı degismiyor.
- Ilk faturalama her zaman ilk onayli bazdan hesaplanıyor.
- Sonraki faturalamalar son onayli faturalama bazini kullaniyor.
- Manuel sayaç girisi onaysiz kaydedilmiyor.
- Geri giden veya tutarsiz sayaçlar otomatik olarak kabul edilmiyor.
- Cihaz listesi ve detay ekranlari toplam uretmiyor, sadece anlik durum gosteriyor.

## Not

Bu planin amaci mevcut sistemi sifirlamadan duzeltmek. Temel strateji: yazma noktalarini azalt, baseline'i kilitle, manuel girisi korumali yap, tum degisiklikleri izlenebilir hale getir.