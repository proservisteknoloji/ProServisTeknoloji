# ui/dialogs/invoice_preview_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFormLayout, QLabel, QMessageBox,
                             QDialogButtonBox, QDoubleSpinBox)
from PyQt6.QtCore import Qt
from decimal import Decimal, ROUND_HALF_UP
import json
from utils.database import db_manager
from typing import Optional

class InvoicePreviewDialog(QDialog):
    """Fatura önizlemesi, KDV ayarı ve onaylama işlemlerini yöneten diyalog."""
    
    def __init__(self, db, customer_info: dict, items_to_invoice: list, parent=None):
        super().__init__(parent)
        self.db = db
        self.customer_info = customer_info
        self.items_to_invoice = items_to_invoice
        self.invoice_data = None

        self.setWindowTitle("Fatura Önizleme ve Oluşturma")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._populate_table()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        self._create_widgets()
        self._create_layout(main_layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.customer_label = QLabel(f"<b>Müşteri:</b> {self.customer_info['name']}")
        
        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["Açıklama", "Adet", "Birim Fiyat", "Tutar"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.subtotal_label = QLabel("0.00 TL")
        self.vat_spinbox = QDoubleSpinBox()
        self.vat_spinbox.focusInEvent = lambda event: (self.vat_spinbox.selectAll(), super(QDoubleSpinBox, self.vat_spinbox).focusInEvent(event))[-1]
        self.vat_spinbox.setSuffix(" %")
        self.vat_spinbox.setRange(0.0, 100.0)
        self.vat_spinbox.setDecimals(2)
        try:
            self.vat_spinbox.setValue(float(self.db.get_setting('vat_rate', '20.0')))
        except (ValueError, TypeError):
            self.vat_spinbox.setValue(20.0)
            
        self.vat_amount_label = QLabel("0.00 TL")
        self.grand_total_label = QLabel("0.00 TL")
        self.grand_total_label.setStyleSheet("font-weight: bold; font-size: 14pt;")

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Faturayı Onayla ve Oluştur")

    def _create_layout(self, main_layout: QVBoxLayout):
        """Widget'ları layout'a yerleştirir."""
        totals_layout = QFormLayout()
        totals_layout.addRow("Ara Toplam:", self.subtotal_label)
        totals_layout.addRow("KDV Oranı:", self.vat_spinbox)
        totals_layout.addRow("KDV Tutarı:", self.vat_amount_label)
        totals_layout.addRow("Genel Toplam:", self.grand_total_label)

        main_layout.addWidget(self.customer_label)
        main_layout.addWidget(self.items_table)
        main_layout.addLayout(totals_layout)
        main_layout.addWidget(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.vat_spinbox.valueChanged.connect(self._calculate_totals)

    def _populate_table(self):
        """Fatura edilecek kalemleri tabloya doldurur."""
        for item in self.items_to_invoice:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            
            # Veri tipine göre açıklama, miktar ve fiyat bilgilerini al
            if item['type'] == 'service':
                service_data = item['data']
                desc = f"Servis: {service_data['model']} - {service_data['notes'][:50] if service_data['notes'] else 'Not yok'}"
                qty = 1
                price = Decimal(str(service_data.get('total_amount', '0.0')))
                currency = 'TL'
            elif item['type'] == 'cpc':
                cpc_data = item['data']
                desc = f"CPC: {cpc_data['model']} ({cpc_data['serial_number']}) - Sayaç Okuma"
                qty = 1  # CPC için miktar her zaman 1
                price = Decimal(str(cpc_data.get('total_amount_tl', '0.0')))
                currency = 'TL'
            else:
                # Varsayılan (eski format) - geri uyumluluk için
                desc = item.get('description', 'Açıklama yok')
                qty = item.get('quantity', 1)
                price = Decimal(str(item.get('unit_price', '0.0')))
                currency = item.get('currency', 'TL')
            
            total = Decimal(qty) * price
            
            self.items_table.setItem(row, 0, QTableWidgetItem(desc))
            self.items_table.setItem(row, 1, QTableWidgetItem(str(qty)))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"{price:.2f} {currency}"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"{total:.2f} {currency}"))
        
        self._calculate_totals()

    def _calculate_totals(self):
        """Tablodaki kalemlere göre ara toplam, KDV ve genel toplamı hesaplar."""
        subtotal = Decimal('0.00')
        for row in range(self.items_table.rowCount()):
            try:
                total_text = self.items_table.item(row, 3).text().split(' ')[0]
                subtotal += Decimal(total_text)
            except (AttributeError, IndexError):
                continue # Boş veya hatalı satırları atla
            
        vat_rate = Decimal(str(self.vat_spinbox.value()))
        vat_amount = (subtotal * (vat_rate / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        grand_total = subtotal + vat_amount
        
        self.subtotal_label.setText(f"{subtotal:.2f} TL")
        self.vat_amount_label.setText(f"{vat_amount:.2f} TL")
        self.grand_total_label.setText(f"{grand_total:.2f} TL")

    def accept(self):
        """Fatura verilerini toplar ve diyaloğu kabul eder."""
        self._collect_invoice_data()
        super().accept()

    def _collect_invoice_data(self):
        """Onay sonrası veritabanına gönderilecek veriyi toplar."""
        try:
            grand_total_str = self.grand_total_label.text().split(' ')[0]
            total_amount = float(Decimal(grand_total_str))
        except (IndexError, ValueError):
            total_amount = 0.0

        # Firma bilgilerini ayarlardan çek
        company_info = {
            'name': self.db.get_setting('company_name', 'Firma Adı'),
            'address': self.db.get_setting('company_address', 'Adres Bilgisi Yok'),
            'phone': self.db.get_setting('company_phone', 'Telefon Bilgisi Yok'),
            'tax_office': self.db.get_setting('company_tax_office', ''),
            'tax_id': self.db.get_setting('company_tax_id', ''),
            'email': self.db.get_setting('company_email', ''),
            'bank_name': self.db.get_setting('company_bank_name', ''),
            'bank_account_holder': self.db.get_setting('company_bank_account_holder', ''),
            'bank_iban': self.db.get_setting('company_bank_iban', ''),
            'logo_path': self.db.get_setting('company_logo_path', ''),
        }
        # Müşteri bilgileri
        customer_info = {
            'name': self.customer_info.get('name', ''),
            'address': self.customer_info.get('address', ''),
            'phone': self.customer_info.get('phone', ''),
            'tax_id': self.customer_info.get('tax_id', ''),
        }
        self.invoice_data = {
            'customer_id': self.customer_info['id'],
            'total_amount': total_amount,
            'currency': 'TL', # Varsayılan para birimi
            'vat_rate': self.vat_spinbox.value(),
            'details_json': json.dumps(self.items_to_invoice, ensure_ascii=False),
            'original_items': self.items_to_invoice,
            'company_info': company_info,
            'customer_info': customer_info
        }

    def get_invoice_data(self) -> Optional[dict]:
        """Toplanan fatura verilerini döndürür."""
        return self.invoice_data
