"""
Basitleştirilmiş Ayarlar Sekmesi
Butonları işlevlere göre gruplandırılmış hali
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, 
    QGroupBox, QGridLayout, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .dialogs.company_settings_dialog import CompanySettingsDialog
from .dialogs.smtp_settings_dialog import SMTPSettingsDialog
from .dialogs.user_management_dialog import UserManagementDialog
from .dialogs.activation_dialog import ActivationDialog
from .dialogs.update_manager_dialog import UpdateManagerDialog
from .dialogs.backup_restore_dialog import BackupRestoreDialog
from .dialogs.data_transfer_dialog import DataTransferDialog
from .dialogs.api_settings_dialog import APISettingsDialog
from .dialogs.bank_settings_dialog import BankSettingsDialog
from .dialogs.price_settings_dialog import PriceSettingsDialog


class SimplifiedSettingsTab(QWidget):
    """Basitleştirilmiş ayarlar sekmesi"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()
    
    def init_ui(self):
        """UI'ı oluştur"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Başlık
        title = QLabel("⚙️ Ayarlar")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        # 1. Firma ve İşletme Ayarları
        business_group = self._create_group(
            "🏢 Firma ve İşletme Ayarları",
            [
                ("Firma Bilgileri ve KDV", self.open_company_settings),
                ("Banka Hesap Bilgileri", self.open_bank_settings),
                ("Fiyat ve Kâr Marjı Ayarları", self.open_price_settings),
            ]
        )
        scroll_layout.addWidget(business_group)
        
        # 2. Sistem ve Kullanıcılar
        system_group = self._create_group(
            "👥 Sistem ve Kullanıcı Yönetimi",
            [
                ("Kullanıcı Yönetimi", self.open_user_management),
                ("Lisans ve Aktivasyon", self.open_activation),
            ]
        )
        scroll_layout.addWidget(system_group)
        
        # 3. İletişim ve Entegrasyonlar
        comm_group = self._create_group(
            "📡 İletişim ve Entegrasyonlar",
            [
                ("E-Posta (SMTP) Ayarları", self.open_smtp_settings),
                ("API Ayarları ve Entegrasyonlar", self.open_api_settings),
            ]
        )
        scroll_layout.addWidget(comm_group)
        
        # 4. Yedekleme ve Veri
        data_group = self._create_group(
            "💾 Yedekleme ve Veri Yönetimi",
            [
                ("Yedekleme ve Geri Yükleme", self.open_backup_restore),
                ("Veri Aktarımı (İçe/Dışa)", self.open_data_transfer),
            ]
        )
        scroll_layout.addWidget(data_group)
        
        # 5. Güncelleme ve Hakkında
        about_group = self._create_group(
            "ℹ️ Sistem Bilgileri",
            [
                ("Sistem Güncelleme", self.open_update_manager),
                ("Program Hakkında", self.show_about),
            ]
        )
        scroll_layout.addWidget(about_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
    
    def _create_group(self, title: str, buttons: list) -> QGroupBox:
        """
        Ayar grubu oluştur
        
        Args:
            title: Grup başlığı
            buttons: [(button_text, callback), ...] listesi
        """
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        for button_text, callback in buttons:
            btn = QPushButton(button_text)
            btn.setMinimumHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 15px;
                    font-size: 11pt;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    background-color: white;
                }
                QPushButton:hover {
                    background-color: #f0f8ff;
                    border-color: #0078d4;
                }
                QPushButton:pressed {
                    background-color: #e0f0ff;
                }
            """)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        group.setLayout(layout)
        return group
    
    # ============================================
    # Dialog açma metodları
    # ============================================
    
    def open_company_settings(self):
        """Firma ayarları dialogunu aç"""
        try:
            dialog = CompanySettingsDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_bank_settings(self):
        """Banka ayarları dialogunu aç"""
        try:
            dialog = BankSettingsDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_price_settings(self):
        """Fiyat ayarları dialogunu aç"""
        try:
            dialog = PriceSettingsDialog(self.db, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_user_management(self):
        """Kullanıcı yönetimi dialogunu aç"""
        try:
            dialog = UserManagementDialog(self.db, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_activation(self):
        """Aktivasyon dialogunu aç"""
        try:
            dialog = ActivationDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_smtp_settings(self):
        """SMTP ayarları dialogunu aç"""
        try:
            dialog = SMTPSettingsDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_api_settings(self):
        """API ayarları dialogunu aç"""
        try:
            dialog = APISettingsDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_backup_restore(self):
        """Yedekleme/geri yükleme dialogunu aç"""
        try:
            dialog = BackupRestoreDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_data_transfer(self):
        """Veri aktarımı dialogunu aç"""
        try:
            dialog = DataTransferDialog(self.db, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def open_update_manager(self):
        """Güncelleme yöneticisi dialogunu aç"""
        try:
            dialog = UpdateManagerDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dialog açılamadı: {str(e)}")
    
    def show_about(self):
        """Program hakkında bilgi göster"""
        about_text = """
        <h2>ProServis v2.2</h2>
        <p><b>Teknik Servis Yönetim Sistemi</b></p>
        <p>© 2024-2025 Tüm hakları saklıdır.</p>
        <hr>
        <p><b>Geliştirici:</b> Ümit Sağdıç</p>
        <p><b>İletişim:</b> umitsagdic77@gmail.com</p>
        <hr>
        <p>Bu yazılım, teknik servis işletmelerinin günlük operasyonlarını 
        yönetmek üzere geliştirilmiştir.</p>
        """
        QMessageBox.about(self, "ProServis Hakkında", about_text)
