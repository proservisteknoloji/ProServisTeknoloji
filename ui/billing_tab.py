# -*- coding: utf-8 -*-
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
logger = logging.getLogger(__name__)

from PyQt6.QtCore import Qt, QDate, pyqtSignal as Signal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QLineEdit, QPushButton,
    QMessageBox, QHeaderView, QCompleter, QFileDialog
)

from utils.currency_converter import get_exchange_rates
from utils.pdf_generator import create_professional_invoice_pdf

class BillingTab(QWidget):
    """Sayaç okuma ve CPC faturalandırma işlemlerini yöneten sekme."""
    data_changed = Signal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.parent_window = parent
        self.meter_inputs = {}
        self.status_bar = getattr(self.parent_window, 'status_bar', None)
        self.init_ui()
        self.load_customers()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        controls_group = self._create_controls_group()
        self.meters_table = self._create_meters_table()
        button_layout = self._create_button_layout()
        
        main_layout.addWidget(controls_group)
        main_layout.addWidget(self.meters_table)
        main_layout.addLayout(button_layout)
        
        self._connect_signals()

    def _create_controls_group(self):
        """Müşteri ve tarih seçimi kontrollerini içeren grubu oluşturur."""
        group = QGroupBox("Müşteri ve Fatura Dönemi Seçimi")
        layout = QHBoxLayout(group)
        
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.customer_combo.lineEdit().setPlaceholderText("Müşteri Seçin veya Filtreleyin...")
        
        today = QDate.currentDate()
        self.start_date_edit = QDateEdit(today.addMonths(-1))
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit = QDateEdit(today)
        self.end_date_edit.setCalendarPopup(True)
        
        layout.addWidget(QLabel("Müşteri:"))
        layout.addWidget(self.customer_combo, 1)
        layout.addWidget(QLabel("Başlangıç Tarihi:"))
        layout.addWidget(self.start_date_edit)
        layout.addWidget(QLabel("Bitiş Tarihi:"))
        layout.addWidget(self.end_date_edit)
        
        return group

    def _create_meters_table(self):
        """Sayaç bilgilerini gösteren tabloyu oluşturur."""
        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels([
            "Cihaz ID", "Cihaz Modeli", "Seri No", 
            "Son S/B Sayaç", "Yeni S/B Sayaç", 
            "Son Renkli Sayaç", "Yeni Renkli Sayaç"
        ])
        table.setColumnHidden(0, True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in [3, 4, 5, 6]:
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _create_button_layout(self):
        """İşlem butonlarını içeren layout'u oluşturur."""
        layout = QHBoxLayout()
        self.save_meters_btn = QPushButton("💾 Sayaçları Kaydet")
        self.create_invoice_btn = QPushButton("📄 Faturaya Dönüştür")
        
        layout.addStretch()
        layout.addWidget(self.save_meters_btn)
        layout.addWidget(self.create_invoice_btn)
        return layout

    def _connect_signals(self):
        """Sinyalleri slotlara bağlar."""
        self.customer_combo.activated.connect(self.populate_devices_for_customer)
        self.save_meters_btn.clicked.connect(self.save_meters)
        self.create_invoice_btn.clicked.connect(self.create_invoice)

    def load_customers(self):
        """Müşteri listesini veritabanından yükler - sadece CPC cihazı olan müşteriler."""
        self.customer_combo.blockSignals(True)
        current_data = self.customer_combo.currentData()
        self.customer_combo.clear()
        try:
            # Sadece CPC cihazı olan müşterileri getir (customer_devices tablosundan)
            customers = self.db.fetch_all("""
                SELECT DISTINCT c.id, c.name 
                FROM customers c 
                INNER JOIN customer_devices cd ON c.id = cd.customer_id 
                WHERE cd.is_cpc = 1 
                ORDER BY c.name
            """)
            
            if not customers:
                self.customer_combo.addItem("CPC cihazı olan müşteri bulunamadı", None)
                return
                
            for cust_id, name in customers:
                self.customer_combo.addItem(name, cust_id)
            
            if current_data:
                idx = self.customer_combo.findData(current_data)
                if idx > -1:
                    self.customer_combo.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Müşteriler yüklenirken bir hata oluştu: {str(e)}")
        finally:
            self.customer_combo.blockSignals(False)

    def populate_devices_for_customer(self, index=-1):
        """Seçilen müşteriye ait cihazları tabloya yükler."""
        customer_id = self.customer_combo.currentData()
        self.meters_table.setRowCount(0)
        self.meter_inputs.clear()
        
        if not customer_id:
            return
            
        try:
            logger.debug(f"DEBUG: Müşteri ID: {customer_id} için cihazlar alınıyor...")
            devices = self.db.get_cpc_devices_for_customer(customer_id)
            logger.debug(f"DEBUG: {len(devices) if devices else 0} cihaz bulundu")
            
            if not devices:
                # Artık CPC cihazı olmayan müşteriler listede olmayacağı için
                # bu durumda daha uygun bir mesaj gösterelim
                QMessageBox.information(self, "Bilgi", 
                    f"Seçilen müşteriye ait CPC cihaz bulunamadı.\n\n"
                    f"Bu durum şu sebeplerden olabilir:\n"
                    f"• Henüz bu müşteri için sayaç okuma kaydı girilmemiş\n"
                    f"• Cihazın CPC ayarları yanlış yapılandırılmış\n\n"
                    f"Lütfen Müşteri ve Cihaz Yönetimi sekmesinden kontrol edin.")
                return

            self.meters_table.setRowCount(len(devices))
            for row, device in enumerate(devices):
                logger.debug(f"DEBUG: Cihaz {row}: {device}")
                self._add_device_row_to_table(row, device)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logging.error(f"populate_devices_for_customer hatası: {error_details}")
            QMessageBox.critical(self, "Veritabanı Hatası", f"Cihazlar yüklenirken bir hata oluştu:\n{str(e)}\n\nDetay:\n{error_details}")

    def _add_device_row_to_table(self, row, device_data):
        """Tabloya tek bir cihaz satırı ekler."""
        dev_id = device_data['id']
        
        self.meters_table.setItem(row, 0, QTableWidgetItem(str(dev_id)))
        self.meters_table.setItem(row, 1, QTableWidgetItem(device_data['model']))
        self.meters_table.setItem(row, 2, QTableWidgetItem(device_data['serial_number']))
        self.meters_table.setItem(row, 3, QTableWidgetItem(str(device_data.get('bw_counter', 0) or 0)))
        
        new_bw_input = QLineEdit()
        new_bw_input.setPlaceholderText("Yeni S/B Sayaç")
        self.meters_table.setCellWidget(row, 4, new_bw_input)
        
        self.meters_table.setItem(row, 5, QTableWidgetItem(str(device_data.get('color_counter', 0) or 0)))
        
        if device_data['color_type'] == 'Renkli':
            new_color_input = QLineEdit()
            new_color_input.setPlaceholderText("Yeni Renkli Sayaç")
            self.meters_table.setCellWidget(row, 6, new_color_input)
        else:
            label_na = QLabel("N/A")
            label_na.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.meters_table.setCellWidget(row, 6, label_na)
            new_color_input = None # Renkli olmayan cihazlar için input None
            
        self.meter_inputs[dev_id] = (new_bw_input, new_color_input)

    def save_meters(self):
        """Girilen yeni sayaç değerlerini işler ve veritabanına kaydeder."""
        try:
            user_id_tuple = self.db.fetch_one("SELECT id FROM users WHERE username = ?", (self.parent_window.logged_in_user,))
            if not user_id_tuple:
                QMessageBox.critical(self, "Kullanıcı Hatası", "Giriş yapan kullanıcı bulunamadı.")
                return
            
            logged_in_user_id = user_id_tuple[0]
            saved_count = self._process_meter_inputs(logged_in_user_id)
            
            if saved_count > 0:
                self.data_changed.emit()
                QMessageBox.information(self, "Başarılı", f"{saved_count} cihaz için sayaç değerleri kaydedildi.")
                if self.status_bar:
                    self.status_bar.showMessage(f"{saved_count} cihaz için sayaç değerleri başarıyla kaydedildi.", 5000)
                # Veri kaydedildikten sonra tabloyu yenile
                self.populate_devices_for_customer()
            else:
                QMessageBox.warning(self, "Uyarı", "Kaydedilecek geçerli bir sayaç girişi bulunamadı.")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Sayaç değerleri kaydedilirken bir hata oluştu: {str(e)}")

    def _process_meter_inputs(self, logged_in_user_id):
        """Girilen sayaç değerlerini işler ve veritabanına kaydeder."""
        saved_count = 0
        operation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for dev_id, (bw_input, color_input) in self.meter_inputs.items():
            new_bw_str = bw_input.text().strip()
            new_color_str = color_input.text().strip() if color_input else ""
            
            if not new_bw_str and not new_color_str:
                continue

            try:
                row_index = self._find_row_by_device_id(dev_id)
                if row_index == -1: continue

                device_model = self.meters_table.item(row_index, 1).text()
                
                new_bw = int(new_bw_str) if new_bw_str else None
                last_bw = int(self.meters_table.item(row_index, 3).text())
                if new_bw is not None and not self._validate_counter_value(new_bw, last_bw, device_model, "S/B"):
                    continue

                new_color = int(new_color_str) if new_color_str else None
                if new_color is not None and color_input:
                    last_color = int(self.meters_table.item(row_index, 5).text())
                    if not self._validate_counter_value(new_color, last_color, device_model, "Renkli"):
                        continue
                
                # Sadece yeni bir değer girilmişse kaydet
                if new_bw is not None or new_color is not None:
                    self.db.add_meter_reading_record(
                        device_id=dev_id,
                        assigned_user_id=logged_in_user_id,
                        bw_counter=new_bw,
                        color_counter=new_color
                    )
                    saved_count += 1

            except ValueError:
                QMessageBox.warning(self, "Hata", f"'{device_model}' için geçersiz sayaç değeri girildi.")
                continue
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"'{device_model}' için sayaç kaydedilemedi: {e}")
                continue

        return saved_count

    def _validate_counter_value(self, new_value, last_value, device_model, counter_type="S/B"):
        """Yeni sayaç değerinin geçerliliğini kontrol eder."""
        if new_value < last_value:
            QMessageBox.warning(self, "Hatalı Sayaç", 
                f"'{device_model}' cihazının yeni {counter_type} sayacı ({new_value}) "
                f"eskisinden ({last_value}) küçük olamaz.")
            return False
        return True

    def create_invoice(self):
        """Seçili müşteri için faturalandırılmamış CPC okumalarından fatura oluşturur."""
        logger.debug("DEBUG: create_invoice fonksiyonu çağrıldı")
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir müşteri seçin.")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        try:
            logger.debug(f"DEBUG: get_billable_cpc_data çağrılıyor - customer_id: {customer_id}, start_date: {start_date}, end_date: {end_date}")
            billable_data = self.db.get_billable_cpc_data(customer_id, start_date, end_date)
            logger.debug(f"DEBUG: billable_data alındı - {len(billable_data) if billable_data else 0} kayıt")

            if not billable_data:
                QMessageBox.information(self, "Bilgi", "Seçilen tarih aralığında faturalandırılacak yeni sayaç okuması bulunamadı.")
                return

            rates = get_exchange_rates()
            logger.debug(f"DEBUG-RATES: TCMB'den çekilen döviz kurları: {rates}")
            
            # Kur kontrolü - eksik kurları belirle
            missing_currencies = []
            if not rates:
                missing_currencies = ['TÜM KURLAR']
            else:
                if 'EUR' not in rates:
                    missing_currencies.append('EUR')
                if 'USD' not in rates:
                    missing_currencies.append('USD')
            
            if missing_currencies:
                error_msg = f"Döviz kurları alınamadı!\n\n"
                error_msg += f"Eksik kurlar: {', '.join(missing_currencies)}\n\n"
                error_msg += f"Lütfen kontrol edin:\n"
                error_msg += f"• İnternet bağlantınız aktif mi?\n"
                error_msg += f"• TCMB web sitesine erişim var mı?\n\n"
                error_msg += f"Not: Varsayılan kurlar kullanılacak ancak fatura tutarları yanlış olabilir."
                logger.warning(f"⚠️ UYARI: {error_msg}")
                
                # Kullanıcıya uyarı göster ama devam etmesine izin ver (varsayılan kurlarla)
                reply = QMessageBox.warning(
                    self, "Döviz Kuru Uyarısı", 
                    error_msg + "\n\nYine de devam etmek istiyor musunuz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            logger.debug("DEBUG: _process_billing_data çağrılıyor")
            invoice_details, grand_total_tl = self._process_billing_data(billable_data, rates, customer_id, start_date, end_date)

            logger.debug(f"DEBUG: Fatura detayları oluşturuldu - {len(invoice_details)} kalem, toplam: {grand_total_tl} TL")

            if not invoice_details:
                QMessageBox.warning(self, "Uyarı", "Hesaplama sonrası faturalandırılacak veri bulunamadı.")
                return

            # Müşterinin ilk lokasyonunu al
            location_row = self.db.fetch_one("SELECT id FROM customer_locations WHERE customer_id = ? ORDER BY id ASC LIMIT 1", (customer_id,))
            if not location_row:
                QMessageBox.critical(self, "Lokasyon Hatası", "Bu müşteriye ait bir lokasyon bulunamadı. Fatura oluşturmak için önce müşteri lokasyonu ekleyin.")
                return
            location_id = location_row['id']

            # Faturayı veritabanına kaydet
            details_json = json.dumps([{k: str(v) for k, v in item.items()} for item in invoice_details], ensure_ascii=False, indent=4)
            logger.debug(f"DEBUG-JSON: invoice_details (STRINGIFIED): {details_json}")

            invoice_id = self.db.create_cpc_invoice(
                location_id=location_id,
                start_date=start_date,
                end_date=end_date,
                total_tl=float(grand_total_tl),
                details_json=details_json
            )
            
            # Faturalandırılan kayıtları işaretle
            if invoice_id:
                for item in invoice_details:
                    for record_id in item.get('record_ids', []):
                        self.db.execute_query("UPDATE service_records SET is_invoiced = 1 WHERE id = ?", (record_id,))
            
            # Fatura verilerini PDF'e yazdırmak için hazırla
            if invoice_id:
                customer_info = self.db.get_customer_by_id(customer_id)
                company_info = self.db.get_all_company_info()
                
                # PDF'e gönderilecek fatura kalemlerini formatla
                pdf_items = []
                def _norm(cur):
                    c = str(cur or 'TL').strip().upper()
                    if c in ('EURO','EUR','E'): return 'EUR'
                    if c in ('DOLAR','USD','US$'): return 'USD'
                    if c in ('TL','TRY','₺'): return 'TL'
                    return c
                for item in invoice_details:
                    # Kiralama bedeli kalemi ise
                    if item.get('is_rental', False):
                        # Sadeleştirilmiş kiralama bedeli açıklaması
                        model = item.get('model', '')
                        serial_number = item.get('serial_number', '')
                        rental_item = {
                            "description": f"{model} ({serial_number}) - Aylık Kiralama",
                            "quantity": item['quantity'],
                            "unit_price": float(item.get('unit_price_tl', 0)),  # Sadece TL fiyat göster
                            "unit_price_tl": float(item.get('unit_price_tl', 0)),
                            "total": float(item.get('total_tl', 0)),
                            "currency": 'TL'  # Her zaman TL göster
                        }
                        logger.debug(f"DEBUG: Kiralama bedeli PDF kalemi: {rental_item}")
                        pdf_items.append(rental_item)
                    else:
                        # Normal CPC kalemi
                        device_model = item['model']
                        serial_number = item['serial_number']
                        bw_usage = int(item['bw_usage'])
                        color_usage = int(item['color_usage'])
                        
                        # Siyah-beyaz kullanım kalemi (eğer kullanım varsa)
                        if bw_usage > 0:
                            bw_unit_price_tl = float(item.get('cpc_bw_price_tl', 0))
                            bw_total_tl = float(item.get('total_bw_cost_tl', 0))
                            bw_item = {
                                "description": f"{device_model} ({serial_number}) - S/B Baskı",
                                "quantity": bw_usage,
                                "unit_price": bw_unit_price_tl,  # Sadece TL fiyat
                                "unit_price_tl": bw_unit_price_tl,
                                "total": bw_total_tl,
                                "currency": 'TL'  # Her zaman TL göster
                            }
                            logger.debug(f"DEBUG: S/B PDF kalemi: {bw_item}")
                            pdf_items.append(bw_item)
                        
                        # Renkli kullanım kalemi (eğer kullanım varsa)
                        if color_usage > 0:
                            color_unit_price_tl = float(item.get('cpc_color_price_tl', 0))
                            color_total_tl = float(item.get('total_color_cost_tl', 0))
                            color_item = {
                                "description": f"{device_model} ({serial_number}) - Renkli Baskı",
                                "quantity": color_usage,
                                "unit_price": color_unit_price_tl,  # Sadece TL fiyat
                                "unit_price_tl": color_unit_price_tl,
                                "total": color_total_tl,
                                "currency": 'TL'  # Her zaman TL göster
                            }
                            logger.debug(f"DEBUG: Renkli PDF kalemi: {color_item}")
                            pdf_items.append(color_item)

                logger.debug(f"DEBUG-PDFITEMS: pdf_items={pdf_items}")
                pdf_data = {
                    'id': invoice_id,
                    'invoice_date': end_date,
                    'customer_info': customer_info,
                    'company_info': company_info,
                    'items': pdf_items,
                    'vat_rate': self.db.get_setting('default_vat_rate', 20),
                    'currency': 'TL',
                }
                
                # Faturayı PDF olarak kaydetmek için dosya iletişim kutusunu aç
                self._save_invoice_pdf(pdf_data)

                self.data_changed.emit()
                QMessageBox.information(self, "Başarılı", f"Fatura (ID: {invoice_id}) başarıyla oluşturuldu.")
                self._redirect_to_invoicing_tab()

        except Exception as e:
            QMessageBox.critical(self, "Fatura Oluşturma Hatası", f"Fatura oluşturulurken beklenmedik bir hata oluştu: {str(e)}")

    def _save_invoice_pdf(self, invoice_data):
        """Oluşturulan faturayı PDF olarak kaydetmek için dosya diyalogunu açar."""
        customer_name = invoice_data.get('customer_info', {}).get('name', 'bilinmeyen_musteri')
        invoice_date = invoice_data.get('invoice_date', datetime.now().strftime('%Y-%m-%d'))
        safe_customer_name = "".join(c for c in customer_name if c.isalnum() or c in " _-").rstrip()
        
        default_filename = f"cpc_fatura_{safe_customer_name}_{invoice_date}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Faturayı Kaydet", default_filename, "PDF Dosyaları (*.pdf)")
        
        if file_path:
            try:
                success = create_professional_invoice_pdf(invoice_data, file_path)
                if success:
                    QMessageBox.information(self, "Başarılı", f"Fatura başarıyla PDF olarak kaydedildi:\n{file_path}")
                else:
                    QMessageBox.critical(self, "PDF Hatası", "Fatura PDF dosyası oluşturulamadı.")
            except Exception as e:
                QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")

    def _process_billing_data(self, billable_data, rates, customer_id=None, start_date: str | None = None, end_date: str | None = None):
        """Fatura verilerini işler, maliyetleri hesaplar ve TL'ye çevirir. Cihaz bazında toplulaştırır."""
        # Cihaz bazında verileri toplulaştır
        device_aggregates = {}
        
        if not customer_id and billable_data:
            customer_id = billable_data[0].get('customer_id')
            
        logger.debug(f"DEBUG: Müşteri ID: {customer_id}")
        
        for data in billable_data:
            device_id = data.get('device_id')
            if not device_id:
                continue
                
            bw_usage = Decimal(data.get('bw_usage', 0))
            color_usage = Decimal(data.get('color_usage', 0))

            if bw_usage <= 0 and color_usage <= 0:
                continue

            if device_id not in device_aggregates:
                # İlk kez karşılaşılan cihaz - temel bilgileri kaydet
                device_aggregates[device_id] = {
                    'device_id': device_id,
                    'model': data.get('model', ''),
                    'serial_number': data.get('serial_number', ''),
                    'color_type': data.get('color_type', ''),
                    'cpc_bw_price': Decimal(data.get('cpc_bw_price', 0)),
                    'cpc_color_price': Decimal(data.get('cpc_color_price', 0)),
                    'cpc_bw_currency': data.get('cpc_bw_currency', 'TL'),
                    'cpc_color_currency': data.get('cpc_color_currency', 'TL'),
                    'total_bw_usage': Decimal('0'),
                    'total_color_usage': Decimal('0'),
                    'record_ids': []  # Faturalandırılan kayıt ID'lerini takip et
                }
            
            # Kullanımları topla
            device_aggregates[device_id]['total_bw_usage'] += bw_usage
            device_aggregates[device_id]['total_color_usage'] += color_usage
            device_aggregates[device_id]['record_ids'].append(data.get('record_id'))

        # Toplulaştırılmış verileri işle
        invoice_details = []
        grand_total_tl = Decimal('0.00')

        for device_id, device_data in device_aggregates.items():
            try:
                bw_usage = device_data['total_bw_usage']
                color_usage = device_data['total_color_usage']
                
                cpc_bw_price = device_data['cpc_bw_price']
                cpc_color_price = device_data['cpc_color_price']
                
                bw_currency = device_data['cpc_bw_currency']
                color_currency = device_data['cpc_color_currency']
                
                logger.debug(f"DEBUG-CURRENCY: Cihaz {device_id} - Ham para birimleri: BW='{bw_currency}', Color='{color_currency}'")
                
                # Normalize currency codes: map common variants to ISO codes used in rates
                def _normalize_currency(cur):
                    if not cur:
                        logger.debug(f"DEBUG-CURRENCY: Para birimi boş/None, varsayılan TL kullanılıyor")
                        return 'TL'
                    c = str(cur).strip().upper()
                    original_c = c
                    if c in ('EURO', 'EUR', 'E', '€'): 
                        c = 'EUR'
                    elif c in ('DOLAR', 'USD', 'US$', '$', 'DOLLAR'): 
                        c = 'USD'
                    elif c in ('TL', 'TRY', '₺', 'TÜRK LİRASI', 'TURK LIRASI'): 
                        c = 'TL'
                    else:
                        # Bilinmeyen para birimi - logla ve varsayılan olarak TL kullan
                        logger.debug(f"DEBUG-CURRENCY: Bilinmeyen para birimi '{original_c}', TL olarak işleniyor")
                        c = 'TL'
                    
                    if original_c != c:
                        logger.debug(f"DEBUG-CURRENCY: Para birimi normalize edildi: '{original_c}' -> '{c}'")
                    return c
                bw_currency = _normalize_currency(bw_currency)
                color_currency = _normalize_currency(color_currency)
                
                logger.debug(f"DEBUG-CURRENCY: Normalize edilmiş para birimleri: BW='{bw_currency}', Color='{color_currency}'")
                logger.debug(f"DEBUG-RATES: Mevcut döviz kurları: {rates}")
                logger.debug(f"DEBUG-RATES: BW para birimi '{bw_currency}' için kur: {rates.get(bw_currency, 'BULUNAMADI')}")
                logger.debug(f"DEBUG-RATES: Color para birimi '{color_currency}' için kur: {rates.get(color_currency, 'BULUNAMADI')}")
                
                bw_rate = Decimal(str(rates.get(bw_currency, 1.0)))
                color_rate = Decimal(str(rates.get(color_currency, 1.0)))
                
                # Kur kontrolü - eğer döviz ise ama kur 1.0 ise uyarı ver
                if bw_currency != 'TL' and bw_rate == Decimal('1.0'):
                    logger.warning(f"⚠️ UYARI: {bw_currency} için kur bulunamadı, 1.0 kullanılıyor!")
                if color_currency != 'TL' and color_rate == Decimal('1.0'):
                    logger.warning(f"⚠️ UYARI: {color_currency} için kur bulunamadı, 1.0 kullanılıyor!")

                logger.debug(f"DEBUG-CALC: ═══ Cihaz {device_id} Hesaplama Başlangıcı ═══")
                logger.debug(f"DEBUG-CALC: BW Kullanım: {bw_usage} sayfa")
                logger.debug(f"DEBUG-CALC: BW Birim Fiyat: {cpc_bw_price} {bw_currency}")
                logger.debug(f"DEBUG-CALC: BW Kur: {bw_rate}")
                logger.debug(f"DEBUG-CALC: Color Kullanım: {color_usage} sayfa")
                logger.debug(f"DEBUG-CALC: Color Birim Fiyat: {cpc_color_price} {color_currency}")
                logger.debug(f"DEBUG-CALC: Color Kur: {color_rate}")

                # Toplam maliyetleri hesapla (orijinal para biriminde)
                total_bw_cost = bw_usage * cpc_bw_price
                total_color_cost = color_usage * cpc_color_price
                
                logger.debug(f"DEBUG-CALC: BW Toplam Maliyet ({bw_currency}): {total_bw_cost}")
                logger.debug(f"DEBUG-CALC: Color Toplam Maliyet ({color_currency}): {total_color_cost}")

                # TL'ye çevir
                total_bw_cost_tl = total_bw_cost * bw_rate
                total_color_cost_tl = total_color_cost * color_rate
                
                logger.debug(f"DEBUG-CALC: BW Toplam Maliyet (TL): {bw_currency} {total_bw_cost} × {bw_rate} = {total_bw_cost_tl} TL")
                logger.debug(f"DEBUG-CALC: Color Toplam Maliyet (TL): {color_currency} {total_color_cost} × {color_rate} = {total_color_cost_tl} TL")

                # TL'ye çevrilmiş birim fiyatları da hesapla
                cpc_bw_price_tl = (cpc_bw_price * bw_rate).quantize(Decimal('0.0001'))
                cpc_color_price_tl = (cpc_color_price * color_rate).quantize(Decimal('0.0001'))
                
                logger.debug(f"DEBUG-CALC: BW Birim Fiyat (TL): {bw_currency} {cpc_bw_price} × {bw_rate} = {cpc_bw_price_tl} TL")
                logger.debug(f"DEBUG-CALC: Color Birim Fiyat (TL): {color_currency} {cpc_color_price} × {color_rate} = {cpc_color_price_tl} TL")
                logger.debug(f"DEBUG-CALC: ═══ Cihaz {device_id} Hesaplama Sonu ═══")

                device_total_tl = total_bw_cost_tl + total_color_cost_tl
                grand_total_tl += device_total_tl

                detail = {
                    'device_id': device_id,
                    'model': device_data['model'],
                    'serial_number': device_data['serial_number'],
                    'color_type': device_data['color_type'],
                    'bw_usage': bw_usage,
                    'color_usage': color_usage,
                    'cpc_bw_price': cpc_bw_price,
                    'cpc_color_price': cpc_color_price,
                    'cpc_bw_currency': bw_currency,
                    'cpc_color_currency': color_currency,
                    'total_bw_cost': total_bw_cost,
                    'total_color_cost': total_color_cost,
                    'total_bw_cost_tl': total_bw_cost_tl,
                    'total_color_cost_tl': total_color_cost_tl,
                    'cpc_bw_price_tl': cpc_bw_price_tl,
                    'cpc_color_price_tl': cpc_color_price_tl,
                    'device_total_tl': device_total_tl,
                    'record_ids': device_data['record_ids']  # Faturalandırılacak kayıt ID'leri
                }
                invoice_details.append(detail)

            except (InvalidOperation, TypeError) as e:
                raise ValueError(f"Fatura verisi işlenirken geçersiz bir değerle karşılaşıldı: {e} (Cihaz ID: {device_id})")

        # Cihazlara tanımlı aylık kiralama bedellerini ekle
        if customer_id:
            logger.debug(f"DEBUG: Müşteri için kiralama bedelleri aranıyor...")
            rental_devices = self.db.fetch_all("""
                SELECT id, device_model as model, serial_number, rental_fee, rental_currency 
                FROM customer_devices 
                WHERE customer_id = ? AND rental_fee > 0
            """, (customer_id,))
            
            logger.debug(f"DEBUG: {len(rental_devices)} adet kiralama bedeli olan cihaz bulundu")
            if rental_devices:
                for i, rd in enumerate(rental_devices):
                    logger.debug(f"DEBUG: Kiralama cihaz {i}: {rd}")
            else:
                logger.debug("DEBUG: rental_devices listesi boş")
            
            for device in rental_devices:
                device_id, model, serial_number, rental_fee, rental_currency = device
                rental_fee = Decimal(str(rental_fee))
                
                logger.debug(f"DEBUG-RENTAL: ═══ Kiralama Bedeli Hesaplama Başlangıcı ═══")
                logger.debug(f"DEBUG-RENTAL: Cihaz: {model} ({serial_number})")
                logger.debug(f"DEBUG-RENTAL: Ham kiralama bedeli: {rental_fee} {rental_currency}")
                
                if rental_fee > 0:
                    # Para birimini normalize et (aynı _normalize_currency fonksiyonunu kullan)
                    def _normalize_rental_currency(cur):
                        if not cur:
                            logger.debug(f"DEBUG-RENTAL: Kiralama para birimi boş/None, varsayılan TL kullanılıyor")
                            return 'TL'
                        c = str(cur).strip().upper()
                        original_c = c
                        if c in ('EURO', 'EUR', 'E', '€'): 
                            c = 'EUR'
                        elif c in ('DOLAR', 'USD', 'US$', '$', 'DOLLAR'): 
                            c = 'USD'
                        elif c in ('TL', 'TRY', '₺', 'TÜRK LİRASI', 'TURK LIRASI'): 
                            c = 'TL'
                        else:
                            logger.debug(f"DEBUG-RENTAL: Bilinmeyen kiralama para birimi '{original_c}', TL olarak işleniyor")
                            c = 'TL'
                        
                        if original_c != c:
                            logger.debug(f"DEBUG-RENTAL: Kiralama para birimi normalize edildi: '{original_c}' -> '{c}'")
                        return c
                    
                    rental_currency = _normalize_rental_currency(rental_currency)
                    logger.debug(f"DEBUG-RENTAL: Normalize edilmiş para birimi: {rental_currency}")
                    
                    # Kiralama bedelini TL'ye çevir
                    rental_rate = Decimal(str(rates.get(rental_currency, 1.0)))
                    logger.debug(f"DEBUG-RENTAL: Döviz kuru ({rental_currency}): {rental_rate}")
                    
                    # Kur kontrolü
                    if rental_currency != 'TL' and rental_rate == Decimal('1.0'):
                        logger.warning(f"⚠️ UYARI: Kiralama bedeli için {rental_currency} kuru bulunamadı, 1.0 kullanılıyor!")
                    
                    rental_fee_tl = rental_fee * rental_rate
                    logger.debug(f"DEBUG-RENTAL: Kiralama bedeli TL: {rental_currency} {rental_fee} × {rental_rate} = {rental_fee_tl} TL")
                    
                    # Prorata hesaplama: start/end tarihleri verildiyse, kiralama bedelinin fatura periyoduna göre hesaplanması
                    rental_billed_tl = rental_fee_tl
                    quantity_for_rental = 1.0
                    if start_date and end_date:
                        try:
                            from datetime import datetime as _dt
                            s = _dt.strptime(start_date, '%Y-%m-%d')
                            e = _dt.strptime(end_date, '%Y-%m-%d')
                            days = (e - s).days + 1
                            
                            # Tam ay kontrolü: 28-31 gün arası tam ay sayılır
                            if 28 <= days <= 31:
                                quantity_for_rental = 1.0
                                rental_billed_tl = rental_fee_tl
                                logger.debug(f"DEBUG-RENTAL: Tam ay ({days} gün), quantity=1, tutar={rental_billed_tl} TL")
                            else:
                                # Kısmi ay için prorata hesaplama (30 gün üzerinden)
                                quantity_for_rental = float((Decimal(days) / Decimal(30)).quantize(Decimal('0.01')))
                                rental_billed_tl = (rental_fee_tl * Decimal(days) / Decimal(30)).quantize(Decimal('0.01'))
                                logger.debug(f"DEBUG-RENTAL: Prorata hesaplama: {days} gün / 30 gün = {quantity_for_rental}")
                                logger.debug(f"DEBUG-RENTAL: Prorata kiralama bedeli: {rental_fee_tl} × {quantity_for_rental} = {rental_billed_tl} TL")
                        except Exception as ex:
                            logger.debug(f"DEBUG-RENTAL: Prorata hesaplama hatası: {ex}, tam aylık ücret kullanılıyor")
                            rental_billed_tl = rental_fee_tl
                            quantity_for_rental = 1.0
                    
                    grand_total_tl += rental_billed_tl
                    logger.debug(f"DEBUG-RENTAL: Faturaya eklenen tutar: {rental_billed_tl} TL")
                    logger.debug(f"DEBUG-RENTAL: ═══ Kiralama Bedeli Hesaplama Sonu ═══")
                    
                    # Kiralama bedeli kalemi olarak fatura detayına ekle
                    rental_detail = {
                        'device_id': device_id,
                        'model': model,
                        'serial_number': serial_number,
                        'description': f"{model} ({serial_number}) - Aylık Kiralama Bedeli",
                        'quantity': quantity_for_rental,
                        'unit_price': rental_fee,
                        'currency': rental_currency,
                        'unit_price_tl': rental_fee_tl,
                        'total_tl': float(rental_billed_tl),
                        'is_rental': True  # Bu kalemin kiralama bedeli olduğunu belirt
                    }
                    invoice_details.append(rental_detail)
                    logger.debug(f"DEBUG: Kiralama bedeli fatura detayına eklendi")

        return invoice_details, grand_total_tl

    def _redirect_to_invoicing_tab(self):
        """Kullanıcıyı Faturalar sekmesine yönlendirir ve verileri yeniler."""
        if not hasattr(self.parent_window, "tabWidget"):
            return

        for i in range(self.parent_window.tabWidget.count()):
            tab_text = self.parent_window.tabWidget.tabText(i)
            if "Faturalar" in tab_text:
                self.parent_window.tabWidget.setCurrentIndex(i)
                # Faturalar sekmesini bul ve yenile
                invoicing_tab = self.parent_window.tabWidget.widget(i)
                if hasattr(invoicing_tab, 'refresh_invoices'):
                    invoicing_tab.refresh_invoices()
                if self.status_bar:
                    self.status_bar.showMessage("Fatura oluşturuldu ve Faturalar sekmesine yönlendirildi.", 5000)
                return

    def _find_row_by_device_id(self, device_id):
        """Verilen cihaz ID'sine göre tablodaki satır indeksini bulur."""
        for row in range(self.meters_table.rowCount()):
            item = self.meters_table.item(row, 0)
            if item and int(item.text()) == device_id:
                return row
        return -1

    def refresh_data(self):
        """Sekme verilerini yeniler."""
        current_customer_id = self.customer_combo.currentData()
        self.load_customers()
        if current_customer_id:
            idx = self.customer_combo.findData(current_customer_id)
            if idx > -1:
                self.customer_combo.setCurrentIndex(idx)
                self.populate_devices_for_customer()
            else:
                self.meters_table.setRowCount(0)
                self.meter_inputs.clear()
        else:
            self.meters_table.setRowCount(0)
            self.meter_inputs.clear()
