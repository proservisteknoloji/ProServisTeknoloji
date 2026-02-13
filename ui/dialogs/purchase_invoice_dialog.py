# ui/dialogs/purchase_invoice_dialog.py

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QTextEdit, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox,
    QHeaderView, QDoubleSpinBox, QDateEdit, QCompleter
)
from PyQt6.QtCore import QDate
from ui.dialogs.stock_dialogs import StockItemDialog

logger = logging.getLogger(__name__)


class PurchaseInvoiceDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Al\u0131\u015f Faturas\u0131")
        self.resize(900, 600)
        self._init_ui()
        self._load_suppliers()
        self._load_stock_items()
        self._add_row()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Tedarik\u00e7i:"))
        self.supplier_combo = QComboBox()
        self.supplier_combo.setEditable(True)
        header.addWidget(self.supplier_combo)

        header.addWidget(QLabel("Fatura No:"))
        self.invoice_no_input = QLineEdit()
        header.addWidget(self.invoice_no_input)

        header.addWidget(QLabel("Tarih:"))
        self.invoice_date = QDateEdit()
        self.invoice_date.setCalendarPopup(True)
        self.invoice_date.setDate(QDate.currentDate())
        header.addWidget(self.invoice_date)
        layout.addLayout(header)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels([
            "U\u0308ru\u0308n", "Miktar", "Birim Fiyat", "D\u00f6viz", "KDV %"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 5):
            self.items_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.items_table)

        buttons = QHBoxLayout()
        buttons.addWidget(QLabel("Yeni \u00dcr\u00fcn Tipi:"))
        self.new_item_type_combo = QComboBox()
        self.new_item_type_combo.addItems(["Yedek Parça", "Toner", "Kit", "Cihaz", "Sarf Malzeme"])
        buttons.addWidget(self.new_item_type_combo)
        self.new_item_btn = QPushButton("+ Yeni \u00dcr\u00fcn")
        buttons.addWidget(self.new_item_btn)
        self.add_row_btn = QPushButton("+ Kalem Ekle")
        self.remove_row_btn = QPushButton("- Kalem Sil")
        buttons.addWidget(self.add_row_btn)
        buttons.addWidget(self.remove_row_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        notes_layout = QVBoxLayout()
        notes_layout.addWidget(QLabel("Notlar:"))
        self.notes_edit = QTextEdit()
        notes_layout.addWidget(self.notes_edit)
        layout.addLayout(notes_layout)

        action_layout = QHBoxLayout()
        self.save_btn = QPushButton("Kaydet")
        self.cancel_btn = QPushButton("\u0130ptal")
        action_layout.addStretch()
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.cancel_btn)
        layout.addLayout(action_layout)

        self.add_row_btn.clicked.connect(self._add_row)
        self.new_item_btn.clicked.connect(self._new_item)
        self.remove_row_btn.clicked.connect(self._remove_row)
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)

    def _load_suppliers(self):
        try:
            suppliers = self.db.fetch_all("SELECT id, name FROM suppliers ORDER BY name")
            self.supplier_combo.clear()
            for sid, name in suppliers:
                self.supplier_combo.addItem(name, name)
        except Exception as e:
            logger.error("Tedarikci yuklenemedi: %s", e)

    def _load_stock_items(self):
        self.stock_items = []
        try:
            items = self.db.fetch_all("SELECT id, name, part_number FROM stock_items ORDER BY name")
            for row in items:
                self.stock_items.append({
                    'id': row[0],
                    'name': row[1],
                    'part_number': row[2] or ''
                })
        except Exception as e:
            logger.error("Stok urunleri yuklenemedi: %s", e)

    def _configure_item_combo(self, combo: QComboBox):
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = combo.completer()
        if completer:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

    def _add_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        item_combo = QComboBox()
        self._configure_item_combo(item_combo)
        for item in self.stock_items:
            display = f"{item['name']} ({item['part_number']})" if item['part_number'] else item['name']
            item_combo.addItem(display, item['id'])
        self.items_table.setCellWidget(row, 0, item_combo)

        qty = QDoubleSpinBox()
        qty.setRange(0.01, 999999)
        qty.setDecimals(2)
        qty.setValue(1)
        self.items_table.setCellWidget(row, 1, qty)

        price = QDoubleSpinBox()
        price.setRange(0, 999999999)
        price.setDecimals(4)
        self.items_table.setCellWidget(row, 2, price)

        currency = QComboBox()
        currency.addItems(["TL", "USD", "EUR"])
        self.items_table.setCellWidget(row, 3, currency)

        tax = QDoubleSpinBox()
        tax.setRange(0, 100)
        tax.setDecimals(2)
        tax.setValue(20)
        self.items_table.setCellWidget(row, 4, tax)

    def _new_item(self):
        item_type = self.new_item_type_combo.currentText()
        dialog = StockItemDialog(item_type=item_type, parent=self)
        if dialog.exec():
            form_data = dialog.get_data()
            if not form_data or not form_data.get('name'):
                QMessageBox.warning(self, "Uyar\u0131", "\u00dcr\u00fcn ad\u0131 bo\u015f olamaz.")
                return
            saved_id = self.db.save_stock_item(form_data, None)
            if not saved_id:
                QMessageBox.critical(self, "Hata", "Yeni \u00fcr\u00fcn kaydedilemedi.")
                return
            self._load_stock_items()
            self._refresh_item_combos()

    def _refresh_item_combos(self):
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            if not combo:
                continue
            current = combo.currentData()
            combo.clear()
            for item in self.stock_items:
                display = f"{item['name']} ({item['part_number']})" if item['part_number'] else item['name']
                combo.addItem(display, item['id'])
            if current is not None:
                idx = combo.findData(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def _remove_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)

    def _save(self):
        supplier_name = self.supplier_combo.currentText().strip()
        invoice_no = self.invoice_no_input.text().strip()
        invoice_date = self.invoice_date.date().toString("yyyy-MM-dd")
        notes = self.notes_edit.toPlainText().strip()

        items = []
        for row in range(self.items_table.rowCount()):
            item_combo = self.items_table.cellWidget(row, 0)
            qty = self.items_table.cellWidget(row, 1)
            price = self.items_table.cellWidget(row, 2)
            currency = self.items_table.cellWidget(row, 3)
            tax = self.items_table.cellWidget(row, 4)

            if not item_combo:
                continue
            stock_item_id = item_combo.currentData()
            if not stock_item_id:
                continue

            item = {
                'stock_item_id': stock_item_id,
                'quantity': qty.value(),
                'unit_price': price.value(),
                'currency': currency.currentText(),
                'tax_rate': tax.value(),
            }
            items.append(item)

        if not items:
            QMessageBox.warning(self, "Uyar\u0131", "En az bir kalem ekleyin.")
            return

        ok, result = self.db.create_purchase_invoice(supplier_name, invoice_no, invoice_date, items, notes)
        if not ok:
            QMessageBox.critical(self, "Hata", str(result))
            return

        QMessageBox.information(self, "Ba\u015far\u0131l\u0131", f"Al\u0131\u015f faturas\u0131 kaydedildi. ID: {result}")
        self.accept()
