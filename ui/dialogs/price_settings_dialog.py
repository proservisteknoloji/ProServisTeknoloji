# ui/dialogs/price_settings_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QDoubleSpinBox, QPushButton, QGroupBox,
                             QMessageBox, QFrame, QTabWidget, QWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from decimal import Decimal

class PriceSettingsDialog(QDialog):
    """Fiyat ayarları diyalogu - bayi ve son kullanıcı fiyat yönetimi."""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Fiyat Ayarları")
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self._init_ui()
        self._load_settings()
        
    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)
        
        # Başlık
        title_label = QLabel("Fiyat Yönetimi Ayarları")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Ayırıcı çizgi
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Genel ayarlar sekmesi
        self.general_tab = self._create_general_tab()
        self.tab_widget.addTab(self.general_tab, "Genel Ayarlar")
        
        # Özel fiyat sekmesi
        self.custom_tab = self._create_custom_tab()
        self.tab_widget.addTab(self.custom_tab, "Özel Fiyatlar")
        
        layout.addWidget(self.tab_widget)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Kaydet")
        self.cancel_btn = QPushButton("İptal")
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Sinyaller
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        
    def _create_general_tab(self):
        """Genel ayarlar sekmesini oluşturur."""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Kar marjı ayarları
        margin_group = QGroupBox("Kar Marjı Ayarları (Son Kullanıcı Fiyatı)")
        margin_layout = QGridLayout(margin_group)
        
        # Açıklama
        desc_label = QLabel("Bayi satış fiyatına eklenmecek kar marjı yüzdelerini belirleyin:")
        desc_label.setWordWrap(True)
        margin_layout.addWidget(desc_label, 0, 0, 1, 2)
        
        # Toner marjı
        margin_layout.addWidget(QLabel("Toner Kar Marjı (%):"), 1, 0)
        self.toner_margin_spin = QDoubleSpinBox()
        self.toner_margin_spin.setRange(0, 200)
        self.toner_margin_spin.setSuffix(" %")
        self.toner_margin_spin.setValue(30)
        margin_layout.addWidget(self.toner_margin_spin, 1, 1)
        
        # Yedek parça marjı
        margin_layout.addWidget(QLabel("Yedek Parça Kar Marjı (%):"), 2, 0)
        self.parts_margin_spin = QDoubleSpinBox()
        self.parts_margin_spin.setRange(0, 200)
        self.parts_margin_spin.setSuffix(" %")
        self.parts_margin_spin.setValue(25)
        margin_layout.addWidget(self.parts_margin_spin, 2, 1)
        
        # Cihaz marjı
        margin_layout.addWidget(QLabel("Cihaz Kar Marjı (%):"), 3, 0)
        self.device_margin_spin = QDoubleSpinBox()
        self.device_margin_spin.setRange(0, 200)
        self.device_margin_spin.setSuffix(" %")
        self.device_margin_spin.setValue(20)
        margin_layout.addWidget(self.device_margin_spin, 3, 1)
        
        layout.addWidget(margin_group)
        
        # Örnek hesaplama
        example_group = QGroupBox("Örnek Hesaplama")
        example_layout = QGridLayout(example_group)
        
        example_layout.addWidget(QLabel("Bayi Satış Fiyatı:"), 0, 0)
        self.example_input = QDoubleSpinBox()
        self.example_input.focusInEvent = lambda event: (self.example_input.selectAll(), super(QDoubleSpinBox, self.example_input).focusInEvent(event))[-1]
        self.example_input.setRange(0, 999999)
        self.example_input.setValue(100)
        self.example_input.valueChanged.connect(self._update_example)
        example_layout.addWidget(self.example_input, 0, 1)
        
        example_layout.addWidget(QLabel("Ürün Tipi:"), 1, 0)
        self.example_type_combo = QComboBox()
        self.example_type_combo.addItems(["Toner", "Yedek Parça", "Cihaz"])
        self.example_type_combo.currentTextChanged.connect(self._update_example)
        example_layout.addWidget(self.example_type_combo, 1, 1)
        
        example_layout.addWidget(QLabel("Son Kullanıcı Fiyatı:"), 2, 0)
        self.example_result = QLabel("130.00 TL")
        self.example_result.setStyleSheet("font-weight: bold; color: green;")
        example_layout.addWidget(self.example_result, 2, 1)
        
        layout.addWidget(example_group)
        
        layout.addStretch()
        return widget
        
    def _create_custom_tab(self):
        """Özel fiyatlar sekmesini oluşturur."""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Açıklama
        desc_label = QLabel("Belirli ürünler için özel kar marjı belirleyebilirsiniz:")
        layout.addWidget(desc_label)
        
        # Tablo
        self.custom_table = QTableWidget()
        self.custom_table.setColumnCount(4)
        self.custom_table.setHorizontalHeaderLabels(["Ürün Adı", "Tip", "Özel Marj (%)", "İşlem"])
        
        header = self.custom_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.custom_table)
        
        # Yeni özel fiyat ekleme
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Yeni özel fiyat eklemek için bir ürün seçin ve marj belirleyin."))
        add_layout.addStretch()
        
        self.add_custom_btn = QPushButton("Özel Fiyat Ekle")
        self.add_custom_btn.clicked.connect(self._add_custom_price)
        add_layout.addWidget(self.add_custom_btn)
        
        layout.addLayout(add_layout)
        
        return widget
        
    def _update_example(self):
        """Örnek hesaplama günceller."""
        base_price = self.example_input.value()
        product_type = self.example_type_combo.currentText()
        
        if product_type == "Toner":
            margin = self.toner_margin_spin.value()
        elif product_type == "Yedek Parça":
            margin = self.parts_margin_spin.value()
        else:  # Cihaz
            margin = self.device_margin_spin.value()
        
        final_price = base_price * (1 + margin / 100)
        self.example_result.setText(f"{final_price:.2f} TL")
        
    def _add_custom_price(self):
        """Özel fiyat ekleme diyalogunu açar."""
        dialog = CustomPriceDialog(self.db, self)
        if dialog.exec():
            self._load_custom_prices()
            
    def _load_settings(self):
        """Mevcut ayarları yükler."""
        try:
            # Veritabanından mevcut ayarları çek
            settings = self.db.get_price_settings()
            if settings:
                self.toner_margin_spin.setValue(settings.get('toner_margin', 30))
                self.parts_margin_spin.setValue(settings.get('parts_margin', 25))
                self.device_margin_spin.setValue(settings.get('device_margin', 20))
            
            self._load_custom_prices()
            self._update_example()
            
        except Exception as e:
            QMessageBox.warning(self, "Uyarı", f"Ayarlar yüklenirken hata: {e}")
            
    def _load_custom_prices(self):
        """Özel fiyatları yükler."""
        try:
            custom_prices = self.db.get_custom_price_margins()
            self.custom_table.setRowCount(len(custom_prices))
            
            for row, price_data in enumerate(custom_prices):
                self.custom_table.setItem(row, 0, QTableWidgetItem(price_data['name']))
                self.custom_table.setItem(row, 1, QTableWidgetItem(price_data['item_type']))
                self.custom_table.setItem(row, 2, QTableWidgetItem(f"{price_data['custom_margin']:.1f}"))
                
                # Sil butonu
                delete_btn = QPushButton("Sil")
                delete_btn.clicked.connect(lambda checked, item_id=price_data['id']: self._delete_custom_price(item_id))
                self.custom_table.setCellWidget(row, 3, delete_btn)
                
        except Exception as e:
            QMessageBox.warning(self, "Uyarı", f"Özel fiyatlar yüklenirken hata: {e}")
            
    def _delete_custom_price(self, item_id):
        """Özel fiyat kaydını siler."""
        try:
            self.db.delete_custom_price_margin(item_id)
            self._load_custom_prices()
            QMessageBox.information(self, "Başarılı", "Özel fiyat kaydı silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme işlemi başarısız: {e}")
            
    def save_settings(self):
        """Ayarları kaydeder."""
        try:
            settings = {
                'toner_margin': self.toner_margin_spin.value(),
                'parts_margin': self.parts_margin_spin.value(),
                'device_margin': self.device_margin_spin.value()
            }
            
            self.db.save_price_settings(settings)
            QMessageBox.information(self, "Başarılı", "Fiyat ayarları başarıyla kaydedildi.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Ayarlar kaydedilirken hata oluştu: {e}")


class CustomPriceDialog(QDialog):
    """Özel fiyat ekleme diyalogu."""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Özel Fiyat Ekle")
        self.setFixedSize(400, 200)
        
        self._init_ui()
        self._load_products()
        
    def _init_ui(self):
        """UI oluştur."""
        layout = QVBoxLayout(self)
        
        # Ürün seçimi
        layout.addWidget(QLabel("Ürün:"))
        self.product_combo = QComboBox()
        layout.addWidget(self.product_combo)
        
        # Marj girişi
        layout.addWidget(QLabel("Özel Kar Marjı (%):"))
        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.focusInEvent = lambda event: (self.margin_spin.selectAll(), super(QDoubleSpinBox, self.margin_spin).focusInEvent(event))[-1]
        self.margin_spin.setRange(0, 500)
        self.margin_spin.setSuffix(" %")
        layout.addWidget(self.margin_spin)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Kaydet")
        self.cancel_btn = QPushButton("İptal")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Sinyaller
        self.save_btn.clicked.connect(self.save_custom_price)
        self.cancel_btn.clicked.connect(self.reject)
        
    def _load_products(self):
        """Ürünleri yükle."""
        try:
            products = self.db.fetch_all("SELECT id, name, item_type FROM stock_items ORDER BY item_type, name")
            for product in products:
                self.product_combo.addItem(f"{product[1]} ({product[2]})", product[0])
        except Exception as e:
            QMessageBox.warning(self, "Uyarı", f"Ürünler yüklenirken hata: {e}")
            
    def save_custom_price(self):
        """Özel fiyatı kaydet."""
        try:
            if self.product_combo.count() == 0:
                QMessageBox.warning(self, "Uyarı", "Ürün seçiniz.")
                return
                
            product_id = self.product_combo.currentData()
            margin = self.margin_spin.value()
            
            self.db.save_custom_price_margin(product_id, margin)
            QMessageBox.information(self, "Başarılı", "Özel fiyat kaydedildi.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme işlemi başarısız: {e}")