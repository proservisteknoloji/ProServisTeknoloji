# ui/dialogs/api_settings_dialog.py

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
                             QComboBox, QLabel, QMessageBox)
from PyQt6.QtCore import Qt
from utils.database import db_manager

class ApiSettingsDialog(QDialog):
    """Yapay zeka servis sağlayıcısı ve API anahtarı ayarlarını yönetmek için diyalog."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Yapay Zeka API Ayarları")
        self.setMinimumWidth(450)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Google Gemini"])
        # OpenAI'yı varsayılan yap (daha stabil)
        self.provider_combo.setCurrentText("OpenAI")

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setOpenExternalLinks(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        layout.addRow("Servis Sağlayıcı:", self.provider_combo)
        layout.addRow("API Anahtarı:", self.api_key_input)
        layout.addRow(self.info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)

        self._connect_signals(buttons)

    def _connect_signals(self, buttons: QDialogButtonBox):
        """Sinyalleri slotlara bağlar."""
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        self.provider_combo.currentIndexChanged.connect(self.provider_changed)

    def load_settings(self):
        """Veritabanından mevcut ayarları yükler."""
        try:
            provider = self.db.get_setting('ai_provider', 'OpenAI')
            self.provider_combo.setCurrentText(provider)
            self.provider_changed()
        except Exception as e:
            QMessageBox.critical(self, "Ayar Yükleme Hatası", f"API ayarları yüklenirken bir hata oluştu: {e}")

    def provider_changed(self):
        """Sağlayıcı değiştikçe doğru API anahtarını yükler ve bilgi metnini günceller."""
        try:
            provider = self.provider_combo.currentText()
            api_key = ''
            info_text = ''
            
            if provider == "OpenAI":
                api_key = self.db.get_setting('openai_api_key', '')
                info_text = "API anahtarınızı <a href='https://platform.openai.com/api-keys'>OpenAI Platform</a> sayfasından alabilirsiniz."
            elif provider == "Google Gemini":
                api_key = self.db.get_setting('gemini_api_key', '')
                info_text = "Ücretsiz API anahtarınızı <a href='https://aistudio.google.com/app/apikey'>Google AI Studio</a> sayfasından alabilirsiniz."
            
            self.api_key_input.setText(api_key)
            self.info_label.setText(info_text)
        except Exception as e:
            QMessageBox.critical(self, "Ayar Değiştirme Hatası", f"Sağlayıcı değiştirilirken bir hata oluştu: {e}")

    def save_and_accept(self):
        """Seçilen sağlayıcıyı ve girilen API anahtarını veritabanına kaydeder."""
        try:
            provider = self.provider_combo.currentText()
            api_key = self.api_key_input.text().strip()
            
            # API key validasyonu
            if not api_key:
                QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir API anahtarı girin.")
                return
            
            # Geçersiz karakterleri kontrol et
            if any(char in api_key for char in ['\n', '\r', '\t']):
                QMessageBox.warning(self, "Geçersiz API Key", "API anahtarında geçersiz karakterler var. Lütfen sadece API anahtarını kopyalayın.")
                return

            self.db.set_setting('ai_provider', provider)
            if provider == "OpenAI":
                self.db.set_setting('openai_api_key', api_key)
            elif provider == "Google Gemini":
                self.db.set_setting('gemini_api_key', api_key)
            
            QMessageBox.information(self, "Başarılı", "API ayarları başarıyla kaydedildi.\n\nNot: API anahtarınızın doğru olduğundan emin olun.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Kayıt Hatası", f"API ayarları kaydedilirken bir hata oluştu: {e}")