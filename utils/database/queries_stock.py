# utils/database/queries_stock.py

"""
Veritabanı yöneticisi için stok kalemleri, stok hareketleri ve envanter
yönetimi ile ilgili sorguları içeren mixin.

Bu modül, `DatabaseManager` sınıfına stok yönetimiyle ilgili veritabanı
fonksiyonlarını eklemek için tasarlanmıştır.
"""
# type: ignore

import logging
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union

# Logging yapılandırması
logger = logging.getLogger(__name__)

class StockQueriesMixin:
    """
    Stok kalemleri, stok hareketleri ve envanter yönetimi için veritabanı
    sorgularını içeren bir mixin sınıfı. `DatabaseManager` ile birlikte kullanılır.
    """

    def get_stock_items(self, filter_text: str = '') -> List[Dict[str, Any]]:
        """
        Stok kalemlerini filtreleyerek listeler.
        """
        query = "SELECT id, item_type, name, part_number, quantity, compatible_models FROM stock_items"
        params = []
        if filter_text:
            # --- GÜNCELLEME: Uyumlu Modeller içinde de arama yap ---
            query += " WHERE name LIKE ? OR part_number LIKE ? OR compatible_models LIKE ?"
            params.extend([f'%{filter_text}%', f'%{filter_text}%', f'%{filter_text}%'])
        query += " ORDER BY item_type, name"
        return [dict(row) for row in self.fetch_all(query, tuple(params))]

    def get_stock_items_for_sale(self, filter_text: str = '') -> List[Dict[str, Any]]:
        """
        Sadece stok miktarı 0'dan büyük olan satılabilir ürünleri listeler.
        """
        query = "SELECT id, item_type, name, quantity, sale_price, sale_currency, compatible_models FROM stock_items WHERE quantity > 0"
        params = []
        if filter_text:
            # --- GÜNCELLEME: Uyumlu Modeller içinde de arama yap ---
            query += " AND (name LIKE ? OR part_number LIKE ? OR compatible_models LIKE ?)"
            params.extend([f'%{filter_text}%', f'%{filter_text}%', f'%{filter_text}%'])
        query += " ORDER BY item_type, name"
        return [dict(row) for row in self.fetch_all(query, tuple(params))]

    def get_stock_item_details(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Belirli bir stok kaleminin tüm detaylarını döndürür.
        """
        row = self.fetch_one("SELECT * FROM stock_items WHERE id = ?", (item_id,))
        return dict(row) if row else None

    def get_stock_movements(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Belirli bir stok kalemine ait t??m stok hareketlerini listeler.
        """
        try:
            cols = [row[1] for row in self.fetch_all("PRAGMA table_info(stock_movements)")]
            if 'quantity_after' not in cols:
                self.execute_query("ALTER TABLE stock_movements ADD COLUMN quantity_after REAL")
                cols.append('quantity_after')
            if 'unit_price' not in cols:
                self.execute_query("ALTER TABLE stock_movements ADD COLUMN unit_price REAL")
                cols.append('unit_price')
            if 'currency' not in cols:
                self.execute_query("ALTER TABLE stock_movements ADD COLUMN currency TEXT")
                cols.append('currency')
        except Exception:
            cols = []

        if 'quantity_after' in cols and 'unit_price' in cols and 'currency' in cols:
            query = "SELECT movement_date, movement_type, quantity_changed, quantity_after, unit_price, currency, notes FROM stock_movements WHERE stock_item_id = ? ORDER BY movement_date DESC"
        else:
            query = "SELECT movement_date, movement_type, quantity_changed, notes FROM stock_movements WHERE stock_item_id = ? ORDER BY movement_date DESC"

        movements = [dict(row) for row in self.fetch_all(query, (item_id,))]

        # Backfill display values if missing (legacy movements)
        try:
            stock_row = self.fetch_one("SELECT purchase_price, purchase_currency, sale_price, sale_currency FROM stock_items WHERE id = ?", (item_id,))
            if stock_row:
                purchase_price = float(stock_row[0]) if stock_row[0] is not None else 0.0
                purchase_currency = stock_row[1] or 'TL'
                sale_price = float(stock_row[2]) if stock_row[2] is not None else 0.0
                sale_currency = stock_row[3] or 'TL'
            else:
                purchase_price = 0.0
                purchase_currency = 'TL'
                sale_price = 0.0
                sale_currency = 'TL'
        except Exception:
            purchase_price = 0.0
            purchase_currency = 'TL'
            sale_price = 0.0
            sale_currency = 'TL'

        for mv in movements:
            if 'unit_price' not in mv or mv.get('unit_price') in (None, 0, ''):
                movement_type = (mv.get('movement_type') or '')
                movement_type_lower = movement_type.lower()
                quantity_changed = mv.get('quantity_changed', 0)

                is_in = False
                is_out = False
                if quantity_changed > 0:
                    is_in = True
                elif quantity_changed < 0:
                    is_out = True
                else:
                    # Fallback to text match when quantity is 0/unknown
                    in_tokens = ['giriş', 'giris', 'giriåÿ', 'giri?', 'stok giri', 'iade']
                    out_tokens = ['çıkış', 'cikis', 'ã‡ä±kä±åÿ', '??k??', 'stok çık', 'stok cik', 'satış', 'satis']
                    if any(token in movement_type_lower for token in in_tokens):
                        is_in = True
                    elif any(token in movement_type_lower for token in out_tokens):
                        is_out = True

                if is_in:
                    mv['unit_price'] = purchase_price
                    mv['currency'] = purchase_currency
                elif is_out:
                    mv['unit_price'] = sale_price
                    mv['currency'] = sale_currency
        return movements

    def save_stock_item(self, data: Dict[str, Any], item_id: Optional[int] = None) -> Optional[int]:
        """
        Yeni bir stok kalemi ekler veya mevcut birini günceller.
        """
        color_type = data.get('color_type', 'Siyah-Beyaz')
        compatible_models = data.get('compatible_models', '') # --- GÜNCELLEME: Veriyi al ---

        if item_id:
            # --- GÜNCELLEME: UPDATE sorgusuna compatible_models eklendi ---
            query = """
                UPDATE stock_items 
                SET item_type=?, name=?, part_number=?, description=?, supplier=?, 
                    purchase_price=?, purchase_currency=?, sale_price=?, sale_currency=?, 
                    color_type=?, compatible_models=? 
                WHERE id=?
            """
            params = (
                data['item_type'], data['name'], data['part_number'], data['description'], 
                data.get('supplier'), data.get('purchase_price'), data.get('purchase_currency'), 
                data.get('sale_price'), data.get('sale_currency'), 
                color_type, compatible_models, item_id
            )
            result = self.execute_query(query, params)
            return item_id if result is not None else None
        else:
            # --- GÜNCELLEME: INSERT sorgusuna compatible_models eklendi ---
            query = """
                INSERT INTO stock_items (
                    item_type, name, part_number, description, supplier, quantity, 
                    purchase_price, purchase_currency, sale_price, sale_currency, 
                    color_type, compatible_models
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data['item_type'], data['name'], data['part_number'], data['description'], 
                data.get('supplier'), data.get('quantity', 0), 
                data.get('purchase_price'), data.get('purchase_currency'), 
                data.get('sale_price'), data.get('sale_currency'), 
                color_type, compatible_models
            )
            return self.execute_query(query, params)

    def add_stock_movement(self, item_id: int, movement_type: str, quantity: int, notes: str, related_service_id: Optional[int] = None, related_invoice_id: Optional[int] = None, unit_price: Optional[float] = None, currency: Optional[str] = None) -> Union[bool, str]:
        """
        Bir stok kalemi için stok hareketi ekler ve stok miktarını günceller.
        """
        conn = self.get_connection()
        if not conn: return False
        
        try:
            with conn:
                # ensure movement detail columns exist
                cols = [row[1] for row in conn.execute('PRAGMA table_info(stock_movements)').fetchall()]
                if 'quantity_after' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN quantity_after REAL')
                if 'unit_price' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN unit_price REAL')
                if 'currency' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN currency TEXT')

                cursor = conn.cursor()
                current_quantity_row = cursor.execute("SELECT quantity FROM stock_items WHERE id = ?", (item_id,)).fetchone()
                if not current_quantity_row:
                    raise ValueError(f"Stok kalemi ID {item_id} bulunamadı.")
                
                current_quantity = current_quantity_row[0]
                quantity_changed = 0

                if movement_type == 'Giriş':
                    new_quantity = current_quantity + quantity
                    quantity_changed = quantity
                elif movement_type == 'Çıkış':
                    if current_quantity < quantity:
                        logging.warning(f"Yetersiz stok denemesi: ID {item_id}, mevcut {current_quantity}, istenen {quantity}")
                        return "Yetersiz Stok"
                    new_quantity = current_quantity - quantity
                    quantity_changed = -quantity
                else:
                    raise ValueError(f"Geçersiz hareket tipi: {movement_type}")

                cursor.execute("UPDATE stock_items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
                
                movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(
                    "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes, related_service_id, related_invoice_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item_id, movement_type, quantity_changed, new_quantity, unit_price, currency, movement_date, notes, related_service_id, related_invoice_id)
                )
            logging.info(f"Stok hareketi eklendi: ID {item_id}, Tip {movement_type}, Miktar {quantity}")
            return True
        except Exception as e:
            logging.error(f"Stok hareketi hatası: {e}", exc_info=True)
            return False

    def get_spare_parts(self, filter_text: str = '') -> List[Dict[str, Any]]:
        """
        'Yedek Parça' tipindeki stok kalemlerini listeler.
        """
        query = "SELECT id, name, part_number, quantity, sale_price, sale_currency, compatible_models FROM stock_items WHERE item_type = 'Yedek Parça'"
        params = []
        if filter_text:
            # --- GÜNCELLEME: Uyumlu Modeller içinde de arama yap ---
            query += " AND (name LIKE ? OR part_number LIKE ? OR compatible_models LIKE ?)"
            params.extend([f'%{filter_text}%', f'%{filter_text}%', f'%{filter_text}%'])
        query += " ORDER BY name"
        return [dict(row) for row in self.fetch_all(query, tuple(params))]

    def sell_bulk_stock_devices_to_customer(self, stock_item_id: int, customer_id: int, sale_price: Decimal, sale_currency: str, serial_numbers: List[str]) -> Union[bool, str]:
        """
        Toplu olarak cihazları bir müşteriye satar, stoktan düşer ve fatura oluşturur.
        """
        conn = self.get_connection()
        if not conn: return "Veritabanı bağlantısı kurulamadı."
        
        quantity_to_sell = len(serial_numbers)
        if quantity_to_sell == 0: return "Satılacak cihaz seri numarası belirtilmedi."

        try:
            with conn:
                # ensure movement detail columns exist
                cols = [row[1] for row in conn.execute('PRAGMA table_info(stock_movements)').fetchall()]
                if 'quantity_after' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN quantity_after REAL')
                if 'unit_price' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN unit_price REAL')
                if 'currency' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN currency TEXT')

                cursor = conn.cursor()
                item_info = cursor.execute("SELECT name, item_type, quantity, color_type FROM stock_items WHERE id = ?", (stock_item_id,)).fetchone()
                if not item_info: raise ValueError("Stok kalemi bulunamadı.")
                item_name, item_type, current_quantity, color_type = item_info
                if item_type != 'Cihaz': raise ValueError("Sadece 'Cihaz' tipindeki ürünler bu yöntemle satılabilir.")
                if current_quantity < quantity_to_sell: raise ValueError(f"Yetersiz Stok! Mevcut: {current_quantity}, İstenen: {quantity_to_sell}")

                # Cihazları ve fatura kalemlerini oluştur
                invoice_items = []
                for serial in serial_numbers:
                    # type alanı: color_type'a göre atanır
                    device_type = color_type if color_type in ['Renkli', 'Siyah-Beyaz'] else 'Bilinmiyor'
                    # Önce devices tablosuna ekle (eski sistem uyumluluğu için)
                    cursor.execute("INSERT INTO devices (customer_id, model, serial_number, type, is_cpc, color_type) VALUES (?, ?, ?, ?, ?, ?)", 
                                   (customer_id, item_name, serial, device_type, False, color_type))
                    # Sonra customer_devices tablosuna da ekle (yeni sistem)
                    cursor.execute("""
                        INSERT INTO customer_devices 
                        (customer_id, device_model, serial_number, device_type, color_type, is_cpc, installation_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (customer_id, item_name, serial, 'Yazıcı', color_type, 0, datetime.now().strftime('%Y-%m-%d')))
                    invoice_items.append({'description': f"{item_name} ({serial}) Cihaz Satışı", 'quantity': 1, 'unit_price': float(sale_price)})
                
                # Faturayı oluştur
                total_amount = Decimal(str(sale_price)) * Decimal(str(quantity_to_sell))
                rates = get_exchange_rates()
                enriched_items = []
                for item in invoice_items:
                    item_currency = (item.get('currency', 'TL') or 'TL').strip().upper()
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    quantity = Decimal(str(item.get('quantity', 0)))
                    rate = Decimal(str(rates.get(item_currency, 1.0))) if item_currency != 'TL' else Decimal('1')
                    unit_price_tl = unit_price * rate
                    total_tl = unit_price_tl * quantity
                    enriched = dict(item)
                    enriched['currency'] = item_currency
                    enriched['exchange_rate'] = float(rate)
                    enriched['unit_price_tl'] = float(unit_price_tl)
                    enriched['total_tl'] = float(total_tl)
                    enriched_items.append(enriched)
                invoice_date = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    "INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (customer_id, 'Cihaz Satış', customer_id, invoice_date, float(total_amount), sale_currency, json.dumps(enriched_items, ensure_ascii=False))
                )
                invoice_id = cursor.lastrowid

                # Satılan müşterinin adını al
                customer_row = cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,)).fetchone()
                customer_name = customer_row[0] if customer_row else f"ID:{customer_id}"
                # Stoktan düş ve hareket kaydı oluştur
                cursor.execute("UPDATE stock_items SET quantity = quantity - ? WHERE id = ?", (quantity_to_sell, stock_item_id))
                notes = f"{quantity_to_sell} adet cihaz {customer_name} müşterisine satıldı (Fatura No: {invoice_id})"
                movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_quantity = current_quantity - quantity_to_sell
                cursor.execute(
                    "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes, related_invoice_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (stock_item_id, '\u00c7\u0131k\u0131\u015f', -quantity_to_sell, new_quantity, float(sale_price), sale_currency, movement_date, notes, invoice_id)
                )
            
            logging.info(f"{quantity_to_sell} adet cihaz (Stok ID: {stock_item_id}) müşteri ID {customer_id} için satıldı. Fatura No: {invoice_id}")
            return True
        except ValueError as e:
            logging.warning(f"Toplu cihaz satışı doğrulama hatası: {e}")
            return str(e)
        except sqlite3.IntegrityError:
            logging.error("Toplu cihaz satışı sırasında seri numarası çakışması.", exc_info=True)
            return "Girilen seri numaralarından biri zaten başka bir müşteriye kayıtlı. Lütfen kontrol edin."
        except Exception as e:
            logging.error(f"Toplu cihaz satışı sırasında beklenmedik hata: {e}", exc_info=True)
            return f"Beklenmedik bir hata oluştu: {e}"

    def _find_consignment_item(self, serial_number: str) -> Optional[int]:
        """Verilen seri numarasına sahip emanet cihazın stok ID'sini bulur."""
        query = "SELECT id FROM stock_items WHERE part_number = ? AND is_consignment = 1"
        result = self.fetch_one(query, (serial_number,))
        return result[0] if result else None

    def add_consignment_device_to_stock(self, device_info: Dict[str, str]) -> Optional[int]:
        """
        Servis için gelen bir emanet cihazı stoğa ekler veya miktarını günceller.
        """
        serial = device_info['serial']
        name = device_info['name']
        
        existing_id = self._find_consignment_item(serial)
        
        if existing_id:
            logging.info(f"Mevcut emanet cihaz ({serial}) tekrar stoğa ekleniyor.")
            self.execute_query("UPDATE stock_items SET quantity = 1 WHERE id = ?", (existing_id,))
            self.add_stock_movement(item_id=existing_id, movement_type='Giriş', quantity=1, notes='Tekrar servis için emanete alındı')
            return existing_id
        
        logging.info(f"Yeni emanet cihaz ({serial}) stoğa ekleniyor.")
        query = "INSERT INTO stock_items (item_type, name, part_number, quantity, is_consignment, description) VALUES ('Cihaz', ?, ?, 1, 1, 'Müşteri emanet cihazı')"
        stock_item_id = self.execute_query(query, (name, serial))
        
        if stock_item_id:
            self.add_stock_movement(item_id=stock_item_id, movement_type='Giriş', quantity=1, notes='Servis için emanete alındı')
        
        return stock_item_id

    def remove_consignment_device_from_stock(self, serial_number: str, service_id: int) -> bool:
        """
        Servisi tamamlanan emanet cihazı stoktan düşer.
        """
        stock_item_id = self._find_consignment_item(serial_number)
        if not stock_item_id:
            logging.warning(f"Stoktan düşülecek emanet cihaz ({serial_number}) bulunamadı.")
            return False
            
        notes = f'Servis No {service_id} tamamlandı, müşteriye teslim edildi.'
        result = self.add_stock_movement(
            item_id=stock_item_id, 
            movement_type='Çıkış', 
            quantity=1, 
            notes=notes, 
            related_service_id=service_id
        )
        
        if result is True:
            logging.info(f"Emanet cihaz ({serial_number}) stoktan düşüldü.")
            return True
        else:
            logging.error(f"Emanet cihaz ({serial_number}) stoktan düşülemedi. Sebep: {result}")
            return False

    def sell_items_and_create_invoice(self, sale_data: dict) -> Union[int, str]:
        """
        Cihaz, toner ve sarf malzeme satışı için stoktan düşüm, cihazı müşteri envanterine ekleme ve tek fatura oluşturma işlemlerini yapar.
        """
        conn = self.get_connection()
        if not conn:
            return "Veritabanı bağlantısı kurulamadı."
        
        invoice_id = -1
        try:
            with conn:
                # ensure movement detail columns exist
                cols = [row[1] for row in conn.execute('PRAGMA table_info(stock_movements)').fetchall()]
                if 'quantity_after' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN quantity_after REAL')
                if 'unit_price' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN unit_price REAL')
                if 'currency' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN currency TEXT')

                cursor = conn.cursor()
                customer_id = sale_data['customer_id']
                invoice_items = []
                total_amount = Decimal('0.0')
                movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Başta tanımla
                # Para birimini belirle (ilk öğeden al, yoksa TL varsay)
                all_items = sale_data.get('devices', []) + sale_data.get('toners', []) + sale_data.get('consumables', [])
                currency = all_items[0]['currency'] if all_items else 'TL'

                # Cihazlar
                customer_row = cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,)).fetchone()
                customer_name = customer_row[0] if customer_row else f"ID:{customer_id}"
                
                for device in sale_data.get('devices', []):
                    item_id = device['stock_item_id']
                    model = device['model']
                    qty = device['quantity']
                    unit_price = Decimal(str(device['unit_price']))
                    serials = device['serial_numbers']
                    
                    stock_row = cursor.execute("SELECT quantity, color_type FROM stock_items WHERE id = ?", (item_id,)).fetchone()
                    if not stock_row or stock_row[0] < qty:
                        raise ValueError(f"Yetersiz stok: {model}")
                    
                    color_type = stock_row['color_type']

                    for serial in serials:
                        # Önce devices tablosuna ekle (eski sistem uyumluluğu için)
                        cursor.execute("INSERT INTO devices (customer_id, model, serial_number, type, is_cpc, color_type) VALUES (?, ?, ?, ?, ?, ?)", 
                                       (customer_id, model, serial, color_type, False, color_type))
                        # Sonra customer_devices tablosuna da ekle (yeni sistem)
                        cursor.execute("""
                            INSERT INTO customer_devices 
                            (customer_id, device_model, serial_number, device_type, color_type, is_cpc, installation_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (customer_id, model, serial, 'Yazıcı', color_type, 0, datetime.now().strftime('%Y-%m-%d')))
                        invoice_items.append({'description': f"{model} ({serial}) Cihaz Satışı", 'quantity': 1, 'unit_price': float(unit_price), 'currency': currency})
                    
                    cursor.execute("UPDATE stock_items SET quantity = quantity - ? WHERE id = ?", (qty, item_id))
                    new_quantity = stock_row[0] - qty
                    cursor.execute(
                        "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (item_id, 'Çıkış', -qty, new_quantity, float(unit_price), currency, movement_date, f"{qty} adet cihaz {customer_name} müşterisine satıldı")
                    )
                    total_amount += unit_price * Decimal(str(qty))

                # Sarf malzemeler
                for part in sale_data.get('consumables', []):
                    item_id = part['stock_item_id']
                    name = part['name']
                    qty = part['quantity']
                    unit_price = Decimal(str(part['unit_price']))
                    
                    stock_row = cursor.execute("SELECT quantity FROM stock_items WHERE id = ?", (item_id,)).fetchone()
                    if not stock_row or stock_row[0] < qty:
                        raise ValueError(f"Yetersiz stok: {name}")
                    
                    invoice_items.append({'description': f"{name} Sarf Satışı", 'quantity': qty, 'unit_price': float(unit_price), 'currency': currency})
                    
                    cursor.execute("UPDATE stock_items SET quantity = quantity - ? WHERE id = ?", (qty, item_id))
                    new_quantity = stock_row[0] - qty
                    cursor.execute(
                        "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (item_id, 'Çıkış', -qty, new_quantity, float(unit_price), currency, movement_date, f"{qty} adet {name} {customer_name} müşterisine satıldı")
                    )
                    total_amount += unit_price * Decimal(str(qty))

                # Toner malzemeler
                for toner in sale_data.get('toners', []):
                    item_id = toner['stock_item_id']
                    name = toner['name']
                    qty = toner['quantity']
                    unit_price = Decimal(str(toner['unit_price']))
                    
                    stock_row = cursor.execute("SELECT quantity FROM stock_items WHERE id = ?", (item_id,)).fetchone()
                    if not stock_row or stock_row[0] < qty:
                        raise ValueError(f"Yetersiz stok: {name}")
                    
                    invoice_items.append({'description': f"{name} Toner Satışı", 'quantity': qty, 'unit_price': float(unit_price), 'currency': currency})
                    
                    cursor.execute("UPDATE stock_items SET quantity = quantity - ? WHERE id = ?", (qty, item_id))
                    new_quantity = stock_row[0] - qty
                    cursor.execute(
                        "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (item_id, 'Çıkış', -qty, new_quantity, float(unit_price), currency, movement_date, f"{qty} adet {name} {customer_name} müşterisine satıldı")
                    )
                    total_amount += unit_price * Decimal(str(qty))

                # Fatura kaydı
                invoice_date = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    "INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (customer_id, 'Satış', customer_id, invoice_date, float(total_amount), currency, json.dumps(enriched_items, ensure_ascii=False))
                )
                invoice_id = cursor.lastrowid
                if not invoice_id:
                    raise Exception("Fatura oluşturulamadı.")

                # Stok hareketlerine fatura ID'sini ekle
                cursor.execute("UPDATE stock_movements SET related_invoice_id = ? WHERE movement_date = ? AND notes LIKE ?", (invoice_id, movement_date, f"%{customer_name}%satıldı"))

            return invoice_id
        except sqlite3.IntegrityError as e:
            logging.error(f"Satış işlemi sırasında bütünlük hatası: {e}", exc_info=True)
            return "Seri numarası veya stok işlemi hatası. Lütfen girişleri kontrol edin."
        except Exception as e:
            logging.error(f"Satış işlemi sırasında hata: {e}", exc_info=True)
            return f"Satış işlemi sırasında hata: {e}"

    def create_pending_sale(self, sale_data: dict) -> Union[int, str]:
        """
        Satışı yapar ve stoktan düşer ama fatura oluşturmaz. Faturalar sekmesinde bekletir.
        """
        conn = self.get_connection()
        if not conn:
            return "Veritabanı bağlantısı kurulamadı."
        
        try:
            with conn:
                # ensure movement detail columns exist
                cols = [row[1] for row in conn.execute('PRAGMA table_info(stock_movements)').fetchall()]
                if 'quantity_after' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN quantity_after REAL')
                if 'unit_price' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN unit_price REAL')
                if 'currency' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN currency TEXT')

                cursor = conn.cursor()
                customer_id = sale_data['customer_id']
                items = sale_data.get('items', [])
                
                if not items:
                    return "Satış için en az bir ürün gerekli."
                
                # Bekleyen satışlar tablosunu oluştur
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pending_sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_amount REAL DEFAULT 0,
                        currency TEXT DEFAULT 'TL',
                        items_json TEXT,
                        sale_data_json TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        FOREIGN KEY (customer_id) REFERENCES customers (id)
                    )
                """)
                
                # Müşteri bilgisini al
                customer_row = cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,)).fetchone()
                customer_name = customer_row[0] if customer_row else f"ID:{customer_id}"
                movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Güncel kurları al (karışık para birimi için)
                from utils.currency_converter import get_exchange_rates
                rates = get_exchange_rates()
                
                total_amount_tl = 0.0
                
                # Her ürün için işlem yap
                for item in items:
                    item_id = item['stock_item_id']
                    description = item['description']
                    quantity = item['quantity']
                    unit_price = item['unit_price']
                    currency = (item.get('currency', 'TL') or 'TL').strip().upper()
                    serials = item.get('serial_numbers', [])
                    
                    # Ürün tutarını TL'ye çevir
                    if currency and currency != 'TL':
                        rate = float(rates.get(currency, 1.0))
                        item_total_tl = quantity * unit_price * rate
                    else:
                        item_total_tl = quantity * unit_price
                    
                    total_amount_tl += item_total_tl
                    
                    # Stok kontrolü
                    stock_row = cursor.execute(
                        "SELECT quantity, item_type, color_type FROM stock_items WHERE id = ?", 
                        (item_id,)
                    ).fetchone()
                    
                    if not stock_row:
                        raise ValueError(f"Stok kartı bulunamadı: {description}")
                    
                    if stock_row[0] < quantity:
                        raise ValueError(f"Yetersiz stok: {description} (Mevcut: {stock_row[0]}, İstenen: {quantity})")
                    
                    item_type = stock_row[1]
                    color_type = stock_row[2] if len(stock_row) > 2 else 'Bilinmiyor'
                    
                    # Cihaz ise müşteri envanterine ekle (customer_devices tablosuna)
                    if item_type == 'Cihaz' and serials:
                        for serial in serials:
                            if serial:  # Boş seri numarası kontrolü
                                # customer_devices kontrolü (seri numarası benzersiz)
                                existing_cd = cursor.execute(
                                    "SELECT id, customer_id FROM customer_devices WHERE serial_number = ?",
                                    (serial,)
                                ).fetchone()
                                if existing_cd:
                                    existing_customer_id = existing_cd[1]
                                    if existing_customer_id and existing_customer_id != customer_id:
                                        raise ValueError(f"Seri numarası başka bir müşteriye kayıtlı: {serial}")
                                    # Aynı müşteri veya boştaysa, müşteriye bağla ve eklemeyi atla
                                    if existing_customer_id != customer_id:
                                        cursor.execute(
                                            "UPDATE customer_devices SET customer_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                            (customer_id, existing_cd[0])
                                        )
                                else:
                                    cursor.execute("""
                                        INSERT INTO customer_devices 
                                        (customer_id, device_model, serial_number, device_type, color_type, is_cpc, installation_date)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (customer_id, description, serial, 'Yazıcı', color_type, 0, datetime.now().strftime('%Y-%m-%d')))

                                # devices tablosu (eski sistem uyumluluğu)
                                existing_dev = cursor.execute(
                                    "SELECT id, customer_id FROM devices WHERE serial_number = ?",
                                    (serial,)
                                ).fetchone()
                                if existing_dev:
                                    existing_customer_id = existing_dev[1]
                                    if existing_customer_id and existing_customer_id != customer_id:
                                        raise ValueError(f"Seri numarası başka bir müşteriye kayıtlı: {serial}")
                                    if existing_customer_id != customer_id:
                                        cursor.execute(
                                            "UPDATE devices SET customer_id = ? WHERE id = ?",
                                            (customer_id, existing_dev[0])
                                        )
                                else:
                                    cursor.execute(
                                        "INSERT INTO devices (customer_id, model, serial_number, type, is_cpc, color_type) VALUES (?, ?, ?, ?, ?, ?)", 
                                        (customer_id, description, serial, color_type, False, color_type)
                                    )
                    
                    # Stoktan düş
                    cursor.execute("UPDATE stock_items SET quantity = quantity - ? WHERE id = ?", (quantity, item_id))
                    
                    # Stok hareketi kaydet
                    movement_note = f"{quantity} adet {description} - {customer_name} müşterisine satıldı (beklemede)"
                    if unit_price == 0:
                        movement_note += " [BEDELSİZ]"
                    if currency != 'TL':
                        movement_note += f" [{unit_price} {currency} -> {item_total_tl:.2f} TL]"
                    
                    new_quantity = stock_row[0] - quantity
                    cursor.execute(
                        "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (item_id, 'Çıkış', -quantity, new_quantity, float(unit_price), currency, movement_date, movement_note)
                    )
                
                # Bekleyen satış kaydı - TÜM ÜRÜNLER TL'YE ÇEVRİLDİ
                sale_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                items_json = json.dumps(items, ensure_ascii=False)
                sale_json = json.dumps(sale_data, ensure_ascii=False)
                
                # Tüm ürünler TL'ye çevrildi - fatura para birimi TL
                final_currency = 'TL'
                
                cursor.execute(
                    "INSERT INTO pending_sales (customer_id, sale_date, total_amount, currency, items_json, sale_data_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (customer_id, sale_date, total_amount_tl, final_currency, items_json, sale_json)
                )
                
                pending_sale_id = cursor.lastrowid
                if not pending_sale_id:
                    raise Exception("Bekleyen satış kaydı oluşturulamadı.")

            return pending_sale_id
            
        except Exception as e:
            logging.error(f"Bekleyen satış işlemi sırasında hata: {e}", exc_info=True)
            return f"Satış işlemi sırasında hata: {e}"

    def get_price_settings(self) -> Dict[str, float]:
        """Fiyat ayarlarını getirir."""
        try:
            result = self.fetch_one("SELECT settings_json FROM price_settings WHERE id = 1")
            if result:
                return json.loads(result[0])
            else:
                # Varsayılan ayarları döndür
                return {
                    'toner_margin': 30.0,
                    'parts_margin': 25.0,
                    'device_margin': 20.0
                }
        except Exception as e:
            logging.error(f"Fiyat ayarları alınırken hata: {e}")
            return {
                'toner_margin': 30.0,
                'parts_margin': 25.0,
                'device_margin': 20.0
            }

    def save_price_settings(self, settings: Dict[str, float]) -> bool:
        """Fiyat ayarlarını kaydeder."""
        try:
            # Tablo yoksa oluştur
            self.execute_query("""
                CREATE TABLE IF NOT EXISTS price_settings (
                    id INTEGER PRIMARY KEY,
                    settings_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            settings_json = json.dumps(settings)
            
            # Mevcut kayıt var mı kontrol et
            existing = self.fetch_one("SELECT id FROM price_settings WHERE id = 1")
            
            if existing:
                self.execute_query(
                    "UPDATE price_settings SET settings_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                    (settings_json,)
                )
            else:
                self.execute_query(
                    "INSERT INTO price_settings (id, settings_json) VALUES (1, ?)",
                    (settings_json,)
                )
            
            logging.info("Fiyat ayarları başarıyla kaydedildi")
            return True
            
        except Exception as e:
            logging.error(f"Fiyat ayarları kaydedilirken hata: {e}")
            return False

    def get_custom_price_margins(self) -> List[Dict[str, Any]]:
        """Özel fiyat marjlarını getirir."""
        try:
            query = """
                SELECT cp.id, si.name, si.item_type, cp.custom_margin
                FROM custom_price_margins cp
                JOIN stock_items si ON cp.stock_item_id = si.id
                ORDER BY si.item_type, si.name
            """
            return [dict(row) for row in self.fetch_all(query)]
        except Exception as e:
            logging.error(f"Özel fiyat marjları alınırken hata: {e}")
            return []

    def save_custom_price_margin(self, stock_item_id: int, margin: float) -> bool:
        """Belirli bir ürün için özel fiyat marjı kaydeder."""
        try:
            # Tablo yoksa oluştur
            self.execute_query("""
                CREATE TABLE IF NOT EXISTS custom_price_margins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_item_id INTEGER NOT NULL,
                    custom_margin REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_item_id) REFERENCES stock_items (id),
                    UNIQUE (stock_item_id)
                )
            """)
            
            # Mevcut kayıt var mı kontrol et
            existing = self.fetch_one(
                "SELECT id FROM custom_price_margins WHERE stock_item_id = ?",
                (stock_item_id,)
            )
            
            if existing:
                self.execute_query(
                    "UPDATE custom_price_margins SET custom_margin = ? WHERE stock_item_id = ?",
                    (margin, stock_item_id)
                )
            else:
                self.execute_query(
                    "INSERT INTO custom_price_margins (stock_item_id, custom_margin) VALUES (?, ?)",
                    (stock_item_id, margin)
                )
            
            logging.info(f"Özel fiyat marjı kaydedildi: stock_item_id={stock_item_id}, margin={margin}")
            return True
            
        except Exception as e:
            logging.error(f"Özel fiyat marjı kaydedilirken hata: {e}")
            return False

    def delete_custom_price_margin(self, margin_id: int) -> bool:
        """Özel fiyat marjını siler."""
        try:
            self.execute_query("DELETE FROM custom_price_margins WHERE id = ?", (margin_id,))
            logging.info(f"Özel fiyat marjı silindi: id={margin_id}")
            return True
        except Exception as e:
            logging.error(f"Özel fiyat marjı silinirken hata: {e}")
            return False

    def calculate_end_user_price(self, stock_item_id: int, dealer_price: float) -> float:
        """
        Bayi fiyatından son kullanıcı fiyatını hesaplar.
        """
        try:
            # Önce özel marj var mı kontrol et
            custom_margin = self.fetch_one(
                "SELECT custom_margin FROM custom_price_margins WHERE stock_item_id = ?",
                (stock_item_id,)
            )
            
            if custom_margin:
                margin = custom_margin[0]
            else:
                # Genel marj ayarlarını kullan
                item_type = self.fetch_one(
                    "SELECT item_type FROM stock_items WHERE id = ?", 
                    (stock_item_id,)
                )
                
                if not item_type:
                    return dealer_price
                
                settings = self.get_price_settings()
                item_type_name = item_type[0]
                
                if item_type_name == "Toner":
                    margin = settings.get('toner_margin', 30.0)
                elif item_type_name == "Yedek Parça":
                    margin = settings.get('parts_margin', 25.0)
                elif item_type_name == "Cihaz":
                    margin = settings.get('device_margin', 20.0)
                else:
                    margin = 25.0  # Varsayılan marj
            
            # Son kullanıcı fiyatını hesapla
            end_user_price = dealer_price * (1 + margin / 100.0)
            return round(end_user_price, 2)
            
        except Exception as e:
            logging.error(f"Son kullanıcı fiyatı hesaplanırken hata: {e}")
            return dealer_price  # Hata durumunda bayi fiyatını döndür

    def convert_pending_sale_to_invoice(self, pending_sale_id: int) -> Union[int, str]:
        """
        Beklemede olan satışı faturaya çevirir.
        """
        conn = self.get_connection()
        if not conn:
            return "Veritabanı bağlantısı kurulamadı."
        
        try:
            with conn:
                # ensure movement detail columns exist
                cols = [row[1] for row in conn.execute('PRAGMA table_info(stock_movements)').fetchall()]
                if 'quantity_after' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN quantity_after REAL')
                if 'unit_price' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN unit_price REAL')
                if 'currency' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN currency TEXT')

                cursor = conn.cursor()
                
                # Pending sale verisini al
                pending_sale = cursor.execute(
                    "SELECT customer_id, sale_date, total_amount, currency, items_json FROM pending_sales WHERE id = ? AND status = 'pending'",
                    (pending_sale_id,)
                ).fetchone()
                
                if not pending_sale:
                    return "Beklemede satış bulunamadı veya zaten faturalandırılmış."
                
                customer_id, sale_date, total_amount, currency, items_json = pending_sale
                
                # items_json NULL kontrolü
                if not items_json:
                    return "Satış detayları bulunamadı (items_json NULL)."
                
                try:
                    items_data = json.loads(items_json)
                except (json.JSONDecodeError, TypeError) as e:
                    return f"Satış detayları okunamadı: {e}"
                
                # Format kontrolü ve dönüştürme
                invoice_items = []
                
                # Eski format kontrolü (dict with 'devices', 'toners', 'consumables' keys)
                if isinstance(items_data, dict) and ('devices' in items_data or 'toners' in items_data or 'consumables' in items_data):
                    # Eski format - dönüştür
                    for device in items_data.get('devices', []):
                        invoice_items.append({
                            'description': f"{device['model']} Cihaz Satış",
                            'quantity': device['quantity'],
                            'unit_price': device['unit_price'],
                            'currency': device['currency']
                        })
                    
                    for toner in items_data.get('toners', []):
                        invoice_items.append({
                            'description': f"{toner['name']} Toner Satış",
                            'quantity': toner['quantity'],
                            'unit_price': toner['unit_price'],
                            'currency': toner['currency']
                        })
                    
                    for consumable in items_data.get('consumables', []):
                        invoice_items.append({
                            'description': f"{consumable['name']} Sarf Malzeme Satış",
                            'quantity': consumable['quantity'],
                            'unit_price': consumable['unit_price'],
                            'currency': consumable['currency']
                        })
                        
                # Yeni format kontrolü (list of items)
                elif isinstance(items_data, list):
                    for item in items_data:
                        invoice_items.append({
                            'description': f"{item['description']} Satış",
                            'quantity': item['quantity'],
                            'unit_price': item['unit_price'],
                            'currency': item['currency']
                        })
                else:
                    return f"Bilinmeyen satış detayı formatı: {type(items_data)}"
                
                # Güncel kur bilgisini al
                from utils.currency_converter import get_exchange_rates
                rates = get_exchange_rates()
                exchange_rate = 1.0
                enriched_items = []
                for item in invoice_items:
                    item_currency = (item.get('currency', 'TL') or 'TL').strip().upper()
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    quantity = Decimal(str(item.get('quantity', 0)))
                    rate = Decimal(str(rates.get(item_currency, 1.0))) if item_currency != 'TL' else Decimal('1')
                    unit_price_tl = unit_price * rate
                    total_tl = unit_price_tl * quantity
                    enriched = dict(item)
                    enriched['currency'] = item_currency
                    enriched['exchange_rate'] = float(rate)
                    enriched['unit_price_tl'] = float(unit_price_tl)
                    enriched['total_tl'] = float(total_tl)
                    enriched_items.append(enriched)

                if currency and currency != 'TL':
                    exchange_rate = float(rates.get(currency, 1.0))
                
                # Fatura oluştur
                invoice_date = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    "INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, exchange_rate, details_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (customer_id, 'Satış', pending_sale_id, invoice_date, total_amount, currency, exchange_rate, json.dumps(enriched_items, ensure_ascii=False))
                )
                
                invoice_id = cursor.lastrowid
                if not invoice_id:
                    raise Exception("Fatura oluşturulamadı.")
                
                # Pending sale'i completed olarak işaretle
                cursor.execute(
                    "UPDATE pending_sales SET status = 'completed', invoice_id = ? WHERE id = ?",
                    (invoice_id, pending_sale_id)
                )
                
                # Stok hareketlerine fatura ID'sini ekle
                cursor.execute(
                    "UPDATE stock_movements SET related_invoice_id = ? WHERE notes LIKE ? AND related_invoice_id IS NULL",
                    (invoice_id, f"%Beklemede%")
                )
                
                logging.info(f"Beklemede satış faturalandırıldı: Pending Sale ID={pending_sale_id}, Invoice ID={invoice_id}")
                return invoice_id
                
        except Exception as e:
            logging.error(f"Pending sale faturalama hatası: {e}", exc_info=True)
            return f"Faturalama sırasında hata: {e}"


    def _ensure_supplier(self, cursor: sqlite3.Cursor, supplier_name: str) -> Optional[int]:
        if not supplier_name:
            return None
        row = cursor.execute("SELECT id FROM suppliers WHERE name = ?", (supplier_name,)).fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO suppliers (name) VALUES (?)", (supplier_name,))
        return cursor.lastrowid

    def _calculate_weighted_avg_cost(self, current_qty: float, current_avg: float, add_qty: float, add_cost_tl: float) -> float:
        if current_qty <= 0:
            return float(add_cost_tl)
        total_cost = (current_qty * current_avg) + (add_qty * add_cost_tl)
        total_qty = current_qty + add_qty
        if total_qty <= 0:
            return 0.0
        return float(total_cost / total_qty)

    def create_purchase_invoice(self, supplier_name: str, invoice_no: str, invoice_date: str, items: List[Dict[str, Any]], notes: str = "") -> Tuple[bool, Optional[str]]:
        conn = self.get_connection()
        if not conn:
            return False, "Veritabani baglantisi kurulamad?."

        if not items:
            return False, "Fatura kalemi bulunamadi."

        try:
            with conn:
                # ensure movement detail columns exist
                cols = [row[1] for row in conn.execute('PRAGMA table_info(stock_movements)').fetchall()]
                if 'quantity_after' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN quantity_after REAL')
                if 'unit_price' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN unit_price REAL')
                if 'currency' not in cols:
                    conn.execute('ALTER TABLE stock_movements ADD COLUMN currency TEXT')

                cursor = conn.cursor()
                supplier_id = self._ensure_supplier(cursor, supplier_name)

                rates = self.get_exchange_rates()

                subtotal = Decimal('0')
                tax_total = Decimal('0')

                cursor.execute(
                    """
                    INSERT INTO purchase_invoices (supplier_id, invoice_no, invoice_date, currency, exchange_rate, subtotal, tax_total, total, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (supplier_id, invoice_no, invoice_date, 'TL', 1.0, 0.0, 0.0, 0.0, notes)
                )
                purchase_invoice_id = cursor.lastrowid
                if not purchase_invoice_id:
                    raise Exception("Alis faturasi olusturulamadi.")

                # Ensure new columns exist (safety for older DBs)
                try:
                    cols = [row[1] for row in cursor.execute("PRAGMA table_info(stock_items)").fetchall()]
                    if 'avg_cost' not in cols:
                        cursor.execute("ALTER TABLE stock_items ADD COLUMN avg_cost REAL DEFAULT 0.0")
                    if 'avg_cost_currency' not in cols:
                        cursor.execute("ALTER TABLE stock_items ADD COLUMN avg_cost_currency TEXT DEFAULT 'TL'")
                except Exception as e:
                    logger.warning("avg_cost columns check failed: %s", e)

                for item in items:
                    stock_item_id = int(item['stock_item_id'])
                    qty = Decimal(str(item.get('quantity', 0)))
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    currency = item.get('currency', 'TL') or 'TL'
                    tax_rate = Decimal(str(item.get('tax_rate', 0)))

                    line_subtotal = qty * unit_price
                    line_tax = (line_subtotal * tax_rate / Decimal('100')).quantize(Decimal('0.01'))
                    line_total = line_subtotal + line_tax

                    subtotal += line_subtotal
                    tax_total += line_tax

                    rate = Decimal(str(rates.get(currency, 1.0)))
                    unit_cost_tl = (unit_price * rate).quantize(Decimal('0.0001'))

                    cursor.execute(
                        """
                        INSERT INTO purchase_items
                        (purchase_invoice_id, stock_item_id, description, quantity, unit_price, currency, tax_rate, tax_amount, total, unit_cost_tl)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (purchase_invoice_id, stock_item_id, None, float(qty), float(unit_price), currency, float(tax_rate), float(line_tax), float(line_total), float(unit_cost_tl))
                    )

                    row = cursor.execute(
                        "SELECT quantity, avg_cost FROM stock_items WHERE id = ?",
                        (stock_item_id,)
                    ).fetchone()
                    if not row:
                        raise Exception(f"Stok kalemi bulunamadi: {stock_item_id}")

                    current_qty = float(row[0] or 0)
                    current_avg = float(row[1] or 0)
                    new_avg = self._calculate_weighted_avg_cost(current_qty, current_avg, float(qty), float(unit_cost_tl))
                    new_qty = current_qty + float(qty)

                    cursor.execute(
                        "UPDATE stock_items SET quantity = ?, avg_cost = ?, avg_cost_currency = 'TL' WHERE id = ?",
                        (new_qty, new_avg, stock_item_id)
                    )

                    movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    notes_text = f"Alis Faturasi: {invoice_no or purchase_invoice_id}"
                    cursor.execute(
                        """
                        INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (stock_item_id, 'Giri?', float(qty), new_qty, float(unit_price), currency, movement_date, notes_text)
                    )

                    cursor.execute(
                        """
                        INSERT INTO stock_price_history (stock_item_id, price_type, price, currency, source)
                        VALUES (?, 'purchase', ?, ?, ?)
                        """,
                        (stock_item_id, float(unit_price), currency, f"purchase_invoice:{purchase_invoice_id}")
                    )

                total = subtotal + tax_total
                cursor.execute(
                    "UPDATE purchase_invoices SET subtotal = ?, tax_total = ?, total = ? WHERE id = ?",
                    (float(subtotal), float(tax_total), float(total), purchase_invoice_id)
                )

                return True, str(purchase_invoice_id)
        except Exception as e:
            logger.error(f"Alis faturasi olusturma hatasi: {e}", exc_info=True)
            return False, f"Hata: {e}"

