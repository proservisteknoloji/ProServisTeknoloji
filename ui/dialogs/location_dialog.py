"""
Müşteri lokasyon yönetimi için dialog sınıfı.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QFormLayout, QGroupBox, QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt
from utils.database import db_manager


class LocationDialog(QDialog):
    """
    Müşteri lokasyonlarını yönetmek için dialog sınıfı.
    Lokasyon ekleme, düzenleme ve silme işlemlerini destekler.
    """

    def __init__(self, customer_id=None, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.location_id = None
        self.setWindowTitle("Lokasyon Yönetimi")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()
        self.load_locations()

    def setup_ui(self):
        """UI bileşenlerini oluşturur."""
        layout = QVBoxLayout()

        # Lokasyon listesi grubu
        list_group = QGroupBox("Lokasyonlar")
        list_layout = QVBoxLayout()

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Lokasyon Adı", "Adres", "Telefon", "E-posta"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_selected_location)

        # Butonlar
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Yeni Lokasyon")
        self.add_button.clicked.connect(self.add_location)

        self.edit_button = QPushButton("Düzenle")
        self.edit_button.clicked.connect(self.edit_selected_location)

        self.delete_button = QPushButton("Sil")
        self.delete_button.clicked.connect(self.delete_selected_location)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        list_layout.addWidget(self.table)
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)

        layout.addWidget(list_group)
        self.setLayout(layout)

    def load_locations(self):
        """Müşteriye ait lokasyonları yükler."""
        try:
            if self.customer_id:
                locations = db_manager.fetch_all("""
                    SELECT id, location_name, address, phone, email
                    FROM customer_locations
                    WHERE customer_id = ?
                    ORDER BY location_name
                """, (self.customer_id,))
            else:
                locations = db_manager.fetch_all("""
                    SELECT cl.id, cl.location_name, cl.address, cl.phone, cl.email, c.name as customer_name
                    FROM customer_locations cl
                    JOIN customers c ON cl.customer_id = c.id
                    ORDER BY c.name, cl.location_name
                """)

            self.table.setRowCount(len(locations))

            for row, location in enumerate(locations):
                self.table.setItem(row, 0, QTableWidgetItem(str(location['id'])))
                self.table.setItem(row, 1, QTableWidgetItem(location['location_name'] or ''))
                self.table.setItem(row, 2, QTableWidgetItem(location['address'] or ''))
                self.table.setItem(row, 3, QTableWidgetItem(location['phone'] or ''))
                self.table.setItem(row, 4, QTableWidgetItem(location['email'] or ''))

        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Lokasyonlar yüklenirken hata oluştu:\n{str(e)}")

    def add_location(self):
        """Yeni lokasyon ekleme dialogunu açar."""
        dialog = LocationEditDialog(self.customer_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_locations()

    def edit_selected_location(self):
        """Seçili lokasyonu düzenleme dialogunu açar."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek istediğiniz lokasyonu seçin.")
            return

        location_id = int(self.table.item(current_row, 0).text())
        dialog = LocationEditDialog(self.customer_id, location_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_locations()

    def delete_selected_location(self):
        """Seçili lokasyonu siler."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek istediğiniz lokasyonu seçin.")
            return

        location_id = int(self.table.item(current_row, 0).text())
        location_name = self.table.item(current_row, 1).text()

        # Bu lokasyonda cihaz var mı kontrol et
        device_count = db_manager.fetch_one("""
            SELECT COUNT(*) as count FROM customer_devices WHERE location_id = ?
        """, (location_id,))

        if device_count and device_count['count'] > 0:
            QMessageBox.warning(self, "Silinemez",
                              f"'{location_name}' lokasyonunda {device_count['count']} cihaz bulunmaktadır.\n"
                              "Lokasyonu silmeden önce bu cihazları başka bir lokasyona taşımalısınız.")
            return

        reply = QMessageBox.question(self, "Onay",
                                   f"'{location_name}' lokasyonunu silmek istediğinizden emin misiniz?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                db_manager.execute_query("DELETE FROM customer_locations WHERE id = ?", (location_id,))
                QMessageBox.information(self, "Başarılı", "Lokasyon başarıyla silindi.")
                self.load_locations()
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Lokasyon silinirken hata oluştu:\n{str(e)}")


class LocationEditDialog(QDialog):
    """
    Lokasyon ekleme/düzenleme için dialog sınıfı.
    """

    def __init__(self, customer_id, location_id=None, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.location_id = location_id
        self.setWindowTitle("Lokasyon Ekle" if location_id is None else "Lokasyon Düzenle")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        if location_id:
            self.load_location_data()

    def setup_ui(self):
        """UI bileşenlerini oluşturur."""
        layout = QVBoxLayout()

        # Form grubu
        form_group = QGroupBox("Lokasyon Bilgileri")
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Örn: Ankara Şube, İstanbul Merkez")

        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        self.address_input.setPlaceholderText("Adres bilgilerini girin")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Telefon numarası")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("E-posta adresi")

        form_layout.addRow("Lokasyon Adı:", self.name_input)
        form_layout.addRow("Adres:", self.address_input)
        form_layout.addRow("Telefon:", self.phone_input)
        form_layout.addRow("E-posta:", self.email_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Butonlar
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Kaydet")
        self.save_button.clicked.connect(self.save_location)

        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_location_data(self):
        """Düzenleme için lokasyon verilerini yükler."""
        try:
            location = db_manager.fetch_one("""
                SELECT location_name, address, phone, email
                FROM customer_locations
                WHERE id = ?
            """, (self.location_id,))

            if location:
                self.name_input.setText(location['location_name'] or '')
                self.address_input.setText(location['address'] or '')
                self.phone_input.setText(location['phone'] or '')
                self.email_input.setText(location['email'] or '')

        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Lokasyon verileri yüklenirken hata oluştu:\n{str(e)}")

    def save_location(self):
        """Lokasyon bilgilerini kaydeder."""
        location_name = self.name_input.text().strip()
        address = self.address_input.toPlainText().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()

        if not location_name:
            QMessageBox.warning(self, "Eksik Bilgi", "Lokasyon adı zorunludur.")
            return

        try:
            if self.location_id:
                # Güncelleme
                db_manager.execute_query("""
                    UPDATE customer_locations
                    SET location_name = ?, address = ?, phone = ?, email = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (location_name, address, phone, email, self.location_id))
                QMessageBox.information(self, "Başarılı", "Lokasyon başarıyla güncellendi.")
            else:
                # Yeni ekleme
                db_manager.execute_query("""
                    INSERT INTO customer_locations (customer_id, location_name, address, phone, email)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.customer_id, location_name, address, phone, email))
                QMessageBox.information(self, "Başarılı", "Lokasyon başarıyla eklendi.")

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Lokasyon kaydedilirken hata oluştu:\n{str(e)}")
