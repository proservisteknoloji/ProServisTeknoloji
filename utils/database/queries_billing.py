"""
Veritabanı yöneticisi için faturalandırma ile ilgili sorguları içeren mixin.

Bu modül, `DatabaseManager` sınıfına faturalandırma, satış, ödemeler ve
finansal raporlama ile ilgili veritabanı işlemlerini eklemek için tasarlanmıştır.
"""

import json
import logging
logger = logging.getLogger(__name__)
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple

# Logging yapılandırması

class BillingQueriesMixin:
    """
    Faturalandırma, satış ve finansal işlemler için veritabanı sorgularını
    içeren bir mixin sınıfı. `DatabaseManager` ile birlikte kullanılır.
    """

    def create_sale_invoice(self, customer_id: int, items: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Yeni bir satış faturası oluşturur, stokları günceller ve stok hareketlerini kaydeder.
        Cihaz satışlarında, cihazı müşterinin envanterine ekler.

        Args:
            customer_id: Müşterinin ID'si.
            items: Satılan ürünleri içeren bir sözlük listesi. Her sözlük
                   {'stock_item_id', 'quantity', 'unit_price', 'currency', 'description', 'serial_number'?}
                   içermelidir.

        Returns:
            (True, None) başarılı olursa.
            (False, "Hata mesajı") başarısız olursa.
        """
        conn = self.get_connection()
        if not conn:
            return False, "Veritabanı bağlantısı kurulamadı."

        try:
            with conn:  # `with` bloğu transaction'ı otomatik yönetir (commit/rollback)
                cursor = conn.cursor()

                # Fatura toplamını ve para birimini hesapla
                total_amount, invoice_currency = self._calculate_invoice_total(items)
                rates = self.get_exchange_rates()
                enriched_items = []
                for item in items:
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
                details_json = json.dumps(enriched_items, ensure_ascii=False)
                
                invoice_params = (customer_id, 'Satış', customer_id, invoice_date, float(total_amount), invoice_currency, details_json)
                cursor.execute("INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)", invoice_params)
                invoice_id = cursor.lastrowid
                if not invoice_id:
                    raise Exception("Fatura ID'si alınamadı.")

                # Fatura kalemlerini kaydet
                for item in enriched_items:
                    stock_item_id = item.get('stock_item_id')
                    quantity = Decimal(str(item.get('quantity', 0)))
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    currency = (item.get('currency', 'TL') or 'TL').strip().upper()
                    tax_rate = Decimal(str(item.get('tax_rate', 20)))
                    tax_amount = (quantity * unit_price) * tax_rate / Decimal('100')

                    cost_at_sale = Decimal('0')
                    if stock_item_id:
                        row = cursor.execute("SELECT avg_cost FROM stock_items WHERE id = ?", (stock_item_id,)).fetchone()
                        if row and row[0] is not None:
                            cost_at_sale = Decimal(str(row[0]))

                    cursor.execute(
                        """
                        INSERT INTO invoice_items (invoice_id, stock_item_id, description, quantity, unit_price, currency, tax_rate, tax_amount, cost_at_sale, cost_currency)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (invoice_id, stock_item_id, item.get('description', ''), float(quantity), float(unit_price), currency, float(tax_rate), float(tax_amount), float(cost_at_sale), 'TL')
                    )


                # Stokları güncelle ve hareketleri kaydet
                for item in items:
                    self._update_stock_for_sale(cursor, item, invoice_id, customer_id)

            logging.info(f"Satış faturası #{invoice_id} başarıyla oluşturuldu.")
            return True, str(invoice_id)
        except sqlite3.IntegrityError as e:
            logging.error(f"Satış faturası oluşturulurken bütünlük hatası: {e}", exc_info=True)
            return False, "Girilen seri numaralarından biri zaten başka bir müşteriye kayıtlı."
        except Exception as e:
            logging.error(f"Satış faturası oluşturma hatası: {e}", exc_info=True)
            return False, f"Beklenmedik bir hata oluştu: {e}"

    def _calculate_invoice_total(self, items: List[Dict[str, Any]]) -> Tuple[Decimal, str]:
        """Verilen kalemler listesinden toplam fatura tutarini ve para birimini hesaplar."""
        if not items:
            return Decimal('0.00'), 'TL'

        total_amount = Decimal('0.00')
        rates = self.get_exchange_rates()
        for item in items:
            item_currency = (item.get('currency', 'TL') or 'TL').strip().upper()
            rate = Decimal(str(rates.get(item_currency, 1.0))) if item_currency != 'TL' else Decimal('1')
            quantity = Decimal(str(item.get('quantity', 0)))
            unit_price = Decimal(str(item.get('unit_price', 0)))
            tax_rate = Decimal(str(item.get('tax_rate', 20)))
            line_total = (quantity * unit_price) * (Decimal('1') + tax_rate / Decimal('100'))
            total_amount += line_total * rate

        return total_amount.quantize(Decimal('0.01')), 'TL'

    def _update_stock_for_sale(self, cursor: sqlite3.Cursor, item: Dict[str, Any], invoice_id: int, customer_id: int) -> None:
        """Bir satış kalemi için stokları günceller ve hareket kaydı oluşturur."""
        stock_item_id = item['stock_item_id']
        quantity_sold = Decimal(str(item['quantity']))
        
        # Stok miktarını kontrol et ve güncelle
        cursor.execute("SELECT quantity, item_type FROM stock_items WHERE id = ?", (stock_item_id,))
        stock_info = cursor.fetchone()
        if not stock_info or Decimal(str(stock_info['quantity'])) < quantity_sold:
            raise Exception(f"'{item.get('description', 'Bilinmeyen Ürün')}' için yetersiz stok!")
        
        cursor.execute("UPDATE stock_items SET quantity = quantity - ? WHERE id = ?", (float(quantity_sold), stock_item_id))
        new_quantity = Decimal(str(stock_info['quantity'])) - quantity_sold
        
        # Stok hareketini kaydet
        movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        notes = f"Satış Faturası No: {invoice_id}"
        currency = (item.get('currency', 'TL') or 'TL').strip().upper()
        unit_price = Decimal(str(item.get('unit_price', 0)))
        cursor.execute(
            "INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes, related_invoice_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (stock_item_id, 'Çıkış', -float(quantity_sold), float(new_quantity), float(unit_price), currency, movement_date, notes, invoice_id)
        )
        
        # Eğer satılan ürün bir cihaz ise, müşteri envanterine ekle
        if stock_info['item_type'] == 'Cihaz':
            serial = item.get('serial_number') or f"SATIS-{invoice_id}-{stock_item_id}"
            cursor.execute(
                "INSERT INTO devices (customer_id, model, serial_number, type, is_cpc) VALUES (?, ?, ?, ?, ?)",
                (customer_id, item.get('description', 'Bilinmeyen Cihaz'), serial, 'Bilinmiyor', 0)
            )

    def create_invoice_for_service(self, service_id: int) -> Optional[int]:
        """
        Tamamlanmış bir servis kaydı için otomatik olarak fatura oluşturur.
        Eğer zaten bir fatura varsa, işlem yapmaz.
        Ücretsiz cihazlara ait servis kayıtları faturalandırılmaz.
        """
        if self.fetch_one("SELECT id FROM invoices WHERE invoice_type = 'Servis' AND related_id = ?", (service_id,)):
            logging.warning(f"Servis #{service_id} için zaten bir fatura mevcut. Yeni fatura oluşturulmadı.")
            return None

        service_data = self.get_full_service_form_data(service_id)
        if not service_data or not service_data.get('main_info'):
            logging.error(f"Servis #{service_id} için fatura oluşturulamadı: Servis verileri bulunamadı.")
            return None

        # Ücretsiz cihaz kontrolü
        device_id = service_data['main_info'].get('device_id')
        if device_id:
            device_info = self.fetch_one("SELECT is_free FROM customer_devices WHERE id = ?", (device_id,))
            if device_info and device_info['is_free']:
                logging.info(f"Servis #{service_id} için fatura oluşturulmadı: Cihaz ücretsiz.")
                return None

        quote_items = service_data.get('quote_items', [])
        if not quote_items:
            logging.info(f"Servis #{service_id} için fatura oluşturulmadı: Ücretli kalem bulunmuyor.")
            return None

        total_amount = sum(Decimal(item.get('total_tl', 0)) for item in quote_items)
        currency = 'TL' # Servis faturaları her zaman TL
        customer_id = service_data['main_info'].get('customer_id')
        
        if not customer_id:
            logging.error(f"Servis #{service_id} için fatura oluşturulamadı: Müşteri ID'si bulunamadı.")
            return None
        
        details_for_json = [
            {"description": item.get('description'), "quantity": item.get('quantity'), "unit_price": item.get('unit_price')}
            for item in quote_items
        ]
        
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        params = (customer_id, 'Servis', service_id, invoice_date, float(total_amount), currency, json.dumps(details_for_json, ensure_ascii=False))
        query = "INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)"
        
        logging.info(f"Fatura oluşturuluyor: tarih={invoice_date}, tutar={total_amount} {currency}")
        invoice_id = self.execute_query(query, params)
        if invoice_id:
            self.execute_query("UPDATE service_records SET is_invoiced = 1 WHERE id = ?", (service_id,))
            logging.info(f"Servis #{service_id} için fatura #{invoice_id} başarıyla oluşturuldu.")
        return invoice_id

    def create_cpc_invoice(self, location_id: int, start_date: str, end_date: str, total_tl: float, details_json: str) -> bool:
        """
        Bir Kopya Başı Anlaşması (CPC) için fatura oluşturur. Hem eski `cpc_invoices`
        tablosuna hem de merkezi `invoices` tablosuna kayıt ekler.
        """
        conn = self.get_connection()
        if not conn: return False
        try:
            with conn:
                cursor = conn.cursor()
                invoice_date = datetime.now().strftime("%Y-%m-%d")
                
                # Eski `cpc_invoices` tablosuna kayıt
                legacy_query = "INSERT INTO cpc_invoices (location_id, billing_period_start, billing_period_end, invoice_date, total_amount_tl, details_json) VALUES (?, ?, ?, ?, ?, ?)"
                legacy_params = (location_id, start_date, end_date, invoice_date, total_tl, details_json)
                cursor.execute(legacy_query, legacy_params)
                legacy_invoice_id = cursor.lastrowid
                if not legacy_invoice_id:
                    raise Exception("CPC fatura ID'si alınamadı.")

                # Lokasyon bilgilerini al
                location_info = self.fetch_one("SELECT customer_id FROM customer_locations WHERE id = ?", (location_id,))
                customer_id = location_info['customer_id'] if location_info else None
                
                # Merkezi `invoices` tablosuna kayıt
                central_query = "INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, details_json, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                central_params = (customer_id, 'Kopya Başı', legacy_invoice_id, invoice_date, total_tl, 'TL', details_json, f"Dönem: {start_date} - {end_date}")
                cursor.execute(central_query, central_params)
            
            # İlgili sayaç kayıtlarını faturalandırıldı olarak işaretle
            data = json.loads(details_json)
            device_ids = [item.get('device_id') for item in data if item.get('device_id')]
            if device_ids:
                update_query = """
                    UPDATE service_records
                    SET is_invoiced = 1
                    WHERE device_id IN ({}) 
                    AND created_date BETWEEN ? AND ?
                """.format(','.join('?' * len(device_ids)))
                cursor.execute(update_query, device_ids + [start_date, end_date])
            
            logging.info(f"CPC Faturası (eski ID: {legacy_invoice_id}) başarıyla oluşturuldu.")
            return True
        except sqlite3.Error as e:
            logging.error(f"CPC Fatura oluşturma hatası: {e}", exc_info=True)
            return False

    def get_dashboard_stats(self) -> Dict[str, int]:
        """Ana panel için temel servis istatistiklerini alır.
        
        Not: CPC sayaç okumaları (is_cpc=1 olan cihazlara ait kayıtlar veya 
        "Periyodik Sayaç Okuma" problem tanımlı kayıtlar) servis sayılarına dahil edilmez.
        """
        stats = {'monthly_new': 0, 'on_repair': 0, 'awaiting_part': 0, 'awaiting_approval': 0}
        
        try:
            # CPC sayaç okumalarını hariç tutan temel filtre
            # is_cpc=0 olan cihazlara ait veya problem_description "Periyodik Sayaç Okuma" olmayan kayıtlar
            cpc_filter = """
                AND (
                    sr.problem_description IS NULL 
                    OR sr.problem_description NOT LIKE '%Periyodik Sayaç Okuma%'
                )
                AND (
                    cd.is_cpc IS NULL 
                    OR cd.is_cpc = 0
                )
            """
            
            # Bu ay açılan gerçek servis sayısı (CPC sayaç okumaları hariç)
            monthly_query = f"""
                SELECT COUNT(*) FROM service_records sr
                LEFT JOIN customer_devices cd ON sr.device_id = cd.id
                WHERE strftime('%Y-%m', sr.created_date) = strftime('%Y-%m', 'now')
                {cpc_filter}
            """
            result = self.fetch_one(monthly_query)
            if result:
                stats['monthly_new'] = result[0]
                logging.info(f"Dashboard: Bu ay açılan servis sayısı = {result[0]} (CPC hariç)")

            # Onarımda bekleyen: İşleme alındı veya Servise alındı durumundaki servisler (CPC hariç)
            on_repair_query = f"""
                SELECT COUNT(*) FROM service_records sr
                LEFT JOIN customer_devices cd ON sr.device_id = cd.id
                WHERE sr.status IN ('İşleme alındı', 'Servise alındı')
                {cpc_filter}
            """
            result = self.fetch_one(on_repair_query)
            if result:
                stats['on_repair'] = result[0]

            # Parça bekleyen servisler (CPC hariç)
            awaiting_part_query = f"""
                SELECT COUNT(*) FROM service_records sr
                LEFT JOIN customer_devices cd ON sr.device_id = cd.id
                WHERE sr.status = 'Parça bekleniyor'
                {cpc_filter}
            """
            result = self.fetch_one(awaiting_part_query)
            if result:
                stats['awaiting_part'] = result[0]

            # Müşteri onayı bekleyen servisler (CPC hariç)
            awaiting_approval_query = f"""
                SELECT COUNT(*) FROM service_records sr
                LEFT JOIN customer_devices cd ON sr.device_id = cd.id
                WHERE sr.status = 'Müşteri Onayı Alınacak'
                {cpc_filter}
            """
            result = self.fetch_one(awaiting_approval_query)
            if result:
                stats['awaiting_approval'] = result[0]

            logging.info(f"Dashboard stats: {stats}")

        except Exception as e:
            logging.error(f"Dashboard servis istatistikleri alınırken hata: {e}", exc_info=True)
            
        return stats

    def get_dashboard_financial_stats(self) -> Dict[str, Any]:
        """Ana panel için finansal istatistikleri (aylık ciro, ödemeler, bekleyen bakiye) alır."""
        stats = {'total_invoiced': Decimal('0.0'), 'total_paid': Decimal('0.0'), 'invoice_count': 0, 'pending_balance': Decimal('0.0')}
        try:
            rates = self.get_exchange_rates()

            # Bu ay faturalanan toplam tutar (fatura kesim tarihindeki kur + %20 vergi)
            query_invoiced = "SELECT total_amount, currency, exchange_rate FROM invoices WHERE strftime('%Y-%m', invoice_date) = strftime('%Y-%m', 'now')"
            all_invoices_this_month = self.fetch_all(query_invoiced)
            
            # DEBUG: Fatura sayısını logla
            logging.info(f"Dashboard: Bu ay {len(all_invoices_this_month)} fatura bulundu")
            
            total_invoiced_tl = Decimal('0.0')
            
            for row in all_invoices_this_month:
                amount = Decimal(str(row['total_amount']))
                currency = row['currency']
                saved_rate = row['exchange_rate'] if 'exchange_rate' in row.keys() else None  # Fatura kesildiğindeki kur
                
                # Eğer döviz ise TL'ye çevir (kaydedilmiş kur varsa onu kullan)
                if currency and currency != 'TL':
                    if saved_rate and saved_rate > 0:
                        rate = Decimal(str(saved_rate))
                    else:
                        # Eski faturalar için güncel kuru kullan (fallback)
                        rate = Decimal(str(rates.get(currency, 1.0)))
                    amount_in_tl = amount * rate
                else:
                    amount_in_tl = amount
                
                # %20 vergi ekle
                amount_with_tax = amount_in_tl * Decimal('1.20')
                total_invoiced_tl += amount_with_tax
            
            stats['invoice_count'] = len(all_invoices_this_month)
            stats['total_invoiced'] = total_invoiced_tl

            # Bu ay alınan toplam ödeme (ödeme tarihindeki güncel kur + %20 vergi)
            query_paid = "SELECT p.amount_paid, i.currency, i.exchange_rate FROM payments p JOIN invoices i ON p.invoice_id = i.id WHERE strftime('%Y-%m', p.payment_date) = strftime('%Y-%m', 'now')"
            all_payments_this_month = self.fetch_all(query_paid)
            total_paid_tl = Decimal('0.0')
            
            for row in all_payments_this_month:
                amount = Decimal(str(row['amount_paid']))
                currency = row['currency']
                saved_rate = row['exchange_rate'] if 'exchange_rate' in row.keys() else None
                
                # Eğer döviz ise TL'ye çevir
                if currency and currency != 'TL':
                    if saved_rate and saved_rate > 0:
                        rate = Decimal(str(saved_rate))
                    else:
                        rate = Decimal(str(rates.get(currency, 1.0)))
                    amount_in_tl = amount * rate
                else:
                    amount_in_tl = amount
                
                # %20 vergi ekle
                amount_with_tax = amount_in_tl * Decimal('1.20')
                total_paid_tl += amount_with_tax
            
            stats['total_paid'] = total_paid_tl

            # Tüm zamanlardaki ödenmemiş bakiye (faturadaki kur + %20 vergi)
            query_pending = "SELECT total_amount, paid_amount, currency, exchange_rate FROM invoices WHERE status != 'Ödendi'"
            pending_invoices = self.fetch_all(query_pending)
            total_pending_tl = Decimal('0.0')
            
            for row in pending_invoices:
                total = Decimal(str(row['total_amount']))
                paid = Decimal(str(row['paid_amount']))
                remaining = total - paid
                currency = row['currency']
                saved_rate = row['exchange_rate'] if 'exchange_rate' in row.keys() else None
                
                # Eğer döviz ise TL'ye çevir
                if currency and currency != 'TL':
                    if saved_rate and saved_rate > 0:
                        rate = Decimal(str(saved_rate))
                    else:
                        rate = Decimal(str(rates.get(currency, 1.0)))
                    remaining_in_tl = remaining * rate
                else:
                    remaining_in_tl = remaining
                
                # %20 vergi ekle
                remaining_with_tax = remaining_in_tl * Decimal('1.20')
                total_pending_tl += remaining_with_tax
            
            stats['pending_balance'] = total_pending_tl
        except (InvalidOperation, Exception) as e:
            logging.error(f"Dashboard finansal istatistikleri alınırken hata: {e}", exc_info=True)
        
        # Sonuçları float'a çevirerek döndür (UI uyumluluğu için)
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in stats.items()}

    def get_invoices_for_current_month(self) -> List[Dict[str, Any]]:
        """İçinde bulunulan ay için oluşturulan tüm faturaları listeler."""
        query = """
            SELECT i.id, i.invoice_date, c.name, i.invoice_type, i.total_amount, i.currency, i.exchange_rate, i.status 
            FROM invoices i 
            JOIN customers c ON i.customer_id = c.id 
            WHERE strftime('%Y-%m', i.invoice_date) = strftime('%Y-%m', 'now') 
            ORDER BY i.invoice_date DESC
        """
        return [dict(row) for row in self.fetch_all(query)]

    def get_payments_for_current_month(self) -> List[Dict[str, Any]]:
        """İçinde bulunulan ayda yapılan tüm ödemeleri listeler."""
        query = """
            SELECT p.payment_date, c.name, p.invoice_id, p.amount_paid, i.currency, p.payment_method 
            FROM payments p 
            JOIN invoices i ON p.invoice_id = i.id 
            JOIN customers c ON i.customer_id = c.id 
            WHERE strftime('%Y-%m', p.payment_date) = strftime('%Y-%m', 'now') 
            ORDER BY p.payment_date DESC
        """
        return [dict(row) for row in self.fetch_all(query)]

    def get_pending_invoices(self) -> List[Dict[str, Any]]:
        """Durumu 'Ödendi' olmayan tüm faturaları ve kalan bakiyelerini listeler."""
        query = """
            SELECT i.id, i.invoice_date, c.name, i.total_amount, i.paid_amount, 
                   (i.total_amount - i.paid_amount) as balance, i.currency 
            FROM invoices i 
            JOIN customers c ON i.customer_id = c.id 
            WHERE i.status != 'Ödendi' 
            ORDER BY i.invoice_date DESC
        """
        return [dict(row) for row in self.fetch_all(query)]

    def get_full_invoice_details(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """
        Belirli bir faturanın tüm detaylarını (kalemler, müşteri bilgileri vb.) alır.
        Fatura tipine göre (Servis, Satış, Kopya Başı) ilgili ek verileri de getirir.
        """
        invoice_info = self.fetch_one("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        if not invoice_info:
            return None

        invoice_dict = dict(invoice_info)

        # JSON detaylarını ayrıştır
        try:
            invoice_dict['items'] = json.loads(invoice_dict.get('details_json', '[]'))
        except (json.JSONDecodeError, TypeError):
            invoice_dict['items'] = []

        # Müşteri bilgilerini müşteri tablosundan çek
        cust_id = invoice_dict.get('customer_id')
        customer_info = None
        if cust_id:
            cust_row = self.fetch_one("SELECT name, address, phone, tax_id, tax_office FROM customers WHERE id = ?", (cust_id,))
            if cust_row:
                customer_info = {
                    'name': cust_row['name'],
                    'address': cust_row['address'],
                    'phone': cust_row['phone'],
                    'tax_id': cust_row['tax_id'],
                    'tax_office': cust_row['tax_office'],
                }
        if customer_info:
            invoice_dict['customer_info'] = customer_info

        # Fatura tipine göre ek verileri zenginleştir
        if invoice_dict['invoice_type'] == 'Servis':
            service_data = self.get_full_service_form_data(invoice_dict['related_id'])
            if service_data:
                invoice_dict['items'] = service_data.get('quote_items', [])
                invoice_dict['main_info'] = service_data.get('main_info', {})

        elif invoice_dict['invoice_type'] == 'Bakım Sözleşmesi':
            # Bakım sözleşmesi faturası için invoice_items tablosundan kalemleri al
            invoice_items = self.fetch_all(
                "SELECT description, quantity, unit_price, currency FROM invoice_items WHERE invoice_id = ?",
                (invoice_id,)
            )
            if invoice_items:
                items_list = []
                for item in invoice_items:
                    items_list.append({
                        'description': item['description'],
                        'quantity': item['quantity'],
                        'unit_price': item['unit_price'],
                        'total': item['quantity'] * item['unit_price'],
                        'currency': item['currency']
                    })
                invoice_dict['items'] = items_list

        elif invoice_dict['invoice_type'] == 'Kopya Başı':
            logger.debug(f"DEBUG: CPC faturası işleniyor, ID: {invoice_dict['related_id']}")
            cpc_details = self.fetch_one("SELECT * FROM cpc_invoices WHERE id = ?", (invoice_dict['related_id'],))
            if cpc_details:
                invoice_dict['cpc_details'] = dict(cpc_details)
                # CPC detaylarındaki JSON'u da ayrıştır
                try:
                    cpc_items = json.loads(invoice_dict['cpc_details'].get('details_json', '[]'))
                    logger.debug(f"DEBUG: JSON'dan {len(cpc_items)} kalem çıktı")
                    processed_items = []
                    
                    for i, item in enumerate(cpc_items):
                        logger.debug(f"DEBUG: Ham item {i}: {item.keys()}")
                        # Kiralama bedeli kalemi ise
                        if item.get('is_rental', False):
                            # TL değerleri kullan
                            unit_price_tl = float(item.get('unit_price_tl', 0))
                            total_tl = float(item.get('total_tl', 0))
                            processed_item = {
                                'description': item.get('description', 'Kiralama Bedeli'),
                                'quantity': float(item.get('quantity', 1)),
                                'unit_price': unit_price_tl,
                                'total': total_tl,
                                'currency': 'TL'
                            }
                            logger.debug(f"DEBUG: Kiralama bedeli kalemi: {processed_item}")
                            processed_items.append(processed_item)
                        else:
                            # Normal CPC kalemi - S/B ve renkli için ayrı kalemler oluştur
                            model = item.get('model', '')
                            serial_number = item.get('serial_number', '')
                            
                            # String değerleri sayıya çevir ve floating point hatalarını düzelt
                            try:
                                bw_usage = float(item.get('bw_usage', 0))
                                color_usage = float(item.get('color_usage', 0))
                                
                                # Floating point hassasiyeti problemi için round kullan
                                cpc_bw_price_tl = round(float(item.get('cpc_bw_price_tl', 0)), 4)
                                cpc_color_price_tl = round(float(item.get('cpc_color_price_tl', 0)), 4)
                                total_bw_cost_tl = round(float(item.get('total_bw_cost_tl', 0)), 2)
                                total_color_cost_tl = round(float(item.get('total_color_cost_tl', 0)), 2)
                            except (ValueError, TypeError):
                                logger.debug(f"DEBUG: Sayısal değer çevirme hatası, varsayılan değerler kullanılıyor")
                                bw_usage = color_usage = 0
                                cpc_bw_price_tl = cpc_color_price_tl = 0
                                total_bw_cost_tl = total_color_cost_tl = 0
                            
                            logger.debug(f"DEBUG: CPC kalemi - Model: {model}, S/B: {bw_usage}, Renkli: {color_usage}")
                            
                            # Siyah-beyaz kullanım kalemi
                            if bw_usage > 0:
                                bw_item = {
                                    'description': f"{model} ({serial_number}) - Siyah/Beyaz Baskı",
                                    'quantity': bw_usage,
                                    'unit_price': cpc_bw_price_tl,
                                    'total': total_bw_cost_tl,
                                    'currency': 'TL'
                                }
                                logger.debug(f"DEBUG: S/B kalemi: {bw_item}")
                                processed_items.append(bw_item)
                            
                            # Renkli kullanım kalemi
                            if color_usage > 0:
                                color_item = {
                                    'description': f"{model} ({serial_number}) - Renkli Baskı",
                                    'quantity': color_usage,
                                    'unit_price': cpc_color_price_tl,
                                    'total': total_color_cost_tl,
                                    'currency': 'TL'
                                }
                                logger.debug(f"DEBUG: Renkli kalemi: {color_item}")
                                processed_items.append(color_item)
                    
                    logger.debug(f"DEBUG: Toplam {len(processed_items)} işlenmiş kalem")
                    invoice_dict['items'] = processed_items
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"DEBUG: JSON ayrıştırma hatası: {e}")
                    pass # Ana 'items' zaten dolu olabilir

        # Kalemlere TL kar??l?klar?n? ekle (PDF i?in)
        try:
            items = invoice_dict.get('items', [])
            if isinstance(items, list) and items:
                rates = self.get_exchange_rates()
                for item in items:
                    try:
                        item_currency = (item.get('currency', 'TL') or 'TL').strip().upper()
                        unit_price = Decimal(str(item.get('unit_price', 0)))
                        quantity = Decimal(str(item.get('quantity', 0)))
                        rate_value = item.get('exchange_rate')
                        if rate_value is None:
                            rate_value = float(rates.get(item_currency, 1.0)) if item_currency != 'TL' else 1.0
                        rate = Decimal(str(rate_value))
                        unit_price_tl = unit_price * rate
                        total_tl = unit_price_tl * quantity
                        if 'unit_price_tl' not in item:
                            item['unit_price_tl'] = float(unit_price_tl)
                        if 'total_tl' not in item:
                            item['total_tl'] = float(total_tl)
                        if 'exchange_rate' not in item:
                            item['exchange_rate'] = float(rate)
                    except Exception:
                        # Sessiz ge?: mevcut alanlar bozulmas?n
                        continue
        except Exception:
            pass

        return invoice_dict

    def add_payment(self, invoice_id: int, payment_date: str, amount_paid: float, payment_method: str, notes: str) -> bool:
        """
        Bir faturaya yeni bir ödeme ekler ve faturanın durumunu günceller.
        """
        conn = self.get_connection()
        if not conn: return False
        try:
            with conn:
                cursor = conn.cursor()
                
                # Ödemeyi ekle
                cursor.execute(
                    "INSERT INTO payments (invoice_id, payment_date, amount_paid, payment_method, notes) VALUES (?, ?, ?, ?, ?)",
                    (invoice_id, payment_date, amount_paid, payment_method, notes)
                )
                
                # Faturanın ödenen miktarını güncelle
                cursor.execute("UPDATE invoices SET paid_amount = paid_amount + ? WHERE id = ?", (amount_paid, invoice_id))
                
                # Fatura durumunu kontrol et ve güncelle
                cursor.execute("SELECT total_amount, paid_amount FROM invoices WHERE id = ?", (invoice_id,))
                invoice_amounts = cursor.fetchone()
                if invoice_amounts:
                    total_amount = Decimal(str(invoice_amounts['total_amount']))
                    paid_amount_new = Decimal(str(invoice_amounts['paid_amount']))
                    
                    if paid_amount_new >= total_amount - Decimal('0.01'):
                        new_status = 'Ödendi'
                    elif paid_amount_new > Decimal('0.00'):
                        new_status = 'Kısmi Ödendi'
                    else:
                        new_status = 'Ödenmedi'
                    
                    cursor.execute("UPDATE invoices SET status = ? WHERE id = ?", (new_status, invoice_id))
            
            logging.info(f"Fatura #{invoice_id} için {amount_paid} tutarında ödeme eklendi.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ödeme eklenirken hata oluştu: {e}", exc_info=True)
            return False

    def get_payments_for_invoice(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Belirli bir faturaya ait tüm ödemeleri listeler."""
        query = "SELECT payment_date, amount_paid, payment_method, notes FROM payments WHERE invoice_id = ? ORDER BY payment_date DESC"
        return [dict(row) for row in self.fetch_all(query, (invoice_id,))]

    def get_cpc_devices_for_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """
        Bir müşteriye ait CPC anlaşmalı cihazları, en son kaydedilen sayaç bilgileriyle birlikte listeler.
        Ücretsiz cihazlar dahil edilmez.
        """
        query = """
            WITH RankedServiceRecords AS (
                SELECT *, ROW_NUMBER() OVER(PARTITION BY device_id ORDER BY created_date DESC, id DESC) as rn 
                FROM service_records
            ) 
            SELECT cd.id, cd.device_model as model, cd.serial_number, cd.device_type as type, cd.color_type, cd.is_cpc, 
                   rsr.bw_counter, rsr.color_counter, rsr.created_date as last_update 
            FROM customer_devices cd 
            LEFT JOIN RankedServiceRecords rsr ON cd.id = rsr.device_id AND rsr.rn = 1 
            WHERE cd.customer_id = ? AND cd.is_cpc = 1 AND cd.is_free = 0
            ORDER BY cd.device_model
        """
        try:
            logger.debug(f"DEBUG: SQL sorgusu çalıştırılıyor, customer_id: {customer_id}")
            results = self.fetch_all(query, (customer_id,))
            logger.debug(f"DEBUG: SQL sonucu: {len(results)} kayıt")
            if results:
                logger.debug(f"DEBUG: İlk kayıt: {results[0]}")
                logger.debug(f"DEBUG: İlk kayıt sütun sayısı: {len(results[0]) if results[0] else 0}")
            
            return [dict(row) for row in results]
        except Exception as e:
            import traceback
            logger.debug(f"DEBUG: get_cpc_devices_for_customer hatası: {traceback.format_exc()}")
            raise

    def get_billable_cpc_data(self, customer_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Belirtilen müşteri ve tarih aralığı için faturalandırılabilir CPC verilerini hesaplar.
        Bu fonksiyon, belirtilen tarih aralığındaki faturalandırılmamış sayaç okumalarını alır
        ve her biri için bir önceki okumayla (tarih aralığı dışında olabilir) arasındaki farkı bularak tüketimi hesaplar.
        """
        logger.debug(f"DEBUG: get_billable_cpc_data çağrıldı - customer_id: {customer_id}, start_date: {start_date}, end_date: {end_date}")
        query = """
            WITH AllRecords AS (
                -- Müşterinin tüm CPC cihazlarına ait tüm servis kayıtlarını al
                SELECT
                    sr.id as record_id,
                    sr.device_id,
                    sr.created_date,
                    sr.bw_counter,
                    sr.color_counter,
                    sr.is_invoiced,
                    ROW_NUMBER() OVER (PARTITION BY sr.device_id ORDER BY sr.created_date, sr.id) as row_num
                FROM service_records sr
                JOIN customer_devices cd ON sr.device_id = cd.id
                WHERE cd.customer_id = ? AND cd.is_cpc = 1 AND cd.is_free = 0
            ),
            RecordsWithPrevious AS (
                -- Her kayıt için bir önceki kaydı bul (tarih aralığına bakılmaksızın)
                SELECT
                    ar.record_id,
                    ar.device_id,
                    ar.created_date,
                    ar.bw_counter,
                    ar.color_counter,
                    ar.is_invoiced,
                    COALESCE(prev_ar.bw_counter, 0) as prev_bw_counter,
                    COALESCE(prev_ar.color_counter, 0) as prev_color_counter
                FROM AllRecords ar
                LEFT JOIN AllRecords prev_ar ON ar.device_id = prev_ar.device_id 
                    AND prev_ar.row_num = ar.row_num - 1
            )
            SELECT
                rwp.record_id,
                cd.id as device_id,
                cd.device_model as model,
                cd.serial_number,
                cd.color_type,
                rwp.created_date,
                rwp.bw_counter,
                rwp.color_counter,
                rwp.prev_bw_counter,
                rwp.prev_color_counter,
                (rwp.bw_counter - rwp.prev_bw_counter) as bw_usage,
                CASE
                    WHEN cd.color_type = 'Renkli' THEN (rwp.color_counter - rwp.prev_color_counter)
                    ELSE 0
                END as color_usage,
                cd.cpc_bw_price,
                cd.cpc_color_price,
                COALESCE(cd.cpc_bw_currency, 'TL') as cpc_bw_currency,
                COALESCE(cd.cpc_color_currency, 'TL') as cpc_color_currency,
                0.0 as rental_fee,
                'TRY' as rental_currency,
                cd.customer_id
            FROM RecordsWithPrevious rwp
            JOIN customer_devices cd ON rwp.device_id = cd.id
            WHERE
                rwp.is_invoiced = 0
                AND rwp.created_date >= ?
                AND rwp.created_date <= ?
                AND ( (rwp.bw_counter - rwp.prev_bw_counter) > 0 OR (cd.color_type = 'Renkli' AND (rwp.color_counter - rwp.prev_color_counter) > 0) )
            ORDER BY cd.device_model, rwp.created_date;
        """
        end_date_full = end_date + " 23:59:59"
        try:
            logger.debug("DEBUG: SQL sorgusu çalıştırılıyor...")
            results = self.fetch_all(query, (customer_id, start_date, end_date_full))
            logger.debug(f"DEBUG: SQL sonucu: {len(results)} kayıt")
            if results:
                logger.debug(f"DEBUG: İlk kayıt sütun sayısı: {len(results[0])}")
                logger.debug(f"DEBUG: İlk kayıt: {dict(results[0])}")
            
            return [dict(row) for row in results]
        except Exception as e:
            import traceback
            logger.debug(f"DEBUG: get_billable_cpc_data hatası: {traceback.format_exc()}")
            raise

    def mark_service_records_as_invoiced(self, record_ids: List[int], invoice_id: int) -> bool:
        """Verilen servis kaydı ID'lerini faturalandırıldı olarak işaretler."""
        if not record_ids:
            return False
        
        placeholders = ','.join('?' for _ in record_ids)
        query = f"UPDATE service_records SET is_invoiced = 1, related_invoice_id = ? WHERE id IN ({placeholders})"
        
        try:
            self.execute_query(query, [invoice_id] + record_ids)
            logging.info(f"{len(record_ids)} adet servis kaydı fatura #{invoice_id} ile ilişkilendirildi.")
            return True
        except Exception as e:
            logging.error(f"Servis kayıtları faturalandırıldı olarak işaretlenirken hata: {e}", exc_info=True)
            return False

    def get_cpc_billing_data(self, customer_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Belirtilen tarih aralığı için bir müşterinin CPC faturalandırma verilerini hesaplar.
        Her cihaz için başlangıç ve bitiş sayaçlarını bularak tüketimi ve maliyeti hesaplar.
        """
        query = "SELECT id, device_model as model, serial_number, cpc_bw_price, cpc_color_price, device_type as type, COALESCE(cpc_bw_currency, 'TL') as cpc_bw_currency, COALESCE(cpc_color_currency, 'TL') as cpc_color_currency FROM customer_devices WHERE customer_id = ? AND is_cpc = 1 AND is_free = 0"
        cpc_devices = self.fetch_all(query, (customer_id,))
        billing_data = []

        for device in cpc_devices:
            dev_id = device['id']
            
            # Bitiş sayacını bul (verilen aralıktaki en son kayıt)
            end_query = "SELECT id, created_date, bw_counter, color_counter FROM service_records WHERE device_id = ? AND created_date <= ? ORDER BY created_date DESC, id DESC LIMIT 1"
            end_record = self.fetch_one(end_query, (dev_id, end_date + " 23:59:59"))
            
            # Eğer bitiş kaydı yoksa veya aralığın başından daha eskiyse, bu cihazı atla
            if not end_record or end_record['created_date'] < (start_date + " 00:00:00"):
                continue

            # Başlangıç sayacını bul (bitiş kaydından önceki en son kayıt)
            start_query = "SELECT bw_counter, color_counter FROM service_records WHERE device_id = ? AND (created_date < ? OR (created_date = ? AND id < ?)) ORDER BY created_date DESC, id DESC LIMIT 1"
            start_record = self.fetch_one(start_query, (dev_id, end_record['created_date'], end_record['created_date'], end_record['id']))
            
            start_bw = Decimal(start_record['bw_counter'] or 0) if start_record else Decimal(0)
            start_color = Decimal(start_record['color_counter'] or 0) if start_record else Decimal(0)
            end_bw = Decimal(end_record['bw_counter'] or 0)
            end_color = Decimal(end_record['color_counter'] or 0)

            # Sayaç sıfırlanmış olabilir, negatif tüketimi engelle
            if end_bw < start_bw or (device['type'] == 'Renkli' and end_color < start_color):
                continue

            usage_bw = end_bw - start_bw
            usage_color = (end_color - start_color) if device['type'] == 'Renkli' else Decimal(0)

            if (usage_bw + usage_color) > 0:
                bw_price = Decimal(device['cpc_bw_price'] or 0)
                color_price = Decimal(device['cpc_color_price'] or 0)
                
                # TODO: Kur dönüşümü burada da uygulanmalı
                total_bw_cost = usage_bw * bw_price
                total_color_cost = usage_color * color_price
                
                billing_data.append({
                    'model': device['model'], 'serial': device['serial_number'],
                    'usage_bw': float(usage_bw), 'total_bw_cost': float(total_bw_cost),
                    'bw_price': float(bw_price), 'bw_currency': device['cpc_bw_currency'],
                    'usage_color': float(usage_color), 'total_color_cost': float(total_color_cost),
                    'color_price': float(color_price), 'color_currency': device['cpc_color_currency'],
                    'device_total_tl': float(total_bw_cost + total_color_cost) # Varsayım: Fiyatlar TL
                })
        return billing_data

    def get_invoices_for_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Belirli bir müşteriye ait tüm faturaları listeler."""
        query = "SELECT id, invoice_date, invoice_type, total_amount, paid_amount, (total_amount - paid_amount) as balance, status, currency FROM invoices WHERE customer_id = ? ORDER BY invoice_date DESC"
        return [dict(row) for row in self.fetch_all(query, (customer_id,))]

    def get_uninvoiced_cpc_readings(self, customer_id: int) -> List[Dict[str, Any]]:
        """Bir müşteriye ait faturalandırılmamış CPC okumalarını listeler."""
        devices_query = """
            WITH LastInvoicedReading AS (
                SELECT device_id, MAX(created_date) as last_date
                FROM service_records
                WHERE is_invoiced = 1
                GROUP BY device_id
            )
            SELECT 
                cd.id as device_id, 
                cd.device_model as model, 
                cd.serial_number, 
                cd.color_type,
                COALESCE(prev.created_date, '2000-01-01') as start_date,
                sr.created_date as end_date,
                COALESCE(prev.bw_counter, 0) as start_bw,
                sr.bw_counter as end_bw,
                COALESCE(prev.color_counter, 0) as start_color,
                sr.color_counter as end_color,
                cd.cpc_bw_price,
                cd.cpc_color_price,
                COALESCE(cd.cpc_bw_currency, 'TL') as cpc_bw_currency,
                COALESCE(cd.cpc_color_currency, 'TL') as cpc_color_currency
            FROM customer_devices cd
            INNER JOIN service_records sr ON cd.id = sr.device_id AND sr.is_invoiced = 0
            LEFT JOIN LastInvoicedReading lir ON cd.id = lir.device_id
            LEFT JOIN service_records prev ON cd.id = prev.device_id AND prev.created_date = lir.last_date
            WHERE cd.customer_id = ? AND cd.is_cpc = 1 AND cd.is_free = 0
            ORDER BY sr.created_date DESC
        """
        
        # Henüz faturalandırılmamış tüm sayaç okumalarını al
        devices = self.fetch_all(devices_query, (customer_id,))
        
        # Her cihaz için faturalandırılacak dönemleri belirle
        billing_periods = []
        for dev in devices:
            if dev['start_bw'] is None or dev['end_bw'] is None:
                continue
                
            bw_usage = float(dev['end_bw'] or 0) - float(dev['start_bw'] or 0)
            color_usage = float(dev['end_color'] or 0) - float(dev['start_color'] or 0) if dev['color_type'] == 'Renkli' else 0
            
            if bw_usage <= 0 and color_usage <= 0:
                continue
                
            total_amount = (bw_usage * float(dev['cpc_bw_price'] or 0)) + (color_usage * float(dev['cpc_color_price'] or 0))
            
            billing_periods.append({
                'id': f"cpc_{dev['device_id']}",
                'start_date': dev['start_date'],
                'end_date': dev['end_date'],
                'total_amount_tl': total_amount,
                'model': dev['model'],
                'serial': dev['serial_number'],
                'bw_usage': bw_usage,
                'color_usage': color_usage,
                'start_bw': dev['start_bw'],
                'end_bw': dev['end_bw'],
                'start_color': dev['start_color'],
                'end_color': dev['end_color'],
                'cpc_bw_price': dev['cpc_bw_price'],
                'cpc_color_price': dev['cpc_color_price'],
                'cpc_bw_currency': dev['cpc_bw_currency'],
                'cpc_color_currency': dev['cpc_color_currency']
            })
            
        return billing_periods

    def create_consolidated_invoice(self, customer_id: int, total_amount: float, currency: str, details_json: str, original_items: List[Dict[str, str]], vat_rate: float = 20.0) -> bool:
        """
        Birden fazla servis kaydını ve/veya CPC okumasını tek bir 'Toplu Hizmet' faturasında birleştirir.
        İlgili kayıtları 'faturalandı' olarak işaretler.
        """
        conn = self.get_connection()
        if not conn:
            logging.error("Toplu fatura oluşturulamadı: Veritabanı bağlantısı yok.")
            return False
        try:
            with conn:
                cursor = conn.cursor()
                invoice_date = datetime.now().strftime('%Y-%m-%d')
                
                query = "INSERT INTO invoices (customer_id, invoice_type, related_id, invoice_date, total_amount, currency, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)"
                params = (customer_id, 'Toplu Hizmet', customer_id, invoice_date, total_amount, currency, details_json)
                cursor.execute(query, params)
                
                # Orijinal kalemleri 'faturalandı' olarak işaretle
                for item in original_items:
                    item_type, item_id_str = item.get('original_id', '_').split('_')
                    item_id = int(item_id_str)
                    if item_type == 'servis':
                        cursor.execute("UPDATE service_records SET is_invoiced = 1 WHERE id = ?", (item_id,))
                    elif item_type == 'cpc':
                        cursor.execute("UPDATE cpc_invoices SET is_invoiced = 1 WHERE id = ?", (item_id,))
            
            logging.info(f"Müşteri #{customer_id} için toplu fatura başarıyla oluşturuldu.")
            return True
        except (ValueError, sqlite3.Error) as e:
            logging.error(f"Toplu fatura oluşturma hatası: {e}", exc_info=True)
            return False

    def get_items_for_invoice_creation(self, item_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Seçilen işlem ID'lerini (servis ve CPC) alır ve fatura oluşturma için gerekli verileri döndürür.
        """
        items_to_invoice = []
        
        for item_id in item_ids:
            if item_id.startswith('servis_'):
                # Servis işlemi
                service_id = int(item_id.replace('servis_', ''))
                service_data = self.get_service_for_invoice(service_id)
                if service_data:
                    items_to_invoice.append({
                        'type': 'service',
                        'original_id': item_id,
                        'data': service_data
                    })
            elif item_id.startswith('cpc_'):
                # CPC işlemi
                device_id = int(item_id.replace('cpc_', ''))
                cpc_data = self.get_cpc_for_invoice(device_id)
                if cpc_data:
                    items_to_invoice.append({
                        'type': 'cpc',
                        'original_id': item_id,
                        'data': cpc_data
                    })
        
        return items_to_invoice

    def get_service_for_invoice(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Servis kaydının fatura detaylarını alır."""
        query = """
            SELECT sr.id, sr.created_date, cd.device_model as model, sr.notes,
                   (SELECT SUM(qi.total_tl) FROM quote_items qi WHERE qi.service_record_id = sr.id) as total_amount
            FROM service_records sr
            JOIN customer_devices cd ON sr.device_id = cd.id
            WHERE sr.id = ?
        """
        result = self.fetch_one(query, (service_id,))
        return dict(result) if result else None

    def get_cpc_for_invoice(self, device_id: int) -> Optional[Dict[str, Any]]:
        """CPC cihazının faturalanmamış okumalarını alır."""
        cpc_readings = self.get_uninvoiced_cpc_readings_for_device(device_id)
        return cpc_readings[0] if cpc_readings else None

    def get_uninvoiced_cpc_readings_for_device(self, device_id: int) -> List[Dict[str, Any]]:
        """Belirli bir cihaz için faturalandırılmamış CPC okumalarını alır."""
        query = """
            WITH LastInvoicedReading AS (
                SELECT device_id, MAX(created_date) as last_date
                FROM service_records
                WHERE is_invoiced = 1 AND device_id = ?
                GROUP BY device_id
            )
            SELECT 
                cd.id as device_id, 
                cd.device_model as model, 
                cd.serial_number, 
                cd.color_type,
                COALESCE(prev.created_date, '2000-01-01') as start_date,
                sr.created_date as end_date,
                COALESCE(prev.bw_counter, 0) as start_bw,
                sr.bw_counter as end_bw,
                COALESCE(prev.color_counter, 0) as start_color,
                sr.color_counter as end_color,
                cd.cpc_bw_price,
                cd.cpc_color_price,
                COALESCE(cd.cpc_bw_currency, 'TL') as cpc_bw_currency,
                COALESCE(cd.cpc_color_currency, 'TL') as cpc_color_currency
            FROM customer_devices cd
            INNER JOIN service_records sr ON cd.id = sr.device_id AND sr.is_invoiced = 0
            LEFT JOIN LastInvoicedReading lir ON cd.id = lir.device_id
            LEFT JOIN service_records prev ON cd.id = prev.device_id AND prev.created_date = lir.last_date
            WHERE cd.id = ? AND cd.is_cpc = 1 AND cd.is_free = 0
            ORDER BY sr.created_date DESC
            LIMIT 1
        """
        
        devices = self.fetch_all(query, (device_id, device_id))
        
        billing_periods = []
        for dev in devices:
            if dev['start_bw'] is None or dev['end_bw'] is None:
                continue
                
            bw_usage = float(dev['end_bw'] or 0) - float(dev['start_bw'] or 0)
            color_usage = float(dev['end_color'] or 0) - float(dev['start_color'] or 0) if dev['color_type'] == 'Renkli' else 0
            
            if bw_usage <= 0 and color_usage <= 0:
                continue
                
            total_amount = (bw_usage * float(dev['cpc_bw_price'] or 0)) + (color_usage * float(dev['cpc_color_price'] or 0))
            
            billing_periods.append({
                'id': f"cpc_{dev['device_id']}",
                'start_date': dev['start_date'],
                'end_date': dev['end_date'],
                'total_amount_tl': total_amount,
                'model': dev['model'],
                'serial': dev['serial_number'],
                'bw_usage': bw_usage,
                'color_usage': color_usage,
                'start_bw': dev['start_bw'],
                'end_bw': dev['end_bw'],
                'start_color': dev['start_color'],
                'end_color': dev['end_color'],
                'cpc_bw_price': dev['cpc_bw_price'],
                'cpc_color_price': dev['cpc_color_price'],
                'cpc_bw_currency': dev['cpc_bw_currency'],
                'cpc_color_currency': dev['cpc_color_currency']
            })
            
        return billing_periods
    def delete_invoice(self, invoice_id: int) -> bool:
        """
        Belirtilen ID'ye sahip faturayÄ± ve iliÅŸkili verilerini siler.
        AyrÄ±ca ilgili servis kayÄ±tlarÄ±nÄ± tekrar faturalanmamÄ±ÅŸ olarak iÅŸaretler.
        """
        conn = self.get_connection()
        if not conn: 
            return False
        
        try:
            with conn:
                cursor = conn.cursor()
                
                # Ã–nce fatura bilgilerini al
                cursor.execute("SELECT invoice_type, related_id, details_json FROM invoices WHERE id = ?", (invoice_id,))
                invoice_info = cursor.fetchone()
                
                if not invoice_info:
                    raise Exception("Fatura bulunamadÄ±.")
                
                invoice_type = invoice_info["invoice_type"]
                related_id = invoice_info["related_id"]
                details_json = invoice_info["details_json"]

                # Stoktan d?sen ?r?nleri fatura silinince/i?ptal edilince geri al
                try:
                    cols = [row[1] for row in cursor.execute("PRAGMA table_info(stock_movements)").fetchall()]
                    if 'related_invoice_id' in cols:
                        movements = cursor.execute("SELECT stock_item_id, quantity_changed, unit_price, currency FROM stock_movements WHERE related_invoice_id = ?", (invoice_id,)).fetchall()
                        for mv in movements:
                            try:
                                stock_item_id = mv["stock_item_id"]
                                qty_changed = mv["quantity_changed"]
                                unit_price = mv["unit_price"]
                                currency = mv["currency"]
                            except Exception:
                                stock_item_id = mv[0]
                                qty_changed = mv[1]
                                unit_price = mv[2] if len(mv) > 2 else None
                                currency = mv[3] if len(mv) > 3 else None
                            if qty_changed is None:
                                continue
                            try:
                                qty_changed_val = Decimal(str(qty_changed))
                            except Exception:
                                continue
                            if qty_changed_val >= 0:
                                continue
                            restore_qty = -qty_changed_val
                            row = cursor.execute("SELECT quantity FROM stock_items WHERE id = ?", (stock_item_id,)).fetchone()
                            if not row:
                                continue
                            try:
                                current_qty = Decimal(str(row["quantity"]))
                            except Exception:
                                current_qty = Decimal(str(row[0]))
                            new_qty = current_qty + restore_qty
                            cursor.execute("UPDATE stock_items SET quantity = ? WHERE id = ?", (float(new_qty), stock_item_id))
                            movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            notes = f"Fatura iptali: Stok iade (Fatura No: {invoice_id})"
                            cursor.execute("INSERT INTO stock_movements (stock_item_id, movement_type, quantity_changed, quantity_after, unit_price, currency, movement_date, notes, related_invoice_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                           (stock_item_id, 'Giriş', float(restore_qty), float(new_qty), unit_price, currency, movement_date, notes, invoice_id))
                except Exception as e:
                    logging.error(f"Fatura #{invoice_id} stok iade işlemi hatası: {e}", exc_info=True)
                
                # Fatura tipine gÃ¶re ilgili kayÄ±tlarÄ± tekrar faturalanmamÄ±ÅŸ olarak iÅŸaretle
                if invoice_type == "Servis":
                    # Servis kaydÄ±nÄ± tekrar faturalanmamÄ±ÅŸ olarak iÅŸaretle
                    cursor.execute("UPDATE service_records SET is_invoiced = 0 WHERE id = ?", (related_id,))
                
                elif invoice_type == "Kopya BaÅŸÄ±":
                    # CPC faturasÄ± - details_json'dan cihaz ID'lerini al ve sayaÃ§ kayÄ±tlarÄ±nÄ± iÅŸaretle
                    try:
                        details = json.loads(details_json)
                        for item in details:
                            device_id = item.get("device_id")
                            record_ids = item.get("record_ids", [])
                            if device_id and record_ids:
                                # Bu cihaza ait kayÄ±tlarÄ± tekrar faturalanmamÄ±ÅŸ olarak iÅŸaretle
                                placeholders = ",".join("?" for _ in record_ids)
                                cursor.execute(f"UPDATE service_records SET is_invoiced = 0 WHERE id IN ({placeholders})", record_ids)
                    except (json.JSONDecodeError, KeyError) as e:
                        logging.warning(f"CPC fatura detaylarÄ± ayrÄ±ÅŸtÄ±rÄ±lamadÄ±: {e}")
                
                # Fatura ile iliÅŸkili Ã¶demeleri sil
                cursor.execute("DELETE FROM payments WHERE invoice_id = ?", (invoice_id,))
                
                # Ana faturayÄ± sil
                cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
                
            logging.info(f"Fatura #{invoice_id} baÅŸarÄ±yla silindi.")
            return True
            
        except Exception as e:
            logging.error(f"Fatura #{invoice_id} silinirken hata oluÅŸtu: {e}", exc_info=True)
            return False
