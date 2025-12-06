# ui/dialogs/new_device_sale_dialog.py

import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialogButtonBox, QSpinBox, QCompleter
)
from PyQt6.QtCore import Qt

# Proje kök dizinini Python yoluna ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.database import db_manager

class NewDeviceSaleDialog(QDialog):
    """
    Yeni bir cihaz satışı oluşturmak için kullanılan dialog.
    Bu dialog, kullanıcıya önce bir müşteri, sonra stoktan bir cihaz seçtirir
    ve ardından satılan adet kadar seri numarası girmesini sağlar.
    """
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Yeni Cihaz Satışı")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.load_customers()
        self.load_stock_items()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)

        # Müşteri Seçimi
        customer_layout = QHBoxLayout()
        customer_layout.addWidget(QLabel("Müşteri:"))
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.customer_combo.lineEdit().setPlaceholderText("Müşteri Seçin...")
        customer_layout.addWidget(self.customer_combo)
        layout.addLayout(customer_layout)

        # Stoktan Cihaz Seçimi
        stock_layout = QHBoxLayout()
        stock_layout.addWidget(QLabel("Stoktan Cihaz Seçin:"))
        self.stock_combo = QComboBox()
        self.stock_combo.lineEdit().setPlaceholderText("Cihaz Seçin...")
        stock_layout.addWidget(self.stock_combo)
        
        stock_layout.addWidget(QLabel("Adet:"))
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.focusInEvent = lambda event: (self.quantity_spinbox.selectAll(), super(QSpinBox, self.quantity_spinbox).focusInEvent(event))[-1]
        self.quantity_spinbox.setMinimum(1)
        self.quantity_spinbox.setMaximum(1) # Başlangıçta 1, stok seçilince güncellenecek
        stock_layout.addWidget(self.quantity_spinbox)

        stock_layout.addWidget(QLabel("Cihaz Tipi:"))
        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems(["Siyah-Beyaz", "Renkli"])
        stock_layout.addWidget(self.device_type_combo)

        layout.addLayout(stock_layout)

        # Seri Numaraları için Tablo
        self.serials_table = QTableWidget()
        self.serials_table.setColumnCount(1)
        self.serials_table.setHorizontalHeaderLabels(["Seri Numarası"])
        self.serials_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.serials_table)

        # Butonlar
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)

        # Sinyaller
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.stock_combo.currentIndexChanged.connect(self.update_quantity_and_serials_table)
        self.quantity_spinbox.valueChanged.connect(self.update_serials_table_rows)

    def load_customers(self):
        """Müşterileri ComboBox'a yükler."""
        try:
            customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
            for cust_id, name in customers:
                self.customer_combo.addItem(name, cust_id)
            self.customer_combo.setCurrentIndex(-1) # Başlangıçta seçim olmasın
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Müşteriler yüklenirken hata: {e}")

    def load_stock_items(self):
        """Stoktaki cihazları ComboBox'a yükler."""
        try:
            # Sadece 'Cihaz' tipindeki ve adedi 0'dan büyük olanları al
            items = self.db.fetch_all_dict("""
                SELECT id, name, part_number, quantity, sale_price 
                FROM stock_items 
                WHERE item_type = 'Cihaz' AND quantity > 0
            """)
            for item in items:
                display_text = f"{item['name']} ({item['part_number']}) - Stok: {item['quantity']}"
                self.stock_combo.addItem(display_text, item)
            self.stock_combo.setCurrentIndex(-1)
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Stoktaki cihazlar yüklenirken hata: {e}")

    def update_quantity_and_serials_table(self):
        """Stok seçimi değiştiğinde adet spinbox'ını ve seri no tablosunu günceller."""
        selected_item_data = self.stock_combo.currentData()
        if not selected_item_data:
            self.quantity_spinbox.setMaximum(1)
            self.quantity_spinbox.setValue(1)
            self.serials_table.setRowCount(0)
            return

        max_quantity = selected_item_data.get('quantity', 1)
        self.quantity_spinbox.setMaximum(max_quantity)
        self.quantity_spinbox.setValue(1)
        self.update_serials_table_rows()

    def update_serials_table_rows(self):
        """Adet değiştiğinde seri numarası tablosunun satır sayısını günceller."""
        quantity = self.quantity_spinbox.value()
        self.serials_table.setRowCount(quantity)

    def accept(self):
        """Satış işlemini gerçekleştirir."""
        customer_id = self.customer_combo.currentData()
        stock_item_data = self.stock_combo.currentData()
        quantity = self.quantity_spinbox.value()
        device_type = self.device_type_combo.currentText()

        if not customer_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir müşteri seçin.")
            return

        if not stock_item_data:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen satılacak bir cihaz seçin.")
            return

        # Seri numaralarını topla
        serials = []
        for i in range(quantity):
            item = self.serials_table.item(i, 0)
            serial = item.text().strip() if item else ""
            if not serial:
                QMessageBox.warning(self, "Eksik Bilgi", f"{i+1}. sıradaki seri numarasını girin.")
                return
            serials.append(serial)
        
        if len(set(serials)) != len(serials):
            QMessageBox.warning(self, "Hatalı Giriş", "Seri numaraları benzersiz olmalıdır.")
            return

        try:
            stock_item_id = stock_item_data['id']
            sale_price = stock_item_data['sale_price']
            
            # Her bir seri numarası için ayrı bir cihaz oluştur
            for serial_number in serials:
                self.db.add_device(
                    customer_id=customer_id,
                    model=f"{stock_item_data['name']} ({stock_item_data['part_number']})",
                    serial_number=serial_number,
                    device_type=device_type,
                    cpc_agreement=0, # Satılan cihazda başlangıçta CPC olmaz
                    installation_date=None # Kurulum tarihi daha sonra servis formuyla belirlenebilir
                )

            # Stoktan düş
            notes = f"{quantity} adet cihaz satışı. Müşteri: {self.customer_combo.currentText()}"
            self.db.add_stock_movement(stock_item_id, 'Çıkış', quantity, notes)
            
            # Satış faturası oluştur
            self.db.create_sale_invoice(
                customer_id=customer_id,
                stock_item_id=stock_item_id,
                quantity=quantity,
                unit_price=sale_price,
                serials=serials,
                stock_item_name=stock_item_data['name']
            )

            QMessageBox.information(self, "Başarılı", f"{quantity} adet cihaz satışı başarıyla kaydedildi.")
            super().accept()

        except ValueError as e:
            QMessageBox.critical(self, "Veri Hatası", str(e))
        except Exception as e:
            QMessageBox.critical(self, "İşlem Hatası", f"Satış kaydedilirken bir hata oluştu: {e}")

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    # Bu kısım sadece test için
    app = QApplication(sys.argv)
    # Gerçek bir db bağlantısı yerine geçici bir mock db gerekebilir
    # db_manager = DatabaseManager('dummy.db') 
    # dialog = NewDeviceSaleDialog(db_manager)
    # dialog.show()
    sys.exit(app.exec())
