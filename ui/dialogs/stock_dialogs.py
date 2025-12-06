# ui/dialogs/stock_dialogs.py

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDialogButtonBox, QTextEdit, QSpinBox, QLabel, 
                             QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, 
                             QGridLayout, QScrollArea, QWidget, QPushButton)
from PyQt6.QtCore import Qt
from typing import Optional

class StockItemDialog(QDialog):
    """Yeni stok kartı eklemek veya mevcut olanı düzenlemek için kullanılan diyalog."""
    
    def __init__(self, item_type: str = 'Yedek Parça', data: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.is_editing = data is not None
        self.item_type = (data or {}).get('item_type') if self.is_editing else item_type
        self.data = data

        self.setWindowTitle("Stok Kartı Düzenle" if self.is_editing else f"Yeni {self.item_type} Kartı")
        self.is_device = self.item_type == "Cihaz"  # Cihaz tipi kontrolü için
        
        # Pencere boyutunu ayarla
        if self.is_device:
            self.resize(800, 600)
        else:
            self.resize(500, 550)  # Uyumlu modeller eklendiği için biraz büyüttük
        
        self._init_ui()
        if self.is_editing:
            self._load_data()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        # Ana layout
        main_layout = QVBoxLayout(self)
        
        # Scroll area oluştur
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Scroll içeriği için widget
        scroll_widget = QWidget()
        layout = QFormLayout(scroll_widget)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        self._create_widgets()
        self._create_layout(layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.type_label = QLabel(f"<b>{self.item_type}</b>")
        self.name_input = QLineEdit()
        self.part_number_input = QLineEdit()
        self.description_edit = QTextEdit()
        
        # --- YENİ: Uyumlu Modeller Alanı ---
        self.compatible_models_input = QLineEdit()
        self.compatible_models_input.setPlaceholderText("Örn: M2540dn, 3050ci, TK-1170 kullananlar...")
        # -----------------------------------
        
        self.purchase_price_input = QLineEdit()
        self.purchase_price_input.focusInEvent = lambda a0: (self.purchase_price_input.selectAll(), super(QLineEdit, self.purchase_price_input).focusInEvent(a0))[-1]
        self.purchase_price_input.setPlaceholderText("0.00")
        self.purchase_currency_combo = QComboBox()
        self.purchase_currency_combo.addItems(["TL", "USD", "EUR"])

        self.sale_price_input = QLineEdit()
        self.sale_price_input.focusInEvent = lambda a0: (self.sale_price_input.selectAll(), super(QLineEdit, self.sale_price_input).focusInEvent(a0))[-1]
        self.sale_price_input.setPlaceholderText("0.00")
        self.sale_currency_combo = QComboBox()
        self.sale_currency_combo.addItems(["TL", "USD", "EUR"])
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.focusInEvent = lambda e: (self.quantity_spin.selectAll(), super(QSpinBox, self.quantity_spin).focusInEvent(e))[-1]
        self.quantity_spin.setRange(0, 9999)
        self.quantity_spin.setValue(1)  # Varsayılan olarak 1 adet
        self.quantity_label = QLabel("Başlangıç Miktarı (*):")
        
        # Çift tıklama ile stok girişi özelliği (sadece düzenleme modunda)
        if self.is_editing:
            self.quantity_spin.mouseDoubleClickEvent = lambda a0: self._quantity_double_clicked(a0)

        self.supplier_input = QLineEdit()

        # Cihaz tipi için özel alanlar
        if self.is_device:
            self.color_type_combo = QComboBox()
            self.color_type_combo.addItems(["Siyah-Beyaz", "Renkli"])
            self.color_type_combo.currentTextChanged.connect(self.update_toner_fields)
            
            # Manuel toner giriş alanları
            self.toner_black_input = QLineEdit()
            self.toner_black_input.setPlaceholderText("Siyah toner kodu (örn: TK-3190)")
            self.toner_black_equivalent_input = QLineEdit()
            self.toner_black_equivalent_input.setPlaceholderText("🔄 Muadil siyah toner kodu")

            self.toner_cyan_input = QLineEdit()
            self.toner_cyan_input.setPlaceholderText("💙 Mavi toner kodu (örn: TK-5240C)")
            self.toner_cyan_equivalent_input = QLineEdit()
            self.toner_cyan_equivalent_input.setPlaceholderText("🔄 Muadil mavi toner kodu")

            self.toner_magenta_input = QLineEdit()
            self.toner_magenta_input.setPlaceholderText("❤️ Kırmızı toner kodu (örn: TK-5240M)")
            self.toner_magenta_equivalent_input = QLineEdit()
            self.toner_magenta_equivalent_input.setPlaceholderText("🔄 Muadil kırmızı toner kodu")

            self.toner_yellow_input = QLineEdit()
            self.toner_yellow_input.setPlaceholderText("💛 Sarı toner kodu (örn: TK-5240Y)")
            self.toner_yellow_equivalent_input = QLineEdit()
            self.toner_yellow_equivalent_input.setPlaceholderText("🔄 Muadil sarı toner kodu")
            
            self.toner_info_label = QLabel()
            self.toner_info_label.setWordWrap(True)
            self.toner_info_label.setStyleSheet("""
                QLabel {
                    background-color: #E8F5E8;
                    border: 1px solid #4CAF50;
                    border-radius: 6px;
                    padding: 8px;
                    margin: 5px 0px;
                    font-size: 12px;
                }
            """)
            self.toner_info_label.setText("💡 Cihazın kullandığı toner kodlarını manuel olarak girebilirsiniz")
            
            # Manuel kit giriş alanları
            self.kit_input_1 = QLineEdit()
            self.kit_input_1.setPlaceholderText("1. Kit kodu (örn: MK-3370)")
            self.kit_input_2 = QLineEdit()
            self.kit_input_2.setPlaceholderText("2. Kit kodu")
            self.kit_input_3 = QLineEdit()
            self.kit_input_3.setPlaceholderText("3. Kit kodu")
            self.kit_input_4 = QLineEdit()
            self.kit_input_4.setPlaceholderText("4. Kit kodu")
            self.kit_input_5 = QLineEdit()
            self.kit_input_5.setPlaceholderText("5. Kit kodu")
            self.kit_input_6 = QLineEdit()
            self.kit_input_6.setPlaceholderText("6. Kit kodu")
            
            self.kit_info_label = QLabel()
            self.kit_info_label.setWordWrap(True)
            self.kit_info_label.setStyleSheet("""
                QLabel {
                    background-color: #F3E5F5;
                    border: 1px solid #9C27B0;
                    border-radius: 6px;
                    padding: 8px;
                    margin: 5px 0px;
                    font-size: 12px;
                }
            """)
            self.kit_info_label.setText("🔧 Cihazın kullandığı kit kodlarını manuel olarak girebilirsiniz")
            
            # İlk başta toner alanlarını güncelle
            self.update_toner_fields()
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)

    def _create_layout(self, layout: QFormLayout):
        """Widget'ları layout'a yerleştirir."""
        purchase_price_layout = QHBoxLayout()
        purchase_price_layout.addWidget(self.purchase_price_input)
        purchase_price_layout.addWidget(self.purchase_currency_combo)

        sale_price_layout = QHBoxLayout()
        sale_price_layout.addWidget(self.sale_price_input)
        sale_price_layout.addWidget(self.sale_currency_combo)

        layout.addRow("Kart Tipi:", self.type_label)
        
        if self.is_device:
            # Üst kısım: Temel bilgiler sol, toner sağ
            top_layout = QHBoxLayout()
            
            # Sol taraf - Temel bilgiler
            basic_group = QGroupBox("📋 Temel Bilgiler")
            basic_group.setMinimumWidth(450)
            basic_layout = QFormLayout()
            basic_layout.addRow("İsim/Model (*):", self.name_input)
            basic_layout.addRow("Parça Numarası:", self.part_number_input)
            basic_layout.addRow("Açıklama:", self.description_edit)
            basic_layout.addRow("Tedarikçi:", self.supplier_input)
            basic_layout.addRow("Baskı Tipi:", self.color_type_combo)
            basic_group.setLayout(basic_layout)
            
            # Sağ taraf - Toner alanları
            toner_group = QGroupBox("🖤 Toner Bilgileri")
            toner_layout = QVBoxLayout()
            toner_layout.addWidget(self.toner_info_label)

            toner_grid = QGridLayout()
            toner_grid.addWidget(QLabel("Renk"), 0, 0)
            toner_grid.addWidget(QLabel("Orijinal Toner"), 0, 1)
            toner_grid.addWidget(QLabel("Muadil Toner"), 0, 2)

            toner_grid.addWidget(QLabel("🖤 Siyah:"), 1, 0)
            toner_grid.addWidget(self.toner_black_input, 1, 1)
            toner_grid.addWidget(self.toner_black_equivalent_input, 1, 2)

            toner_grid.addWidget(QLabel("💙 Mavi:"), 2, 0)
            toner_grid.addWidget(self.toner_cyan_input, 2, 1)
            toner_grid.addWidget(self.toner_cyan_equivalent_input, 2, 2)

            toner_grid.addWidget(QLabel("❤️ Kırmızı:"), 3, 0)
            toner_grid.addWidget(self.toner_magenta_input, 3, 1)
            toner_grid.addWidget(self.toner_magenta_equivalent_input, 3, 2)

            toner_grid.addWidget(QLabel("💛 Sarı:"), 4, 0)
            toner_grid.addWidget(self.toner_yellow_input, 4, 1)
            toner_grid.addWidget(self.toner_yellow_equivalent_input, 4, 2)

            toner_layout.addLayout(toner_grid)
            toner_group.setLayout(toner_layout)
            
            top_layout.addWidget(basic_group, 2)
            top_layout.addWidget(toner_group, 3)
            
            layout.addRow(top_layout)
            
            # Alt kısım: Fiyatlar sol, Kit alanları sağ
            bottom_layout = QHBoxLayout()
            
            price_group = QGroupBox("💰 Fiyat ve Başlangıç Bilgileri")
            price_layout = QFormLayout()
            price_layout.addRow("Alış Fiyatı:", purchase_price_layout)
            price_layout.addRow("Satış Fiyatı:", sale_price_layout)
            price_layout.addRow(self.quantity_label, self.quantity_spin)
            price_group.setLayout(price_layout)
            
            kit_group = QGroupBox("🔧 Kit Bilgileri")
            kit_layout = QGridLayout()
            kit_layout.addWidget(self.kit_info_label, 0, 0, 1, 4)
            
            kit_layout.addWidget(QLabel("🔧 1. Kit:"), 1, 0)
            kit_layout.addWidget(self.kit_input_1, 1, 1)
            kit_layout.addWidget(QLabel("🔧 2. Kit:"), 2, 0)
            kit_layout.addWidget(self.kit_input_2, 2, 1)
            kit_layout.addWidget(QLabel("🔧 3. Kit:"), 3, 0)
            kit_layout.addWidget(self.kit_input_3, 3, 1)
            
            kit_layout.addWidget(QLabel("🔧 4. Kit:"), 1, 2)
            kit_layout.addWidget(self.kit_input_4, 1, 3)
            kit_layout.addWidget(QLabel("🔧 5. Kit:"), 2, 2)
            kit_layout.addWidget(self.kit_input_5, 2, 3)
            kit_layout.addWidget(QLabel("🔧 6. Kit:"), 3, 2)
            kit_layout.addWidget(self.kit_input_6, 3, 3)
            
            kit_group.setLayout(kit_layout)
            
            bottom_layout.addWidget(price_group, 1)
            bottom_layout.addWidget(kit_group, 2)
            
            layout.addRow(bottom_layout)
            
        else:
            # Cihaz olmayan kartlar için normal layout
            layout.addRow("İsim/Model (*):", self.name_input)
            layout.addRow("Parça Numarası:", self.part_number_input)
            
            # --- YENİ: Uyumlu Modeller Sadece Buraya Ekleniyor ---
            layout.addRow("Uyumlu Modeller:", self.compatible_models_input)
            # -----------------------------------------------------
            
            layout.addRow("Açıklama:", self.description_edit)
            layout.addRow("Tedarikçi:", self.supplier_input)
            layout.addRow("Alış Fiyatı:", purchase_price_layout)
            layout.addRow("Satış Fiyatı:", sale_price_layout)
            layout.addRow(self.quantity_label, self.quantity_spin)
            
        layout.addRow(self.buttons)
        
        if self.is_editing:
            self.quantity_label.setVisible(False)
            self.quantity_spin.setVisible(False)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _load_data(self):
        """Mevcut kart verilerini forma yükler."""
        data = self.data or {}
        self.name_input.setText(data.get('name', ''))
        self.part_number_input.setText(data.get('part_number', ''))
        
        # --- YENİ: Uyumlu modelleri yükle ---
        self.compatible_models_input.setText(data.get('compatible_models', ''))
        # ------------------------------------
        
        description = data.get('description', '') or ''
        clean_description = description
        
        # Cihaz detaylarını (Toner/Kit) description'dan ayıkla
        if self.is_device:
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

                        self.toner_black_input.setText(toner_data.get('black', ''))
                        self.toner_black_equivalent_input.setText(toner_data.get('black_equivalent', ''))
                        self.toner_cyan_input.setText(toner_data.get('cyan', ''))
                        self.toner_cyan_equivalent_input.setText(toner_data.get('cyan_equivalent', ''))
                        self.toner_magenta_input.setText(toner_data.get('magenta', ''))
                        self.toner_magenta_equivalent_input.setText(toner_data.get('magenta_equivalent', ''))
                        self.toner_yellow_input.setText(toner_data.get('yellow', ''))
                        self.toner_yellow_equivalent_input.setText(toner_data.get('yellow_equivalent', ''))

                        clean_description = description[:description.find(start_tag)] + description[end_idx + len(end_tag):]
                        clean_description = clean_description.strip()
                except: pass
            
            if '[KIT_DATA]' in description:
                import json
                try:
                    start_tag = '[KIT_DATA]'
                    end_tag = '[/KIT_DATA]'
                    start_idx = description.find(start_tag) + len(start_tag)
                    end_idx = description.find(end_tag)
                    
                    if start_idx > len(start_tag) - 1 and end_idx > start_idx:
                        kit_json = description[start_idx:end_idx]
                        kit_data = json.loads(kit_json)
                        
                        self.kit_input_1.setText(kit_data.get('kit1', ''))
                        self.kit_input_2.setText(kit_data.get('kit2', ''))
                        self.kit_input_3.setText(kit_data.get('kit3', ''))
                        self.kit_input_4.setText(kit_data.get('kit4', ''))
                        self.kit_input_5.setText(kit_data.get('kit5', ''))
                        self.kit_input_6.setText(kit_data.get('kit6', ''))
                        
                        clean_description = description[:description.find(start_tag)] + description[end_idx + len(end_tag):]
                        clean_description = clean_description.strip()
                except: pass

        self.description_edit.setText(clean_description or '')
        self.supplier_input.setText(data.get('supplier', ''))
        
        if self.is_device:
            self.color_type_combo.setCurrentText(data.get('color_type', 'Siyah-Beyaz'))
            self.update_toner_fields()
        
        # Fiyatları yükle
        purchase_price = data.get('purchase_price')
        if purchase_price: self.purchase_price_input.setText(str(purchase_price))
        self.purchase_currency_combo.setCurrentText(data.get('purchase_currency', 'TL'))
        
        sale_price = data.get('sale_price')
        if sale_price: self.sale_price_input.setText(str(sale_price))
        self.sale_currency_combo.setCurrentText(data.get('sale_currency', 'TL'))

    def update_toner_fields(self):
        """Baskı tipi değiştiğinde toner alanlarının görünürlüğünü ayarlar."""
        if not self.is_device: return

        color_type = self.color_type_combo.currentText()
        is_color = color_type == "Renkli"

        self.toner_black_input.setVisible(True)
        self.toner_black_equivalent_input.setVisible(True)

        self.toner_cyan_input.setVisible(is_color)
        self.toner_cyan_equivalent_input.setVisible(is_color)
        self.toner_magenta_input.setVisible(is_color)
        self.toner_magenta_equivalent_input.setVisible(is_color)
        self.toner_yellow_input.setVisible(is_color)
        self.toner_yellow_equivalent_input.setVisible(is_color)

        if is_color:
            self.toner_info_label.setText("🎨 Renkli cihaz için 4 toner tipi girilebilir")
        else:
            self.toner_info_label.setText("⚫ Siyah-beyaz cihaz için sadece siyah toner girilebilir")

    def get_data(self) -> dict:
        """Formdaki verileri bir sözlük olarak döndürür."""
        data = {
            'item_type': self.item_type,
            'name': self.name_input.text().strip(),
            'part_number': self.part_number_input.text().strip(),
            
            # --- YENİ: Uyumlu Modeller ---
            'compatible_models': self.compatible_models_input.text().strip(),
            # -----------------------------
            
            'description': self.description_edit.toPlainText().strip(),
            'quantity': self.quantity_spin.value(),
            'purchase_price': self._parse_price(self.purchase_price_input.text()),
            'purchase_currency': self.purchase_currency_combo.currentText(),
            'sale_price': self._parse_price(self.sale_price_input.text()),
            'sale_currency': self.sale_currency_combo.currentText(),
            'supplier': self.supplier_input.text().strip(),
            'is_consignment': 0
        }
        
        if self.is_device:
            data['color_type'] = self.color_type_combo.currentText()
            
            # Toner verilerini description'a ekle
            toner_data = self.get_toner_data()
            import json
            if toner_data:
                toner_json = json.dumps(toner_data, ensure_ascii=False)
                data['description'] = f"{data['description']}\n\n[TONER_DATA]{toner_json}[/TONER_DATA]" if data['description'] else f"[TONER_DATA]{toner_json}[/TONER_DATA]"
                    
            # Kit verilerini description'a ekle
            kit_data = self.get_kit_data()
            if kit_data:
                kit_json = json.dumps(kit_data, ensure_ascii=False)
                data['description'] = f"{data['description']}\n\n[KIT_DATA]{kit_json}[/KIT_DATA]" if data['description'] else f"[KIT_DATA]{kit_json}[/KIT_DATA]"
        
        return data

    def _parse_price(self, price_text: str) -> float:
        try:
            return float(price_text.replace(',', '.').strip())
        except:
            return 0.0

    def get_toner_data(self) -> dict:
        """Girilen toner verilerini döndürür."""
        if not self.is_device: return {}
        
        toner_data = {}
        if self.toner_black_input.text().strip(): toner_data['black'] = self.toner_black_input.text().strip()
        if self.toner_black_equivalent_input.text().strip(): toner_data['black_equivalent'] = self.toner_black_equivalent_input.text().strip()

        if self.toner_cyan_input.text().strip(): toner_data['cyan'] = self.toner_cyan_input.text().strip()
        if self.toner_cyan_equivalent_input.text().strip(): toner_data['cyan_equivalent'] = self.toner_cyan_equivalent_input.text().strip()

        if self.toner_magenta_input.text().strip(): toner_data['magenta'] = self.toner_magenta_input.text().strip()
        if self.toner_magenta_equivalent_input.text().strip(): toner_data['magenta_equivalent'] = self.toner_magenta_equivalent_input.text().strip()

        if self.toner_yellow_input.text().strip(): toner_data['yellow'] = self.toner_yellow_input.text().strip()
        if self.toner_yellow_equivalent_input.text().strip(): toner_data['yellow_equivalent'] = self.toner_yellow_equivalent_input.text().strip()

        return toner_data

    def get_kit_data(self) -> dict:
        """Girilen kit verilerini döndürür."""
        if not self.is_device: return {}
        
        kit_data = {}
        for i in range(1, 7):
            widget = getattr(self, f'kit_input_{i}')
            if widget.text().strip():
                kit_data[f'kit{i}'] = widget.text().strip()
        return kit_data

    def accept(self):
        new_data = self.get_data()
        if new_data:
            self.data = new_data
            super().accept()

    def _quantity_double_clicked(self, a0):
        try:
            if not self.is_editing: return
            item_name = self.name_input.text().strip()
            if not item_name: return
            
            stock_entry_dialog = QuickStockEntryDialog(
                item_name=item_name,
                current_quantity=self.quantity_spin.value(),
                parent=self
            )
            
            if stock_entry_dialog.exec():
                entry_data = stock_entry_dialog.get_data()
                new_quantity = self.quantity_spin.value() + entry_data['quantity']
                self.quantity_spin.setValue(new_quantity)
                
                if hasattr(self.parent(), 'handle_stock_entry_from_dialog'):
                    self.parent().handle_stock_entry_from_dialog(
                        item_name=item_name,
                        quantity_change=entry_data['quantity'],
                        notes=entry_data['notes']
                    )
                QMessageBox.information(self, "Başarılı", f"{entry_data['quantity']} adet eklendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))


class StockMovementDialog(QDialog):
    """Stok giriş/çıkış işlemleri için kullanılan diyalog."""

    def __init__(self, item_name: str, movement_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{item_name} - Stok {movement_type}")
        self._init_ui(movement_type)

    def _init_ui(self, movement_type: str):
        layout = QFormLayout(self)
        self.title_label = QLabel(f"<b>{movement_type} yapılacak miktar:</b>")
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 9999)
        self.notes_edit = QLineEdit()
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        layout.addRow(self.title_label)
        layout.addRow("Miktar (*):", self.quantity_spin)
        layout.addRow("Not (İrsaliye vb.):", self.notes_edit)
        layout.addRow(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def get_data(self) -> dict:
        return {
            'quantity': self.quantity_spin.value(),
            'notes': self.notes_edit.text().strip()
        }


class QuickStockEntryDialog(QDialog):
    """Hızlı stok giriş diyalogu - Basit tasarım."""

    def __init__(self, item_name: str, current_quantity: int = 0, parent=None):
        super().__init__(parent)
        self.item_name = item_name
        self.current_quantity = current_quantity
        self.setWindowTitle("Hızlı Stok Girişi")
        self.setFixedSize(380, 200)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        product_label = QLabel(f"Ürün: {self.item_name}")
        product_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        
        current_label = QLabel(f"Mevcut Stok: {self.current_quantity} adet")
        current_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        
        form_layout = QFormLayout()
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 9999)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setMinimumHeight(25)
        self.quantity_spin.selectAll()
        self.quantity_spin.setFocus()
        
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("İrsaliye no, tedarikçi, açıklama...")
        self.notes_edit.setMinimumHeight(35)
        
        form_layout.addRow("Giriş Miktarı:", self.quantity_spin)
        form_layout.addRow("Not (isteğe bağlı):", self.notes_edit)
        
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("İptal")
        self.ok_btn = QPushButton("✓ Stok Girişi Yap")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addWidget(product_label)
        layout.addWidget(current_label)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.quantity_spin.returnPressed.connect(self.accept)
        self.notes_edit.returnPressed.connect(self.accept)

    def get_data(self) -> dict:
        return {
            'quantity': self.quantity_spin.value(),
            'notes': self.notes_edit.text().strip()
        }
