#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProServis Azure SQL Database Manager
Azure SQL Server ile merkezi veritabanı yönetimi
"""

import pyodbc
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from cryptography.fernet import Fernet
from datetime import datetime

logger = logging.getLogger(__name__)


class AzureSQLManager:
    """
    Azure SQL Database Yöneticisi
    
    Özellikler:
    - Merkezi Azure SQL veritabanı
    - Firma bazlı tablo/schema yönetimi
    - Şifreli bağlantı bilgileri
    - Otomatik bağlantı yönetimi
    """
    
    # Azure SQL Server bilgileri
    SERVER = "proservis.database.windows.net"
    DATABASE = "Proservis-Database"
    PORT = 1433
    
    def __init__(self, credentials_dir: Path):
        # Azure entegrasyonu askıya alındı
        pass
    
    def _ensure_encryption_key(self):
        """Encryption key oluştur veya yükle"""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            
            # Windows'da gizle
            import os
            if os.name == 'nt':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(str(self.key_file), 2)
                except:
                    pass
            
            logger.info("Yeni encryption key oluşturuldu")
        
        self.cipher = Fernet(self.key_file.read_bytes())
    
    def save_credentials(self, username: str, password: str) -> bool:
        """
        Azure SQL credentials'ı şifreli kaydet
        
        Args:
            username: SQL Server kullanıcı adı
            password: SQL Server şifresi
            
        Returns:
            Başarılı ise True
        """
        try:
            creds = {
                'username': username,
                'password': password,
                'server': self.SERVER,
                'database': self.DATABASE
            }
            
            creds_json = json.dumps(creds)
            encrypted = self.cipher.encrypt(creds_json.encode())
            
            self.creds_file.write_bytes(encrypted)
            
            self.username = username
            self.password = password
            
            logger.info("Azure SQL credentials şifreli olarak kaydedildi")
            return True
            
        except Exception as e:
            logger.error(f"Credentials kaydetme hatası: {e}")
            return False
    
    def load_credentials(self) -> bool:
        """
        Kaydedilmiş credentials'ı yükle
        
        Returns:
            Başarılı ise True
        """
        try:
            if not self.creds_file.exists():
                logger.warning("Credentials dosyası bulunamadı")
                return False
            
            encrypted = self.creds_file.read_bytes()
            decrypted = self.cipher.decrypt(encrypted).decode()
            creds = json.loads(decrypted)
            
            self.username = creds['username']
            self.password = creds['password']
            
            logger.info("Credentials yüklendi")
            return True
            
        except Exception as e:
            logger.error(f"Credentials yükleme hatası: {e}")
            return False
    
    def get_connection_string(self) -> str:
        """
        ODBC connection string oluştur
        
        Returns:
            Connection string
        """
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.SERVER},{self.PORT};"
            f"DATABASE={self.DATABASE};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
    
    def connect(self) -> bool:
        """
        Azure SQL'e bağlan
        
        Returns:
            Başarılı ise True
        """
        try:
            if not self.username or not self.password:
                if not self.load_credentials():
                    logger.error("Credentials yüklü değil!")
                    return False
            
            logger.info("Azure SQL'e bağlanılıyor...")
            
            conn_str = self.get_connection_string()
            self.connection = pyodbc.connect(conn_str, timeout=30)
            
            logger.info(f"✅ Azure SQL bağlantısı başarılı: {self.DATABASE}")
            return True
            
        except pyodbc.Error as e:
            logger.error(f"Azure SQL bağlantı hatası: {e}")
            return False
        except Exception as e:
            logger.error(f"Bağlantı hatası: {e}")
            return False
    
    def disconnect(self):
        """Bağlantıyı kapat"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Azure SQL bağlantısı kapatıldı")
            except:
                pass
            finally:
                self.connection = None
    
    def test_connection(self) -> bool:
        """
        Bağlantıyı test et
        
        Returns:
            Başarılı ise True
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            
            logger.info(f"SQL Server Version: {version[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Test hatası: {e}")
            return False
    
    def ensure_global_users_table(self) -> bool:
        """
        Merkezi kullanıcı tablosunu oluştur (multi-tenant için)
        Her kullanıcı bir firmaya ait
        
        Returns:
            Başarılı ise True
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            cursor = self.connection.cursor()
            
            # dbo.global_users tablosu (tüm firmalar için merkezi)
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT * FROM sys.tables 
                    WHERE name = 'global_users' AND schema_id = SCHEMA_ID('dbo')
                )
                BEGIN
                    CREATE TABLE dbo.global_users (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        username NVARCHAR(255) NOT NULL UNIQUE,
                        password_hash NVARCHAR(255) NOT NULL,
                        full_name NVARCHAR(255),
                        role NVARCHAR(50) DEFAULT 'user',
                        company_name NVARCHAR(255) NOT NULL,
                        company_schema NVARCHAR(255) NOT NULL,
                        is_active INT DEFAULT 1,
                        created_at DATETIME DEFAULT GETDATE(),
                        last_login DATETIME,
                        INDEX idx_username (username),
                        INDEX idx_company (company_name)
                    )
                END
            """)
            
            self.connection.commit()
            logger.info("✅ Global users tablosu hazır")
            return True
            
        except Exception as e:
            logger.error(f"Global users tablo hatası: {e}")
            return False
    
    def ensure_company_schema(self, company_name: str) -> bool:
        """
        Firma için schema oluştur (yoksa)
        
        Args:
            company_name: Firma adı
            
        Returns:
            Başarılı ise True
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Güvenli schema adı (register_user ile aynı format!)
            safe_name = company_name.replace(' ', '_')  # Boşlukları _ ile değiştir
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == '_')  # Geçersiz karakterleri kaldır
            schema_name = f"Company_{safe_name}"
            
            cursor = self.connection.cursor()
            
            # Schema var mı kontrol et
            cursor.execute("""
                SELECT SCHEMA_NAME 
                FROM INFORMATION_SCHEMA.SCHEMATA 
                WHERE SCHEMA_NAME = ?
            """, schema_name)
            
            if cursor.fetchone():
                logger.info(f"Schema mevcut: {schema_name}")
                # ⚠️ current_company'yi değiştirme - login sonrası set edilecek
                return True
            
            # Schema oluştur
            logger.info(f"Schema oluşturuluyor: {schema_name}")
            cursor.execute(f"CREATE SCHEMA {schema_name}")
            self.connection.commit()
            
            # Metadata tablosu
            cursor.execute(f"""
                CREATE TABLE {schema_name}._metadata (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    company_name NVARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )
            """)
            
            cursor.execute(f"""
                INSERT INTO [{schema_name}].[_metadata] (company_name)
                VALUES (?)
            """, company_name)
            
            self.connection.commit()
            
            # ⚠️ current_company'yi değiştirme - login sonrası set edilecek
            logger.info(f"✅ Schema oluşturuldu: {schema_name}")
            return True
            
        except Exception as e:
            logger.error(f"Schema oluşturma hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def list_companies(self) -> List[str]:
        """
        Tüm firmaları listele
        
        Returns:
            Firma isimleri listesi
        """
        try:
            if not self.connection:
                if not self.connect():
                    return []
            
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT SCHEMA_NAME 
                FROM INFORMATION_SCHEMA.SCHEMATA 
                WHERE SCHEMA_NAME LIKE 'Company_%'
            """)
            
            schemas = [row[0].replace('Company_', '') for row in cursor.fetchall()]
            
            logger.info(f"{len(schemas)} firma bulundu")
            return schemas
            
        except Exception as e:
            logger.error(f"Firma listesi hatası: {e}")
            return []
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[int]:
        """
        Query çalıştır (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query
            params: Query parametreleri
            
        Returns:
            Affected rows veya None
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            self.connection.commit()
            
            return cursor.rowcount
            
        except Exception as e:
            logger.error(f"Query hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """
        Tek satır getir
        
        Args:
            query: SQL query
            params: Query parametreleri
            
        Returns:
            Row dict veya None
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Dict'e çevir
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
            
        except Exception as e:
            logger.error(f"Fetch hatası: {e}")
            return None
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Tüm satırları getir
        
        Args:
            query: SQL query
            params: Query parametreleri
            
        Returns:
            Row dict listesi
        """
        try:
            if not self.connection:
                if not self.connect():
                    return []
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            
            if not rows:
                return []
            
            # Dict listesine çevir
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Fetch all hatası: {e}")
            return []
    
    def get_company_info(self, company_name: str) -> Optional[Dict]:
        """
        Firma bilgilerini al
        
        Args:
            company_name: Firma adı
            
        Returns:
            Firma bilgileri dict
        """
        try:
            safe_name = "".join(c for c in company_name if c.isalnum() or c == '_')
            schema_name = f"Company_{safe_name}"
            
            query = f"""
                SELECT company_name, created_at, updated_at
                FROM [{schema_name}].[_metadata]
            """
            
            return self.fetch_one(query)
            
        except Exception as e:
            logger.error(f"Firma bilgisi alma hatası: {e}")
            return None
    
    def create_tables_from_sqlite_schema(self, schema_name: str = None) -> bool:
        """
        SQLite tablo yapısını Azure SQL'e kopyala
        
        Args:
            schema_name: Hedef schema (None ise current_company kullanılır)
            
        Returns:
            Başarılı ise True
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Schema adını belirle
            if schema_name is None:
                if not self.current_company:
                    logger.error("Firma seçilmemiş!")
                    return False
                safe_name = "".join(c for c in self.current_company if c.isalnum() or c == '_')
                schema_name = f"Company_{safe_name}"
            
            logger.info(f"Tablolar oluşturuluyor: {schema_name}")
            
            cursor = self.connection.cursor()
            
            # Azure SQL Server tablo tanımları (SQLite'dan uyarlanmış)
            tables = {
                "users": f"""
                    CREATE TABLE {schema_name}.users (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        username NVARCHAR(255) NOT NULL UNIQUE,
                        password_hash NVARCHAR(255) NOT NULL,
                        role NVARCHAR(50) DEFAULT 'user'
                    )
                """,
                
                "settings": f"""
                    CREATE TABLE {schema_name}.settings (
                        [key] NVARCHAR(255) PRIMARY KEY,
                        value NVARCHAR(MAX)
                    )
                """,
                
                "banks": f"""
                    CREATE TABLE {schema_name}.banks (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        bank_name NVARCHAR(255) NOT NULL,
                        account_holder NVARCHAR(255) NOT NULL,
                        iban NVARCHAR(50) NOT NULL,
                        notes NVARCHAR(MAX),
                        is_default INT DEFAULT 0
                    )
                """,
                
                "technicians": f"""
                    CREATE TABLE {schema_name}.technicians (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        name NVARCHAR(255) NOT NULL,
                        surname NVARCHAR(255) NOT NULL,
                        phone NVARCHAR(50),
                        email NVARCHAR(255),
                        is_active INT DEFAULT 1,
                        created_date DATETIME DEFAULT GETDATE(),
                        updated_date DATETIME DEFAULT GETDATE()
                    )
                """,
                
                "customers": f"""
                    CREATE TABLE {schema_name}.customers (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        name NVARCHAR(255) NOT NULL UNIQUE,
                        phone NVARCHAR(50),
                        email NVARCHAR(255),
                        address NVARCHAR(MAX),
                        tax_id NVARCHAR(50),
                        tax_office NVARCHAR(255),
                        is_contract INT DEFAULT 0,
                        contract_start_date DATE,
                        contract_end_date DATE,
                        contract_pdf_path NVARCHAR(500)
                    )
                """,
                
                "devices": f"""
                    CREATE TABLE {schema_name}.devices (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        customer_id INT,
                        model NVARCHAR(255) NOT NULL,
                        type NVARCHAR(100),
                        serial_number NVARCHAR(255) UNIQUE,
                        is_cpc INT DEFAULT 0,
                        cpc_bw_price FLOAT DEFAULT 0.0,
                        cpc_color_price FLOAT DEFAULT 0.0,
                        cpc_bw_currency NVARCHAR(10) DEFAULT 'TL',
                        cpc_color_currency NVARCHAR(10) DEFAULT 'TL',
                        color_type NVARCHAR(50) DEFAULT 'Siyah-Beyaz',
                        rental_fee FLOAT,
                        rental_currency NVARCHAR(10),
                        stock_id INT,
                        FOREIGN KEY (customer_id) REFERENCES {schema_name}.customers(id) ON DELETE CASCADE
                    )
                """,
                
                "service_records": f"""
                    CREATE TABLE {schema_name}.service_records (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        device_id INT,
                        assigned_user_id INT,
                        problem_description NVARCHAR(MAX),
                        notes NVARCHAR(MAX),
                        created_date DATETIME,
                        bw_counter INT,
                        color_counter INT,
                        status NVARCHAR(50),
                        technician_id INT,
                        technician_report NVARCHAR(MAX),
                        service_form_pdf_path NVARCHAR(500),
                        FOREIGN KEY (device_id) REFERENCES {schema_name}.devices(id) ON DELETE CASCADE
                    )
                """,
                
                "stock_items": f"""
                    CREATE TABLE {schema_name}.stock_items (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        name NVARCHAR(255) NOT NULL,
                        category NVARCHAR(100),
                        quantity INT DEFAULT 0,
                        min_stock_level INT DEFAULT 0,
                        unit NVARCHAR(50),
                        purchase_price FLOAT,
                        sale_price FLOAT,
                        currency NVARCHAR(10) DEFAULT 'TL',
                        supplier NVARCHAR(255),
                        notes NVARCHAR(MAX),
                        color_type NVARCHAR(50),
                        location NVARCHAR(255),
                        created_at DATETIME DEFAULT GETDATE()
                    )
                """,
                
                "invoices": f"""
                    CREATE TABLE {schema_name}.invoices (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        customer_id INT,
                        invoice_number NVARCHAR(100) UNIQUE,
                        invoice_date DATE,
                        due_date DATE,
                        subtotal FLOAT,
                        tax_amount FLOAT,
                        total_amount FLOAT,
                        currency NVARCHAR(10) DEFAULT 'TL',
                        status NVARCHAR(50) DEFAULT 'Beklemede',
                        notes NVARCHAR(MAX),
                        created_at DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (customer_id) REFERENCES {schema_name}.customers(id) ON DELETE CASCADE
                    )
                """,
                
                "payments": f"""
                    CREATE TABLE {schema_name}.payments (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        invoice_id INT,
                        payment_date DATE,
                        amount FLOAT,
                        currency NVARCHAR(10) DEFAULT 'TL',
                        payment_method NVARCHAR(100),
                        notes NVARCHAR(MAX),
                        created_at DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (invoice_id) REFERENCES {schema_name}.invoices(id) ON DELETE CASCADE
                    )
                """
            }
            
            # Tabloları oluştur
            created_count = 0
            for table_name, create_sql in tables.items():
                try:
                    # Tablo var mı kontrol et
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    """, schema_name, table_name)
                    
                    if cursor.fetchone()[0] > 0:
                        logger.debug(f"Tablo mevcut: {table_name}")
                        continue
                    
                    # Tabloyu oluştur
                    cursor.execute(create_sql)
                    self.connection.commit()
                    created_count += 1
                    logger.info(f"✅ Tablo oluşturuldu: {schema_name}.{table_name}")
                    
                except Exception as e:
                    logger.error(f"Tablo oluşturma hatası ({table_name}): {e}")
                    self.connection.rollback()
            
            logger.info(f"✅ {created_count} yeni tablo oluşturuldu")
            return True
            
        except Exception as e:
            logger.error(f"Tablolar oluşturulamadı: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def sync_table_data(self, table_name: str, records: list, schema_name: str = None) -> dict:
        """
        SQLite'tan Azure SQL'e veri senkronize et
        
        Args:
            table_name: Tablo adı
            records: Senkronize edilecek kayıtlar [{'id': 1, 'name': 'Test', ...}, ...]
            schema_name: Hedef schema (None ise current_company)
            
        Returns:
            {'success': int, 'failed': int, 'errors': []}
        """
        if not self.connection:
            if not self.connect():
                return {'success': 0, 'failed': len(records), 'errors': ['Connection failed']}
        
        if schema_name is None:
            if not self.current_company:
                return {'success': 0, 'failed': len(records), 'errors': ['No company selected']}
            # current_company zaten "Company_Test_Company_1" formatında
            schema_name = self.current_company
        
        cursor = self.connection.cursor()
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            for record in records:
                try:
                    # Kayıt var mı kontrol et
                    record_id = record.get('id')
                    if not record_id:
                        failed_count += 1
                        errors.append(f"No ID in record: {record}")
                        continue
                    
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM [{schema_name}].[{table_name}]
                        WHERE id = ?
                    """, (record_id,))
                    
                    exists = cursor.fetchone()[0] > 0
                    
                    # Sütun adlarını ve değerlerini hazırla
                    columns = [k for k in record.keys() if k != 'id']
                    values = [record[k] for k in columns]
                    
                    if exists:
                        # UPDATE
                        set_clause = ', '.join([f"{col} = ?" for col in columns])
                        query = f"""
                            UPDATE [{schema_name}].[{table_name}]
                            SET {set_clause}
                            WHERE id = ?
                        """
                        cursor.execute(query, values + [record_id])
                    else:
                        # INSERT (IDENTITY kolonu için özel ayar gerekli)
                        columns_with_id = ['id'] + columns
                        placeholders = ', '.join(['?' for _ in columns_with_id])
                        
                        # IDENTITY_INSERT ON (SQLite'tan gelen id değerini kullanabilmek için)
                        cursor.execute(f"SET IDENTITY_INSERT [{schema_name}].[{table_name}] ON")
                        
                        query = f"""
                            INSERT INTO [{schema_name}].[{table_name}]
                            ({', '.join(columns_with_id)})
                            VALUES ({placeholders})
                        """
                        cursor.execute(query, [record_id] + values)
                        
                        # IDENTITY_INSERT OFF (geri al)
                        cursor.execute(f"SET IDENTITY_INSERT [{schema_name}].[{table_name}] OFF")
                    
                    success_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Record {record_id}: {str(e)}")
                    logger.error(f"Sync error for {table_name}.{record_id}: {e}")
            
            self.connection.commit()
            logger.info(f"✅ {table_name}: {success_count} success, {failed_count} failed")
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Sync transaction failed: {e}")
            return {'success': 0, 'failed': len(records), 'errors': [str(e)]}
        
        return {'success': success_count, 'failed': failed_count, 'errors': errors}
    
    def authenticate_user(self, username: str, password: str) -> dict:
        """
        Kullanıcıyı merkezi tablodan doğrula ve firma bilgisini al
        
        Args:
            username: Kullanıcı adı
            password: Plain password (bcrypt ile karşılaştırılacak)
            
        Returns:
            {
                'success': bool,
                'user': {'id', 'username', 'full_name', 'role', 'company_name', 'company_schema'},
                'error': str
            }
        """
        try:
            import bcrypt
            
            if not self.connection:
                if not self.connect():
                    return {'success': False, 'user': None, 'error': 'Connection failed'}
            
            cursor = self.connection.cursor()
            
            # Kullanıcıyı bul
            cursor.execute("""
                SELECT id, username, password_hash, full_name, role, 
                       company_name, company_schema, is_active
                FROM dbo.global_users
                WHERE username = ? AND is_active = 1
            """, (username,))
            
            row = cursor.fetchone()
            
            if not row:
                return {'success': False, 'user': None, 'error': 'User not found'}
            
            user_id, db_username, db_password_hash, full_name, role, company_name, company_schema, is_active = row
            
            # Şifre kontrolü (bcrypt)
            password_bytes = password.encode('utf-8') if isinstance(password, str) else password
            hash_bytes = db_password_hash.encode('utf-8') if isinstance(db_password_hash, str) else db_password_hash
            
            if not bcrypt.checkpw(password_bytes, hash_bytes):
                return {'success': False, 'user': None, 'error': 'Invalid password'}
            
            # Last login güncelle
            cursor.execute("""
                UPDATE dbo.global_users
                SET last_login = GETDATE()
                WHERE id = ?
            """, (user_id,))
            self.connection.commit()
            
            # Firma schema'sını set et
            self.current_company = company_name
            
            logger.info(f"✅ Kullanıcı doğrulandı: {username} ({company_name})")
            
            return {
                'success': True,
                'user': {
                    'id': user_id,
                    'username': db_username,
                    'full_name': full_name,
                    'role': role,
                    'company_name': company_name,
                    'company_schema': company_schema
                },
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {'success': False, 'user': None, 'error': str(e)}
    
    def register_user(self, username: str, password_hash: str, full_name: str, 
                     role: str, company_name: str) -> dict:
        """
        Yeni kullanıcı kaydet (merkezi tabloya)
        
        Args:
            username: Kullanıcı adı
            password_hash: Bcrypt hash
            full_name: Tam ad
            role: Rol (Admin, user, etc.)
            company_name: Firma adı
            
        Returns:
            {'success': bool, 'user_id': int, 'error': str}
        """
        try:
            if not self.connection:
                if not self.connect():
                    return {'success': False, 'user_id': None, 'error': 'Connection failed'}
            
            # Güvenli schema adı (boşlukları alt çizgiye çevir)
            safe_name = company_name.replace(' ', '_')
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == '_')
            company_schema = f"Company_{safe_name}"
            
            cursor = self.connection.cursor()
            
            # Kullanıcı var mı kontrol et
            cursor.execute("""
                SELECT id FROM dbo.global_users WHERE username = ?
            """, (username,))
            
            if cursor.fetchone():
                return {'success': False, 'user_id': None, 'error': 'Username already exists'}
            
            # Kullanıcıyı ekle
            cursor.execute("""
                INSERT INTO dbo.global_users 
                (username, password_hash, full_name, role, company_name, company_schema)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, password_hash, full_name, role, company_name, company_schema))
            
            self.connection.commit()
            
            # ID'yi al
            cursor.execute("SELECT @@IDENTITY")
            user_id = cursor.fetchone()[0]
            
            logger.info(f"✅ Kullanıcı kaydedildi: {username} → {company_name}")
            
            return {
                'success': True,
                'user_id': int(user_id),
                'company_schema': company_schema,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"User registration error: {e}")
            return {'success': False, 'user_id': None, 'company_schema': None, 'error': str(e)}
    
    def update_user_company_schema(self, username: str, correct_company_schema: str) -> bool:
        """
        Kullanıcının company_schema bilgisini güncelle (schema adı düzeltme için)
        
        Args:
            username: Kullanıcı adı
            correct_company_schema: Doğru schema adı
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            cursor = self.connection.cursor()
            
            cursor.execute("""
                UPDATE dbo.global_users 
                SET company_schema = ?
                WHERE username = ?
            """, (correct_company_schema, username))
            
            self.connection.commit()
            
            logger.info(f"✅ Kullanıcı schema güncellendi: {username} → {correct_company_schema}")
            return True
            
        except Exception as e:
            logger.error(f"Schema update error: {e}")
            return False
    
    def update_user_password(self, username: str, new_password_hash: str) -> bool:
        """
        Kullanıcının şifresini güncelle
        
        Args:
            username: Kullanıcı adı
            new_password_hash: Yeni bcrypt hash
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            cursor = self.connection.cursor()
            
            cursor.execute("""
                UPDATE dbo.global_users 
                SET password_hash = ?
                WHERE username = ?
            """, (new_password_hash, username))
            
            self.connection.commit()
            
            logger.info(f"✅ Kullanıcı şifresi güncellendi: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Password update error: {e}")
            return False


    def fetch_table_data(self, table_name: str) -> List[Dict]:
        """
        Azure'daki bir tablodan tüm verileri çek
        
        Args:
            table_name: Tablo adı
            
        Returns:
            List of dicts (her satır bir dict)
        """
        try:
            if not self.connection:
                if not self.connect():
                    return []
            
            if not self.current_company:
                logger.warning(f"fetch_table_data: current_company belirtilmemiş")
                return []
            
            cursor = self.connection.cursor()
            
            # Company schema'dan veriyi çek (köşeli parantez ile - özel karakter desteği)
            query = f"SELECT * FROM [{self.current_company}].[{table_name}]"
            cursor.execute(query)
            
            # Kolon isimlerini al
            columns = [column[0] for column in cursor.description]
            
            # Her satırı dict'e çevir
            rows = []
            for row in cursor.fetchall():
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[columns[i]] = value
                rows.append(row_dict)
            
            logger.info(f"✅ {table_name}: {len(rows)} kayıt çekildi (Azure)")
            return rows
            
        except Exception as e:
            logger.error(f"fetch_table_data error ({table_name}): {e}")
            return []


# Test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test
    creds_dir = Path.cwd() / 'test_credentials'
    creds_dir.mkdir(exist_ok=True)
    
    manager = AzureSQLManager(creds_dir)
    
    # Credentials kaydet (ilk kez)
    # manager.save_credentials("your_username", "your_password")
    
    # Bağlan
    # if manager.connect():
    #     print("✅ Bağlantı başarılı")
    #     
    #     # Test
    #     if manager.test_connection():
    #         print("✅ Test başarılı")
    #     
    #     # Firma oluştur
    #     if manager.ensure_company_schema("Test Firma"):
    #         print("✅ Schema oluşturuldu")
    #     
    #     # Tabloları oluştur
    #     if manager.create_tables_from_sqlite_schema("Company_Test_Firma"):
    #         print("✅ Tablolar oluşturuldu")
    #     
    #     # Firmaları listele
    #     companies = manager.list_companies()
    #     print(f"Firmalar: {companies}")
    
    print("Azure SQL Manager hazır")
