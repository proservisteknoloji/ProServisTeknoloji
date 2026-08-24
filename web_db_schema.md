# Firestore Multi-Tenant Schema Design

Bu belge, ProServis 2.0 projesi için çok kiracılı (multi-tenant) veritabanı yapısını tanımlar.

## 📂 Collections

### 1. `tenants` (Top-level)
Kiracı (Firma) bilgilerini ve abonelik durumunu tutar.
- `id`: Unique Tenant ID
- `companyName`: string
- `subscriptionType`: "monthly" | "yearly" | "unlimited"
- `expiresAt`: Timestamp
- `gracePeriodEnd`: Timestamp (Abonelik süresi + %10)
- `isActive`: boolean
- `adminUid`: string (Sorumlu kullanıcının Firebase Auth ID'si)

### 2. `users` (Top-level)
Tüm kullanıcıların yetki ve kiracı eşleşmelerini tutar.
- `uid`: Firebase Auth UID
- `name`: string
- `email`: string
- `role`: "superadmin" | "admin" | "technician" | "user"
- `tenantId`: string (Superadmin için boş olabilir)

### 3. `customers` (Tenant-scoped)
- `id`: Firestore ID
- `tenantId`: string (Indexing için kritik)
- `name`: string
- `taxId`: string
- `phone`: string
- ... (legacy fields)

### 4. `devices` (Tenant-scoped)
- `id`: Firestore ID
- `tenantId`: string
- `customerId`: string
- `model`: string
- `serialNumber`: string
- ... (legacy fields)

### 5. `serviceRecords` (Tenant-scoped)
- `id`: Firestore ID
- `tenantId`: string
- `deviceId`: string
- `status`: string
- `technicianId`: string
- ... (legacy fields)

## 🛡️ Security Rules Logic

```javascript
service cloud.firestore {
  match /databases/{database}/documents {
    // Tenant verilerine erişim kuralı
    match /{collectionName}/{docId} {
      allow read, write: if request.auth != null && 
        (resource.data.tenantId == get(/databases/$(database)/documents/users/$(request.auth.uid)).data.tenantId ||
         get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'superadmin');
    }
  }
}
```

---
> [!NOTE]
> Tüm dokümanlarda `tenantId` kullanımı zorunlu tutularak veritabanı seviyesinde izolasyon sağlanacaktır.
