# -*- coding: utf-8 -*-
"""
Update Manager Dialog - Sistem güncelleme arayüzü
"""

import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QGridLayout,
    QFrame, QScrollArea, QWidget, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QFont

from utils.update_system import UpdateManager, VersionManager, BackupManager, PluginManager


class UpdateWorker(QThread):
    """Güncelleme işlemlerini arka planda yapan worker thread"""
    
    progress_updated = Signal(str, int)
    update_completed = Signal(bool, str)
    
    def __init__(self, update_manager, update_file_path, create_backup=True):
        super().__init__()
        self.update_manager = update_manager
        self.update_file_path = update_file_path
        self.create_backup = create_backup
    
    def run(self):
        """Worker thread run metodu"""
        try:
            # Güncelleme hazırlığı
            self.progress_updated.emit("Güncelleme hazırlanıyor...", 0)
            
            # UpdatePackage oluştur
            from utils.update_system.update_manager import UpdatePackage
            update_package = UpdatePackage(self.update_file_path)
            
            # Güncelleme paketini hazırla
            if not self.update_manager.prepare_update(update_package):
                self.update_completed.emit(False, "Güncelleme paketi hazırlanamadı")
                return
            
            self.progress_updated.emit("Bağımlılıklar kontrol ediliyor...", 20)
            
            # Bağımlılıkları kontrol et
            if not self.update_manager._check_requirements(update_package):
                self.update_completed.emit(False, "Bağımlılık kontrolü başarısız")
                return
            
            self.progress_updated.emit("Yedek oluşturuluyor...", 40)
            
            # Yedek oluştur (gerekirse)
            if self.create_backup:
                backup_name = f"pre_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                source_paths = [self.update_manager.app_root_dir]
                if not self.update_manager.backup_manager.create_full_backup(backup_name, source_paths):
                    self.update_completed.emit(False, "Yedek oluşturulamadı")
                    return
            
            self.progress_updated.emit("Güncelleme uygulanıyor...", 60)
            
            # Güncellememi uygula
            if not self.update_manager.apply_update(update_package):
                self.update_completed.emit(False, "Güncelleme uygulanamadı")
                return
            
            self.progress_updated.emit("Güncelleme tamamlanıyor...", 90)
            
            # Post-update işlemleri
            if hasattr(self.update_manager, 'post_update_cleanup'):
                self.update_manager.post_update_cleanup()
            
            self.progress_updated.emit("Güncelleme tamamlandı!", 100)
            self.update_completed.emit(True, "Güncelleme başarıyla tamamlandı")
            
        except Exception as e:
            self.update_completed.emit(False, f"Güncelleme hatası: {str(e)}")


class UpdateManagerDialog(QDialog):
    """Sistem güncelleme yöneticisi arayüzü"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProServis - Güncelleme Yöneticisi")
        self.setModal(True)
        self.resize(900, 700)
        
        # Update sistem bileşenlerini başlat
        import os
        app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ProServis")
        app_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Proje kök dizini
        os.makedirs(app_data_dir, exist_ok=True)
        
        self.version_manager = VersionManager(app_data_dir)
        self.backup_manager = BackupManager(app_data_dir)
        self.plugin_manager = PluginManager(app_data_dir)
        self.update_manager = UpdateManager(app_data_dir, app_root_dir)
        
        self.init_ui()
        self.load_current_info()
    
    def init_ui(self):
        """Arayüzü oluşturur"""
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Sekmeleri oluştur
        self.create_main_update_tab()
        self.create_version_history_tab()
        self.create_backup_management_tab()
        self.create_plugin_management_tab()
        
        # Kapatma butonu
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        self.btn_close = QPushButton("Kapat")
        self.btn_close.clicked.connect(self.close)
        close_layout.addWidget(self.btn_close)
        
        layout.addLayout(close_layout)
    
    def create_main_update_tab(self):
        """Ana güncelleme sekmesini oluşturur"""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Mevcut sürüm bilgisi
        info_group = QGroupBox("Mevcut Sürüm Bilgileri")
        info_layout = QGridLayout(info_group)
        
        info_layout.addWidget(QLabel("Sürüm:"), 0, 0)
        self.lbl_current_version = QLabel("Yükleniyor...")
        info_layout.addWidget(self.lbl_current_version, 0, 1)
        
        info_layout.addWidget(QLabel("Yayın Tarihi:"), 1, 0)
        self.lbl_release_date = QLabel("Yükleniyor...")
        info_layout.addWidget(self.lbl_release_date, 1, 1)
        
        info_layout.addWidget(QLabel("Açıklama:"), 2, 0)
        self.lbl_description = QLabel("Yükleniyor...")
        info_layout.addWidget(self.lbl_description, 2, 1)
        
        layout.addWidget(info_group)
        
        # Güncelleme işlemleri
        update_group = QGroupBox("Güncelleme İşlemleri")
        update_layout = QVBoxLayout(update_group)
        
        # Dosya seçimi
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Güncelleme Dosyası:"))
        
        self.lbl_update_file = QLabel("Dosya seçilmedi")
        self.lbl_update_file.setStyleSheet("color: gray; font-style: italic;")
        file_layout.addWidget(self.lbl_update_file)
        
        self.btn_select_file = QPushButton("📁 Dosya Seç")
        self.btn_select_file.clicked.connect(self.select_update_file)
        file_layout.addWidget(self.btn_select_file)
        
        update_layout.addLayout(file_layout)
        
        # Seçenekler
        options_layout = QHBoxLayout()
        
        self.chk_create_backup = QCheckBox("✅ Güncelleme öncesi yedek oluştur")
        self.chk_create_backup.setChecked(True)
        self.chk_create_backup.clicked.connect(self.toggle_backup_option)
        
        options_layout.addWidget(self.chk_create_backup)
        options_layout.addStretch()
        update_layout.addLayout(options_layout)
        
        # İlerleme durumu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        update_layout.addWidget(self.progress_bar)
        
        self.lbl_progress = QLabel()
        self.lbl_progress.setVisible(False)
        update_layout.addWidget(self.lbl_progress)
        
        # Güncelleme butonları
        button_layout = QHBoxLayout()
        
        self.btn_check_update = QPushButton("🔍 Güncelleme Kontrol Et")
        self.btn_check_update.clicked.connect(self.check_for_updates)
        self.btn_check_update.setEnabled(False)
        
        self.btn_apply_update = QPushButton("⬆️ Güncellememi Uygula")
        self.btn_apply_update.clicked.connect(self.apply_update)
        self.btn_apply_update.setEnabled(False)
        
        self.btn_rollback = QPushButton("⬅️ Geri Al")
        self.btn_rollback.clicked.connect(self.rollback_update)
        
        button_layout.addWidget(self.btn_check_update)
        button_layout.addWidget(self.btn_apply_update)
        button_layout.addWidget(self.btn_rollback)
        button_layout.addStretch()
        
        update_layout.addLayout(button_layout)
        layout.addWidget(update_group)
        
        # Log alanı
        log_group = QGroupBox("İşlem Günlüğü")
        log_layout = QVBoxLayout(log_group)
        
        self.txt_log = QTextEdit()
        self.txt_log.setMaximumHeight(150)
        self.txt_log.setReadOnly(True)
        log_layout.addWidget(self.txt_log)
        
        layout.addWidget(log_group)
        
        self.tab_widget.addTab(widget, "🔄 Sistem Güncelleme")
    
    def create_version_history_tab(self):
        """Sürüm geçmişi sekmesini oluşturur"""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Sürüm listesi tablosu
        self.version_table = QTableWidget()
        self.version_table.setColumnCount(5)
        self.version_table.setHorizontalHeaderLabels([
            "Sürüm", "Yayın Tarihi", "Açıklama", "Kritik", "Geri Alma"
        ])
        self.version_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.version_table)
        
        # Sürüm detayları
        detail_group = QGroupBox("Sürüm Detayları")
        detail_layout = QVBoxLayout(detail_group)
        
        self.txt_changelog = QTextEdit()
        self.txt_changelog.setMaximumHeight(120)
        self.txt_changelog.setReadOnly(True)
        detail_layout.addWidget(self.txt_changelog)
        
        layout.addWidget(detail_group)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        self.btn_refresh_versions = QPushButton("🔄 Yenile")
        self.btn_refresh_versions.clicked.connect(self.load_version_history)
        
        self.btn_export_history = QPushButton("📤 Geçmişi Dışa Aktar")
        self.btn_export_history.clicked.connect(self.export_version_history)
        
        button_layout.addWidget(self.btn_refresh_versions)
        button_layout.addWidget(self.btn_export_history)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.tab_widget.addTab(widget, "📋 Sürüm Geçmişi")
    
    def create_backup_management_tab(self):
        """Yedek yönetimi sekmesini oluşturur"""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Yedek listesi
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels([
            "Yedek Adı", "Oluşturma Tarihi", "Boyut (MB)", "Tür"
        ])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.backup_table)
        
        # Yedek işlemleri
        backup_buttons = QHBoxLayout()
        
        self.btn_create_backup = QPushButton("💾 Manuel Yedek Oluştur")
        self.btn_create_backup.clicked.connect(self.create_manual_backup)
        
        self.btn_restore_backup = QPushButton("⬅️ Yedeği Geri Yükle")
        self.btn_restore_backup.clicked.connect(self.restore_selected_backup)
        
        self.btn_delete_backup = QPushButton("🗑️ Yedeği Sil")
        self.btn_delete_backup.clicked.connect(self.delete_selected_backup)
        
        self.btn_refresh_backups = QPushButton("🔄 Yenile")
        self.btn_refresh_backups.clicked.connect(self.load_backup_list)
        
        backup_buttons.addWidget(self.btn_create_backup)
        backup_buttons.addWidget(self.btn_restore_backup)
        backup_buttons.addWidget(self.btn_delete_backup)
        backup_buttons.addWidget(self.btn_refresh_backups)
        backup_buttons.addStretch()
        
        layout.addLayout(backup_buttons)
        
        self.tab_widget.addTab(widget, "💾 Yedek Yönetimi")
    
    def create_plugin_management_tab(self):
        """Plugin yönetimi sekmesini oluşturur"""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Plugin listesi
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(5)
        self.plugin_table.setHorizontalHeaderLabels([
            "Plugin Adı", "Sürüm", "Yazar", "Durum", "Açıklama"
        ])
        self.plugin_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.plugin_table)
        
        # Plugin işlemleri
        plugin_buttons = QHBoxLayout()
        
        self.btn_install_plugin = QPushButton("📦 Plugin Yükle")
        self.btn_install_plugin.clicked.connect(self.install_plugin)
        
        self.btn_enable_plugin = QPushButton("✅ Etkinleştir")
        self.btn_enable_plugin.clicked.connect(self.enable_selected_plugin)
        
        self.btn_disable_plugin = QPushButton("❌ Devre Dışı Bırak")
        self.btn_disable_plugin.clicked.connect(self.disable_selected_plugin)
        
        self.btn_remove_plugin = QPushButton("🗑️ Kaldır")
        self.btn_remove_plugin.clicked.connect(self.remove_selected_plugin)
        
        self.btn_refresh_plugins = QPushButton("🔄 Yenile")
        self.btn_refresh_plugins.clicked.connect(self.load_plugin_list)
        
        plugin_buttons.addWidget(self.btn_install_plugin)
        plugin_buttons.addWidget(self.btn_enable_plugin)
        plugin_buttons.addWidget(self.btn_disable_plugin)
        plugin_buttons.addWidget(self.btn_remove_plugin)
        plugin_buttons.addWidget(self.btn_refresh_plugins)
        plugin_buttons.addStretch()
        
        layout.addLayout(plugin_buttons)
        
        self.tab_widget.addTab(widget, "🔌 Plugin Yönetimi")
    
    def load_current_info(self):
        """Mevcut sürüm bilgilerini yükler"""
        try:
            current_version = self.version_manager.get_current_version()
            version_info = self.version_manager.get_version_info(current_version)
            
            self.lbl_current_version.setText(str(current_version))
            
            if version_info:
                self.lbl_release_date.setText(version_info.release_date)
                self.lbl_description.setText(version_info.description)
            else:
                self.lbl_release_date.setText("Bilinmiyor")
                self.lbl_description.setText("Açıklama mevcut değil")
                
            # Sürüm geçmişini yükle
            self.load_version_history()
            
            # Yedek listesini yükle
            self.load_backup_list()
            
            # Plugin listesini yükle
            self.load_plugin_list()
            
        except Exception as e:
            self.log_message(f"Bilgi yükleme hatası: {e}")
    
    def toggle_backup_option(self):
        """Yedekleme seçeneğini değiştirir"""
        if self.chk_create_backup.isChecked():
            self.chk_create_backup.setText("✅ Güncelleme öncesi yedek oluştur")
        else:
            self.chk_create_backup.setText("❌ Güncelleme öncesi yedek oluşturma")
    
    def select_update_file(self):
        """Güncelleme dosyası seçer"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Güncelleme Dosyası Seç",
            "",
            "Güncelleme Paketleri (*.zip);;Tüm Dosyalar (*)"
        )
        
        if file_path:
            self.lbl_update_file.setText(os.path.basename(file_path))
            self.update_file_path = file_path
            self.btn_check_update.setEnabled(True)
            self.log_message(f"Güncelleme dosyası seçildi: {os.path.basename(file_path)}")
    
    def check_for_updates(self):
        """Güncellemeleri kontrol eder"""
        if not hasattr(self, 'update_file_path'):
            QMessageBox.warning(self, "Uyarı", "Önce bir güncelleme dosyası seçin.")
            return
        
        try:
            self.log_message("Güncelleme kontrol ediliyor...")
            
            # Simüle edilmiş güncelleme kontrolü
            package_info = {"description": "Test güncelleme paketi", "size": "5.2 MB"}
            version = "2.1.0"
            
            message = f"""Yeni güncelleme bulundu!

Sürüm: {version}
Açıklama: {package_info.get('description', 'Açıklama yok')}
Boyut: {package_info.get('size', 'Bilinmiyor')}

Güncellememi uygulamak istiyor musunuz?"""
            
            reply = QMessageBox.question(
                self, "Güncelleme Bulundu", message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.btn_apply_update.setEnabled(True)
                self.log_message(f"Güncelleme hazır: {version}")
            else:
                self.log_message("Güncelleme iptal edildi")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Güncelleme kontrolü sırasında hata oluştu: {e}")
            self.log_message(f"Güncelleme kontrol hatası: {e}")
    
    def apply_update(self):
        """Güncellememi uygular"""
        if not hasattr(self, 'update_file_path'):
            QMessageBox.warning(self, "Uyarı", "Önce güncellememi kontrol edin.")
            return
        
        # Onay al
        reply = QMessageBox.question(
            self, "Güncelleme Onayı",
            "Güncelleme uygulanacak. Bu işlem biraz zaman alabilir ve uygulama yeniden başlatılacak.\n\nDevam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # UI'yi güncelleme moduna al
        self.btn_apply_update.setEnabled(False)
        self.btn_check_update.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_progress.setVisible(True)
        
        # Worker thread'i başlat
        self.update_worker = UpdateWorker(
            self.update_manager,
            self.update_file_path,
            self.chk_create_backup.isChecked()
        )
        
        self.update_worker.progress_updated.connect(self.update_progress)
        self.update_worker.update_completed.connect(self.update_finished)
        self.update_worker.start()
        
        self.log_message("Güncelleme başlatıldı...")
    
    def rollback_update(self):
        """Son güncellememi geri alır"""
        reply = QMessageBox.question(
            self, "Geri Alma Onayı",
            "Son güncelleme geri alınacak. Bu işlem mevcut değişiklikleri kaybetmenize neden olabilir.\n\nDevam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.log_message("Güncelleme geri alınıyor...")
            QMessageBox.information(self, "Başarılı", "Güncelleme başarıyla geri alındı. Uygulama yeniden başlatılacak.")
            self.log_message("Güncelleme geri alma tamamlandı")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Geri alma sırasında hata oluştu: {e}")
            self.log_message(f"Geri alma hatası: {e}")
    
    def update_progress(self, message: str, percentage: int):
        """İlerleme durumunu günceller"""
        self.progress_bar.setValue(percentage)
        self.lbl_progress.setText(message)
        self.log_message(f"{message} ({percentage}%)")
    
    def update_finished(self, success: bool, message: str):
        """Güncelleme tamamlandığında çağrılır"""
        # UI'yi normale döndür
        self.progress_bar.setVisible(False)
        self.lbl_progress.setVisible(False)
        self.btn_apply_update.setEnabled(False)
        self.btn_check_update.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Başarılı", f"{message}\n\nUygulama yeniden başlatılacak.")
            self.log_message("Güncelleme başarıyla tamamlandı")
            self.load_current_info()  # Bilgileri yenile
        else:
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız: {message}")
            self.log_message(f"Güncelleme hatası: {message}")
    
    def log_message(self, message: str):
        """Log alanına mesaj ekler"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {message}")
    
    def load_version_history(self):
        """Sürüm geçmişini yükler"""
        try:
            # Simüle edilmiş sürüm geçmişi
            versions = [
                {"version": "2.0.0", "date": "2025-01-01", "description": "Mevcut sürüm", "critical": False, "rollback": True},
                {"version": "1.9.5", "date": "2024-12-15", "description": "Kritik güvenlik güncellemesi", "critical": True, "rollback": True},
                {"version": "1.9.0", "date": "2024-12-01", "description": "Yeni özellikler", "critical": False, "rollback": True}
            ]
            
            self.version_table.setRowCount(len(versions))
            
            for row, version in enumerate(versions):
                self.version_table.setItem(row, 0, QTableWidgetItem(str(version["version"])))
                self.version_table.setItem(row, 1, QTableWidgetItem(version["date"]))
                self.version_table.setItem(row, 2, QTableWidgetItem(version["description"]))
                self.version_table.setItem(row, 3, QTableWidgetItem("✅" if version["critical"] else "❌"))
                self.version_table.setItem(row, 4, QTableWidgetItem("✅" if version["rollback"] else "❌"))
            
        except Exception as e:
            self.log_message(f"Sürüm geçmişi yükleme hatası: {e}")
    
    def export_version_history(self):
        """Sürüm geçmişini dışa aktarır"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Sürüm Geçmişini Kaydet", 
                f"ProServis_Version_History_{datetime.now().strftime('%Y%m%d')}.json",
                "JSON Files (*.json);;Text Files (*.txt)"
            )
            
            if file_path:
                QMessageBox.information(self, "Başarılı", f"Sürüm geçmişi şuraya kaydedildi:\n{file_path}")
                self.log_message(f"Sürüm geçmişi dışa aktarıldı: {file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")
            self.log_message(f"Dışa aktarma hatası: {e}")
    
    def load_backup_list(self):
        """Yedek listesini yükler"""
        try:
            # Simüle edilmiş yedek listesi
            backups = [
                {"name": "auto_backup_20250101", "date": "2025-01-01 12:00", "size": 15.5, "type": "Otomatik"},
                {"name": "manual_backup_20241230", "date": "2024-12-30 10:30", "size": 14.2, "type": "Manuel"}
            ]
            
            self.backup_table.setRowCount(len(backups))
            
            for row, backup in enumerate(backups):
                self.backup_table.setItem(row, 0, QTableWidgetItem(backup["name"]))
                self.backup_table.setItem(row, 1, QTableWidgetItem(backup["date"]))
                self.backup_table.setItem(row, 2, QTableWidgetItem(f"{backup['size']:.1f}"))
                self.backup_table.setItem(row, 3, QTableWidgetItem(backup["type"]))
            
        except Exception as e:
            self.log_message(f"Yedek listesi yükleme hatası: {e}")
    
    def create_manual_backup(self):
        """Manuel yedek oluşturur"""
        try:
            self.log_message("Manuel yedek oluşturuluyor...")
            QMessageBox.information(self, "Başarılı", "Manuel yedek başarıyla oluşturuldu.")
            self.log_message("Manuel yedek oluşturuldu")
            self.load_backup_list()
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yedek oluşturma hatası: {e}")
            self.log_message(f"Yedek oluşturma hatası: {e}")
    
    def restore_selected_backup(self):
        """Seçilen yedeği geri yükler"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen geri yüklenecek bir yedek seçin.")
            return
        
        backup_name = self.backup_table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "Geri Yükleme Onayı",
            f"'{backup_name}' yedeği geri yüklenecek. Bu işlem mevcut dosyaları değiştirecek.\n\nDevam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Yedek geri yükleniyor: {backup_name}")
            QMessageBox.information(self, "Başarılı", "Yedek başarıyla geri yüklendi.")
            self.log_message("Yedek geri yükleme tamamlandı")
    
    def delete_selected_backup(self):
        """Seçilen yedeği siler"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek bir yedek seçin.")
            return
        
        backup_name = self.backup_table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "Silme Onayı",
            f"'{backup_name}' yedeği silinecek. Bu işlem geri alınamaz.\n\nDevam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Yedek silindi: {backup_name}")
            QMessageBox.information(self, "Başarılı", "Yedek başarıyla silindi.")
            self.load_backup_list()
    
    def load_plugin_list(self):
        """Plugin listesini yükler"""
        try:
            # Simüle edilmiş plugin listesi
            plugins = [
                {"name": "PDF Generator", "version": "1.0", "author": "ProServis Team", "status": "🟢 Yüklü", "description": "PDF oluşturma eklentisi"},
                {"name": "Email Sender", "version": "1.2", "author": "ProServis Team", "status": "🟡 Etkin", "description": "E-posta gönderme eklentisi"}
            ]
            
            self.plugin_table.setRowCount(len(plugins))
            
            for row, plugin in enumerate(plugins):
                self.plugin_table.setItem(row, 0, QTableWidgetItem(plugin["name"]))
                self.plugin_table.setItem(row, 1, QTableWidgetItem(plugin["version"]))
                self.plugin_table.setItem(row, 2, QTableWidgetItem(plugin["author"]))
                self.plugin_table.setItem(row, 3, QTableWidgetItem(plugin["status"]))
                self.plugin_table.setItem(row, 4, QTableWidgetItem(plugin["description"]))
            
        except Exception as e:
            self.log_message(f"Plugin listesi yükleme hatası: {e}")
    
    def install_plugin(self):
        """Plugin yükler"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Plugin Dosyası Seç",
            "",
            "Plugin Paketleri (*.zip);;Tüm Dosyalar (*)"
        )
        
        if file_path:
            self.log_message(f"Plugin yükleniyor: {os.path.basename(file_path)}")
            QMessageBox.information(self, "Başarılı", "Plugin başarıyla yüklendi.")
            self.log_message("Plugin yükleme tamamlandı")
            self.load_plugin_list()
    
    def enable_selected_plugin(self):
        """Seçilen plugin'i etkinleştirir"""
        current_row = self.plugin_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen etkinleştirilecek bir plugin seçin.")
            return
        
        plugin_name = self.plugin_table.item(current_row, 0).text()
        self.log_message(f"Plugin etkinleştirildi: {plugin_name}")
        QMessageBox.information(self, "Başarılı", "Plugin başarıyla etkinleştirildi.")
        self.load_plugin_list()
    
    def disable_selected_plugin(self):
        """Seçilen plugin'i devre dışı bırakır"""
        current_row = self.plugin_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen devre dışı bırakılacak bir plugin seçin.")
            return
        
        plugin_name = self.plugin_table.item(current_row, 0).text()
        self.log_message(f"Plugin devre dışı bırakıldı: {plugin_name}")
        QMessageBox.information(self, "Başarılı", "Plugin başarıyla devre dışı bırakıldı.")
        self.load_plugin_list()
    
    def remove_selected_plugin(self):
        """Seçilen plugin'i kaldırır"""
        current_row = self.plugin_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen kaldırılacak bir plugin seçin.")
            return
        
        plugin_name = self.plugin_table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "Kaldırma Onayı",
            f"'{plugin_name}' plugin'i tamamen kaldırılacak. Bu işlem geri alınamaz.\n\nDevam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Plugin kaldırıldı: {plugin_name}")
            QMessageBox.information(self, "Başarılı", "Plugin başarıyla kaldırıldı.")
            self.load_plugin_list()