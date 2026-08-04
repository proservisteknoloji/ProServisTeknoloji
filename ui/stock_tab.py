# ui/stock_tab.py

import logging

import logging
from utils.error_logger import log_error, log_warning, log_info
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QLabel, QFormLayout, QMessageBox, QGroupBox, QFrame, QTabWidget, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from .dialogs.stock_dialogs import StockItemDialog, StockMovementDialog
from .dialogs.bulk_device_sale_dialog import BulkDeviceSaleDialog
from .dialogs.stock_history_dialog import StockHistoryDialog
from utils.database import db_manager
from .stock.cpc_stock import CPCStockManager

class StockTab(QWidget):
    """Stok yönetimi sekmesi."""
    data_changed = Signal()

    def __init__(self, db, current_user=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_user = current_user
        self.selected_item_id = None
        self.selected_item_type = None
        
        self.init_ui()
        
        # CPC stok yöneticisini başlat (UI oluşturulduktan sonra)
        self.cpc_manager = CPCStockManager(self)
        
        self.refresh_data()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        # Tab widget oluştur
        self.tab_widget = QTabWidget()
        
        # Normal stok sekmesi
        normal_stock_tab = self._create_normal_stock_tab()
        self.tab_widget.addTab(normal_stock_tab, "📦 Normal Stok")
        
        # CPC stok sekmesi
        cpc_stock_tab = self._create_cpc_stock_tab()
        self.tab_widget.addTab(cpc_stock_tab, "🔄 CPC Stok")

        # Emanet stok sekmesi
        emanet_stock_tab = self._create_emanet_stock_tab()
        self.tab_widget.addTab(emanet_stock_tab, "📥 Emanet Stok")

        # 2. El cihaz stok sekmesi
        second_hand_stock_tab = self._create_second_hand_stock_tab()
        self.tab_widget.addTab(second_hand_stock_tab, "🔄 2. El Cihaz")
        
        main_layout.addWidget(self.tab_widget)
        
        self._connect_signals()
    def _create_emanet_stock_tab(self):
        """Emanet stok sekmesini oluşturur."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        # Tabloya ek olarak yazdır butonu
        btn_layout = QHBoxLayout()
        self.print_emanet_btn = QPushButton("🖨 Emanet Stok Listesini Yazdır")
        self.print_emanet_btn.clicked.connect(self.print_emanet_stock_list)
        btn_layout.addStretch()
        btn_layout.addWidget(self.print_emanet_btn)
        layout.addLayout(btn_layout)
        # Tabloya yeni sütunlar ekle: Arıza, Beklenen Parça
        self.emanet_table = QTableWidget(0, 6)
        self.emanet_table.setHorizontalHeaderLabels(["ID", "İsim/Model", "Seri No", "Miktar", "Arıza Açıklaması", "Beklenen Parça"])
        self.emanet_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.emanet_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.emanet_table.hideColumn(0)
        # Tüm sütunlar içeriğe göre otomatik genişlesin, sadece İsim/Model kalan alanı doldursun
        from PyQt6.QtCore import QSettings
        header = self.emanet_table.horizontalHeader()
        if header:
            from PyQt6.QtWidgets import QHeaderView
            # Tüm sütunlar kullanıcı tarafından ayarlanabilir (Interactive)
            for col in range(self.emanet_table.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            # Sütun genişliklerini ayarlama/okuma için QSettings kullan
            settings = QSettings("ProServis", "EmanetStok")
            for col in range(self.emanet_table.columnCount()):
                width = settings.value(f"emanet_col_width_{col}", None, type=int)
                if width:
                    self.emanet_table.setColumnWidth(col, width)
            # Genişlik değişince kaydet
            def save_column_widths():
                for c in range(self.emanet_table.columnCount()):
                    settings.setValue(f"emanet_col_width_{c}", self.emanet_table.columnWidth(c))
            header.sectionResized.connect(lambda idx, old, new: save_column_widths())
        layout.addWidget(self.emanet_table)
        self.refresh_emanet_stock()
        return tab

    def refresh_emanet_stock(self):
        """Emanet stokları yeniler."""
        self.emanet_table.setRowCount(0)        # Cihaz ve servis kayd? ile birlikte ar?za ve beklenen par?a bilgisini ?ek
        # Not: Yaln?zca serviste bekleyen cihazlar listelenir (teslimata kadar).
        query = '''
            SELECT s.id, s.name, s.part_number as serial_number, s.quantity,
                   sr.problem_description, sr.notes,
                   (SELECT GROUP_CONCAT(description, ', ') FROM quote_items WHERE service_record_id = sr.id AND unit_price IS NULL) as waiting_parts
            FROM stock_items s
            LEFT JOIN service_records sr ON sr.id = (
                SELECT sr2.id FROM service_records sr2
                WHERE sr2.device_id = (
                    SELECT cd.id FROM customer_devices cd WHERE cd.serial_number = s.part_number LIMIT 1
                )
                ORDER BY sr2.created_date DESC, sr2.id DESC
                LIMIT 1
            )
            WHERE s.item_type = 'Cihaz'
              AND s.is_consignment = 1
              AND s.quantity > 0
              AND sr.id IS NOT NULL
              AND sr.status NOT IN ('Onarıldı', 'Teslim Edildi', 'İptal edildi')
            ORDER BY s.name
        '''
        emanet_items = self.db.fetch_all(query)
        for row_idx, item in enumerate(emanet_items):
            self.emanet_table.insertRow(row_idx)
            self.emanet_table.setItem(row_idx, 0, QTableWidgetItem(str(item['id'])))
            self.emanet_table.setItem(row_idx, 1, QTableWidgetItem(item['name']))
            self.emanet_table.setItem(row_idx, 2, QTableWidgetItem(item['serial_number'] if item['serial_number'] is not None else ""))
            self.emanet_table.setItem(row_idx, 3, QTableWidgetItem(str(item['quantity'])))
            # Arıza açıklaması: problem_description ve notes birleştir
            ariza = (item['problem_description'] or '').strip()
            notes = (item['notes'] or '').strip()
            if ariza and notes:
                ariza_text = f"{ariza}\n---\n{notes}"
            elif ariza:
                ariza_text = ariza
            elif notes:
                ariza_text = notes
            else:
                ariza_text = ''
            self.emanet_table.setItem(row_idx, 4, QTableWidgetItem(ariza_text))
            self.emanet_table.setItem(row_idx, 5, QTableWidgetItem(item['waiting_parts'] if item['waiting_parts'] is not None else ""))

    def print_emanet_stock_list(self):
        """Emanet stok listesini yazdırılabilir tablo olarak açar."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt6.QtGui import QTextDocument
        html = "<h2>Emanet Stok Listesi</h2><table border='1' cellspacing='0' cellpadding='4'><tr>"
        headers = []
        for i in range(self.emanet_table.columnCount()):
            if not self.emanet_table.isColumnHidden(i):
                header_item = self.emanet_table.horizontalHeaderItem(i)
                if header_item is not None:
                    header_text = header_item.text()
                else:
                    header_text = ''
                # Sütun başlığında Parça No yerine Seri No yaz
                header_text = header_text.replace("Parça No", "Seri No")
                headers.append(header_text)
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr>"
        for row in range(self.emanet_table.rowCount()):
            html += "<tr>"
            for col in range(self.emanet_table.columnCount()):
                if not self.emanet_table.isColumnHidden(col):
                    val = self.emanet_table.item(row, col)
                    html += f"<td>{val.text() if val else ''}</td>"
            html += "</tr>"
        html += "</table>"
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter()
        dlg = QPrintDialog(printer, self)
        if dlg.exec():
            doc.print(printer)

    def _create_second_hand_stock_tab(self):
        """2. El cihaz stok sekmesini oluşturur."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Arama alanı
        filter_layout = QHBoxLayout()
        self.second_hand_filter_input = QLineEdit()
        self.second_hand_filter_input.setPlaceholderText("Model, seri no veya alınan kişi/kurum ile ara...")
        filter_layout.addWidget(self.second_hand_filter_input)
        layout.addLayout(filter_layout)

        # Buton alanı
        btn_layout = QHBoxLayout()
        self.add_second_hand_btn = QPushButton("➕ 2. El Cihaz Ekle")
        self.edit_second_hand_btn = QPushButton("✏️ Düzenle")
        self.history_second_hand_btn = QPushButton("📋 Geçmiş Görüntüle")
        self.scrap_device_btn = QPushButton("🗑️ Hurda Çıkar")
        self.delete_second_hand_btn = QPushButton("🗑️ Cihazı Sil")
        self.print_second_hand_btn = QPushButton("🖨️ 2. El Listesi Yazdır")

        # Buton stilleri
        for btn in [self.add_second_hand_btn, self.edit_second_hand_btn, self.history_second_hand_btn, self.scrap_device_btn, self.delete_second_hand_btn, self.print_second_hand_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)

        self.scrap_device_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.delete_second_hand_btn.setStyleSheet("""
            QPushButton {
                background-color: #B71C1C;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #8E0000;
            }
        """)

        self.edit_second_hand_btn.setEnabled(False)
        self.history_second_hand_btn.setEnabled(False)
        self.scrap_device_btn.setEnabled(False)
        self.delete_second_hand_btn.setEnabled(False)

        btn_layout.addWidget(self.add_second_hand_btn)
        btn_layout.addWidget(self.edit_second_hand_btn)
        btn_layout.addWidget(self.history_second_hand_btn)
        btn_layout.addWidget(self.scrap_device_btn)
        btn_layout.addWidget(self.delete_second_hand_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.print_second_hand_btn)
        layout.addLayout(btn_layout)
        
        # 2. El cihaz tablosu
        self.second_hand_table = QTableWidget(0, 10)
        self.second_hand_table.setHorizontalHeaderLabels([
            "ID", "Cihaz Model", "Seri No", "Alınan Kişi/Kurum", 
            "Alınma Tarihi", "Alış Fiyatı", "Satış Fiyatı", "Durum", "Kâr Marjı", "Notlar"
        ])
        self.second_hand_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.second_hand_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.second_hand_table.hideColumn(0)
        
        # Sütun genişlikleri
        header = self.second_hand_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Cihaz Model - esnek
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Seri No - sabit
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Alınan Kişi - esnek
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Tarih - sabit
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Alış Fiyatı - sabit
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)   # Satış Fiyatı - sabit
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)   # Durum - sabit
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)   # Kâr Marjı - sabit
            header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)  # Notlar - esnek
            
            self.second_hand_table.setColumnWidth(2, 120)  # Seri No
            self.second_hand_table.setColumnWidth(4, 100)  # Tarih
            self.second_hand_table.setColumnWidth(5, 80)   # Alış Fiyatı
            self.second_hand_table.setColumnWidth(6, 80)   # Satış Fiyatı
            self.second_hand_table.setColumnWidth(7, 80)   # Durum
            self.second_hand_table.setColumnWidth(8, 70)   # Kâr Marjı
        
        layout.addWidget(self.second_hand_table)
        
        # Sinyalleri bağla
        self.add_second_hand_btn.clicked.connect(self.add_second_hand_device)
        self.edit_second_hand_btn.clicked.connect(self.edit_second_hand_device_from_button)
        self.history_second_hand_btn.clicked.connect(self.show_second_hand_device_history)
        self.scrap_device_btn.clicked.connect(self.scrap_second_hand_device)
        self.delete_second_hand_btn.clicked.connect(self.delete_second_hand_device)
        self.print_second_hand_btn.clicked.connect(self.print_second_hand_list)
        self.second_hand_table.itemSelectionChanged.connect(self.second_hand_device_selected)
        self.second_hand_table.itemDoubleClicked.connect(self.edit_second_hand_device)
        self.second_hand_filter_input.textChanged.connect(self.filter_second_hand_devices)
        
        self.refresh_second_hand_stock()
        return tab

    def _create_normal_stock_tab(self):
        """Normal stok sekmesini oluşturur."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 500])
        layout.addWidget(splitter)
        
        return tab

    def _create_cpc_stock_tab(self):
        """CPC stok sekmesini oluşturur."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_cpc_left_panel()
        right_panel = self._create_cpc_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 500])
        layout.addWidget(splitter)
        
        return tab

    def _create_left_panel(self):
        """Stok listesini, filtrelemeyi ve hareket geçmişini içeren sol paneli oluşturur."""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        
        # Filtre alanı
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Stok adı veya parça no ile ara...")
        filter_layout.addWidget(self.filter_input)
        
        # Stok listesi
        stock_group = QGroupBox("📋 Stok Listesi")
        stock_layout = QVBoxLayout(stock_group)
        
        self.stock_table = QTableWidget(0, 5)
        self.stock_table.setHorizontalHeaderLabels(["ID", "Renk Tipi", "İsim/Model", "Parça No", "Miktar"])
        self.stock_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.stock_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)  # Tek seçim
        self.stock_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Düzenleme kapalı
        
        # Sütun genişliklerini özelleştir
        header = self.stock_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID - gizli
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Tip - sabit
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # İsim/Model - esnek
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Parça No - sabit
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Miktar - sabit
        
        # Sabit sütun genişlikleri
        self.stock_table.setColumnWidth(1, 80)   # Tip - dar
        self.stock_table.setColumnWidth(3, 120)  # Parça No - orta
        self.stock_table.setColumnWidth(4, 70)   # Miktar - dar
        
        self.stock_table.hideColumn(0)
        stock_layout.addWidget(self.stock_table)
        
        # Hareket geçmişi alanı (kompakt)
        movements_group = QGroupBox("📊 Stok Hareket Geçmişi (Seçili Ürün)")
        movements_layout = QVBoxLayout(movements_group)
        
        # Hareket geçmişi için buton alanı
        movements_btn_layout = QHBoxLayout()
        self.detailed_history_btn = QPushButton("🔍 Detaylı Geçmiş")
        self.detailed_history_btn.setEnabled(False)
        self.detailed_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5E35B1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        movements_btn_layout.addWidget(self.detailed_history_btn)
        movements_btn_layout.addStretch()
        
        # Kompakt hareket tablosu
        self.movements_table_compact = QTableWidget(0, 4)
        self.movements_table_compact.setHorizontalHeaderLabels(["Tarih", "Hareket", "Miktar", "Açıklama"])
        
        # Hareket tablosu sütun genişlikleri
        movements_header = self.movements_table_compact.horizontalHeader()
        if movements_header:
            movements_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Tarih - sabit
            movements_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Hareket - sabit
            movements_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Miktar - sabit  
            movements_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Açıklama - esnek
        
        self.movements_table_compact.setColumnWidth(0, 90)   # Tarih - dar
        self.movements_table_compact.setColumnWidth(1, 80)   # Hareket - dar
        self.movements_table_compact.setColumnWidth(2, 60)   # Miktar - dar
        
        self.movements_table_compact.setMaximumHeight(150)  # Kompakt boyut
        self.movements_table_compact.setAlternatingRowColors(True)
        
        movements_layout.addLayout(movements_btn_layout)
        movements_layout.addWidget(self.movements_table_compact)
        
        # Layout'a ekle
        layout.addLayout(filter_layout)
        layout.addWidget(stock_group, 2)  # Stok listesi daha fazla yer kaplasın
        layout.addWidget(movements_group, 1)  # Hareket geçmişi daha az yer kaplasın
        
        return panel

    def _create_right_panel(self):
        """Detayları ve butonları içeren sağ paneli oluşturur."""
        # FIXED: Add parent to prevent memory leak
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        
        button_layout = self._create_button_layout()
        self.details_group = self._create_details_group()

        layout.addLayout(button_layout)
        layout.addWidget(self.details_group)
        layout.addStretch()  # Alt kısmı boş bırak
        return panel

    def _create_details_group(self):
        """Stok kartı detaylarını gösteren grubu oluşturur."""
        group = QGroupBox("Stok Kartı Detayları")
        layout = QFormLayout(group)
        self.type_label = QLabel()
        self.name_label = QLabel()
        self.part_number_label = QLabel()
        self.compatible_label = QLabel()
        self.compatible_label.setWordWrap(True)
        self.compatible_label.setStyleSheet("color: #2E7D32; font-style: italic;")
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumHeight(60)  # Maksimum 60 piksel yükseklik
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.description_label.setStyleSheet("QLabel { border: 1px solid #E0E0E0; padding: 5px; background-color: #F9F9F9; }")
        self.sale_price_label = QLabel()
        self.quantity_label = QLabel()
        self.quantity_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #1E40AF;")
        
        layout.addRow("Renk Tipi:", self.type_label)
        layout.addRow("İsim/Model:", self.name_label)
        layout.addRow("Parça No:", self.part_number_label)
        layout.addRow("Uyumlu Modeller:", self.compatible_label)
        layout.addRow("Açıklama:", self.description_label)
        layout.addRow("Satış Fiyatı:", self.sale_price_label)
        layout.addRow("Mevcut Miktar:", self.quantity_label)
        return group

    def _create_movements_group(self):
        """Stok hareket geçmişini gösteren grubu oluşturur."""
        group = QGroupBox("Stok Hareket Geçmişi")
        layout = QVBoxLayout(group)
        self.movements_table = QTableWidget(0, 4)
        self.movements_table.setHorizontalHeaderLabels(["İşlem Tarihi", "Hareket Tipi", "Miktar", "Açıklama"])
        
        # Detaylı hareket tablosu sütun genişlikleri
        detail_header = self.movements_table.horizontalHeader()
        if detail_header:
            detail_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Tarih - sabit
            detail_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Hareket - sabit
            detail_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Miktar - sabit
            detail_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Açıklama - esnek
        
        self.movements_table.setColumnWidth(0, 130)  # İşlem Tarihi - orta
        self.movements_table.setColumnWidth(1, 100)  # Hareket Tipi - dar
        self.movements_table.setColumnWidth(2, 80)   # Miktar - dar
        
        layout.addWidget(self.movements_table)
        return group

    def _create_button_layout(self):
        """Modern dashboard tarzında gruplanmış buton layout'u oluşturur."""
        main_layout = QVBoxLayout()
        
        # GRUP 1: STOK GİRİŞİ (Yeni Ekle)
        stock_input_group = QGroupBox("📦 Stok Girişi")
        stock_input_layout = QHBoxLayout(stock_input_group)
        
        self.add_part_btn = QPushButton("🔧 Yedek Parça")
        self.add_device_btn = QPushButton("🖨 Cihaz")
        self.add_toner_btn = QPushButton("📝 Toner")
        self.add_kit_btn = QPushButton("🔨 Kit")
        
        # Stok giriş butonları stili - basitleştirilmiş
        for btn in [self.add_part_btn, self.add_device_btn, self.add_toner_btn, self.add_kit_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border-radius: 8px;
                    padding: 12px 20px;
                    min-height: 40px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
        
        stock_input_layout.addWidget(self.add_part_btn)
        stock_input_layout.addWidget(self.add_device_btn)
        stock_input_layout.addWidget(self.add_toner_btn)
        stock_input_layout.addWidget(self.add_kit_btn)
        stock_input_layout.addStretch()
        
        # GRUP 2: STOK DÜZENLEME
        stock_edit_group = QGroupBox("⚙️ Stok Düzenleme")
        stock_edit_layout = QHBoxLayout(stock_edit_group)
        
        self.edit_item_btn = QPushButton("✏️ Kartı Düzenle")
        self.stock_in_btn = QPushButton("⬆️ Stok Girişi")
        self.stock_out_btn = QPushButton("⬇️ Stok Çıkışı")
        
        # Admin için stok silme butonu
        self.delete_item_btn = QPushButton("🗑️ Stok Kartını Sil")
        self.delete_item_btn.setEnabled(False)
        
        self.edit_item_btn.setEnabled(False)
        self.stock_in_btn.setEnabled(False)
        self.stock_out_btn.setEnabled(False)
        
        # Admin kontrolü - sadece admin kullanıcılar silme butonunu görebilir
        if not self._is_admin_user():
            self.delete_item_btn.hide()
        
        # Stok düzenleme butonları stili - basitleştirilmiş
        edit_buttons = [self.edit_item_btn, self.stock_in_btn, self.stock_out_btn]
        if self._is_admin_user():
            edit_buttons.append(self.delete_item_btn)
            
        for btn in edit_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border-radius: 8px;
                    padding: 12px 20px;
                    min-height: 40px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                    color: #757575;
                }
            """)
        
        # Silme butonu için özel stil (kırmızı)
        if self._is_admin_user():
            self.delete_item_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border-radius: 8px;
                    padding: 12px 20px;
                    min-height: 40px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                    color: #757575;
                }
            """)
        
        stock_edit_layout.addWidget(self.edit_item_btn)
        stock_edit_layout.addWidget(self.stock_in_btn)
        stock_edit_layout.addWidget(self.stock_out_btn)
        if self._is_admin_user():
            stock_edit_layout.addWidget(self.delete_item_btn)
        stock_edit_layout.addStretch()
        
        # GRUP 3: RAPORLAR VE AYARLAR
        reports_group = QGroupBox("📈 Raporlar & Ayarlar")
        reports_layout = QHBoxLayout(reports_group)
        
        self.stock_settings_btn = QPushButton("⚙️ Stok Ayarları")
        self.price_settings_btn = QPushButton("💰 Fiyat Ayarları")
        self.device_analysis_btn = QPushButton("🔍 Cihaz-Toner Analizi")
        
        # Rapor butonları stili - basitleştirilmiş
        for btn in [self.stock_settings_btn, self.price_settings_btn, self.device_analysis_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #9C27B0;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border-radius: 8px;
                    padding: 12px 20px;
                    min-height: 40px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #7B1FA2;
                }
            """)
        
        reports_layout.addWidget(self.stock_settings_btn)
        reports_layout.addWidget(self.price_settings_btn)
        reports_layout.addWidget(self.device_analysis_btn)
        reports_layout.addStretch()
        
        # GRUP 4: SATIŞ (Ayrı vurgulanmış alan)
        sales_group = QGroupBox("💵 Satış İşlemleri")
        sales_layout = QHBoxLayout(sales_group)
        self.purchase_invoice_btn = QPushButton("Al\u0131\u015f Faturas\u0131")
        self.purchase_invoice_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 15px 25px;
                min-height: 50px;
                min-width: 150px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        sales_layout.addWidget(self.purchase_invoice_btn)
        
        self.new_sale_btn = QPushButton("🛒 Yeni Satış")
        self.new_sale_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 15px 25px;
                min-height: 50px;
                min-width: 150px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        sales_layout.addWidget(self.new_sale_btn)
        sales_layout.addStretch()
        
        # Grupları ana layout'a ekle
        main_layout.addWidget(stock_input_group)
        main_layout.addWidget(stock_edit_group)
        main_layout.addWidget(reports_group)
        main_layout.addWidget(sales_group)
        
        return main_layout

    def _connect_signals(self):
        """Sinyalleri slotlara bağlar."""
        self.filter_input.textChanged.connect(self.refresh_data)
        self.stock_table.itemSelectionChanged.connect(self.item_selected)
        self.stock_table.itemDoubleClicked.connect(self.stock_table_double_clicked)
        self.stock_table.cellChanged.connect(self.stock_table_cell_changed)
        
        self.add_part_btn.clicked.connect(lambda: self.open_item_dialog(item_type='Yedek Parça'))
        self.add_device_btn.clicked.connect(lambda: self.open_item_dialog(item_type='Cihaz'))
        self.add_toner_btn.clicked.connect(lambda: self.open_item_dialog(item_type='Toner'))
        self.add_kit_btn.clicked.connect(lambda: self.open_item_dialog(item_type='Kit'))
        self.edit_item_btn.clicked.connect(lambda: self.open_item_dialog(edit_mode=True))
        self.stock_in_btn.clicked.connect(lambda: self.open_movement_dialog('Giriş'))
        self.stock_out_btn.clicked.connect(lambda: self.open_movement_dialog('Çıkış'))
        
        # Admin için silme butonunu bağla
        if self._is_admin_user():
            self.delete_item_btn.clicked.connect(self.delete_stock_item)
        
        self.stock_settings_btn.clicked.connect(self.open_stock_settings_dialog)
        self.purchase_invoice_btn.clicked.connect(self.open_purchase_invoice_dialog)
        self.price_settings_btn.clicked.connect(self.open_price_settings_dialog)
        self.device_analysis_btn.clicked.connect(self.open_device_analysis_dialog)
        self.new_sale_btn.clicked.connect(self.open_tabbed_sale_dialog)
        
        # Detaylı hareket geçmişi butonu
        self.detailed_history_btn.clicked.connect(self.open_detailed_history)
        
        # CPC stok bağlantıları
        self.tab_widget.currentChanged.connect(self.tab_changed)
        self.cpc_filter_input.textChanged.connect(self.filter_cpc_devices)
        self.cpc_device_table.itemSelectionChanged.connect(self.cpc_device_selected)
        self.cpc_device_table.itemDoubleClicked.connect(self.cpc_device_double_clicked)
        self.add_cpc_toner_btn.clicked.connect(self.add_cpc_toner)
        self.view_cpc_history_btn.clicked.connect(self.view_cpc_history)
        
    def _is_admin_user(self):
        """Kullanıcının admin olup olmadığını kontrol eder."""
        if not self.current_user:
            return False
        
        # Admin kontrolü - role veya is_admin field'ına göre (büyük/küçük harf duyarsız)
        role = self.current_user.get('role', '').lower()
        username = self.current_user.get('username', '').lower()
        is_admin = self.current_user.get('is_admin', False)
        
        return (role in ['admin', 'superadmin'] or 
                is_admin == True or
                username == 'admin')
    
    def delete_stock_item(self):
        """Seçili stok öğesini siler (sadece admin)."""
        if not self._is_admin_user():
            QMessageBox.warning(self, "Yetki Hatası", "Bu işlem için admin yetkisi gereklidir!")
            return
        
        if not self.selected_item_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek stok öğesini seçin!")
            return
        
        # Stok bilgilerini al
        try:
            item_query = "SELECT name, item_type, quantity FROM stock_items WHERE id = ?"
            item_data = self.db.fetch_one(item_query, (self.selected_item_id,))
            
            if not item_data:
                QMessageBox.warning(self, "Hata", "Stok öğesi bulunamadı!")
                return
            
            item_name = item_data['name']
            item_type = item_data['item_type']
            quantity = item_data['quantity']
            
            # Onay penceresi
            reply = QMessageBox.question(
                self, "Stok Silme Onayı",
                f"🗑️ Bu stok öğesini kalıcı olarak silmek istediğinizden emin misiniz?\n\n"
                f"📝 Öğe: {item_name}\n"
                f"🏷️ Tip: {item_type}\n"
                f"📦 Miktar: {quantity}\n\n"
                f"⚠️ Bu işlem GERİ ALINAMAZ!\n"
                f"Tüm hareket geçmişi de silinecektir.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._perform_stock_deletion(item_name, item_type)
                
        except Exception as e:
              log_error("StockTab", e)
              QMessageBox.critical(self, "Hata", f"Stok silme işlemi sırasında hata oluştu:\n{str(e)}")
    
    def _perform_stock_deletion(self, item_name, item_type):
        """Stok silme işlemini gerçekleştirir."""
        try:
            # Hareket geçmişini sil
            self.db.execute_query("DELETE FROM stock_movements WHERE stock_item_id = ?", (self.selected_item_id,))
            
            # Stok öğesini sil
            self.db.execute_query("DELETE FROM stock_items WHERE id = ?", (self.selected_item_id,))
            
            # Log kaydı
            username = (self.current_user or {}).get('username', 'N/A')
            logging.info(f"Admin {username} tarafından stok silindi: {item_name} ({item_type})")
            
            QMessageBox.information(
                self, "Başarılı",
                f"✅ Stok öğesi başarıyla silindi!\n\n"
                f"📝 Silinen: {item_name}\n"
                f"🏷️ Tip: {item_type}\n\n"
                f"🔄 Stok listesi güncelleniyor..."
            )
            
            # Seçimi temizle ve veriyi yenile
            self.selected_item_id = None
            self.selected_item_type = None
            self.clear_details()
            self.refresh_data()
            
        except Exception as e:
              log_error("StockTab", e)
              QMessageBox.critical(self, "Silme Hatası", f"Stok silme işlemi başarısız:\n{str(e)}")
    def open_tabbed_sale_dialog(self):
        from ui.dialogs.new_sale_dialog import NewSaleInvoiceDialog
        dialog = NewSaleInvoiceDialog(self.db, self)
        if dialog.exec():
            sale_data = dialog.get_data()
            if sale_data:
                # Satışı "beklemede" durumuna al - henüz faturalamadan 
                result = self.db.create_pending_sale(sale_data)
                if isinstance(result, int):
                    QMessageBox.information(self, "Başarılı", f"Satış işlemi tamamlandı. Stoktan düşürüldü.\nFaturalama işlemi için 'Faturalar' sekmesine gidin.\nSatış ID: {result}")
                    self.data_changed.emit()
                    self.refresh_data()
                else:
                    QMessageBox.critical(self, "Satış Hatası", str(result))

    def open_detailed_history(self):
        """Seçili ürün için detaylı hareket geçmişi diyalogunu açar."""
        if not self.selected_item_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir stok kartı seçin.")
            return
            
        try:
            # Seçili ürünün adını al
            item_name = self.name_label.text() or "Bilinmeyen Ürün"
            
            # Detaylı hareket geçmişi diyalogunu aç
            dialog = StockHistoryDialog(
                item_id=self.selected_item_id,
                item_name=item_name,
                db_manager=self.db,
                parent=self
            )
            dialog.exec()
            
        except Exception as e:
              log_error("StockTab", e)
              QMessageBox.critical(self, "Hata", f"Detaylı geçmiş açılırken hata oluştu: {e}")

    def refresh_data(self):
        """Stok listesini veritabanından yeniler."""
        filter_text = self.filter_input.text()
        current_id = self.selected_item_id
        self.stock_table.setRowCount(0)
        
        # Emanet stokları da yenile
        self.refresh_emanet_stock()
        
        try:
            items = self.db.get_stock_items(filter_text)
            if not items:
                return

            self.stock_table.setRowCount(len(items))
            
            new_row_to_select = -1
            for row, item_data in enumerate(items):
                # Tonerlerde orijinal/muadil etiketini görünür tut
                name = item_data.get('name', '')
                part_number = item_data.get('part_number', '') or ''
                if item_data.get('item_type', '') == 'Toner':
                    toner_text = f"{name} {part_number}".lower()
                    if 'muadil' in toner_text:
                        display_name = f"{name} 🔄 MUADİL"
                    else:
                        display_name = f"{name} ✅ ORİJİNAL"
                else:
                    display_name = name
                self.stock_table.setItem(row, 0, QTableWidgetItem(str(item_data.get('id', ''))))
                self.stock_table.setItem(row, 1, QTableWidgetItem(item_data.get('item_type', '')))
                self.stock_table.setItem(row, 2, QTableWidgetItem(display_name))
                self.stock_table.setItem(row, 3, QTableWidgetItem(part_number))
                self.stock_table.setItem(row, 4, QTableWidgetItem(str(item_data.get('quantity', ''))))
                
                if item_data.get('id') == current_id:
                    new_row_to_select = row

            if new_row_to_select != -1:
                self.stock_table.selectRow(new_row_to_select)
            else:
                self.clear_details()
        except Exception as e:
              log_error("StockTab", e)
              QMessageBox.critical(self, "Veritabanı Hatası", f"Stok verileri yüklenirken bir hata oluştu: {e}")

    def item_selected(self):
        """Stok tablosundan bir öğe seçildiğinde tetiklenir."""
        selection_model = self.stock_table.selectionModel()
        if not selection_model:
            self.clear_details()
            return
            
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            self.clear_details()
            return

        # Multiple selection varsa sadece ilk seçimi al
        if len(selected_rows) > 1:
            # Sadece ilk seçili satırı tut, diğerlerini temizle
            selection_model.clearSelection()
            self.stock_table.selectRow(selected_rows[0].row())
            return

        row = selected_rows[0].row()
        try:
            item_0 = self.stock_table.item(row, 0)
            item_1 = self.stock_table.item(row, 1)
            if item_0 and item_1:
                self.selected_item_id = int(item_0.text())
                self.selected_item_type = item_1.text()
            else:
                self.clear_details()
                return
        except (ValueError, AttributeError):
            self.clear_details()
            return

        self._update_ui_for_selection()
        self._load_item_details()
        self._load_item_movements()

    def _update_ui_for_selection(self):
        """Seçime göre butonların ve arayüzün durumunu günceller."""
        self.edit_item_btn.setEnabled(True)
        self.stock_in_btn.setEnabled(True)
        self.stock_out_btn.setEnabled(True)
        
        # Admin için silme butonunu aktifleştir
        if self._is_admin_user():
            self.delete_item_btn.setEnabled(True)
    # self.sell_device_btn was removed; no longer needed

    def _load_item_details(self):
        """Seçili öğenin detaylarını yükler ve gösterir."""
        try:
            details = self.db.get_stock_item_details(self.selected_item_id)
            if details:
                self.type_label.setText(details.get('item_type', 'N/A'))
                self.name_label.setText(details.get('name', 'N/A'))
                self.part_number_label.setText(details.get('part_number') or 'N/A')
                self.compatible_label.setText(details.get('compatible_models') or '-')
                
                description = details.get('description') or ''
                if details.get('item_type') == 'Cihaz':
                    color_type = details.get('color_type', 'Siyah-Beyaz')
                    # JSON verilerini kısalt
                    if '[TONER_DATA]' in description and '[KIT_DATA]' in description:
                        # Sadece baskı tipini göster, JSON verilerini gizle
                        description = f"Baskı Tipi: {color_type}\nMFP A4 BW\n\n✅ Toner ve Kit bilgileri mevcut"
                    else:
                        description = f"Baskı Tipi: {color_type}\n{description}"
                else:
                    # Diğer item türleri için description'ı kısalt
                    if len(description) > 100:
                        description = description[:100] + "..."
                        
                self.description_label.setText(description)
                
                self.quantity_label.setText(str(details.get('quantity', 0)))
                sale_price = details.get('sale_price', 0.0)
                sale_curr = details.get('sale_currency', 'TL')
                self.sale_price_label.setText(f"{sale_price or 0.00:.2f} {sale_curr or 'TL'}")
        except Exception as e:
            QMessageBox.warning(self, "Detay Hatası", f"Stok detayları yüklenemedi: {e}")
            self.clear_details()

    def _load_item_movements(self):
        """Seçili öğenin stok hareketlerini yükler."""
        self.movements_table_compact.setRowCount(0)
        self.detailed_history_btn.setEnabled(bool(self.selected_item_id))
        
        try:
            movements = self.db.get_stock_movements(self.selected_item_id)
            # Son 5 hareketi kompakt tabloda göster
            recent_movements = movements[:5] if movements else []
            
            self.movements_table_compact.setRowCount(len(recent_movements))
            for row, move in enumerate(recent_movements):
                # Tarih formatını kısalt
                date_str = move.get('movement_date', '')
                if len(date_str) > 10:
                    date_str = date_str[:10]  # Sadece tarih kısmı
                
                # Eksik setItem çağrısı düzeltildi
                self.movements_table_compact.setItem(row, 0, QTableWidgetItem(date_str))
                self.movements_table_compact.setItem(row, 1, QTableWidgetItem(move.get('movement_type', '')))
                
                # Miktar değişimini renklendir - doğru yöntem
                quantity_changed = move.get('quantity_changed', 0)
                quantity_item = QTableWidgetItem(str(quantity_changed))
                
                # QTableWidgetItem için doğru renklendirme yöntemi
                from PyQt6.QtGui import QColor
                if quantity_changed > 0:
                    quantity_item.setForeground(QColor(0, 128, 0))  # Yeşil
                    font = quantity_item.font()
                    font.setBold(True)
                    quantity_item.setFont(font)
                elif quantity_changed < 0:
                    quantity_item.setForeground(QColor(255, 0, 0))  # Kırmızı
                    font = quantity_item.font()
                    font.setBold(True)
                    quantity_item.setFont(font)
                
                self.movements_table_compact.setItem(row, 2, quantity_item)
                
                # Açıklamayı kısalt
                notes = move.get('notes', '') or ''
                if len(notes) > 30:
                    notes = notes[:27] + "..."
                self.movements_table_compact.setItem(row, 3, QTableWidgetItem(notes))
                
        except Exception as e:
            QMessageBox.warning(self, "Hareket Hatası", f"Stok hareketleri yüklenemedi: {e}")

    def clear_details(self):
        """Detay panelini temizler ve butonları devre dışı bırakır."""
        self.selected_item_id = None
        self.selected_item_type = None
        self.edit_item_btn.setEnabled(False)
        self.stock_in_btn.setEnabled(False)
        self.stock_out_btn.setEnabled(False)
        self.detailed_history_btn.setEnabled(False)
        if self._is_admin_user():
           self.delete_item_btn.setEnabled(False)
        
        # Admin için silme butonunu da devre dışı bırak
        if self._is_admin_user():
            self.delete_item_btn.setEnabled(False)
            
        for label in [self.type_label, self.name_label, self.part_number_label, 
                      self.compatible_label,  # <-- Bunu eklemeyi unutmayın
                      self.description_label, self.quantity_label, self.sale_price_label]:
            label.clear()
        self.movements_table_compact.setRowCount(0)

    def open_item_dialog(self, item_type=None, edit_mode=False):
        """Yeni stok kartı ekleme veya düzenleme diyalogunu açar."""
        try:
            data = None
            item_id_to_process = None

            if edit_mode:
                if not self.selected_item_id:
                    QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir stok kartı seçin.")
                    return
                item_id_to_process = self.selected_item_id
                data = self.db.get_stock_item_details(item_id_to_process)
                if not data:
                    QMessageBox.critical(self, "Hata", "Seçili stok kartının detayları alınamadı.")
                    return
                dialog = StockItemDialog(data=data, parent=self)
            else:
                dialog = StockItemDialog(item_type=item_type or 'Yedek Parça', parent=self)

            if dialog.exec():
                form_data = dialog.get_data()
                if not form_data.get('name'):
                    QMessageBox.warning(self, "Eksik Bilgi", "İsim/Model alanı boş bırakılamaz.")
                    return
                
                # save_stock_item, item_id'yi ikinci argüman olarak bekliyor
                saved_id = self.db.save_stock_item(form_data, item_id_to_process)
                
                if saved_id:
                    
                    # Eğer yeni cihaz eklendiyse, toner ve kit ekleme sistemi çalıştır
                    if not edit_mode and item_type == 'Cihaz':
                        
                        # Önce manuel girilen tonerleri ekle
                        manual_toners_added = self.add_manual_toners_to_stock(dialog)
                        
                        # Eğer manuel toner girilmemişse, otomatik ekleme yap
                        # if not manual_toners_added:
                        #     self.add_device_toners_to_stock(form_data.get('name', ''))
                        #     self.add_device_kits_to_stock(form_data.get('name', ''))
                        
                        # Manuel girilen kitleri ekle
                        self.add_manual_kits_to_stock(dialog)
                    
                    self.refresh_data()
                    self.data_changed.emit()
                    # Yeni eklenen veya güncellenen öğeyi seçili hale getir
                    self.select_item_in_table(saved_id)
                else:
                    QMessageBox.critical(self, "Veritabanı Hatası", "Stok kartı kaydedilemedi.")

        except Exception as e:
            logging.error(f"Stok kartı penceresi açılırken hata oluştu: {e}", exc_info=True)
            QMessageBox.critical(self, "Diyalog Hatası", f"Stok kartı penceresi açılamadı: {e}")

    def add_manual_toners_to_stock(self, dialog):
        """Dialog'dan girilen manuel toner kodlarını stoka ekler. Akıllı renk kodu ve muadil/orijinal ayrımı ile ekler."""
        if not hasattr(self, 'operation_logs'):
            self.operation_logs = []
        try:
            toner_data = dialog.get_toner_data()
            color_type = dialog.color_type_combo.currentText() if hasattr(dialog, 'color_type_combo') else 'Siyah-Beyaz'
            added_toners = []
            if color_type == 'Renkli':
                renkler = [
                    ('Siyah', 'K'),
                    ('Mavi', 'C'),
                    ('Kırmızı', 'M'),
                    ('Sarı', 'Y')
                ]
                base_code = toner_data.get('black') or ''
                muadil_code = toner_data.get('black_equivalent') or ''

                # Orijinal tonerler (4 renkli set)
                if base_code:
                    for renk_ad, renk_suffix in renkler:
                        toner_name = f"{base_code}-{renk_suffix}"
                        part_number = f"{base_code}-{renk_suffix}"
                        color_type_val = renk_ad
                        existing = self.db.fetch_one(
                            "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                            (toner_name, part_number)
                        )
                        if not existing:
                            new_toner_data = {
                                'item_type': 'Toner',
                                'name': toner_name,
                                'part_number': part_number,
                                'description': f"{renk_ad} Toner - Orijinal - Otomatik eklendi",
                                'quantity': 0,
                                'purchase_price': 0.0,
                                'purchase_currency': 'TL',
                                'sale_price': 0.0,
                                'sale_currency': 'TL',
                                'supplier': '',
                                'is_consignment': 0,
                                'color_type': color_type_val
                            }
                            saved_id = self.db.save_stock_item(new_toner_data, None)
                            if saved_id:
                                added_toners.append(f"{renk_ad} Orijinal: {toner_name}")
                                log_msg = f"Manuel toner eklendi: {renk_ad} Orijinal: {toner_name}"
                                logging.info(log_msg)
                                self.operation_logs.append(log_msg)

                # Muadil tonerler (4 renkli set)
                if muadil_code:
                    # Eğer muadil kod zaten -K, -C gibi bitiyorsa, temel kodu çıkar
                    ana_kod = muadil_code
                    for suf in ['-K', '-C', '-M', '-Y']:
                        if muadil_code.endswith(suf):
                            ana_kod = muadil_code[:-2]
                            break
                    for renk_ad, renk_suffix in renkler:
                        toner_name_muadil = f"{ana_kod}-{renk_suffix} (Muadil)"
                        part_number_muadil = f"{ana_kod}-{renk_suffix} (Muadil)"  # 👈 Burada (Muadil) eklendi
                        color_type_val = renk_ad
                        existing_muadil = self.db.fetch_one(
                            "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                            (toner_name_muadil, part_number_muadil)
                        )
                        if not existing_muadil:
                            new_toner_data_muadil = {
                                'item_type': 'Toner',
                                'name': toner_name_muadil,
                                'part_number': part_number_muadil,
                                'description': f"{renk_ad} Toner - Muadil - Otomatik eklendi",
                                'quantity': 0,
                                'purchase_price': 0.0,
                                'purchase_currency': 'TL',
                                'sale_price': 0.0,
                                'sale_currency': 'TL',
                                'supplier': '',
                                'is_consignment': 0,
                                'color_type': color_type_val
                            }
                            saved_id = self.db.save_stock_item(new_toner_data_muadil, None)
                            if saved_id:
                                added_toners.append(f"{renk_ad} Muadil: {toner_name_muadil}")
                                log_msg = f"Manuel toner eklendi: {renk_ad} Muadil: {toner_name_muadil}"
                                logging.info(log_msg)
                                self.operation_logs.append(log_msg)

                # Kullanıcı ayrı ayrı renk kodları girdiyse (manuel override)
                manual_colors = [
                    ('cyan', 'Mavi'),
                    ('magenta', 'Kirmizi'),
                    ('yellow', 'Sari')
                ]
                for field, renk_ad in manual_colors:
                    kod = toner_data.get(field)
                    kod_muadil = toner_data.get(f"{field}_equivalent")
                    # Orijinal
                    if kod:
                        toner_name = kod
                        part_number = kod
                        existing = self.db.fetch_one(
                            "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                            (toner_name, part_number)
                        )
                        if not existing:
                            new_toner_data = {
                                'item_type': 'Toner',
                                'name': toner_name,
                                'part_number': part_number,
                                'description': f"{renk_ad} Toner - Orijinal - Manuel girildi",
                                'quantity': 0,
                                'purchase_price': 0.0,
                                'purchase_currency': 'TL',
                                'sale_price': 0.0,
                                'sale_currency': 'TL',
                                'supplier': '',
                                'is_consignment': 0,
                                'color_type': renk_ad
                            }
                            saved_id = self.db.save_stock_item(new_toner_data, None)
                            if saved_id:
                                added_toners.append(f"{renk_ad} Orijinal: {toner_name}")
                                log_msg = f"Manuel toner eklendi: {renk_ad} Orijinal: {toner_name}"
                                logging.info(log_msg)
                                self.operation_logs.append(log_msg)
                    # Muadil
                    if kod_muadil:
                        toner_name = f"{kod_muadil} (Muadil)"
                        part_number = f"{kod_muadil} (Muadil)"  # 👈 Burada da (Muadil) eklendi
                        existing = self.db.fetch_one(
                            "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                            (toner_name, part_number)
                        )
                        if not existing:
                            new_toner_data = {
                                'item_type': 'Toner',
                                'name': toner_name,
                                'part_number': part_number,
                                'description': f"{renk_ad} Toner - Muadil - Manuel girildi",
                                'quantity': 0,
                                'purchase_price': 0.0,
                                'purchase_currency': 'TL',
                                'sale_price': 0.0,
                                'sale_currency': 'TL',
                                'supplier': '',
                                'is_consignment': 0,
                                'color_type': renk_ad
                            }
                            saved_id = self.db.save_stock_item(new_toner_data, None)
                            if saved_id:
                                added_toners.append(f"{renk_ad} Muadil: {toner_name}")
                                log_msg = f"Manuel toner eklendi: {renk_ad} Muadil: {toner_name}"
                                logging.info(log_msg)
                                self.operation_logs.append(log_msg)

            else:
                # Siyah-beyaz cihaz
                base_code = toner_data.get('black') or ''
                muadil_code = toner_data.get('black_equivalent') or ''
                if base_code:
                    toner_name = base_code
                    part_number = base_code
                    existing = self.db.fetch_one(
                        "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                        (toner_name, part_number)
                    )
                    if not existing:
                        new_toner_data = {
                            'item_type': 'Toner',
                            'name': toner_name,
                            'part_number': part_number,
                            'description': "Siyah Toner - Orijinal - Otomatik eklendi",
                            'quantity': 0,
                            'purchase_price': 0.0,
                            'purchase_currency': 'TL',
                            'sale_price': 0.0,
                            'sale_currency': 'TL',
                            'supplier': '',
                            'is_consignment': 0,
                            'color_type': 'Siyah'
                        }
                        saved_id = self.db.save_stock_item(new_toner_data, None)
                        if saved_id:
                            added_toners.append(f"Siyah Orijinal: {toner_name}")
                            log_msg = f"Manuel toner eklendi: Siyah Orijinal: {toner_name}"
                            logging.info(log_msg)
                            self.operation_logs.append(log_msg)
                if muadil_code:
                    toner_name_muadil = f"{muadil_code} (Muadil)"
                    part_number_muadil = f"{muadil_code} (Muadil)"  # 👈 Burada da düzeltildi
                    existing_muadil = self.db.fetch_one(
                        "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                        (toner_name_muadil, part_number_muadil)
                    )
                    if not existing_muadil:
                        new_toner_data_muadil = {
                            'item_type': 'Toner',
                            'name': toner_name_muadil,
                            'part_number': part_number_muadil,
                            'description': "Siyah Toner - Muadil - Otomatik eklendi",
                            'quantity': 0,
                            'purchase_price': 0.0,
                            'purchase_currency': 'TL',
                            'sale_price': 0.0,
                            'sale_currency': 'TL',
                            'supplier': '',
                            'is_consignment': 0,
                            'color_type': 'Siyah'
                        }
                        saved_id = self.db.save_stock_item(new_toner_data_muadil, None)
                        if saved_id:
                            added_toners.append(f"Siyah Muadil: {toner_name_muadil}")
                            log_msg = f"Manuel toner eklendi: Siyah Muadil: {toner_name_muadil}"
                            logging.info(log_msg)
                            self.operation_logs.append(log_msg)

            if added_toners:
                toner_list = "\n".join(added_toners)
                QMessageBox.information(
                    self,
                    "Manuel Toner Ekleme",
                    f"✅ Aşağıdaki tonerler stoka eklendi:\n{toner_list}\n"
                    f"💡 Fiyat ve miktar bilgilerini sonradan güncelleyebilirsiniz."
                )
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Akıllı toner ekleme hatası: {e}", exc_info=True)
            QMessageBox.warning(self, "Uyarı", f"Toner ekleme sırasında hata: {e}")
            return False

    def add_manual_kits_to_stock(self, dialog):
        """Dialog'dan girilen manuel kit kodlarını stoka ekler. Kit eklenirse True, eklenmezse False döner."""
        try:
            kit_data = dialog.get_kit_data()
            
            if not kit_data:
                return False
                
            added_kits = []
            
            for kit_order, kit_code in kit_data.items():
                
                if not kit_code.strip():
                    continue
                    
                # Kit zaten stokta var mı kontrol et
                existing = self.db.fetch_one(
                    "SELECT id FROM stock_items WHERE item_type = 'Kit' AND (name = ? OR part_number = ?)",
                    (kit_code, kit_code)
                )
                
                if existing:
                    continue  # Zaten var, eklemiyoruz
                    
                # Yeni kit kartı oluştur
                new_kit_data = {
                    'item_type': 'Kit',
                    'name': kit_code,
                    'part_number': kit_code,
                    'description': f"Bakım Kiti - Manuel olarak eklendi",
                    'quantity': 0,  # Başlangıçta 0 adet
                    'purchase_price': 0.0,
                    'purchase_currency': 'TL',
                    'sale_price': 0.0,
                    'sale_currency': 'TL',
                    'supplier': '',
                    'is_consignment': 0
                }
                
                saved_id = self.db.save_stock_item(new_kit_data, None)
                
                if saved_id:
                    added_kits.append(kit_code)
            
            if added_kits:
                kit_list = "\n".join(added_kits)
                QMessageBox.information(
                    self, 
                    "Manuel Kit Ekleme",
                    f"✅ Aşağıdaki kitler stoka eklendi:\n\n{kit_list}\n\n"
                    f"💡 Fiyat ve miktar bilgilerini sonradan güncelleyebilirsiniz."
                )
                return True  # Manuel kit eklendi
            else:
                return False  # Hiç kit eklenmedi
                
        except Exception as e:
            logging.error(f"Manuel kit ekleme hatası: {e}", exc_info=True)
            QMessageBox.warning(self, "Uyarı", f"Manuel kit ekleme sırasında hata: {e}")
            return False

    def add_device_toners_to_stock(self, device_model):
        """Cihazın tonerlerini otomatik olarak stoka ekler."""
        try:
            from utils.kyocera_compatibility_scraper import suggest_missing_toners_for_device
            from utils.device_toner_compatibility import find_compatible_toners
            # Cihazın uyumlu tonerlerini bul
            missing_toners = suggest_missing_toners_for_device(device_model, self.db)
            # Muadil tonerleri de ekle
            compatible_toners = find_compatible_toners(device_model)
            for toner_code in compatible_toners:
                existing = self.db.fetch_one(
                    "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?)",
                    (toner_code, toner_code)
                )
                if not existing:
                    toner_data = {
                        'item_type': 'Toner',
                        'name': f"{toner_code} (Muadil)",
                        'part_number': toner_code,
                        'description': f"Muadil toner - {device_model} uyumlu",
                        'supplier': '',
                        'quantity': 0,
                        'purchase_price': 0.00,
                        'purchase_currency': 'TL',
                        'sale_price': 0.00,
                        'sale_currency': 'TL',
                        'color_type': ''
                    }
                    self.db.save_stock_item(toner_data, None)
            # Orijinal tonerler ekleniyor
            if not missing_toners:
                logging.info(f"Cihaz {device_model} için toner bulunamadı veya zaten stokta mevcut")
                return
            # Tonerleri stoka ekle
            added_count = 0
            toner_names = []
            for toner in missing_toners:
                try:
                    toner_data = {
                        'item_type': 'Toner',
                        'name': toner['toner_code'],
                        'part_number': toner['toner_code'],
                        'description': f"Kyocera {toner['color_type']} Toner - {toner['print_capacity']} sayfa kapasiteli - {device_model} uyumlu",
                        'supplier': 'Kyocera',
                        'quantity': 0,
                        'purchase_price': 0.00,
                        'purchase_currency': 'TL',
                        'sale_price': 0.00,
                        'sale_currency': 'TL',
                        'color_type': toner['color_type']
                    }
                    saved_id = self.db.save_stock_item(toner_data, None)
                    if saved_id:
                        added_count += 1
                        toner_names.append(toner['toner_code'])
                        logging.info(f"Toner stoka eklendi: {toner['toner_code']}")
                except Exception as toner_error:
                    logging.warning(f"Toner eklenemedi {toner['toner_code']}: {toner_error}")
                    continue
            if added_count > 0:
                QMessageBox.information(
                    self, "Otomatik Toner Eklendi",
                    f"✅ Cihaz '{device_model}' için {added_count} adet toner otomatik olarak stoka eklendi:\n\n"
                    f"📝 Tonerler: {', '.join(toner_names)}\n\n"
                    f"💡 Bu tonerlerin fiyatlarını ve stok miktarlarını güncelleyebilirsiniz."
                )
                logging.info(f"Cihaz {device_model} için {added_count} adet toner stoka eklendi")
        except Exception as e:
            logging.error(f"Otomatik toner ekleme hatası: {e}")
            # Toner ekleme hatası cihaz kaydetmeyi engellemez

    def add_device_kits_to_stock(self, device_model):
        """Cihazın kitlerini otomatik olarak stoka ekler."""
        # Uyumluluk sistemi kaldırıldı - manuel kit ekleme
        QMessageBox.information(
            self, "Bilgi",
            f"'{device_model}' için kit ekleme özelliği devre dışı bırakıldı.\n\n"
            f"Kitleri manuel olarak stok ekleme bölümünden ekleyebilirsiniz."
        )

    def stock_table_cell_changed(self, row, column):
        # Sadece isim/model (2) ve miktar (4) alanı düzenlenebilir
        if column not in [2, 4]:
            return
            
        item_0 = self.stock_table.item(row, 0)
        item_col = self.stock_table.item(row, column)
        
        if not item_0 or not item_col:
            return
            
        item_id = item_0.text()
        new_value = item_col.text()
        
        if column == 2:
            if hasattr(self.db, 'update_stock_item_name'):
                self.db.update_stock_item_name(item_id, new_value)
        elif column == 4:
            try:
                new_qty = int(new_value)
                if hasattr(self.db, 'update_stock_item_quantity'):
                    self.db.update_stock_item_quantity(item_id, new_qty)
            except Exception:
                QMessageBox.warning(self, "Hatalı Giriş", "Miktar sayısal olmalıdır.")
                self.refresh_data()
            
    def stock_table_double_clicked(self, item):
        """Stok tablosunda çift tıklama yapıldığında hangi sütuna göre farklı işlem yapar."""
        if not item:
            return
        
        row = item.row()
        column = item.column()
        item_0 = self.stock_table.item(row, 0)
        
        if not item_0:
            return
        
        try:
            # Seçili satırı işaretle
            self.stock_table.selectRow(row)
            
            # Sütuna göre farklı işlemler
            if column == 4:  # Miktar sütunu - Hızlı stok giriş diyalogu aç
                # Önce seçimi güncelle
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self._open_quick_stock_entry)
            elif column == 2:  # İsim/Model sütunu - Stok kartı düzenleme diyalogu aç
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, lambda: self.open_item_dialog(edit_mode=True))
            # Diğer sütunlara çift tıklama için bir işlem yapma
                
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İşlem sırasında hata oluştu: {e}")
    
    def _open_quick_stock_entry(self):
        """Hızlı stok giriş diyalogunu açar."""
        if not self.selected_item_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir stok kartı seçin.")
            return
        
        try:
            # Seçili stok kartının bilgilerini al
            item_name = self.name_label.text() or "Bilinmeyen Ürün"
            current_quantity = int(self.quantity_label.text() or "0")
            
            # Hızlı stok giriş diyalogunu import et ve aç
            from ui.dialogs.stock_dialogs import QuickStockEntryDialog
            
            dialog = QuickStockEntryDialog(
                item_name=item_name,
                current_quantity=current_quantity,
                parent=self
            )
            
            if dialog.exec():
                # Kullanıcı stok girişi yaptı
                entry_data = dialog.get_data()
                
                # Stok hareket kaydı oluştur
                result = self.db.add_stock_movement(
                    self.selected_item_id, 
                    "Giriş", 
                    entry_data['quantity'], 
                    entry_data['notes'] or "Hızlı stok girişi"
                )
                
                if result == "Yetersiz Stok":
                    QMessageBox.critical(
                        self, 
                        "Yetersiz Stok", 
                        "Çıkış yapmak istediğiniz miktar mevcut stoktan fazla!"
                    )
                    return
                    
                # Başarılı ise stok listesini güncelle
                self.refresh_data()
                self.data_changed.emit()
                
                QMessageBox.information(
                    self, 
                    "Stok Girişi Tamamlandı", 
                    f"✅ {entry_data['quantity']} adet stok girişi yapıldı.\n"
                    f"📝 Not: {entry_data['notes'] or 'Yok'}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hızlı stok giriş işlemi başarısız:\n{str(e)}")
            
    def open_movement_dialog(self, movement_type):
        """Stok giriş/çıkış diyalogunu açar."""
        if not self.selected_item_id: return
        try:
            item_name = self.name_label.text()
            dialog = StockMovementDialog(item_name, movement_type, self)
            if dialog.exec():
                data = dialog.get_data()
                result = self.db.add_stock_movement(self.selected_item_id, movement_type, data['quantity'], data['notes'])
                if result == "Yetersiz Stok":
                    QMessageBox.critical(self, "İşlem İptal Edildi", "Yetersiz stok! Çıkış yapmak istediğiniz miktar mevcut stoktan fazla olamaz.")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Diyalog Hatası", f"Stok hareket penceresi açılamadı: {e}")
            
    def open_device_sale_dialog(self):
        """Toplu cihaz satışı diyalogunu açar."""
        if not self.selected_item_id or self.selected_item_type != 'Cihaz':
            return
        
        try:
            device_info = self.db.get_stock_item_details(self.selected_item_id)
            if not device_info:
                QMessageBox.critical(self, "Hata", "Cihaz detayları alınamadı.")
                return

            if device_info.get('quantity', 0) < 1:
                QMessageBox.warning(self, "Stokta Yok", "Bu cihazdan stokta kalmamış.")
                return

            dialog = BulkDeviceSaleDialog(self.db, device_info, self)
            if dialog.exec():
                sale_data = dialog.get_data()
                if sale_data:
                    result = self.db.sell_bulk_stock_devices_to_customer(
                        stock_item_id=self.selected_item_id,
                        customer_id=sale_data['customer_id'],
                        sale_price=sale_data['sale_price'],
                        sale_currency=sale_data['sale_currency'],
                        serial_numbers=sale_data['serial_numbers']
                    )
                    if result is True:
                        QMessageBox.information(self, "Başarılı", f"{len(sale_data['serial_numbers'])} adet cihaz satışı başarıyla tamamlandı.")
                        self.data_changed.emit()
                        self.refresh_data()
                    else:
                        QMessageBox.critical(self, "Satış Hatası", str(result))
        except Exception as e:
            QMessageBox.critical(self, "Diyalog Hatası", f"Cihaz satış penceresi açılamadı: {e}")

    def select_item_in_table(self, item_id: int):
        """Verilen ID'ye sahip öğeyi tabloda bulur ve seçer."""
        for row in range(self.stock_table.rowCount()):
            item = self.stock_table.item(row, 0)
            if item and int(item.text()) == item_id:
                self.stock_table.selectRow(row)
                return

    def open_purchase_invoice_dialog(self):
        from ui.dialogs.purchase_invoice_dialog import PurchaseInvoiceDialog
        dialog = PurchaseInvoiceDialog(self.db, self)
        if dialog.exec():
            self.refresh_stock_list()

    def open_stock_settings_dialog(self):
        """Stok ayarları diyalogunu açar."""
        from ui.dialogs.stock_settings_dialog import StockSettingsDialog
        dialog = StockSettingsDialog(self.db, self)
        dialog.exec()

    def open_price_settings_dialog(self):
        """Fiyat ayarları diyalogunu açar."""
        from ui.dialogs.price_settings_dialog import PriceSettingsDialog
        dialog = PriceSettingsDialog(self.db, self)
        if dialog.exec():
            # Fiyat ayarları değiştiğinde tabloyu yenile
            self.refresh_data()

    def filter_stock_items(self):
        """Stok öğelerini filtreler - Case insensitive"""
        search_text = self.filter_input.text().strip().lower()  # Küçük harfe çevir
        
        if not search_text:
            self.refresh_data()
            return
        
        try:
            cursor = self.db.get_connection().cursor()
            
            # Case insensitive arama - LOWER() fonksiyonu kullan
            cursor.execute("""
                SELECT id, item_type, name, part_number, quantity, unit_price, supplier
                FROM stock_items 
                WHERE LOWER(name) LIKE ? 
                   OR LOWER(part_number) LIKE ? 
                   OR LOWER(supplier) LIKE ?
                   OR LOWER(item_type) LIKE ?
                ORDER BY name
            """, (f'%{search_text}%', f'%{search_text}%', f'%{search_text}%', f'%{search_text}%'))
            
            # Tabloyu temizle
            self.stock_table.setRowCount(0)
            
            # Filtrelenmiş sonuçları ekle
            for row_num, row_data in enumerate(cursor.fetchall()):
                self.stock_table.insertRow(row_num)
                for col_num, data in enumerate(row_data):
                    self.stock_table.setItem(row_num, col_num, QTableWidgetItem(str(data)))
            
            logging.info(f"Stok filtrelendi: '{search_text}' - {self.stock_table.rowCount()} sonuç")
            
        except Exception as e:
            logging.error(f"Stok filtreleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Filtreleme hatası:\n{str(e)}")
            
    def open_device_analysis_dialog(self):
        """Cihaz-Toner analiz dialog'unu açar."""
        from ui.dialogs.device_analysis_dialog import DeviceAnalysisDialog
        dialog = DeviceAnalysisDialog(self.db, self)
        dialog.exec()

    # --- CPC Stok Yönetimi ---

    def _create_cpc_left_panel(self):
        """CPC stok listesini içeren sol paneli oluşturur."""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        
        # Filtre alanı
        filter_layout = QHBoxLayout()
        self.cpc_filter_input = QLineEdit()
        self.cpc_filter_input.setPlaceholderText("Cihaz modeli veya müşteri adı ile ara...")
        filter_layout.addWidget(self.cpc_filter_input)
        
        # CPC cihaz listesi
        cpc_group = QGroupBox("🔄 CPC Cihaz Listesi")
        cpc_layout = QVBoxLayout(cpc_group)
        
        self.cpc_device_table = QTableWidget(0, 6)
        self.cpc_device_table.setHorizontalHeaderLabels(["ID", "Müşteri", "Telefon", "Lokasyon", "Tip", "Renk"])
        self.cpc_device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cpc_device_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.cpc_device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Düzenleme kapalı
        
        # Sütun genişliklerini kullanıcıya bırak, ayarları QSettings ile sakla
        from PyQt6.QtCore import QSettings
        header = self.cpc_device_table.horizontalHeader()
        if header:
            from PyQt6.QtWidgets import QHeaderView
            for col in range(self.cpc_device_table.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            
            settings = QSettings("ProServis", "CPCStok")
            for col in range(self.cpc_device_table.columnCount()):
                width = settings.value(f"cpc_col_width_{col}", None, type=int)
                if width:
                    self.cpc_device_table.setColumnWidth(col, width)
            
            def save_column_widths():
                for c in range(self.cpc_device_table.columnCount()):
                    settings.setValue(f"cpc_col_width_{c}", self.cpc_device_table.columnWidth(c))
            
            header.sectionResized.connect(lambda idx, old, new: save_column_widths())
        
        self.cpc_device_table.hideColumn(0)
        cpc_layout.addWidget(self.cpc_device_table)
        
        # CPC toner listesi
        toner_group = QGroupBox("🖨️ CPC Toner Listesi (Seçili Cihaz)")
        toner_layout = QVBoxLayout(toner_group)
        
        self.cpc_toner_table = QTableWidget(0, 4)
        self.cpc_toner_table.setHorizontalHeaderLabels(["ID", "Toner Kodu", "Renk", "Miktar"])
        self.cpc_toner_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cpc_toner_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Sütun genişliklerini özelleştir
        toner_header = self.cpc_toner_table.horizontalHeader()
        if toner_header:
            toner_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID - gizli
            toner_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Toner Kodu - esnek
            toner_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Renk - sabit
            toner_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Miktar - sabit
        
        self.cpc_toner_table.setColumnWidth(2, 80)  # Renk
        self.cpc_toner_table.setColumnWidth(3, 70)  # Miktar
        
        self.cpc_toner_table.hideColumn(0)
        toner_layout.addWidget(self.cpc_toner_table)
        
        # Layout'a ekle
        layout.addLayout(filter_layout)
        layout.addWidget(cpc_group, 1)
        layout.addWidget(toner_group, 1)
        
        return panel

    def _create_cpc_right_panel(self):
        """CPC stok detaylarını ve butonları içeren sağ paneli oluşturur."""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.add_cpc_toner_btn = QPushButton("➕ Toner Ekle")
        self.view_cpc_history_btn = QPushButton("📋 Kullanım Geçmişi")
        
        button_layout.addWidget(self.add_cpc_toner_btn)
        button_layout.addWidget(self.view_cpc_history_btn)
        button_layout.addStretch()
        
        # Detay grubu
        details_group = QGroupBox("CPC Stok Detayları")
        details_layout = QVBoxLayout(details_group)
        
        self.cpc_details_text = QTextEdit()
        self.cpc_details_text.setReadOnly(True)
        self.cpc_details_text.setMaximumHeight(200)
        details_layout.addWidget(self.cpc_details_text)
        
        layout.addLayout(button_layout)
        layout.addWidget(details_group)
        layout.addStretch()
        
        return panel

    # === CPC Fonksiyonları (CPCStockManager'a yönlendirilir) ===
    
    def load_cpc_devices(self):
        """CPC cihazlarını listeler - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.load_cpc_devices()
    
    def cpc_device_selected(self):
        """CPC cihaz seçimi - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.cpc_device_selected()
    
    def load_cpc_toners(self, device_id: int):
        """CPC tonerlerini listeler - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.load_cpc_toners(device_id)
    
    def add_toners_for_cpc_device(self, device_id: int, device_model: str):
        """CPC toner ekler - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.add_toners_for_cpc_device(device_id, device_model)
    
    def add_manual_toners_to_stock_for_cpc(self, dialog, device_id: int, device_model: str, device_color_type: str) -> int:
        """Manuel toner ekler - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.add_manual_toners_to_stock_for_cpc(dialog, device_id, device_model, device_color_type)
    
    def add_manual_kits_to_stock_for_cpc(self, dialog, device_id: int, device_model: str) -> int:
        """Manuel kit ekler - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.add_manual_kits_to_stock_for_cpc(dialog, device_id, device_model)
    
    def filter_cpc_devices(self):
        """CPC cihaz filtresi - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.filter_cpc_devices()
    
    def add_cpc_toner(self):
        """CPC toner ekle butonu - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.add_cpc_toner()
    
    def view_cpc_history(self):
        """CPC geçmiş - CPCStockManager'a yönlendirir."""
        return self.cpc_manager.view_cpc_history()

    def tab_changed(self, index: int):
        """Tab değiştiğinde çağrılır."""
        if index == 1:  # CPC Stok tabı
            self.load_cpc_devices()
        elif index == 0:  # Normal Stok tabı
            self.refresh_data()

    def cpc_device_double_clicked(self, item):
        """CPC cihaz çift tıklama - dialog açar."""
        row = item.row()
        item_id = self.cpc_device_table.item(row, 0)
        item_model = self.cpc_device_table.item(row, 5)
        
        if not item_id or not item_model:
            return
            
        device_id = int(item_id.text())
        device_model = item_model.text()
        self.add_toners_for_cpc_device(device_id, device_model)
    
    # === Normal Stok Fonksiyonları ===

    def handle_stock_entry_from_dialog(self, item_name: str, quantity_change: int, notes: str):
        """
        Stok kartı düzenleme diyalogundan gelen stok giriş talebini işler.
        
        Args:
            item_name: Stok öğesinin adı
            quantity_change: Miktar değişimi (pozitif değer stok girişi)
            notes: Stok hareket notu
        """
        try:
            if not self.selected_item_id:
                QMessageBox.warning(self, "Hata", "Seçili stok öğesi bulunamadı!")
                return
            
            # Stok hareket kaydı oluştur
            movement_type = "Giriş" if quantity_change > 0 else "Çıkış"
            movement_data = {
                'quantity': abs(quantity_change),
                'notes': notes or f"Kart düzenlemeden {movement_type.lower()}"
            }
            
            # Veritabanında stok hareketi kaydet
            result = self.db.add_stock_movement(
                self.selected_item_id, 
                movement_type, 
                movement_data['quantity'], 
                movement_data['notes']
            )
            
            if result == "Yetersiz Stok":
                QMessageBox.critical(
                    self, 
                    "Yetersiz Stok", 
                    "Çıkış yapmak istediğiniz miktar mevcut stoktan fazla!"
                )
                return
                
            # Başarılı ise stok listesini güncelle
            self.refresh_data()
            self.data_changed.emit()
            
            logging.info(f"Dialog'dan stok {movement_type.lower()}: {item_name} - {movement_data['quantity']} adet")
            
        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"Stok işlemi başarısız: {e}")

    # === 2. El Cihaz Fonksiyonları ===

    def refresh_second_hand_stock(self):
        """2. El cihaz stok listesini yeniler."""
        self.second_hand_table.setRowCount(0)

        query = '''
            SELECT shd.id, shd.device_model, shd.serial_number,
                   COALESCE(c.name, shd.source_person) as source_person,
                   shd.acquisition_date, shd.purchase_price, COALESCE(shd.sale_price, 0) as sale_price,
                   shd.status, shd.notes
            FROM second_hand_devices shd
            LEFT JOIN customers c ON c.id = shd.customer_id
            ORDER BY shd.acquisition_date DESC
        '''

        try:
            devices = self.db.fetch_all(query)
            for row_idx, device in enumerate(devices):
                self.second_hand_table.insertRow(row_idx)
                self.second_hand_table.setItem(row_idx, 0, QTableWidgetItem(str(device['id'])))
                self.second_hand_table.setItem(row_idx, 1, QTableWidgetItem(device['device_model'] or ''))
                self.second_hand_table.setItem(row_idx, 2, QTableWidgetItem(device['serial_number'] or ''))
                self.second_hand_table.setItem(row_idx, 3, QTableWidgetItem(device['source_person'] or ''))
                self.second_hand_table.setItem(row_idx, 4, QTableWidgetItem(device['acquisition_date'] or ''))
                self.second_hand_table.setItem(row_idx, 5, QTableWidgetItem(str(device['purchase_price'] or 0)))

                # Satış fiyatı ve kâr marjı hesapla
                purchase_price = float(device['purchase_price'] or 0)
                sale_price = float(device['sale_price'] or (purchase_price * 1.3))  # Varsayılan %30 kâr
                profit_margin = sale_price - purchase_price

                self.second_hand_table.setItem(row_idx, 6, QTableWidgetItem(f"{sale_price:.2f}"))
                self.second_hand_table.setItem(row_idx, 7, QTableWidgetItem(device['status'] or 'Stokta'))
                self.second_hand_table.setItem(row_idx, 8, QTableWidgetItem(f"{profit_margin:.2f}"))
                self.second_hand_table.setItem(row_idx, 9, QTableWidgetItem(device['notes'] or ''))
                
                # Kâr marjı rengini ayarla
                profit_item = self.second_hand_table.item(row_idx, 8)
                if profit_item and profit_margin > 0:
                    profit_item.setForeground(Qt.GlobalColor.darkGreen)
                elif profit_item and profit_margin < 0:
                    profit_item.setForeground(Qt.GlobalColor.red)
                    
        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"2. El cihaz listesi yüklenemedi: {e}")

        # Liste yenilendikten sonra filtre uygula
        self.filter_second_hand_devices()

    def filter_second_hand_devices(self):
        """2. El cihaz listesini arama kutusuna göre filtreler."""
        if not hasattr(self, 'second_hand_filter_input'):
            return
        filter_text = self.second_hand_filter_input.text().strip().lower()
        for row in range(self.second_hand_table.rowCount()):
            model_item = self.second_hand_table.item(row, 1)
            serial_item = self.second_hand_table.item(row, 2)
            source_item = self.second_hand_table.item(row, 3)
            haystack = " ".join([
                model_item.text() if model_item else "",
                serial_item.text() if serial_item else "",
                source_item.text() if source_item else ""
            ]).lower()
            self.second_hand_table.setRowHidden(row, filter_text not in haystack)

    def add_second_hand_device(self):
        """Yeni 2. El cihaz ekler."""
        try:
            from PyQt6.QtWidgets import (
                QDialog, QFormLayout, QLineEdit, QComboBox, QPushButton, QDialogButtonBox,
                QCheckBox, QListWidget, QListWidgetItem, QHBoxLayout, QLabel, QWidget, QVBoxLayout
            )
            
            dialog = QDialog(self)
            dialog.setWindowTitle("2. El Cihaz Ekle")
            dialog.setMinimumWidth(400)
            layout = QFormLayout(dialog)
            
            # Form alanları
            model_input = QLineEdit()
            serial_input = QLineEdit()
            source_input = QLineEdit()
            date_input = QLineEdit()
            date_input.setPlaceholderText("YYYY-MM-DD")
            price_input = QLineEdit()
            sale_price_input = QLineEdit()
            notes_input = QLineEdit()
            reason_input = QLineEdit()
            status_combo = QComboBox()
            status_combo.addItems(['Stokta', 'Serviste', 'Satıldı'])
            
            # Varsayılan değerler
            from datetime import datetime
            date_input.setText(datetime.now().strftime("%Y-%m-%d"))
            
            # Müşteri cihazı seçimi alanı
            use_customer_device_chk = QCheckBox("Müşteri cihazından seç")
            customer_device_filter = QLineEdit()
            customer_device_filter.setPlaceholderText("Müşteri adı, model veya seri no ile ara...")
            customer_device_list = QListWidget()
            customer_device_list.setFixedHeight(120)
            clear_selection_btn = QPushButton("Seçimi Temizle")

            customer_device_container = QWidget()
            customer_device_layout = QVBoxLayout(customer_device_container)
            customer_device_layout.setContentsMargins(0, 0, 0, 0)
            customer_device_layout.addWidget(use_customer_device_chk)
            customer_device_layout.addWidget(customer_device_filter)
            customer_device_layout.addWidget(customer_device_list)
            customer_device_layout.addWidget(clear_selection_btn)

            # Müşteri cihazlarını yükle
            all_customer_devices = self.db.fetch_all("""
                SELECT cd.id as device_id, c.id as customer_id, c.name as customer_name,
                       cd.device_model, cd.serial_number
                FROM customer_devices cd
                JOIN customers c ON c.id = cd.customer_id
                ORDER BY c.name, cd.device_model
            """)

            selected_customer_device = {'device_id': None, 'customer_id': None, 'customer_name': '', 'device_model': '', 'serial_number': ''}

            def populate_customer_devices(filter_text: str = ""):
                customer_device_list.clear()
                if not all_customer_devices:
                    return
                ft = (filter_text or "").strip().lower()
                for row in all_customer_devices:
                    customer_name = row['customer_name'] or ''
                    device_model = row['device_model'] or ''
                    serial_number = row['serial_number'] or ''
                    haystack = f"{customer_name} {device_model} {serial_number}".lower()
                    if ft and ft not in haystack:
                        continue
                    display = f"{customer_name} | {device_model} | {serial_number}"
                    item = QListWidgetItem(display)
                    item.setData(Qt.ItemDataRole.UserRole, {
                        'device_id': row['device_id'],
                        'customer_id': row['customer_id'],
                        'customer_name': customer_name,
                        'device_model': device_model,
                        'serial_number': serial_number
                    })
                    customer_device_list.addItem(item)

            def set_customer_device_ui(enabled: bool):
                customer_device_filter.setEnabled(enabled)
                customer_device_list.setEnabled(enabled)
                clear_selection_btn.setEnabled(enabled)
                if not enabled:
                    model_input.setReadOnly(False)
                    serial_input.setReadOnly(False)
                    customer_device_list.clearSelection()

            def clear_customer_device_selection():
                selected_customer_device.update({
                    'device_id': None,
                    'customer_id': None,
                    'customer_name': '',
                    'device_model': '',
                    'serial_number': ''
                })
                customer_device_list.clearSelection()
                model_input.setReadOnly(False)
                serial_input.setReadOnly(False)

            def handle_device_selection():
                item = customer_device_list.currentItem()
                if not item:
                    return
                data = item.data(Qt.ItemDataRole.UserRole) or {}
                selected_customer_device.update({
                    'device_id': data.get('device_id'),
                    'customer_id': data.get('customer_id'),
                    'customer_name': data.get('customer_name', ''),
                    'device_model': data.get('device_model', ''),
                    'serial_number': data.get('serial_number', '')
                })
                model_input.setText(selected_customer_device['device_model'])
                serial_input.setText(selected_customer_device['serial_number'])
                source_input.setText(selected_customer_device['customer_name'])
                model_input.setReadOnly(True)
                serial_input.setReadOnly(True)

            use_customer_device_chk.toggled.connect(set_customer_device_ui)
            customer_device_filter.textChanged.connect(populate_customer_devices)
            customer_device_list.itemSelectionChanged.connect(handle_device_selection)
            clear_selection_btn.clicked.connect(clear_customer_device_selection)
            set_customer_device_ui(False)
            populate_customer_devices()

            layout.addRow("Cihaz Model:", model_input)
            layout.addRow("Seri No:", serial_input)
            layout.addRow("Alınan Kişi/Kurum:", source_input)
            layout.addRow("Alınma Tarihi:", date_input)
            layout.addRow("Alış Fiyatı:", price_input)
            layout.addRow("Satış Fiyatı:", sale_price_input)
            layout.addRow("Durum:", status_combo)
            layout.addRow("Alım Nedeni:", reason_input)
            layout.addRow("Notlar:", notes_input)
            layout.addRow("Müşteri Cihazı:", customer_device_container)
            
            # Butonlar
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Verileri kaydet
                reason_text = reason_input.text().strip()
                notes_text = notes_input.text().strip()
                if reason_text:
                    notes_text = f"{notes_text} | Alım nedeni: {reason_text}" if notes_text else f"Alım nedeni: {reason_text}"
                
                data = {
                    'device_model': model_input.text().strip(),
                    'serial_number': serial_input.text().strip(),
                    'source_person': source_input.text().strip(),
                    'acquisition_date': date_input.text().strip(),
                    'purchase_price': float(price_input.text() or 0),
                    'sale_price': float(sale_price_input.text() or 0),
                    'status': status_combo.currentText(),
                    'notes': notes_text
                }

                # Müşteri cihazından seçildiyse cihaz bilgilerini sabitle
                if selected_customer_device.get('device_id'):
                    data['device_model'] = selected_customer_device.get('device_model', data['device_model'])
                    data['serial_number'] = selected_customer_device.get('serial_number', data['serial_number'])
                    if selected_customer_device.get('customer_name'):
                        data['source_person'] = selected_customer_device.get('customer_name')
                
                if not data['device_model']:
                    QMessageBox.warning(self, "Uyarı", "Cihaz modeli boş olamaz!")
                    return
                
                # Veritabanına ekle
                query = '''
                    INSERT INTO second_hand_devices 
                    (device_model, serial_number, source_person, acquisition_date, purchase_price, sale_price, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''
                self.db.execute_query(query, (
                    data['device_model'], data['serial_number'], data['source_person'],
                    data['acquisition_date'], data['purchase_price'], data['sale_price'], 
                    data['status'], data['notes']
                ))

                # Müşteri cihazından alındıysa müşteri cihazını boşa al (customer_id = NULL)
                if selected_customer_device.get('device_id'):
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
                        (move_note, move_note, selected_customer_device['device_id'])
                    )
                
                # Normal stoka da ekle
                self._add_second_hand_to_normal_stock(data)
                
                self.refresh_second_hand_stock()
                self.refresh_data()
                QMessageBox.information(self, "Başarılı", "2. El cihaz başarıyla eklendi!")
                
        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"2. El cihaz eklenemedi: {e}")

    def edit_second_hand_device(self, item):
        """Seçili 2. El cihazı düzenleme dialogunu açar."""
        selection_model = self.second_hand_table.selectionModel()
        if not selection_model:
            return
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        id_item = self.second_hand_table.item(row, 0)
        if not id_item:
            return
        device_id = int(id_item.text())

        try:
            device = self.db.fetch_one(
                """
                SELECT shd.id, shd.device_model, shd.serial_number, shd.customer_id, shd.source_person,
                       shd.acquisition_date, shd.purchase_price, shd.sale_price, shd.status, shd.notes,
                       c.name as customer_name
                FROM second_hand_devices shd
                LEFT JOIN customers c ON c.id = shd.customer_id
                WHERE shd.id = ?
                """,
                (device_id,)
            )
            if not device:
                QMessageBox.warning(self, "Hata", "Cihaz bilgisi bulunamadı.")
                return

            old_model = device['device_model'] or ''
            old_serial = device['serial_number'] or ''
            old_status = device['status'] or 'Stokta'

            from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox
            from PyQt6.QtCore import pyqtSignal as Signal

            dialog = QDialog(self)
            dialog.setWindowTitle("2. El Cihaz Düzenle")
            dialog.setMinimumWidth(400)
            layout = QFormLayout(dialog)

            model_input = QLineEdit(device['device_model'] or "")
            serial_input = QLineEdit(device['serial_number'] or "")
            source_input = QLineEdit(device['customer_name'] or device['source_person'] or "")
            date_input = QLineEdit(device['acquisition_date'] or "")
            date_input.setPlaceholderText("YYYY-MM-DD")
            price_input = QLineEdit(str(device['purchase_price'] or 0))
            sale_price_input = QLineEdit(str(device['sale_price'] or 0))
            notes_input = QLineEdit(device['notes'] or "")
            status_combo = QComboBox()
            status_combo.addItems(['Stokta', 'Serviste', 'Satıldı', 'Hurda'])
            status_combo.setCurrentText(device['status'] or 'Stokta')

            layout.addRow("Cihaz Model:", model_input)
            layout.addRow("Seri No:", serial_input)
            layout.addRow("Alınan Kişi/Kurum:", source_input)
            layout.addRow("Alınma Tarihi:", date_input)
            layout.addRow("Alış Fiyatı:", price_input)
            layout.addRow("Satış Fiyatı:", sale_price_input)
            layout.addRow("Durum:", status_combo)
            layout.addRow("Notlar:", notes_input)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            data = {
                'device_model': model_input.text().strip(),
                'serial_number': serial_input.text().strip(),
                'source_person': source_input.text().strip(),
                'customer_id': device['customer_id'],
                'acquisition_date': date_input.text().strip(),
                'purchase_price': float(price_input.text() or 0),
                'sale_price': float(sale_price_input.text() or 0),
                'status': status_combo.currentText(),
                'notes': notes_input.text().strip()
            }

            if not data['device_model']:
                QMessageBox.warning(self, "Uyarı", "Cihaz modeli boş olamaz!")
                return

            self.db.execute_query(
                """
                UPDATE second_hand_devices
                SET device_model = ?, serial_number = ?, source_person = ?, customer_id = ?, acquisition_date = ?,
                    purchase_price = ?, sale_price = ?, status = ?, notes = ?
                WHERE id = ?
                """,
                (
                    data['device_model'], data['serial_number'], data['source_person'], data['customer_id'],
                    data['acquisition_date'], data['purchase_price'], data['sale_price'],
                    data['status'], data['notes'], device_id
                )
            )

            # Normal stok senkronizasyonu (Hurda olsa bile stokta kalsın)
            stock_item = self.db.fetch_one(
                "SELECT id FROM stock_items WHERE item_type = 'Cihaz' AND part_number = ?",
                (old_serial,)
            )
            if stock_item:
                self.db.execute_query(
                    """
                    UPDATE stock_items
                    SET name = ?, part_number = ?, sale_price = ?, description = ?
                    WHERE id = ?
                    """,
                    (
                        data['device_model'],
                        data['serial_number'],
                        data['sale_price'],
                        f"2. El cihaz - Alınan: {data['source_person']}",
                        stock_item['id']
                    )
                )

            self.refresh_second_hand_stock()
            self.refresh_data()
            QMessageBox.information(self, "Başarılı", "2. El cihaz güncellendi.")

        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"2. El cihaz güncellenemedi: {e}")

    def _add_second_hand_to_normal_stock(self, device_data):
        """2. El cihazı normal stoka ekler."""
        try:
            # Normal stokta var mı kontrol et
            existing = self.db.fetch_one(
                "SELECT id, quantity FROM stock_items WHERE name = ? AND item_type = 'Cihaz'",
                (device_data['device_model'],)
            )
            
            if existing:
                # Varsa miktarını artır
                new_quantity = existing['quantity'] + 1
                self.db.execute_query(
                    "UPDATE stock_items SET quantity = ? WHERE id = ?",
                    (new_quantity, existing['id'])
                )
                
                # Stok hareketi kaydet
                self.db.add_stock_movement(
                    existing['id'], 'Giriş', 1, 
                    f"2. El cihaz eklendi - Seri No: {device_data['serial_number']}"
                )
            else:
                # Yoksa yeni stok kaydı oluştur
                stock_data = {
                    'name': device_data['device_model'],
                    'item_type': 'Cihaz',
                    'part_number': device_data['serial_number'],
                    'quantity': 1,
                    'sale_price': device_data.get('sale_price') or (device_data['purchase_price'] * 1.2),  # Belirlenen satış fiyatı veya %20 kar marjı
                    'description': f"2. El cihaz - Alınan: {device_data['source_person']}"
                }
                
                new_id = self.db.execute_query('''
                    INSERT INTO stock_items (name, item_type, part_number, quantity, sale_price, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (stock_data['name'], stock_data['item_type'], stock_data['part_number'],
                      stock_data['quantity'], stock_data['sale_price'], stock_data['description']))
                
                # Stok hareketi kaydet
                if new_id:
                    self.db.add_stock_movement(
                        new_id, 'Giriş', 1,
                        f"2. El cihaz eklendi - Seri No: {device_data['serial_number']}"
                    )
                    
        except Exception as e:
            log_error("StockTab", e)

    def edit_second_hand_device_from_button(self):
        """Edit butonu tıklandığında seçili cihazı düzenle."""
        selected_row = self.second_hand_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir cihaz seçin.")
            return
        self.edit_second_hand_device(self.second_hand_table.item(selected_row, 0))

    def show_second_hand_device_history(self):
        """Seçili 2. El cihazının geçmiş detaylarını gösterir."""
        selected_row = self.second_hand_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir cihaz seçin.")
            return

        id_item = self.second_hand_table.item(selected_row, 0)
        if not id_item:
            return
        device_id = int(id_item.text())

        try:
            device = self.db.fetch_one(
                """
                SELECT shd.id, shd.device_model, shd.serial_number, shd.customer_id,
                       shd.acquisition_date, shd.purchase_price, shd.sale_price,
                       shd.status, shd.notes,
                       c.name as customer_name
                FROM second_hand_devices shd
                LEFT JOIN customers c ON c.id = shd.customer_id
                WHERE shd.id = ?
                """,
                (device_id,)
            )
            if not device:
                QMessageBox.warning(self, "Hata", "Cihaz bilgisi bulunamadı.")
                return

            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox
            from PyQt6.QtCore import Qt

            history_dialog = QDialog(self)
            history_dialog.setWindowTitle(f"📋 Cihaz Geçmişi: {device['device_model']}")
            history_dialog.setMinimumSize(600, 500)
            layout = QVBoxLayout(history_dialog)

            # Temel bilgiler
            info_text = f"""
<b>Cihaz Model:</b> {device['device_model'] or 'N/A'}<br>
<b>Seri No:</b> {device['serial_number'] or 'N/A'}<br>
<b>Mevcut Durum:</b> {device['status'] or 'Stokta'}<br>
<b>Alınan Kişi/Kurum:</b> {device['customer_name'] or device.get('notes', 'N/A')}<br>
<b>Alınma Tarihi:</b> {device['acquisition_date'] or 'N/A'}<br>
<b>Alış Fiyatı:</b> {device['purchase_price'] or 0:.2f} TL<br>
<b>Satış Fiyatı:</b> {device['sale_price'] or 0:.2f} TL<br>
"""
            info_label = QLabel(info_text)
            info_label.setStyleSheet("""
                background-color: #f0f4f8;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ccc;
            """)
            layout.addWidget(info_label)

            # Geçmiş/Notlar
            layout.addWidget(QLabel("<b>📝 Geçmiş & Notlar:</b>"))
            history_edit = QTextEdit()
            history_edit.setReadOnly(True)
            history_edit.setText(device['notes'] or "Henüz geçmiş kaydı yok.")
            layout.addWidget(history_edit)

            # Kapatma butonu
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(history_dialog.reject)
            layout.addWidget(buttons)

            history_dialog.exec()

        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"Cihaz geçmişi gösterilemedi: {e}")

    def second_hand_device_selected(self):
        """2. El cihaz seçildiğinde hurda butonunu aktif eder."""
        selection_model = self.second_hand_table.selectionModel()
        if selection_model:
            selected_rows = selection_model.selectedRows()
            self.edit_second_hand_btn.setEnabled(len(selected_rows) > 0)
            self.history_second_hand_btn.setEnabled(len(selected_rows) > 0)
            self.scrap_device_btn.setEnabled(len(selected_rows) > 0)
            self.delete_second_hand_btn.setEnabled(len(selected_rows) > 0)
        else:
            self.edit_second_hand_btn.setEnabled(False)
            self.history_second_hand_btn.setEnabled(False)
            self.scrap_device_btn.setEnabled(False)
            self.delete_second_hand_btn.setEnabled(False)

    def scrap_second_hand_device(self):
        """Seçili 2. El cihazı hurdaya çıkarır."""
        selection_model = self.second_hand_table.selectionModel()
        if not selection_model:
            return
            
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return
        
        try:
            row = selected_rows[0].row()
            id_item = self.second_hand_table.item(row, 0)
            model_item = self.second_hand_table.item(row, 1)
            serial_item = self.second_hand_table.item(row, 2)
            
            if not id_item or not model_item or not serial_item:
                QMessageBox.warning(self, "Hata", "Cihaz bilgileri eksik!")
                return
                
            device_id = int(id_item.text())
            device_model = model_item.text()
            serial_number = serial_item.text()
            
            reply = QMessageBox.question(
                self, "Hurda Çıkarma Onayı",
                f"Bu cihazı hurdaya çıkarmak istediğinizden emin misiniz?\n\n"
                f"Cihaz: {device_model}\n"
                f"Seri No: {serial_number}\n\n"
                f"Bu işlem geri alınamaz!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 2. El cihazı güncelle
                self.db.execute_query(
                    "UPDATE second_hand_devices SET status = 'Hurda' WHERE id = ?",
                    (device_id,)
                )
                
                self.refresh_second_hand_stock()
                self.refresh_data()
                QMessageBox.information(self, "Başarılı", "Cihaz hurdaya çıkarıldı!")
                
        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"Hurda çıkarma işlemi başarısız: {e}")

    def delete_second_hand_device(self):
        """Seçili 2. El cihazı tamamen siler."""
        selection_model = self.second_hand_table.selectionModel()
        if not selection_model:
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return

        try:
            row = selected_rows[0].row()
            id_item = self.second_hand_table.item(row, 0)
            model_item = self.second_hand_table.item(row, 1)
            serial_item = self.second_hand_table.item(row, 2)

            if not id_item or not model_item or not serial_item:
                QMessageBox.warning(self, "Hata", "Cihaz bilgileri eksik!")
                return

            device_id = int(id_item.text())
            device_model = model_item.text()
            serial_number = serial_item.text()

            reply = QMessageBox.question(
                self,
                "Silme Onayı",
                "Bu işlem geri alınamaz. Cihazı tamamen silmek istediğinizden eminmisiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Normal stoktan düş (varsa)
            try:
                self._remove_second_hand_from_normal_stock(device_model, serial_number)
            except Exception:
                pass

            # 2. el cihaz kaydını sil
            self.db.execute_query(
                "DELETE FROM second_hand_devices WHERE id = ?",
                (device_id,)
            )

            # Müşteri cihazı kaydı boşta ise temizle (seri no bazlı)
            try:
                self.db.execute_query(
                    "DELETE FROM customer_devices WHERE serial_number = ? AND (customer_id IS NULL OR customer_id = '')",
                    (serial_number,)
                )
            except Exception:
                pass

            self.refresh_second_hand_stock()
            self.refresh_data()
            QMessageBox.information(self, "Başarılı", "Cihaz tamamen silindi.")

        except Exception as e:
            log_error("StockTab", e)
            QMessageBox.critical(self, "Hata", f"Silme işlemi başarısız: {e}")

    def _remove_second_hand_from_normal_stock(self, device_model, serial_number):
        """2. El cihazı normal stoktan çıkarır."""
        try:
            # Stokta bul
            stock_item = self.db.fetch_one(
                "SELECT id, quantity FROM stock_items WHERE name = ? AND item_type = 'Cihaz'",
                (device_model,)
            )
            
            if stock_item and stock_item['quantity'] > 0:
                new_quantity = stock_item['quantity'] - 1
                
                if new_quantity > 0:
                    # Miktarı azalt
                    self.db.execute_query(
                        "UPDATE stock_items SET quantity = ? WHERE id = ?",
                        (new_quantity, stock_item['id'])
                    )
                else:
                    # Stoktan tamamen kaldır
                    self.db.execute_query("DELETE FROM stock_items WHERE id = ?", (stock_item['id'],))
                
                # Stok hareketi kaydet
                self.db.add_stock_movement(
                    stock_item['id'], 'Çıkış', 1,
                    f"2. El cihaz hurda çıkarıldı - Seri No: {serial_number}"
                )
                
        except Exception as e:
            log_error("StockTab", e)

    def print_second_hand_list(self):
        """2. El cihaz listesini yazdırır."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt6.QtGui import QTextDocument
        
        html = "<h2>2. El Cihaz Listesi</h2><table border='1' cellspacing='0' cellpadding='4'><tr>"
        headers = []
        for i in range(self.second_hand_table.columnCount()):
            if not self.second_hand_table.isColumnHidden(i):
                header_item = self.second_hand_table.horizontalHeaderItem(i)
                if header_item:
                    headers.append(header_item.text())
        
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr>"
        
        for row in range(self.second_hand_table.rowCount()):
            html += "<tr>"
            for col in range(self.second_hand_table.columnCount()):
                if not self.second_hand_table.isColumnHidden(col):
                    val = self.second_hand_table.item(row, col)
                    html += f"<td>{val.text() if val else ''}</td>"
            html += "</tr>"
        html += "</table>"
        
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter()
        dlg = QPrintDialog(printer, self)
        if dlg.exec():
            doc.print(printer)
