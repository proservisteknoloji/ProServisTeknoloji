# ui/dialogs/network_path_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QFileDialog, QMessageBox,
                             QDialogButtonBox)
from utils.settings_manager import load_app_config, save_app_config

class NetworkPathDialog(QDialog):
    """Yerel SQLite veritabanı dosyasının ağ yolunu ayarlamak için kullanılan diyalog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yerel Veritabanı Konumunu Ayarla")
        self.setMinimumWidth(500)
        
        self._init_ui()
        self._load_current_path()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        self._create_widgets()
        self._create_layout(main_layout)
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.info_label = QLabel(
            "Bu ayar, 'Yerel Mod' (SQLite) çalışırken veritabanı dosyasının (.db) nerede saklanacağını belirtir.\n"
            "Ağdaki paylaşılan bir klasörü seçerek verilerinize farklı bilgisayarlardan erişebilirsiniz."
        )
        self.info_label.setWordWrap(True)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(r"Örn: \\SUNUCU\Paylasim\teknik_servis.db")
        self.browse_btn = QPushButton("Gözat...")
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)

    def _create_layout(self, main_layout: QVBoxLayout):
        """Widget'ları layout'a yerleştirir."""
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)

        main_layout.addWidget(self.info_label)
        main_layout.addLayout(path_layout)
        main_layout.addWidget(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.browse_btn.clicked.connect(self._browse_path)
        self.buttons.accepted.connect(self._save_and_accept)
        self.buttons.rejected.connect(self.reject)
        
    def _load_current_path(self):
        """Mevcut yapılandırmadan veritabanı yolunu yükler."""
        try:
            config = load_app_config()
            current_path = config.get('sqlite_network_path', '')
            self.path_input.setText(current_path)
        except Exception as e:
            QMessageBox.critical(self, "Yapılandırma Hatası", f"Ayarlar yüklenirken bir hata oluştu: {e}")

    def _browse_path(self):
        """Veritabanı dosyasını seçmek için bir dosya diyalogu açar."""
        current_path = self.path_input.text() or "teknik_servis_local.db"
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Veritabanı Dosyasını Kaydet", 
            current_path, 
            "SQLite Veritabanı (*.db)"
        )
        if file_path:
            self.path_input.setText(file_path.replace('/', '\\'))

    def _save_and_accept(self):
        """Yeni veritabanı yolunu yapılandırma dosyasına kaydeder."""
        try:
            new_path = self.path_input.text().strip()
            config = load_app_config()
            
            if not new_path:
                if 'sqlite_network_path' in config:
                    del config['sqlite_network_path']
            else:
                config['sqlite_network_path'] = new_path
            
            save_app_config(config)
            QMessageBox.information(
                self, 
                "Ayarlar Kaydedildi", 
                "Veritabanı konumu ayarlandı.\nDeğişikliklerin etkili olması için lütfen uygulamayı yeniden başlatın."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Kayıt Hatası", f"Ayarlar kaydedilirken bir hata oluştu: {e}")