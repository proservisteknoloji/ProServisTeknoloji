# ui/dialogs/stock_picker_dialog.py

from typing import Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QSpinBox, QLabel, QDialogButtonBox, 
                             QMessageBox, QCheckBox)
from PyQt6.QtCore import QTimer
from utils.database import db_manager

class StockPickerDialog(QDialog):
    """Stoktan yedek parça/toner seçmek için kullanılan diyalog."""

    def __init__(self, db, filter_model=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_part = None
        self.filter_model = filter_model  # Filtrelenecek cihaz modeli (örn: Kyocera M2540dn)
        self._init_complete = False  # UI tam olarak oluşturulduktan sonra True olacak
        
        self.setWindowTitle("Stoktan Ürün Seç")
        self.setMinimumSize(700, 500)
        
        # Filtreleme için gecikme zamanlayıcısı
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._load_parts)
        
        self._init_ui()
        self._init_complete = True  # UI tamamlandı
        self._load_parts()  # Şimdi doğru şekilde yüklenecek

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Filtreleme
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Parça adı, kodu veya uyumluluk ile ara...")
        self.filter_input.textChanged.connect(self._on_filter_changed)
        
        # Uyumluluk Checkbox
        self.compatible_check = QCheckBox("Sadece Uyumlu Parçaları Göster")
        if self.filter_model:
            # Model adını temizle (sondaki kodlara odaklan)
            display_model = self.filter_model.split(' ')[-1] if ' ' in self.filter_model else self.filter_model
            self.compatible_check.setText(f"✓ Sadece '{display_model}' ile Uyumlu Olanlar")
            self.compatible_check.setChecked(False)  # Varsayılan olarak tüm parçaları göster
            self.compatible_check.setStyleSheet("""
                QCheckBox {
                    font-weight: bold;
                    font-size: 11pt;
                    color: #1565C0;
                    padding: 8px 12px;
                    background-color: #E3F2FD;
                    border: 2px solid #1565C0;
                    border-radius: 6px;
                }
                QCheckBox:checked {
                    background-color: #C8E6C9;
                    border-color: #2E7D32;
                    color: #2E7D32;
                }
                QCheckBox:hover {
                    background-color: #BBDEFB;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
        else:
            self.compatible_check.setEnabled(False)
            self.compatible_check.setVisible(False)
            
        self.compatible_check.toggled.connect(self._load_parts)
        
        filter_layout.addWidget(self.filter_input)
        if self.filter_model:
            filter_layout.addWidget(self.compatible_check)
        
        layout.addLayout(filter_layout)

        # Tablo
        self.parts_table = QTableWidget(0, 6)
        self.parts_table.setHorizontalHeaderLabels(["ID", "Ad", "Parça No", "Uyumlu Modeller", "Stok", "Fiyat"])
        self.parts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.parts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.parts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.parts_table.hideColumn(0)
        self.parts_table.doubleClicked.connect(self.accept)
        
        layout.addWidget(self.parts_table)
        
        # Miktar ve Butonlar
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(QLabel("<b>Seçilen Adet:</b>"))
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999)
        self.quantity_spin.setValue(1)
        bottom_layout.addWidget(self.quantity_spin)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        layout.addLayout(bottom_layout)
        layout.addWidget(self.buttons)

    def _on_filter_changed(self):
        """Filtreleme için 300ms gecikme ile yeniden yükleme tetikler."""
        self.filter_timer.stop()
        self.filter_timer.start(300)

    def _load_parts(self):
        filter_text = self.filter_input.text().strip()
        
        # UI tam olarak oluşturulduktan sonra checkbox kontrolü yap
        if self._init_complete and self.filter_model:
            check_checked = self.compatible_check.isChecked()
        else:
            check_checked = False
        
        # Tablo güncellemelerini geçici olarak durdur (performans için)
        self.parts_table.setUpdatesEnabled(False)
        self.parts_table.setRowCount(0)
        
        try:
            query = """
                SELECT id, name, part_number, quantity, sale_price, sale_currency, compatible_models 
                FROM stock_items 
                WHERE item_type != 'Cihaz' AND quantity > 0
            """
            params = []

            # Metin Araması - FIXED: COALESCE for NULL handling
            if filter_text:
                query += " AND (name LIKE ? OR COALESCE(part_number, '') LIKE ? OR COALESCE(compatible_models, '') LIKE ?)"
                like_text = f"%{filter_text}%"
                params.extend([like_text, like_text, like_text])

            # Uyumluluk Filtresi - FIXED: COALESCE for NULL handling
            if check_checked and self.filter_model:
                # Cihaz modelinden arama terimi çıkar (örn: "Kyocera M2540dn" -> "M2540")
                model_parts = self.filter_model.split(' ')
                search_term = self.filter_model
                for part in reversed(model_parts):
                    if any(char.isdigit() for char in part):
                        search_term = part
                        break
                
                query += " AND COALESCE(compatible_models, '') LIKE ?"
                params.append(f"%{search_term}%")

            query += " ORDER BY name ASC"
            parts = self.db.fetch_all(query, tuple(params))
            
            for part in parts:
                # FIXED: Convert sqlite3.Row to dict to use .get() method
                part_dict = dict(part)
                
                row = self.parts_table.rowCount()
                self.parts_table.insertRow(row)
                self.parts_table.setItem(row, 0, QTableWidgetItem(str(part_dict.get('id', ''))))
                self.parts_table.setItem(row, 1, QTableWidgetItem(part_dict.get('name', '') or ''))
                self.parts_table.setItem(row, 2, QTableWidgetItem(part_dict.get('part_number', '') or ''))
                self.parts_table.setItem(row, 3, QTableWidgetItem(part_dict.get('compatible_models', '') or ''))
                
                qty_item = QTableWidgetItem(str(part_dict.get('quantity', 0)))
                qty_item.setTextAlignment(0x0082) # Sağa yasla
                self.parts_table.setItem(row, 4, qty_item)
                
                price = part_dict.get('sale_price', 0.00) or 0.00
                currency = part_dict.get('sale_currency', 'TL') or 'TL'
                price_item = QTableWidgetItem(f"{float(price):.2f} {currency}")
                price_item.setTextAlignment(0x0082)
                self.parts_table.setItem(row, 5, price_item)

        except Exception as e:
            if "no such column: compatible_models" in str(e):
                QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanında 'compatible_models' sütunu eksik.")
            else:
                QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata: {e}")
        finally:
            # Tablo güncellemelerini tekrar aç
            self.parts_table.setUpdatesEnabled(True)

    def accept(self):
        selected_rows = self.parts_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir ürün seçin.")
            return
        
        row = selected_rows[0].row()
        try:
            price_text = self.parts_table.item(row, 5).text()
            price_parts = price_text.split(' ')
            price_val = float(price_parts[0])
            currency_val = price_parts[1] if len(price_parts) > 1 else 'TL'
            
            self.selected_part = {
                'id': int(self.parts_table.item(row, 0).text()),
                'name': self.parts_table.item(row, 1).text(),
                'quantity': self.quantity_spin.value(),
                'unit_price': price_val,
                'currency': currency_val,
                'part_number': self.parts_table.item(row, 2).text()
            }
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Seçim hatası: {e}")

    def get_selected_part(self):
        """Seçili parçayı döndürür."""
        return self.selected_part