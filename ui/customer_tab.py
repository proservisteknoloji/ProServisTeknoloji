# ui/customer_tab.py
# type: ignore

from decimal import Decimal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QLabel, QFormLayout, QComboBox, QMessageBox, 
                             QDialog, QDialogButtonBox, QTextEdit, QGroupBox, QDateEdit, QListWidget, QListWidgetItem)
import logging
logger = logging.getLogger(__name__)
from PyQt6.QtCore import pyqtSignal as Signal, Qt, QDate
from .dialogs.device_dialog import DeviceDialog
from utils.database import db_manager
import re

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

class CustomerDeviceTab(QWidget):
    def save_customer_table_column_widths(self):
        from PyQt6.QtCore import QSettings
        settings = QSettings("ProServis", "CustomerTab")
        for col in range(self.customer_table.columnCount()):
            settings.setValue(f"customer_table_col_width_{col}", self.customer_table.columnWidth(col))

    def restore_customer_table_column_widths(self):
        from PyQt6.QtCore import QSettings
        settings = QSettings("ProServis", "CustomerTab")
        for col in range(self.customer_table.columnCount()):
            width = settings.value(f"customer_table_col_width_{col}")
            if width is not None:
                self.customer_table.setColumnWidth(col, int(width))
    """Müşteri ve cihaz bilgilerini yöneten sekme."""

    def fix_is_cpc_column(self):
        """Veritabanındaki is_cpc alanı 0 veya 1 olmayan tüm kayıtları 0 yapar."""
        try:
            self.db.execute_query("UPDATE customer_devices SET is_cpc = 0 WHERE is_cpc NOT IN (0, 1)")
            QMessageBox.information(self, "Düzeltme Tamamlandı", "CPC sütunundaki hatalı kayıtlar düzeltildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Düzeltme sırasında hata oluştu: {e}")
    data_changed = Signal()

    def __init__(self, db, status_bar, user_role=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.status_bar = status_bar
        self.user_role = user_role or "user"  # Default to "user" if not provided
        self.selected_customer_id = None
        self.selected_location_id = None
        self.selected_device_id = None
        self.init_ui()
        self.refresh_customers()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sol Panel: Müşteriler
        customer_widget = self._create_customer_panel()
        
        # Sağ Panel: Lokasyonlar + Cihazlar
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Üst kısım: Lokasyonlar
        self.location_panel = self._create_location_panel()
        
        # Alt kısım: Cihazlar
        device_widget = self._create_device_panel()
        
        right_splitter.addWidget(self.location_panel)
        right_splitter.addWidget(device_widget)
        right_splitter.setSizes([300, 400])  # Lokasyon ve cihaz için oran
        
        main_splitter.addWidget(customer_widget)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([300, 700])  # Müşteri ve sağ panel için oran
        
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(main_splitter)
        
        self._connect_signals()

    def _create_customer_panel(self):
        """Müşteri listesi ve filtreleme panelini oluşturur."""
        customer_widget = QGroupBox("Müşteriler")
        customer_layout = QVBoxLayout(customer_widget)
        
        filter_layout = QHBoxLayout()
        
        # Mevcut arama kutusunu güncelle
        self.customer_filter_input = QLineEdit()
        self.customer_filter_input.setPlaceholderText("Müşteri adı, cihaz modeli veya seri no ile ara...")
        self.customer_filter_input.setToolTip("Müşteri adı, cihaz modeli veya seri numarası ile arama yapabilirsiniz.")
        
        # Arama seçenekleri için combobox
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem("Tümünde Ara", "all")
        self.search_type_combo.addItem("Müşteri Adı", "customer")
        self.search_type_combo.addItem("Cihaz Modeli", "device")
        self.search_type_combo.addItem("Seri No", "serial")
        self.search_type_combo.setFixedWidth(120)
        
        # Butonlar
        self.show_contract_btn = QPushButton("Sözleşmeli Müşteriler")
        self.show_all_btn = QPushButton("Tüm Müşteriler")
        self.add_customer_btn = QPushButton("Yeni Müşteri")
        self.delete_customer_btn = QPushButton("Müşteri Sil")
        
        self.delete_customer_btn.setEnabled(False)
        self.contract_manage_btn = QPushButton("Sözleşme Yönet")
        self.contract_manage_btn.setEnabled(False)
        
        # Admin kontrolü - sadece admin müşteri silebilir
        if self.user_role.lower() != "admin":
            self.delete_customer_btn.setVisible(False)
        
        # Arama alanını düzenle
        filter_layout.addWidget(self.search_type_combo)
        filter_layout.addWidget(self.customer_filter_input, 1)  # 1 = genişleyebilir
        filter_layout.addWidget(self.show_contract_btn)
        filter_layout.addWidget(self.show_all_btn)
        
        # İkinci satır: Müşteri işlem butonları
        button_row_2 = QHBoxLayout()
        button_row_2.addWidget(self.add_customer_btn)
        button_row_2.addWidget(self.contract_manage_btn)
        button_row_2.addWidget(self.delete_customer_btn)
        button_row_2.addStretch()  # Sola yaslamak için
        
        # Buton stilleri
        self.add_customer_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        self.contract_manage_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.delete_customer_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; font-weight: bold; }")
        
        customer_layout.addLayout(filter_layout)
        self.customer_table = QTableWidget(0, 5)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Ad Soyad", "Durum", "Başlangıç", "Bitiş"])
        self.customer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.customer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.customer_table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.setStretchLastSection(False)
        for col in range(self.customer_table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        self.customer_table.hideColumn(0)
        self.restore_customer_table_column_widths()
        header.sectionResized.connect(lambda idx, old, new: self.save_customer_table_column_widths())
        
        customer_layout.addLayout(button_row_2)
        customer_layout.addWidget(self.customer_table)
        return customer_widget

    def _create_location_panel(self):
        """Müşteriye ait lokasyonlar panelini oluşturur."""
        location_widget = QGroupBox("Lokasyonlar")
        location_layout = QVBoxLayout(location_widget)
        
        self.location_table = QTableWidget(0, 4)
        self.location_table.setHorizontalHeaderLabels(["ID", "Lokasyon Adı", "Adres", "Telefon"])
        self.location_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.location_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.location_table.setAlternatingRowColors(True)
        self.location_table.setShowGrid(True)
        
        # Sütun genişliklerini ayarla
        if self.location_table.horizontalHeader():
            self.location_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Lokasyon adı
        self.location_table.setColumnWidth(2, 150)  # Adres
        self.location_table.setColumnWidth(3, 120)  # Telefon
        self.location_table.hideColumn(0)
        
        location_layout.addWidget(self.location_table)
        return location_widget

    def _create_device_panel(self):
        """Müşteriye ait cihazlar panelini oluşturur."""
        device_widget = QGroupBox("Müşteriye Ait Cihazlar")
        device_layout = QVBoxLayout(device_widget)
        
        # Butonlar
        device_buttons = QHBoxLayout()
        self.add_device_btn = QPushButton("Yeni Cihaz")
        self.add_device_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        self.move_to_second_hand_btn = QPushButton("2. El Depoya Taşı")
        self.move_to_second_hand_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        self.move_to_second_hand_btn.setEnabled(False)
        device_buttons.addWidget(self.add_device_btn)
        device_buttons.addWidget(self.move_to_second_hand_btn)
        device_buttons.addStretch()
        device_layout.addLayout(device_buttons)
        
        # Cihaz tablosu - butonlar kaldırıldı, sadece listeleme
        self.device_table = QTableWidget(0, 6)
        self.device_table.setHorizontalHeaderLabels(["ID", "Model", "Seri Numarası", "Lokasyon", "Renk Tipi", "CPC"])
        self.device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.device_table.setAlternatingRowColors(True)  # Alternatif satır renkleri
        self.device_table.setShowGrid(True)  # Grid çizgilerini göster
        
        # Daha iyi okunabilirlik için sütun genişliklerini optimize et
        if self.device_table.horizontalHeader():
            self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Model - kullanıcı ayarlayabilir
            self.device_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Seri No - kullanıcı ayarlayabilir
            self.device_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Lokasyon - geniş
            self.device_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Renk Tipi - içeriğe göre
            self.device_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # CPC - sabit
        
        # Başlangıç genişlikleri ayarla
        self.device_table.setColumnWidth(1, 200)  # Model kolonu - geniş
        self.device_table.setColumnWidth(2, 150)  # Seri Numarası kolonu
        self.device_table.setColumnWidth(5, 80)   # CPC kolonu için sabit genişlik
        self.device_table.hideColumn(0)
        
        # Tablo başlıklarına tooltips ekle
        if self.device_table.horizontalHeaderItem(1):
            self.device_table.horizontalHeaderItem(1).setToolTip("Cihaz markası ve modeli - Sütun genişliğini ayarlayabilirsiniz")
        if self.device_table.horizontalHeaderItem(2):
            self.device_table.horizontalHeaderItem(2).setToolTip("Cihazın seri numarası - Sütun genişliğini ayarlayabilirsiniz")
        if self.device_table.horizontalHeaderItem(3):
            self.device_table.horizontalHeaderItem(3).setToolTip("Cihazın bulunduğu lokasyon")
        if self.device_table.horizontalHeaderItem(4):
            self.device_table.horizontalHeaderItem(4).setToolTip("Siyah-Beyaz veya Renkli")
        if self.device_table.horizontalHeaderItem(5):
            self.device_table.horizontalHeaderItem(5).setToolTip("Sayfa başına ücret sistemi")
        
        device_layout.addWidget(self.device_table)
        return device_widget

    def _create_edit_panel(self):
        """Cihaz bilgilerini düzenleme panelini oluşturur."""
        edit_panel = QGroupBox("Cihaz Bilgileri")
        edit_layout = QFormLayout(edit_panel)
        
        self.model_input = QLineEdit()
        self.serial_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Siyah-Beyaz", "Renkli"])
        self.is_cpc_combo = QComboBox()
        self.is_cpc_combo.addItems(["Seçim Yapınız...", "Evet", "Hayır"])
        
        self.bw_price_input = QLineEdit("0,0000")
        self.bw_price_input.focusInEvent = lambda a0: (self.bw_price_input.selectAll(), super(QLineEdit, self.bw_price_input).focusInEvent(a0))[-1]
        self.bw_currency_combo = QComboBox()
        self.bw_currency_combo.addItems(["TL", "USD", "EURO"])
        bw_price_layout = QHBoxLayout()
        bw_price_layout.addWidget(self.bw_price_input)
        bw_price_layout.addWidget(self.bw_currency_combo)
        
        self.color_price_input = QLineEdit("0,0000")
        self.color_price_input.focusInEvent = lambda a0: (self.color_price_input.selectAll(), super(QLineEdit, self.color_price_input).focusInEvent(a0))[-1]
        self.color_currency_combo = QComboBox()
        self.color_currency_combo.addItems(["TL", "USD", "EURO"])
        color_price_layout = QHBoxLayout()
        color_price_layout.addWidget(self.color_price_input)
        color_price_layout.addWidget(self.color_currency_combo)
        
        # Kiralama bedeli alanları kaldırıldı - veritabanında yok
        
        self.bw_price_label = QLabel("S/B Birim Fiyat:")
        self.color_price_label = QLabel("Renkli Birim Fiyat:")
        
        # Sözleşme bilgileri için etiketler
        self.contract_status_label = QLabel("Sözleşme Durumu:")
        self.contract_status_value = QLabel("")
        self.contract_dates_label = QLabel("Sözleşme Tarihleri:")
        self.contract_dates_value = QLabel("")
        
        self.save_device_btn = QPushButton("Değişiklikleri Kaydet")
        
        edit_layout.addRow("Model (*):", self.model_input)
        edit_layout.addRow("Seri Numarası (*):", self.serial_input)
        edit_layout.addRow("Renk Tipi:", self.type_combo)
        edit_layout.addRow("Kopya Başı mı? (*):", self.is_cpc_combo)
        edit_layout.addRow(self.bw_price_label, bw_price_layout)
        edit_layout.addRow(self.color_price_label, color_price_layout)
        edit_layout.addRow(self.contract_status_label, self.contract_status_value)
        edit_layout.addRow(self.contract_dates_label, self.contract_dates_value)
        edit_layout.addRow(self.save_device_btn)
        
        return edit_panel

    def _connect_signals(self):
        """Arayüz elemanlarının sinyallerini ilgili slotlara bağlar."""
        self.customer_table.itemSelectionChanged.connect(self.customer_selected)
        self.customer_table.itemDoubleClicked.connect(self.edit_selected_customer)
        self.location_table.itemSelectionChanged.connect(self.location_selected)
        self.location_table.itemDoubleClicked.connect(self.open_location_device_dialog)
        self.device_table.itemSelectionChanged.connect(self.device_selected)
        self.device_table.itemDoubleClicked.connect(self.change_device_location)  # Çift tıklama ile lokasyon değiştir
        self.customer_filter_input.textChanged.connect(self.filter_customers)
        
        self.show_contract_btn.clicked.connect(self.show_contract_customers)
        self.show_all_btn.clicked.connect(self.show_all_customers)
        self.add_customer_btn.clicked.connect(lambda: self.open_customer_dialog())
        self.contract_manage_btn.clicked.connect(self.manage_customer_contract)
        self.delete_customer_btn.clicked.connect(self.delete_selected_customer)
        self.add_device_btn.clicked.connect(self.add_new_device)
        self.move_to_second_hand_btn.clicked.connect(self.move_selected_device_to_second_hand)

    def customer_selected(self):
        """Müşteri tablosundan bir öğe seçildiğinde tetiklenir."""
        if not self.customer_table.selectionModel():
            return
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_customer_id = None
            self.selected_location_id = None
            self.device_table.setRowCount(0)
            self.contract_manage_btn.setEnabled(False)
            return

        item = self.customer_table.item(selected_rows[0].row(), 0)
        if not item:
            return
        self.selected_customer_id = int(item.text())
        self.selected_location_id = None  # Artık lokasyon seçimi yok
        
        self.contract_manage_btn.setEnabled(True)
        if self.user_role.lower() == "admin":
            self.delete_customer_btn.setEnabled(True)
        
        self.refresh_devices()
        self.refresh_locations()

    def location_selected(self):
        """Lokasyon tablosundan bir öğe seçildiğinde tetiklenir."""
        if not self.location_table.selectionModel():
            return
        selected_rows = self.location_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_location_id = None
            self.device_table.setRowCount(0)
            return

        item = self.location_table.item(selected_rows[0].row(), 0)
        if not item:
            return
        self.selected_location_id = int(item.text())
        
        self.refresh_devices()

    def open_location_device_dialog(self):
        """Seçili lokasyona ait cihazları yönetmek için dialog açar."""
        if not self.selected_location_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir lokasyon seçin.")
            return

        # Lokasyon bilgilerini al
        location_data = self.db.fetch_one("""
            SELECT location_name FROM customer_locations 
            WHERE id = ? AND customer_id = ?
        """, (self.selected_location_id, self.selected_customer_id))

        if not location_data:
            QMessageBox.warning(self, "Hata", "Lokasyon bilgileri bulunamadı.")
            return

        location_name = location_data['location_name']

        # LocationDeviceDialog'u aç
        from ui.dialogs.location_device_dialog import LocationDeviceDialog
        dialog = LocationDeviceDialog(
            self.db, 
            self.selected_customer_id, 
            self.selected_location_id, 
            location_name, 
            parent=self
        )
        dialog.exec()

        # Dialog kapandıktan sonra cihaz listesini yenile
        self.refresh_devices()

    def device_selected(self):
        if not self.device_table.selectionModel():
            return
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_device_id = None
            self.move_to_second_hand_btn.setEnabled(False)
            return
            
        item = self.device_table.item(selected_rows[0].row(), 0)
        if not item:
            return
        self.selected_device_id = int(item.text())
        self.move_to_second_hand_btn.setEnabled(True)

    def change_device_location(self, item):
        """Cihaza çift tıklandığında lokasyon değiştirme dialogunu açar."""
        if not self.selected_device_id or not self.selected_customer_id:
            return
        
        # Müşterinin lokasyonlarını al
        try:
            locations = self.db.fetch_all("""
                SELECT id, location_name, address
                FROM customer_locations
                WHERE customer_id = ?
                ORDER BY location_name
            """, (self.selected_customer_id,))
            
            if not locations:
                QMessageBox.information(
                    self,
                    "Lokasyon Yok",
                    "Bu müşteriye ait lokasyon bulunmuyor.\n"
                    "Önce lokasyon ekleyin."
                )
                return
            
            # Mevcut cihaz bilgisini al
            device_info = self.db.fetch_one("""
                SELECT device_model, serial_number, location_id
                FROM customer_devices
                WHERE id = ?
            """, (self.selected_device_id,))
            
            if not device_info:
                QMessageBox.warning(self, "Hata", "Cihaz bilgisi bulunamadı!")
                return
            
            # Lokasyon seçim dialogu
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Cihaz Lokasyonu Değiştir")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(dialog)
            
            # Cihaz bilgisi
            info_label = QLabel(f"<b>{device_info['device_model']}</b><br>"
                               f"Seri No: {device_info['serial_number']}")
            layout.addWidget(info_label)
            
            # Lokasyon seçimi
            layout.addWidget(QLabel("Lokasyon Seçin:"))
            location_combo = QComboBox()
            
            # "Lokasyon Yok" seçeneği ekle
            location_combo.addItem("Lokasyon Yok", None)
            
            # Mevcut lokasyonu seç
            current_location_idx = 0
            
            for idx, loc in enumerate(locations, start=1):
                location_text = f"{loc['location_name']}"
                if loc['address']:
                    location_text += f" - {loc['address']}"
                location_combo.addItem(location_text, loc['id'])
                
                # Mevcut lokasyonu işaretle
                if device_info['location_id'] and loc['id'] == device_info['location_id']:
                    current_location_idx = idx
            
            location_combo.setCurrentIndex(current_location_idx)
            layout.addWidget(location_combo)
            
            # Butonlar
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | 
                QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            if dialog.exec():
                # Seçilen lokasyon
                selected_location_id = location_combo.currentData()
                
                # Veritabanını güncelle
                try:
                    self.db.execute_query("""
                        UPDATE customer_devices
                        SET location_id = ?
                        WHERE id = ?
                    """, (selected_location_id, self.selected_device_id))
                    
                    # Tabloyu yenile
                    self.refresh_devices()
                    
                    location_name = location_combo.currentText().split(' - ')[0]
                    QMessageBox.information(
                        self,
                        "Başarılı",
                        f"Cihaz lokasyonu '{location_name}' olarak güncellendi."
                    )
                    
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Hata",
                        f"Lokasyon güncellenirken hata oluştu:\n{str(e)}"
                    )
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Hata",
                f"Lokasyonlar yüklenirken hata oluştu:\n{str(e)}"
            )

    def _populate_edit_form(self, data):
        """Cihaz düzenleme formunu veritabanından gelen verilerle doldurur."""
        self.model_input.setText(data['device_model'] if 'device_model' in data else '')
        self.serial_input.setText(data['serial_number'] if 'serial_number' in data else '')
        self.type_combo.setCurrentText(data['device_type'] if 'device_type' in data else 'Siyah-Beyaz')
        
        # CPC bilgilerini veritabanından gelen verilerle doldur
        is_cpc = data['is_cpc'] if 'is_cpc' in data else False
        if is_cpc:
            self.is_cpc_combo.setCurrentText("Evet")
        else:
            self.is_cpc_combo.setCurrentText("Hayır")
        
        # Fiyat bilgilerini doldur
        self.bw_price_input.setText(str(data['cpc_bw_price'] if 'cpc_bw_price' in data else 0).replace('.', ','))
        bw_currency = data['cpc_bw_currency'] if 'cpc_bw_currency' in data else 'TL'
        self.bw_currency_combo.setCurrentText(bw_currency)
        
        self.color_price_input.setText(str(data['cpc_color_price'] if 'cpc_color_price' in data else 0).replace('.', ','))
        color_currency = data['cpc_color_currency'] if 'cpc_color_currency' in data else 'TL'
        self.color_currency_combo.setCurrentText(color_currency)
        
        # Sözleşme bilgilerini göster
        if self.selected_customer_id:
            customer_data = self.db.fetch_one(
                "SELECT is_contract, contract_start_date, contract_end_date FROM customers WHERE id = ?", 
                (self.selected_customer_id,)
            )
            if customer_data:
                contract_status = "Sözleşmeli" if customer_data['is_contract'] else "Ücretli"
                self.contract_status_value.setText(contract_status)
                
                start_date = customer_data['contract_start_date'] or "Belirtilmemiş"
                end_date = customer_data['contract_end_date'] or "Belirtilmemiş"
                self.contract_dates_value.setText(f"{start_date} - {end_date}")
            else:
                self.contract_status_value.setText("Bilinmiyor")
                self.contract_dates_value.setText("Bilinmiyor")
        else:
            self.contract_status_value.setText("")
            self.contract_dates_value.setText("")
        
        self.toggle_price_fields()

    def manage_customer_contract(self):
        """Müşterinin sözleşme PDF'ini yönetir."""
        import os
        from PyQt6.QtWidgets import QFileDialog
        
        if not self.selected_customer_id:
            return
            
        # Müşteri bilgilerini al
        customer = self.db.fetch_one(
            "SELECT name, contract_pdf_path FROM customers WHERE id = ?", 
            (self.selected_customer_id,)
        )
        
        if not customer:
            QMessageBox.warning(self, "Hata", "Müşteri bilgisi bulunamadı.")
            return
            
        customer_name, existing_pdf = customer
        
        # Dialog oluştur
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{customer_name} - Sözleşme Yönetimi")
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Mevcut PDF durumu
        if existing_pdf and os.path.exists(existing_pdf):
            info_label = QLabel(f"Mevcut sözleşme: {os.path.basename(existing_pdf)}")
            layout.addWidget(info_label)
            
            # Görüntüle butonu
            view_btn = QPushButton("Sözleşmeyi Görüntüle")
            def view_contract():
                try:
                    if os.name == 'nt':
                        os.startfile(existing_pdf)
                    else:
                        os.system(f'xdg-open "{existing_pdf}"')
                except Exception as e:
                    QMessageBox.critical(dialog, "Hata", f"PDF açılırken hata: {e}")
            view_btn.clicked.connect(view_contract)
            layout.addWidget(view_btn)
        else:
            info_label = QLabel("Henüz sözleşme PDF'i yüklenmemiş.")
            layout.addWidget(info_label)
        
        # Yeni PDF yükle butonu
        upload_btn = QPushButton("Yeni Sözleşme PDF'i Yükle")
        def upload_contract():
            file_path, _ = QFileDialog.getOpenFileName(
                dialog, "Sözleşme PDF'ini Seç", "", "PDF Dosyaları (*.pdf)"
            )
            if file_path:
                try:
                    # contracts dizinini oluştur
                    contracts_dir = os.path.join(os.path.dirname(__file__), "..", "contracts")
                    os.makedirs(contracts_dir, exist_ok=True)
                    
                    # Dosyayı kopyala
                    import shutil
                    filename = f"sozlesme_{self.selected_customer_id}_{customer_name.replace(' ', '_')}.pdf"
                    dest_path = os.path.join(contracts_dir, filename)
                    shutil.copy2(file_path, dest_path)
                    
                    # Veritabanını güncelle
                    self.db.execute_query(
                        "UPDATE customers SET contract_pdf_path = ? WHERE id = ?",
                        (dest_path, self.selected_customer_id)
                    )
                    
                    QMessageBox.information(dialog, "Başarılı", "Sözleşme PDF'i başarıyla yüklendi.")
                    dialog.accept()
                    
                except Exception as e:
                    QMessageBox.critical(dialog, "Hata", f"PDF yüklenirken hata: {e}")
        
        upload_btn.clicked.connect(upload_contract)
        layout.addWidget(upload_btn)
        
        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.reject)
        layout.addWidget(close_btn)
        
        dialog.exec()

    def add_location(self):
        """Yeni lokasyon ekleme dialogunu açar."""
        if not self.selected_customer_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir müşteri seçin.")
            return
        
        from ui.dialogs.location_dialog import LocationDialog
        dialog = LocationDialog(self.selected_customer_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_locations()

    def prepare_for_new_device(self):
        """Yeni bir cihaz eklemek için dialog açar."""
        if not self.selected_location_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir lokasyon seçin.")
            return
        
        if not self.selected_customer_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir müşteri seçin.")
            return
        
        dialog = DeviceDialog(self.db, self.selected_customer_id, location_id=self.selected_location_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # DeviceDialog kendi içinde save_device_with_toners() ile kayıt yapar
            # Otomatik toner ekleme de burada gerçekleşir
            self.load_devices()
            self.data_changed.emit()

    def add_new_device(self):
        """Yeni cihaz ekleme dialogunu açar - buton tıklaması için."""
        if not self.selected_customer_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir müşteri seçin.")
            return

        # DeviceDialog'u açma - lokasyon isteğe bağlı olacak
        dialog = DeviceDialog(self.db, self.selected_customer_id, location_id=self.selected_location_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_devices()
            self.data_changed.emit()

    def move_selected_device_to_second_hand(self):
        """Seçili müşteri cihazını 2. el depoya taşır."""
        if not self.selected_device_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir cihaz seçin.")
            return

        try:
            device_info = self.db.fetch_one("""
                SELECT cd.id, cd.device_model, cd.serial_number, cd.notes,
                       c.name as customer_name
                FROM customer_devices cd
                JOIN customers c ON c.id = cd.customer_id
                WHERE cd.id = ?
            """, (self.selected_device_id,))

            if not device_info:
                QMessageBox.warning(self, "Hata", "Cihaz bilgisi bulunamadı.")
                return

            from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel
            from datetime import datetime

            dialog = QDialog(self)
            dialog.setWindowTitle("2. El Depoya Taşı")
            dialog.setMinimumWidth(400)
            layout = QFormLayout(dialog)

            info_label = QLabel(
                f"<b>Müşteri:</b> {device_info['customer_name']}<br>"
                f"<b>Cihaz:</b> {device_info['device_model']}<br>"
                f"<b>Seri No:</b> {device_info['serial_number']}"
            )
            layout.addRow(info_label)

            date_input = QLineEdit()
            date_input.setText(datetime.now().strftime("%Y-%m-%d"))
            price_input = QLineEdit()
            sale_price_input = QLineEdit()
            status_combo = QComboBox()
            status_combo.addItems(['Stokta', 'Serviste', 'Satıldı'])
            reason_input = QLineEdit()
            notes_input = QLineEdit()

            layout.addRow("Alınma Tarihi:", date_input)
            layout.addRow("Alış Fiyatı:", price_input)
            layout.addRow("Satış Fiyatı:", sale_price_input)
            layout.addRow("Durum:", status_combo)
            layout.addRow("Alım Nedeni:", reason_input)
            layout.addRow("Notlar:", notes_input)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            reason_text = reason_input.text().strip()
            notes_text = notes_input.text().strip()
            if reason_text:
                notes_text = f"{notes_text} | Alım nedeni: {reason_text}" if notes_text else f"Alım nedeni: {reason_text}"

            data = {
                'device_model': device_info['device_model'],
                'serial_number': device_info['serial_number'],
                'source_person': device_info['customer_name'],
                'acquisition_date': date_input.text().strip(),
                'purchase_price': float(price_input.text() or 0),
                'sale_price': float(sale_price_input.text() or 0),
                'status': status_combo.currentText(),
                'notes': notes_text
            }

            # 2. el tablosuna ekle
            self.db.execute_query(
                """
                INSERT INTO second_hand_devices 
                (device_model, serial_number, source_person, acquisition_date, purchase_price, sale_price, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data['device_model'], data['serial_number'], data['source_person'],
                    data['acquisition_date'], data['purchase_price'], data['sale_price'],
                    data['status'], data['notes']
                )
            )

            # Müşteri cihazını boşa al (customer_id = NULL)
            move_note = f"2. el depoya taşındı: {data['acquisition_date']}"
            self.db.execute_query(
                """
                UPDATE customer_devices
                SET customer_id = NULL, location_id = NULL,
                    notes = CASE
                        WHEN notes IS NULL OR notes = '' THEN ?
                        ELSE notes || '\n' || ?
                    END
                WHERE id = ?
                """,
                (move_note, move_note, self.selected_device_id)
            )

            # Normal stoka da ekle
            self._add_second_hand_to_normal_stock(data)

            self.refresh_devices()
            self.data_changed.emit()

            main_window = self.window()
            if hasattr(main_window, 'stock_tab'):
                main_window.stock_tab.refresh_second_hand_stock()
                main_window.stock_tab.refresh_data()

            QMessageBox.information(self, "Başarılı", "Cihaz 2. el depoya taşındı.")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"2. el depoya taşıma sırasında hata oluştu:\n{e}")

    def _add_second_hand_to_normal_stock(self, device_data):
        """2. El cihazı normal stoka ekler."""
        try:
            existing = self.db.fetch_one(
                "SELECT id, quantity FROM stock_items WHERE name = ? AND item_type = 'Cihaz'",
                (device_data['device_model'],)
            )

            if existing:
                new_quantity = existing['quantity'] + 1
                self.db.execute_query(
                    "UPDATE stock_items SET quantity = ? WHERE id = ?",
                    (new_quantity, existing['id'])
                )
                self.db.add_stock_movement(
                    existing['id'], 'Giriş', 1,
                    f"2. El cihaz eklendi - Seri No: {device_data['serial_number']}"
                )
            else:
                stock_data = {
                    'name': device_data['device_model'],
                    'item_type': 'Cihaz',
                    'part_number': device_data['serial_number'],
                    'quantity': 1,
                    'sale_price': device_data.get('sale_price') or (device_data['purchase_price'] * 1.2),
                    'description': f"2. El cihaz - Alınan: {device_data['source_person']}"
                }
                new_id = self.db.execute_query(
                    """
                    INSERT INTO stock_items (name, item_type, part_number, quantity, sale_price, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stock_data['name'], stock_data['item_type'], stock_data['part_number'],
                        stock_data['quantity'], stock_data['sale_price'], stock_data['description']
                    )
                )
                if new_id:
                    self.db.add_stock_movement(
                        new_id, 'Giriş', 1,
                        f"2. El cihaz eklendi - Seri No: {device_data['serial_number']}"
                    )
        except Exception as e:
            QMessageBox.warning(self, "Uyarı", f"Normal stok güncellenemedi: {e}")

    def save_device(self):
        """Yeni cihazı veya mevcut cihazdaki değişiklikleri veritabanına kaydeder."""
        if not self.model_input.text() or not self.serial_input.text():
            QMessageBox.warning(self, "Eksik Bilgi", "Model ve Seri Numarası alanları boş bırakılamaz.")
            return
        
        if self.is_cpc_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen 'Cihaz Kopya Başı mı?' sorusuna cevap verin.")
            return
            
        is_cpc = self.is_cpc_combo.currentText() == "Evet"
        
        try:
            device_data = {
                "device_model": self.model_input.text(),
                "serial_number": self.serial_input.text(),
                "device_type": self.type_combo.currentText(),
                "color_type": self.type_combo.currentText(),
                "brand": "",  # Brand alanı eklenebilir
                "installation_date": "",  # Kurulum tarihi eklenebilir
                "notes": "",  # Notlar eklenebilir
                "is_cpc": is_cpc,
                "bw_price": float(self.bw_price_input.text().replace(',', '.') or 0),
                "bw_currency": self.bw_currency_combo.currentText(),
                "color_price": float(self.color_price_input.text().replace(',', '.') or 0),
                "color_currency": self.color_currency_combo.currentText()
            }
            
            # Debug: Para birimi değerlerini kontrol et
            logger.debug(f"DEBUG: Kaydedilecek para birimleri - S/B: '{device_data['bw_currency']}', Renkli: '{device_data['color_currency']}'")

            saved_id = self.db.save_customer_device(
                self.selected_customer_id, 
                device_data, 
                self.selected_device_id
            )

            if saved_id:
                message = "Cihaz başarıyla güncellendi." if self.selected_device_id else "Cihaz başarıyla eklendi."
                QMessageBox.information(self, "Başarılı", message)
                
                # Cihaz listesini yenile
                self.load_devices()
                
                # Düzenleme panelini güncellenmiş bilgilerle yeniden doldur
                if self.selected_device_id:
                    # Cihazı tabloda tekrar seç
                    for row in range(self.device_table.rowCount()):
                        item = self.device_table.item(row, 0)
                        if item and int(item.text()) == self.selected_device_id:
                            self.device_table.selectRow(row)
                            break
                    
                    device_data = self.db.get_customer_device(self.selected_device_id)
                    if device_data:
                        self._populate_edit_form(device_data)
                
                self.data_changed.emit()
                self.status_bar.showMessage(message, 3000)
            else:
                QMessageBox.critical(self, "Hata", "Cihaz kaydedilirken bir hata oluştu.")

        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Cihaz kaydedilirken bir hata oluştu.\n\nDetay: {e}")

    def open_customer_dialog(self, customer_id=None):
        """Yeni müşteri eklemek veya mevcut müşteriyi düzenlemek için bir diyalog açar."""
        from PyQt6.QtWidgets import QCheckBox, QDateEdit, QTabWidget
        from PyQt6.QtCore import QDate
        
        is_editing = customer_id is not None
        dialog = QDialog(self)
        dialog.setWindowTitle("Müşteri Düzenle" if is_editing else "Yeni Müşteri")
        dialog.resize(900, 700)  # Daha büyük boyut

        main_layout = QVBoxLayout(dialog)
        
        # Tab widget oluştur
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Yeni müşteri için geçici customer_id (veritabanına kaydedilince güncellenecek)
        temp_customer_id = customer_id
        
        # Sekme 1: Müşteri Bilgileri
        customer_tab = QWidget()
        customer_layout = QFormLayout(customer_tab)
        
        name_input = QLineEdit()
        phone_input = QLineEdit()
        email_input = QLineEdit()
        address_input = QTextEdit()
        tax_office_input = QLineEdit()
        tax_number_input = QLineEdit()
        
        # Sözleşme alanları
        is_contract_combo = QComboBox()
        is_contract_combo.addItems(["Hayır", "Evet"])
        contract_start_date = QDateEdit()
        contract_end_date = QDateEdit()
        contract_period_combo = QComboBox()
        contract_period_combo.addItems(["Aylık", "Yıllık"])
        contract_price_input = QLineEdit()
        contract_price_input.setPlaceholderText("0.00")
        contract_currency_combo = QComboBox()
        contract_currency_combo.addItems(["TL", "USD", "EUR"])
        bill_contract_btn = QPushButton("Faturalandır")
        contract_start_date.setDate(QDate.currentDate())
        contract_end_date.setDate(QDate.currentDate().addYears(1))
        contract_start_date.setCalendarPopup(True)
        contract_end_date.setCalendarPopup(True)
        contract_start_date.setEnabled(False)
        contract_end_date.setEnabled(False)
        contract_price_input.setEnabled(False)
        contract_currency_combo.setEnabled(False)
        
        def toggle_contract_fields():
            enabled = is_contract_combo.currentText() == "Evet"
            contract_start_date.setEnabled(enabled)
            contract_end_date.setEnabled(enabled)
            contract_period_combo.setEnabled(enabled)
            contract_price_input.setEnabled(enabled)
            contract_currency_combo.setEnabled(enabled)
            bill_contract_btn.setEnabled(enabled)
        
        is_contract_combo.currentTextChanged.connect(toggle_contract_fields)

        def create_maintenance_invoice():
            try:
                customer_name = name_input.text().strip()
                if not customer_name:
                    QMessageBox.warning(dialog, "Uyarı", "Önce müşteri bilgilerini kaydedin.")
                    return

                price_text = contract_price_input.text() or "0"
                logger.debug(f"DEBUG: Sözleşme bedeli text: '{price_text}'")
                price = float(price_text)
                logger.debug(f"DEBUG: Sözleşme bedeli float: {price}")
                
                if price <= 0:
                    QMessageBox.warning(dialog, "Uyarı", f"Sözleşme bedeli girilmemiş veya 0. Mevcut değer: {price}")
                    return

                customer_id_value = customer_id or temp_customer_id
                if not customer_id_value:
                    customer_id_value = ensure_customer_saved()
                if not customer_id_value:
                    QMessageBox.warning(dialog, "Uyarı", "Müşteri kaydı bulunamadı.")
                    return

                from datetime import datetime
                from decimal import Decimal
                
                # Sözleşme periyodu (Aylık/Yıllık) al
                contract_period = contract_period_combo.currentText()
                # Para birimi al
                contract_currency = contract_currency_combo.currentText()
                logger.debug(f"DEBUG: Sözleşme periyodu: {contract_period}, Para birimi: {contract_currency}")
                logger.debug(f"DEBUG: Fatura oluşturuluyor - customer_id: {customer_id_value}, price: {price} {contract_currency}")
                
                # Fiyatı ondalık sayıya çevir
                price_decimal = Decimal(str(price))
                
                # Para birimi TL değilse, güncel kur ile TL'ye çevir
                price_tl = price_decimal
                if contract_currency != 'TL':
                    from utils.currency_converter import get_exchange_rates
                    try:
                        rates = get_exchange_rates()
                        if contract_currency in rates:
                            price_tl = price_decimal * Decimal(str(rates[contract_currency]))
                            logger.debug(f"DEBUG: Kur dönüşümü: {price} {contract_currency} = {price_tl} TL (Kur: {rates[contract_currency]})")
                        else:
                            QMessageBox.warning(dialog, "Uyarı", f"Para birimi {contract_currency} için kur bulunamadı!")
                            return
                    except Exception as e:
                        QMessageBox.warning(dialog, "Uyarı", f"Kur dönüşümü başarısız: {e}")
                        return
                
                # Float'a geri çevir (veritabanı için)
                price_tl_float = float(price_tl)
                
                invoice_id = self.db.execute_query(
                    """
                    INSERT INTO invoices (customer_id, invoice_date, total_amount, currency, notes, status, invoice_type)
                    VALUES (?, ?, ?, ?, ?, 'Kesildi', 'Bakım Sözleşmesi')
                    """,
                    (
                        customer_id_value,
                        datetime.now().strftime("%Y-%m-%d"),
                        price_tl_float,
                        "TL",
                        "Bakım Sözleşmesi Bedeli",
                    ),
                )
                logger.debug(f"DEBUG: Fatura oluşturuldu, ID: {invoice_id}")

                if invoice_id:
                    # Bakım sözleşmesi bedeli için invoice_items tablosuna kalem ekle
                    # Açıklamayı "Aylık" veya "Yıllık" ile birlikte oluştur
                    if contract_currency == 'TL':
                        item_description = f"Bakım Sözleşmesi {contract_period} Bedeli"
                    else:
                        item_description = f"Bakım Sözleşmesi {contract_period} Bedeli ({price} {contract_currency})"
                    
                    self.db.execute_query(
                        """
                        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, currency)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            invoice_id,
                            item_description,
                            1,
                            price_tl_float,
                            "TL",
                        ),
                    )
                    logger.debug(f"DEBUG: Fatura kalemleri oluşturuldu - {item_description}")
                    QMessageBox.information(dialog, "Başarılı", f"Faturalandırıldı.\n\nBedel: {price} {contract_currency} = {price_tl_float:.2f} TL")
            except Exception as e:
                QMessageBox.critical(dialog, "Hata", f"Faturalandırma hatası: {e}")

        bill_contract_btn.clicked.connect(create_maintenance_invoice)

        customer_layout.addRow("Ad Soyad (*):", name_input)
        customer_layout.addRow("Telefon (*):", phone_input)
        customer_layout.addRow("E-posta:", email_input)
        
        # Telefon formatlama
        def format_phone_on_change():
            current_text = phone_input.text()
            formatted = format_phone_number(current_text)
            if formatted != current_text:
                phone_input.setText(formatted)
        phone_input.textChanged.connect(format_phone_on_change)
        
        # Email normalize etme
        def normalize_email_on_change():
            current_text = email_input.text()
            normalized = normalize_email(current_text)
            if normalized != current_text:
                email_input.setText(normalized)
        
        email_input.textChanged.connect(normalize_email_on_change)
        customer_layout.addRow("Adres:", address_input)
        customer_layout.addRow("Vergi Dairesi:", tax_office_input)
        customer_layout.addRow("Vergi No:", tax_number_input)
        customer_layout.addRow("", QLabel())  # Boşluk
        customer_layout.addRow("Sözleşme Durumu:", is_contract_combo)

        contract_dates_layout = QHBoxLayout()
        contract_dates_layout.addWidget(QLabel("Sözleşme Başlangıç:"))
        contract_dates_layout.addWidget(contract_start_date)
        contract_dates_layout.addWidget(QLabel("Sözleşme Bitiş:"))
        contract_dates_layout.addWidget(contract_end_date)
        contract_dates_layout.addWidget(QLabel("Sözleşme Bedeli:"))
        contract_dates_layout.addWidget(contract_price_input)
        contract_dates_layout.addWidget(contract_currency_combo)
        contract_dates_layout.addStretch()
        customer_layout.addRow(contract_dates_layout)

        period_bill_layout = QHBoxLayout()
        period_bill_layout.addWidget(contract_period_combo)
        period_bill_layout.addWidget(bill_contract_btn)
        customer_layout.addRow("Sözleşme Şekli:", period_bill_layout)
        
        tab_widget.addTab(customer_tab, "Müşteri Bilgileri")
        
        # Sekme 2: Lokasyon Yönetimi
        location_tab = QWidget()
        location_layout = QVBoxLayout(location_tab)
        
        # Lokasyon tablosu
        location_table = QTableWidget(0, 4)
        location_table.setHorizontalHeaderLabels(["ID", "Lokasyon Adı", "Adres", "Telefon"])
        location_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        location_table.setAlternatingRowColors(True)
        location_table.hideColumn(0)  # ID kolonunu gizle
        location_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        location_layout.addWidget(location_table)
        
        # Lokasyon butonları
        location_buttons = QHBoxLayout()
        add_location_btn = QPushButton("Yeni Lokasyon")
        edit_location_btn = QPushButton("Düzenle")
        delete_location_btn = QPushButton("Sil")
        refresh_location_btn = QPushButton("Yenile")
        
        add_location_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        edit_location_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        delete_location_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; font-weight: bold; }")
        
        location_buttons.addWidget(add_location_btn)
        location_buttons.addWidget(edit_location_btn)
        location_buttons.addWidget(delete_location_btn)
        location_buttons.addWidget(refresh_location_btn)
        location_buttons.addStretch()
        location_layout.addLayout(location_buttons)
        
        tab_widget.addTab(location_tab, "Lokasyonlar")
        
        # Sekme 3: Cihaz Yönetimi
        device_tab = QWidget()
        device_layout = QVBoxLayout(device_tab)
        
        # Bilgi etiketi
        device_info_label = QLabel("💡 <i>Cihazın lokasyonunu değiştirmek için cihaza çift tıklayın</i>")
        device_info_label.setStyleSheet("color: #666; padding: 5px;")
        device_layout.addWidget(device_info_label)
        
        # Cihaz tablosu - lokasyon değişikliği için double-click destekli
        device_table = QTableWidget(0, 6)
        device_table.setHorizontalHeaderLabels(["ID", "Model", "Seri Numarası", "Lokasyon", "Renk Tipi", "CPC"])
        device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        device_table.setAlternatingRowColors(True)
        device_table.hideColumn(0)  # ID kolonunu gizle
        device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        device_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        device_layout.addWidget(device_table)
        
        tab_widget.addTab(device_tab, "Cihazlar")
        
        # Ana butonlar
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        main_layout.addWidget(buttons)

        # Dialog seviyesinde değişkenler
        selected_location_id = None

        # Yeni müşteri için otomatik kaydetme fonksiyonu
        def ensure_customer_saved():
            """Müşteri bilgileri girilmişse ve henüz kaydedilmemişse, otomatik kaydet."""
            nonlocal temp_customer_id
            
            # Eğer zaten düzenleniyorsa, kaydetmeye gerek yok
            if temp_customer_id:
                return temp_customer_id
            
            # Zorunlu alanlar kontrolü
            if not name_input.text().strip():
                QMessageBox.warning(dialog, "Uyarı", 
                    "Lokasyon veya cihaz eklemeden önce lütfen müşteri adını girin.")
                tab_widget.setCurrentIndex(0)  # Müşteri Bilgileri sekmesine dön
                name_input.setFocus()
                return None
            
            if not phone_input.text().strip():
                QMessageBox.warning(dialog, "Uyarı", 
                    "Lokasyon veya cihaz eklemeden önce lütfen telefon numarasını girin.")
                tab_widget.setCurrentIndex(0)  # Müşteri Bilgileri sekmesine dön
                phone_input.setFocus()
                return None
            
            # Müşteriyi kaydet
            try:
                normalized_email = normalize_email(email_input.text())
                
                # Sözleşme tarihleri
                start_date_str = None
                end_date_str = None
                if is_contract_combo.currentText() == "Evet":
                    start_date_str = contract_start_date.date().toString("yyyy-MM-dd")
                    end_date_str = contract_end_date.date().toString("yyyy-MM-dd")
                
                contract_period_value = contract_period_combo.currentText() if is_contract_combo.currentText() == "Evet" else None
                contract_price_value = float(contract_price_input.text() or 0) if is_contract_combo.currentText() == "Evet" else 0
                contract_currency_value = contract_currency_combo.currentText() if is_contract_combo.currentText() == "Evet" else "TL"

                params = (
                    name_input.text().strip(),
                    phone_input.text().strip(),
                    normalized_email,
                    address_input.toPlainText().strip(),
                    tax_office_input.text().strip(),
                    tax_number_input.text().strip(),
                    1 if is_contract_combo.currentText() == "Evet" else 0,
                    start_date_str,
                    end_date_str,
                    contract_period_value,
                    contract_price_value,
                    contract_currency_value
                )
                
                # execute_query lastrowid döndürür
                lastrowid = self.db.execute_query(
                    "INSERT INTO customers (name, phone, email, address, tax_office, tax_id, is_contract, contract_start_date, contract_end_date, contract_period, contract_price, contract_currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                    params
                )
                
                if lastrowid:
                    temp_customer_id = lastrowid
                    # Dialog başlığını güncelle
                    dialog.setWindowTitle("Müşteri Düzenle")
                    return temp_customer_id
                else:
                    QMessageBox.critical(dialog, "Hata", "Müşteri kaydedilemedi.")
                    return None
                    
            except Exception as e:
                QMessageBox.critical(dialog, "Hata", f"Müşteri kaydedilirken hata oluştu:\n{str(e)}")
                return None

        # Veri yükleme fonksiyonları
        def load_locations():
            """Lokasyonları yükler."""
            location_table.setRowCount(0)
            current_cust_id = temp_customer_id
            if not current_cust_id:
                return
            try:
                locations = self.db.fetch_all("""
                    SELECT id, location_name, address, phone, email
                    FROM customer_locations
                    WHERE customer_id = ?
                    ORDER BY location_name
                """, (current_cust_id,))
                
                for location in locations:
                    row = location_table.rowCount()
                    location_table.insertRow(row)
                    location_table.setItem(row, 0, QTableWidgetItem(str(location['id'])))
                    location_table.setItem(row, 1, QTableWidgetItem(location['location_name'] or ''))
                    location_table.setItem(row, 2, QTableWidgetItem(location['address'] or ''))
                    location_table.setItem(row, 3, QTableWidgetItem(location['phone'] or ''))
            except Exception as e:
                QMessageBox.warning(dialog, "Veri Hatası", f"Lokasyonlar yüklenirken hata: {e}")

        def load_devices(location_id=None):
            """Müşteriye ait cihazları yükler. location_id verilirse o lokasyona ait cihazları filtreler."""
            device_table.setRowCount(0)
            current_cust_id = temp_customer_id
            if not current_cust_id:
                return
            try:
                if location_id:
                    # Sadece seçili lokasyona ait cihazları göster
                    devices = self.db.fetch_all("""
                        SELECT cd.id, cd.device_model, cd.serial_number, 
                               COALESCE(cl.location_name, 'Lokasyon Yok') as location_name,
                               cd.device_type, cd.is_cpc
                        FROM customer_devices cd
                        LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                        WHERE cd.customer_id = ? AND cd.location_id = ?
                        ORDER BY cd.device_model
                    """, (current_cust_id, location_id))
                else:
                    # Lokasyon seçili değilse, müşteriye ait tüm cihazları göster
                    devices = self.db.fetch_all("""
                        SELECT cd.id, cd.device_model, cd.serial_number, 
                               COALESCE(cl.location_name, 'Lokasyon Yok') as location_name,
                               cd.device_type, cd.is_cpc
                        FROM customer_devices cd
                        LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                        WHERE cd.customer_id = ?
                        ORDER BY cd.device_model
                    """, (current_cust_id,))
                
                for device in devices:
                    row = device_table.rowCount()
                    device_table.insertRow(row)
                    device_table.setItem(row, 0, QTableWidgetItem(str(device['id'])))
                    device_table.setItem(row, 1, QTableWidgetItem(device['device_model'] or ''))
                    device_table.setItem(row, 2, QTableWidgetItem(device['serial_number'] or ''))
                    device_table.setItem(row, 3, QTableWidgetItem(device['location_name'] or 'Lokasyon Yok'))
                    # Renk Tipi: Sadece device_type gösterilecek
                    renk_tipi = device['device_type'] if 'device_type' in device.keys() and device['device_type'] else ''
                    device_table.setItem(row, 4, QTableWidgetItem(renk_tipi))
                    # CPC: Sadece is_cpc alanı 1 ise "Evet", değilse "Hayır" gösterilecek (renk tipiyle ilgisi yok)
                    cpc_val = device['is_cpc'] if 'is_cpc' in device.keys() else 0
                    cpc_text = "Evet" if int(cpc_val) == 1 else "Hayır"
                    device_table.setItem(row, 5, QTableWidgetItem(cpc_text))
            except Exception as e:
                QMessageBox.warning(dialog, "Veri Hatası", f"Cihazlar yüklenirken hata: {e}")

        # Sinyal bağlamaları
        def add_location():
            """Yeni lokasyon ekler."""
            # Önce müşteriyi kaydet
            cust_id = ensure_customer_saved()
            if not cust_id:
                return
            
            # Kod bloğu içeride olmalı
            from ui.dialogs.location_dialog import LocationDialog
            loc_dialog = LocationDialog(customer_id=cust_id, parent=dialog)
            if loc_dialog.exec() == QDialog.DialogCode.Accepted:
                load_locations()

        def edit_location():
            """Seçili lokasyonu düzenler."""
            # Önce müşteriyi kaydet
            cust_id = ensure_customer_saved()
            if not cust_id:
                return
            
            current_row = location_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(dialog, "Uyarı", "Lütfen düzenlemek istediğiniz lokasyonu seçin.")
                return
            
            item = location_table.item(current_row, 0)
            if not item:
                return
            location_id = int(item.text())
            from ui.dialogs.location_dialog import LocationEditDialog
            loc_dialog = LocationEditDialog(customer_id=cust_id, location_id=location_id, parent=dialog)
            if loc_dialog.exec() == QDialog.DialogCode.Accepted:
                load_locations()

        def delete_location():
            """Seçili lokasyonu siler."""
            current_row = location_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(dialog, "Uyarı", "Lütfen silmek istediğiniz lokasyonu seçin.")
                return
            
            item = location_table.item(current_row, 0)
            if not item:
                return
            location_id = int(item.text())
            item_name = location_table.item(current_row, 1)
            location_name = item_name.text() if item_name else ""
            
            # Bu lokasyonda cihaz var mı kontrol et
            device_count = self.db.fetch_one("""
                SELECT COUNT(*) as count FROM customer_devices WHERE location_id = ?
            """, (location_id,))
            
            if device_count and device_count['count'] > 0:
                QMessageBox.warning(dialog, "Silinemez",
                                  f"'{location_name}' lokasyonunda {device_count['count']} cihaz bulunmaktadır.\n"
                                  "Lokasyonu silmeden önce bu cihazları başka bir lokasyona taşımalısınız.")
                return
            
            reply = QMessageBox.question(dialog, "Onay",
                                       f"'{location_name}' lokasyonunu silmek istediğinizden emin misiniz?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.db.execute_query("DELETE FROM customer_locations WHERE id = ?", (location_id,))
                    QMessageBox.information(dialog, "Başarılı", "Lokasyon başarıyla silindi.")
                    load_locations()
                except Exception as e:
                    QMessageBox.critical(dialog, "Hata", f"Lokasyon silinirken hata oluştu:\n{str(e)}")

        def open_location_devices():
            """Seçili lokasyona ait cihazları yönetmek için dialog açar."""
            # Önce müşteriyi kaydet
            cust_id = ensure_customer_saved()
            if not cust_id:
                return
            
            current_row = location_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(dialog, "Uyarı", "Lütfen bir lokasyon seçin.")
                return
            
            item = location_table.item(current_row, 0)
            if not item:
                return
            location_id = int(item.text())
            item_name = location_table.item(current_row, 1)
            location_name = item_name.text() if item_name else ""
            
            # LocationDeviceDialog'u aç
            from ui.dialogs.location_device_dialog import LocationDeviceDialog
            loc_dev_dialog = LocationDeviceDialog(
                self.db, 
                cust_id, 
                location_id, 
                location_name, 
                parent=dialog
            )
            loc_dev_dialog.exec()
            # Dialog kapandıktan sonra cihaz listesini yenile
            load_devices()

        # Cihaz lokasyonu değiştirme fonksiyonu (dialog içindeki cihaz tablosu için)
        def change_device_location_in_dialog():
            """Seçili cihazın lokasyonunu değiştirmek için dialog açar."""
            selected_location_id = None
            current_row = device_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(dialog, "Uyarı", "Lütfen lokasyonunu değiştirmek istediğiniz cihazı seçin.")
                return
            
            # Cihaz bilgilerini al
            device_id_item = device_table.item(current_row, 0)
            device_model_item = device_table.item(current_row, 1)
            device_serial_item = device_table.item(current_row, 2)
            
            if not device_id_item:
                return
            
            device_id = int(device_id_item.text())
            device_model = device_model_item.text() if device_model_item else "Bilinmiyor"
            device_serial = device_serial_item.text() if device_serial_item else "Yok"
            
            # Müşteri ID'sini al
            current_cust_id = temp_customer_id
            if not current_cust_id:
                QMessageBox.warning(dialog, "Uyarı", "Müşteri bilgisi bulunamadı.")
                return
            
            # Müşteriye ait lokasyonları getir
            try:
                locations = self.db.fetch_all("""
                    SELECT id, location_name 
                    FROM customer_locations 
                    WHERE customer_id = ?
                    ORDER BY location_name
                """, (current_cust_id,))
                
                if not locations:
                    QMessageBox.information(dialog, "Bilgi", 
                        "Bu müşteriye ait lokasyon bulunamadı.\n"
                        "Önce 'Lokasyonlar' sekmesinden lokasyon ekleyin.")
                    return
                
                # Lokasyon seçim dialogu oluştur
                location_dialog = QDialog(dialog)
                location_dialog.setWindowTitle(f"Cihaz Lokasyonunu Değiştir - {device_model}")
                location_dialog.resize(500, 400)
                
                loc_layout = QVBoxLayout(location_dialog)
                
                # Bilgi etiketi
                info_label = QLabel(
                    f"<b>Cihaz:</b> {device_model}<br>"
                    f"<b>Seri No:</b> {device_serial}<br><br>"
                    f"Yeni lokasyon seçin:"
                )
                info_label.setWordWrap(True)
                loc_layout.addWidget(info_label)
                
                # Lokasyon listesi
                location_list = QListWidget()
                for location in locations:
                    item = QListWidgetItem(location['location_name'])
                    item.setData(Qt.ItemDataRole.UserRole, location['id'])
                    location_list.addItem(item)
                
                loc_layout.addWidget(location_list)
                
                # Butonlar
                button_box = QDialogButtonBox(
                    QDialogButtonBox.StandardButton.Ok | 
                    QDialogButtonBox.StandardButton.Cancel
                )
                button_box.accepted.connect(location_dialog.accept)
                button_box.rejected.connect(location_dialog.reject)
                loc_layout.addWidget(button_box)
                
                # Dialog'u göster
                if location_dialog.exec() == QDialog.DialogCode.Accepted:
                    selected_item = location_list.currentItem()
                    if not selected_item:
                        QMessageBox.warning(dialog, "Uyarı", "Lütfen bir lokasyon seçin.")
                        return
                    
                    new_location_id = selected_item.data(Qt.ItemDataRole.UserRole)
                    new_location_name = selected_item.text()
                    
                    # Lokasyonu güncelle
                    try:
                        self.db.execute_query("""
                            UPDATE customer_devices 
                            SET location_id = ?
                            WHERE id = ?
                        """, (new_location_id, device_id))
                        
                        QMessageBox.information(dialog, "Başarılı", 
                            f"{device_model} cihazı '{new_location_name}' lokasyonuna taşındı.")
                        
                        # Cihaz listesini yenile
                        load_devices(selected_location_id)
                        
                    except Exception as e:
                        QMessageBox.critical(dialog, "Hata", 
                            f"Cihaz lokasyonu güncellenirken hata oluştu:\n{str(e)}")
                        
            except Exception as e:
                QMessageBox.critical(dialog, "Hata", 
                    f"Lokasyonlar yüklenirken hata oluştu:\n{str(e)}")
        
        # Sinyal bağlamaları
        add_location_btn.clicked.connect(add_location)
        edit_location_btn.clicked.connect(edit_location)
        delete_location_btn.clicked.connect(delete_location)
        refresh_location_btn.clicked.connect(lambda: load_locations())
        
        # Çift tıklama sinyalleri
        location_table.itemDoubleClicked.connect(lambda: open_location_devices())
        device_table.itemDoubleClicked.connect(change_device_location_in_dialog)  # Cihaz tablosu için double-click
        

        # Lokasyon seçimi değiştiğinde cihazları filtrele
        selected_location_id = None
        def on_location_selected():
            nonlocal selected_location_id
            current_row = location_table.currentRow()
            
            # Önce item'ı None olarak tanımlayalım ki hata almayalım
            item = None
            
            if current_row >= 0:
                item = location_table.item(current_row, 0)

            if item:
                selected_location_id = int(item.text())
            else:
                selected_location_id = None
             
            load_devices(selected_location_id)
            
        location_table.itemSelectionChanged.connect(on_location_selected)
        
        # Sekme değiştiğinde otomatik kaydetme
        def on_tab_changed(index):
            """Lokasyon veya Cihazlar sekmesine geçildiğinde müşteriyi otomatik kaydet."""
            
            # Önce cust_id'yi mevcut temp_customer_id olarak varsayalım
            cust_id = temp_customer_id
            
            # Eğer Lokasyon (1) veya Cihazlar (2) sekmesine geçiliyorsa 
            # VE henüz bir müşteri ID'si yoksa (yeni müşteri ise) kaydetmeyi dene
            if index in [1, 2] and not cust_id: 
                cust_id = ensure_customer_saved()
            
            # Eğer sonuçta geçerli bir ID varsa verileri yükle
            # (Hem yeni kaydedilen hem de zaten var olan müşteriler için çalışır)
            if cust_id:
                load_locations()
                load_devices()
        
        tab_widget.currentChanged.connect(on_tab_changed)

        # Girinti tab_widget ile aynı hizada olmalı
        if is_editing:
            customer_data = self.db.fetch_one("SELECT name, phone, email, address, tax_office, tax_id, is_contract, contract_start_date, contract_end_date, contract_period, contract_price, contract_currency FROM customers WHERE id = ?", (customer_id,))
            if customer_data:
                name_input.setText(customer_data['name'] or "")
                phone_input.setText(customer_data['phone'] or "")
                email_input.setText(customer_data['email'] or "")
                address_input.setText(customer_data['address'] or "")
                tax_office_input.setText(customer_data['tax_office'] or "")
                tax_number_input.setText(customer_data['tax_id'] or "")
                
                # Sözleşme bilgilerini yükle
                is_contract = customer_data['is_contract']
                if is_contract and int(is_contract) == 1:
                    is_contract_combo.setCurrentText("Evet")
                    contract_start_str = customer_data['contract_start_date']
                    contract_end_str = customer_data['contract_end_date']
                    
                    if contract_start_str:
                        start_date = QDate.fromString(str(contract_start_str), "yyyy-MM-dd")
                        if start_date.isValid():
                            contract_start_date.setDate(start_date)
                    if contract_end_str:
                        end_date = QDate.fromString(str(contract_end_str), "yyyy-MM-dd")
                        if end_date.isValid():
                            contract_end_date.setDate(end_date)
                    if customer_data[9]:  # contract_period
                        contract_period_combo.setCurrentText(customer_data[9])
                    if customer_data[10] is not None:  # contract_price
                        contract_price_input.setText(str(customer_data[10]))
                    if len(customer_data) > 11 and customer_data[11] is not None:  # contract_currency
                        contract_currency_combo.setCurrentText(customer_data[11])
                    else:
                        contract_currency_combo.setCurrentText("TL")  # Varsayılan
                else:
                    is_contract_combo.setCurrentText("Hayır")
                toggle_contract_fields()
            
            # Lokasyon ve cihaz verilerini yükle
            load_locations()
            load_devices()
            
            # Lokasyon ve cihaz verilerini yükle
            load_locations()
            load_devices()

        def save_customer():
            nonlocal temp_customer_id
            
            # Zorunlu alan kontrolleri
            if not name_input.text().strip():
                QMessageBox.warning(dialog, "Uyarı", "Ad Soyad alanı zorunludur!")
                return
            
            if not phone_input.text().strip():
                QMessageBox.warning(dialog, "Uyarı", "Telefon alanı zorunludur!")
                return
            
            # Email normalize et (son kontrol)
            normalized_email = normalize_email(email_input.text())
            
            if name_input.text():
                try:
                    # Sözleşme tarihleri
                    start_date_str = None
                    end_date_str = None
                    if is_contract_combo.currentText() == "Evet":
                        start_date_str = contract_start_date.date().toString("yyyy-MM-dd")
                        end_date_str = contract_end_date.date().toString("yyyy-MM-dd")
                    
                    contract_period_value = contract_period_combo.currentText() if is_contract_combo.currentText() == "Evet" else None
                    contract_price_value = float(contract_price_input.text() or 0) if is_contract_combo.currentText() == "Evet" else 0
                    contract_currency_value = contract_currency_combo.currentText() if is_contract_combo.currentText() == "Evet" else "TL"

                    params = (
                        name_input.text().strip(),
                        phone_input.text().strip(),
                        normalized_email,  # Normalize edilmiş email
                        address_input.toPlainText().strip(),
                        tax_office_input.text().strip(),
                        tax_number_input.text().strip(),
                        1 if is_contract_combo.currentText() == "Evet" else 0,
                        start_date_str,
                        end_date_str,
                        contract_period_value,
                        contract_price_value,
                        contract_currency_value
                    )
                    
                    # Eğer yeni müşteri ise ve zaten geçici kaydedilmişse (temp_customer_id varsa), güncelle
                    if temp_customer_id:
                        self.db.execute_query("UPDATE customers SET name=?, phone=?, email=?, address=?, tax_office=?, tax_id=?, is_contract=?, contract_start_date=?, contract_end_date=?, contract_period=?, contract_price=?, contract_currency=? WHERE id=?", params + (temp_customer_id,))
                    elif is_editing:
                        # Düzenleme modunda
                        self.db.execute_query("UPDATE customers SET name=?, phone=?, email=?, address=?, tax_office=?, tax_id=?, is_contract=?, contract_start_date=?, contract_end_date=?, contract_period=?, contract_price=?, contract_currency=? WHERE id=?", params + (customer_id,))
                    else:
                        # Yeni müşteri ve henüz geçici kaydedilmemiş (bu durum oluşmamalı ama güvenlik için)
                        lastrowid = self.db.execute_query("INSERT INTO customers (name, phone, email, address, tax_office, tax_id, is_contract, contract_start_date, contract_end_date, contract_period, contract_price, contract_currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
                        if lastrowid:
                            temp_customer_id = lastrowid
                    
                    QMessageBox.information(dialog, "Başarılı", "Müşteri bilgileri başarıyla kaydedildi.")
                    dialog.accept()
                except Exception as e:
                    QMessageBox.critical(dialog, "Veritabanı Hatası", f"Müşteri kaydedilirken bir hata oluştu.\n\nDetay: {e}")

        buttons.accepted.disconnect()
        buttons.accepted.connect(save_customer)

        # Dialog'u çalıştır
        result = dialog.exec()
        
        # Dialog kapatıldığında ana pencereyi güncelle
        if result == QDialog.DialogCode.Accepted:
            self.refresh_customers()
            self.data_changed.emit()

    def edit_selected_customer(self, item):
        """Seçili müşteriyi düzenleme diyalogunu açar."""
        # Çift tıklanan satırdan müşteri ID'sini al
        row = item.row()
        customer_id_item = self.customer_table.item(row, 0)
        if customer_id_item:
            customer_id = int(customer_id_item.text())
            self.open_customer_dialog(customer_id=customer_id)
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek istediğiniz müşteriyi seçin.")

    def refresh_customers(self):
        """Müşteri listesini veritabanından yeniler."""
        from PyQt6.QtCore import QDate
        from PyQt6.QtGui import QColor
        
        self.customer_table.setRowCount(0)
        try:
            customers = self.db.fetch_all(
                "SELECT id, name, is_contract, contract_start_date, contract_end_date FROM customers ORDER BY name"
            )
            current_date = QDate.currentDate()
            
            for row_data in customers:
                customer_id, name, is_contract, start_date, end_date = row_data
                
                # Durumu belirle
                status = "Ücretli"
                start_str = ""
                end_str = ""
                row_color = None
                
                if is_contract:
                    status = "Sözleşmeli"
                    if start_date:
                        start_str = start_date
                    if end_date:
                        end_str = end_date
                        
                        # Renk kodlaması
                        end_date_obj = QDate.fromString(end_date, "yyyy-MM-dd")
                        if end_date_obj.isValid():
                            days_left = current_date.daysTo(end_date_obj)
                            if days_left < 0:  # Süresi dolmuş
                                row_color = QColor(255, 200, 200)  # Açık kırmızı
                            elif days_left <= 30:  # 30 günden az
                                row_color = QColor(255, 255, 200)  # Açık sarı
                
                # Satırı tabloya ekle
                row_index = self.customer_table.rowCount()
                self.customer_table.insertRow(row_index)
                
                items = [
                    QTableWidgetItem(str(customer_id)),
                    QTableWidgetItem(name),
                    QTableWidgetItem(status),
                    QTableWidgetItem(start_str),
                    QTableWidgetItem(end_str)
                ]
                
                for col, item in enumerate(items):
                    if row_color:
                        item.setBackground(row_color)
                    self.customer_table.setItem(row_index, col, item)
        
        except Exception as e:
            QMessageBox.warning(self, "Veri Hatası", f"Müşteriler yüklenemedi: {e}")

    def refresh_devices(self):
        """Seçili müşteriye ait cihazları yeniler (lokasyon filtresi ile)."""
        self.device_table.setRowCount(0)
        if not self.selected_customer_id:
            return
        try:
            # Seçili müşteriye ait cihazları çek (lokasyon filtresi ile)
            if self.selected_location_id:
                # Sadece seçili lokasyona ait cihazları göster
                devices = self.db.fetch_all("""
                    SELECT cd.id, cd.device_model, cd.serial_number, 
                           COALESCE(cl.location_name, 'Lokasyon Yok') as location_name, 
                           cd.device_type, cd.color_type, cd.is_cpc
                    FROM customer_devices cd
                    LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                    WHERE cd.customer_id = ? AND cd.location_id = ?
                    ORDER BY cd.device_model
                """, (self.selected_customer_id, self.selected_location_id))
            else:
                # Lokasyon seçili değilse, müşteriye ait tüm cihazları göster
                devices = self.db.fetch_all("""
                    SELECT cd.id, cd.device_model, cd.serial_number, 
                           COALESCE(cl.location_name, 'Lokasyon Yok') as location_name, 
                           cd.device_type, cd.color_type, cd.is_cpc
                    FROM customer_devices cd
                    LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                    WHERE cd.customer_id = ?
                    ORDER BY cl.location_name, cd.device_model
                """, (self.selected_customer_id,))
                
            for device in devices:
                # is_cpc değerini düzgün boolean'a çevir (SQLite 0/1 döndürüyor)
                is_cpc_raw = device['is_cpc'] if 'is_cpc' in device.keys() else 0
                is_cpc_value = bool(is_cpc_raw)

                # Renk Tipi bilgisini belirle (öncelik color_type, yoksa device_type)
                renk_tipi = device['color_type'] if 'color_type' in device.keys() and device['color_type'] else (device['device_type'] if 'device_type' in device.keys() and device['device_type'] else '')

                # Tabloya ekle: ID, Model, Seri No, Lokasyon, Renk Tipi, CPC
                row_data = (
                    device['id'],
                    device['device_model'] or '',
                    device['serial_number'] or '',
                    device['location_name'],
                    renk_tipi,
                    is_cpc_value
                )
                self._add_row_to_table(self.device_table, row_data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Veri Hatası", f"Cihazlar yüklenemedi: {e}")

    def load_devices(self):
        """refresh_devices için alias."""
        self.refresh_devices()

    def refresh_locations(self):
        """Seçili müşteriye ait lokasyon listesini yeniler."""
        self.location_table.setRowCount(0)
        if not self.selected_customer_id:
            return
        try:
            locations = self.db.fetch_all("""
                SELECT id, location_name, address, phone, email
                FROM customer_locations
                WHERE customer_id = ?
                ORDER BY location_name
            """, (self.selected_customer_id,))
            for location in locations:
                row_data = [
                    location['id'],
                    location['location_name'],
                    location['address'],
                    location['phone'],
                    location['email']
                ]
                self._add_row_to_table(self.location_table, tuple(row_data))
        except Exception as e:
            QMessageBox.warning(self, "Veri Hatası", f"Lokasyonlar yüklenemedi: {e}")

    def manage_selected_location(self):
        """Seçili lokasyonu düzenleme dialogunu açar."""
        if not self.selected_location_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek istediğiniz lokasyonu seçin.")
            return
        from ui.dialogs.location_dialog import LocationEditDialog
        dialog = LocationEditDialog(customer_id=self.selected_customer_id, location_id=self.selected_location_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_locations()

    def open_location_management_dialog(self):
        """Lokasyon yönetimi dialogunu açar."""
        if not self.selected_customer_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir müşteri seçin.")
            return

        from ui.dialogs.location_dialog import LocationDialog
        dialog = LocationDialog(self.selected_customer_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_locations()

    def _find_customers_by_device_info(self, search_text, search_type="all"):
        """Verilen kriterlere göre müşteri ID'lerini bulur."""
        if len(search_text) < 2:  # En az 2 karakter girilmişse arama yap
            return set()
            
        search_text = f'%{search_text.lower()}%'
        query = """
            SELECT DISTINCT c.id
            FROM customers c
            LEFT JOIN customer_devices cd ON c.id = cd.customer_id
            WHERE 1=1
        """
        params = []
        
        if search_type == "all":
            query += """
                AND (LOWER(c.name) LIKE ? 
                     OR LOWER(cd.device_model) LIKE ? 
                     OR LOWER(cd.serial_number) LIKE ?)
            """
            params = [search_text, search_text, search_text]
        elif search_type == "customer":
            query += " AND LOWER(c.name) LIKE ?"
            params = [search_text]
        elif search_type == "device":
            query += " AND LOWER(cd.device_model) LIKE ?"
            params = [search_text]
        elif search_type == "serial":
            query += " AND LOWER(cd.serial_number) LIKE ?"
            params = [search_text]
            
        query += " ORDER BY c.name"
        
        results = self.db.fetch_all(query, params)
        return {row['id'] for row in results} if results else set()
        
    def filter_customers(self):
        """Müşteri listesini arama kutusuna göre filtreler."""
        search_text = self.customer_filter_input.text().strip()
        search_type = self.search_type_combo.currentData()
        
        # Arama metni yoksa tüm müşterileri göster
        if not search_text:
            for row in range(self.customer_table.rowCount()):
                self.customer_table.setRowHidden(row, False)
            return
            
        # Arama yap
        customer_ids = self._find_customers_by_device_info(search_text, search_type)
        
        # Sonuçları filtrele
        for row in range(self.customer_table.rowCount()):
            customer_id_item = self.customer_table.item(row, 0)
            if not customer_id_item:
                continue
                
            customer_id = int(customer_id_item.text())
            
            # Eğer arama sonucunda müşteri ID'si bulunduysa göster, değilse gizle
            self.customer_table.setRowHidden(row, customer_id not in customer_ids)

    def show_contract_customers(self):
        """Sadece sözleşmeli müşterileri gösterir."""
        for row in range(self.customer_table.rowCount()):
            status_item = self.customer_table.item(row, 2)
            if status_item:
                is_contract = status_item.text() == "Sözleşmeli"
                self.customer_table.setRowHidden(row, not is_contract)

    def show_all_customers(self):
        """Tüm müşterileri gösterir."""
        for row in range(self.customer_table.rowCount()):
            self.customer_table.setRowHidden(row, False)

    def clear_edit_form(self):
        """Cihaz düzenleme formundaki tüm alanları temizler."""
        self.model_input.clear()
        self.serial_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.is_cpc_combo.setCurrentIndex(0)
        self.bw_price_input.setText("0.0000")
        self.color_price_input.setText("0.0000")
        self.bw_currency_combo.setCurrentIndex(0)
        self.color_currency_combo.setCurrentIndex(0)

    def toggle_price_fields(self):
        """'Kopya Başı mı?' seçimine göre fiyat alanlarını gösterir/gizler."""
        is_cpc = 1 if self.is_cpc_combo.currentText() == "Evet" else 0
        self.bw_price_label.setVisible(is_cpc)
        self.bw_price_input.setVisible(is_cpc)
        self.bw_currency_combo.setVisible(is_cpc)
        self.toggle_color_price_field()

    def toggle_color_price_field(self):
        """Cihaz türüne göre renkli fiyat alanını gösterir/gizler."""
        is_cpc = self.is_cpc_combo.currentText() == "Evet"
        is_color_device = self.type_combo.currentText() == "Renkli"
        is_visible = is_cpc and is_color_device
        self.color_price_label.setVisible(is_visible)
        self.color_price_input.setVisible(is_visible)
        self.color_currency_combo.setVisible(is_visible)

    def _add_row_to_table(self, table: QTableWidget, data: tuple):
        """Verilen tabloya yeni bir satır ve veri ekler."""
        row_count = table.rowCount()
        table.insertRow(row_count)
        for col_index, value in enumerate(data):
            # CPC kolonunu (5. kolon) özel işle
            if col_index == 5 and table == self.device_table:  # CPC kolonu
                cpc_text = "✅ Evet" if value else "❌ Hayır"
                item = QTableWidgetItem(cpc_text)
                item.setToolTip("Sayfa başına ücret sistemi aktif" if value else "Sayfa başına ücret sistemi değil")
                table.setItem(row_count, col_index, item)
            else:
                item = QTableWidgetItem(str(value))
                # Uzun metinler için tooltip ekle
                if len(str(value)) > 20:
                    item.setToolTip(str(value))
                table.setItem(row_count, col_index, item)
            
    def refresh_data(self):
        """Sekme verilerini yenilemek için ana arayüz tarafından çağrılır."""
        current_customer_id = self.selected_customer_id
        self.refresh_customers()
        if current_customer_id:
            # Eğer önceden bir müşteri seçiliyse, onu tekrar bul ve seç
            for row in range(self.customer_table.rowCount()):
                item = self.customer_table.item(row, 0)
                if item and int(item.text()) == current_customer_id:
                    self.customer_table.selectRow(row)
                    break
        else:
            # Seçili müşteri yoksa, cihaz listesini temizle
            self.device_table.setRowCount(0)

    def delete_selected_device(self):
        """Seçili cihazı siler."""
        if not self.selected_device_id:
            QMessageBox.warning(self, "Seçim Hatası", "Lütfen silmek istediğiniz cihazı seçin.")
            return
        
        # Cihaz bilgilerini al
        device_data = self.db.get_customer_device(self.selected_device_id)
        
        if not device_data:
            QMessageBox.critical(self, "Hata", "Cihaz bilgileri bulunamadı.")
            return
        
        model = device_data['device_model'] if 'device_model' in device_data else ''
        serial_number = device_data['serial_number'] if 'serial_number' in device_data else ''
        
        # Onay mesajı
        reply = QMessageBox.question(
            self, 
            "Cihaz Silme Onayı", 
            f"'{model}' ({serial_number}) cihazını silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Cihazı sil
            success = self.db.delete_customer_device(self.selected_device_id)
            
            if success:
                # UI'yi güncelle
                self.selected_device_id = None
                self.refresh_devices()
                self.data_changed.emit()
                
                self.status_bar.showMessage(f"Cihaz '{model}' ({serial_number}) başarıyla silindi.", 3000)
            else:
                QMessageBox.critical(self, "Silme Hatası", "Cihaz silinirken bir hata oluştu.")
            
        except Exception as e:
            QMessageBox.critical(self, "Silme Hatası", f"Cihaz silinirken bir hata oluştu:\n\n{e}")

    def delete_selected_customer(self):
        """Seçili müşteriyi siler."""
        if not self.selected_customer_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek müşteriyi seçin.")
            return
        
        # Admin kontrolü
        if self.user_role.lower() != "admin":
            QMessageBox.warning(self, "Yetki Hatası", "Müşteri silme işlemi sadece admin kullanıcıları tarafından yapılabilir.")
            return
        
        try:
            # Müşteri bilgilerini al
            customer_query = "SELECT name FROM customers WHERE id = ?"
            customer_data = self.db.fetch_one(customer_query, (self.selected_customer_id,))
            
            if not customer_data:
                QMessageBox.warning(self, "Hata", "Müşteri bulunamadı.")
                return
            
            customer_name = customer_data['name']
            
            # Müşteriye ait cihaz sayısını kontrol et (customer_devices tablosundan)
            device_count_query = "SELECT COUNT(*) as count FROM customer_devices WHERE customer_id = ?"
            device_count = self.db.fetch_one(device_count_query, (self.selected_customer_id,))['count']
            
            # Müşteriye ait servis kayıtlarını kontrol et
            service_count_query = """
                SELECT COUNT(*) as count FROM service_records sr
                JOIN devices d ON sr.device_id = d.id
                WHERE d.customer_id = ?
            """
            service_count = self.db.fetch_one(service_count_query, (self.selected_customer_id,))['count']
            
            # Müşteriye ait fatura sayısını kontrol et
            invoice_count_query = "SELECT COUNT(*) as count FROM invoices WHERE customer_id = ?"
            invoice_count = self.db.fetch_one(invoice_count_query, (self.selected_customer_id,))['count']
            
            # Uyarı mesajı oluştur
            warning_msg = f"'{customer_name}' müşterisini silmek istediğinizden emin misiniz?\n\n"
            warning_msg += f"Bu müşteriye ait:\n"
            warning_msg += f"• {device_count} adet cihaz\n"
            warning_msg += f"• {service_count} adet servis kaydı\n"
            warning_msg += f"• {invoice_count} adet fatura\n\n"
            warning_msg += "Bu işlem GERİ ALINAMAZ ve tüm ilişkili veriler silinecektir!"
            
            reply = QMessageBox.question(
                self, 
                "Müşteri Silme Onayı", 
                warning_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Müşteriyi ve tüm ilişkili verileri sil
            conn = self.db.get_connection()
            if not conn:
                QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı kurulamadı.")
                return
            
            with conn:
                cursor = conn.cursor()
                
                # 1. Müşteriye ait cihazların servis kayıtlarını sil
                cursor.execute("""
                    DELETE FROM service_records 
                    WHERE device_id IN (SELECT id FROM devices WHERE customer_id = ?)
                """, (self.selected_customer_id,))
                
                # 2. Müşteriye ait cihazları sil (customer_devices tablosundan)
                cursor.execute("DELETE FROM customer_devices WHERE customer_id = ?", (self.selected_customer_id,))
                
                # 3. Müşteriye ait ödemeleri sil
                cursor.execute("""
                    DELETE FROM payments 
                    WHERE invoice_id IN (SELECT id FROM invoices WHERE customer_id = ?)
                """, (self.selected_customer_id,))
                
                # 4. Müşteriye ait faturaları sil
                cursor.execute("DELETE FROM invoices WHERE customer_id = ?", (self.selected_customer_id,))
                
                # 5. Müşteriyi sil
                cursor.execute("DELETE FROM customers WHERE id = ?", (self.selected_customer_id,))
            
            # Arayüzü güncelle
            self.selected_customer_id = None
            self.selected_device_id = None
            self.refresh_customers()
            self.device_table.setRowCount(0)
            self.delete_customer_btn.setEnabled(False)
            
            # Değişiklik sinyali gönder
            self.data_changed.emit()
            
            self.status_bar.showMessage(f"Müşteri '{customer_name}' ve tüm ilişkili veriler başarıyla silindi.", 5000)
            
        except Exception as e:
            QMessageBox.critical(self, "Silme Hatası", f"Müşteri silinirken bir hata oluştu:\n\n{e}")

    def edit_selected_device(self):
        """Seçili cihazı düzenleme dialog'unu açar."""
        # Çift tıklama için seçili satırdan device_id'yi al
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek istediğiniz cihazı seçin.")
            return

        device_id = int(self.device_table.item(selected_rows[0].row(), 0).text())

        from ui.dialogs.device_dialog import DeviceDialog
        dialog = DeviceDialog(self.db, self.selected_customer_id, device_id=device_id, parent=self)
        if dialog.exec():
            self.refresh_devices()
            self.data_changed.emit()
