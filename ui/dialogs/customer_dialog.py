# ui/dialogs/customer_dialog.py

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QTextEdit,
                             QDialogButtonBox, QMessageBox, QDateEdit, QComboBox, QLabel, QPushButton, QHBoxLayout)
from PyQt6.QtCore import QDate
from utils.database import db_manager

def format_phone_number(phone):
    """Telefon numarasını X(XXX) XXX XX XX formatına çevirir"""
    # Sadece rakamları al
    digits = re.sub(r'\D', '', phone)

    # 11 haneli (0 ile başlayan) telefon numarası kontrolü
    if len(digits) == 11 and digits.startswith('0'):
        return f"{digits[0]}({digits[1:4]}) {digits[4:7]} {digits[7:9]} {digits[9:]}"
    # 10 haneli telefon numarası (0 olmadan)
    elif len(digits) == 10:
        return f"0({digits[0:3]}) {digits[3:6]} {digits[6:8]} {digits[8:]}"
    # Geçersiz uzunluk
    else:
        return phone  # Orijinal formatı döndür

def normalize_email(email):
    """Email adresini küçük harfe çevirir ve Türkçe karakterleri İngilizce karşılıklarıyla değiştirir"""
    if not email:
        return email

    # Küçük harfe çevir
    email = email.lower()

    # Türkçe karakterleri İngilizce karşılıklarıyla değiştir
    turkish_chars = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
    }

    for turkish, english in turkish_chars.items():
        email = email.replace(turkish, english)

    return email

import re

class CustomerDialog(QDialog):
    """Müşteri ekleme/düzenleme dialog'u."""

    def __init__(self, db, customer_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.customer_id = customer_id
        self.is_editing = self.customer_id is not None

        self.setWindowTitle("Müşteri Düzenle" if self.is_editing else "Yeni Müşteri")
        self.resize(450, 650)

        self.init_ui()
        if self.is_editing:
            self.load_customer_data()

    def init_ui(self):
        """UI oluştur."""
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.address_input = QTextEdit()
        self.tax_office_input = QLineEdit()
        self.tax_id_input = QLineEdit()

        # Sözleşme alanları
        self.is_contract_combo = QComboBox()
        self.is_contract_combo.addItems(["Hayır", "Evet"])
        self.contract_start_input = QDateEdit()
        self.contract_end_input = QDateEdit()
        self.contract_period_combo = QComboBox()
        self.contract_period_combo.addItems(["Aylık", "Yıllık"])
        self.contract_price_input = QLineEdit()
        self.contract_price_input.setPlaceholderText("0.00")
        
        self.contract_start_input.setDate(QDate.currentDate())
        self.contract_end_input.setDate(QDate.currentDate().addYears(1))
        self.contract_start_input.setCalendarPopup(True)  # Takvim popup'ı etkinleştir
        self.contract_end_input.setCalendarPopup(True)    # Takvim popup'ı etkinleştir
        self.contract_start_input.setEnabled(False)
        self.contract_end_input.setEnabled(False)
        self.contract_period_combo.setEnabled(False)
        self.contract_price_input.setEnabled(False)

        def toggle_contract_fields():
            enabled = self.is_contract_combo.currentText() == "Evet"
            self.contract_start_input.setEnabled(enabled)
            self.contract_end_input.setEnabled(enabled)
            self.contract_period_combo.setEnabled(enabled)
            self.contract_price_input.setEnabled(enabled)
            if self.is_editing and hasattr(self, "invoice_button"):
                self.invoice_button.setEnabled(enabled)

        self.is_contract_combo.currentTextChanged.connect(toggle_contract_fields)

        layout.addRow("Ad Soyad (*):", self.name_input)
        layout.addRow("Telefon (*):", self.phone_input)
        layout.addRow("E-posta:", self.email_input)

        # Telefon formatlama
        def format_phone_on_change():
            current_text = self.phone_input.text()
            formatted = format_phone_number(current_text)
            if formatted != current_text:
                self.phone_input.setText(formatted)
        self.phone_input.textChanged.connect(format_phone_on_change)

        # Email normalize etme
        def normalize_email_on_change():
            current_text = self.email_input.text()
            normalized = normalize_email(current_text)
            if normalized != current_text:
                self.email_input.setText(normalized)

        self.email_input.textChanged.connect(normalize_email_on_change)
        layout.addRow("Adres:", self.address_input)
        layout.addRow("Vergi Dairesi:", self.tax_office_input)
        layout.addRow("Vergi No:", self.tax_id_input)
        layout.addRow("", QLabel())  # Boşluk
        layout.addRow("Sözleşme Durumu:", self.is_contract_combo)

        contract_dates_layout = QHBoxLayout()
        contract_dates_layout.addWidget(QLabel("Sözleşme Başlangıç:"))
        contract_dates_layout.addWidget(self.contract_start_input)
        contract_dates_layout.addWidget(QLabel("Sözleşme Bitiş:"))
        contract_dates_layout.addWidget(self.contract_end_input)
        layout.addRow(contract_dates_layout)

        period_invoice_layout = QHBoxLayout()
        period_invoice_layout.addWidget(self.contract_period_combo)
        if self.is_editing:
            self.invoice_button = QPushButton("Faturalandır")
            self.invoice_button.clicked.connect(self.create_maintenance_invoice)
            self.invoice_button.setEnabled(self.is_contract_combo.currentText() == "Evet")
            period_invoice_layout.addWidget(self.invoice_button)
        layout.addRow("Sözleşme Şekli:", period_invoice_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(self.buttons)

        self.buttons.accepted.connect(self.save_customer)
        self.buttons.rejected.connect(self.reject)

    def load_customer_data(self):
        """Mevcut müşteri verilerini yükle."""
        try:
            customer = self.db.fetch_one("SELECT name, phone, email, address, tax_office, tax_id, is_contract, contract_start_date, contract_end_date, contract_period, contract_price FROM customers WHERE id = ?", (self.customer_id,))
            if customer:
                self.name_input.setText(customer[0] or "")
                self.phone_input.setText(customer[1] or "")
                self.email_input.setText(customer[2] or "")
                self.address_input.setText(customer[3] or "")
                self.tax_office_input.setText(customer[4] or "")
                self.tax_id_input.setText(customer[5] or "")

                # Sözleşme bilgilerini yükle
                if len(customer) > 6 and customer[6]:
                    self.is_contract_combo.setCurrentText("Evet")
                    if customer[7]:  # contract_start_date
                        start_date = QDate.fromString(customer[7], "yyyy-MM-dd")
                        if start_date.isValid():
                            self.contract_start_input.setDate(start_date)
                    if customer[8]:  # contract_end_date
                        end_date = QDate.fromString(customer[8], "yyyy-MM-dd")
                        if end_date.isValid():
                            self.contract_end_input.setDate(end_date)
                    if customer[9]:  # contract_period
                        self.contract_period_combo.setCurrentText(customer[9])
                    if customer[10]:  # contract_price
                        self.contract_price_input.setText(str(customer[10]))
                    # toggle_contract_fields()  # Bu fonksiyon yok, manuel toggle
                    self.contract_start_input.setEnabled(True)
                    self.contract_end_input.setEnabled(True)
                    self.contract_period_combo.setEnabled(True)
                    self.contract_price_input.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Müşteri verileri yüklenirken hata: {e}")

    def save_customer(self):
        """Müşteri kaydet."""
        # Zorunlu alan kontrolleri
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Uyarı", "Ad Soyad alanı zorunludur!")
            return

        if not self.phone_input.text().strip():
            QMessageBox.warning(self, "Uyarı", "Telefon alanı zorunludur!")
            return

        # Email normalize et (son kontrol)
        normalized_email = normalize_email(self.email_input.text())

        try:
            # Sözleşme tarihleri
            start_date_str = None
            end_date_str = None
            if self.is_contract_combo.currentText() == "Evet":
                start_date_str = self.contract_start_input.date().toString("yyyy-MM-dd")
                end_date_str = self.contract_end_input.date().toString("yyyy-MM-dd")

            # Sözleşme bilgileri
            contract_period = self.contract_period_combo.currentText() if self.is_contract_combo.currentText() == "Evet" else None
            contract_price = float(self.contract_price_input.text() or 0) if self.is_contract_combo.currentText() == "Evet" else 0

            params = (
                self.name_input.text().strip(),
                self.phone_input.text().strip(),
                normalized_email,  # Normalize edilmiş email
                self.address_input.toPlainText().strip(),
                self.tax_office_input.text().strip(),
                self.tax_id_input.text().strip(),
                1 if self.is_contract_combo.currentText() == "Evet" else 0,
                start_date_str,
                end_date_str,
                contract_period,
                contract_price
            )
            if self.is_editing:
                self.db.execute_query("UPDATE customers SET name=?, phone=?, email=?, address=?, tax_office=?, tax_id=?, is_contract=?, contract_start_date=?, contract_end_date=?, contract_period=?, contract_price=? WHERE id=?", params + (self.customer_id,))
            else:
                self.db.execute_query("INSERT INTO customers (name, phone, email, address, tax_office, tax_id, is_contract, contract_start_date, contract_end_date, contract_period, contract_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)

            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Müşteri kaydedilirken bir hata oluştu.\n\nDetay: {e}")

    def create_maintenance_invoice(self):
        """Bakım sözleşmesi faturası oluşturur."""
        try:
            if not self.customer_id:
                QMessageBox.warning(self, "Uyarı", "Müşteri ID bulunamadı!")
                return
                
            # Müşteri bilgilerini al
            customer = self.db.fetch_one("SELECT name, contract_price FROM customers WHERE id = ?", (self.customer_id,))
            if not customer:
                QMessageBox.warning(self, "Uyarı", "Müşteri bulunamadı!")
                return
                
            contract_price = customer[1] or 0
            if contract_price <= 0:
                QMessageBox.warning(self, "Uyarı", "Bakım ücret bedeli girilmemiş!")
                return
                
            # Fatura oluştur
            from datetime import datetime
            invoice_data = {
                'customer_id': self.customer_id,
                'customer_name': customer[0],
                'invoice_date': datetime.now().strftime("%Y-%m-%d"),
                'total_amount': contract_price,
                'currency': 'TRY',
                'description': 'Bakım Sözleşmesi Bedeli',
                'items': [
                    {
                        'description': f'Bakım Sözleşmesi Bedeli - {customer[0]}',
                        'quantity': 1,
                        'unit_price': contract_price,
                        'total_price': contract_price
                    }
                ]
            }
            
            # Fatura tablosuna kaydet
            invoice_id = self.db.execute_query('''
                INSERT INTO invoices (
                    customer_id, invoice_date, total_amount, currency, description, status
                ) VALUES (?, ?, ?, ?, ?, 'Kesildi')
            ''', (
                invoice_data['customer_id'],
                invoice_data['invoice_date'],
                invoice_data['total_amount'],
                invoice_data['currency'],
                invoice_data['description']
            ))
            
            if invoice_id:
                # Fatura kalemlerini kaydet
                for item in invoice_data['items']:
                    self.db.execute_query('''
                        INSERT INTO invoice_items (
                            invoice_id, description, quantity, unit_price, total_price
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        invoice_id,
                        item['description'],
                        item['quantity'],
                        item['unit_price'],
                        item['total_price']
                    ))
                
                QMessageBox.information(self, "Başarılı", 
                    f"Bakım sözleşmesi faturası başarıyla oluşturuldu!\n\n"
                    f"Fatura No: {invoice_id}\n"
                    f"Müşteri: {customer[0]}\n"
                    f"Tutar: {contract_price} TL")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Fatura oluşturulurken hata: {e}")