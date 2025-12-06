# ui/dialogs/location_device_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
                             QLabel, QMessageBox, QSplitter, QHeaderView)
from PyQt6.QtCore import Qt
from utils.database import db_manager

class LocationDeviceDialog(QDialog):
    """Belirli bir lokasyona ait cihazları yöneten dialog."""

    def __init__(self, db, customer_id, location_id, location_name, parent=None):
        super().__init__(parent)
        self.db = db
        self.customer_id = customer_id
        self.location_id = location_id
        self.location_name = location_name
        self.selected_device_id = None

        self.setWindowTitle(f"{location_name} - Cihaz Yönetimi")
        self.resize(1000, 700)

        self.init_ui()
        self.load_devices()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        main_layout = QVBoxLayout(self)

        # Üst kısım: Başlık ve butonlar
        header_layout = QHBoxLayout()
        title_label = QLabel(f"<h2>{self.location_name}</h2>")
        header_layout.addWidget(title_label)

        # Cihaz butonları
        self.add_device_btn = QPushButton("Yeni Cihaz")
        self.edit_device_btn = QPushButton("Düzenle")
        self.delete_device_btn = QPushButton("Sil")
        self.refresh_btn = QPushButton("Yenile")

        self.add_device_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        self.edit_device_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        self.delete_device_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; font-weight: bold; }")

        self.edit_device_btn.setEnabled(False)
        self.delete_device_btn.setEnabled(False)

        header_layout.addStretch()
        header_layout.addWidget(self.add_device_btn)
        header_layout.addWidget(self.edit_device_btn)
        header_layout.addWidget(self.delete_device_btn)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # Ana splitter: Cihaz listesi + Düzenleme paneli
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sol taraf: Cihaz listesi
        device_group = QGroupBox("Lokasyondaki Cihazlar")
        device_layout = QVBoxLayout(device_group)

        self.device_table = QTableWidget(0, 6)
        self.device_table.setHorizontalHeaderLabels(["ID", "Model", "Seri Numarası", "Tür", "Renk Tipi", "CPC"])
        self.device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setShowGrid(True)

        # Sütun genişliklerini ayarla
        self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Model
        self.device_table.setColumnWidth(2, 150)  # Seri No
        self.device_table.setColumnWidth(3, 100)  # Tür
        self.device_table.setColumnWidth(4, 100)  # Renk Tipi
        self.device_table.setColumnWidth(5, 80)   # CPC
        self.device_table.hideColumn(0)

        device_layout.addWidget(self.device_table)
        splitter.addWidget(device_group)

        # Sağ taraf: Düzenleme paneli
        self.edit_panel = self._create_edit_panel()
        splitter.addWidget(self.edit_panel)

        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)

        # Alt kısım: Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)

        # Sinyal bağlantıları
        self.device_table.itemSelectionChanged.connect(self.device_selected)
        self.device_table.itemDoubleClicked.connect(self.edit_selected_device)
        self.add_device_btn.clicked.connect(self.add_device)
        self.edit_device_btn.clicked.connect(self.edit_selected_device)
        self.delete_device_btn.clicked.connect(self.delete_selected_device)
        self.refresh_btn.clicked.connect(self.load_devices)

    def _create_edit_panel(self):
        """Cihaz bilgilerini düzenleme panelini oluşturur."""
        edit_panel = QGroupBox("Cihaz Bilgileri")
        edit_layout = QFormLayout(edit_panel)

        self.model_input = QLineEdit()
        self.serial_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Siyah-Beyaz", "Renkli"])
        self.color_type_combo = QComboBox()
        self.color_type_combo.addItems(["Siyah-Beyaz", "Renkli"])
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

        self.bw_price_label = QLabel("S/B Birim Fiyat:")
        self.color_price_label = QLabel("Renkli Birim Fiyat:")
        self.rental_price_label = QLabel("Kiralama Bedeli:")

        self.rental_price_input = QLineEdit("0,0000")
        self.rental_price_input.focusInEvent = lambda a0: (self.rental_price_input.selectAll(), super(QLineEdit, self.rental_price_input).focusInEvent(a0))[-1]
        self.rental_currency_combo = QComboBox()
        self.rental_currency_combo.addItems(["TL", "USD", "EURO"])
        rental_price_layout = QHBoxLayout()
        rental_price_layout.addWidget(self.rental_price_input)
        rental_price_layout.addWidget(self.rental_currency_combo)

        self.save_device_btn = QPushButton("Değişiklikleri Kaydet")

        edit_layout.addRow("Model (*):", self.model_input)
        edit_layout.addRow("Seri Numarası (*):", self.serial_input)
        edit_layout.addRow("Türü:", self.type_combo)
        edit_layout.addRow("Renk Tipi:", self.color_type_combo)
        edit_layout.addRow("Kopya Başı mı? (*):", self.is_cpc_combo)
        edit_layout.addRow(self.bw_price_label, bw_price_layout)
        edit_layout.addRow(self.color_price_label, color_price_layout)
        edit_layout.addRow(self.rental_price_label, rental_price_layout)
        edit_layout.addRow(self.save_device_btn)

        # Sinyal bağlantıları
        self.is_cpc_combo.currentIndexChanged.connect(self.toggle_price_fields)
        self.type_combo.currentIndexChanged.connect(self.toggle_color_price_field)
        self.save_device_btn.clicked.connect(self.save_device)

        return edit_panel

    def load_devices(self):
        """Lokasyona ait cihazları yükler."""
        self.device_table.setRowCount(0)
        try:
            devices = self.db.fetch_all("""
                SELECT id, device_model, serial_number, device_type, color_type, is_cpc
                FROM customer_devices
                WHERE customer_id = ? AND location_id = ?
                ORDER BY device_model
            """, (self.customer_id, self.location_id))

            for device in devices:
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)

                row_data = [
                    device['id'],
                    device['device_model'] or '',
                    device['serial_number'] or '',
                    device['device_type'] or '',
                    device['color_type'] or '',
                    device['is_cpc'] if device['is_cpc'] is not None else False
                ]

                for col, value in enumerate(row_data):
                    if col == 5:  # CPC kolonu
                        cpc_text = "✅ Evet" if value else "❌ Hayır"
                        item = QTableWidgetItem(cpc_text)
                        item.setToolTip("Sayfa başına ücret sistemi aktif" if value else "Sayfa başına ücret sistemi değil")
                    else:
                        item = QTableWidgetItem(str(value))
                        if len(str(value)) > 20:
                            item.setToolTip(str(value))
                    self.device_table.setItem(row, col, item)

        except Exception as e:
            QMessageBox.warning(self, "Veri Hatası", f"Cihazlar yüklenirken hata: {e}")

    def device_selected(self):
        """Cihaz seçildiğinde düzenleme panelini doldurur."""
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_device_id = None
            self.edit_device_btn.setEnabled(False)
            self.delete_device_btn.setEnabled(False)
            self.clear_edit_form()
            return

        self.selected_device_id = int(self.device_table.item(selected_rows[0].row(), 0).text())
        self.edit_device_btn.setEnabled(True)
        self.delete_device_btn.setEnabled(True)

        # Cihaz bilgilerini yükle
        device_data = self.db.get_customer_device(self.selected_device_id)
        if device_data:
            self._populate_edit_form(device_data)

    def _populate_edit_form(self, data):
        """Düzenleme formunu cihaz verileriyle doldurur."""
        self.model_input.setText(data.get('device_model', ''))
        self.serial_input.setText(data.get('serial_number', ''))
        self.type_combo.setCurrentText(data.get('device_type', 'Siyah-Beyaz'))
        self.color_type_combo.setCurrentText(data.get('color_type', 'Siyah-Beyaz'))

        is_cpc = data.get('is_cpc', False)
        self.is_cpc_combo.setCurrentText("Evet" if is_cpc else "Hayır")

        self.bw_price_input.setText(str(data.get('cpc_bw_price', 0)).replace('.', ','))
        self.bw_currency_combo.setCurrentText(data.get('cpc_bw_currency', 'TL'))

        self.color_price_input.setText(str(data.get('cpc_color_price', 0)).replace('.', ','))
        self.color_currency_combo.setCurrentText(data.get('cpc_color_currency', 'TL'))

        # Kiralama bedeli
        self.rental_price_input.setText(str(data.get('rental_fee', 0)).replace('.', ','))
        self.rental_currency_combo.setCurrentText(data.get('rental_currency', 'TL'))

        self.toggle_price_fields()

    def clear_edit_form(self):
        """Düzenleme formunu temizler."""
        self.model_input.clear()
        self.serial_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.color_type_combo.setCurrentIndex(0)
        self.is_cpc_combo.setCurrentIndex(0)
        self.bw_price_input.setText("0,0000")
        self.color_price_input.setText("0,0000")
        self.rental_price_input.setText("0,0000")
        self.bw_currency_combo.setCurrentIndex(0)
        self.color_currency_combo.setCurrentIndex(0)
        self.rental_currency_combo.setCurrentIndex(0)

    def toggle_price_fields(self):
        """CPC seçimine göre fiyat alanlarını göster/gizle."""
        is_cpc = self.is_cpc_combo.currentText() == "Evet"
        self.bw_price_label.setVisible(is_cpc)
        self.bw_price_input.setVisible(is_cpc)
        self.bw_currency_combo.setVisible(is_cpc)
        self.toggle_color_price_field()

    def toggle_color_price_field(self):
        """Cihaz türüne göre renkli fiyat alanını göster/gizle."""
        is_cpc = self.is_cpc_combo.currentText() == "Evet"
        is_color_device = self.type_combo.currentText() == "Renkli"
        is_visible = is_cpc and is_color_device
        self.color_price_label.setVisible(is_visible)
        self.color_price_input.setVisible(is_visible)
        self.color_currency_combo.setVisible(is_visible)

    def add_device(self):
        """Yeni cihaz ekleme dialogunu açar."""
        from ui.dialogs.device_dialog import DeviceDialog
        dialog = DeviceDialog(self.db, self.customer_id, location_id=self.location_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_devices()

    def edit_selected_device(self):
        """Seçili cihazı düzenleme dialogunu açar."""
        # Çift tıklama için seçili satırdan device_id'yi al
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek istediğiniz cihazı seçin.")
            return

        device_id = int(self.device_table.item(selected_rows[0].row(), 0).text())

        from ui.dialogs.device_dialog import DeviceDialog
        dialog = DeviceDialog(self.db, self.customer_id, device_id=device_id, location_id=self.location_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_devices()

    def delete_selected_device(self):
        """Seçili cihazı siler."""
        if not self.selected_device_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek istediğiniz cihazı seçin.")
            return

        # Cihaz bilgilerini al
        device_data = self.db.get_customer_device(self.selected_device_id)
        if not device_data:
            QMessageBox.critical(self, "Hata", "Cihaz bilgileri bulunamadı.")
            return

        model = device_data.get('device_model', '')
        serial = device_data.get('serial_number', '')

        reply = QMessageBox.question(
            self, "Onay",
            f"'{model}' ({serial}) cihazını silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.db.delete_customer_device(self.selected_device_id)
                if success:
                    QMessageBox.information(self, "Başarılı", "Cihaz başarıyla silindi.")
                    self.selected_device_id = None
                    self.edit_device_btn.setEnabled(False)
                    self.delete_device_btn.setEnabled(False)
                    self.clear_edit_form()
                    self.load_devices()
                else:
                    QMessageBox.critical(self, "Hata", "Cihaz silinirken bir hata oluştu.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Cihaz silinirken hata oluştu:\n{str(e)}")

    def save_device(self):
        """Cihaz bilgilerini kaydeder."""
        if not self.model_input.text() or not self.serial_input.text():
            QMessageBox.warning(self, "Eksik Bilgi", "Model ve Seri Numarası alanları boş bırakılamaz.")
            return

        if self.is_cpc_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen 'Kopya Başı mı?' sorusuna cevap verin.")
            return

        try:
            device_data = {
                "device_model": self.model_input.text(),
                "serial_number": self.serial_input.text(),
                "device_type": self.type_combo.currentText(),
                "color_type": self.color_type_combo.currentText(),
                "is_cpc": self.is_cpc_combo.currentText() == "Evet",
                "bw_price": float(self.bw_price_input.text().replace(',', '.') or 0),
                "bw_currency": self.bw_currency_combo.currentText(),
                "color_price": float(self.color_price_input.text().replace(',', '.') or 0),
                "color_currency": self.color_currency_combo.currentText(),
                "rental_fee": float(self.rental_price_input.text().replace(',', '.') or 0),
                "rental_currency": self.rental_currency_combo.currentText(),
                "location_id": self.location_id  # Lokasyon ID'sini ekle
            }

            saved_id = self.db.save_customer_device(
                self.customer_id,
                device_data,
                self.selected_device_id
            )

            if saved_id:
                message = "Cihaz başarıyla güncellendi." if self.selected_device_id else "Cihaz başarıyla eklendi."
                QMessageBox.information(self, "Başarılı", message)
                self.load_devices()

                # Düzenleme sonrası formu temizle veya güncelle
                if self.selected_device_id:
                    device_data = self.db.get_customer_device(self.selected_device_id)
                    if device_data:
                        self._populate_edit_form(device_data)
                else:
                    self.clear_edit_form()
            else:
                QMessageBox.critical(self, "Hata", "Cihaz kaydedilirken bir hata oluştu.")

        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Cihaz kaydedilirken hata oluştu:\n{str(e)}")