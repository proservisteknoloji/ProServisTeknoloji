# ui/dialogs/backup_settings_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QCheckBox, QSpinBox, QHBoxLayout, QGroupBox
from PyQt6.QtCore import QTimer
import os
import shutil
from datetime import datetime
from pathlib import Path

class BackupSettingsDialog(QDialog):
    def __init__(self, db=None, settings_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Otomatik Yedekleme Ayarları")
        self.db = db
        self.settings_manager = settings_manager
        self.backup_timer = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        # Otomatik yedekleme grubu
        auto_group = QGroupBox("Otomatik Yedekleme")
        auto_layout = QVBoxLayout()

        self.auto_backup_checkbox = QCheckBox("Otomatik yedeklemeyi etkinleştir")
        auto_layout.addWidget(self.auto_backup_checkbox)

        # Yedekleme aralığı
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Yedekleme aralığı (saat):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 24)
        self.interval_spin.setValue(6)
        interval_layout.addWidget(self.interval_spin)
        auto_layout.addLayout(interval_layout)

        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)

        # Manuel yedekleme grubu
        manual_group = QGroupBox("Manuel Yedekleme")
        manual_layout = QVBoxLayout()

        self.manual_backup_btn = QPushButton("Şimdi Yedek Al")
        self.manual_backup_btn.clicked.connect(self.create_manual_backup)
        manual_layout.addWidget(self.manual_backup_btn)

        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)

        # Durum bilgisi
        self.status_label = QLabel("Yedekleme aktif değil")
        layout.addWidget(self.status_label)

        # Butonlar
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("Kapat")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_settings(self):
        """Mevcut ayarları yükler"""
        try:
            if self.settings_manager:
                auto_backup = self.settings_manager.get_setting('auto_backup_enabled', False)
                interval = self.settings_manager.get_setting('backup_interval_hours', 6)

                self.auto_backup_checkbox.setChecked(auto_backup)
                self.interval_spin.setValue(interval)

                if auto_backup:
                    self.start_auto_backup()
                    self.status_label.setText(f"Otomatik yedekleme aktif - Her {interval} saatte bir")
                else:
                    self.status_label.setText("Otomatik yedekleme devre dışı")
        except Exception as e:
            self.status_label.setText(f"Ayarlar yüklenirken hata: {e}")

    def save_settings(self):
        """Ayarları kaydeder"""
        try:
            if self.settings_manager:
                auto_backup = self.auto_backup_checkbox.isChecked()
                interval = self.interval_spin.value()

                self.settings_manager.set_setting('auto_backup_enabled', auto_backup)
                self.settings_manager.set_setting('backup_interval_hours', interval)

                if auto_backup:
                    self.start_auto_backup()
                    self.status_label.setText(f"Otomatik yedekleme aktif - Her {interval} saatte bir")
                else:
                    self.stop_auto_backup()
                    self.status_label.setText("Otomatik yedekleme devre dışı")

                QMessageBox.information(self, "Başarılı", "Ayarlar kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Ayarlar kaydedilirken hata oluştu: {e}")

    def start_auto_backup(self):
        """Otomatik yedeklemeyi başlatır"""
        self.stop_auto_backup()  # Önceki timer'ı durdur

        interval_hours = self.interval_spin.value()
        interval_ms = interval_hours * 60 * 60 * 1000  # Saatleri milisaniyeye çevir

        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.create_auto_backup)
        self.backup_timer.start(interval_ms)

    def stop_auto_backup(self):
        """Otomatik yedeklemeyi durdurur"""
        if self.backup_timer:
            self.backup_timer.stop()
            self.backup_timer = None

    def create_auto_backup(self):
        """Otomatik yedekleme oluşturur"""
        try:
            self.create_backup_internal("auto")
        except Exception as e:
            print(f"Otomatik yedekleme hatası: {e}")

    def create_manual_backup(self):
        """Manuel yedekleme oluşturur"""
        try:
            self.create_backup_internal("manual")
            QMessageBox.information(self, "Başarılı", "Manuel yedekleme tamamlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Manuel yedekleme sırasında hata oluştu: {e}")

    def create_backup_internal(self, backup_type):
        """Yedekleme işlemini gerçekleştirir"""
        try:
            # Veritabanı yolunu al
            if hasattr(self.db, 'database_path'):
                db_path = self.db.database_path
            else:
                # Fallback: varsayılan yol
                app_data = Path(os.environ.get('APPDATA', '~')) / 'ProServis'
                db_path = str(app_data / 'teknik_servis_local.db')

            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {db_path}")

            # Yedekleme klasörü
            backup_dir = Path(db_path).parent / "backups"
            backup_dir.mkdir(exist_ok=True)

            # Yedekleme dosya adı
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{backup_type}_{timestamp}.db"
            backup_path = backup_dir / backup_name

            # Veritabanını kopyala
            shutil.copy2(db_path, backup_path)

            # Eski yedekleri temizle (son 10 yedeklemeyi tut)
            backup_files = sorted(backup_dir.glob("backup_*.db"), key=os.path.getmtime, reverse=True)
            if len(backup_files) > 10:
                for old_backup in backup_files[10:]:
                    old_backup.unlink()

            print(f"{backup_type.capitalize()} yedekleme oluşturuldu: {backup_path}")

        except Exception as e:
            print(f"Yedekleme hatası: {e}")
            raise

    def closeEvent(self, event):
        """Dialog kapatılırken otomatik yedeklemeyi durdur"""
        self.stop_auto_backup()
        super().closeEvent(event)
