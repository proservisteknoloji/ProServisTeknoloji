# 📱 Teknisyen Mobil Uygulaması Entegrasyon Planı

**Tarih**: 3 Kasım 2025  
**Proje**: ProServis - Teknisyen Mobil Uygulaması  
**Platform**: Android (Flutter/React Native önerisi)

---

## 🎯 Amaç

Teknisyenlerin atanan servis işlerini mobil cihazlarından görüntülemesi, sayaç okumalarını yapması ve iş durumlarını güncellemesi için mobil uygulama entegrasyonu.

---

## 📊 Mevcut Veritabanı Yapısı (Kullanılacak Tablolar)

### 1. **service_records** - Servis İşleri

```sql
- id: INTEGER PRIMARY KEY
- customer_id: INTEGER (Müşteri bilgisi)
- device_id: INTEGER (Cihaz bilgisi)
- technician_id: INTEGER (Atanan teknisyen)
- service_type: TEXT (Bakım/Arıza/Kurulum)
- status: TEXT (Beklemede/Devam Ediyor/Tamamlandı)
- description: TEXT (İş açıklaması)
- created_date: TEXT (İş oluşturma tarihi)
- scheduled_date: TEXT (Planlanan tarih)
- completed_date: TEXT (Tamamlanma tarihi)
- priority: TEXT (Düşük/Orta/Yüksek/Acil)
- notes: TEXT (Teknisyen notları)
```

### 2. **customer_devices** - Müşteri Cihazları

```sql
- id: INTEGER PRIMARY KEY
- customer_id: INTEGER
- device_id: INTEGER
- location_id: INTEGER
- serial_number: TEXT
- installation_date: TEXT
- warranty_end_date: TEXT
- notes: TEXT
```

### 3. **cpc_records** - Sayaç Okuma Kayıtları

```sql
- id: INTEGER PRIMARY KEY
- device_id: INTEGER
- customer_device_id: INTEGER
- reading_date: TEXT
- total_bw: INTEGER (Siyah-beyaz sayfa sayısı)
- total_color: INTEGER (Renkli sayfa sayısı)
- bw_copy: INTEGER
- color_copy: INTEGER
- bw_print: INTEGER
- color_print: INTEGER
- recorded_by: TEXT (Kullanıcı adı)
- notes: TEXT
```

### 4. **devices** - Cihaz Bilgileri

```sql
- id: INTEGER PRIMARY KEY
- brand: TEXT (Marka)
- model: TEXT (Model)
- device_type: TEXT (Yazıcı/Fotokopi)
- color_capability: INTEGER (Renkli/SB)
```

### 5. **customers** - Müşteri Bilgileri

```sql
- id: INTEGER PRIMARY KEY
- name: TEXT
- phone: TEXT
- email: TEXT
- address: TEXT
- company_name: TEXT
```

### 6. **users** - Kullanıcılar (Teknisyenler)

```sql
- id: INTEGER PRIMARY KEY
- username: TEXT
- full_name: TEXT
- email: TEXT
- role: TEXT (admin/technician/user)
- password_hash: TEXT
- is_active: INTEGER
```

---

## 🔧 Gerekli Yeni Veritabanı Değişiklikleri

### 1. **mobile_sessions** Tablosu (Yeni)

Mobil cihaz oturum yönetimi için:

```sql
CREATE TABLE IF NOT EXISTS mobile_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    device_id TEXT NOT NULL,  -- Mobil cihaz UUID
    device_name TEXT,  -- Cihaz modeli (örn: Samsung Galaxy S21)
    session_token TEXT UNIQUE NOT NULL,
    fcm_token TEXT,  -- Firebase Cloud Messaging için
    created_date TEXT NOT NULL,
    last_active TEXT NOT NULL,
    expires_date TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 2. **service_records** Tablosuna Eklenmesi Gerekenler

```sql
-- Konum bilgisi
ALTER TABLE service_records ADD COLUMN location_latitude REAL;
ALTER TABLE service_records ADD COLUMN location_longitude REAL;

-- Teknisyen ulaştığında zaman damgası
ALTER TABLE service_records ADD COLUMN arrived_at TEXT;

-- Fotoğraf ve imza
ALTER TABLE service_records ADD COLUMN photos TEXT;  -- JSON array: ["photo1.jpg", "photo2.jpg"]
ALTER TABLE service_records ADD COLUMN customer_signature TEXT;  -- Base64 encoded image
ALTER TABLE service_records ADD COLUMN technician_signature TEXT;

-- Harcanan süre
ALTER TABLE service_records ADD COLUMN work_duration INTEGER;  -- Dakika cinsinden
```

### 3. **cpc_records** Tablosuna Eklenmesi Gerekenler

```sql
-- Mobil uygulama üzerinden eklendiğini belirtmek için
ALTER TABLE cpc_records ADD COLUMN source TEXT DEFAULT 'desktop';  -- 'desktop' veya 'mobile'
ALTER TABLE cpc_records ADD COLUMN photo_proof TEXT;  -- Sayaç fotoğrafı
```

---

## 🌐 REST API Tasarımı

### API Base URL

```
https://yourdomain.com/api/v1/
```

### 🔐 Kimlik Doğrulama Endpointleri

#### 1. Login

```http
POST /auth/login
Content-Type: application/json

{
    "username": "teknisyen1",
    "password": "şifre123",
    "device_id": "uuid-mobil-cihaz",
    "device_name": "Samsung Galaxy S21",
    "fcm_token": "firebase-token-buraya"
}

Response:
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": 5,
        "username": "teknisyen1",
        "full_name": "Ahmet Yılmaz",
        "role": "technician",
        "email": "ahmet@proservis.com"
    },
    "expires_in": 86400  // 24 saat
}
```

#### 2. Token Yenileme

```http
POST /auth/refresh
Authorization: Bearer {token}

Response:
{
    "success": true,
    "token": "yeni-token",
    "expires_in": 86400
}
```

#### 3. Logout

```http
POST /auth/logout
Authorization: Bearer {token}

Response:
{
    "success": true,
    "message": "Oturum sonlandırıldı"
}
```

---

### 📋 Servis İşleri Endpointleri

#### 1. Teknisyene Atanan İşleri Getir

```http
GET /services/my-jobs
Authorization: Bearer {token}
Query Parameters:
    - status: beklemede|devam_ediyor|tamamlandi (opsiyonel)
    - date_from: 2025-11-01 (opsiyonel)
    - date_to: 2025-11-30 (opsiyonel)

Response:
{
    "success": true,
    "jobs": [
        {
            "id": 123,
            "customer": {
                "id": 45,
                "name": "ABC Şirketi",
                "phone": "+90 532 123 4567",
                "address": "İstanbul, Kadıköy"
            },
            "device": {
                "id": 78,
                "brand": "Kyocera",
                "model": "TASKalfa 3252ci",
                "serial_number": "VPW1234567"
            },
            "service_type": "Bakım",
            "status": "beklemede",
            "priority": "yüksek",
            "description": "Rutin bakım ve toner değişimi",
            "scheduled_date": "2025-11-04T10:00:00",
            "created_date": "2025-11-02T14:30:00",
            "location": {
                "latitude": 40.9923,
                "longitude": 29.0275
            }
        }
    ],
    "total": 15,
    "pending": 8,
    "in_progress": 3,
    "completed": 4
}
```

#### 2. İş Detayını Getir

```http
GET /services/{job_id}
Authorization: Bearer {token}

Response:
{
    "success": true,
    "job": {
        "id": 123,
        "customer": {...},
        "device": {...},
        "service_type": "Bakım",
        "status": "beklemede",
        "priority": "yüksek",
        "description": "Rutin bakım ve toner değişimi",
        "notes": "Teknisyen notları buraya...",
        "scheduled_date": "2025-11-04T10:00:00",
        "created_date": "2025-11-02T14:30:00",
        "completed_date": null,
        "arrived_at": null,
        "work_duration": null,
        "photos": [],
        "customer_signature": null,
        "technician_signature": null,
        "location": {
            "latitude": 40.9923,
            "longitude": 29.0275
        },
        "cpc_history": [
            {
                "reading_date": "2025-10-01",
                "total_bw": 15000,
                "total_color": 5000
            }
        ]
    }
}
```

#### 3. İş Durumunu Güncelle

```http
PUT /services/{job_id}/status
Authorization: Bearer {token}
Content-Type: application/json

{
    "status": "devam_ediyor",  // veya "tamamlandi"
    "notes": "Teknisyen notları",
    "arrived_at": "2025-11-04T10:15:00",  // Opsiyonel
    "work_duration": 45  // Dakika cinsinden, opsiyonel
}

Response:
{
    "success": true,
    "message": "İş durumu güncellendi",
    "job": {...}
}
```

#### 4. İş Fotoğrafı Yükle

```http
POST /services/{job_id}/photos
Authorization: Bearer {token}
Content-Type: multipart/form-data

FormData:
    - photo: (file) image.jpg
    - description: "Toner değişimi öncesi"

Response:
{
    "success": true,
    "photo_url": "https://yourdomain.com/uploads/jobs/123/photo_1.jpg",
    "message": "Fotoğraf yüklendi"
}
```

#### 5. İmza Ekle

```http
POST /services/{job_id}/signature
Authorization: Bearer {token}
Content-Type: application/json

{
    "type": "customer",  // veya "technician"
    "signature": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}

Response:
{
    "success": true,
    "message": "İmza kaydedildi"
}
```

---

### 📊 Sayaç Okuma Endpointleri

#### 1. Sayaç Okuma Ekle

```http
POST /cpc/readings
Authorization: Bearer {token}
Content-Type: application/json

{
    "customer_device_id": 56,
    "reading_date": "2025-11-04T11:30:00",
    "total_bw": 16500,
    "total_color": 5200,
    "bw_copy": 8000,
    "color_copy": 2500,
    "bw_print": 8500,
    "color_print": 2700,
    "notes": "Normal kullanım",
    "photo_proof": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "service_record_id": 123  // Hangi servis işi ile ilişkili (opsiyonel)
}

Response:
{
    "success": true,
    "reading_id": 789,
    "message": "Sayaç okuması kaydedildi",
    "previous_reading": {
        "date": "2025-10-01",
        "total_bw": 15000,
        "total_color": 5000
    },
    "usage_since_last": {
        "bw": 1500,
        "color": 200,
        "days": 34
    }
}
```

#### 2. Cihazın Sayaç Geçmişini Getir

```http
GET /cpc/readings/device/{customer_device_id}
Authorization: Bearer {token}
Query Parameters:
    - limit: 10 (opsiyonel, varsayılan: 10)

Response:
{
    "success": true,
    "readings": [
        {
            "id": 789,
            "reading_date": "2025-11-04",
            "total_bw": 16500,
            "total_color": 5200,
            "recorded_by": "Ahmet Yılmaz",
            "source": "mobile"
        }
    ],
    "device": {
        "brand": "Kyocera",
        "model": "TASKalfa 3252ci",
        "serial_number": "VPW1234567"
    }
}
```

---

### 🗺️ Diğer Endpointler

#### 1. Cihaz Arama

```http
GET /devices/search
Authorization: Bearer {token}
Query Parameters:
    - q: VPW1234  (Seri no, marka, model ile arama)
    - customer_id: 45 (opsiyonel)

Response:
{
    "success": true,
    "devices": [
        {
            "id": 78,
            "brand": "Kyocera",
            "model": "TASKalfa 3252ci",
            "serial_number": "VPW1234567",
            "customer": {
                "id": 45,
                "name": "ABC Şirketi"
            }
        }
    ]
}
```

#### 2. Müşteri Bilgisi Getir

```http
GET /customers/{customer_id}
Authorization: Bearer {token}

Response:
{
    "success": true,
    "customer": {
        "id": 45,
        "name": "ABC Şirketi",
        "company_name": "ABC Ltd. Şti.",
        "phone": "+90 532 123 4567",
        "email": "info@abc.com",
        "address": "İstanbul, Kadıköy",
        "devices": [
            {
                "id": 78,
                "brand": "Kyocera",
                "model": "TASKalfa 3252ci",
                "serial_number": "VPW1234567"
            }
        ]
    }
}
```

---

## 🔨 Backend API İmplementasyonu (Python Flask)

### Gerekli Kütüphaneler

```bash
pip install flask flask-cors pyjwt bcrypt pillow
```

### Örnek API Yapısı

```python
# api/
#   __init__.py
#   auth.py          # Kimlik doğrulama endpointleri
#   services.py      # Servis işleri endpointleri
#   cpc.py           # Sayaç okuma endpointleri
#   middleware.py    # Token kontrolü, CORS vb.
#   utils.py         # Yardımcı fonksiyonlar
```

### Örnek Kod: `api/__init__.py`

```python
from flask import Flask, jsonify
from flask_cors import CORS
from api.auth import auth_bp
from api.services import services_bp
from api.cpc import cpc_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-buraya-güvenli-bir-key'
    
    # CORS ayarları
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],  # Production'da belirli domainler
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Blueprint'leri kaydet
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(services_bp, url_prefix='/api/v1/services')
    app.register_blueprint(cpc_bp, url_prefix='/api/v1/cpc')
    
    # Hata yönetimi
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint bulunamadı'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Sunucu hatası'
        }), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### Örnek Kod: `api/middleware.py`

```python
from functools import wraps
from flask import request, jsonify
import jwt
from datetime import datetime

SECRET_KEY = 'your-secret-key-buraya-güvenli-bir-key'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Header'dan token al
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # "Bearer TOKEN"
            except IndexError:
                return jsonify({
                    'success': False,
                    'error': 'Token formatı hatalı'
                }), 401
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token bulunamadı'
            }), 401
        
        try:
            # Token'ı doğrula
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
            
            # Veritabanından kullanıcı bilgisini al
            # conn = get_db_connection()
            # user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user_id,)).fetchone()
            # conn.close()
            
            # Request'e kullanıcı bilgisini ekle
            request.current_user_id = current_user_id
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Token süresi dolmuş'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': 'Geçersiz token'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated

def technician_required(f):
    """Sadece teknisyenlerin erişebileceği endpointler için"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        # Kullanıcı rolü kontrolü yapılabilir
        # if request.current_user_role not in ['technician', 'admin']:
        #     return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 403
        return f(*args, **kwargs)
    
    return decorated
```

### Örnek Kod: `api/services.py`

```python
from flask import Blueprint, request, jsonify
from api.middleware import token_required, technician_required
import sqlite3
from datetime import datetime

services_bp = Blueprint('services', __name__)

def get_db_connection():
    # Mevcut projenizin database bağlantısını kullanın
    conn = sqlite3.connect('proservis.db')
    conn.row_factory = sqlite3.Row
    return conn

@services_bp.route('/my-jobs', methods=['GET'])
@technician_required
def get_my_jobs():
    """Teknisyene atanan işleri getir"""
    try:
        user_id = request.current_user_id
        status = request.args.get('status', None)
        
        conn = get_db_connection()
        
        query = '''
            SELECT 
                sr.id, sr.service_type, sr.status, sr.priority,
                sr.description, sr.notes, sr.scheduled_date,
                sr.created_date, sr.completed_date,
                c.id as customer_id, c.name as customer_name,
                c.phone as customer_phone, c.address as customer_address,
                d.id as device_id, d.brand, d.model,
                cd.serial_number
            FROM service_records sr
            JOIN customers c ON sr.customer_id = c.id
            JOIN customer_devices cd ON sr.device_id = cd.id
            JOIN devices d ON cd.device_id = d.id
            WHERE sr.technician_id = ?
        '''
        
        params = [user_id]
        
        if status:
            query += ' AND sr.status = ?'
            params.append(status)
        
        query += ' ORDER BY sr.scheduled_date ASC, sr.priority DESC'
        
        jobs = conn.execute(query, params).fetchall()
        
        # İstatistikler
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'beklemede' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'devam_ediyor' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'tamamlandi' THEN 1 ELSE 0 END) as completed
            FROM service_records
            WHERE technician_id = ?
        ''', (user_id,)).fetchone()
        
        conn.close()
        
        # JSON formatına çevir
        jobs_list = []
        for job in jobs:
            jobs_list.append({
                'id': job['id'],
                'customer': {
                    'id': job['customer_id'],
                    'name': job['customer_name'],
                    'phone': job['customer_phone'],
                    'address': job['customer_address']
                },
                'device': {
                    'id': job['device_id'],
                    'brand': job['brand'],
                    'model': job['model'],
                    'serial_number': job['serial_number']
                },
                'service_type': job['service_type'],
                'status': job['status'],
                'priority': job['priority'],
                'description': job['description'],
                'scheduled_date': job['scheduled_date'],
                'created_date': job['created_date']
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'total': stats['total'],
            'pending': stats['pending'],
            'in_progress': stats['in_progress'],
            'completed': stats['completed']
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@services_bp.route('/<int:job_id>/status', methods=['PUT'])
@technician_required
def update_job_status(job_id):
    """İş durumunu güncelle"""
    try:
        data = request.get_json()
        status = data.get('status')
        notes = data.get('notes', '')
        arrived_at = data.get('arrived_at', None)
        work_duration = data.get('work_duration', None)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Durum bilgisi gerekli'
            }), 400
        
        conn = get_db_connection()
        
        # İş sahibini kontrol et
        job = conn.execute(
            'SELECT technician_id FROM service_records WHERE id = ?',
            (job_id,)
        ).fetchone()
        
        if not job:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'İş bulunamadı'
            }), 404
        
        if job['technician_id'] != request.current_user_id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Bu işe erişim yetkiniz yok'
            }), 403
        
        # Güncelleme yap
        update_fields = ['status = ?', 'notes = ?']
        params = [status, notes]
        
        if arrived_at:
            update_fields.append('arrived_at = ?')
            params.append(arrived_at)
        
        if work_duration:
            update_fields.append('work_duration = ?')
            params.append(work_duration)
        
        if status == 'tamamlandi':
            update_fields.append('completed_date = ?')
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        params.append(job_id)
        
        conn.execute(f'''
            UPDATE service_records
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', params)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'İş durumu güncellendi'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## 📱 Mobil Uygulama Özellikleri

### Ekranlar

1. **Login Ekranı**
   - Kullanıcı adı/şifre
   - "Beni Hatırla" özelliği
   - Şifremi Unuttum

2. **Ana Dashboard**
   - Bugünkü işler
   - Bekleyen işler sayısı
   - Devam eden işler
   - Tamamlanan işler (bugün)
   - Hızlı sayaç okuma butonu

3. **İş Listesi**
   - Filtreleme (Durum, Tarih, Öncelik)
   - Sıralama
   - Arama
   - Yol tarifi butonu (Google Maps entegrasyonu)

4. **İş Detayı**
   - Müşteri bilgileri
   - Cihaz bilgileri
   - Sayaç geçmişi
   - İş açıklaması
   - Durum güncelleme
   - Fotoğraf ekleme
   - Not ekleme
   - İmza alma (müşteri + teknisyen)
   - Sayaç okuma butonu

5. **Sayaç Okuma Ekranı**
   - Cihaz seçimi/arama
   - Sayaç değerleri girişi
   - Kamera ile fotoğraf çekme
   - Önceki okuma karşılaştırması
   - Kaydet

6. **Profil**
   - Kullanıcı bilgileri
   - İstatistikler (Bu ay tamamlanan işler)
   - Ayarlar
   - Çıkış

### Özellikler

✅ **Offline Çalışma**:

- SQLite yerel veritabanı
- Senkronizasyon kuyruğu
- İnternet bağlantısı geldiğinde otomatik senkronizasyon

✅ **Push Notification**:

- Yeni iş atandığında bildirim
- İş önceliği değiştiğinde bildirim
- Hatırlatıcılar

✅ **Konum Servisleri**:

- Teknisyen konumu takibi
- İş yerine yol tarifi
- Varış saati kaydı

✅ **Kamera Entegrasyonu**:

- Sayaç fotoğrafı
- İş öncesi/sonrası fotoğraflar
- Arıza fotoğrafları

✅ **İmza Özelliği**:

- Canvas ile dijital imza
- Müşteri onayı
- Teknisyen onayı

---

## 🔒 Güvenlik Önlemleri

1. **JWT Token Kullanımı**
   - Token süre sınırı: 24 saat
   - Refresh token mekanizması
   - Token'ı güvenli bir yerde saklama (KeyChain/KeyStore)

2. **HTTPS Zorunluluğu**
   - API iletişiminde SSL/TLS
   - Certificate pinning (opsiyonel, ekstra güvenlik)

3. **API Rate Limiting**
   - IP bazlı limit (örn: 100 istek/dakika)
   - Token bazlı limit

4. **Veri Şifreleme**
   - Hassas veriler için end-to-end encryption
   - Yerel veritabanı şifrelemesi

5. **Yetkilendirme**
   - Sadece kendi işlerine erişim
   - Admin panelinden teknisyen-iş atama kontrolü

---

## 📊 Veritabanı Migration Scripti

```python
# utils/database/mobile_api_migration.py

def migrate_for_mobile_api(conn):
    """Mobil API için gerekli veritabanı değişiklikleri"""
    
    cursor = conn.cursor()
    
    try:
        # 1. mobile_sessions tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mobile_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                device_name TEXT,
                session_token TEXT UNIQUE NOT NULL,
                fcm_token TEXT,
                created_date TEXT NOT NULL,
                last_active TEXT NOT NULL,
                expires_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 2. service_records tablosuna yeni kolonlar
        new_columns = [
            ('location_latitude', 'REAL'),
            ('location_longitude', 'REAL'),
            ('arrived_at', 'TEXT'),
            ('photos', 'TEXT'),
            ('customer_signature', 'TEXT'),
            ('technician_signature', 'TEXT'),
            ('work_duration', 'INTEGER')
        ]
        
        for col_name, col_type in new_columns:
            try:
                cursor.execute(f'''
                    ALTER TABLE service_records 
                    ADD COLUMN {col_name} {col_type}
                ''')
                print(f"✓ service_records.{col_name} eklendi")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"○ service_records.{col_name} zaten mevcut")
                else:
                    raise
        
        # 3. cpc_records tablosuna yeni kolonlar
        cpc_columns = [
            ('source', 'TEXT', 'desktop'),
            ('photo_proof', 'TEXT', None)
        ]
        
        for col_name, col_type, default in cpc_columns:
            try:
                if default:
                    cursor.execute(f'''
                        ALTER TABLE cpc_records 
                        ADD COLUMN {col_name} {col_type} DEFAULT '{default}'
                    ''')
                else:
                    cursor.execute(f'''
                        ALTER TABLE cpc_records 
                        ADD COLUMN {col_name} {col_type}
                    ''')
                print(f"✓ cpc_records.{col_name} eklendi")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"○ cpc_records.{col_name} zaten mevcut")
                else:
                    raise
        
        conn.commit()
        print("\n✅ Mobil API migration başarıyla tamamlandı!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration hatası: {str(e)}")
        return False

if __name__ == '__main__':
    import sqlite3
    
    # Test için
    conn = sqlite3.connect('proservis.db')
    migrate_for_mobile_api(conn)
    conn.close()
```

---

## 🚀 Adım Adım İmplementasyon Planı

### Faz 1: Backend Hazırlık (2-3 gün)

- [ ] Veritabanı migration scriptini çalıştır
- [ ] Flask API projesini oluştur
- [ ] JWT authentication implementasyonu
- [ ] Service endpoints (CRUD)
- [ ] CPC endpoints
- [ ] API testleri (Postman/Thunder Client)

### Faz 2: Mobil Uygulama Temel (3-4 gün)

- [ ] Mobil proje kurulumu (Flutter/React Native)
- [ ] Login ekranı
- [ ] Token yönetimi
- [ ] Ana dashboard
- [ ] İş listesi ekranı
- [ ] API entegrasyonu

### Faz 3: İleri Özellikler (3-4 gün)

- [ ] İş detay ekranı
- [ ] Sayaç okuma ekranı
- [ ] Kamera entegrasyonu
- [ ] İmza özelliği
- [ ] Fotoğraf yükleme

### Faz 4: Offline & Senkronizasyon (2-3 gün)

- [ ] SQLite yerel veritabanı
- [ ] Offline veri saklama
- [ ] Senkronizasyon mekanizması
- [ ] Push notification (Firebase)

### Faz 5: Test & Deploy (2-3 gün)

- [ ] Kapsamlı test
- [ ] Bug fixing
- [ ] Performance optimizasyonu
- [ ] Google Play Store yayınlama

**Toplam Tahmini Süre**: 12-17 gün

---

## 🛠️ Gerekli Araçlar & Teknolojiler

### Backend

- **Python 3.x**: Ana programlama dili
- **Flask**: Web framework
- **SQLite**: Veritabanı
- **JWT**: Token authentication
- **Pillow**: Image processing

### Mobil (Flutter Önerisi)

- **Flutter SDK**: Mobil framework
- **Dart**: Programlama dili
- **sqflite**: SQLite plugin
- **dio**: HTTP client
- **provider**: State management
- **camera**: Kamera erişimi
- **signature**: İmza widget
- **firebase_messaging**: Push notification
- **geolocator**: Konum servisleri

### Test & Deployment

- **Postman**: API test
- **Android Studio**: Android development
- **VS Code**: Code editor
- **Git**: Version control
- **Google Play Console**: App deployment

---

## 📝 Notlar

1. **API URL Konfigürasyonu**: Mobil uygulamada API base URL'ini config dosyasında tutun (dev/prod ortamları için).

2. **Veritabanı Backup**: Mobil API özelliklerini eklemeden önce mevcut veritabanının yedeğini alın.

3. **Test Kullanıcıları**: API testleri için `role='technician'` olan test kullanıcıları oluşturun.

4. **Loglama**: Hem backend hem mobil uygulamada detaylı loglama yapın (hata ayıklama için).

5. **Documentation**: API endpoint'lerini Swagger/OpenAPI ile dokümante edin.

---

## 📞 Sorular ve Yardım

Bu plan üzerinden ilerlerken karşılaşılabilecek sorunlar:

1. **Flask API nasıl çalıştırılır?**

   ```bash
   cd api
   python __init__.py
   # API http://localhost:5000 adresinde çalışacak
   ```

2. **Mobil uygulama hangi teknoloji ile yapılmalı?**
   - **Flutter** (Önerilen): Hem Android hem iOS için tek kod tabanı
   - **React Native**: JavaScript biliyorsanız
   - **Native Android (Kotlin)**: Sadece Android için

3. **API'yi nasıl dışarıya açabilirim?**
   - **Ngrok** (Test için): Geçici public URL
   - **AWS/Azure**: Production deployment
   - **VPS (DigitalOcean/Linode)**: Ekonomik çözüm

---

**Hazırlayan**: GitHub Copilot  
**Tarih**: 3 Kasım 2025  
**Versiyon**: 1.0
