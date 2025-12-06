# ui/dialogs/new_sale_dialog.py

from typing import Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QMessageBox, QDialogButtonBox,
                             QGroupBox, QFormLayout, QSpinBox, QWidget, QTabWidget,
                             QCheckBox, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.database import db_manager


class SerialListWidget(QWidget):
    """Birden fazla seri numarası girişi için dinamik bir widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.serial_inputs = []

    def set_serial_count(self, count):
        """Giriş alanlarının sayısını ayarlar."""
        # Mevcut widget'ları temizle
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.serial_inputs.clear()

        # Yeni widget'ları oluştur
        for i in range(count):
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"{i + 1}. Seri Numarası")
            self.layout.addWidget(line_edit)
            self.serial_inputs.append(line_edit)

    def get_serials(self) -> list[str]:
        """Tüm seri numaralarını bir liste olarak döndürür."""
        return [le.text().strip() for le in self.serial_inputs]


class StockPickerForSaleDialog(QDialog):
    """Satış faturasına eklenecek ürünleri (cihaz veya parça) seçme ekranı - Sekmeli yapı."""
    
    toner_included_changed = pyqtSignal(bool)  # Toner dahil değişikliği sinyali
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_item = None
        self.selected_toners = []  # Cihaz ile birlikte seçilen tonerler
        self.setWindowTitle("Stoktan Ürün Seç")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_all_items()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QVBoxLayout(self)
        self._create_widgets()
        self._create_layout(layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        # Ana tab widget
        self.tab_widget = QTabWidget()
        
        # Cihaz sekmesi
        self.device_tab = QWidget()
        self.device_layout = QVBoxLayout(self.device_tab)
        
        # Cihaz filtreleme
        self.device_filter = QLineEdit()
        self.device_filter.setPlaceholderText("Cihaz adı veya model ile ara...")
        
        # Toner dahil checkbox
        self.toner_included_group = QGroupBox("Satış Seçenekleri")
        toner_group_layout = QVBoxLayout(self.toner_included_group)
        
        self.toner_included_cb = QCheckBox("Toner dahil satış yap")
        self.toner_included_cb.setToolTip("İşaretlendiğinde, cihazın uyumlu tonerleri bedelsiz olarak faturaya eklenir")
        
        self.sehpa_included_cb = QCheckBox("Sehpa dahil satış yap")
        self.sehpa_included_cb.setToolTip("İşaretlendiğinde, cihazın sehpası bedelsiz olarak faturaya eklenir")
        
        toner_group_layout.addWidget(self.toner_included_cb)
        toner_group_layout.addWidget(self.sehpa_included_cb)
        
        # Cihaz tablosu
        self.device_table = QTableWidget(0, 6)
        self.device_table.setHorizontalHeaderLabels(["ID", "Model", "Stok", "Satış Fiyatı", "Renk Tipi", "Açıklama"])
        self.device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.device_table.hideColumn(0)
        
        self.device_layout.addWidget(self.device_filter)
        self.device_layout.addWidget(self.toner_included_group)
        self.device_layout.addWidget(self.device_table)
        
        # Toner sekmesi
        self.toner_tab = QWidget()
        self.toner_layout = QVBoxLayout(self.toner_tab)
        
        # Toner filtreleme
        self.toner_filter = QLineEdit()
        self.toner_filter.setPlaceholderText("Toner adı veya kodu ile ara...")
        
        # Fiyat sıfırlama seçeneği
        self.zero_price_group = QGroupBox("Fiyat Seçenekleri")
        zero_price_layout = QVBoxLayout(self.zero_price_group)
        
        self.zero_toner_price_cb = QCheckBox("Toner fiyatını sıfırla (bedelsiz)")
        self.zero_toner_price_cb.setToolTip("İşaretlendiğinde toner bedelsiz olarak eklenir")
        
        zero_price_layout.addWidget(self.zero_toner_price_cb)
        
        # Toner tablosu
        self.toner_table = QTableWidget(0, 5)
        self.toner_table.setHorizontalHeaderLabels(["ID", "Toner Adı", "Stok", "Satış Fiyatı", "Uyumlu Cihazlar"])
        self.toner_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.toner_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)  # Çoklu seçim
        self.toner_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.toner_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.toner_table.hideColumn(0)
        
        self.toner_layout.addWidget(self.toner_filter)
        self.toner_layout.addWidget(self.zero_price_group)
        self.toner_layout.addWidget(self.toner_table)
        
        # Diğer sarf malzemeler sekmesi
        self.supplies_tab = QWidget()
        self.supplies_layout = QVBoxLayout(self.supplies_tab)
        
        # Sarf malzeme filtreleme
        self.supplies_filter = QLineEdit()
        self.supplies_filter.setPlaceholderText("Sarf malzeme adı ile ara...")
        
        # Fiyat sıfırlama seçeneği (sarf malzemeler için)
        self.zero_supplies_group = QGroupBox("Fiyat Seçenekleri")
        zero_supplies_layout = QVBoxLayout(self.zero_supplies_group)
        
        self.zero_supplies_price_cb = QCheckBox("Fiyatını sıfırla (bedelsiz)")
        self.zero_supplies_price_cb.setToolTip("İşaretlendiğinde sarf malzeme bedelsiz olarak eklenir")
        
        zero_supplies_layout.addWidget(self.zero_supplies_price_cb)
        
        # Sarf malzeme tablosu
        self.supplies_table = QTableWidget(0, 4)
        self.supplies_table.setHorizontalHeaderLabels(["ID", "Malzeme Adı", "Stok", "Satış Fiyatı"])
        self.supplies_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.supplies_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)  # Çoklu seçim
        self.supplies_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.supplies_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.supplies_table.hideColumn(0)
        
        self.supplies_layout.addWidget(self.supplies_filter)
        self.supplies_layout.addWidget(self.zero_supplies_group)
        self.supplies_layout.addWidget(self.supplies_table)
        
        # Sekmeleri ekle
        self.tab_widget.addTab(self.device_tab, "🖨️ Cihazlar")
        self.tab_widget.addTab(self.toner_tab, "🖤 Tonerler")
        self.tab_widget.addTab(self.supplies_tab, "📦 Diğer Sarf Malzemeler")
        
        # Butonlar
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

    def _create_layout(self, layout: QVBoxLayout):
        """Widget'ları layout'a yerleştirir."""
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        # Filter sinyalleri
        self.device_filter.textChanged.connect(self._load_devices)
        self.toner_filter.textChanged.connect(self._load_toners)
        self.supplies_filter.textChanged.connect(self._load_supplies)
        
        # Tablo çift tıklama sinyalleri
        self.device_table.doubleClicked.connect(self.accept)
        self.toner_table.doubleClicked.connect(self.accept)
        self.supplies_table.doubleClicked.connect(self.accept)
        
        # Buton sinyalleri
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        # Toner dahil checkbox sinyali
        self.toner_included_cb.toggled.connect(self.toner_included_changed.emit)

    def _load_all_items(self):
        """Tüm sekmelerdeki verileri yükler."""
        self._load_devices()
        self._load_toners()
        self._load_supplies()

    def _load_devices(self):
        """Cihazları yükler."""
        try:
            filter_text = self.device_filter.text()
            self.device_table.setRowCount(0)
            
            query = """
                SELECT id, name, quantity, sale_price, sale_currency, description, color_type
                FROM stock_items 
                WHERE item_type = 'Cihaz' AND (name LIKE ? OR part_number LIKE ?)
                ORDER BY name
            """
            devices = self.db.fetch_all(query, (f'%{filter_text}%', f'%{filter_text}%'))
            
            for device_id, name, qty, price, currency, desc, color_type in devices:
                if qty > 0:  # Sadece stokta olanları göster
                    row = self.device_table.rowCount()
                    self.device_table.insertRow(row)
                    self.device_table.setItem(row, 0, QTableWidgetItem(str(device_id)))
                    self.device_table.setItem(row, 1, QTableWidgetItem(name))
                    self.device_table.setItem(row, 2, QTableWidgetItem(str(qty)))
                    self.device_table.setItem(row, 3, QTableWidgetItem(f"{price or 0.00:.2f} {currency or 'TL'}"))
                    self.device_table.setItem(row, 4, QTableWidgetItem(color_type or 'N/A'))
                    self.device_table.setItem(row, 5, QTableWidgetItem(desc or ''))
                    
        except Exception as e:
            QMessageBox.critical(self, "Cihaz Yükleme Hatası", f"Cihazlar yüklenirken hata: {e}")

    def _load_toners(self):
        """Tonerleri yükler."""
        try:
            filter_text = self.toner_filter.text()
            self.toner_table.setRowCount(0)
            
            query = """
                SELECT id, name, quantity, sale_price, sale_currency, description
                FROM stock_items 
                WHERE item_type = 'Toner' AND (name LIKE ? OR part_number LIKE ?)
                ORDER BY name
            """
            toners = self.db.fetch_all(query, (f'%{filter_text}%', f'%{filter_text}%'))
            
            for toner_id, name, qty, price, currency, desc in toners:
                if qty > 0:  # Sadece stokta olanları göster
                    row = self.toner_table.rowCount()
                    self.toner_table.insertRow(row)
                    self.toner_table.setItem(row, 0, QTableWidgetItem(str(toner_id)))
                    self.toner_table.setItem(row, 1, QTableWidgetItem(name))
                    self.toner_table.setItem(row, 2, QTableWidgetItem(str(qty)))
                    self.toner_table.setItem(row, 3, QTableWidgetItem(f"{price or 0.00:.2f} {currency or 'TL'}"))
                    self.toner_table.setItem(row, 4, QTableWidgetItem(desc or ''))
                    
        except Exception as e:
            QMessageBox.critical(self, "Toner Yükleme Hatası", f"Tonerler yüklenirken hata: {e}")

    def _load_supplies(self):
        """Diğer sarf malzemeleri yükler."""
        try:
            filter_text = self.supplies_filter.text()
            self.supplies_table.setRowCount(0)
            
            query = """
                SELECT id, name, quantity, sale_price, sale_currency
                FROM stock_items 
                WHERE item_type IN ('Yedek Parça', 'Sarf Malzeme', 'Kağıt', 'Temizlik', 'Diğer') 
                AND (name LIKE ? OR part_number LIKE ?)
                ORDER BY name
            """
            supplies = self.db.fetch_all(query, (f'%{filter_text}%', f'%{filter_text}%'))
            
            for supply_id, name, qty, price, currency in supplies:
                if qty > 0:  # Sadece stokta olanları göster
                    row = self.supplies_table.rowCount()
                    self.supplies_table.insertRow(row)
                    self.supplies_table.setItem(row, 0, QTableWidgetItem(str(supply_id)))
                    self.supplies_table.setItem(row, 1, QTableWidgetItem(name))
                    self.supplies_table.setItem(row, 2, QTableWidgetItem(str(qty)))
                    self.supplies_table.setItem(row, 3, QTableWidgetItem(f"{price or 0.00:.2f} {currency or 'TL'}"))
                    
        except Exception as e:
            QMessageBox.critical(self, "Sarf Malzeme Yükleme Hatası", f"Sarf malzemeler yüklenirken hata: {e}")

    def accept(self):
        """Seçili öğeyi alır ve diyaloğu kabul eder."""
        if self._collect_selected_item():
            super().accept()

    def _collect_selected_item(self) -> bool:
        """Tablodan seçili olan öğenin verilerini toplar."""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # Cihaz sekmesi
            return self._collect_device_selection()
        elif current_tab == 1:  # Toner sekmesi
            return self._collect_toner_selection()
        elif current_tab == 2:  # Diğer sarf malzemeler sekmesi
            return self._collect_supplies_selection()
        else:
            QMessageBox.warning(self, "Hata", "Geçersiz sekme!")
            return False

    def _collect_device_selection(self) -> bool:
        """Cihaz sekmesinden seçimi toplar."""
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen bir cihaz seçin.")
            return False
        
        row = selected_rows[0].row()
        price_text = self.device_table.item(row, 3).text()
        price_parts = price_text.split(' ')
        
        self.selected_item = {
            'id': int(self.device_table.item(row, 0).text()),
            'type': 'Cihaz',
            'name': self.device_table.item(row, 1).text(),
            'stock_qty': int(self.device_table.item(row, 2).text()),
            'unit_price': float(price_parts[0]),
            'currency': price_parts[1] if len(price_parts) > 1 else 'TL',
            'toner_included': self.toner_included_cb.isChecked(),
            'sehpa_included': self.sehpa_included_cb.isChecked()
        }
        
        # Eğer toner dahil seçildiyse, uyumlu tonerleri bul
        if self.toner_included_cb.isChecked():
            self._find_compatible_toners(self.selected_item['id'])
            
        return True

    def _collect_toner_selection(self) -> bool:
        """Toner sekmesinden seçimi toplar - ÇOKLU SEÇİM DESTEĞİ."""
        selected_rows = self.toner_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen en az bir toner seçin.")
            return False
        
        # İlk toneri ana seçim olarak al
        row = selected_rows[0].row()
        price_text = self.toner_table.item(row, 3).text()
        price_parts = price_text.split(' ')
        
        # Fiyat sıfırlama kontrolü
        unit_price = 0.0 if self.zero_toner_price_cb.isChecked() else float(price_parts[0])
        
        self.selected_item = {
            'id': int(self.toner_table.item(row, 0).text()),
            'type': 'Toner',
            'name': self.toner_table.item(row, 1).text(),
            'stock_qty': int(self.toner_table.item(row, 2).text()),
            'unit_price': unit_price,
            'currency': price_parts[1] if len(price_parts) > 1 else 'TL',
            'zero_price': self.zero_toner_price_cb.isChecked(),
            'multiple_selection': []  # Çoklu seçim listesi
        }
        
        # Eğer birden fazla seçim varsa, diğerlerini de ekle
        if len(selected_rows) > 1:
            for i in range(1, len(selected_rows)):
                row = selected_rows[i].row()
                price_text = self.toner_table.item(row, 3).text()
                price_parts = price_text.split(' ')
                unit_price = 0.0 if self.zero_toner_price_cb.isChecked() else float(price_parts[0])
                
                self.selected_item['multiple_selection'].append({
                    'id': int(self.toner_table.item(row, 0).text()),
                    'type': 'Toner',
                    'name': self.toner_table.item(row, 1).text(),
                    'stock_qty': int(self.toner_table.item(row, 2).text()),
                    'unit_price': unit_price,
                    'currency': price_parts[1] if len(price_parts) > 1 else 'TL',
                    'zero_price': self.zero_toner_price_cb.isChecked()
                })
        
        return True

    def _collect_supplies_selection(self) -> bool:
        """Sarf malzeme sekmesinden seçimi toplar - ÇOKLU SEÇİM DESTEĞİ."""
        selected_rows = self.supplies_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen en az bir sarf malzeme seçin.")
            return False
        
        # İlk sarf malzemeyi ana seçim olarak al
        row = selected_rows[0].row()
        price_text = self.supplies_table.item(row, 3).text()
        price_parts = price_text.split(' ')
        
        # Fiyat sıfırlama kontrolü
        unit_price = 0.0 if self.zero_supplies_price_cb.isChecked() else float(price_parts[0])
        
        self.selected_item = {
            'id': int(self.supplies_table.item(row, 0).text()),
            'type': 'Sarf Malzeme',
            'name': self.supplies_table.item(row, 1).text(),
            'stock_qty': int(self.supplies_table.item(row, 2).text()),
            'unit_price': unit_price,
            'currency': price_parts[1] if len(price_parts) > 1 else 'TL',
            'zero_price': self.zero_supplies_price_cb.isChecked(),
            'multiple_selection': []  # Çoklu seçim listesi
        }
        
        # Eğer birden fazla seçim varsa, diğerlerini de ekle
        if len(selected_rows) > 1:
            for i in range(1, len(selected_rows)):
                row = selected_rows[i].row()
                price_text = self.supplies_table.item(row, 3).text()
                price_parts = price_text.split(' ')
                unit_price = 0.0 if self.zero_supplies_price_cb.isChecked() else float(price_parts[0])
                
                self.selected_item['multiple_selection'].append({
                    'id': int(self.supplies_table.item(row, 0).text()),
                    'type': 'Sarf Malzeme',
                    'name': self.supplies_table.item(row, 1).text(),
                    'stock_qty': int(self.supplies_table.item(row, 2).text()),
                    'unit_price': unit_price,
                    'currency': price_parts[1] if len(price_parts) > 1 else 'TL',
                    'zero_price': self.zero_supplies_price_cb.isChecked()
                })
        
        return True

    def _find_compatible_toners(self, device_id: int):
        """Cihaz ile uyumlu tonerleri bulur."""
        try:
            # Cihazın açıklama alanından toner bilgilerini çıkar
            device_query = "SELECT description FROM stock_items WHERE id = ?"
            device_result = self.db.fetch_one(device_query, (device_id,))
            
            if not device_result or not device_result[0]:
                return
                
            description = device_result[0]
            compatible_toners = []
            
            # [TONER_DATA] tagından toner kodlarını çıkar
            if '[TONER_DATA]' in description:
                import json
                try:
                    start_tag = '[TONER_DATA]'
                    end_tag = '[/TONER_DATA]'
                    start_idx = description.find(start_tag) + len(start_tag)
                    end_idx = description.find(end_tag)
                    
                    if start_idx > len(start_tag) - 1 and end_idx > start_idx:
                        toner_json = description[start_idx:end_idx]
                        toner_data = json.loads(toner_json)
                        
                        # Toner kodlarını topla
                        toner_codes = []
                        for key, value in toner_data.items():
                            if value and value.strip():
                                toner_codes.append(value.strip())
                        
                        # Stokta bu toner kodlarına sahip tonerleri bul
                        if toner_codes:
                            placeholders = ','.join(['?' for _ in toner_codes])
                            toner_query = f"""
                                SELECT id, name, quantity, sale_price, sale_currency
                                FROM stock_items 
                                WHERE item_type = 'Toner' 
                                AND quantity > 0
                                AND (name IN ({placeholders}) OR part_number IN ({placeholders}))
                            """
                            params = toner_codes + toner_codes
                            compatible_toners = self.db.fetch_all(toner_query, params)
                            
                except (json.JSONDecodeError, ValueError, IndexError):
                    pass
            
            self.selected_toners = []
            for toner_id, name, qty, price, currency in compatible_toners:
                self.selected_toners.append({
                    'id': toner_id,
                    'name': name,
                    'stock_qty': qty,
                    'unit_price': 0.0,  # Bedelsiz
                    'currency': currency,
                    'zero_price': True
                })
                
        except Exception as e:
            QMessageBox.warning(self, "Toner Arama Hatası", f"Uyumlu tonerler aranırken hata: {e}")

    def get_selected_item(self) -> Optional[dict]:
        """Seçilen öğenin verilerini döndürür."""
        return self.selected_item
        
    def get_selected_toners(self) -> list:
        """Seçilen cihaz ile birlikte gelen tonerleri döndürür."""
        return self.selected_toners

class NewSaleInvoiceDialog(QDialog):
    """Yeni bir satış faturası oluşturma ana penceresi."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.sale_data = None
        self.setWindowTitle("Yeni Satış Faturası")
        self.setMinimumSize(900, 600)
        
        self._init_ui()
        self._load_customers()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        self._create_widgets()
        self._create_layout(main_layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.customer_group = QGroupBox("Müşteri Bilgileri")
        self.customer_combo = QComboBox()
        self.customer_combo.setPlaceholderText("Müşteri Seçin...")
        
        self.items_group = QGroupBox("Fatura Kalemleri")
        self.invoice_items_table = QTableWidget(0, 6)
        self.invoice_items_table.setHorizontalHeaderLabels(["Stok ID", "Açıklama", "Adet", "Birim Fiyat", "Para Birimi", "Seri Numaraları"])
        self.invoice_items_table.setColumnHidden(0, True)
        self.invoice_items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoice_items_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.add_item_btn = QPushButton("Stoktan Ürün Ekle")
        self.remove_item_btn = QPushButton("Seçili Ürünü Sil")
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Faturayı Oluştur")

    def _create_layout(self, main_layout: QVBoxLayout):
        """Widget'ları layout'a yerleştirir."""
        customer_form_layout = QFormLayout(self.customer_group)
        customer_form_layout.addRow("Müşteri (*):", self.customer_combo)
        
        items_layout = QVBoxLayout(self.items_group)
        items_layout.addWidget(self.invoice_items_table)
        
        item_buttons_layout = QHBoxLayout()
        item_buttons_layout.addStretch()
        item_buttons_layout.addWidget(self.add_item_btn)
        item_buttons_layout.addWidget(self.remove_item_btn)
        items_layout.addLayout(item_buttons_layout)
        
        main_layout.addWidget(self.customer_group)
        main_layout.addWidget(self.items_group)
        main_layout.addWidget(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.add_item_btn.clicked.connect(self._add_item_from_stock)
        self.remove_item_btn.clicked.connect(self._remove_selected_item)

    def _load_customers(self):
        """Veritabanından müşterileri yükler."""
        try:
            customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
            for cust_id, name in customers:
                self.customer_combo.addItem(name, cust_id)
            self.customer_combo.setCurrentIndex(-1)
        except Exception as e:
            QMessageBox.critical(self, "Müşteri Yükleme Hatası", f"Müşteriler yüklenirken bir hata oluştu: {e}")
        
    def _add_item_from_stock(self):
        """Stoktan ürün seçme diyalogunu açar ve seçilen ürünü tabloya ekler - ÇOKLU SEÇİM DESTEĞİ."""
        picker = StockPickerForSaleDialog(self.db, self)
        if picker.exec():
            item = picker.get_selected_item()
            if not item:
                return

            # Ana ürünü ekle
            self._add_item_to_invoice(item)
            
            # Çoklu seçim varsa, diğer ürünleri de ekle
            if item.get('multiple_selection'):
                for extra_item in item['multiple_selection']:
                    self._add_item_to_invoice(extra_item)
                
                total_added = len(item['multiple_selection']) + 1
                QMessageBox.information(
                    self, 
                    "Çoklu Ürün Eklendi", 
                    f"Toplam {total_added} adet ürün faturaya eklendi."
                )
            
            # Eğer toner dahil seçildiyse, tonerleri de ekle
            if item.get('toner_included', False):
                toners = picker.get_selected_toners()
                for toner in toners:
                    self._add_item_to_invoice(toner)
                    
                if toners:
                    QMessageBox.information(
                        self, 
                        "Toner Dahil Satış", 
                        f"Cihaz ile birlikte {len(toners)} adet toner bedelsiz olarak faturaya eklendi."
                    )

    def _add_item_to_invoice(self, item: dict):
        """Bir ürünü fatura tablosuna ekler."""
        row = self.invoice_items_table.rowCount()
        self.invoice_items_table.insertRow(row)
        
        self.invoice_items_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
        
        # Bedelsiz ürünler için ismi işaretle
        item_name = item['name']
        if item.get('zero_price', False) or item.get('unit_price', 0) == 0:
            item_name += " (BEDELSİZ)"
            
        self.invoice_items_table.setItem(row, 1, QTableWidgetItem(item_name))
        
        qty_spinbox = QSpinBox()
        qty_spinbox.setRange(1, item['stock_qty'])
        self.invoice_items_table.setCellWidget(row, 2, qty_spinbox)
        
        self.invoice_items_table.setItem(row, 3, QTableWidgetItem(f"{item['unit_price']:.2f}"))
        self.invoice_items_table.setItem(row, 4, QTableWidgetItem(item['currency']))
        
        if item['type'] == 'Cihaz':
            qty_spinbox.valueChanged.connect(lambda count, r=row: self._update_serial_widgets(r, count))
            self._update_serial_widgets(row, 1) # Başlangıçta 1 adet için oluştur
        else:
            item_na = QTableWidgetItem("N/A")
            item_na.setFlags(item_na.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.invoice_items_table.setItem(row, 5, item_na)

    def _update_serial_widgets(self, row, count):
        """Belirtilen satırdaki seri numarası widget'ını günceller."""
        serials_widget = SerialListWidget()
        serials_widget.set_serial_count(count)
        self.invoice_items_table.setCellWidget(row, 5, serials_widget)
        self.invoice_items_table.resizeRowToContents(row)

    def _remove_selected_item(self):
        """Tablodan seçili olan satırı kaldırır."""
        current_row = self.invoice_items_table.currentRow()
        if current_row >= 0:
            self.invoice_items_table.removeRow(current_row)

    def accept(self):
        """Fatura verilerini doğrular ve başarılıysa diyaloğu kabul eder."""
        if self._validate_and_collect_data():
            super().accept()

    def _validate_and_collect_data(self) -> bool:
        """Formdaki tüm verileri doğrular ve `self.sale_data` içine toplar."""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir müşteri seçin.")
            return False

        items = []
        for row in range(self.invoice_items_table.rowCount()):
            try:
                item_id = int(self.invoice_items_table.item(row, 0).text())
                description = self.invoice_items_table.item(row, 1).text()
                quantity = self.invoice_items_table.cellWidget(row, 2).value()
                unit_price = float(self.invoice_items_table.item(row, 3).text())
                currency = self.invoice_items_table.item(row, 4).text()
                
                serial_widget = self.invoice_items_table.cellWidget(row, 5)
                serials = []
                item_type = self.db.get_stock_item_details(item_id).get('item_type')

                if item_type == 'Cihaz':
                    if isinstance(serial_widget, SerialListWidget):
                        serials = serial_widget.get_serials()
                        if len(serials) != quantity:
                            QMessageBox.warning(self, "Eksik Bilgi", f"'{description}' için {quantity} adet seri numarası girmelisiniz.")
                            return False
                        if any(not s for s in serials):
                            QMessageBox.warning(self, "Eksik Bilgi", f"'{description}' için tüm seri numarası alanlarını doldurun.")
                            return False
                        if len(set(serials)) != len(serials):
                            QMessageBox.warning(self, "Hatalı Giriş", f"'{description}' için girilen seri numaraları benzersiz olmalıdır.")
                            return False
                
                items.append({
                    'stock_item_id': item_id,
                    'description': description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'currency': currency,
                    'serial_numbers': serials if item_type == 'Cihaz' else None
                })
            except (AttributeError, ValueError) as e:
                QMessageBox.critical(self, "Veri Hatası", f"{row + 1}. satırdaki veriler okunamadı: {e}")
                return False

        if not items:
            QMessageBox.warning(self, "Eksik Bilgi", "Faturaya en az bir ürün eklemelisiniz.")
            return False
            
        self.sale_data = {'customer_id': customer_id, 'items': items}
        return True

    def get_data(self) -> Optional[dict]:
        """Toplanan satış verilerini döndürür."""
        return self.sale_data
