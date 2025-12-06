# ui/dialogs/activation_dialog.py (PyQt6'ya güncellendi)

# Değişiklik: PySide6 -> PyQt6
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QHBoxLayout)
from PyQt6.QtCore import Qt

from utils.settings_manager import load_app_config, save_app_config
from utils.validator import validate_key
from datetime import datetime, timedelta

class ActivationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProServis Aktivasyon")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.config = load_app_config()
        self.first_run_date = self.config.get('first_run_date')
        
        # UI Elemanları
        main_layout = QVBoxLayout(self)
        self.status_label = QLabel()
        # Değişiklik: Enum güncellendi
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        
        self.activate_btn = QPushButton("Aktive Et")
        self.trial_btn = QPushButton("30 Günlük Deneme Sürümünü Başlat")
        self.exit_btn = QPushButton("Çıkış")
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.trial_btn)
        button_layout.addWidget(self.activate_btn)
        
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(QLabel("Lisans Anahtarı:"))
        main_layout.addWidget(self.key_input)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.exit_btn)
        
        # Sinyaller
        self.activate_btn.clicked.connect(self.attempt_activation)
        self.trial_btn.clicked.connect(self.start_trial)
        self.exit_btn.clicked.connect(self.reject)
        
        self.update_ui_status()

    def update_ui_status(self):
        """Pencerenin durumunu deneme süresine göre günceller."""
        if self.first_run_date:
            self.trial_btn.setVisible(False) # Deneme zaten başlamışsa butonu gizle
            try:
                start_date = datetime.strptime(self.first_run_date, "%Y-%m-%d")
                days_passed = (datetime.now() - start_date).days
                remaining_days = 30 - days_passed
                
                if remaining_days >= 0:
                    # Bu durum normalde main.py'de yakalanır ama güvenlik için burada da var.
                    self.status_label.setText(f"Deneme sürümünüz devam ediyor. Kalan gün: {remaining_days}")
                else:
                    self.status_label.setText(f"<b>30 günlük deneme süreniz dolmuştur!</b><br>Lütfen devam etmek için programı aktive edin.")
            except ValueError:
                self.status_label.setText("<b>Konfigürasyon hatası!</b><br>Lütfen devam etmek için programı aktive edin.")

        else:
            # İlk çalıştırma
            self.status_label.setText("ProServis'e hoş geldiniz!<br>Devam etmek için programı aktive edin veya 30 günlük deneme sürümünü başlatın.")
            self.trial_btn.setVisible(True)

    def start_trial(self):
        # Değişiklik: Enum güncellendi
        reply = QMessageBox.question(self, "Onay", "30 günlük deneme sürümü başlatılacak. Emin misiniz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config['first_run_date'] = datetime.now().strftime("%Y-%m-%d")
            self.config['is_demo_mode'] = True  # Demo modu flag'i
            save_app_config(self.config)
            
            # Demo kaydını sistem bildirimine gönder
            try:
                from utils.system_notifier import notify_demo_user
                from utils.settings_manager import SettingsManager
                
                settings = SettingsManager()
                company_name = settings.get_setting('company_name', 'ProServis_Demo')
                
                # Arka planda bildirim gönder (hata olsa bile kullanıcı engellenmesin)
                import threading
                threading.Thread(
                    target=notify_demo_user,
                    args=(company_name,),
                    daemon=True
                ).start()
            except:
                pass  # Sessizce devam et
            
            QMessageBox.information(self, "Başarılı", "30 günlük deneme sürümü başlatıldı.")
            self.accept()

    def attempt_activation(self):
        key = self.key_input.text()
        if not key:
            QMessageBox.warning(self, "Hata", "Lütfen bir lisans anahtarı girin.")
            return
            
        if validate_key(key):
            self.config['is_activated'] = True
            self.config['is_demo_mode'] = False  # Demo modu kapat
            # Aktivasyon başarılı olunca deneme tarihi bilgisini silebiliriz
            if 'first_run_date' in self.config:
                del self.config['first_run_date']
            save_app_config(self.config)
            
            # Aktivasyonu sistem bildirimine gönder
            try:
                from utils.system_notifier import notify_activation
                from utils.settings_manager import SettingsManager
                
                settings = SettingsManager()
                company_name = settings.get_setting('company_name', 'ProServis')
                
                # Arka planda bildirim gönder
                import threading
                threading.Thread(
                    target=notify_activation,
                    args=(company_name, key),
                    daemon=True
                ).start()
            except:
                pass  # Sessizce devam et
            
            QMessageBox.information(self, "Başarı", "Program başarıyla aktive edildi!")
            self.accept()
        else:
            QMessageBox.critical(self, "Hata", "Geçersiz lisans anahtarı!")