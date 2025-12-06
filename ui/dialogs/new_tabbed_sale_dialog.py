# ui/dialogs/new_tabbed_sale_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QComboBox, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QSpinBox, QLineEdit, QMessageBox, QWidget, QFormLayout, QHeaderView
)
from PyQt6.QtCore import Qt
from utils.database import db_manager

class SerialListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.serial_inputs = []

    def set_serial_count(self, count):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.serial_inputs.clear()
        for i in range(count):
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"{i + 1}. Seri Numarası")
            self.layout.addWidget(line_edit)
            self.serial_inputs.append(line_edit)

    def get_serials(self):
        return [le.text().strip() for le in self.serial_inputs]

class NewTabbedSaleDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Yeni Satış")
        self.setMinimumSize(900, 600)
        self.sale_data = None
        self._init_ui()
        self._load_customers()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Müşteri seçimi
        self.customer_combo = QComboBox()
        self.customer_combo.setPlaceholderText("Müşteri Seçin...")
        layout.addWidget(QLabel("Müşteri (*):"))
        layout.addWidget(self.customer_combo)
        
        # Fiyat tipi seçimi
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("Fiyat Tipi (*):"))
        self.price_type_combo = QComboBox()
        self.price_type_combo.addItem("Bayi Fiyatı", "dealer")
        self.price_type_combo.addItem("Son Kullanıcı Fiyatı", "end_user")
        self.price_type_combo.setCurrentIndex(0)  # Varsayılan bayi fiyatı
        self.price_type_combo.currentTextChanged.connect(self._on_price_type_changed)
        price_layout.addWidget(self.price_type_combo)
        price_layout.addStretch()
        layout.addLayout(price_layout)
        
        self.tabs = QTabWidget()
        self.device_tab = self._create_device_tab()
        self.toner_tab = self._create_toner_tab()
        self.consumable_tab = self._create_consumable_tab()
        self.tabs.addTab(self.device_tab, "Cihaz Satışı")
        self.tabs.addTab(self.toner_tab, "Toner Satışı")
        self.tabs.addTab(self.consumable_tab, "Diğer Sarf Malzemeler")
        layout.addWidget(self.tabs)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Satışı Tamamla")
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _load_customers(self):
        try:
            customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
            for cust_id, name in customers:
                self.customer_combo.addItem(name, cust_id)
            self.customer_combo.setCurrentIndex(-1)
        except Exception as e:
            QMessageBox.critical(self, "Müşteri Yükleme Hatası", f"Müşteriler yüklenirken bir hata oluştu: {e}")

    def _create_device_tab(self):
        # FIXED: Add parent to prevent memory leak
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        self.device_table = QTableWidget(0, 6)
        self.device_table.setHorizontalHeaderLabels(["Stok ID", "Model", "Adet", "Birim Fiyat", "Para Birimi", "Seri Numaraları"])
        self.device_table.setColumnHidden(0, True)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        add_btn = QPushButton("Cihaz Ekle")
        remove_btn = QPushButton("Seçiliyi Sil")
        add_btn.clicked.connect(self._add_device_row)
        remove_btn.clicked.connect(lambda: self.device_table.removeRow(self.device_table.currentRow()))
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addWidget(self.device_table)
        layout.addLayout(btn_layout)
        return tab

    def _create_toner_tab(self):
        # FIXED: Add parent to prevent memory leak
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        self.toner_table = QTableWidget(0, 5)
        self.toner_table.setHorizontalHeaderLabels(["Stok ID", "Toner", "Adet", "Birim Fiyat", "Para Birimi"])
        self.toner_table.setColumnHidden(0, True)
        self.toner_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        add_btn = QPushButton("Toner Ekle")
        remove_btn = QPushButton("Seçiliyi Sil")
        add_btn.clicked.connect(self._add_toner_row)
        remove_btn.clicked.connect(lambda: self.toner_table.removeRow(self.toner_table.currentRow()))
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addWidget(self.toner_table)
        layout.addLayout(btn_layout)
        return tab

    def _create_consumable_tab(self):
        # FIXED: Add parent to prevent memory leak
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        self.consumable_table = QTableWidget(0, 5)
        self.consumable_table.setHorizontalHeaderLabels(["Stok ID", "Ürün", "Adet", "Birim Fiyat", "Para Birimi"])
        self.consumable_table.setColumnHidden(0, True)
        self.consumable_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        add_btn = QPushButton("Diğer Sarf Malzeme Ekle")
        remove_btn = QPushButton("Seçiliyi Sil")
        add_btn.clicked.connect(self._add_consumable_row)
        remove_btn.clicked.connect(lambda: self.consumable_table.removeRow(self.consumable_table.currentRow()))
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addWidget(self.consumable_table)
        layout.addLayout(btn_layout)
        return tab

    def _add_device_row(self):
        from PyQt6.QtWidgets import QInputDialog
        items = self.db.get_stock_items_for_sale("")
        items = [i for i in items if i['item_type'] == "Cihaz"]
        if not items:
            QMessageBox.warning(self, "Stok Yok", "Satılabilir cihaz bulunamadı.")
            return
        item_names = [f"{i['name']} (Stok: {i['quantity']})" for i in items]
        item_name, ok = QInputDialog.getItem(self, "Cihaz Seç", "Cihaz:", item_names, 0, False)
        if not ok:
            return
        
        selected_index = item_names.index(item_name)
        selected = items[selected_index]

        row = self.device_table.rowCount()
        self.device_table.insertRow(row)
        self.device_table.setItem(row, 0, QTableWidgetItem(str(selected['id'])))
        self.device_table.setItem(row, 1, QTableWidgetItem(selected['name']))
        
        qty_spin = QSpinBox()
        qty_spin.setRange(1, selected['quantity'])
        qty_spin.valueChanged.connect(lambda count, r=row: self._update_serial_widget(r, count))
        self.device_table.setCellWidget(row, 2, qty_spin)
        
        # Fiyat ve para birimi - fiyat tipine göre hesapla
        price_type = self.price_type_combo.currentData()
        sale_price = self._calculate_price_by_type(selected['id'], price_type)
        sale_currency = selected.get('sale_currency', 'TL') or 'TL'
        
        self.device_table.setItem(row, 3, QTableWidgetItem(f"{float(sale_price):.2f}"))
        
        currency_combo = QComboBox()
        currency_combo.addItems(['TL', 'USD', 'EUR'])
        currency_combo.setCurrentText(sale_currency)
        self.device_table.setCellWidget(row, 4, currency_combo)

        self._update_serial_widget(row, 1)

    def _add_toner_row(self):
        from PyQt6.QtWidgets import QInputDialog
        items = self.db.get_stock_items_for_sale("")
        items = [i for i in items if i['item_type'] == "Toner"]
        if not items:
            QMessageBox.warning(self, "Stok Yok", "Satılabilir toner bulunamadı.")
            return
        item_names = [f"{i['name']} (Stok: {i['quantity']})" for i in items]
        item_name, ok = QInputDialog.getItem(self, "Toner Seç", "Toner:", item_names, 0, False)
        if not ok:
            return
        
        selected_index = item_names.index(item_name)
        selected = items[selected_index]

        row = self.toner_table.rowCount()
        self.toner_table.insertRow(row)
        self.toner_table.setItem(row, 0, QTableWidgetItem(str(selected['id'])))
        self.toner_table.setItem(row, 1, QTableWidgetItem(selected['name']))
        
        qty_spin = QSpinBox()
        qty_spin.setRange(1, selected['quantity'])
        self.toner_table.setCellWidget(row, 2, qty_spin)
        
        # Fiyat ve para birimi - fiyat tipine göre hesapla
        price_type = self.price_type_combo.currentData()
        sale_price = self._calculate_price_by_type(selected['id'], price_type)
        sale_currency = selected.get('sale_currency', 'TL') or 'TL'
            
        self.toner_table.setItem(row, 3, QTableWidgetItem(f"{float(sale_price):.2f}"))
        
        currency_combo = QComboBox()
        currency_combo.addItems(['TL', 'USD', 'EUR'])
        currency_combo.setCurrentText(sale_currency)
        self.toner_table.setCellWidget(row, 4, currency_combo)

    def _update_serial_widget(self, row, count):
        serials_widget = SerialListWidget()
        serials_widget.set_serial_count(count)
        self.device_table.setCellWidget(row, 5, serials_widget)
        self.device_table.resizeRowToContents(row)

    def _add_consumable_row(self):
        from PyQt6.QtWidgets import QInputDialog
        items = self.db.get_stock_items_for_sale("")
        items = [i for i in items if i['item_type'] not in ["Cihaz", "Toner"]]
        if not items:
            QMessageBox.warning(self, "Stok Yok", "Satılabilir diğer sarf malzeme bulunamadı.")
            return
        item_names = [f"{i['name']} (Stok: {i['quantity']})" for i in items]
        item_name, ok = QInputDialog.getItem(self, "Diğer Sarf Malzeme Seç", "Ürün:", item_names, 0, False)
        if not ok:
            return
        
        selected_index = item_names.index(item_name)
        selected = items[selected_index]

        row = self.consumable_table.rowCount()
        self.consumable_table.insertRow(row)
        self.consumable_table.setItem(row, 0, QTableWidgetItem(str(selected['id'])))
        self.consumable_table.setItem(row, 1, QTableWidgetItem(selected['name']))
        
        qty_spin = QSpinBox()
        qty_spin.setRange(1, selected['quantity'])
        self.consumable_table.setCellWidget(row, 2, qty_spin)
        
        # Fiyat ve para birimi - fiyat tipine göre hesapla
        price_type = self.price_type_combo.currentData()
        sale_price = self._calculate_price_by_type(selected['id'], price_type)
        sale_currency = selected.get('sale_currency', 'TL') or 'TL'
            
        self.consumable_table.setItem(row, 3, QTableWidgetItem(f"{float(sale_price):.2f}"))
        
        currency_combo = QComboBox()
        currency_combo.addItems(['TL', 'USD', 'EUR'])
        currency_combo.setCurrentText(sale_currency)
        self.consumable_table.setCellWidget(row, 4, currency_combo)

    def accept(self):
        if self._validate_and_collect_data():
            super().accept()

    def _validate_and_collect_data(self):
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir müşteri seçin.")
            return False
        device_items = []
        for row in range(self.device_table.rowCount()):
            try:
                # Boş satırları geç
                if not self.device_table.item(row, 0) or not self.device_table.item(row, 0).text().strip():
                    continue
                    
                item_id = int(self.device_table.item(row, 0).text())
                model = self.device_table.item(row, 1).text()
                qty = self.device_table.cellWidget(row, 2).value()
                unit_price = float(self.device_table.item(row, 3).text())
                currency = self.device_table.cellWidget(row, 4).currentText()
                
                # Cihaz satışında seri numarası kontrolü
                serial_widget = self.device_table.cellWidget(row, 5)
                serials = serial_widget.get_serials() if isinstance(serial_widget, SerialListWidget) else []
                if len(serials) != qty or any(not s for s in serials) or len(set(serials)) != len(serials):
                    QMessageBox.warning(self, "Seri No Hatası", f"'{model}' için {qty} adet benzersiz seri numarası girilmelidir.")
                    return False
                    
                device_items.append({
                    'stock_item_id': item_id,
                    'model': model,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'currency': currency,
                    'serial_numbers': serials
                })
            except Exception as e:
                QMessageBox.critical(self, "Veri Hatası", f"Cihaz satırı okunamadı: {e}")
                return False
        
        # Toner verilerini topla
        toner_items = []
        for row in range(self.toner_table.rowCount()):
            try:
                # Boş satırları geç
                if not self.toner_table.item(row, 0) or not self.toner_table.item(row, 0).text().strip():
                    continue
                    
                item_id = int(self.toner_table.item(row, 0).text())
                name = self.toner_table.item(row, 1).text()
                qty = self.toner_table.cellWidget(row, 2).value()
                unit_price = float(self.toner_table.item(row, 3).text())
                currency = self.toner_table.cellWidget(row, 4).currentText()
                toner_items.append({
                    'stock_item_id': item_id,
                    'name': name,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'currency': currency
                })
            except Exception as e:
                QMessageBox.critical(self, "Veri Hatası", f"Toner satırı okunamadı: {e}")
                return False
        
        consumable_items = []
        for row in range(self.consumable_table.rowCount()):
            try:
                # Boş satırları geç
                if not self.consumable_table.item(row, 0) or not self.consumable_table.item(row, 0).text().strip():
                    continue
                    
                item_id = int(self.consumable_table.item(row, 0).text())
                name = self.consumable_table.item(row, 1).text()
                qty = self.consumable_table.cellWidget(row, 2).value()
                unit_price = float(self.consumable_table.item(row, 3).text())
                currency = self.consumable_table.cellWidget(row, 4).currentText()
                consumable_items.append({
                    'stock_item_id': item_id,
                    'name': name,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'currency': currency
                })
            except Exception as e:
                QMessageBox.critical(self, "Veri Hatası", f"Sarf satırı okunamadı: {e}")
                return False
        if not device_items and not toner_items and not consumable_items:
            QMessageBox.warning(self, "Eksik Bilgi", "En az bir ürün eklemelisiniz.")
            return False

        self.sale_data = {
            'customer_id': customer_id,
            'devices': device_items,
            'toners': toner_items,
            'consumables': consumable_items
        }
        return True

    def get_data(self):
        return self.sale_data

    def _on_price_type_changed(self):
        """Fiyat tipi değiştiğinde tüm fiyatları günceller."""
        self._update_all_prices()

    def _update_all_prices(self):
        """Tablolardaki tüm fiyatları mevcut fiyat tipine göre günceller."""
        price_type = self.price_type_combo.currentData()
        
        # Cihaz tablosundaki fiyatları güncelle
        for row in range(self.device_table.rowCount()):
            stock_id_item = self.device_table.item(row, 0)
            if stock_id_item:
                stock_id = int(stock_id_item.text())
                new_price = self._calculate_price_by_type(stock_id, price_type)
                self.device_table.setItem(row, 3, QTableWidgetItem(f"{new_price:.2f}"))
        
        # Toner tablosundaki fiyatları güncelle
        for row in range(self.toner_table.rowCount()):
            stock_id_item = self.toner_table.item(row, 0)
            if stock_id_item:
                stock_id = int(stock_id_item.text())
                new_price = self._calculate_price_by_type(stock_id, price_type)
                self.toner_table.setItem(row, 3, QTableWidgetItem(f"{new_price:.2f}"))
        
        # Sarf malzeme tablosundaki fiyatları güncelle
        for row in range(self.consumable_table.rowCount()):
            stock_id_item = self.consumable_table.item(row, 0)
            if stock_id_item:
                stock_id = int(stock_id_item.text())
                new_price = self._calculate_price_by_type(stock_id, price_type)
                self.consumable_table.setItem(row, 3, QTableWidgetItem(f"{new_price:.2f}"))

    def _calculate_price_by_type(self, stock_id: int, price_type: str) -> float:
        """
        Stok ID ve fiyat tipine göre fiyat hesaplar.
        
        Args:
            stock_id: Stok kalem ID'si
            price_type: 'dealer' veya 'end_user'
            
        Returns:
            Hesaplanan fiyat
        """
        try:
            # Bayi fiyatını al
            result = self.db.fetch_one(
                "SELECT sale_price FROM stock_items WHERE id = ?", 
                (stock_id,)
            )
            
            if not result:
                return 0.0
                
            dealer_price = float(result[0] or 0.0)
            
            if price_type == "dealer":
                return dealer_price
            elif price_type == "end_user":
                # Son kullanıcı fiyatını hesapla
                return self.db.calculate_end_user_price(stock_id, dealer_price)
            else:
                return dealer_price
                
        except Exception as e:
            print(f"Fiyat hesaplama hatası: {e}")
            return 0.0
