# ui/dialogs/payment_dialog.py

from typing import Optional
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QLabel, QDateEdit, QMessageBox
)
from PyQt6.QtCore import QDate
from decimal import Decimal, InvalidOperation
import re
from utils.database import db_manager

class PaymentDialog(QDialog):
    """Bir fatura için ödeme girişi yapılmasını sağlayan diyalog."""
    
    def __init__(self, invoice_info: dict, parent=None):
        super().__init__(parent)
        self.invoice_info = invoice_info
        self.payment_data = None
        self.db = db_manager
        
        self.setWindowTitle(f"Fatura No {self.invoice_info.get('id', 'Bilinmeyen')} için Ödeme Girişi")
        self.setMinimumWidth(400)

        self._init_ui()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        self._create_widgets()
        self._create_layout(layout)
        self._connect_signals()

    def _safe_float(self, value, default=0.0) -> float:
        """Metin veya sayı girişlerini güvenli şekilde floata çevirir."""
        if isinstance(value, (float, int)):
            return float(value)
        if isinstance(value, str):
            # Para birimi simgeleri ve binlik ayraçları gibi metinleri temizle
            cleaned_value = re.sub(r"[^\d,.-]", "", value).replace(",", ".")
            try:
                return float(cleaned_value)
            except (ValueError, TypeError):
                return default
        return default

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        total = self._safe_float(self.invoice_info.get("total_amount"))
        paid = self._safe_float(self.invoice_info.get("paid_amount"))
        balance = total - paid
        currency = self.invoice_info.get('currency', 'TL')

        self.total_label = QLabel(f"<b>Fatura Tutarı:</b> {total:.2f} {currency}")
        self.balance_label = QLabel(f"<b>Kalan Bakiye:</b> {balance:.2f} {currency}")
        
        self.amount_input = QLineEdit(f"{balance:.2f}")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Nakit", "Kredi Kartı", "Havale/EFT", "Diğer"])
        self.notes_input = QLineEdit()
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Ödemeyi Kaydet")

    def _create_layout(self, layout: QFormLayout):
        """Widget'ları layout'a yerleştirir."""
        layout.addRow(self.total_label)
        layout.addRow(self.balance_label)
        layout.addRow("Ödeme Miktarı (*):", self.amount_input)
        layout.addRow("Ödeme Tarihi (*):", self.date_edit)
        layout.addRow("Ödeme Yöntemi:", self.method_combo)
        layout.addRow("Not:", self.notes_input)
        layout.addRow(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def accept(self):
        """Ödeme verilerini doğrular ve başarılıysa diyaloğu kabul eder."""
        if self._validate_and_collect_data():
            super().accept()

    def _validate_and_collect_data(self) -> bool:
        """Form verilerini doğrular ve `self.payment_data` içine kaydeder."""
        try:
            amount_text = self.amount_input.text().replace(",", ".") or '0'
            amount = float(Decimal(amount_text))
            if amount <= 0:
                QMessageBox.warning(self, "Hatalı Giriş", "Ödeme miktarı sıfırdan büyük olmalıdır.")
                return False
        except InvalidOperation:
            QMessageBox.warning(self, "Hatalı Giriş", "Geçerli bir ödeme miktarı giriniz.")
            return False

        self.payment_data = {
            "amount_paid": amount,
            "payment_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "payment_method": self.method_combo.currentText(),
            "notes": self.notes_input.text().strip(),
        }
        return True

    def get_data(self) -> Optional[dict]:
        """Toplanan ödeme verilerini döndürür."""
        return self.payment_data
