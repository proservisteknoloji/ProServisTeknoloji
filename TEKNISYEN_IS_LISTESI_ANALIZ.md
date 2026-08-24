# Teknisyen İş Listesi – Bildirim Gidiyor Ama İş Listede Görünmüyor

## Özet
Web’de teknisyene atanan iş için Android’e FCM bildirimi gidiyor; ancak atanan iş mobilde “Atanan işler” listesinde görünmüyor. Sebep: **web tarafında bazen atama alanına Firebase Auth UID yerine teknisyen doküman ID’si (custom id) yazılması**; Android ise “bana atanan iş” filtresini **yalnızca Firebase Auth UID ve eşleşen technicianProfileId** ile yapıyor. Bu iki kimlik farklı olduğunda eşleşme olmuyor ve iş listede çıkmıyor.

---

## 1. Akış Özeti

| Adım | Web | Android |
|------|-----|--------|
| Atama | Teknisyen seçilir → `resolveTechnicianUid(tenantId, tech)` → servis kaydına `technicianId` (ve diğer alanlar) yazılır. | — |
| Bildirim | Cloud Functions: `service_records` güncellenince `technicianId` değiştiyse FCM gönderilir. Token `technicianUid` ile bulunur (users veya technicians + email ile). | Bildirim alınır (token e-posta vb. ile bulunabildiği için). |
| Listeleme | — | `observeMyServices(tenantId, uid, email, technicianName, technicianProfileId)` → `belongsToTechnician(assignedId, assignedName, uid, email, technicianName, technicianProfileId)` ile “bana atanan” filtrelenir. |

- **Web’in yazdığı değer:** `resolveTechnicianUid` bazen **Firebase Auth UID** (tenants/xxx/users içindeki kullanıcı doc id), bazen de **teknisyen doküman id’si** (tenants/xxx/technicians doc id) döndürüyor.
- **Android’in kullandığı “ben” kümesi:** `uid` (Firebase Auth), `technicianProfileId` (teknisyen doküman id veya uid), `email`, `technicianName` (normalize edilmiş).
- **Eşleşme:** Servisteki `assignedId` (Firestore’daki technicianId vb.) bu “ben” kümesinde yoksa iş “Atanan işler”de görünmüyor.

---

## 2. Neden–Sonuç İlişkisi

### 2.1 Bildirim neden gidiyor?
- FCM token’ı Cloud Functions tarafında `technicianUid` (yani servise yazılan `technicianId`) ile aranıyor.
- Token hem `tenants/{tenantId}/users/{technicianUid}` hem de `tenants/{tenantId}/technicians/{technicianUid}` ve e-posta ile eşleşen user üzerinden okunabiliyor.
- Yani `technicianId` ister UID ister teknisyen doc id olsun, e-posta ile user bulunup token alınabildiği için bildirim gidebiliyor.

### 2.2 İş neden listede görünmüyor?
- Android “bana atanan” hesabı **sadece** şu küme ile yapıyor:  
  `{ uid, technicianProfileId, email, technicianName }` (ve normalize/loose varyantları).
- **Web, kullanıcı bulunamadığında** `resolveTechnicianUid` içinde son satırda `return technician.id` yapıyor.  
  Bu durumda servise **teknisyen koleksiyonundaki doküman id’si** (örn. Firestore otomatik id) yazılıyor.
- Android’de aynı kullanıcı giriş yaptığında:
  - `uid` = Firebase Auth UID (her zaman bu).
  - `technicianProfileId` = önce `technicians/{uid}` aranır; yoksa e-posta / loginId / isimle teknisyen doc bulunur ve **o dokümanın id’si** alınır.
- Senaryo:
  - Web’de teknisyen kaydı **uid ile değil, custom/otomatik id** ile (örn. `technicians/abc123xyz`).
  - Aynı kişi için `tenants/xxx/users/{uid}` var (mobil giriş veya admin ile oluşturulmuş).
  - Web’de atama yapılırken `resolveTechnicianUid`:
    - `tenants/xxx/users/abc123xyz` yok (abc123xyz teknisyen doc id),
    - E-posta ile user aranır; bazen farklı yazım / boş email / farklı koleksiyon kullanımı vb. yüzünden user bulunamaz,
    - En sonda `return technician.id` → **abc123xyz** döner.
  - Servise `technicianId = "abc123xyz"` yazılır.
  - Android’de:
    - `technicians/{uid}` çoğu zaman yok (çünkü teknisyen doc id `abc123xyz`).
    - E-posta ile teknisyen bulunamazsa (veya farklı normalizasyon) `resolveTechnicianProfileId` **uid** döndürür.
    - Sonuç: `technicianProfileId = uid`, `assignedId = "abc123xyz"`.
  - `belongsToTechnician(assignedId="abc123xyz", ..., uid, technicianProfileId=uid)` → aliases’ta sadece uid var, "abc123xyz" yok → **eşleşme yok** → iş “Atanan işler”de görünmüyor.

Yani **tek sebep**: Web’in bazen **Firebase Auth UID yerine teknisyen doküman id’sini** servise yazması; Android’in ise “ben” olarak **uid + technicianProfileId** (ve email/name) kullanması. İki tarafta kimlik tutarlı olmadığı için liste filtresi işi “bana atanmış” saymıyor.

---

## 3. Çözüm Yolu (Net ve Kesin)

### 3.1 Ana kural
- **Servis / görev atama alanlarında (technicianId, technicianUid, assignedToUid vb.) her zaman yalnızca “tenants/{tenantId}/users” içinde gerçekten var olan bir kullanıcı doc id’si (Firebase Auth UID) yazılmalı.**  
  Böylece Android tarafındaki `uid` ve (uygun olduğunda) `technicianProfileId` ile bire bir eşleşir; iş her zaman “Atanan işler”de çıkar.

### 3.2 Web tarafı (zorunlu)
- **`resolveTechnicianUid`** içinde:
  - E-posta, loginId, isim ve “tüm users” döngüsü denendikten sonra **hiçbir user bulunamazsa** artık `return technician.id` **yapılmamalı**.
  - Bunun yerine **boş string döndürülmeli** (veya net bir hata fırlatılmalı).
- **Teknisyen atama UI** (ör. Teknisyenler sayfası):
  - `resolvedUid` boş geldiğinde atama yapılmamalı; kullanıcıya anlamlı bir mesaj gösterilmeli:  
    örn. *“Bu teknisyen için giriş hesabı (kullanıcı) tanımlı değil; atama yapılamaz. Lütfen ayarlardan teknisyenin e-posta/giriş bilgisini kullanıcı ile eşleştirin.”*
- İsteğe bağlı: Teknisyen oluştururken/güncellerken, atama yapılacak teknisyenler için `tenants/{tenantId}/users/{uid}` kaydının (ve gerekirse `technicians/{uid}` veya e-posta uyumlu teknisyen) var olduğunu kontrol eden bir validasyon eklenebilir.

Bu sayede:
- Atama **sadece** “users” ile eşleşen teknisyenlere yapılır.
- Firestore’a **her zaman** Firebase Auth UID yazılır.
- Android’deki `uid` ve `technicianProfileId` (uid veya e-posta ile bulunan doc id) ile tutarlı olur; bildirim gittiği her atanmış iş, “Atanan işler” listesinde de görünür.

### 3.3 Android tarafı (isteğe bağlı sağlamlaştırma)
- Mevcut mantık (uid, technicianProfileId, email, name ile eşleşme) bu düzeltmeden sonra yeterli.
- İleride geri uyumluluk veya ek senaryolar için: `assignedId`, “ben” kümesinde yoksa ve `assignedId` bir teknisyen doküman id’si gibi görünüyorsa, `tenants/{tenantId}/technicians/{assignedId}` dokümanındaki email/loginId/name ile mevcut oturum bilgisi karşılaştırılıp eşleşme varsa “bana atanmış” sayılabilir. Bu ek okuma maliyeti getirir; web düzeltmesi yapıldığında zorunlu değildir.

### 3.4 Kontrol listesi
- [ ] Web: `resolveTechnicianUid` sonunda `technician.id` dönmüyor; user bulunamazsa boş string (veya hata).
- [ ] Web: Atama UI’da `resolvedUid` boşsa atama yapılmıyor ve açıklayıcı mesaj gösteriliyor.
- [ ] Mevcut teknisyenler için: Atama yapılan her teknisyenin e-posta/loginId/name bilgisinin, ilgili `tenants/xxx/users` kaydıyla uyumlu olduğundan emin olunmalı (gerekirse ayarlardan düzeltme).
- [ ] Android: Giriş sonrası `technicianProfileId` ve `uid` doğru dolduruluyor (mevcut akış aynen kullanılabilir).

### 3.5 Android tarafı ek düzeltme (uygulandı)
Web her zaman UID yazsa bile, eski veri veya farklı kod yoluyla serviste teknisyen **doküman id’si** yazılmış olabilir. Bu yüzden Android’de “bana atanan” eşleşmesi güçlendirildi:
- Oturum açıldığında, **e-posta / loginId / isim** ile eşleşen tüm teknisyen doküman id’leri yüklenecek.
- `belongsToTechnician` içinde bu id’ler de “ben” aliases’ına eklenecek.
- Böylece Firestore’da `technicianId` = teknisyen doc id yazılmış olsa bile, o id bu kullanıcıya ait teknisyen kaydına aitse iş “Atanan işler”de görünecek.

Bu adımlarla “bildirim gidiyor ama iş listede yok” problemi, neden–sonuç ilişkisine uygun ve kalıcı şekilde giderilmiş olur.
