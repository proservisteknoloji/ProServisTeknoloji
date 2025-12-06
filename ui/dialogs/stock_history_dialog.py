# ui/dialogs/stock_history_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                             QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import logging

class StockHistoryDialog(QDialog):
    """Detaylı stok hareket geçmişi diyalogu"""
    
    def __init__(self, item_id, item_name, db_manager, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.item_name = item_name
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        self.setWindowTitle(f"📊 Detaylı Stok Hareket Geçmişi - {item_name}")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_movements()
        
    def _setup_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)
        
        # Başlık
        title_label = QLabel(f"🔍 {self.item_name} - Hareket Geçmişi")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1976D2; margin: 10px 0;")
        layout.addWidget(title_label)
        
        # Hareket tablosu
        self.movements_table = QTableWidget(0, 6)
        self.movements_table.setHorizontalHeaderLabels([
            "📅 İşlem Tarihi", "🔄 Hareket Tipi", "📦 Miktar", 
            "📈 Stok Sonrası", "💰 Birim Fiyat", "📝 Açıklama"
        ])
        
        # Tablo stilini ayarla
        self.movements_table.setAlternatingRowColors(True)
        self.movements_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.movements_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.movements_table.verticalHeader().setVisible(False)
        
        # Tablo başlık stilini ayarla - Sadece temel stil
        header_style = """
            QHeaderView::section {
                background-color: #1976D2;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
            }
        """
        self.movements_table.horizontalHeader().setStyleSheet(header_style)
        
        layout.addWidget(self.movements_table)
        
        # İstatistik alanı
        stats_group = self._create_stats_group()
        layout.addWidget(stats_group)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.clicked.connect(self._load_movements)
        refresh_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        refresh_btn.setStyleSheet(refresh_style)
        
        close_btn = QPushButton("❌ Kapat")
        close_btn.clicked.connect(self.accept)
        close_style = """
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """
        close_btn.setStyleSheet(close_style)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def _create_stats_group(self):
        """İstatistik grupunu oluşturur."""
        group = QGroupBox("📈 İstatistikler")
        layout = QHBoxLayout(group)
        
        self.total_in_label = QLabel("Toplam Giriş: 0")
        self.total_out_label = QLabel("Toplam Çıkış: 0")
        self.transaction_count_label = QLabel("İşlem Sayısı: 0")
        
        # İstatistik etiketlerini stillendir
        stats_style = """
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """
        
        for label in [self.total_in_label, self.total_out_label, self.transaction_count_label]:
            label.setStyleSheet(stats_style)
        
        layout.addWidget(self.total_in_label)
        layout.addWidget(self.total_out_label)
        layout.addWidget(self.transaction_count_label)
        layout.addStretch()
        
        return group
        
    def _load_movements(self):
        """Stok hareketlerini yükler."""
        try:
            movements = self.db.get_stock_movements(self.item_id)
            self._populate_table(movements)
            self._update_statistics(movements)
        except Exception as e:
            self.logger.error(f"Hareket geçmişi yüklenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Hareket geçmişi yüklenemedi: {e}")
            
    def _populate_table(self, movements):
        """Tabloyu hareket verileriyle doldurur."""
        self.movements_table.setRowCount(len(movements))
        
        for row, move in enumerate(movements):
            # Tarih
            date_item = QTableWidgetItem(move.get('movement_date', ''))
            self.movements_table.setItem(row, 0, date_item)
            
            # Hareket tipi
            movement_type = move.get('movement_type', '')
            type_item = QTableWidgetItem(movement_type)
            # Hareket tipine göre renklendirme - QTableWidget seviyesinde yapılacak
            self.movements_table.setItem(row, 1, type_item)
            
            # Miktar değişimi
            quantity_changed = move.get('quantity_changed', 0)
            quantity_item = QTableWidgetItem(str(quantity_changed))
            # Renklendirme widget seviyesinde yapılacak
            self.movements_table.setItem(row, 2, quantity_item)
            
            # Stok sonrası
            self.movements_table.setItem(row, 3, QTableWidgetItem(
                str(move.get('quantity_after', ''))
            ))
            
            # Birim fiyat
            unit_price = move.get('unit_price', 0)
            currency = move.get('currency', 'TL')
            price_text = f"{unit_price:.2f} {currency}" if unit_price else "-"
            self.movements_table.setItem(row, 4, QTableWidgetItem(price_text))
            
            # Açıklama
            self.movements_table.setItem(row, 5, QTableWidgetItem(
                move.get('notes', '') or '-'
            ))
            
            # Renklendirme işlemini tablo seviyesinde yap
            self._apply_row_styling(row, movement_type, quantity_changed)
            
    def _update_statistics(self, movements):
        """İstatistikleri günceller."""
        total_in = sum(move.get('quantity_changed', 0) 
                      for move in movements 
                      if move.get('quantity_changed', 0) > 0)
        
        total_out = abs(sum(move.get('quantity_changed', 0) 
                           for move in movements 
                           if move.get('quantity_changed', 0) < 0))
        
        transaction_count = len(movements)
        
        self.total_in_label.setText(f"📈 Toplam Giriş: {total_in}")
        self.total_out_label.setText(f"📉 Toplam Çıkış: {total_out}")
        self.transaction_count_label.setText(f"🔢 İşlem Sayısı: {transaction_count}")
        
    def _apply_row_styling(self, row, movement_type, quantity_changed):
        """Satır renklendirmesi uygular."""
        from PyQt6.QtGui import QColor
        from PyQt6.QtCore import Qt
        
        # Hareket tipine göre arka plan rengi
        if movement_type in ['Stok Girişi', 'İade']:
            bg_color = QColor(232, 245, 232)  # Açık yeşil
            text_color = QColor(46, 125, 50)  # Koyu yeşil
        elif movement_type in ['Stok Çıkışı', 'Satış']:
            bg_color = QColor(255, 235, 238)  # Açık kırmızı
            text_color = QColor(198, 40, 40)  # Koyu kırmızı
        else:
            return  # Varsayılan renkler
            
        # Hareket tipi sütununu renklendir
        type_item = self.movements_table.item(row, 1)
        if type_item:
            type_item.setBackground(bg_color)
            type_item.setForeground(text_color)
            
        # Miktar sütununu renklendir
        qty_item = self.movements_table.item(row, 2)
        if qty_item and quantity_changed != 0:
            if quantity_changed > 0:
                qty_item.setForeground(QColor(0, 128, 0))  # Yeşil
            else:
                qty_item.setForeground(QColor(255, 0, 0))  # Kırmızı
            # Kalın font
            font = qty_item.font()
            font.setBold(True)
            qty_item.setFont(font)