# ui/dialogs/bulk_device_sale_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QSpinBox, QLabel,
    QDialogButtonBox, QComboBox, QScrollArea, QWidget,
    QFormLayout, QMessageBox
)
from decimal import Decimal
import sqlite3


class BulkDeviceSaleDialog(QDialog):
    def __init__(self, db, device_info, parent=None):
        super().__init__(parent)
        self.db = db
        self.device_info = device_info
        self.serial_inputs = []
        self.setWindowTitle("Toplu Cihaz Satışı")

        main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.customer_combo = QComboBox()
        self.quantity_spin = QSpinBox()
        self.quantity_spin.focusInEvent = lambda event: (self.quantity_spin.selectAll(), super(QSpinBox, self.quantity_spin).focusInEvent(event))[-1]
        self.sale_price_input = QLineEdit()
        self.sale_price_input.focusInEvent = lambda event: (self.sale_price_input.selectAll(), super(QLineEdit, self.sale_price_input).focusInEvent(event))[-1]

        device_name = self.device_info.get("name", "Bilinmiyor")
        available_qty = self.device_info.get("quantity", 0)
        sale_price = self.device_info.get("sale_price") or 0.0
        self.sale_currency = self.device_info.get("sale_currency", "TL")

        if available_qty > 0:
            self.quantity_spin.setRange(1, available_qty)
        else:
            self.quantity_spin.setRange(0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # FIXED: Add parent to prevent memory leak
        scroll_content = QWidget(self)
        self.serials_layout = QVBoxLayout(scroll_content)
        self.serials_layout.setSpacing(6)  # kutular arasında boşluk
        self.scroll_area.setWidget(scroll_content)

        self.form_layout.addRow(
            QLabel(f"<b>Satılan Cihaz:</b> {device_name} (Stokta: {available_qty})")
        )
        self.form_layout.addRow("Müşteri (*):", self.customer_combo)
        self.form_layout.addRow(
            f"Satış Fiyatı (Birim/{self.sale_currency}):", self.sale_price_input
        )
        self.form_layout.addRow("Satılacak Adet (*):", self.quantity_spin)

        self.sale_price_input.setText(f"{sale_price:.2f}")

        main_layout.addLayout(self.form_layout)
        main_layout.addWidget(QLabel("<b>Seri Numaraları (*):</b>"))
        main_layout.addWidget(self.scroll_area)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Satışı Onayla")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.quantity_spin.valueChanged.connect(self.update_serial_fields)
        self.load_customers()
        self.update_serial_fields()

    def accept(self):
        """Dialog'u kabul etmeden önce veri doğrulaması yapar."""
        data = self.get_data()
        if data is not None:
            # Seri numarası benzersizlik kontrolü
            serials = data['serial_numbers']
            try:
                # Veritabanında bu seri numaralarının kullanılıp kullanılmadığını kontrol et
                placeholders = ','.join(['?' for _ in serials])
                existing_serials = self.db.fetch_all(
                    f"SELECT serial_number FROM devices WHERE serial_number IN ({placeholders})",
                    tuple(serials)
                )
                
                if existing_serials:
                    existing_list = [row['serial_number'] for row in existing_serials]
                    QMessageBox.warning(
                        self, "Seri Numarası Hatası", 
                        f"Aşağıdaki seri numaraları zaten kullanılmış:\n" + "\n".join(existing_list) + 
                        "\n\nLütfen farklı seri numaraları girin."
                    )
                    # Dialog'u açık bırak, kullanıcı düzeltsin
                    return
                    
                # Her şey OK ise parent dialog'u kapat
                super().accept()
                
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Seri numarası kontrolü yapılırken hata oluştu: {e}")
                # Hata durumunda da dialog'u açık bırak
                return
        # Eğer data None ise (validasyon hatası), dialog açık kalır

    def load_customers(self):
        customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
        for cust_id, name in customers:
            self.customer_combo.addItem(name, cust_id)
        self.customer_combo.setCurrentIndex(-1)

    def update_serial_fields(self):
        """Adet değiştikçe seri numarası alanlarını günceller ve pencere boyutunu ayarlar."""
        # Önceki alanları temizle
        for i in reversed(range(self.serials_layout.count())):
            widget = self.serials_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        self.serial_inputs.clear()

        # Yeni adet kadar alan oluştur
        count = self.quantity_spin.value()
        for i in range(count):
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"{i+1}. Cihaz Seri Numarası")
            line_edit.setFixedHeight(32)  # kutuların daha okunaklı olması için
            self.serials_layout.addWidget(line_edit)
            self.serial_inputs.append(line_edit)

        # --- Boyutlandırma ---
        row_height = 38  # her satır için yükseklik (32 + boşluk)
        max_rows = 10

        if count <= max_rows:
            self.scroll_area.setFixedHeight(row_height * count + 8)
        else:
            self.scroll_area.setFixedHeight(row_height * max_rows + 8)

        # pencere minimum genişlik ve auto resize
        self.setMinimumWidth(420)
        self.adjustSize()

    def get_data(self):
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir müşteri seçin.")
            return None

        serials = [le.text().strip() for le in self.serial_inputs]
        if any(not s for s in serials):
            QMessageBox.warning(
                self, "Eksik Bilgi", "Lütfen tüm seri numarası alanlarını doldurun."
            )
            return None

        if len(set(serials)) != len(serials):
            QMessageBox.warning(
                self, "Hatalı Giriş", "Seri numaraları birbirinden farklı olmalıdır."
            )
            return None

        try:
            price = float(
                Decimal(self.sale_price_input.text().replace(",", ".") or 0)
            )
        except Exception:
            QMessageBox.warning(
                self, "Geçersiz Fiyat", "Lütfen satış fiyatı için geçerli bir sayı girin."
            )
            return None

        return {
            "customer_id": customer_id,
            "serial_numbers": serials,
            "sale_price": price,
            "sale_currency": self.sale_currency,
        }
