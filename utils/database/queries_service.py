"""
Veritabanı yöneticisi için servis kayıtları, teklifler ve sayaç okumaları
ile ilgili sorguları içeren mixin.

Bu modül, `DatabaseManager` sınıfına servis işlemleriyle ilgili veritabanı
fonksiyonlarını eklemek için tasarlanmıştır.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ServiceQueriesMixin:
    """
    Servis kayıtları, teklifler ve sayaç okumaları için veritabanı sorgularını
    içeren bir mixin sınıfı. `DatabaseManager` ile birlikte kullanılır.
    """

    def get_last_counter(self, device_id: int, counter_type: str, exclude_record_id: Optional[int] = None) -> int:
        """
        Belirli bir cihaz için belirtilen sayaç tipinin en son değerini döndürür.
        Sayaç sıfırlanmışsa veya hiç kayıt yoksa 0 döndürür.

        Args:
            device_id: Cihazın ID'si.
            counter_type: 'bw_counter' veya 'color_counter'.
            exclude_record_id: Sonuçlara dahil edilmeyecek servis kaydı ID'si (genellikle düzenleme sırasında kullanılır).

        Returns:
            En son sayaç değeri.
        """
        if counter_type not in ['bw_counter', 'color_counter']:
            raise ValueError("Geçersiz sayaç tipi. 'bw_counter' veya 'color_counter' olmalıdır.")

        query = f"SELECT {counter_type} FROM service_records WHERE device_id = ? AND {counter_type} IS NOT NULL"
        params = [device_id]
        
        if exclude_record_id:
            query += " AND id != ?"
            params.append(exclude_record_id)
            
        query += " ORDER BY created_date DESC, id DESC LIMIT 1"
        
        result = self.fetch_one(query, tuple(params))
        return result[0] if result and result[0] is not None else 0

    def get_uninvoiced_services(self, customer_id: int) -> List[Dict[str, Any]]:
        """Bir müşteriye ait, tamamlanmış ve henüz faturalandırılmamış servis kayıtlarını listeler."""
        query = """
            SELECT sr.id, sr.created_date, cd.device_model, sr.notes,
                   (SELECT SUM(qi.total_tl) FROM quote_items qi WHERE qi.service_record_id = sr.id) as total_amount
            FROM service_records sr
            JOIN customer_devices cd ON sr.device_id = cd.id
            WHERE cd.customer_id = ? AND sr.status = 'Tamamlandı' AND sr.is_invoiced = 0
            ORDER BY sr.created_date DESC
        """
        return [dict(row) for row in self.fetch_all(query, (customer_id,))]

    def get_history_for_device(self, device_id: int) -> List[Dict[str, Any]]:
        """Belirli bir cihaza ait tüm servis geçmişini listeler."""
        query = "SELECT created_date, status, problem_description, notes FROM service_records WHERE device_id = ? ORDER BY created_date DESC"
        return [dict(row) for row in self.fetch_all(query, (device_id,))]

    def get_all_services_for_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Belirli bir müşteriye ait tüm cihazların servis kayıtlarını birleştirerek listeler."""
        query = """
            SELECT sr.created_date, cd.device_model, cd.serial_number, sr.status, sr.problem_description, sr.notes 
            FROM service_records sr 
            JOIN customer_devices cd ON sr.device_id = cd.id 
            WHERE cd.customer_id = ? 
            ORDER BY sr.created_date DESC
        """
        return [dict(row) for row in self.fetch_all(query, (customer_id,))]

    def get_all_quotes(self, start_date: str, end_date: str) -> List[tuple]:
        """
        Belirtilen tarih aralığındaki tüm servis tekliflerini listeler.
        Teklifleri (servis kayıtları) tarih aralığına göre filtreler.
        
        Returns:
            List[tuple]: (Servis ID, Müşteri Adı, Cihaz Modeli, Tarih, Toplam Tutar, Durum)
        """
        query = """
            SELECT 
                sr.id,
                c.name as customer_name,
                cd.device_model,
                sr.created_date,
                COALESCE((SELECT SUM(qi.total_tl) FROM quote_items qi WHERE qi.service_record_id = sr.id), 0) as total_amount,
                sr.status
            FROM service_records sr
            JOIN customer_devices cd ON sr.device_id = cd.id
            JOIN customers c ON cd.customer_id = c.id
            WHERE sr.created_date BETWEEN ? AND ?
            ORDER BY sr.created_date DESC
        """
        rows = self.fetch_all(query, (start_date, end_date + ' 23:59:59'))
        return [(row['id'], row['customer_name'], row['device_model'], row['created_date'], row['total_amount'], row['status']) for row in rows]

    def get_quote_details(self, service_record_id: int) -> Optional[Dict[str, Any]]:
        """
        Bir servis kaydının tüm teklif detaylarını döndürür.
        PDF oluşturmak için kullanılır.
        
        Returns:
            Dict: customer_name, customer_address, customer_phone, customer_tax_id, items, company_info, vat_rate
        """
        try:
            service_record_id = int(service_record_id)
        except (ValueError, TypeError):
            logging.error(f"Geçersiz service_record_id: {service_record_id}")
            return None
            
        main_info_query = """
            SELECT
                c.name as customer_name, c.phone as customer_phone,
                c.address as customer_address, c.tax_id as customer_tax_id,
                cd.device_model, cd.serial_number as device_serial
            FROM service_records sr
            JOIN customer_devices cd ON sr.device_id = cd.id
            JOIN customers c ON cd.customer_id = c.id
            WHERE sr.id = ?
        """
        main_info_row = self.fetch_one(main_info_query, (service_record_id,))
        
        if not main_info_row:
            logging.warning(f"Teklif detayları bulunamadı: ID {service_record_id}")
            return None
        
        main_info = dict(main_info_row)
        items = self.get_quote_items(service_record_id)
        company_info = self.get_all_company_info()
        
        return {
            'customer_name': main_info.get('customer_name', ''),
            'customer_address': main_info.get('customer_address', ''),
            'customer_phone': main_info.get('customer_phone', ''),
            'customer_tax_id': main_info.get('customer_tax_id', ''),
            'device_model': main_info.get('device_model', ''),
            'device_serial': main_info.get('device_serial', ''),
            'items': items,
            'company_info': company_info,
            'vat_rate': '20.0'
        }

    def get_quote_items(self, service_record_id: int) -> List[Dict[str, Any]]:
        """Bir servis kaydına ait tüm teklif kalemlerini listeler."""
        query = "SELECT id, description, quantity, unit_price, stock_item_id, currency, total_tl FROM quote_items WHERE service_record_id = ? ORDER BY id"
        return [dict(row) for row in self.fetch_all(query, (service_record_id,))]

    def save_quote_items(self, service_record_id: int, items: List[Dict[str, Any]]) -> bool:
        """
        Bir servis kaydının teklif kalemlerini kaydeder. Önce mevcut kalemleri siler,
        sonra yenilerini ekler. Her kalemin TL toplamını da hesaplar ve kaydeder.
        """
        conn = self.get_connection()
        if not conn: return False
        
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM quote_items WHERE service_record_id = ?", (service_record_id,))
                
                rates = self.get_exchange_rates()

                for item in items:
                    quantity = Decimal(str(item.get('quantity', 0)))
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    currency = item.get('currency', 'TL')
                    rate = Decimal(str(rates.get(currency, 1.0)))
                    
                    total_tl = (quantity * unit_price * rate).quantize(Decimal('0.01'))

                    query = "INSERT INTO quote_items (service_record_id, description, quantity, unit_price, stock_item_id, currency, total_tl) VALUES (?, ?, ?, ?, ?, ?, ?)"
                    params = (
                        service_record_id, 
                        item.get('description'), 
                        float(quantity), 
                        float(unit_price), 
                        item.get('stock_item_id'), 
                        currency,
                        float(total_tl)
                    )
                    cursor.execute(query, params)
            logging.info(f"Servis #{service_record_id} için teklif kalemleri başarıyla kaydedildi.")
            return True
        except Exception as e:
            logging.error(f"Teklif kalemleri kaydedilirken hata: {e}", exc_info=True)
            return False

    def get_full_service_form_data(self, service_record_id: int) -> Optional[Dict[str, Any]]:
        """
        Bir servis kaydının tüm verilerini (ana bilgiler, müşteri, cihaz, teknisyen,
        teklif kalemleri, firma bilgileri) birleşik bir sözlük olarak döndürür.
        """
        main_info_query = """
            SELECT
                sr.id, sr.created_date, sr.status, sr.problem_description, sr.notes,
                sr.bw_counter, sr.color_counter, sr.technician_report,
                c.id as customer_id, c.name as customer_name, c.phone as customer_phone,
                c.address as customer_address, c.email as customer_email, c.tax_id as customer_tax_id,
                cd.id as device_id, cd.device_model as device_model, cd.serial_number as device_serial,
                COALESCE(u.username, 'Atanmadı') as technician_name
            FROM service_records sr
            JOIN customer_devices cd ON sr.device_id = cd.id
            JOIN customers c ON cd.customer_id = c.id
            LEFT JOIN users u ON sr.assigned_user_id = u.id
            WHERE sr.id = ?
        """
        main_info_row = self.fetch_one(main_info_query, (service_record_id,))
        
        if not main_info_row:
            logging.warning(f"Servis formu verisi bulunamadı: ID {service_record_id}")
            return None
            
        data = {
            'main_info': dict(main_info_row),
            'quote_items': self.get_quote_items(service_record_id),
            'company_info': self.get_all_company_info()
        }
        return data

    def add_meter_reading_record(self, device_id: int, assigned_user_id: int, bw_counter: Optional[int], color_counter: Optional[int]) -> Optional[int]:
        """
        Periyodik sayaç okuması için özel bir servis kaydı oluşturur.
        """
        if bw_counter is None and color_counter is None:
            logging.warning("Sayaç okuma kaydı oluşturulmadı: Her iki sayaç değeri de boş.")
            return None
            
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        query = "INSERT INTO service_records (device_id, assigned_user_id, problem_description, status, bw_counter, color_counter, created_date, is_invoiced) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        params = (device_id, assigned_user_id, "Periyodik Sayaç Okuma", "Tamamlandı", bw_counter, color_counter, date, 0) # Sayaç okumaları başlangıçta faturalanmamış olarak kaydedilir
        
        record_id = self.execute_query(query, params)
        if record_id:
            logging.info(f"Cihaz #{device_id} için sayaç okuma kaydı #{record_id} oluşturuldu.")
        return record_id

    def get_previous_counter_readings(self, device_id: int, current_service_id: int) -> Dict[str, Optional[int]]:
        """
        Cihazın önceki servis kaydındaki sayaç okumalarını döndürür.
        
        Args:
            device_id: Cihaz ID'si
            current_service_id: Mevcut servis kaydının ID'si (bu kaydı hariç tutmak için)
            
        Returns:
            Dict[str, Optional[int]]: {'bw_counter': int, 'color_counter': int} veya None değerler
        """
        query = """
        SELECT bw_counter, color_counter 
        FROM service_records 
        WHERE device_id = ? AND id != ? AND (bw_counter IS NOT NULL OR color_counter IS NOT NULL)
        ORDER BY created_date DESC 
        LIMIT 1
        """
        params = (device_id, current_service_id)
        result = self.fetch_one(query, params)
        
        if result:
            return {
                'bw_counter': result[0],
                'color_counter': result[1]
            }
        return {'bw_counter': None, 'color_counter': None}

