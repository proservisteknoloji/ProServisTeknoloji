"""
Veritabanı yöneticisi için genel sorguları (ayarlar, kullanıcılar, müşteriler,
cihazlar) içeren mixin.

Bu modül, `DatabaseManager` sınıfına genel veritabanı işlemlerini eklemek
için tasarlanmıştır.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeneralQueriesMixin:
    """
    Genel veritabanı sorguları için bir mixin sınıfı.
    `DatabaseManager` ile birlikte kullanılır.
    """

    # --- Ayar Sorguları ---

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Veritabanından belirli bir ayarı alır."""
        res = self.fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return res['value'] if res else default

    def set_setting(self, key: str, value: Any) -> None:
        """Veritabanına bir ayarı kaydeder veya günceller."""
        self.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

    def get_all_smtp_settings(self) -> Dict[str, Any]:
        """Tüm SMTP ayarlarını bir sözlük olarak döndürür."""
        keys = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'smtp_encryption']
        settings = {key: self.get_setting(key, '') for key in keys}
        try:
            settings['smtp_port'] = int(settings.get('smtp_port') or 0)
        except (ValueError, TypeError):
            settings['smtp_port'] = 0
        return settings

    def get_all_company_info(self) -> Dict[str, str]:
        """Firma ve banka ile ilgili tüm ayarları bir sözlük olarak döndürür."""
        keys = [
            'company_name', 'company_address', 'company_phone', 'company_email', 
            'company_tax_office', 'company_tax_id', 'company_logo_path',
            'bank_name', 'bank_account_holder', 'bank_iban'
        ]
        return {key: self.get_setting(key, '') for key in keys}

    def get_api_keys(self) -> Dict[str, str]:
        """OpenAI ve Gemini için API anahtarlarını döndürür."""
        return {
            'openai_api_key': self.get_setting('openai_api_key', ''),
            'gemini_api_key': self.get_setting('gemini_api_key', '')
        }

    def update_exchange_rates(self, rates: Dict[str, float]) -> None:
        """Döviz kurlarını veritabanına kaydeder."""
        self.set_setting('usd_rate', rates.get('USD', 0.0))
        self.set_setting('eur_rate', rates.get('EUR', 0.0))
        self.set_setting('last_currency_update', datetime.now().isoformat())

    # --- Kullanıcı Sorguları ---

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Tüm kullanıcıları rolleriyle birlikte listeler (root kullanıcısı hariç)."""
        query = "SELECT id, username, role FROM users WHERE username != 'root' ORDER BY username"
        return [dict(row) for row in self.fetch_all(query)]

    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Bir kullanıcının rolünü günceller."""
        result = self.execute_query("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        return result is not None

    def get_technicians(self) -> List[Dict[str, Any]]:
        """Aktif saha teknisyenlerini listeler (technicians tablosundan)."""
        query = """
            SELECT id, name || ' ' || surname as full_name
            FROM technicians 
            WHERE is_active = 1
            ORDER BY name, surname
        """
        return [(row[0], row[1]) for row in self.fetch_all(query)]

    # --- Müşteri ve Cihaz Sorguları ---

    def add_customer(self, name: str, phone: str, email: str, address: str, tax_id: str, tax_office: str) -> Optional[int]:
        """Veritabanına yeni bir müşteri ekler."""
        query = "INSERT INTO customers (name, phone, email, address, tax_id, tax_office) VALUES (?, ?, ?, ?, ?, ?)"
        params = (name, phone, email, address, tax_id, tax_office)
        return self.execute_query(query, params)

    def update_customer(self, customer_id: int, name: str, phone: str, email: str, address: str, tax_id: str, tax_office: str) -> bool:
        """Bir müşterinin bilgilerini günceller."""
        query = "UPDATE customers SET name=?, phone=?, email=?, address=?, tax_id=?, tax_office=? WHERE id=?"
        params = (name, phone, email, address, tax_id, tax_office, customer_id)
        result = self.execute_query(query, params)
        return result is not None

    def delete_customer(self, customer_id: int) -> bool:
        """Bir müşteriyi ve ona bağlı tüm cihazları siler (CASCADE sayesinde)."""
        result = self.execute_query("DELETE FROM customers WHERE id=?", (customer_id,))
        return result is not None

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """ID ile bir müşterinin bilgilerini alır."""
        res = self.fetch_one("SELECT * FROM customers WHERE id=?", (customer_id,))
        return dict(res) if res else None

    def get_customer_id_by_name(self, name: str) -> Optional[int]:
        """İsim ile bir müşterinin ID'sini alır."""
        result = self.fetch_one("SELECT id FROM customers WHERE name = ?", (name,))
        return result['id'] if result else None

    def add_device(self, customer_id: int, model: str, serial: str, dev_type: str, is_cpc: bool, bw_price: float, color_price: float, bw_curr: str, color_curr: str, color_type: str) -> Optional[int]:
        """Bir müşteriye yeni bir cihaz ekler."""
        query = """
            INSERT INTO devices (customer_id, model, serial_number, type, is_cpc, cpc_bw_price, cpc_color_price, cpc_bw_currency, cpc_color_currency, color_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (customer_id, model, serial, dev_type, int(is_cpc), bw_price, color_price, bw_curr, color_curr, color_type)
        return self.execute_query(query, params)

    def update_device(self, device_id: int, model: str, serial: str, dev_type: str, is_cpc: bool, bw_price: float, color_price: float, bw_curr: str, color_curr: str, color_type: str) -> bool:
        """Bir cihazın bilgilerini günceller."""
        query = """
            UPDATE devices SET model=?, serial_number=?, type=?, is_cpc=?, cpc_bw_price=?, cpc_color_price=?, cpc_bw_currency=?, cpc_color_currency=?, color_type=?
            WHERE id=?
        """
        params = (model, serial, dev_type, int(is_cpc), bw_price, color_price, bw_curr, color_curr, color_type, device_id)
        result = self.execute_query(query, params)
        return result is not None

    def delete_device(self, device_id: int) -> bool:
        """Bir cihazı siler."""
        result = self.execute_query("DELETE FROM devices WHERE id=?", (device_id,))
        return result is not None

    def get_all_customers_and_devices(self) -> Dict[int, Dict[str, Any]]:
        """
        Tüm müşterileri ve onlara ait cihazları yapılandırılmış bir sözlük olarak döndürür.
        
        Returns:
            {
                customer_id_1: {'info': {...}, 'devices': [{...}, ...]},
                customer_id_2: {'info': {...}, 'devices': [{...}, ...]}
            }
        """
        query = """
            SELECT 
                c.id as customer_id, c.name, c.phone, c.email, c.address, c.tax_id, c.tax_office,
                cd.id as device_id, cd.device_model as model, cd.serial_number, cd.device_type as type, cd.is_cpc, 
                cd.bw_price as cpc_bw_price, cd.bw_currency as cpc_bw_currency, 
                cd.color_price as cpc_color_price, cd.color_currency as cpc_color_currency,
                cl.location_name, cl.address as location_address, cl.phone as location_phone
            FROM customers c 
            LEFT JOIN customer_devices cd ON c.id = cd.customer_id 
            LEFT JOIN customer_locations cl ON cd.location_id = cl.id
            ORDER BY c.name, cl.location_name, cd.device_model
        """
        rows = self.fetch_all(query)
        
        customers_data: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            cust_id = row['customer_id']
            if cust_id not in customers_data:
                customers_data[cust_id] = {
                    'info': {
                        'id': cust_id,
                        'name': row['name'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'address': row['address'],
                        'tax_id': row['tax_id'],
                        'tax_office': row['tax_office']
                    },
                    'devices': []
                }
            
            if row['device_id'] is not None:
                customers_data[cust_id]['devices'].append({
                    'id': row['device_id'],
                    'model': row['model'],
                    'serial_number': row['serial_number'],
                    'type': row['type'],
                    'is_cpc': bool(row['is_cpc']),
                    'cpc_bw_price': row['cpc_bw_price'],
                    'cpc_bw_currency': row['cpc_bw_currency'],
                    'cpc_color_price': row['cpc_color_price'],
                    'cpc_color_currency': row['cpc_color_currency'],
                    'location_name': row['location_name'] or 'Lokasyon Yok',
                    'location_address': row['location_address'] or '',
                    'location_phone': row['location_phone'] or ''
                })
                
        return customers_data

    # --- Customer Devices Sorguları ---

    def save_customer_device(self, customer_id: int, device_data: Dict[str, Any], device_id: Optional[int] = None) -> Optional[int]:
        """Müşteri cihazını kaydeder veya günceller."""
        try:
            # Eksik CPC sütunlarını kontrol edip ekle
            cpc_columns = [
                ('cpc_bw_price', 'REAL DEFAULT 0.0'),
                ('cpc_bw_currency', 'TEXT DEFAULT "TL"'),
                ('cpc_color_price', 'REAL DEFAULT 0.0'),
                ('cpc_color_currency', 'TEXT DEFAULT "TL"'),
                ('rental_fee', 'REAL DEFAULT 0.0'),
                ('rental_currency', 'TEXT DEFAULT "TL"')
            ]
            
            for column_name, column_type in cpc_columns:
                if not self._column_exists('customer_devices', column_name):
                    self._add_column_if_not_exists('customer_devices', column_name, column_type)
                    logging.info(f"'customer_devices' tablosuna '{column_name}' sütunu eklendi.")
            
            if device_id:
                # Güncelleme - tüm alanları güncelle
                query = """
                    UPDATE customer_devices 
                    SET device_model = ?, serial_number = ?, brand = ?, device_type = ?, 
                        color_type = ?, installation_date = ?, notes = ?, is_cpc = ?,
                        cpc_bw_price = ?, cpc_bw_currency = ?, cpc_color_price = ?, cpc_color_currency = ?,
                        rental_fee = ?, rental_currency = ?, location_id = ?, is_free = ?
                    WHERE id = ?
                """
                params = (
                    device_data.get('device_model', ''),
                    device_data.get('serial_number', ''),
                    device_data.get('brand', ''),
                    device_data.get('device_type', ''),
                    device_data.get('color_type', ''),
                    device_data.get('installation_date', ''),
                    device_data.get('notes', ''),
                    device_data.get('is_cpc', 0),
                    device_data.get('bw_price', 0),
                    device_data.get('bw_currency', 'TL'),
                    device_data.get('color_price', 0),
                    device_data.get('color_currency', 'TL'),
                    device_data.get('rental_fee', 0),
                    device_data.get('rental_currency', 'TL'),
                    device_data.get('location_id'),
                    device_data.get('is_free', 0),
                    device_id
                )
                self.execute_query(query, params)
                return device_id
            else:
                # Yeni ekleme
                query = """
                    INSERT INTO customer_devices 
                    (customer_id, location_id, device_model, serial_number, brand, device_type, color_type, 
                     installation_date, notes, is_cpc, cpc_bw_price, cpc_bw_currency, 
                     cpc_color_price, cpc_color_currency, rental_fee, rental_currency, is_free)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    customer_id,
                    device_data.get('location_id'),
                    device_data.get('device_model', ''),
                    device_data.get('serial_number', ''),
                    device_data.get('brand', ''),
                    device_data.get('device_type', ''),
                    device_data.get('color_type', ''),
                    device_data.get('installation_date', ''),
                    device_data.get('notes', ''),
                    device_data.get('is_cpc', 0),
                    device_data.get('bw_price', 0),
                    device_data.get('bw_currency', 'TL'),
                    device_data.get('color_price', 0),
                    device_data.get('color_currency', 'TL'),
                    device_data.get('rental_fee', 0),
                    device_data.get('rental_currency', 'TL'),
                    device_data.get('is_free', 0)
                )
                return self.execute_query(query, params)
        except Exception as e:
            logging.error(f"Customer device kaydetme hatası: {e}")
            return None

    def get_customer_devices(self, customer_id: int) -> List[Dict[str, Any]]:
        """Müşterinin cihazlarını listeler."""
        query = """
            SELECT cd.id, cd.device_model, cd.serial_number, cd.brand, cd.device_type, cd.color_type, 
                   cd.installation_date, cd.notes, cd.is_cpc, cd.cpc_bw_price, cd.cpc_bw_currency,
                   cd.cpc_color_price, cd.cpc_color_currency, cd.rental_fee, cd.rental_currency, cd.is_free,
                   cl.location_name, cl.address as location_address, cl.phone as location_phone
            FROM customer_devices cd
            LEFT JOIN customer_locations cl ON cd.location_id = cl.id
            WHERE cd.customer_id = ?
            ORDER BY cl.location_name, cd.device_model
        """
        results = self.fetch_all(query, (customer_id,))
        return [dict(row) for row in results]

    def get_customer_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Belirli bir müşteri cihazını getirir."""
        query = """
            SELECT id, customer_id, location_id, device_model, serial_number, brand, device_type, 
                   color_type, installation_date, notes, created_at, is_cpc,
                   cpc_bw_price, cpc_bw_currency, cpc_color_price, cpc_color_currency,
                   rental_fee, rental_currency
            FROM customer_devices 
            WHERE id = ?
        """
        result = self.fetch_one(query, (device_id,))
        return dict(result) if result else None

    def delete_customer_device(self, device_id: int) -> bool:
        """Müşteri cihazını siler."""
        try:
            self.execute_query("DELETE FROM customer_devices WHERE id = ?", (device_id,))
            return True
        except Exception as e:
            logging.error(f"Customer device silme hatası: {e}")
            return False

    # --- CPC Stok Yönetimi ---

    def add_cpc_stock_item(self, device_id: int, toner_code: str, toner_name: str, 
                          color: str, quantity: int = 0, min_quantity: int = 5) -> bool:
        """CPC cihazı için stok öğesi ekler."""
        try:
            query = """
                INSERT INTO cpc_stock_items 
                (device_id, toner_code, toner_name, color, quantity, min_quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.execute_query(query, (device_id, toner_code, toner_name, color, quantity, min_quantity))
            return True
        except Exception as e:
            logging.error(f"CPC stok öğesi ekleme hatası: {e}")
            return False

    def get_cpc_stock_items(self, device_id: int = None) -> List[Dict[str, Any]]:
        """CPC stok öğelerini getirir. device_id verilmezse tümünü getirir."""
        try:
            if device_id:
                query = "SELECT * FROM cpc_stock_items WHERE device_id = ? ORDER BY toner_name"
                return [dict(row) for row in self.fetch_all(query, (device_id,))]
            else:
                query = "SELECT * FROM cpc_stock_items ORDER BY device_id, toner_name"
                return [dict(row) for row in self.fetch_all(query)]
        except Exception as e:
            logging.error(f"CPC stok öğeleri getirme hatası: {e}")
            return []

    def update_cpc_stock_quantity(self, item_id: int, quantity: int) -> bool:
        """CPC stok öğesinin miktarını günceller."""
        try:
            query = "UPDATE cpc_stock_items SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.execute_query(query, (quantity, item_id))
            return True
        except Exception as e:
            logging.error(f"CPC stok miktarı güncelleme hatası: {e}")
            return False

    def get_cpc_device_counters(self, device_id: int) -> Optional[Dict[str, Any]]:
        """CPC cihazının sayaç bilgilerini getirir."""
        try:
            query = "SELECT * FROM cpc_device_counters WHERE device_id = ?"
            result = self.fetch_one(query, (device_id,))
            return dict(result) if result else None
        except Exception as e:
            logging.error(f"CPC cihaz sayaçları getirme hatası: {e}")
            return None

    def update_cpc_device_counters(self, device_id: int, bw_counter: int, color_counter: int) -> bool:
        """CPC cihazının sayaç bilgilerini günceller."""
        try:
            query = """
                INSERT OR REPLACE INTO cpc_device_counters 
                (device_id, bw_counter, color_counter, last_update)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """
            self.execute_query(query, (device_id, bw_counter, color_counter))
            return True
        except Exception as e:
            logging.error(f"CPC cihaz sayaçları güncelleme hatası: {e}")
            return False

    def get_all_cpc_devices_with_stock(self) -> List[Dict[str, Any]]:
        """Tüm CPC cihazlarını stok bilgileriyle birlikte getirir."""
        try:
            query = """
                SELECT 
                    cd.id, cd.device_model, cd.serial_number, cd.device_type, c.name as customer_name,
                    cl.location_name, cd.is_free,
                    COUNT(csi.id) as toner_count, SUM(csi.quantity) as total_quantity
                FROM customer_devices cd
                JOIN customers c ON cd.customer_id = c.id
                JOIN customer_locations cl ON cd.location_id = cl.id
                LEFT JOIN cpc_stock_items csi ON cd.id = csi.device_id
                WHERE cd.is_cpc = 1 AND cd.is_free = 0
                GROUP BY cd.id, cd.device_model, cd.serial_number, cd.device_type, c.name, cl.location_name, cd.is_free
                ORDER BY c.name, cl.location_name, cd.device_model
            """
            return [dict(row) for row in self.fetch_all(query)]
        except Exception as e:
            logging.error(f"CPC cihazları getirme hatası: {e}")
            return []

    def add_cpc_usage_history(self, device_id: int, toner_id: int, usage_date: str, 
                             bw_pages: int = 0, color_pages: int = 0, notes: str = "") -> bool:
        """CPC kullanım geçmişine yeni kayıt ekler."""
        try:
            query = """
                INSERT INTO cpc_usage_history 
                (device_id, toner_id, usage_date, bw_pages, color_pages, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.execute_query(query, [device_id, toner_id, usage_date, bw_pages, color_pages, notes])
            logging.info(f"CPC kullanım geçmişi eklendi: Device {device_id}, Toner {toner_id}")
            return True
        except Exception as e:
            logging.error(f"CPC kullanım geçmişi ekleme hatası: {e}")
            return False

    def get_cpc_usage_history(self, device_id: int, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """CPC cihazının kullanım geçmişini getirir."""
        try:
            query = """
                SELECT 
                    cuh.id, cuh.usage_date, cuh.bw_pages, cuh.color_pages, cuh.notes,
                    csi.toner_code, csi.color,
                    cd.device_model, c.name as customer_name
                FROM cpc_usage_history cuh
                JOIN cpc_stock_items csi ON cuh.toner_id = csi.id
                JOIN customer_devices cd ON cuh.device_id = cd.id
                JOIN customers c ON cd.customer_id = c.id
                WHERE cuh.device_id = ?
            """
            params = [device_id]
            
            if start_date and end_date:
                query += " AND cuh.usage_date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND cuh.usage_date >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND cuh.usage_date <= ?"
                params.append(end_date)
                
            query += " ORDER BY cuh.usage_date DESC, cuh.id DESC"
            
            return [dict(row) for row in self.fetch_all(query, params)]
        except Exception as e:
            logging.error(f"CPC kullanım geçmişi getirme hatası: {e}")
            return []

    def get_cpc_usage_summary(self, device_id: int, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """CPC cihazının kullanım özetini getirir."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_records,
                    SUM(bw_pages) as total_bw_pages,
                    SUM(color_pages) as total_color_pages,
                    MIN(usage_date) as first_usage,
                    MAX(usage_date) as last_usage
                FROM cpc_usage_history
                WHERE device_id = ?
            """
            params = [device_id]
            
            if start_date and end_date:
                query += " AND usage_date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND usage_date >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND usage_date <= ?"
                params.append(end_date)
                
            result = self.fetch_one(query, params)
            return dict(result) if result else {}
        except Exception as e:
            logging.error(f"CPC kullanım özeti getirme hatası: {e}")
            return {}

