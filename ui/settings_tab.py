# ui/settings_tab.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QMessageBox, QGridLayout,
                            QDialog, QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QHBoxLayout, QLabel, QSizePolicy, QLayout)
from PyQt6.QtCore import pyqtSignal as Signal, Qt

from utils.database import db_manager
from .dialogs.company_settings_dialog import CompanySettingsDialog
from .dialogs.smtp_settings_dialog import SmtpSettingsDialog
from .dialogs.user_management_dialog import UserManagementDialog
from .dialogs.data_transfer_dialog import DataTransferDialog
from .dialogs.api_settings_dialog import ApiSettingsDialog
from .dialogs.network_path_dialog import NetworkPathDialog
from .dialogs.bank_settings_dialog import BankSettingsDialog
from .dialogs.backup_settings_dialog import BackupSettingsDialog
from .dialogs.update_manager_dialog import UpdateManagerDialog
from .dialogs.sync_status_dialog import SyncStatusDialog

class SettingsTab(QWidget):
    """Uygulama ayarlarını yönetmek için kullanılan sekme."""
    settings_saved = Signal()

    def __init__(self, status_bar, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.status_bar = status_bar
        self.init_ui()

    def init_ui(self):
        """Ana layout'u oluştur ve buton gridini ekle."""
        main_layout = QVBoxLayout(self)
        grid_layout = self._create_buttons_grid()
        main_layout.addLayout(grid_layout)
        main_layout.addStretch()
        self._connect_signals()

    def _create_buttons_grid(self):
        """Ayar butonlarını QGroupBox ile modern ve temiz şekilde gruplandırır."""
        from PyQt6.QtWidgets import QGroupBox
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        button_style = """
            QPushButton {
                font-size: 9pt;
                text-align: center;
                padding: 8px 14px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3B82F6, stop:1 #2563EB);
                border: 1px solid #1E40AF;
                border-radius: 5px;
                color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #60A5FA, stop:1 #3B82F6); border-color: #2563EB; }
            QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1E40AF); }
        """

        # Firma Ayarları
        group_firma = QGroupBox("🏢 Firma Ayarları")
        group_firma.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; color: #1E40AF; border: 2px solid #3B82F6; border-radius: 8px; margin-top: 8px; padding: 8px; }")
        grid1 = QGridLayout()
        self.btn_company = QPushButton("Firma & KDV"); self.btn_bank = QPushButton("Banka"); self.btn_technicians = QPushButton("Teknisyen")
        for btn in [self.btn_company, self.btn_bank, self.btn_technicians]:
            btn.setMinimumHeight(32); btn.setMaximumHeight(32); btn.setFixedWidth(185); btn.setStyleSheet(button_style)
        grid1.addWidget(self.btn_company, 0, 0); grid1.addWidget(self.btn_bank, 0, 1); grid1.addWidget(self.btn_technicians, 0, 2)
        group_firma.setLayout(grid1)
        main_layout.addWidget(group_firma)

        # Sistem Ayarları
        group_sistem = QGroupBox("⚙ Sistem Ayarları")
        group_sistem.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; color: #1E40AF; border: 2px solid #3B82F6; border-radius: 8px; margin-top: 8px; padding: 8px; }")
        grid2 = QGridLayout()
        self.btn_smtp = QPushButton("E-Posta"); self.btn_users = QPushButton("Kullanıcılar"); self.btn_activation = QPushButton("Lisans"); self.btn_api = QPushButton("API"); self.btn_db_path = QPushButton("Veritabanı"); self.btn_update = QPushButton("Güncelleme"); self.btn_about = QPushButton("Hakkında")
        for btn in [self.btn_smtp, self.btn_users, self.btn_activation, self.btn_api, self.btn_db_path, self.btn_update, self.btn_about]:
            btn.setMinimumHeight(32); btn.setMaximumHeight(32); btn.setFixedWidth(185); btn.setStyleSheet(button_style)
        grid2.addWidget(self.btn_smtp, 0, 0); grid2.addWidget(self.btn_users, 0, 1); grid2.addWidget(self.btn_activation, 0, 2)
        grid2.addWidget(self.btn_api, 1, 0); grid2.addWidget(self.btn_db_path, 1, 1); grid2.addWidget(self.btn_update, 1, 2)
        grid2.addWidget(self.btn_about, 2, 2)
        group_sistem.setLayout(grid2)
        main_layout.addWidget(group_sistem)

        # Senkronizasyon & Yedekleme
        group_sync = QGroupBox("☁️ Senkronizasyon & Yedekleme")
        group_sync.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; color: #1E40AF; border: 2px solid #3B82F6; border-radius: 8px; margin-top: 8px; padding: 8px; }")
        grid3 = QGridLayout()
        self.btn_sync_status = QPushButton("Senkronizasyon"); self.btn_auto_backup = QPushButton("Oto. Yedek"); self.btn_data = QPushButton("Veri Aktar")
        for btn in [self.btn_sync_status, self.btn_auto_backup, self.btn_data]:
            btn.setMinimumHeight(32); btn.setMaximumHeight(32); btn.setFixedWidth(185); btn.setStyleSheet(button_style)
        grid3.addWidget(self.btn_sync_status, 0, 0); grid3.addWidget(self.btn_auto_backup, 0, 1); grid3.addWidget(self.btn_data, 0, 2)
        group_sync.setLayout(grid3)
        main_layout.addWidget(group_sync)

        main_layout.addStretch()
        return main_layout

    def _connect_signals(self):
        """Buton sinyallerini ilgili slotlara bağlar."""
        # Firma Ayarları
        self.btn_company.clicked.connect(self.open_company_settings)
        self.btn_bank.clicked.connect(self.open_bank_settings)
        self.btn_technicians.clicked.connect(self.open_technician_management)
        # Sistem Ayarları
        self.btn_smtp.clicked.connect(self.open_smtp_settings)
        self.btn_users.clicked.connect(self.open_user_management)
        self.btn_activation.clicked.connect(self.open_activation_dialog)
        self.btn_api.clicked.connect(self.open_api_settings)
        self.btn_db_path.clicked.connect(self.open_network_path_dialog)
        self.btn_update.clicked.connect(self.open_update_manager)
        self.btn_about.clicked.connect(self.show_about_dialog)
        # Senkronizasyon & Yedekleme
        self.btn_sync_status.clicked.connect(self.open_sync_status)
        self.btn_auto_backup.clicked.connect(self.open_backup_settings)
        self.btn_data.clicked.connect(self.open_data_transfer)

    def open_company_settings(self):
        """Firma ayarları diyalogunu açar."""
        try:
            dialog = CompanySettingsDialog(self)
            if dialog.exec() == QMessageBox.DialogCode.Accepted:
                self.settings_saved.emit()
                self.status_bar.showMessage("Firma ayarları başarıyla güncellendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Firma ayarları açılırken bir hata oluştu: {e}")

    def open_smtp_settings(self):
        """SMTP ayarları diyalogunu açar."""
        try:
            dialog = SmtpSettingsDialog(self.db, self.status_bar, self)
            if dialog.exec() == QMessageBox.DialogCode.Accepted:
                self.settings_saved.emit()
                self.status_bar.showMessage("E-posta ayarları başarıyla güncellendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"E-posta ayarları açılırken bir hata oluştu: {e}")

    def open_user_management(self):
        """Kullanıcı yönetimi diyalogunu açar."""
        try:
            dialog = UserManagementDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kullanıcı yönetimi açılırken bir hata oluştu: {e}")

    def open_technician_management(self):
        """Teknisyen yönetimi diyalogunu açar."""
        self.show_technician_dialog()

    def open_api_settings(self):
        """API ayarları diyalogunu açar."""
        try:
            dialog = ApiSettingsDialog(self.db, self)
            if dialog.exec() == QMessageBox.DialogCode.Accepted:
                self.settings_saved.emit()
                self.status_bar.showMessage("API ayarları başarıyla güncellendi.", 3000)
                # AI sekmesini yenile
                if hasattr(self.parent(), 'ai_tab'):
                    self.parent().ai_tab.check_activation()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"API ayarları açılırken bir hata oluştu: {e}")

    def open_bank_settings(self):
        """Banka ayarları diyalogunu açar."""
        try:
            dialog = BankSettingsDialog(self.db, self)
            if dialog.exec() == QMessageBox.DialogCode.Accepted:
                self.settings_saved.emit()
                self.status_bar.showMessage("Banka ayarları başarıyla güncellendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Banka ayarları açılırken bir hata oluştu: {e}")
    
    def open_network_path_dialog(self):
        """Ağ yolu diyalogunu açar."""
        try:
            dialog = NetworkPathDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Ağ yolu ayarları açılırken bir hata oluştu: {e}")

    def open_backup_settings(self):
        """Otomatik yedekleme ayarları diyalogunu açar."""
        try:
            from utils.settings_manager import SettingsManager
            settings_manager = SettingsManager()
            dialog = BackupSettingsDialog(self.db, settings_manager, self)
            if dialog.exec() == QMessageBox.DialogCode.Accepted:
                self.settings_saved.emit()
                self.status_bar.showMessage("Otomatik yedekleme ayarları başarıyla güncellendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Otomatik yedekleme ayarları açılırken bir hata oluştu: {e}")

    def open_sync_status(self):
        """Senkronizasyon durumu diyalogunu açar."""
        try:
            from utils.sync_manager import get_sync_manager
            
            # Database path'i al
            db_path = getattr(self.db, 'database_path', None)
            if not db_path:
                # Fallback: AppData yolunu kullan
                import os
                from pathlib import Path
                app_data = Path(os.environ.get('APPDATA', '~')) / 'ProServis'
                db_path = str(app_data / 'teknik_servis_local.db')
            
            sync_manager = get_sync_manager(database_path=db_path)
            dialog = SyncStatusDialog(sync_manager, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Senkronizasyon durumu açılırken bir hata oluştu: {e}")

    def open_data_transfer(self):
        """Veri aktarımı diyalogunu açar."""
        try:
            dialog = DataTransferDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veri aktarımı diyalogu açılırken bir hata oluştu: {e}")

    def show_about_dialog(self):
        """Program hakkında diyalogunu gösterir."""
        about_text = """
        <h3>ProServis Teknik Servis Yönetim Sistemi</h3>
        <p><b>Sürüm:</b> 2.0</p>
        <p><b>Geliştirici:</b> ÜMİT SAĞDIÇ</p>
        <p><b>E-posta:</b> umitsagdic77@gmail.com</p>
        <p><b>Telefon:</b> 0543 203 34 43</p>
        <p><b>Açıklama:</b> Teknik servis işlemlerini yönetmek için geliştirilmiş kapsamlı bir masaüstü uygulamasıdır.</p>
        <p><b>Telif Hakkı:</b> © 2025 ÜMİT SAĞDIÇ - Tüm hakları saklıdır.</p>
        """
        QMessageBox.about(self, "Program Hakkında", about_text)

    def show_technician_dialog(self):
        """Teknisyen yönetimi diyalogunu gösterir."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QLineEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Teknisyen Yönetimi")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Teknisyen tablosu
        self.technician_table = QTableWidget(0, 5)
        self.technician_table.setHorizontalHeaderLabels(["ID", "Ad", "Soyad", "Telefon", "E-posta"])
        self.technician_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.technician_table.hideColumn(0)
        
        layout.addWidget(self.technician_table)
        
        # Butonlar
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Teknisyen Ekle")
        edit_btn = QPushButton("Düzenle")
        delete_btn = QPushButton("Sil")
        
        add_btn.clicked.connect(lambda: self.add_edit_technician(dialog))
        edit_btn.clicked.connect(lambda: self.add_edit_technician(dialog, edit=True))
        delete_btn.clicked.connect(lambda: self.delete_technician(dialog))
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Teknisyenleri yükle
        self.refresh_technicians(dialog)
        
        dialog.exec()

    def refresh_technicians(self, parent_dialog):
        """Teknisyen tablosunu yeniler."""
        self.technician_table.setRowCount(0)
        try:
            technicians = db_manager.fetch_all("SELECT id, name, surname, phone, email FROM technicians WHERE is_active = 1 ORDER BY name, surname")
            for row_data in technicians:
                row_index = self.technician_table.rowCount()
                self.technician_table.insertRow(row_index)
                for col, value in enumerate(row_data):
                    self.technician_table.setItem(row_index, col, QTableWidgetItem(str(value or "")))
        except Exception as e:
            QMessageBox.warning(parent_dialog, "Veri Hatası", f"Teknisyenler yüklenemedi: {e}")

    def add_edit_technician(self, parent_dialog, edit=False):
        """Teknisyen ekleme/düzenleme diyalogu."""
        from PyQt6.QtWidgets import QDialogButtonBox
        
        selected_rows = self.technician_table.selectionModel().selectedRows()
        tech_id = None
        
        if edit and not selected_rows:
            QMessageBox.warning(parent_dialog, "Seçim Hatası", "Lütfen düzenlemek için bir teknisyen seçin.")
            return
        
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("Teknisyen Düzenle" if edit else "Yeni Teknisyen")
        dialog.resize(350, 250)
        
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        surname_input = QLineEdit()
        phone_input = QLineEdit()
        email_input = QLineEdit()
        
        layout.addRow("Ad (*):", name_input)
        layout.addRow("Soyad (*):", surname_input)
        layout.addRow("Telefon:", phone_input)
        layout.addRow("E-posta:", email_input)
        
        if edit and selected_rows:
            row = selected_rows[0].row()
            tech_id = int(self.technician_table.item(row, 0).text())
            name_input.setText(self.technician_table.item(row, 1).text())
            surname_input.setText(self.technician_table.item(row, 2).text())
            phone_input.setText(self.technician_table.item(row, 3).text() or "")
            email_input.setText(self.technician_table.item(row, 4).text() or "")
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not name_input.text() or not surname_input.text():
                QMessageBox.warning(dialog, "Hata", "Ad ve soyad alanları zorunludur.")
                return
            
            try:
                if edit:
                    db_manager.execute_query(
                        "UPDATE technicians SET name=?, surname=?, phone=?, email=? WHERE id=?",
                        (name_input.text(), surname_input.text(), phone_input.text(), email_input.text(), tech_id)
                    )
                else:
                    db_manager.execute_query(
                        "INSERT INTO technicians (name, surname, phone, email) VALUES (?, ?, ?, ?)",
                        (name_input.text(), surname_input.text(), phone_input.text(), email_input.text())
                    )
                
                self.refresh_technicians(parent_dialog)
                self.status_bar.showMessage("Teknisyen başarıyla kaydedildi.", 3000)
                
            except Exception as e:
                QMessageBox.critical(dialog, "Hata", f"Teknisyen kaydedilirken hata: {e}")

    def delete_technician(self, parent_dialog):
        """Seçili teknisyeni siler."""
        selected_rows = self.technician_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(parent_dialog, "Seçim Hatası", "Lütfen silmek için bir teknisyen seçin.")
            return
        
        row = selected_rows[0].row()
        tech_id = int(self.technician_table.item(row, 0).text())
        tech_name = f"{self.technician_table.item(row, 1).text()} {self.technician_table.item(row, 2).text()}"
        
        reply = QMessageBox.question(
            parent_dialog, "Teknisyen Sil", 
            f"'{tech_name}' adlı teknisyeni silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Soft delete - is_active = 0
                db_manager.execute_query("UPDATE technicians SET is_active = 0 WHERE id = ?", (tech_id,))
                self.refresh_technicians(parent_dialog)
                self.status_bar.showMessage("Teknisyen başarıyla silindi.", 3000)
            except Exception as e:
                QMessageBox.critical(parent_dialog, "Hata", f"Teknisyen silinirken hata: {e}")

    def set_setting(self, key, value):
        """Ayar anahtarı ve değerini veritabanına kaydeder."""
        try:
            from utils.settings_manager import save_setting
            save_setting(key, value)
        except Exception as e:
            raise Exception(f"Ayar kaydedilirken hata oluştu: {e}")

    def get_setting(self, key, default_value=""):
        """Ayar anahtarının değerini veritabanından alır."""
        try:
            from utils.settings_manager import get_setting
            return get_setting(key, default_value)
        except Exception as e:
            return default_value

    def open_activation_dialog(self):
        """Aktivasyon dialog'unu açar."""
        try:
            from .dialogs.activation_dialog import ActivationDialog
            from utils.settings_manager import load_app_config
            
            config = load_app_config()
            
            # Mevcut durumu kontrol et
            if config.get('is_activated', False):
                QMessageBox.information(
                    self,
                    "Lisans Durumu",
                    "✅ Uygulama zaten aktive edilmiş durumda!\n\n"
                    "Lisans Durumu: Aktif\n"
                    "Sürüm: ProServis v2.0"
                )
                return
            
            # Deneme sürümü kontrolü
            first_run_date = config.get('first_run_date')
            if first_run_date:
                from datetime import datetime
                try:
                    start_date = datetime.strptime(first_run_date, "%Y-%m-%d")
                    days_passed = (datetime.now() - start_date).days
                    remaining_days = 30 - days_passed
                    
                    if remaining_days > 0:
                        reply = QMessageBox.question(
                            self,
                            "Lisans Durumu",
                            f"🕒 Deneme sürümünü kullanıyorsunuz.\n\n"
                            f"Kalan gün sayısı: {remaining_days}\n\n"
                            f"Şimdi lisans anahtarı girmek istiyor musunuz?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.No:
                            return
                except ValueError:
                    pass
            
            # Aktivasyon dialog'unu göster
            activation_dialog = ActivationDialog(self)
            activation_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Hata",
                f"Aktivasyon penceresi açılırken hata oluştu:\n{str(e)}"
            )

    def open_update_manager(self):
        """Sistem güncelleme yöneticisini açar."""
        try:
            dialog = UpdateManagerDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Güncelleme yöneticisi açılırken bir hata oluştu: {e}")

    def get_all_customers_and_devices(self):
        """Tüm müşteri ve cihaz bilgilerini getirir."""
        try:
            return self.db.get_all_customers_and_devices()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Müşteri ve cihaz bilgileri alınırken hata oluştu: {e}")
            return {}