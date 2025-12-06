# ui/dialogs/smtp_settings_dialog.py

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox,
                             QPushButton, QDialogButtonBox, QMessageBox)
from utils.workers import EmailThread
from utils.database import db_manager
from typing import Optional

def normalize_email(email):
    """Email adresini küçük harfe çevirir ve Türkçe karakterleri İngilizce karşılıklarıyla değiştirir"""
    if not email:
        return email
    
    # Küçük harfe çevir
    email = email.lower()
    
    # Türkçe karakterleri İngilizce karşılıklarıyla değiştir
    turkish_chars = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
    }
    
    for turkish, english in turkish_chars.items():
        email = email.replace(turkish, english)
    
    return email

class SmtpSettingsDialog(QDialog):
    """E-posta (SMTP) sunucu ayarlarını yapılandırmak için kullanılan diyalog."""

    def __init__(self, db, status_bar, parent=None):
        super().__init__(parent)
        self.db = db
        self.status_bar = status_bar
        self.email_thread = None  # E-posta thread'ini saklamak için referans

        self.setWindowTitle("E-Posta (SMTP) Ayarları")
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        self._create_widgets()
        self._create_layout(layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.smtp_host = QLineEdit()
        self.smtp_port = QLineEdit()
        self.smtp_user = QLineEdit()
        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.smtp_encryption = QComboBox()
        self.smtp_encryption.addItems(["TLS", "SSL"])
        self.test_smtp_btn = QPushButton("Test E-postası Gönder")
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)

    def _create_layout(self, layout: QFormLayout):
        """Widget'ları layout'a yerleştirir."""
        layout.addRow("Host:", self.smtp_host)
        layout.addRow("Port:", self.smtp_port)
        layout.addRow("Kullanıcı Adı (E-posta):", self.smtp_user)
        
        # Email normalize etme
        def normalize_smtp_email():
            current_text = self.smtp_user.text()
            normalized = normalize_email(current_text)
            if normalized != current_text:
                self.smtp_user.setText(normalized)
        
        self.smtp_user.textChanged.connect(normalize_smtp_email)
        layout.addRow("Şifre:", self.smtp_pass)
        layout.addRow("Şifreleme:", self.smtp_encryption)
        layout.addRow(self.test_smtp_btn)
        layout.addRow(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.test_smtp_btn.clicked.connect(self._test_smtp)

    def _load_settings(self):
        """Mevcut SMTP ayarlarını veritabanından yükler ve formda gösterir."""
        try:
            self.smtp_host.setText(self.db.get_setting('smtp_host', ''))
            self.smtp_port.setText(self.db.get_setting('smtp_port', '587'))
            self.smtp_user.setText(self.db.get_setting('smtp_user', ''))
            self.smtp_pass.setText(self.db.get_setting('smtp_password', ''))
            self.smtp_encryption.setCurrentText(self.db.get_setting('smtp_encryption', 'TLS'))
        except Exception as e:
            QMessageBox.critical(self, "Ayarları Yükleme Hatası", f"SMTP ayarları yüklenirken bir hata oluştu: {e}")

    def _save_settings(self) -> bool:
        """Formdaki ayarları veritabanına kaydeder."""
        try:
            self.db.set_setting('smtp_host', self.smtp_host.text())
            self.db.set_setting('smtp_port', self.smtp_port.text())
            self.db.set_setting('smtp_user', self.smtp_user.text())
            self.db.set_setting('smtp_password', self.smtp_pass.text())
            self.db.set_setting('smtp_encryption', self.smtp_encryption.currentText())
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ayarları Kaydetme Hatası", f"SMTP ayarları kaydedilirken bir hata oluştu: {e}")
            return False

    def accept(self):
        """Ayarları kaydedip diyalogu kapatır."""
        if self._save_settings():
            QMessageBox.information(self, "Başarılı", "SMTP ayarları başarıyla kaydedildi.")
            super().accept()

    def _collect_smtp_settings(self) -> Optional[dict]:
        """Formdaki SMTP ayarlarını toplar ve doğrular."""
        try:
            port = int(self.smtp_port.text())
        except ValueError:
            QMessageBox.warning(self, "Geçersiz Değer", "Port alanı sayısal bir değer olmalıdır.")
            return None

        settings = {
            'host': self.smtp_host.text(),
            'port': port,
            'user': self.smtp_user.text(),
            'password': self.smtp_pass.text(),
            'encryption': self.smtp_encryption.currentText()
        }
        
        if not all(s for s in settings.values() if isinstance(s, str)):
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen test e-postası göndermeden önce tüm SMTP alanlarını doldurun.")
            return None
        
        return settings

    def _test_smtp(self):
        """Girilen SMTP ayarlarını test etmek için bir e-posta gönderir."""
        smtp_settings = self._collect_smtp_settings()
        if not smtp_settings:
            return
            
        # Firma adını al
        company_info = self.db.get_all_company_info()
        company_name = company_info.get('company_name', 'ProServis')
            
        message_details = {
            'recipient': smtp_settings['user'],
            'subject': 'ProServis Test E-postası',
            'body': 'Bu, ProServis uygulamasından gönderilen bir test e-postasıdır. Ayarlarınız doğru çalışıyor.',
            'sender_name': company_name
        }
        
        self.status_bar.showMessage("Test e-postası gönderiliyor...", 3000)
        
        try:
            self.email_thread = EmailThread(smtp_settings, message_details)
            self.email_thread.task_finished.connect(lambda msg: QMessageBox.information(self, "Test Başarılı", msg))
            self.email_thread.task_error.connect(lambda err: QMessageBox.critical(self, "Test Hatası", err))
            self.email_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"E-posta gönderme işlemi başlatılamadı: {e}")