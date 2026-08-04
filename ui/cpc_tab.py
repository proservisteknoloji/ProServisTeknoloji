# ui/cpc_tab.py

"""
CPC (Kopya Başı Ücret) müşterileri için özel toner sipariş sekmesi.
Müşteri cihazlarına göre otomatik toner önerisi ve bedelsiz çıkış sistemi.
"""

import logging
from utils.error_logger import log_error, log_warning, log_info
import os
from decimal import Decimal
from datetime import datetime, date
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QLabel, QFormLayout, QComboBox, QMessageBox, QGroupBox, 
                             QTextEdit, QSpinBox, QDateEdit, QFrame, QGridLayout, 
                             QFileDialog)
from PyQt6.QtCore import pyqtSignal as Signal, Qt, QDate, QTimer
from utils.predefined_stock import (
    get_compatible_toners_for_device, 
    get_compatible_kits_for_device,
    get_compatible_spare_parts_for_device,
    get_compatible_products_for_device
)
from utils.database import db_manager
from utils.pdf_generator import generate_cpc_order_pdf

class CPCTab(QWidget):
    """CPC müşteriler için toner sipariş sekmesi."""
    data_changed = Signal()

    def __init__(self, db, status_bar, user_role=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.status_bar = status_bar
        self.user_role = user_role or "user"
        self.selected_customer_id = None
        self.selected_device_id = None
        self.current_product_type = 'all'
        self.current_order_items = []
        
        # Filtreleme için timer (debounce özelliği)
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.filter_customers)
        
        self.init_ui()
        self.refresh_cpc_customers()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        main_layout = QVBoxLayout(self)
        
        # Üst panel: CPC müşteri seçimi
        customer_panel = self._create_customer_selection_panel()
        main_layout.addWidget(customer_panel)
        
        # Ana splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sol panel: Cihazlar ve uyumlu ürünler
        left_panel = self._create_device_and_products_panel()
        
        # Sağ panel: Sipariş detayları
        right_panel = self._create_order_panel()
        
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([750, 400])  # Sol panel için daha fazla alan
        
        main_layout.addWidget(main_splitter)
        
        self._connect_signals()
        
    def _create_customer_selection_panel(self):
        """CPC müşteri seçim panelini oluşturur."""
        panel = QGroupBox("CPC Müşteri Seçimi")
        layout = QHBoxLayout(panel)
        
        # Müşteri filtresi
        self.customer_filter = QLineEdit()
        self.customer_filter.setPlaceholderText("CPC müşteri adında ara...")
        
        # Filtre temizleme butonu
        self.clear_filter_btn = QPushButton("✖")
        self.clear_filter_btn.setMaximumWidth(30)
        self.clear_filter_btn.setToolTip("Filtreyi temizle")
        self.clear_filter_btn.clicked.connect(self.clear_customer_filter)
        
        # Müşteri combo
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(300)
        
        # Yenile butonu
        self.refresh_customers_btn = QPushButton("🔄 Yenile")
        
        # Müşteri bilgi labelları
        self.customer_info_label = QLabel("Müşteri seçilmedi")
        self.customer_info_label.setStyleSheet("font-weight: bold; color: #666;")
        
        # Filtreleme durumu göstergesi
        self.filter_status_label = QLabel("")
        self.filter_status_label.setStyleSheet("color: #2196F3; font-size: 10px;")
        
        layout.addWidget(QLabel("Müşteri Ara:"))
        layout.addWidget(self.customer_filter)
        layout.addWidget(self.clear_filter_btn)
        layout.addWidget(QLabel("Müşteri:"))
        layout.addWidget(self.customer_combo)
        layout.addWidget(self.refresh_customers_btn)
        layout.addStretch()
        layout.addWidget(self.filter_status_label)
        layout.addWidget(self.customer_info_label)
        
        return panel
        
    def _create_device_and_products_panel(self):
        """Cihaz ve ürün panelini oluşturur."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Cihazlar bölümü
        devices_group = QGroupBox("Müşteri Cihazları")
        devices_layout = QVBoxLayout(devices_group)
        
        self.devices_table = QTableWidget(0, 4)
        self.devices_table.setHorizontalHeaderLabels(["ID", "Model", "Seri No", "Renk Tipi"])
        self.devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.devices_table.setAlternatingRowColors(True)  # Alternatif satır renkleri
        self.devices_table.setShowGrid(True)  # Grid çizgilerini göster

        # Daha iyi okunabilirlik için sütun genişliklerini optimize et
        header = self.devices_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Model - kullanıcı ayarlayabilir
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Seri No - kullanıcı ayarlayabilir
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Renk Tipi - içeriğe göre

        # Başlangıç genişlikleri ayarla
        self.devices_table.setColumnWidth(1, 250)  # Model kolonu - geniş
        self.devices_table.setColumnWidth(2, 150)  # Seri Numarası kolonu
        self.devices_table.hideColumn(0)

        # Tablo başlıklarına tooltips ekle
        for idx, tip in [(1, "Cihaz markası ve modeli - Sütun genişliğini ayarlayabilirsiniz"),
                         (2, "Cihazın seri numarası - Sütun genişliğini ayarlayabilirsiniz"),
                         (3, "Siyah-Beyaz veya Renkli")]:
            item = self.devices_table.horizontalHeaderItem(idx)
            if item is not None:
                item.setToolTip(tip)
        
        devices_layout.addWidget(self.devices_table)
        
        # Uyumlu ürünler bölümü
        products_group = QGroupBox("Seçili Cihaza Uyumlu Ürünler")
        products_layout = QVBoxLayout(products_group)
        
        # Ürün türü seçimi ve filtreleme
        product_type_layout = QHBoxLayout()
        self.show_toners_btn = QPushButton("Tonerler")
        self.show_kits_btn = QPushButton("Kitler")
        self.show_spare_parts_btn = QPushButton("Yedek Parçalar")
        self.show_all_products_btn = QPushButton("Tümü")
        
        self.show_toners_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        self.show_kits_btn.setStyleSheet("QPushButton { background-color: #9C27B0; color: white; }")
        self.show_spare_parts_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; }")
        self.show_all_products_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        
        product_type_layout.addWidget(self.show_toners_btn)
        product_type_layout.addWidget(self.show_kits_btn)
        product_type_layout.addWidget(self.show_spare_parts_btn)
        product_type_layout.addWidget(self.show_all_products_btn)
        
        # Filtreleme alanı ekle
        product_type_layout.addWidget(QLabel("🔍 Filtre:"))
        self.product_filter = QLineEdit()
        self.product_filter.setPlaceholderText("Ürün ara (yazarak filtreleyin)...")
        self.product_filter.setMaximumWidth(200)
        product_type_layout.addWidget(self.product_filter)
        
        product_type_layout.addStretch()
        
        products_layout.addLayout(product_type_layout)
        
        # Ürün tablosu
        self.products_table = QTableWidget(0, 6)  # 6 sütun (Para Birimi kaldırıldı)
        self.products_table.setHorizontalHeaderLabels(["Stok ID", "Tip", "Açıklama", "Parça No", "Stok", "Fiyat"])
        
        # Sütun genişliklerini ayarla
        header = self.products_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Stok ID
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Tip
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Açıklama (en geniş)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Parça No
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Stok
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Fiyat
        
        # Sütun genişliklerini manuel olarak ayarla
        self.products_table.setColumnWidth(0, 60)   # Stok ID
        self.products_table.setColumnWidth(1, 80)   # Tip
        self.products_table.setColumnWidth(3, 120)  # Parça No
        self.products_table.setColumnWidth(4, 60)   # Stok
        self.products_table.setColumnWidth(5, 80)   # Fiyat
        
        self.products_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.products_table.hideColumn(0)  # Stok ID gizli
        
        products_layout.addWidget(self.products_table)
        
        # Ürün ekleme paneli
        add_product_panel = self._create_add_product_panel()
        products_layout.addWidget(add_product_panel)
        
        layout.addWidget(devices_group, 1)
        layout.addWidget(products_group, 2)
        
        return panel
        
    def _create_add_product_panel(self):
        """Ürün ekleme panelini oluşturur."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QGridLayout(panel)
        
        # Miktar girişi
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(999)
        self.quantity_spin.setValue(1)
        
        # Açıklama
        self.order_note = QLineEdit()
        self.order_note.setPlaceholderText("Sipariş notu (isteğe bağlı)...")
        
        # Ekleme butonu
        self.add_to_order_btn = QPushButton("📦 Siparişe Ekle")
        self.add_to_order_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.add_to_order_btn.setEnabled(False)
        
        layout.addWidget(QLabel("Miktar:"), 0, 0)
        layout.addWidget(self.quantity_spin, 0, 1)
        layout.addWidget(QLabel("Not:"), 0, 2)
        layout.addWidget(self.order_note, 0, 3)
        layout.addWidget(self.add_to_order_btn, 0, 4)
        
        return panel
        
    def _create_order_panel(self):
        """Sipariş panelini oluşturur."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Sipariş özeti
        order_group = QGroupBox("Sipariş Detayları")
        order_layout = QVBoxLayout(order_group)
        
        # Sipariş bilgileri
        info_layout = QFormLayout()
        
        self.order_date = QDateEdit()
        self.order_date.setDate(QDate.currentDate())
        self.order_date.setCalendarPopup(True)
        
        self.order_notes = QTextEdit()
        self.order_notes.setMaximumHeight(80)
        self.order_notes.setPlaceholderText("Genel sipariş notları...")
        
        info_layout.addRow("Sipariş Tarihi:", self.order_date)
        info_layout.addRow("Notlar:", self.order_notes)
        
        order_layout.addLayout(info_layout)
        
        # Sipariş kalemleri tablosu
        self.order_items_table = QTableWidget(0, 5)
        self.order_items_table.setHorizontalHeaderLabels(["Ürün", "Parça No", "Miktar", "Birim Fiyat", "Toplam"])
        header = self.order_items_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        order_layout.addWidget(QLabel("Sipariş Kalemleri:"))
        order_layout.addWidget(self.order_items_table)
        
        # Sipariş butonları
        button_layout = QHBoxLayout()
        
        self.remove_item_btn = QPushButton("🗑️ Kaldır")
        self.remove_item_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; }")
        self.remove_item_btn.setEnabled(False)
        
        self.clear_order_btn = QPushButton("🗑️ Temizle")
        self.clear_order_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        
        self.create_order_btn = QPushButton("✅ Sipariş Oluştur (Bedelsiz Çıkış)")
        self.create_order_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.create_order_btn.setEnabled(False)
        
        button_layout.addWidget(self.remove_item_btn)
        button_layout.addWidget(self.clear_order_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.create_order_btn)
        
        order_layout.addLayout(button_layout)
        
        # Toplam bilgisi
        self.total_label = QLabel("Toplam: 0.00 TL")
        self.total_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1976D2;")
        order_layout.addWidget(self.total_label)
        
        layout.addWidget(order_group)
        
        return panel
        
    def _connect_signals(self):
        """Sinyalleri bağlar."""
        # Müşteri seçimi - debounce ile filtreleme
        self.customer_filter.textChanged.connect(self.on_customer_filter_changed)
        self.customer_combo.currentTextChanged.connect(self.on_customer_selected)
        self.refresh_customers_btn.clicked.connect(self.refresh_cpc_customers)
        
        # Cihaz seçimi
        if self.devices_table.selectionModel() is not None:
            self.devices_table.selectionModel().selectionChanged.connect(self.on_device_selected)
        
        # Ürün butonları
        self.show_toners_btn.clicked.connect(lambda: self.show_compatible_products('toner'))
        self.show_kits_btn.clicked.connect(lambda: self.show_compatible_products('kit'))
        self.show_spare_parts_btn.clicked.connect(lambda: self.show_compatible_products('spare_part'))
        self.show_all_products_btn.clicked.connect(lambda: self.show_compatible_products('all'))
        
        # Ürün filtreleme
        self.product_filter.textChanged.connect(self.filter_products_table)
        
        # Ürün seçimi ve ekleme
        if self.products_table.selectionModel() is not None:
            self.products_table.selectionModel().selectionChanged.connect(self.on_product_selected)
        self.add_to_order_btn.clicked.connect(self.add_product_to_order)
        
        # Sipariş yönetimi
        if self.order_items_table.selectionModel() is not None:
            self.order_items_table.selectionModel().selectionChanged.connect(self.on_order_item_selected)
        self.remove_item_btn.clicked.connect(self.remove_order_item)
        self.clear_order_btn.clicked.connect(self.clear_order)
        self.create_order_btn.clicked.connect(self.create_cpc_order)
        
    def refresh_cpc_customers(self):
        """CPC müşterilerini yeniler."""
        try:
            # Sadece CPC cihazı olan müşterileri getir
            query = """
                SELECT DISTINCT c.id, c.name
                FROM customers c
                WHERE EXISTS (
                    SELECT 1
                    FROM customer_devices cd
                    LEFT JOIN customer_locations cl ON cl.id = cd.location_id
                    WHERE cd.is_cpc = 1
                      AND (cd.customer_id = c.id OR cl.customer_id = c.id)
                )
                ORDER BY c.name
            """
            customers = self.db.fetch_all(query)
            
            self.customer_combo.clear()
            self.customer_combo.addItem("-- CPC Müşteri Seçin --", None)
            
            for customer in customers:
                self.customer_combo.addItem(f"{customer['name']}", customer['id'])
                
            if self.status_bar:
                self.status_bar.showMessage(f"{len(customers)} CPC müşteri yüklendi", 3000)
                
        except Exception as e:
              log_error("CPCTab", e)
              QMessageBox.critical(self, "Hata", f"CPC müşteriler yüklenirken hata oluştu:\n{str(e)}")
            
    def on_customer_filter_changed(self):
        """Müşteri filtresi değiştiğinde timer'ı başlatır (debounce)."""
        # Filtreleme durumunu göster
        filter_text = self.customer_filter.text().strip()
        if filter_text:
            self.filter_status_label.setText("🔍 Filtreleniyor...")
        else:
            self.filter_status_label.setText("")
            
        # Timer'ı durdur ve yeniden başlat (300ms gecikme)
        self.filter_timer.stop()
        self.filter_timer.start(300)
        
    def clear_customer_filter(self):
        """Müşteri filtresini temizler."""
        self.customer_filter.clear()
        self.filter_status_label.setText("")
            
    def filter_customers(self):
        """Müşteri filtrelemesi - CPC müşterilerini filtreler."""
        filter_text = self.customer_filter.text().lower().strip()
        
        try:
            # Filtrelenmiş CPC müşterilerini getir
            if filter_text:
                query = """
                    SELECT DISTINCT c.id, c.name
                    FROM customers c
                    WHERE LOWER(c.name) LIKE ?
                      AND EXISTS (
                          SELECT 1
                          FROM customer_devices cd
                          LEFT JOIN customer_locations cl ON cl.id = cd.location_id
                          WHERE cd.is_cpc = 1
                            AND (cd.customer_id = c.id OR cl.customer_id = c.id)
                      )
                    ORDER BY c.name
                """
                customers = self.db.fetch_all(query, (f"%{filter_text}%",))
            else:
                # Filtre boşsa tüm CPC müşterilerini göster
                query = """
                    SELECT DISTINCT c.id, c.name
                    FROM customers c
                    WHERE EXISTS (
                        SELECT 1
                        FROM customer_devices cd
                        LEFT JOIN customer_locations cl ON cl.id = cd.location_id
                        WHERE cd.is_cpc = 1
                          AND (cd.customer_id = c.id OR cl.customer_id = c.id)
                    )
                    ORDER BY c.name
                """
                customers = self.db.fetch_all(query)
            
            # ComboBox'ı güncelle
            current_selection = self.customer_combo.currentData()  # Mevcut seçimi sakla
            self.customer_combo.clear()
            self.customer_combo.addItem("-- CPC Müşteri Seçin --", None)
            
            for customer in customers:
                self.customer_combo.addItem(f"{customer['name']}", customer['id'])
                
            # Eğer önceki seçim hala mevcutsa geri yükle
            if current_selection:
                for i in range(self.customer_combo.count()):
                    if self.customer_combo.itemData(i) == current_selection:
                        self.customer_combo.setCurrentIndex(i)
                        break
                        
            # Status bar ve filtreleme durumunu güncelle
            if filter_text:
                self.filter_status_label.setText(f"✅ {len(customers)} müşteri bulundu")
                if self.status_bar:
                    self.status_bar.showMessage(f"'{filter_text}' araması: {len(customers)} CPC müşteri bulundu", 3000)
            else:
                self.filter_status_label.setText("")
                if self.status_bar:
                    self.status_bar.showMessage(f"{len(customers)} CPC müşteri yüklendi", 3000)
                    
        except Exception as e:
              log_error("CPCTab", e)
              self.filter_status_label.setText("❌ Hata oluştu")
              QMessageBox.critical(self, "Hata", f"Müşteri filtreleme hatası:\n{str(e)}")
            
    def on_customer_selected(self):
        """Müşteri seçildiğinde tetiklenir."""
        customer_id = self.customer_combo.currentData()
        
        if customer_id:
            self.selected_customer_id = customer_id
            customer_name = self.customer_combo.currentText()
            self.customer_info_label.setText(f"Seçili: {customer_name}")
            self.load_customer_devices()
        else:
            self.selected_customer_id = None
            self.customer_info_label.setText("Müşteri seçilmedi")
            self.clear_devices_table()
            
    def load_customer_devices(self):
        """Seçili müşterinin CPC cihazlarını yükler."""
        if not self.selected_customer_id:
            return
        try:
            query = """
                SELECT DISTINCT cd.id, cd.device_model, cd.serial_number, cd.color_type
                FROM customer_devices cd
                LEFT JOIN customer_locations cl ON cl.id = cd.location_id
                WHERE cd.is_cpc = 1
                  AND (cd.customer_id = ? OR cl.customer_id = ?)
                ORDER BY cd.device_model
            """
            devices = self.db.fetch_all(query, (self.selected_customer_id, self.selected_customer_id))
            self.devices_table.setRowCount(len(devices))
            for row, device in enumerate(devices):
                self.devices_table.setItem(row, 0, QTableWidgetItem(str(device['id'])))
                model_item = QTableWidgetItem(device['device_model'] or '')
                if device['device_model'] and len(device['device_model']) > 20:
                    model_item.setToolTip(device['device_model'])
                self.devices_table.setItem(row, 1, model_item)
                serial_item = QTableWidgetItem(device['serial_number'] or '')
                if device['serial_number'] and len(device['serial_number']) > 15:
                    serial_item.setToolTip(device['serial_number'])
                self.devices_table.setItem(row, 2, serial_item)
                self.devices_table.setItem(row, 3, QTableWidgetItem(device['color_type'] or ''))
        except Exception as e:
            log_error("CPCTab", e)
            QMessageBox.critical(self, "Hata", f"Cihazlar yüklenirken hata oluştu:\n{str(e)}")
            
    def clear_devices_table(self):
        """Cihaz tablosunu temizler."""
        self.devices_table.setRowCount(0)
        self.products_table.setRowCount(0)
        
    def on_device_selected(self):
        """Cihaz seçildiğinde tetiklenir."""
        selection_model = self.devices_table.selectionModel()
        if selection_model is None:
            return
        selected_rows = selection_model.selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            item = self.devices_table.item(row, 0)
            if item is not None:
                device_id = item.text()
                self.selected_device_id = int(device_id)
                # Seçili cihaza uyumlu ürünleri göster
                self.show_compatible_products('all')
            else:
                self.selected_device_id = None
                self.products_table.setRowCount(0)
        else:
            self.selected_device_id = None
            self.products_table.setRowCount(0)
            
    def show_compatible_products(self, product_type='all'):
        """Seçili cihaza uyumlu ürünleri gösterir."""
        self.current_product_type = product_type
        if product_type == 'spare_part':
            # Modelden bağımsız olarak tüm yedek parçaları göster
            query = """
                SELECT id, item_type, name, part_number, quantity, sale_price, sale_currency, supplier, description 
                FROM stock_items 
                WHERE item_type = 'Yedek Parça' AND quantity > 0
            """
            db_matches = self.db.fetch_all(query)
            all_compatible = []
            for match in db_matches:
                all_compatible.append({
                    'name': match['name'],
                    'part_number': match['part_number'],
                    'item_type': match['item_type'],
                    'description': match['description'] or "Yedek Parça (DB)",
                    'supplier': match['supplier'],
                    'sale_price': match['sale_price'],
                    'sale_currency': match['sale_currency']
                })
        else:
            if not self.selected_device_id:
                QMessageBox.information(self, "Bilgi", "Önce bir cihaz seçin.")
                return
            try:
                # 1. Seçili cihazın modelini al
                query = "SELECT device_model FROM customer_devices WHERE id = ?"
                device = self.db.fetch_one(query, (self.selected_device_id,))
                if not device:
                    return
                device_model = device['device_model']
                # 2. Standart (Predefined ve JSON tabanlı) uyumlu ürünleri getir
                if product_type == 'all':
                    all_compatible = get_compatible_products_for_device(device_model)
                else:
                    all_compatible = [] # Aşağıda filtreye göre doldurulacak
                # 3. YENİ MANTIK: Veritabanında 'compatible_models' eşleşmesi ile ürün bul
                # Python-side filtering to handle Turkish characters correctly
                search_terms = [device_model]
                if " " in device_model:
                    search_terms.append(device_model.split(" ")[-1]) # Sadece model kodu
                
                # Fetch all items with compatible_models field populated
                query = """
                    SELECT id, item_type, name, part_number, quantity, sale_price, sale_currency, supplier, description, compatible_models
                    FROM stock_items 
                    WHERE compatible_models IS NOT NULL AND compatible_models != '' AND quantity > 0
                """
                if product_type == 'toner':
                    query += " AND item_type = 'Toner'"
                elif product_type == 'kit':
                    query += " AND item_type = 'Kit'"
                
                db_matches = self.db.fetch_all(query)
                
                # Filter in Python for proper Turkish character handling
                for match in db_matches:
                    compatible_models = match['compatible_models'] if match['compatible_models'] else ''
                    compatible_models_lower = compatible_models.lower()
                    
                    # Check if any search term matches
                    for term in search_terms:
                        term_lower = term.lower()
                        if term_lower in compatible_models_lower:
                            # Avoid duplicates
                            if not any(item['part_number'] == match['part_number'] for item in all_compatible):
                                all_compatible.append({
                                    'name': match['name'],
                                    'part_number': match['part_number'],
                                    'item_type': match['item_type'],
                                    'description': match['description'] or f"{term} ile uyumlu (DB)",
                                    'supplier': match['supplier'],
                                    'sale_price': match['sale_price'],
                                    'sale_currency': match['sale_currency']
                                })
                            break  # Found a match, no need to check other terms for this item

                # Eşleşme tanımlanmamış tonerler için arama fallback'i
                search_text = self.product_filter.text().strip()
                if search_text and product_type in ('toner', 'all'):
                    toner_query = """
                        SELECT id, item_type, name, part_number, quantity, sale_price, sale_currency, supplier, description
                        FROM stock_items
                        WHERE item_type = 'Toner'
                          AND quantity > 0
                          AND (LOWER(name) LIKE ? OR LOWER(part_number) LIKE ?)
                    """
                    search_param = f"%{search_text.lower()}%"
                    toner_search_matches = self.db.fetch_all(toner_query, (search_param, search_param))
                    for match in toner_search_matches:
                        if not any(item['part_number'] == match['part_number'] for item in all_compatible):
                            all_compatible.append({
                                'name': match['name'],
                                'part_number': match['part_number'],
                                'item_type': match['item_type'],
                                'description': match['description'] or "Arama sonucu toner",
                                'supplier': match['supplier'],
                                'sale_price': match['sale_price'],
                                'sale_currency': match['sale_currency']
                            })
            except Exception as e:
                log_error("CPCTab", e)
                return
        # 4. Tabloyu Doldur (Gerçek stok kontrolü ile)
        self.products_table.setRowCount(0)
        for item in all_compatible:
            if product_type == 'kit' and item['item_type'] != 'Kit':
                continue
            if product_type == 'toner' and item['item_type'] != 'Toner':
                continue
            if product_type == 'spare_part' and item['item_type'] != 'Yedek Parça':
                continue
            stock_query = """
                SELECT id, quantity, sale_price, sale_currency 
                FROM stock_items 
                WHERE part_number = ?
            """
            stock_item = self.db.fetch_one(stock_query, (item['part_number'],))
            if stock_item or item['item_type'] == 'Toner':
                row = self.products_table.rowCount()
                self.products_table.insertRow(row)
                # Stok ID
                stock_id = str(stock_item['id']) if stock_item else '0'
                self.products_table.setItem(row, 0, QTableWidgetItem(stock_id))
                self.products_table.setItem(row, 1, QTableWidgetItem(item['item_type']))
                self.products_table.setItem(row, 2, QTableWidgetItem(item['name']))
                self.products_table.setItem(row, 3, QTableWidgetItem(item['part_number']))
                # Miktar
                if item['item_type'] == 'Toner':
                    if stock_item:
                        actual_quantity = stock_item['quantity'] if stock_item['quantity'] > 0 else 999
                    else:
                        actual_quantity = 999  # Stokta yoksa 999 olarak göster
                else:
                    actual_quantity = stock_item['quantity'] if stock_item else 0

                self.products_table.setItem(row, 4, QTableWidgetItem(str(actual_quantity)))

                # Fiyat
                if stock_item:
                    price_text = f"{stock_item['sale_price']:.2f} {stock_item['sale_currency']}"
                else:
                    price_text = f"{item['sale_price']:.2f} {item['sale_currency']}"
                self.products_table.setItem(row, 5, QTableWidgetItem(price_text))
                    
          # except bloğu kaldırıldı veya doğru hizaya getirildi, çünkü try bloğu yukarıda zaten var ve burada gereksizdi.
            
    def on_product_selected(self):
        """Ürün seçildiğinde tetiklenir."""
        selection_model = self.products_table.selectionModel()
        if selection_model is None:
            return
        selected_rows = selection_model.selectedRows()
        self.add_to_order_btn.setEnabled(len(selected_rows) > 0)
        
    def add_product_to_order(self):
        """Seçili ürünü siparişe ekler."""
        selection_model = self.products_table.selectionModel()
        if selection_model is None:
            return
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        def get_item_text(col):
            item = self.products_table.item(row, col)
            return item.text() if item is not None else ""
        try:
            stock_id = int(get_item_text(0))
        except ValueError:
            stock_id = 0
        product_type = get_item_text(1)
        product_name = get_item_text(2)
        part_number = get_item_text(3)
        try:
            available_stock = int(get_item_text(4))
        except ValueError:
            available_stock = 0
        price_text = get_item_text(5)
        try:
            price_parts = price_text.split()
            unit_price = float(price_parts[0])
            currency = price_parts[1] if len(price_parts) > 1 else "TL"
        except:
            unit_price = 0.0
            currency = "TL"
        quantity = self.quantity_spin.value()
        note = self.order_note.text().strip()
        # Stok kontrolü - Kit'ler için özel işlem
        if product_type == 'Kit':
            if quantity > 999:
                QMessageBox.warning(self, "Adet Sınırı", f"Kit için maksimum adet: 999\nİstenen: {quantity}")
                return
        else:
            if quantity > available_stock:
                QMessageBox.warning(self, "Stok Yetersiz", f"Yeterli stok yok!\nİstenen: {quantity}\nMevcut: {available_stock}")
                return
        order_item = {
            'stock_id': stock_id,
            'product_name': product_name,
            'part_number': part_number,
            'quantity': quantity,
            'unit_price': unit_price,
            'currency': currency,
            'note': note,
            'total': quantity * unit_price
        }
        existing_index = -1
        for i, item in enumerate(self.current_order_items):
            if item['stock_id'] == stock_id:
                existing_index = i
                break
        if existing_index >= 0:
            self.current_order_items[existing_index]['quantity'] += quantity
            self.current_order_items[existing_index]['total'] = (
                self.current_order_items[existing_index]['quantity'] * self.current_order_items[existing_index]['unit_price']
            )
        else:
            self.current_order_items.append(order_item)
        self.refresh_order_table()
        self.quantity_spin.setValue(1)
        self.order_note.clear()
        
    def refresh_order_table(self):
        """Sipariş tablosunu yeniler."""
        self.order_items_table.setRowCount(len(self.current_order_items))
        total_amount = 0
        
        for row, item in enumerate(self.current_order_items):
            self.order_items_table.setItem(row, 0, QTableWidgetItem(item['product_name']))
            self.order_items_table.setItem(row, 1, QTableWidgetItem(item['part_number']))
            self.order_items_table.setItem(row, 2, QTableWidgetItem(str(item['quantity'])))
            self.order_items_table.setItem(row, 3, QTableWidgetItem(f"{item['unit_price']:.2f} {item['currency']}"))
            self.order_items_table.setItem(row, 4, QTableWidgetItem(f"{item['total']:.2f} {item['currency']}"))
            
            total_amount += item['total']
            
        self.total_label.setText(f"Toplam: {total_amount:.2f} TL")
        self.create_order_btn.setEnabled(len(self.current_order_items) > 0)
        
    def on_order_item_selected(self):
        """Sipariş kalemi seçildiğinde tetiklenir."""
        selection_model = self.order_items_table.selectionModel()
        if selection_model is None:
            return
        selected_rows = selection_model.selectedRows()
        self.remove_item_btn.setEnabled(len(selected_rows) > 0)
        
    def remove_order_item(self):
        """Seçili sipariş kalemini kaldırır."""
        selected_rows = self.order_items_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            del self.current_order_items[row]
            self.refresh_order_table()
            
    def clear_order(self):
        """Tüm sipariş kalemlerini temizler."""
        reply = QMessageBox.question(
            self, "Onay", "Tüm sipariş kalemleri silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.current_order_items.clear()
            self.refresh_order_table()
            
    def create_cpc_order(self):
        """CPC siparişi oluşturur (bedelsiz çıkış)."""
        if not self.selected_customer_id:
            QMessageBox.warning(self, "Hata", "Müşteri seçilmedi!")
            return
            
        if not self.current_order_items:
            QMessageBox.warning(self, "Hata", "Sipariş kalemi eklenmedi!")
            return
            
        try:
            # Onay al
            reply = QMessageBox.question(
                self, "CPC Sipariş Onayı",
                f"Bu sipariş CPC müşterisi için bedelsiz olarak çıkış yapılacak.\n"
                f"Toplam {len(self.current_order_items)} kalem stoktan düşülecek.\n\n"
                f"Devam edilsin mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            try:
                # Sipariş bilgilerini al
                order_date = self.order_date.date().toPyDate()
                general_notes = self.order_notes.toPlainText().strip()
                
                # Stok çıkışları yap (ana işlem)
                for item in self.current_order_items:
                    # Stok güncelle
                    self.db.execute_query(
                        "UPDATE stock_items SET quantity = quantity - ? WHERE id = ?",
                        (item['quantity'], item['stock_id'])
                    )
                    
                    # Stok hareketi kaydet
                    movement_query = """
                        INSERT INTO stock_movements 
                        (stock_item_id, movement_date, movement_type, quantity_changed, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    
                    movement_note = f"CPC Bedelsiz Çıkış - {item['product_name']}"
                    if general_notes:
                        movement_note += f" - {general_notes}"
                    if item['note']:
                        movement_note += f" - {item['note']}"
                        
                    self.db.execute_query(
                        movement_query,
                        (item['stock_id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Çıkış", 
                         -item['quantity'], movement_note)
                    )
                
                # Başarı mesajı ve çıktı seçeneği
                reply = QMessageBox.question(
                    self, "CPC Sipariş Başarılı",
                    f"CPC siparişi başarıyla oluşturuldu!\n"
                    f"{len(self.current_order_items)} kalem stoktan bedelsiz çıkış yapıldı.\n\n"
                    f"Sipariş çıktısını almak ister misiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.generate_cpc_order_pdf(order_date, general_notes, self.current_order_items.copy())
                
                # Formu temizle
                self.clear_order()
                self.show_compatible_products('all')  # Stok güncellemelerini göster
                self.data_changed.emit()
                
                if self.status_bar:
                    self.status_bar.showMessage("CPC siparişi başarıyla oluşturuldu", 5000)
                    
            except Exception as e:
                 log_error("CPCTab", e)
                 raise e
                
        except Exception as e:
              log_error("CPCTab", e)
              QMessageBox.critical(self, "Hata", f"Sipariş oluşturulurken hata oluştu:\n{str(e)}")
    
    def generate_cpc_order_pdf(self, order_date, general_notes, order_items):
        """CPC sipariş çıktısı PDF'i oluşturur."""
        try:
            # Dosya kaydetme yeri seç
            filename, _ = QFileDialog.getSaveFileName(
                self, "CPC Sipariş Çıktısını Kaydet",
                f"CPC_Siparis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not filename:
                return
                
            # Müşteri bilgilerini al
            customer_info = self.db.fetch_one(
                "SELECT name, phone, email, address FROM customers WHERE id = ?",
                (self.selected_customer_id,)
            )
            
            if not customer_info:
                QMessageBox.warning(self, "Hata", "Müşteri bilgisi bulunamadı!")
                return
                
            # Cihaz bilgilerini al (varsa)
            device_info = None
            if self.selected_device_id:
                device_info = self.db.fetch_one(
                    "SELECT device_model, serial_number, device_type, color_type FROM customer_devices WHERE id = ?",
                    (self.selected_device_id,)
                )
            
            # Şirket bilgilerini al
            company_name = self.db.get_setting('company_name', 'KYOCERA YETKİLİ SATİS & SERVİS')
            company_address = self.db.get_setting('company_address', '')
            company_phone = self.db.get_setting('company_phone', '')
            company_email = self.db.get_setting('company_email', '')
            
            # PDF başlığı ve müşteri bilgileri
            pdf_data = {
                'title': 'CPC SİPARİŞ ÇIKTISI (BEDELSİZ ÇIKIŞ)',
                'company': {
                    'name': company_name,
                    'address': company_address,
                    'phone': company_phone,
                    'email': company_email
                },
                'customer': {
                    'name': customer_info[0],
                    'phone': customer_info[1] or '',
                    'email': customer_info[2] or '',
                    'address': customer_info[3] or ''
                },
                'order_date': order_date.strftime('%d.%m.%Y'),
                'order_number': f"CPC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'notes': general_notes,
                'items': []
            }
            
            # Cihaz bilgisi varsa ekle
            if device_info:
                pdf_data['device'] = {
                    'model': device_info[0],
                    'serial': device_info[1],
                    'type': device_info[2],
                    'color_type': device_info[3]
                }
            
            # Sipariş kalemlerini ekle
            total_items = 0
            for item in order_items:
                pdf_data['items'].append({
                    'product_name': item['product_name'],
                    'part_number': item.get('part_number', ''),
                    'quantity': item['quantity'],
                    'unit_price': 0.0,  # CPC için bedelsiz
                    'total_price': 0.0,
                    'note': item.get('note', '')
                })
                total_items += item['quantity']
            
            pdf_data['total_quantity'] = total_items
            pdf_data['total_amount'] = 0.0  # CPC için bedelsiz
            pdf_data['currency'] = 'TL'
            
            # PDF'i oluştur
            success = generate_cpc_order_pdf(pdf_data, filename)
            
            if success:
                reply = QMessageBox.question(
                    self, "PDF Oluşturuldu",
                    f"CPC sipariş çıktısı başarıyla oluşturuldu:\n{filename}\n\nDosyayı açmak ister misiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    os.startfile(filename)
                    
            else:
                QMessageBox.warning(self, "Hata", "PDF oluşturulurken bir hata oluştu!")
                
        except Exception as e:
              log_error("CPCTab", e)
              QMessageBox.critical(self, "Hata", f"PDF oluşturulurken hata oluştu:\n{str(e)}")
    
    def filter_products_table(self):
        """Ürün tablosunu filtreler."""
        filter_text = self.product_filter.text().lower()

        # Toner aramasını eşleşme dışı ürünler için DB fallback ile destekle
        if self.selected_device_id and filter_text and self.current_product_type in ('toner', 'all'):
            self.show_compatible_products(self.current_product_type)
        
        for row in range(self.products_table.rowCount()):
            should_show = True
            
            if filter_text:
                # Tip, Açıklama ve Parça No sütunlarında ara
                tip_item = self.products_table.item(row, 1)
                aciklama_item = self.products_table.item(row, 2)
                parca_no_item = self.products_table.item(row, 3)
                
                tip_text = tip_item.text().lower() if tip_item else ""
                aciklama_text = aciklama_item.text().lower() if aciklama_item else ""
                parca_no_text = parca_no_item.text().lower() if parca_no_item else ""
                
                # Herhangi bir sütunda filter_text varsa göster
                should_show = (filter_text in tip_text or 
                             filter_text in aciklama_text or 
                             filter_text in parca_no_text)
            
            self.products_table.setRowHidden(row, not should_show)
