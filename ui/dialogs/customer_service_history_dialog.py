# ui/dialogs/customer_service_history_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTextEdit, QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from utils.database import db_manager

class CustomerServiceHistoryDialog(QDialog):
    """Müşterinin geçmiş servis kayıtlarını gösteren ve raporlayan diyalog."""
    
    def __init__(self, customer_id: int, db, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.db = db
        self.customer_name = "Bilinmeyen Müşteri"

        self.setWindowTitle("Müşteri Servis Geçmişi Raporu")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_history()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        self._create_widgets()
        self._create_layout(main_layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.header_label = QLabel("Müşteri Servis Geçmişi")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14pt; padding: 5px;")
        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        self.pdf_button = QPushButton("PDF Olarak Kaydet")
        self.print_button = QPushButton("Yazdır")
        self.close_button = QPushButton("Kapat")

    def _create_layout(self, main_layout: QVBoxLayout):
        """Widget'ları layout'a yerleştirir."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.pdf_button)
        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.close_button)
        
        main_layout.addWidget(self.header_label)
        main_layout.addWidget(self.history_display)
        main_layout.addLayout(button_layout)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.pdf_button.clicked.connect(self._export_to_pdf)
        self.print_button.clicked.connect(self._print_history)
        self.close_button.clicked.connect(self.reject)

    def _load_history(self):
        """Veritabanından servis geçmişini yükler ve görüntüler."""
        try:
            customer_info = self.db.fetch_one("SELECT name FROM customers WHERE id = ?", (self.customer_id,))
            if customer_info:
                self.customer_name = customer_info[0]
                self.header_label.setText(f"Rapor: {self.customer_name}")

            history_records = self.db.get_all_services_for_customer(self.customer_id)

            if not history_records:
                self.history_display.setText("Bu müşteri için geçmiş servis kaydı bulunamadı.")
                return

            self._build_html_report(history_records)

        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", 
                                 f"Servis geçmişi yüklenirken bir hata oluştu: {e}")
            self.history_display.setText("Veri yüklenemedi.")

    def _build_html_report(self, records: list):
        """Gelen kayıtlardan bir HTML raporu oluşturur."""
        html_content = ""
        for record in records:
            date = record['created_date'] if 'created_date' in record else 'N/A'
            model = record['device_model'] if 'device_model' in record else 'N/A'
            serial = record['serial_number'] if 'serial_number' in record else 'N/A'
            status = record['status'] if 'status' in record else 'N/A'
            problem = record['problem_description'] if 'problem_description' in record else ''
            notes = record['notes'] if 'notes' in record else ''
            
            problem_text = str(problem or '').replace('\n', "<br>")
            notes_text = str(notes or "<i>Not girilmemiş</i>").replace('\n', "<br>")
            
            html_content += f"""
            <div style="border-bottom: 1px solid #ccc; padding-bottom: 10px; margin-bottom: 10px;">
                <p><b>Tarih:</b> {date} | <b>Cihaz:</b> {model} ({serial}) | <b>Durum:</b> {status}</p>
                <p><b>Bildirilen Arıza:</b><br>{problem_text}</p>
                <p><b>Yapılan İşlemler:</b><br>{notes_text}</p>
            </div>
            """
        self.history_display.setHtml(html_content)
        
    def _export_to_pdf(self):
        """Mevcut raporu bir PDF dosyasına kaydeder."""
        safe_customer_name = "".join(c for c in self.customer_name if c.isalnum() or c in " _-").rstrip()
        default_path = f"servis_dokumu_{safe_customer_name}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Raporu PDF Olarak Kaydet", default_path, 
                                                   "PDF Dosyaları (*.pdf)")
        if not file_path:
            return
            
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            self.history_display.document().print(printer)
            QMessageBox.information(self, "Başarılı", f"Rapor başarıyla '{file_path}' dosyasına kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "PDF Oluşturma Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")

    def _print_history(self):
        """Mevcut raporu bir yazıcıya gönderir."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.history_display.print(printer)