# ui/dialogs/stock_history_dialog.py

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QMessageBox,
    QGroupBox,
)
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class StockHistoryDialog(QDialog):
    """Detayli stok hareket gecmisi diyalogu"""

    def __init__(self, item_id, item_name, db_manager, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.item_name = item_name
        self.db = db_manager
        self.logger = logging.getLogger(__name__)

        self.setWindowTitle(f"Detayl\u0131 Stok Hareket Ge\u00e7mi\u015fi - {item_name}")
        self.setModal(True)
        self.resize(800, 600)
        self.setFont(QFont("Segoe UI", 10))

        self._setup_ui()
        self._load_movements()

    def _setup_ui(self):
        """Kullanici arayuzunu olusturur."""
        layout = QVBoxLayout(self)

        # Baslik
        title_label = QLabel(f"{self.item_name} - Hareket Ge\u00e7mi\u015fi")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1976D2; margin: 10px 0;")
        layout.addWidget(title_label)

        # Hareket tablosu
        self.movements_table = QTableWidget(0, 7)
        self.movements_table.setHorizontalHeaderLabels(
            [
                "\u0130\u015flem Tarihi",
                "Hareket Tipi",
                "Miktar",
                "Stok Sonras\u0131",
                "Al\u0131\u015f Fiyat\u0131",
                "Sat\u0131\u015f Fiyat\u0131",
                "A\u00e7\u0131klama",
            ]
        )

        # Tablo stilini ayarla
        self.movements_table.setAlternatingRowColors(True)
        self.movements_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.movements_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.movements_table.verticalHeader().setVisible(False)

        # Tablo baslik stilini ayarla - Sadece temel stil
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

        # Istatistik alani
        stats_group = self._create_stats_group()
        layout.addWidget(stats_group)

        # Butonlar
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("Yenile")
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

        close_btn = QPushButton("Kapat")
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
        """Istatistik grubunu olusturur."""
        group = QGroupBox("\u0130statistikler")
        layout = QHBoxLayout(group)

        self.total_in_label = QLabel("Toplam Giri\u015f: 0")
        self.total_out_label = QLabel("Toplam \u00c7\u0131k\u0131\u015f: 0")
        self.transaction_count_label = QLabel("\u0130\u015flem Say\u0131s\u0131: 0")

        # Istatistik etiketlerini stillendir
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
        """Stok hareketlerini yukler."""
        try:
            movements = self.db.get_stock_movements(self.item_id)
            self._populate_table(movements)
            self._update_statistics(movements)
        except Exception as e:
            self.logger.error(f"Hareket gecmisi yuklenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Hareket gecmisi yuklenemedi: {e}")

    def _populate_table(self, movements):
        """Tabloyu hareket verileriyle doldurur."""
        self.movements_table.setRowCount(len(movements))

        for row, move in enumerate(movements):
            # Tarih
            date_item = QTableWidgetItem(move.get("movement_date", ""))
            self.movements_table.setItem(row, 0, date_item)

            # Hareket tipi
            movement_type = move.get("movement_type", "")
            type_item = QTableWidgetItem(movement_type)
            self.movements_table.setItem(row, 1, type_item)

            # Miktar degisimi
            quantity_changed = move.get("quantity_changed", 0)
            quantity_item = QTableWidgetItem(str(quantity_changed))
            self.movements_table.setItem(row, 2, quantity_item)

            # Stok sonrasi
            self.movements_table.setItem(row, 3, QTableWidgetItem(str(move.get("quantity_after", ""))))

            # Alis/Satis fiyatlari
            unit_price = move.get("unit_price", 0)
            currency = move.get("currency", "TL")
            price_text = f"{unit_price:.2f} {currency}" if unit_price else "-"
            is_in = quantity_changed > 0
            is_out = quantity_changed < 0
            self.movements_table.setItem(row, 4, QTableWidgetItem(price_text if is_in else "-"))
            self.movements_table.setItem(row, 5, QTableWidgetItem(price_text if is_out else "-"))

            # Aciklama
            self.movements_table.setItem(row, 6, QTableWidgetItem(move.get("notes", "") or "-"))

            # Renklendirme islemini tablo seviyesinde yap
            self._apply_row_styling(row, movement_type, quantity_changed)

    def _update_statistics(self, movements):
        """Istatistikleri gunceller."""
        total_in = sum(
            move.get("quantity_changed", 0)
            for move in movements
            if move.get("quantity_changed", 0) > 0
        )

        total_out = abs(
            sum(
                move.get("quantity_changed", 0)
                for move in movements
                if move.get("quantity_changed", 0) < 0
            )
        )

        transaction_count = len(movements)

        self.total_in_label.setText(f"Toplam Giri\u015f: {total_in}")
        self.total_out_label.setText(f"Toplam \u00c7\u0131k\u0131\u015f: {total_out}")
        self.transaction_count_label.setText(f"\u0130\u015flem Say\u0131s\u0131: {transaction_count}")

    def _apply_row_styling(self, row, movement_type, quantity_changed):
        """Satir renklendirmesi uygular."""
        from PyQt6.QtGui import QColor

        # Hareket tipine gore arka plan rengi
        if movement_type in ["Stok Girisi", "Iade", "Giris", "Stok Giri\u015fi", "\u0130ade", "Giri\u015f"]:
            bg_color = QColor(232, 245, 232)  # Acik yesil
            text_color = QColor(46, 125, 50)  # Koyu yesil
        elif movement_type in ["Stok Cikisi", "Satis", "Cikis", "Stok \u00c7\u0131k\u0131\u015f\u0131", "Sat\u0131\u015f", "\u00c7\u0131k\u0131\u015f"]:
            bg_color = QColor(255, 235, 238)  # Acik kirmizi
            text_color = QColor(198, 40, 40)  # Koyu kirmizi
        else:
            return  # Varsayilan renkler

        # Hareket tipi sutununu renklendir
        type_item = self.movements_table.item(row, 1)
        if type_item:
            type_item.setBackground(bg_color)
            type_item.setForeground(text_color)

        # Miktar sutununu renklendir
        qty_item = self.movements_table.item(row, 2)
        if qty_item and quantity_changed != 0:
            if quantity_changed > 0:
                qty_item.setForeground(QColor(0, 128, 0))  # Yesil
            else:
                qty_item.setForeground(QColor(255, 0, 0))  # Kirmizi
            # Kalin font
            font = qty_item.font()
            font.setBold(True)
            qty_item.setFont(font)
