# ui/dialogs/device_sale_dialog.py

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox, 
                             QDialogButtonBox, QLabel, QMessageBox)
from decimal import Decimal, InvalidOperation
from utils.database import db_manager

class DeviceSaleDialog(QDialog):
    """Stoktan bir cihazın satışını gerçekleştirmek için kullanılan diyalog."""
    
    def __init__(self, db, device_info: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.device_info = device_info
        self.sale_data = None

        self.setWindowTitle("Stoktan Cihaz Satışı")
        self.setMinimumWidth(400)
        
        self._init_ui()
        self._load_customers()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        self._create_widgets()
        self._create_layout(layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        device_name = self.device_info.get('name', 'Bilinmiyor')
        sale_price = self.device_info.get('sale_price', 0.0)
        
        self.device_label = QLabel(f"<b>Satılan Cihaz:</b> {device_name}")
        self.customer_combo = QComboBox()
        self.customer_combo.setPlaceholderText("Müşteri Seçin...")
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Cihazın seri numarasını girin")
        self.sale_price_input = QLineEdit(f"{sale_price:.2f}")
        self.sale_price_input.focusInEvent = lambda event: (self.sale_price_input.selectAll(), super(QLineEdit, self.sale_price_input).focusInEvent(event))[-1]
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Satışı Onayla")

    def _create_layout(self, layout: QFormLayout):
        """Widget'ları layout'a yerleştirir."""
        sale_currency = self.device_info.get('sale_currency', 'TL')
        
        layout.addRow(self.device_label)
        layout.addRow("Müşteri (*):", self.customer_combo)
        layout.addRow("Seri Numarası (*):", self.serial_input)
        layout.addRow(f"Satış Fiyatı ({sale_currency}):", self.sale_price_input)
        layout.addRow(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _load_customers(self):
        """Veritabanından müşterileri yükler ve combobox'a ekler."""
        try:
            customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
            for cust_id, name in customers:
                self.customer_combo.addItem(name, cust_id)
            self.customer_combo.setCurrentIndex(-1)
        except Exception as e:
            QMessageBox.critical(self, "Müşteri Yükleme Hatası", 
                                 f"Müşteriler yüklenirken bir hata oluştu: {e}")

    def accept(self):
        """Satış verilerini doğrular ve başarılıysa diyaloğu kabul eder."""
        if self._validate_and_get_data():
            super().accept()

    def _validate_and_get_data(self) -> bool:
        """Form verilerini doğrular ve `self.sale_data` içine kaydeder."""
        customer_id = self.customer_combo.currentData()
        serial = self.serial_input.text().strip()
        
        if not customer_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir müşteri seçin.")
            return False
        
        if not serial:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen cihazın seri numarasını girin.")
            return False
            
        try:
            price_text = self.sale_price_input.text().replace(',', '.') or '0'
            price = float(Decimal(price_text))
        except InvalidOperation:
            QMessageBox.warning(self, "Geçersiz Fiyat", "Lütfen satış fiyatı için geçerli bir sayı girin.")
            return False
            
        self.sale_data = {
            'customer_id': customer_id,
            'serial_number': serial,
            'sale_price': price,
            'sale_currency': self.device_info.get('sale_currency', 'TL'),
            'stock_id': self.device_info.get('id')
        }
        return True

    def get_data(self) -> Optional[dict]:
        """Doğrulanmış satış verilerini döndürür."""
        return self.sale_data