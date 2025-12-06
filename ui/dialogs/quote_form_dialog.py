# ui/dialogs/quote_form_dialog.py

from decimal import Decimal, ROUND_HALF_UP
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
from utils.workers import EmailThread
from utils.email_generator import generate_quote_html
from utils.pdf_generator import create_quote_form_pdf
from .stock_picker_dialog import StockPickerDialog
from utils.currency_converter import get_exchange_rates
from utils.database import db_manager

class QuoteFormDialog(QDialog):
    """Bir servis kaydı için fiyat teklifi oluşturma, düzenleme ve gönderme diyalogu."""
    
    def __init__(self, service_record_id: int, db, status_bar, parent=None):
        super().__init__(parent)
        self.service_id = service_record_id
        self.db = db
        self.status_bar = status_bar
        self.rates = {}
        self.device_model = None
        
        self.setWindowTitle(f"Fiyat Teklif Formu (Servis ID: {self.service_id})")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        self._create_widgets()
        self._create_layout(main_layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.info_label = QLabel("Bilgiler yükleniyor...")
        self.info_label.setStyleSheet("font-weight: bold;")

        self.quote_table = QTableWidget(0, 7)
        self.quote_table.setHorizontalHeaderLabels(["ID", "Açıklama", "Adet", "Birim Fiyat", "Para Birimi", "Toplam Fiyat (TL)", "Stok ID"])
        self.quote_table.setColumnHidden(0, True)
        self.quote_table.setColumnHidden(6, True)
        self.quote_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in [2, 3, 4, 5]:
            self.quote_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.add_item_btn = QPushButton("Yeni Kalem Ekle")
        self.add_from_stock_btn = QPushButton("Stoktan Parça Ekle")
        self.remove_item_btn = QPushButton("Seçili Kalemi Sil")
        
        self.total_price_label = QLabel("Toplam Teklif: 0.00 TL")
        self.total_price_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1E40AF;")

        self.save_btn = QPushButton("Teklifi Kaydet ve Kapat")
        self.pdf_btn = QPushButton("PDF Olarak Aktar")
        self.print_btn = QPushButton("Yazdır")
        self.email_btn = QPushButton("Teklifi E-posta Gönder")

    def _create_layout(self, main_layout: QVBoxLayout):
        """Widget'ları layout'a yerleştirir."""
        item_button_layout = QHBoxLayout()
        item_button_layout.addWidget(self.add_item_btn)
        item_button_layout.addWidget(self.add_from_stock_btn)
        item_button_layout.addWidget(self.remove_item_btn)
        item_button_layout.addStretch()

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.save_btn)
        action_button_layout.addWidget(self.pdf_btn)
        action_button_layout.addWidget(self.print_btn)
        action_button_layout.addWidget(self.email_btn)

        main_layout.addWidget(self.info_label)
        main_layout.addWidget(self.quote_table)
        main_layout.addLayout(item_button_layout)
        main_layout.addWidget(self.total_price_label, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(action_button_layout)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.quote_table.cellChanged.connect(self._update_line_total)
        self.add_item_btn.clicked.connect(self._add_item)
        self.add_from_stock_btn.clicked.connect(self._open_stock_picker)
        self.remove_item_btn.clicked.connect(self._remove_item)
        self.save_btn.clicked.connect(self.save_and_close)
        self.pdf_btn.clicked.connect(self._export_to_pdf)
        self.print_btn.clicked.connect(self._print_quote)
        self.email_btn.clicked.connect(self._send_quote_email)

    def _load_data(self):
        """Gerekli verileri (kurlar, servis bilgisi, teklif kalemleri) yükler."""
        try:
            self.rates = get_exchange_rates()
            info = self.db.fetch_one(
                "SELECT c.name, cd.device_model, cd.serial_number FROM service_records sr "
                "JOIN customer_devices cd ON sr.device_id = cd.id "
                "JOIN customers c ON cd.customer_id = c.id WHERE sr.id = ?", (self.service_id,)
            )
            if info:
                self.device_model = info['device_model']
                self.info_label.setText(f"Müşteri: {info['name']}  |  Cihaz: {self.device_model} ({info['serial_number']})")

            self.quote_table.setRowCount(0)
            items = self.db.get_quote_items(self.service_id)
            for item in items:
                self._add_row_to_table(
                    desc=item.get('description'),
                    qty=item.get('quantity'),
                    price=item.get('unit_price'),
                    item_id=item.get('id'),
                    stock_item_id=item.get('stock_item_id'),
                    currency=item.get('currency')
                )
            self._update_grand_total()
        except Exception as e:
            QMessageBox.critical(self, "Veri Yükleme Hatası", f"Teklif verileri yüklenirken bir hata oluştu: {e}")

    def _add_row_to_table(self, desc="", qty=1.0, price=0.0, item_id=None, stock_item_id=None, currency='TL'):
        """Tabloya yeni bir satır ekler ve verileri doldurur."""
        row_pos = self.quote_table.rowCount()
        self.quote_table.insertRow(row_pos)
        self.quote_table.setItem(row_pos, 0, QTableWidgetItem(str(item_id or '')))
        self.quote_table.setItem(row_pos, 1, QTableWidgetItem(desc))
        self.quote_table.setItem(row_pos, 2, QTableWidgetItem(str(qty)))
        self.quote_table.setItem(row_pos, 3, QTableWidgetItem(f"{Decimal(price):.2f}"))
        self.quote_table.setItem(row_pos, 4, QTableWidgetItem(currency))
        
        total_tl_item = QTableWidgetItem()
        total_tl_item.setFlags(total_tl_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.quote_table.setItem(row_pos, 5, total_tl_item)
        self.quote_table.setItem(row_pos, 6, QTableWidgetItem(str(stock_item_id or '')))
        
        self._update_line_total(row_pos, 2) # Trigger calculation

    def _open_stock_picker(self):
        """Stoktan parça seçme diyalogunu açar."""
        dialog = StockPickerDialog(self.db, self.device_model, parent=self)
        if dialog.exec():
            part = dialog.get_selected_part()
            if part:
                self._add_row_to_table(
                    desc=part['name'],
                    qty=part['quantity'],
                    price=part['unit_price'],
                    stock_item_id=part['id'],
                    currency=part.get('currency', 'TL')
                )

    def _update_line_total(self, row, column):
        """Bir satırın toplam TL tutarını günceller."""
        if column not in [2, 3, 4]: return
        try:
            qty = Decimal(self.quote_table.item(row, 2).text().replace(',', '.'))
            price = Decimal(self.quote_table.item(row, 3).text().replace(',', '.'))
            currency = self.quote_table.item(row, 4).text()

            line_total = qty * price
            rate = Decimal(str(self.rates.get(currency, 1.0)))
            total_tl = (line_total * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            self.quote_table.item(row, 5).setText(f"{total_tl:.2f}")
            self._update_grand_total()
        except (AttributeError, TypeError, ValueError):
            pass # Handle cases where items are not yet fully populated

    def _update_grand_total(self):
        """Genel toplamı hesaplar ve etiketi günceller."""
        grand_total = sum(Decimal(self.quote_table.item(row, 5).text() or 0) for row in range(self.quote_table.rowCount()))
        self.total_price_label.setText(f"Genel Toplam: {grand_total:.2f} TL")

    def _save_quote(self) -> bool:
        """Teklif kalemlerini veritabanına kaydeder."""
        items = []
        for row in range(self.quote_table.rowCount()):
            try:
                stock_id_text = self.quote_table.item(row, 6).text()
                stock_id = int(stock_id_text) if stock_id_text and stock_id_text.lower() != 'none' else None
                desc = self.quote_table.item(row, 1).text()
                qty = float(Decimal(self.quote_table.item(row, 2).text().replace(',', '.')))
                price = float(Decimal(self.quote_table.item(row, 3).text().replace(',', '.')))
                currency = self.quote_table.item(row, 4).text()
                
                if not desc:
                    QMessageBox.warning(self, "Eksik Bilgi", f"{row + 1}. satırda açıklama boş olamaz.")
                    return False
                items.append({
                    'description': desc, 'quantity': qty, 'unit_price': price,
                    'stock_item_id': stock_id, 'currency': currency
                })
            except (AttributeError, ValueError) as e:
                QMessageBox.warning(self, "Geçersiz Değer", f"{row + 1}. satırda geçersiz bir sayısal değer var: {e}")
                return False
        
        try:
            self.db.save_quote_items(self.service_id, items)
            self.status_bar.showMessage("Fiyat teklifi kaydedildi.", 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Kayıt Hatası", f"Teklif kaydedilirken bir hata oluştu: {e}")
            return False

    def _add_item(self):
        self._add_row_to_table()

    def _remove_item(self):
        current_row = self.quote_table.currentRow()
        if current_row >= 0:
            self.quote_table.removeRow(current_row)
            self._update_grand_total()

    def save_and_close(self):
        if self._save_quote():
            self.accept()

    def _send_quote_email(self):
        """Teklifi e-posta olarak gönderir."""
        reply = QMessageBox.question(self, "Onay", "E-posta göndermeden önce mevcut teklifi kaydetmek ister misiniz?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.No: return
        if not self._save_quote(): return

        try:
            full_data = self.db.get_full_service_form_data(self.service_id)
            if not full_data:
                QMessageBox.critical(self, "Hata", "Teklif verileri alınamadı.")
                return

            customer_email = full_data['main_info'].get('customer_email')
            if not customer_email:
                QMessageBox.warning(self, "E-posta Adresi Yok", "Müşterinin kayıtlı bir e-posta adresi yok.")
                return

            smtp_settings = self.db.get_all_smtp_settings()
            # Zorunlu alanları kontrol et: host, port, user
            required_fields = ['smtp_host', 'smtp_port', 'smtp_user']
            missing_fields = [field for field in required_fields if not smtp_settings.get(field)]
            if missing_fields:
                QMessageBox.critical(self, "SMTP Ayarları Eksik", "Lütfen Ayarlar menüsünden SMTP bilgilerini eksiksiz doldurun.")
                return

            # SMTP ayarlarını EmailThread formatına dönüştür
            email_smtp_settings = {
                'host': smtp_settings['smtp_host'],
                'port': smtp_settings['smtp_port'],
                'user': smtp_settings['smtp_user'],
                'password': smtp_settings['smtp_password'],
                'encryption': smtp_settings['smtp_encryption']
            }

            html_body = generate_quote_html(full_data)
            subject = f"{full_data['company_info']['company_name']} - Fiyat Teklifi (Servis No: {self.service_id})"

            # PDF oluştur (ReportLab ile - PDF Aktar ile aynı format)
            import tempfile
            import os
            from utils.pdf_generator import create_quote_form_pdf

            # Geçici PDF dosyası oluştur
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_pdf_path = temp_file.name

            # PDF'i ReportLab ile oluştur (PDF Aktar ile aynı)
            if not create_quote_form_pdf(full_data, temp_pdf_path):
                QMessageBox.critical(self, "Hata", "PDF eki oluşturulamadı.")
                return

            # PDF verisini oku
            with open(temp_pdf_path, 'rb') as f:
                pdf_data = f.read()

            # Geçici dosyayı sil
            os.unlink(temp_pdf_path)

            # Müşteri adını al ve dosya adı oluştur
            customer_name = full_data.get('main_info', {}).get('customer_name', 'Musteri')
            import re
            customer_name_clean = re.sub(r'[^\w\s-]', '', customer_name).strip().replace(' ', '_')
            pdf_filename = f"{customer_name_clean}_teklif_{self.service_id}.pdf"

            attachments = [{
                'filename': pdf_filename,
                'data': pdf_data,
                'content_type': 'application/pdf'
            }]

            message_details = {
                'recipient': customer_email,
                'subject': subject,
                'body': html_body,
                'sender_name': full_data['company_info']['company_name'],
                'attachments': attachments
            }

            self.status_bar.showMessage(f"Teklif e-postası ve PDF eki {customer_email} adresine gönderiliyor...", 5000)
            self.email_thread = EmailThread(email_smtp_settings, message_details)
            self.email_thread.task_finished.connect(lambda msg: QMessageBox.information(self, "Başarılı", msg))
            self.email_thread.task_error.connect(lambda err: QMessageBox.critical(self, "E-posta Hatası", err))
            self.email_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "E-posta Gönderme Hatası", f"Beklenmedik bir hata oluştu: {e}")

    def _export_to_pdf(self):
        """Teklifi PDF olarak dışa aktarır (email ile aynı format)."""
        if not self._save_quote(): return

        try:
            full_data = self.db.get_full_service_form_data(self.service_id)
            if not full_data:
                QMessageBox.critical(self, "Hata", "PDF için teklif verileri alınamadı.")
                return

            # Müşteri adını al ve dosya adı oluştur
            customer_name = full_data.get('main_info', {}).get('customer_name', 'Musteri')
            # Özel karakterleri temizle
            import re
            customer_name_clean = re.sub(r'[^\w\s-]', '', customer_name).strip().replace(' ', '_')

            # Masaüstünde 'Müşteri Teklifleri' klasörü
            import os
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            teklif_dir = os.path.join(desktop_path, "Müşteri Teklifleri")
            if not os.path.exists(teklif_dir):
                os.makedirs(teklif_dir)

            # Dosya adını oluştur
            file_name = f"{customer_name_clean}_teklif_{self.service_id}.pdf"
            file_path = os.path.join(teklif_dir, file_name)

            from utils.pdf_generator import create_quote_form_pdf
            if create_quote_form_pdf(full_data, file_path):
                QMessageBox.information(self, "Başarılı", f"Teklif PDF kaydedildi:\n{file_path}")
                # PDF'i otomatik aç
                os.startfile(file_path)
            else:
                QMessageBox.critical(self, "PDF Oluşturma Hatası", "PDF oluşturulurken bir hata oluştu.")
        except Exception as e:
            QMessageBox.critical(self, "PDF Oluşturma Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")

    def _print_quote(self):
        """Teklifi doğrudan yazıcıya gönderir - yazıcı seçim dialogu ile."""
        try:
            # Önce teklifi kaydet
            if not self._save_quote(): 
                return
                
            full_data = self.db.get_full_service_form_data(self.service_id)
            if not full_data:
                QMessageBox.critical(self, "Hata", "Yazdırma için teklif verileri alınamadı.")
                return
            
            import tempfile
            import os
            from utils.pdf_generator import create_quote_form_pdf
            
            # Geçici PDF dosyası oluştur
            temp_dir = tempfile.gettempdir()
            temp_pdf_path = os.path.join(temp_dir, f"teklif_yazdir_{self.service_id}.pdf")
            
            # PDF'i oluştur
            if not create_quote_form_pdf(full_data, temp_pdf_path):
                QMessageBox.critical(self, "Hata", "PDF oluşturulamadı.")
                return
            
            # Yazıcı seçim dialogu
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QPixmap, QPainter, QPageSize
            from PyQt6.QtCore import Qt
            import fitz  # PyMuPDF
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            
            dialog = QPrintDialog(printer, self)
            dialog.setWindowTitle("Yazıcı Seç")
            
            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                # PDF'i PyMuPDF ile aç ve yazdır
                doc = fitz.open(temp_pdf_path)
                painter = QPainter()
                painter.begin(printer)
                
                for page_num in range(len(doc)):
                    if page_num > 0:
                        printer.newPage()
                    
                    page = doc[page_num]
                    # Yüksek çözünürlüklü render
                    zoom = 3.0  # 300 DPI için
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # QPixmap'e dönüştür
                    img_data = pix.tobytes("ppm")
                    qpixmap = QPixmap()
                    qpixmap.loadFromData(img_data)
                    
                    # Sayfaya sığdır
                    page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
                    scaled_pixmap = qpixmap.scaled(
                        int(page_rect.width()), 
                        int(page_rect.height()),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    # Ortala ve çiz
                    x = int((page_rect.width() - scaled_pixmap.width()) / 2)
                    y = int((page_rect.height() - scaled_pixmap.height()) / 2)
                    painter.drawPixmap(x, y, scaled_pixmap)
                
                painter.end()
                doc.close()
                
                QMessageBox.information(self, "Başarılı", "Teklif yazıcıya gönderildi.")
            
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_pdf_path)
            except:
                pass
                
        except ImportError:
            # PyMuPDF yoksa alternatif yöntem
            QMessageBox.warning(self, "Uyarı", "Doğrudan yazdırma için PyMuPDF gerekli.\n'pip install pymupdf' komutu ile yükleyin.")
        except Exception as e:
            QMessageBox.critical(self, "Yazdırma Hatası", f"Yazdırma işlemi sırasında bir hata oluştu: {e}")
