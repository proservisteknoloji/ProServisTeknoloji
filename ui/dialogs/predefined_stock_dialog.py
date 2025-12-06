# ui/dialogs/predefined_stock_dialog.py

"""
Hazır stok seçenekleri dialog'u.
Kullanıcıya farklı stok ekleme seçenekleri sunar.
"""

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGroupBox, QMessageBox, QListWidget, 
                             QListWidgetItem, QComboBox, QLineEdit, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QTextEdit, QSplitter,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from PyQt6.QtGui import QFont, QIcon

# Import Kyocera compatibility system
from utils.kyocera_compatibility_scraper import (
    find_compatible_toners_for_device,
    get_stock_compatible_toners,
    suggest_missing_toners_for_device,
    create_missing_toner_stock_card,
    normalize_device_name
)

class PredefinedStockDialog(QDialog):
    """Hazır stok seçenekleri dialog'u."""
    
    stock_added = Signal()
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("📋 Hazır Stok Yönetimi")
        self.setMinimumSize(900, 650)
        self.resize(1200, 800)
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)
        
        # Başlık
        title_label = QLabel("📋 Hazır Stok Yönetimi")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2E3440; margin: 5px;")
        layout.addWidget(title_label)
        
        # Ana seçenekler - kompakt
        options_group = QGroupBox("Seçenekler")
        options_layout = QHBoxLayout(options_group)  # Yatay layout
        options_group.setMaximumHeight(80)  # Yükseklik sınırla
        
        # Seçenek 1: Mevcut hazır stokları ekle
        self.predefined_btn = QPushButton("🔄 Önceden\nTanımlanmış")
        self.predefined_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 8px;
                text-align: center;
                min-width: 80px;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # Seçenek 2: Cihaz-toner eşleştirmesi (Kyocera Otomatik)
        self.device_toner_btn = QPushButton("🔧 Kyocera\nUyumluluk")
        self.device_toner_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 8px;
                text-align: center;
                min-width: 80px;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        # Seçenek 3: Manuel toner tanımla
        self.manual_toner_btn = QPushButton("✏️ Manuel\nToner")
        self.manual_toner_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 8px;
                text-align: center;
                min-width: 80px;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        # Seçenek 4: Cihaz ekleme sırasında uyumlu toner öner
        self.auto_suggest_btn = QPushButton("🤖 Otomatik\nÖneri")
        self.auto_suggest_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 8px;
                text-align: center;
                min-width: 80px;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        
        options_layout.addWidget(self.predefined_btn)
        options_layout.addWidget(self.device_toner_btn)
        options_layout.addWidget(self.manual_toner_btn)
        options_layout.addWidget(self.auto_suggest_btn)
        options_layout.addStretch()  # Sağ tarafa hizala
        
        layout.addWidget(options_group)
        
        # Alt panel: İçerik alanı - daha geniş
        self.content_area = QGroupBox("İçerik")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_area.setMinimumHeight(500)  # Minimum yükseklik
        layout.addWidget(self.content_area)
        
        # Butonları bağla
        self.predefined_btn.clicked.connect(self.show_predefined_stocks)
        self.device_toner_btn.clicked.connect(self.show_kyocera_compatibility)
        self.manual_toner_btn.clicked.connect(self.show_manual_toner_form)
        self.auto_suggest_btn.clicked.connect(self.show_auto_suggest_demo)
        
        # Kapat butonu
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        self.close_btn = QPushButton("✖ Kapat")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        close_layout.addWidget(self.close_btn)
        layout.addLayout(close_layout)
        
    def load_data(self):
        """Başlangıç verilerini yükler."""
        self.show_predefined_stocks()  # Varsayılan olarak önceden tanımlanmış stokları göster
        
    def clear_content_area(self):
        """İçerik alanını temizler."""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            
    def show_predefined_stocks(self):
        """Önceden tanımlanmış stokları gösterir."""
        self.clear_content_area()
        
        info_label = QLabel("""
        <b>🔄 Önceden Tanımlanmış Stoklar</b><br>
        Bu seçenek ile aşağıdaki ürünler otomatik olarak stok kartları olarak eklenecektir:<br><br>
        
        <b>📝 Kyocera Tonerleri:</b><br>
        • TK-1150, TK-3190, TK-3300 serisi<br>
        • TK-5240 renkli toner serisi<br><br>
        
        <b>🔧 Sarf Malzemeleri:</b><br>
        • Drum Üniteleri (DK-1150, DK-3300)<br>
        • Fuser Üniteleri (FK-1150)<br>
        • Waste Toner Box (WT-3300)<br><br>
        
        <b>💼 CPC Uyumluluğu:</b><br>
        Bu ürünler CPC müşteriler için otomatik sipariş sisteminde kullanılır.
        """)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #E8F5E8; padding: 15px; border-radius: 8px;")
        
        self.content_layout.addWidget(info_label)
        
        # Ekle butonu
        add_btn = QPushButton("➕ Önceden Tanımlanmış Stokları Ekle")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_btn.clicked.connect(self.add_predefined_stocks)
        self.content_layout.addWidget(add_btn)
        
        self.content_layout.addStretch()
        
    def show_device_toner_mapping(self):
        """Cihaz-toner eşleştirme arayüzünü gösterir."""
        self.clear_content_area()
        
        # Splitter ile iki panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sol panel: Mevcut cihazlar
        left_panel = QGroupBox("📱 Mevcut Cihazlar")
        left_layout = QVBoxLayout(left_panel)
        
        self.devices_table = QTableWidget(0, 4)
        self.devices_table.setHorizontalHeaderLabels(["ID", "Model", "Seri No", "Renk Tipi"])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.devices_table.hideColumn(0)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        left_layout.addWidget(QLabel("Toner eklemek istediğiniz cihazı seçin:"))
        left_layout.addWidget(self.devices_table)
        
        # Sağ panel: Toner ekleme formu
        right_panel = QGroupBox("📝 Toner Ekleme")
        right_layout = QFormLayout(right_panel)
        
        self.selected_device_label = QLabel("Seçilen cihaz: Henüz seçilmedi")
        self.selected_device_label.setStyleSheet("font-weight: bold; color: #666;")
        
        self.toner_name_input = QLineEdit()
        self.toner_name_input.setPlaceholderText("Örn: TK-3300 TONER")
        
        self.toner_part_number_input = QLineEdit()
        self.toner_part_number_input.setPlaceholderText("Örn: TK-3300")
        
        self.toner_color_combo = QComboBox()
        self.toner_color_combo.addItems(["Siyah-Beyaz", "Renkli", "Siyah", "Cyan", "Magenta", "Yellow"])
        
        self.toner_quantity_input = QSpinBox()
        self.toner_quantity_input.setRange(0, 9999)
        self.toner_quantity_input.setValue(0)  # Default to 0 to show actual stock count
        
        self.toner_price_input = QDoubleSpinBox()
        self.toner_price_input.setRange(0.01, 99999.99)
        self.toner_price_input.setDecimals(2)
        self.toner_price_input.setValue(250.00)
        
        self.toner_currency_combo = QComboBox()
        self.toner_currency_combo.addItems(["TL", "USD", "EUR"])
        
        right_layout.addRow("", self.selected_device_label)
        right_layout.addRow("Toner Adı:", self.toner_name_input)
        right_layout.addRow("Parça Numarası:", self.toner_part_number_input)
        right_layout.addRow("Renk Tipi:", self.toner_color_combo)
        right_layout.addRow("Miktar:", self.toner_quantity_input)
        right_layout.addRow("Fiyat:", self.toner_price_input)
        right_layout.addRow("Para Birimi:", self.toner_currency_combo)
        
        # Toner ekle butonu
        add_toner_btn = QPushButton("➕ Toner Ekle")
        add_toner_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        add_toner_btn.clicked.connect(self.add_device_toner)
        right_layout.addRow("", add_toner_btn)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])
        
        self.content_layout.addWidget(splitter)
        
        # Sinyalleri bağla
        self.devices_table.selectionModel().selectionChanged.connect(self.on_device_selected)
        
        # Cihazları yükle
        self.load_devices_for_toner_mapping()
        
    def show_manual_toner_form(self):
        """Manuel toner tanımlama formunu gösterir."""
        self.clear_content_area()
        
        form_group = QGroupBox("✏️ Manuel Toner Tanımla")
        form_layout = QFormLayout(form_group)
        
        self.manual_toner_name = QLineEdit()
        self.manual_toner_name.setPlaceholderText("Örn: Canon CRG-728 Toner")
        
        self.manual_toner_part_number = QLineEdit()
        self.manual_toner_part_number.setPlaceholderText("Örn: CRG-728")
        
        self.manual_toner_description = QTextEdit()
        self.manual_toner_description.setMaximumHeight(60)
        self.manual_toner_description.setPlaceholderText("Toner açıklaması...")
        
        self.manual_toner_compatible_models = QTextEdit()
        self.manual_toner_compatible_models.setMaximumHeight(100)
        self.manual_toner_compatible_models.setPlaceholderText("Uyumlu cihaz modelleri (her satıra bir model):\nCanon i-SENSYS LBP6200d\nCanon i-SENSYS MF4410")
        
        self.manual_color_combo = QComboBox()
        self.manual_color_combo.addItems(["Siyah-Beyaz", "Renkli", "Siyah", "Cyan", "Magenta", "Yellow"])
        
        self.manual_quantity = QSpinBox()
        self.manual_quantity.setRange(1, 9999)
        self.manual_quantity.setValue(50)
        
        self.manual_price = QDoubleSpinBox()
        self.manual_price.setRange(0.01, 99999.99)
        self.manual_price.setDecimals(2)
        self.manual_price.setValue(180.00)
        
        self.manual_currency = QComboBox()
        self.manual_currency.addItems(["TL", "USD", "EUR"])
        
        self.manual_supplier = QLineEdit()
        self.manual_supplier.setPlaceholderText("Örn: Canon")
        
        form_layout.addRow("Toner Adı*:", self.manual_toner_name)
        form_layout.addRow("Parça Numarası*:", self.manual_toner_part_number)
        form_layout.addRow("Açıklama:", self.manual_toner_description)
        form_layout.addRow("Uyumlu Modeller:", self.manual_toner_compatible_models)
        form_layout.addRow("Renk Tipi:", self.manual_color_combo)
        form_layout.addRow("Miktar:", self.manual_quantity)
        form_layout.addRow("Satış Fiyatı:", self.manual_price)
        form_layout.addRow("Para Birimi:", self.manual_currency)
        form_layout.addRow("Tedarikçi:", self.manual_supplier)
        
        # Manuel toner ekle butonu
        add_manual_btn = QPushButton("➕ Manuel Toner Ekle")
        add_manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        add_manual_btn.clicked.connect(self.add_manual_toner)
        form_layout.addRow("", add_manual_btn)
        
        self.content_layout.addWidget(form_group)
        
    def load_devices_for_toner_mapping(self):
        """Cihaz-toner eşleştirmesi için cihazları yükler."""
        try:
            # Stok cihazları ve müşteri cihazları getir
            devices = []
            
            # Stok cihazlarını getir (name kolonunu model olarak kullan)
            stock_query = """
            SELECT name as model, 'Stok' as source, 
                   COALESCE(color_type, 'Siyah-Beyaz') as color_type, 
                   quantity as count
            FROM stock_items 
            WHERE item_type = 'Cihaz' AND quantity > 0
            """
            stock_devices = self.db.fetch_all(stock_query)
            devices.extend(stock_devices)
            
            # Müşteri cihazlarını getir
            customer_query = """
            SELECT DISTINCT model, 'Müşteri' as source, 
                   COALESCE(color_type, 'Siyah-Beyaz') as color_type, 
                   COUNT(*) as count
            FROM devices 
            WHERE model IS NOT NULL AND model != ''
            GROUP BY model, color_type
            """
            customer_devices = self.db.fetch_all(customer_query)
            devices.extend(customer_devices)
            
            # Sıralama
            devices.sort(key=lambda x: x['model'])
            
            self.devices_table.setRowCount(len(devices))
            
            for row, device in enumerate(devices):
                self.devices_table.setItem(row, 0, QTableWidgetItem(str(row)))  # Fake ID
                self.devices_table.setItem(row, 1, QTableWidgetItem(device['model']))
                self.devices_table.setItem(row, 2, QTableWidgetItem(f"{device['source']} ({device['count']} adet)"))
                self.devices_table.setItem(row, 3, QTableWidgetItem(device['color_type'] or 'Siyah-Beyaz'))
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Cihazlar yüklenirken hata oluştu:\n{str(e)}")
            
    def on_device_selected(self):
        """Cihaz seçildiğinde tetiklenir."""
        selected_rows = self.devices_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            model = self.devices_table.item(row, 1).text()
            source = self.devices_table.item(row, 2).text()
            color_type = self.devices_table.item(row, 3).text()
            
            self.selected_device_label.setText(f"Seçilen: {model} ({source}) - {color_type}")
            self.selected_device_label.setStyleSheet("font-weight: bold; color: #2196F3;")
            
            # Otomatik toner adı önerisi
            suggested_name = f"{model.upper()} TONER"
            self.toner_name_input.setText(suggested_name)
            
    def add_predefined_stocks(self):
        """Önceden tanımlanmış stokları ekler."""
        QMessageBox.information(
            self, "Bilgi", 
            "⚠️ Önceden Tanımlanmış Stok Sistemi Kaldırıldı\n\n"
            "Bu özellik artık kullanılamıyor. Stok kartlarını manuel olarak ekleyebilirsiniz.\n\n"
            "📝 Stok sekmesinden yeni ürünler ekleyebilirsiniz."
        )
            
    def add_device_toner(self):
        """Seçili cihaz için toner ekler."""
        selected_rows = self.devices_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir cihaz seçin.")
            return
            
        toner_name = self.toner_name_input.text().strip()
        part_number = self.toner_part_number_input.text().strip()
        
        if not toner_name or not part_number:
            QMessageBox.warning(self, "Uyarı", "Toner adı ve parça numarası gereklidir.")
            return
            
        try:
            # Toner stok kartı ekle
            insert_query = """
            INSERT INTO stock_items (item_type, name, part_number, description, 
                                    color_type, quantity, sale_price, sale_currency, supplier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            row = selected_rows[0].row()
            device_model = self.devices_table.item(row, 1).text()
            description = f"{device_model} için uyumlu toner"
            
            self.db.execute_query(insert_query, (
                'Toner',
                toner_name,
                part_number,
                description,
                self.toner_color_combo.currentText(),
                self.toner_quantity_input.value(),
                self.toner_price_input.value(),
                self.toner_currency_combo.currentText(),
                'Manuel Tanım'
            ))
            
            QMessageBox.information(
                self, "Başarılı", 
                f"✅ Toner başarıyla eklendi!\n\n"
                f"📝 Toner: {toner_name}\n"
                f"🔧 Parça No: {part_number}\n"
                f"📱 Cihaz: {device_model}\n"
                f"📦 Miktar: {self.toner_quantity_input.value()}"
            )
            
            # Formu temizle
            self.toner_name_input.clear()
            self.toner_part_number_input.clear()
            self.toner_quantity_input.setValue(50)
            
            self.stock_added.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Toner ekleme hatası:\n{str(e)}")
            
    def add_manual_toner(self):
        """Manuel toner tanımı ekler."""
        name = self.manual_toner_name.text().strip()
        part_number = self.manual_toner_part_number.text().strip()
        
        if not name or not part_number:
            QMessageBox.warning(self, "Uyarı", "Toner adı ve parça numarası gereklidir.")
            return
            
        try:
            insert_query = """
            INSERT INTO stock_items (item_type, name, part_number, description, 
                                    color_type, quantity, sale_price, sale_currency, supplier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            description = self.manual_toner_description.toPlainText().strip()
            if not description:
                description = f"{name} - Manuel tanım"
                
            self.db.execute_query(insert_query, (
                'Toner',
                name,
                part_number,
                description,
                self.manual_color_combo.currentText(),
                self.manual_quantity.value(),
                self.manual_price.value(),
                self.manual_currency.currentText(),
                self.manual_supplier.text().strip() or 'Manuel Tanım'
            ))
            
            # Uyumlu modeller varsa, bunları kaydet (gelecekte kullanım için)
            compatible_models = self.manual_toner_compatible_models.toPlainText().strip()
            
            QMessageBox.information(
                self, "Başarılı",
                f"✅ Manuel toner başarıyla eklendi!\n\n"
                f"📝 Toner: {name}\n"
                f"🔧 Parça No: {part_number}\n"
                f"💰 Fiyat: {self.manual_price.value()} {self.manual_currency.currentText()}\n"
                f"📦 Miktar: {self.manual_quantity.value()}"
            )
            
            # Formu temizle
            self.manual_toner_name.clear()
            self.manual_toner_part_number.clear()
            self.manual_toner_description.clear()
            self.manual_toner_compatible_models.clear()
            self.manual_supplier.clear()
            
            self.stock_added.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Manuel toner ekleme hatası:\n{str(e)}")
    
    def show_kyocera_compatibility(self):
        """Kyocera cihaz-toner uyumluluk sistemini gösterir."""
        self.clear_content_area()
        
        info_label = QLabel("""
        <b>🔧 Kyocera Cihaz-Toner Uyumluluk Sistemi</b><br>
        Bu sistem verilen listeye göre cihazlar ve uyumlu tonerler arasında otomatik eşleştirme yapar.<br>
        � <b>Test için cihaz adı girin:</b>
        """)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #E3F2FD; padding: 10px; border-radius: 6px; font-size: 11px;")
        self.content_layout.addWidget(info_label)
        
        # Test formu
        test_group = QGroupBox("Cihaz Test")
        test_layout = QFormLayout(test_group)
        
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("Örn: TASKalfa 2550ci, FS-1300DN, ECOSYS M2135dn")
        test_layout.addRow("Cihaz Modeli:", self.device_name_input)
        
        # Test butonu
        test_btn = QPushButton("🔍 Uyumlu Tonerleri Bul")
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        test_btn.clicked.connect(self.test_device_compatibility)
        test_layout.addRow("", test_btn)
        
        self.content_layout.addWidget(test_group)
        
        # Sonuçlar tablosu - daha geniş
        self.compatibility_results = QTableWidget()
        self.compatibility_results.setColumnCount(7)
        self.compatibility_results.setHorizontalHeaderLabels([
            "Toner Kodu", "Toner Adı", "Renk Tipi", "Baskı Kapasitesi", 
            "Stok Durumu", "Fiyat", "İşlem"
        ])
        
        header = self.compatibility_results.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.compatibility_results.setMinimumHeight(250)  # Minimum yükseklik
        self.compatibility_results.setAlternatingRowColors(True)
        
        self.content_layout.addWidget(self.compatibility_results)
        
        # Otomatik eksik toner ekleme butonu
        auto_add_btn = QPushButton("🤖 Eksik Tonerleri Otomatik Stok Kartı Yap")
        auto_add_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        auto_add_btn.clicked.connect(self.auto_create_missing_toners)
        self.content_layout.addWidget(auto_add_btn)
    
    def test_device_compatibility(self):
        """Cihaz uyumluluğunu test eder."""
        device_name = self.device_name_input.text().strip()
        if not device_name:
            QMessageBox.warning(self, "Uyarı", "Lütfen cihaz modelini girin!")
            return
        
        try:
            # Kyocera uyumluluk sistemini kullan
            compatible_toners = find_compatible_toners_for_device(device_name)
            stock_toners = get_stock_compatible_toners(device_name, self.db)
            missing_toners = suggest_missing_toners_for_device(device_name, self.db)
            
            # Tabloyu güncelle
            all_results = []
            
            # Stokta bulunan tonerler
            for toner in stock_toners:
                all_results.append({
                    "toner_code": toner["toner_code"],
                    "toner_name": toner["name"],
                    "color_type": toner["color_type"],
                    "print_capacity": toner["print_capacity"],
                    "stock_status": f"✅ Stokta ({toner['quantity']} adet)",
                    "price": f"{toner['sale_price']} {toner['sale_currency']}",
                    "action": "Mevcut"
                })
            
            # Eksik tonerler
            for toner in missing_toners:
                all_results.append({
                    "toner_code": toner["toner_code"],
                    "toner_name": toner["toner_name"],
                    "color_type": toner["color_type"],
                    "print_capacity": toner["print_capacity"],
                    "stock_status": "❌ Stokta Yok",
                    "price": "Belirtilmemiş",
                    "action": "Eklenebilir"
                })
            
            self.compatibility_results.setRowCount(len(all_results))
            
            for row, result in enumerate(all_results):
                self.compatibility_results.setItem(row, 0, QTableWidgetItem(result["toner_code"]))
                self.compatibility_results.setItem(row, 1, QTableWidgetItem(result["toner_name"]))
                self.compatibility_results.setItem(row, 2, QTableWidgetItem(result["color_type"]))
                self.compatibility_results.setItem(row, 3, QTableWidgetItem(str(result["print_capacity"])))
                self.compatibility_results.setItem(row, 4, QTableWidgetItem(result["stock_status"]))
                self.compatibility_results.setItem(row, 5, QTableWidgetItem(result["price"]))
                self.compatibility_results.setItem(row, 6, QTableWidgetItem(result["action"]))
            
            # Sonuç bilgisi
            info_text = f"""
            <b>📊 Test Sonuçları:</b><br>
            🔍 Cihaz: {device_name}<br>
            ✅ Uyumlu toner sayısı: {len(compatible_toners)}<br>
            📦 Stokta bulunan: {len(stock_toners)}<br>
            ❌ Eksik olan: {len(missing_toners)}
            """
            
            result_label = QLabel(info_text)
            result_label.setStyleSheet("background-color: #FFF3E0; padding: 10px; border-radius: 6px;")
            result_label.setWordWrap(True)
            
            # Mevcut sonuç labelını kaldır ve yenisini ekle
            if hasattr(self, 'result_info_label'):
                self.result_info_label.deleteLater()
            
            self.result_info_label = result_label
            self.content_layout.insertWidget(self.content_layout.count()-2, result_label)
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Uyumluluk testi hatası:\n{str(e)}")
    
    def auto_create_missing_toners(self):
        """Eksik tonerleri otomatik olarak stok kartı yapar."""
        device_name = self.device_name_input.text().strip()
        if not device_name:
            QMessageBox.warning(self, "Uyarı", "Önce cihaz testi yapın!")
            return
        
        try:
            missing_toners = suggest_missing_toners_for_device(device_name, self.db)
            
            if not missing_toners:
                QMessageBox.information(self, "Bilgi", "Eksik toner bulunamadı! Tüm uyumlu tonerler stokta mevcut.")
                return
            
            # Kullanıcıdan onay al
            reply = QMessageBox.question(
                self, "Onay",
                f"📝 {len(missing_toners)} adet eksik toner için otomatik stok kartı oluşturulsun mu?\n\n"
                f"Bu tonerler varsayılan fiyatlarla oluşturulacak ve sonradan düzenleyebilirsiniz.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                created_count = 0
                for toner in missing_toners:
                    if create_missing_toner_stock_card(toner, self.db):
                        created_count += 1
                
                QMessageBox.information(
                    self, "Başarılı",
                    f"✅ {created_count} adet toner stok kartı oluşturuldu!\n\n"
                    f"📋 Stok listesinden fiyatları ve detayları düzenleyebilirsiniz."
                )
                
                # Sonuç tablosunu yenile
                self.test_device_compatibility()
                self.stock_added.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Otomatik toner oluşturma hatası:\n{str(e)}")
    
    def show_auto_suggest_demo(self):
        """Cihaz ekleme sırasında otomatik toner önerme demo'sunu gösterir."""
        self.clear_content_area()
        
        info_label = QLabel("""
        <b>🤖 Otomatik Toner Önerme Sistemi</b><br>
        Bu özellik henüz aktif değildir. Geliştirme aşamasındadır.<br><br>
        
        <b>🎯 Planlanmış Özellikler:</b><br>
        • Cihaz ekleme dialog'unda uyumlu tonerleri otomatik göster<br>
        • Kullanıcı cihazı stoğa eklediğinde uyumlu tonerleri öner<br>
        • Toner stok seviyesi düştüğünde uyarı ver<br>
        • CPC müşterileri için otomatik toner siparişi<br><br>
        
        <b>⚙️ Entegrasyon Noktaları:</b><br>
        • Device Dialog (cihaz ekleme)<br>
        • Stock Tab (stok yönetimi)<br>
        • CPC ordering system<br><br>
        
        <i>Bu özellik gelecek güncellemelerde aktif hale gelecektir.</i>
        """)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #F3E5F5; padding: 15px; border-radius: 8px;")
        
        self.content_layout.addWidget(info_label)