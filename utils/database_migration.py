import sqlite3
import logging
from pathlib import Path

class DatabaseMigration:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    def add_missing_columns(self):
        """Eksik kolonları ekler"""
        try:
            cursor = self.db_manager.get_connection().cursor()
            
            # pending_sales tablosuna sale_data_json kolonu ekle
            try:
                cursor.execute("ALTER TABLE pending_sales ADD COLUMN sale_data_json TEXT")
                logging.info("sale_data_json kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("sale_data_json kolonu zaten mevcut.")
                else:
                    raise
            
            # devices tablosuna rental_fee ve rental_currency kolonları ekle
            try:
                cursor.execute("ALTER TABLE devices ADD COLUMN rental_fee DECIMAL(10,4) DEFAULT 0")
                logging.info("devices tablosuna rental_fee kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("rental_fee kolonu zaten mevcut.")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE devices ADD COLUMN rental_currency VARCHAR(3) DEFAULT 'TL'")
                logging.info("devices tablosuna rental_currency kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("rental_currency kolonu zaten mevcut.")
                else:
                    raise
            
            # customer_devices tablosuna rental_fee ve rental_currency kolonları ekle
            try:
                cursor.execute("ALTER TABLE customer_devices ADD COLUMN rental_fee DECIMAL(10,4) DEFAULT 0")
                logging.info("customer_devices tablosuna rental_fee kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("customer_devices rental_fee kolonu zaten mevcut.")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE customer_devices ADD COLUMN rental_currency VARCHAR(3) DEFAULT 'TL'")
                logging.info("customer_devices tablosuna rental_currency kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("customer_devices rental_currency kolonu zaten mevcut.")
                else:
                    raise
            
            # customer_devices tablosuna CPC fiyat kolonları ekle
            try:
                cursor.execute("ALTER TABLE customer_devices ADD COLUMN cpc_bw_price DECIMAL(10,4) DEFAULT 0")
                logging.info("customer_devices tablosuna cpc_bw_price kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("customer_devices cpc_bw_price kolonu zaten mevcut.")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE customer_devices ADD COLUMN cpc_bw_currency VARCHAR(3) DEFAULT 'TL'")
                logging.info("customer_devices tablosuna cpc_bw_currency kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("customer_devices cpc_bw_currency kolonu zaten mevcut.")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE customer_devices ADD COLUMN cpc_color_price DECIMAL(10,4) DEFAULT 0")
                logging.info("customer_devices tablosuna cpc_color_price kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("customer_devices cpc_color_price kolonu zaten mevcut.")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE customer_devices ADD COLUMN cpc_color_currency VARCHAR(3) DEFAULT 'TL'")
                logging.info("customer_devices tablosuna cpc_color_currency kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("customer_devices cpc_color_currency kolonu zaten mevcut.")
                else:
                    raise
            
            # customers tablosuna contract_pdf_path kolonu ekle
            try:
                cursor.execute("ALTER TABLE customers ADD COLUMN contract_pdf_path TEXT")
                logging.info("customers tablosuna contract_pdf_path kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("contract_pdf_path kolonu zaten mevcut.")
                else:
                    raise
            
            # service_records tablosuna technician_id kolonu ekle
            try:
                cursor.execute("ALTER TABLE service_records ADD COLUMN technician_id INTEGER")
                logging.info("service_records tablosuna technician_id kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("technician_id kolonu zaten mevcut.")
                else:
                    raise
            
            # service_records tablosuna assigned_user_id kolonu ekle
            try:
                cursor.execute("ALTER TABLE service_records ADD COLUMN assigned_user_id INTEGER")
                logging.info("service_records tablosuna assigned_user_id kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("assigned_user_id kolonu zaten mevcut.")
                else:
                    raise
            
            # service_records tablosuna completed_date kolonu ekle
            try:
                cursor.execute("ALTER TABLE service_records ADD COLUMN completed_date TEXT")
                logging.info("service_records tablosuna completed_date kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("completed_date kolonu zaten mevcut.")
                else:
                    raise
            
            # service_records tablosuna technician_report kolonu ekle
            try:
                cursor.execute("ALTER TABLE service_records ADD COLUMN technician_report TEXT")
                logging.info("service_records tablosuna technician_report kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("technician_report kolonu zaten mevcut.")
                else:
                    raise
            
            # service_records tablosuna service_form_pdf_path kolonu ekle
            try:
                cursor.execute("ALTER TABLE service_records ADD COLUMN service_form_pdf_path TEXT")
                logging.info("service_records tablosuna service_form_pdf_path kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("service_form_pdf_path kolonu zaten mevcut.")
                else:
                    raise
            
            # pending_sales tablosuna invoice_id kolonu ekle
            try:
                cursor.execute("ALTER TABLE pending_sales ADD COLUMN invoice_id INTEGER")
                logging.info("pending_sales tablosuna invoice_id kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("invoice_id kolonu zaten mevcut.")
                else:
                    raise
            
            # invoices tablosuna exchange_rate kolonu ekle (fatura kesildiğindeki kur)
            try:
                cursor.execute("ALTER TABLE invoices ADD COLUMN exchange_rate REAL DEFAULT 1.0")
                logging.info("invoices tablosuna exchange_rate kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("invoices exchange_rate kolonu zaten mevcut.")
                else:
                    raise
            
            # stock_items tablosuna location kolonu ekle
            try:
                cursor.execute("ALTER TABLE stock_items ADD COLUMN location TEXT")
                logging.info("stock_items tablosuna location kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("location kolonu zaten mevcut.")
                else:
                    raise
            
            # stock_items tablosuna min_stock_level kolonu ekle
            try:
                cursor.execute("ALTER TABLE stock_items ADD COLUMN min_stock_level INTEGER DEFAULT 0")
                logging.info("stock_items tablosuna min_stock_level kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("min_stock_level kolonu zaten mevcut.")
                else:
                    raise
            
            # pending_sales tablosuna total_amount kolonu ekle
            try:
                cursor.execute("ALTER TABLE pending_sales ADD COLUMN total_amount REAL DEFAULT 0")
                logging.info("pending_sales tablosuna total_amount kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("total_amount kolonu zaten mevcut.")
                else:
                    raise
            
            # pending_sales tablosuna currency kolonu ekle
            try:
                cursor.execute("ALTER TABLE pending_sales ADD COLUMN currency TEXT DEFAULT 'TL'")
                logging.info("pending_sales tablosuna currency kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("currency kolonu zaten mevcut.")
                else:
                    raise
            
            # pending_sales tablosuna items_json kolonu ekle
            try:
                cursor.execute("ALTER TABLE pending_sales ADD COLUMN items_json TEXT")
                logging.info("pending_sales tablosuna items_json kolonu eklendi.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logging.info("items_json kolonu zaten mevcut.")
                else:
                    raise
            
            self.db_manager.get_connection().commit()
            return True
            
        except Exception as e:
            logging.error(f"Migration hatası: {e}")
            return False
    
    def check_and_fix_database(self):
        """Veritabanını kontrol eder ve gerekli düzeltmeleri yapar"""
        try:
            cursor = self.db_manager.get_connection().cursor()
            
            # pending_sales tablosunun kolonlarını kontrol et
            cursor.execute("PRAGMA table_info(pending_sales)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # devices tablosunun kolonlarını kontrol et
            cursor.execute("PRAGMA table_info(devices)")
            device_columns = [column[1] for column in cursor.fetchall()]
            
            # customers tablosunun kolonlarını kontrol et
            cursor.execute("PRAGMA table_info(customers)")
            customer_columns = [column[1] for column in cursor.fetchall()]
            
            # customer_devices tablosunun kolonlarını kontrol et
            cursor.execute("PRAGMA table_info(customer_devices)")
            customer_device_columns = [column[1] for column in cursor.fetchall()]
            
            # service_records tablosunun kolonlarını kontrol et
            cursor.execute("PRAGMA table_info(service_records)")
            service_columns = [column[1] for column in cursor.fetchall()]
            
            # stock_items tablosunun kolonlarını kontrol et
            cursor.execute("PRAGMA table_info(stock_items)")
            stock_columns = [column[1] for column in cursor.fetchall()]
            
            missing_columns = False
            
            if 'sale_data_json' not in columns:
                logging.info("sale_data_json kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'invoice_id' not in columns:
                logging.info("invoice_id kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'rental_fee' not in device_columns:
                logging.info("rental_fee kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'rental_currency' not in device_columns:
                logging.info("rental_currency kolonu eksik, ekleniyor...")
                missing_columns = True
                
            # customer_devices tablosu için rental kolonlarını kontrol et
            if 'rental_fee' not in customer_device_columns:
                logging.info("customer_devices rental_fee kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'rental_currency' not in customer_device_columns:
                logging.info("customer_devices rental_currency kolonu eksik, ekleniyor...")
                missing_columns = True
                
            # customer_devices tablosu için CPC kolonlarını kontrol et
            if 'cpc_bw_price' not in customer_device_columns:
                logging.info("customer_devices cpc_bw_price kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'cpc_bw_currency' not in customer_device_columns:
                logging.info("customer_devices cpc_bw_currency kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'cpc_color_price' not in customer_device_columns:
                logging.info("customer_devices cpc_color_price kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'cpc_color_currency' not in customer_device_columns:
                logging.info("customer_devices cpc_color_currency kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'contract_pdf_path' not in customer_columns:
                logging.info("contract_pdf_path kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'technician_id' not in service_columns:
                logging.info("technician_id kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'assigned_user_id' not in service_columns:
                logging.info("assigned_user_id kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'technician_report' not in service_columns:
                logging.info("technician_report kolonu eksik, ekleniyor...")
                missing_columns = True
                
            if 'service_form_pdf_path' not in service_columns:
                logging.info("service_form_pdf_path kolonu eksik, ekleniyor...")
                missing_columns = True
            
            if 'location' not in stock_columns:
                logging.info("location kolonu eksik, ekleniyor...")
                missing_columns = True
            
            if 'min_stock_level' not in stock_columns:
                logging.info("min_stock_level kolonu eksik, ekleniyor...")
                missing_columns = True
            
            if missing_columns:
                return self.add_missing_columns()
            else:
                logging.info("Veritabanı şeması güncel.")
                return True
                
        except Exception as e:
            logging.error(f"Veritabanı kontrol hatası: {e}")
            return False
    
    def create_missing_tables(self):
        """Eksik tabloları oluşturur"""
        try:
            cursor = self.db_manager.get_connection().cursor()
            
            # price_settings tablosunu oluştur
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_settings (
                    id INTEGER PRIMARY KEY,
                    settings_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logging.info("price_settings tablosu oluşturuldu/kontrol edildi.")
            
            # Varsayılan fiyat ayarlarını ekle
            cursor.execute("SELECT COUNT(*) FROM price_settings")
            if cursor.fetchone()[0] == 0:
                default_settings = '''{"default_margin": 20.0, "currency": "TL", "tax_rate": 18.0}'''
                cursor.execute(
                    "INSERT INTO price_settings (id, settings_json) VALUES (1, ?)",
                    (default_settings,)
                )
                logging.info("Varsayılan fiyat ayarları eklendi.")
            
            # custom_price_margins tablosunu oluştur
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_price_margins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_item_id INTEGER NOT NULL,
                    custom_margin DECIMAL(5,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_item_id) REFERENCES stock_items(id),
                    UNIQUE(stock_item_id)
                )
            """)
            logging.info("custom_price_margins tablosu oluşturuldu/kontrol edildi.")
            
            # company_info tablosunu oluştur
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_info (
                    id INTEGER PRIMARY KEY,
                    company_name TEXT,
                    tax_office TEXT,
                    tax_number TEXT,
                    address TEXT,
                    phone TEXT,
                    email TEXT,
                    logo_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logging.info("company_info tablosu oluşturuldu/kontrol edildi.")
            
            self.db_manager.get_connection().commit()
            return True
            
        except Exception as e:
            logging.error(f"Tablo oluşturma hatası: {e}")
            return False
    
    def create_cpc_stock_tables(self):
        """CPC stok yönetimi için yeni tablolar oluşturur"""
        try:
            cursor = self.db_manager.get_connection().cursor()
            
            # CPC stok öğeleri tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cpc_stock_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    toner_code VARCHAR(50) NOT NULL,
                    toner_name VARCHAR(100),
                    color VARCHAR(20),
                    quantity INTEGER DEFAULT 0,
                    min_quantity INTEGER DEFAULT 5,
                    location VARCHAR(100),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES customer_devices(id)
                )
            """)
            logging.info("cpc_stock_items tablosu oluşturuldu/kontrol edildi.")
            
            # CPC cihaz sayaçları tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cpc_device_counters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    bw_counter INTEGER DEFAULT 0,
                    color_counter INTEGER DEFAULT 0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES customer_devices(id)
                )
            """)
            logging.info("cpc_device_counters tablosu oluşturuldu/kontrol edildi.")
            
            # CPC kullanım geçmişi tablosu
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cpc_usage_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id INTEGER NOT NULL,
                        toner_id INTEGER NOT NULL,
                        usage_date DATE NOT NULL,
                        bw_pages INTEGER DEFAULT 0,
                        color_pages INTEGER DEFAULT 0,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (device_id) REFERENCES customer_devices(id),
                        FOREIGN KEY (toner_id) REFERENCES cpc_stock_items(id)
                    )
                """)
                logging.info("cpc_usage_history tablosu oluşturuldu/kontrol edildi.")
            except Exception as e:
                logging.error(f"cpc_usage_history tablosu oluşturma hatası: {e}")
                return False
            
            self.db_manager.get_connection().commit()
            return True
            
        except Exception as e:
            logging.error(f"CPC tablo oluşturma hatası: {e}")
            return False
    
    def run_full_migration(self):
        """Tüm migration işlemlerini çalıştırır"""
        try:
            logging.info("Database migration başlatılıyor...")
            
            # Önce eksik tabloları oluştur
            if not self.create_missing_tables():
                logging.error("Tablo oluşturma başarısız!")
                return False
            
            # CPC stok tablolarını oluştur
            if not self.create_cpc_stock_tables():
                logging.error("CPC tablo oluşturma başarısız!")
                return False
            
            # Eksik kolonları ekle
            if not self.add_missing_columns():
                logging.error("Kolon ekleme başarısız!")
                return False
            
            # Sonra database'i kontrol et ve düzelt
            if not self.check_and_fix_database():
                logging.error("Database düzeltme başarısız!")
                return False
            
            # Performans için index'leri oluştur
            if not self.create_performance_indexes():
                logging.warning("Index oluşturma başarısız - performans düşük olabilir")
            
            logging.info("Database migration başarıyla tamamlandı.")
            return True
            
        except Exception as e:
            logging.error(f"Migration hatası: {e}")
            return False
    
    def create_performance_indexes(self):
        """Performans artışı için database index'lerini oluşturur"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            logging.info("Performans index'leri oluşturuluyor...")
            
            # Customers tablosu index'leri
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customers_name 
                ON customers(name)
            """)
            logging.info("customers.name index'i oluşturuldu")
            
            # Devices tablosu index'leri
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_serial 
                ON devices(serial_number)
            """)
            logging.info("devices.serial_number index'i oluşturuldu")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_customer 
                ON devices(customer_id)
            """)
            logging.info("devices.customer_id index'i oluşturuldu")
            
            # Customer_devices tablosu index'leri
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_devices_serial 
                ON customer_devices(serial_number)
            """)
            logging.info("customer_devices.serial_number index'i oluşturuldu")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_devices_customer 
                ON customer_devices(customer_id)
            """)
            logging.info("customer_devices.customer_id index'i oluşturuldu")
            
            # Service records index'leri
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_service_device 
                ON service_records(device_id)
            """)
            logging.info("service_records.device_id index'i oluşturuldu")
            
            conn.commit()
            logging.info("✅ Tüm performans index'leri başarıyla oluşturuldu")
            return True
            
        except Exception as e:
            logging.error(f"Index oluşturma hatası: {e}")
            return False