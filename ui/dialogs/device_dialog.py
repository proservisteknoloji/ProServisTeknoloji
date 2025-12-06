# ui/dialogs/device_dialog.py

from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging
from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDialogButtonBox, QMessageBox, QLabel, QTextEdit,
                             QGroupBox, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QPushButton, QSplitter, QGridLayout,
                             QCompleter)
from PyQt6.QtCore import Qt, QStringListModel, QSignalBlocker
from utils.database import db_manager

class DeviceDialog(QDialog):
    """Yeni cihaz eklemek veya mevcut bir cihazı düzenlemek için kullanılan diyalog."""
    def __init__(self, db, customer_id: int, device_id: int = None, location_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.customer_id = customer_id
        self.device_id = device_id
        self.location_id = location_id
        self.is_editing = self.device_id is not None
        self.stock_items = []
        self.stock_lookup = {}
        self.stock_model = QStringListModel(self)
        self.stock_completer = None
        self.selected_stock_item = None
        self.stock_mode_active = False
        self.model_default_placeholder = "Örnek: Taskalfa 2554ci"
        
        self.setWindowTitle("Cihaz Düzenle" if self.is_editing else "Yeni Cihaz Ekle")
        self.setMinimumWidth(400)
        
        self.init_ui()
        
        if self.is_editing:
            self.load_device_data()
        else:
            self.toggle_price_fields()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        
        # Cihaz kaynağı seçimi (Manuel Giriş vs Stoktan Seç)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Manuel Giriş", "Stoktan Seç"])
        layout.addRow("Cihaz Kaynağı:", self.source_combo)
        
        # Temel cihaz bilgileri
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Örnek: Kyocera, HP, Canon")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(self.model_default_placeholder)
        self.serial_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Siyah-Beyaz", "Renkli"])
        
        self.is_cpc_combo = QComboBox()
        self.is_cpc_combo.addItems(["Seçim Yapınız...", "Evet", "Hayır"])
        
        self.bw_price_input = QLineEdit()
        self.bw_price_input.setPlaceholderText("Örnek: 0,05 veya 0.05 (Boş bırakılabilir)")
        self.bw_price_input.focusInEvent = lambda a0: (self.bw_price_input.selectAll(), super(QLineEdit, self.bw_price_input).focusInEvent(a0))[-1]
        self.bw_currency_combo = QComboBox()
        self.bw_currency_combo.addItems(["TL", "USD", "EUR"])
        
        self.color_price_input = QLineEdit()
        self.color_price_input.setPlaceholderText("Örnek: 0,15 veya 0.15 (Boş bırakılabilir)")
        self.color_price_input.focusInEvent = lambda a0: (self.color_price_input.selectAll(), super(QLineEdit, self.color_price_input).focusInEvent(a0))[-1]
        self.color_currency_combo = QComboBox()
        self.color_currency_combo.addItems(["TL", "USD", "EURO"])
        
        self.rental_price_input = QLineEdit()
        self.rental_price_input.setPlaceholderText("Aylık kiralama bedeli (Boş bırakılabilir)")
        self.rental_price_input.setText("0,0000")  # Default value
        self.rental_price_input.focusInEvent = lambda a0: (self.rental_price_input.selectAll(), super(QLineEdit, self.rental_price_input).focusInEvent(a0))[-1]
        self.rental_currency_combo = QComboBox()
        self.rental_currency_combo.addItems(["TL", "USD", "EURO"])
        
        self.bw_price_label = QLabel("S/B Birim Fiyat:")
        self.color_price_label = QLabel("Renkli Birim Fiyat:")
        self.rental_price_label = QLabel("Kiralama Bedeli:")
        
        # Fiyat alanları için layout'lar
        bw_price_layout = QHBoxLayout()
        bw_price_layout.addWidget(self.bw_price_input)
        bw_price_layout.addWidget(self.bw_currency_combo)
        
        color_price_layout = QHBoxLayout()
        color_price_layout.addWidget(self.color_price_input)
        color_price_layout.addWidget(self.color_currency_combo)
        
        rental_price_layout = QHBoxLayout()
        rental_price_layout.addWidget(self.rental_price_input)
        rental_price_layout.addWidget(self.rental_currency_combo)
        
        # Form layout'una elemanları ekle
        layout.addRow("Marka (*):", self.brand_input)
        layout.addRow("Model (*):", self.model_input)
        layout.addRow("Seri Numarası (*):", self.serial_input)
        layout.addRow("Baskı Tipi:", self.type_combo)
        layout.addRow("Kopya Başı mı? (*):", self.is_cpc_combo)
        layout.addRow(self.bw_price_label, bw_price_layout)
        layout.addRow(self.color_price_label, color_price_layout)
        layout.addRow(self.rental_price_label, rental_price_layout)
        
        # Butonları oluştur ve bağla
        self.save_btn = QPushButton("KAYDET")
        self.cancel_btn = QPushButton("İPTAL")
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addRow(button_layout)
        
        self._connect_signals()

    def _connect_signals(self):
        """Sinyalleri slotlara bağlar."""
        self.is_cpc_combo.currentIndexChanged.connect(self.toggle_price_fields)
        self.type_combo.currentTextChanged.connect(self.toggle_price_fields)
        
        # Stok seçim sinyalleri
        self.source_combo.currentTextChanged.connect(self.on_source_changed)
        self.model_input.textChanged.connect(self.on_model_text_changed)
        
        # Buton sinyalleri
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
    def on_model_changed(self):
        """Model değiştiğinde - Uyumluluk sistemi kaldırıldı"""
        # Uyumluluk sistemi artık kullanılmıyor
        pass

    def check_toner_compatibility(self):
        """Eski method - uyumluluk sistemi kaldırıldı."""
        # Uyumluluk sistemi artık kullanılmıyor
        pass

    def accept(self):
        """Dialog'u kabul etmeden önce veri doğrulaması yapar."""
        device_data = self.get_device_data()
        if device_data is not None:
            # Cihaz verilerini kaydet
            if self.save_device(device_data):
                # Her şey OK ise parent dialog'u kapat
                super().accept()
        # Eğer device_data None ise (validasyon hatası), dialog açık kalır
    
    def save_toner_data_to_stock(self, device_model):
        """Cihazın toner bilgilerini stock_items'a kaydet - kaldırıldı."""
        # Uyumluluk sistemi kaldırıldı, toner verisi kaydedilmiyor
        pass
    
    def save_device(self, device_data):
        """Cihazı kaydeder."""
        cursor = None
        try:
            # Transaction başlat
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            if self.is_editing:
                # Güncelleme
                cursor.execute("""
                    UPDATE customer_devices 
                    SET brand=?, device_model=?, serial_number=?, device_type=?, 
                        color_type=?, notes=?, is_cpc=?, location_id=?,
                        cpc_bw_price=?, cpc_bw_currency=?, cpc_color_price=?, cpc_color_currency=?,
                        rental_fee=?, rental_currency=?
                    WHERE id=?
                """, (
                    device_data['brand'],
                    device_data['model'],
                    device_data['serial_number'],
                    device_data['device_type'],
                    device_data['device_type'],  # color_type = device_type
                    device_data.get('notes', ''),
                    device_data.get('is_cpc', False),
                    device_data.get('location_id'),
                    device_data.get('bw_price', 0),
                    device_data.get('bw_currency', 'TL'),
                    device_data.get('color_price', 0),
                    device_data.get('color_currency', 'TL'),
                    device_data.get('rental_fee', 0),
                    device_data.get('rental_currency', 'TL'),
                    self.device_id
                ))
                
                logging.info(f"Cihaz güncellendi: {device_data['brand']} {device_data['model']}")
                device_id = self.device_id
            else:
                # Yeni kayıt - Müşteri envanterine ekle
                cursor.execute("""
                    INSERT INTO customer_devices 
                    (customer_id, location_id, brand, device_model, serial_number, device_type, 
                     color_type, installation_date, notes, is_cpc, created_at,
                     cpc_bw_price, cpc_bw_currency, cpc_color_price, cpc_color_currency,
                     rental_fee, rental_currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device_data['customer_id'],
                    device_data.get('location_id'),
                    device_data['brand'],
                    device_data['model'], 
                    device_data['serial_number'],
                    device_data['device_type'],
                    device_data['device_type'],  # color_type = device_type
                    '',  # installation_date
                    device_data.get('notes', ''),
                    device_data.get('is_cpc', False),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    device_data.get('bw_price', 0),
                    device_data.get('bw_currency', 'TL'),
                    device_data.get('color_price', 0),
                    device_data.get('color_currency', 'TL'),
                    device_data.get('rental_fee', 0),
                    device_data.get('rental_currency', 'TL')
                ))
                
                device_id = cursor.lastrowid
                logging.info(f"Yeni cihaz müşteri envanterine eklendi: {device_data['brand']} {device_data['model']} (ID: {device_id})")

                # Toner ekleme kaldırıldı - sadece temel cihaz bilgileri kaydediliyor

            cursor.execute("COMMIT")
            QMessageBox.information(self, "Başarılı", "Cihaz başarıyla kaydedildi!")
            return True
            
        except Exception as e:
            if cursor:
                cursor.execute("ROLLBACK")
            logging.error(f"Cihaz kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Cihaz kaydedilirken hata oluştu:\n{str(e)}")
            return False
        """'Kopya Başı' seçimine göre fiyat alanlarını gösterir/gizler."""
        is_cpc = self.is_cpc_combo.currentText() == "Evet"
        is_color_device = self.type_combo.currentText() == "Renkli"

        # CPC fiyat alanları
        self.bw_price_label.setVisible(is_cpc)
        self.bw_price_input.setVisible(is_cpc)
        self.bw_price_input.setEnabled(is_cpc)
        self.bw_currency_combo.setVisible(is_cpc)
        self.bw_currency_combo.setEnabled(is_cpc)
        
        self.color_price_label.setVisible(is_cpc and is_color_device)
        self.color_price_input.setVisible(is_cpc and is_color_device)
        self.color_price_input.setEnabled(is_cpc and is_color_device)
        self.color_currency_combo.setVisible(is_cpc and is_color_device)
        self.color_currency_combo.setEnabled(is_cpc and is_color_device)
        
        # Kiralama bedeli alanları - her zaman görünür
        self.rental_price_label.setVisible(True)
        self.rental_price_input.setVisible(True)
        self.rental_price_input.setEnabled(True)
        self.rental_currency_combo.setVisible(True)
        self.rental_currency_combo.setEnabled(True)
        
        if not (is_cpc and is_color_device):
            self.color_price_input.setText("0.0000")

    def load_device_data(self):
        """Düzenleme modunda cihaz verilerini veritabanından yükler."""
        try:
            query = """
                SELECT brand, device_model, serial_number, device_type, is_cpc,
                       cpc_bw_price, cpc_bw_currency, cpc_color_price, cpc_color_currency,
                       rental_fee, rental_currency
                FROM customer_devices WHERE id = ?
            """
            device_data = self.db.fetch_one(query, (self.device_id,))
            if device_data:
                self.brand_input.setText(device_data['brand'] or '')
                self.model_input.setText(device_data['device_model'] or '')
                self.serial_input.setText(device_data['serial_number'] or '')
                self.type_combo.setCurrentText(device_data['device_type'] or 'Siyah-Beyaz')

                # CPC bilgilerini yükle
                is_cpc = device_data['is_cpc'] if 'is_cpc' in device_data.keys() else False
                self.is_cpc_combo.setCurrentText("Evet" if is_cpc else "Hayır")

                # Fiyat bilgilerini yükle
                self.bw_price_input.setText(str(device_data['cpc_bw_price'] if 'cpc_bw_price' in device_data.keys() else 0).replace('.', ','))
                bw_currency = device_data['cpc_bw_currency'] if 'cpc_bw_currency' in device_data.keys() else 'TL'
                self.bw_currency_combo.setCurrentText(bw_currency)
                
                self.color_price_input.setText(str(device_data['cpc_color_price'] if 'cpc_color_price' in device_data.keys() else 0).replace('.', ','))
                color_currency = device_data['cpc_color_currency'] if 'cpc_color_currency' in device_data.keys() else 'TL'
                self.color_currency_combo.setCurrentText(color_currency)
                
                # Kiralama bedeli bilgilerini yükle
                self.rental_price_input.setText(str(device_data['rental_fee'] if 'rental_fee' in device_data.keys() else 0).replace('.', ','))
                rental_currency = device_data['rental_currency'] if 'rental_currency' in device_data.keys() else 'TL'
                self.rental_currency_combo.setCurrentText(rental_currency)

                # Fiyat alanlarını güncelle
                self.toggle_price_fields()
                
        except Exception as e:
            logging.error(f"Cihaz verisi yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Cihaz verileri yüklenirken hata oluştu: {e}")
        """Formdaki verileri doğrular ve bir sözlük olarak döndürür."""
        model = self.model_input.text().strip()
        serial = self.serial_input.text().strip()

        if not model or not serial:
            QMessageBox.warning(self, "Eksik Bilgi", "Model ve Seri Numarası alanları boş bırakılamaz.")
            return None
            
        try:
            # Benzersizlik kontrolü (Sadece yeni cihaz eklerken veya seri no değiştiğinde)
            query = "SELECT id FROM customer_devices WHERE serial_number = ? AND id != ?"
            existing_device = self.db.fetch_one(query, (serial, self.device_id or -1))
            if existing_device:
                QMessageBox.warning(self, "Tekrarlanan Veri", f"'{serial}' seri numarası zaten başka bir cihaza atanmış.")
                return None

            # CPC bilgisi kontrolü
            if self.is_cpc_combo.currentIndex() == 0:
                QMessageBox.warning(self, "Eksik Bilgi", "Lütfen 'Kopya Başı mı?' sorusuna cevap verin.")
                return None
                
            is_cpc = self.is_cpc_combo.currentText() == "Evet"
            
            # CPC fiyat bilgileri - sadece CPC cihazlarda ve dolu ise
            if is_cpc:
                # S/B fiyat kontrolü - boş olabilir
                bw_text = self.bw_price_input.text().strip()
                if bw_text:  # Sadece dolu ise kontrol et
                    try:
                        # Türk formatını destekle: virgül yerine nokta kullan
                        bw_text_normalized = bw_text.replace(',', '.')
                        bw_price = float(bw_text_normalized)
                    except ValueError:
                        QMessageBox.warning(self, "S/B Fiyat Hatası", "S/B birim fiyatı için geçerli bir sayı girin. (Örnek: 0.05 veya 0,05)")
                        return None
                
                # Renkli fiyat kontrolü - sadece renkli cihazlarda ve dolu ise
                if self.type_combo.currentText() == "Renkli":
                    color_text = self.color_price_input.text().strip()
                    if color_text:  # Sadece dolu ise kontrol et
                        try:
                            # Türk formatını destekle: virgül yerine nokta kullan
                            color_text_normalized = color_text.replace(',', '.')
                            color_price = float(color_text_normalized)
                        except ValueError:
                            QMessageBox.warning(self, "Renkli Fiyat Hatası", "Renkli birim fiyatı için geçerli bir sayı girin. (Örnek: 0.05 veya 0,05)")
                            return None
            
            device_data = {
                'customer_id': self.customer_id,
                'location_id': self.location_id,
                'brand': self.brand_input.text().strip(),
                'model': model,
                'serial_number': serial,
                'device_type': self.type_combo.currentText(),
                'purchase_date': datetime.now().strftime('%Y-%m-%d'),  # Bugünün tarihi
                'warranty_status': 'Bilinmiyor',  # Varsayılan garanti durumu
                'status': 'Aktif',  # Varsayılan durum
                'notes': '',  # Boş notlar
                'is_cpc': is_cpc,
                'bw_price': float(self.bw_price_input.text().replace(',', '.') or 0),
                'bw_currency': self.bw_currency_combo.currentText(),
                'color_price': float(self.color_price_input.text().replace(',', '.') or 0),
                'color_currency': self.color_currency_combo.currentText(),
                'rental_fee': float(self.rental_price_input.text().replace(',', '.') or 0),
                'rental_currency': self.rental_currency_combo.currentText()
            }
                    
            return device_data
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veri doğrulanırken bir hata oluştu: {e}")
            return None

    def on_source_changed(self):
        """Cihaz kaynağı değiştiğinde stok modunu yönetir."""
        if self.source_combo.currentText() == "Stoktan Seç":
            self.enable_stock_mode()
        else:
            self.disable_stock_mode()

    def enable_stock_mode(self):
        """Stoktan seçim modunu aktive eder."""
        self.stock_mode_active = True
        self.selected_stock_item = None
        self.model_input.setPlaceholderText("Stoktaki cihazın modelini yazmaya başlayın...")
        self.load_stock_items()
        self.model_input.setFocus()

    def disable_stock_mode(self):
        """Stoktan seçim modunu devre dışı bırakır."""
        self.stock_mode_active = False
        self.selected_stock_item = None
        self.model_input.setPlaceholderText(self.model_default_placeholder)
        if self.stock_completer:
            self.model_input.setCompleter(None)
        self.stock_lookup.clear()

    def load_stock_items(self):
        """Stok öğelerini bellek üzerinde hazırlar."""
        try:
            raw_items = self.db.fetch_all(
                "SELECT id, name, item_type, part_number, COALESCE(color_type, 'Siyah-Beyaz') AS color_type "
                "FROM stock_items WHERE quantity > 0 ORDER BY name, item_type"
            ) or []
            self.stock_items = [dict(item) for item in raw_items]
        except Exception as e:
            logging.error('Stok öğeleri yüklenirken hata: %s', e, exc_info=True)
            self.stock_items = []
        completer_entries = []
        self.stock_lookup = {}
        for item in self.stock_items:
            name = (item.get('name') or '').strip()
            part_number = (item.get('part_number') or '').strip()
            if name:
                key = name.lower()
                if key not in self.stock_lookup:
                    self.stock_lookup[key] = item
                    completer_entries.append(name)
            if part_number:
                key = part_number.lower()
                if key not in self.stock_lookup:
                    self.stock_lookup[key] = item
                    completer_entries.append(part_number)
        self._update_stock_completer(completer_entries)

    def on_model_text_changed(self, text: str):
        """Model alanı değiştiğinde stoktan doldurmayı yönetir."""
        if not self.stock_mode_active:
            return
        if not text:
            self.selected_stock_item = None
            return
        match = self._lookup_stock_item(text)
        if match:
            self._apply_stock_item(match)

    def on_stock_name_selected(self, text: str):
        """Tamamlayıcıdan seçim yapıldığında formu doldurur."""
        if not text:
            return
        match = self._lookup_stock_item(text)
        if match:
            self._apply_stock_item(match)

    def _lookup_stock_item(self, text: str):
        """Girilen metin ile tam eşleşen stok kaydını döndürür."""
        if not text:
            return None
        key = text.strip().lower()
        return self.stock_lookup.get(key)

    def _apply_stock_item(self, item: dict):
        """Seçilen stok kaydını form alanlarına uygular."""
        self.selected_stock_item = item
        item_name = item.get('name') or ''
        with QSignalBlocker(self.model_input):
            if item_name:
                self.model_input.setText(item_name)
        brand_value = item.get('item_type') or ''
        serial_value = item.get('part_number') or ''
        if brand_value:
            self.brand_input.setText(brand_value)
        if serial_value:
            self.serial_input.setText(serial_value)
        color_value_raw = (item.get('color_type') or '').strip()
        color_value_lower = color_value_raw.lower()
        if color_value_lower in {"renkli", "color", "colorli"}:
            color_value = "Renkli"
        elif color_value_lower in {"siyah-beyaz", "siyah beyaz", "mono", "monokrom", "black-white", "black white"}:
            color_value = "Siyah-Beyaz"
        else:
            color_value = "Siyah-Beyaz"
        self.type_combo.setCurrentText(color_value)
        self.is_cpc_combo.setCurrentIndex(1)

    def _update_stock_completer(self, entries):
        """Model alanı için stok tamamlayıcısını günceller."""
        self.stock_model.setStringList(entries)
        if not entries:
            if self.stock_completer:
                self.model_input.setCompleter(None)
            return
        if not self.stock_completer:
            self.stock_completer = QCompleter(self.stock_model, self)
            self.stock_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.stock_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.stock_completer.activated.connect(self.on_stock_name_selected)
        else:
            self.stock_completer.setModel(self.stock_model)
        self.model_input.setCompleter(self.stock_completer)

    def toggle_price_fields(self):
        """'Kopya Başı' seçimine göre fiyat alanlarını gösterir/gizler."""
        is_cpc = self.is_cpc_combo.currentText() == "Evet"
        is_color_device = self.type_combo.currentText() == "Renkli"

        # CPC fiyat alanları
        self.bw_price_label.setVisible(is_cpc)
        self.bw_price_input.setVisible(is_cpc)
        self.bw_price_input.setEnabled(is_cpc)
        self.bw_currency_combo.setVisible(is_cpc)
        self.bw_currency_combo.setEnabled(is_cpc)
        
        self.color_price_label.setVisible(is_cpc and is_color_device)
        self.color_price_input.setVisible(is_cpc and is_color_device)
        self.color_price_input.setEnabled(is_cpc and is_color_device)
        self.color_currency_combo.setVisible(is_cpc and is_color_device)
        self.color_currency_combo.setEnabled(is_cpc and is_color_device)
        
        # Kiralama bedeli alanları - her zaman görünür
        self.rental_price_label.setVisible(True)
        self.rental_price_input.setVisible(True)
        self.rental_price_input.setEnabled(True)
        self.rental_currency_combo.setVisible(True)
        self.rental_currency_combo.setEnabled(True)
        
        if not (is_cpc and is_color_device):
            self.color_price_input.setText("0.0000")

    def get_device_data(self):
        """Formdaki verileri doğrular ve bir sözlük olarak döndürür."""
        model = self.model_input.text().strip()
        serial = self.serial_input.text().strip()

        if not model or not serial:
            QMessageBox.warning(self, "Eksik Bilgi", "Model ve Seri Numarası alanları boş bırakılamaz.")
            return None
            
        try:
            # Benzersizlik kontrolü (Sadece yeni cihaz eklerken veya seri no değiştiğinde)
            query = "SELECT id FROM customer_devices WHERE serial_number = ? AND id != ?"
            existing_device = self.db.fetch_one(query, (serial, self.device_id or -1))
            if existing_device:
                QMessageBox.warning(self, "Tekrarlanan Veri", f"'{serial}' seri numarası zaten başka bir cihaza atanmış.")
                return None

            # CPC bilgisi kontrolü
            if self.is_cpc_combo.currentIndex() == 0:
                QMessageBox.warning(self, "Eksik Bilgi", "Lütfen 'Kopya Başı mı?' sorusuna cevap verin.")
                return None
                
            is_cpc = self.is_cpc_combo.currentText() == "Evet"
            
            # CPC fiyat bilgileri - sadece CPC cihazlarda ve dolu ise
            if is_cpc:
                # S/B fiyat kontrolü - boş olabilir
                bw_text = self.bw_price_input.text().strip()
                if bw_text:  # Sadece dolu ise kontrol et
                    try:
                        # Türk formatını destekle: virgül yerine nokta kullan
                        bw_text_normalized = bw_text.replace(',', '.')
                        bw_price = float(bw_text_normalized)
                    except ValueError:
                        QMessageBox.warning(self, "S/B Fiyat Hatası", "S/B birim fiyatı için geçerli bir sayı girin. (Örnek: 0.05 veya 0,05)")
                        return None
                
                # Renkli fiyat kontrolü - sadece renkli cihazlarda ve dolu ise
                if self.type_combo.currentText() == "Renkli":
                    color_text = self.color_price_input.text().strip()
                    if color_text:  # Sadece dolu ise kontrol et
                        try:
                            # Türk formatını destekle: virgül yerine nokta kullan
                            color_text_normalized = color_text.replace(',', '.')
                            color_price = float(color_text_normalized)
                        except ValueError:
                            QMessageBox.warning(self, "Renkli Fiyat Hatası", "Renkli birim fiyatı için geçerli bir sayı girin. (Örnek: 0.05 veya 0,05)")
                            return None
            
            device_data = {
                'customer_id': self.customer_id,
                'location_id': self.location_id,
                'brand': self.brand_input.text().strip(),
                'model': model,
                'serial_number': serial,
                'device_type': self.type_combo.currentText(),
                'purchase_date': datetime.now().strftime('%Y-%m-%d'),  # Bugünün tarihi
                'warranty_status': 'Bilinmiyor',  # Varsayılan garanti durumu
                'status': 'Aktif',  # Varsayılan durum
                'notes': '',  # Boş notlar
                'is_cpc': is_cpc,
                'bw_price': float(self.bw_price_input.text().replace(',', '.') or 0),
                'bw_currency': self.bw_currency_combo.currentText(),
                'color_price': float(self.color_price_input.text().replace(',', '.') or 0),
                'color_currency': self.color_currency_combo.currentText(),
                'rental_fee': float(self.rental_price_input.text().replace(',', '.') or 0),
                'rental_currency': self.rental_currency_combo.currentText()
            }
                    
            return device_data
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veri doğrulanırken bir hata oluştu: {e}")
            return None
