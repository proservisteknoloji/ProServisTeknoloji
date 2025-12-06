# ui/dialogs/billing_preview_dialog.py (PyQt6'ya güncellendi)

import os
from datetime import datetime
from decimal import Decimal
# Değişiklik: PySide6 -> PyQt6
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from utils.pdf_generator import create_billing_invoice_pdf

class BillingPreviewDialog(QDialog):
    def __init__(self, db, billing_data, customer_name, start_date, end_date, rates, parent=None):
        super().__init__(parent)
        self.db = db
        self.billing_data = billing_data
        self.customer_name = customer_name
        self.start_date = start_date
        self.end_date = end_date
        self.rates = rates # Kurları sakla
        self.setWindowTitle(f"Fatura Önizleme - {self.customer_name}")
        self.setMinimumSize(950, 600)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        self.info_label = QLabel(f"<b>Müşteri:</b> {self.customer_name}<br><b>Fatura Dönemi:</b> {self.start_date} - {self.end_date}")
        self.rates_label = QLabel(f"<b>Kullanılan Kurlar:</b> 1 USD = {self.rates.get('USD', 1.0):.4f} TL | 1 EUR = {self.rates.get('EUR', 1.0):.4f} TL")
        self.rates_label.setStyleSheet("font-size: 9pt; color: #555;")
        header_layout.addWidget(self.info_label)
        header_layout.addStretch()
        header_layout.addWidget(self.rates_label)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Cihaz Modeli", "Seri No", 
            "S/B Tüketim", "S/B Birim Fiyat", "S/B Tutar (TL)",
            "Renkli Tüketim", "Renkli Birim Fiyat", "Renkli Tutar (TL)", 
            "Cihaz Toplam (TL)"
        ])
        # Değişiklik: Enum güncellemeleri
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in [2,3,4,5,6,7,8]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        grand_total_tl = Decimal('0.00')
        for row, data in enumerate(self.billing_data):
            self.table.insertRow(row)
            
            bw_cost_in_tl = Decimal(data['total_bw_cost_tl'])
            color_cost_in_tl = Decimal(data['total_color_cost_tl'])
            device_total_tl = Decimal(data['device_total_tl'])
            grand_total_tl += device_total_tl
            
            # Tabloyu doldur
            self.table.setItem(row, 0, QTableWidgetItem(data['model']))
            self.table.setItem(row, 1, QTableWidgetItem(data['serial_number']))
            
            self.table.setItem(row, 2, QTableWidgetItem(str(data['bw_usage'])))
            self.table.setItem(row, 3, QTableWidgetItem(f"{Decimal(data['cpc_bw_price']):.4f} {data['cpc_bw_currency']}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{bw_cost_in_tl:.2f} TL"))

            self.table.setItem(row, 5, QTableWidgetItem(str(data['color_usage'])))
            self.table.setItem(row, 6, QTableWidgetItem(f"{Decimal(data['cpc_color_price']):.4f} {data['cpc_color_currency']}"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{color_cost_in_tl:.2f} TL"))
            
            total_item = QTableWidgetItem(f"{device_total_tl:.2f} TL")
            # Değişiklik: Enum güncellemeleri
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 8, total_item)

        self.total_label = QLabel(f"Genel Toplam: {grand_total_tl:.2f} TL")
        self.total_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        
        button_layout = QHBoxLayout()
        self.pdf_button = QPushButton("📄 Faturayı PDF Olarak Kaydet")
        button_layout.addStretch()
        button_layout.addWidget(self.pdf_button)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.table)
        # Değişiklik: Enum güncellemeleri
        main_layout.addWidget(self.total_label, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(button_layout)

        self.pdf_button.clicked.connect(self.export_to_pdf)

    def export_to_pdf(self):
        safe_customer_name = "".join(c for c in self.customer_name if c.isalnum() or c in " _-").rstrip()
        file_path, _ = QFileDialog.getSaveFileName(self, "Faturayı Kaydet", f"fatura_{safe_customer_name}_{self.end_date}.pdf", "PDF Dosyaları (*.pdf)")
        if not file_path: return
        
        try:
            data_for_pdf = {
                'billing_data': self.billing_data,
                'customer_name': self.customer_name,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'rates': self.rates,
                'company_info': {
                    'name': self.db.get_setting('company_name', 'Firma Adı Belirtilmemiş'),
                    'phone': self.db.get_setting('company_phone', ''),
                    'email': self.db.get_setting('company_email', ''),
                    'logo_path': self.db.get_setting('company_logo_path')
                }
            }
            create_billing_invoice_pdf(data_for_pdf, file_path)
            QMessageBox.information(self, "Başarılı", f"Fatura başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken bir hata oluştu: {e}")