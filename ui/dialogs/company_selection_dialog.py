#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProServis Company Selection Dialog
Google Drive'dan firma seçimi veya yeni firma oluşturma
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QLineEdit,
    QMessageBox, QProgressDialog, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from datetime import datetime
from pathlib import Path

from utils.drive_database_manager import DriveDatabaseManager


class DriveAuthWorker(QThread):
    """Drive kimlik doğrulama worker"""
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def __init__(self, drive_manager):
        super().__init__()
        self.drive_manager = drive_manager
    
    def run(self):
        try:
            success = self.drive_manager.authenticate()
            self.finished.emit(success)
        except Exception as e:
            self.error.emit(str(e))


class CompanyListWorker(QThread):
    """Firma listesi yükleme worker"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, drive_manager):
        super().__init__()
        self.drive_manager = drive_manager
    
    def run(self):
        try:
            companies = self.drive_manager.list_companies()
            self.finished.emit(companies)
        except Exception as e:
            self.error.emit(str(e))


class CompanySelectionDialog(QDialog):
    """
    Firma seçimi dialog'u
    
    Not: Kimlik doğrulaması main.py'de yapılmıştır.
    Bu dialog sadece firma listesi ve seçimi için kullanılır.
    
    İşlevler:
    - Mevcut firmaları listeleme
    - Yeni firma oluşturma
    - Firma seçimi
    """
    
    def __init__(self, drive_manager: DriveDatabaseManager, parent=None):
        super().__init__(parent)
        self.drive_manager = drive_manager
        self.selected_company = None
        self.selected_db_path = None
        
        self.setWindowTitle("🏢 ProServis - Firma Seçimi")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        self.init_ui()
        
        # Otomatik firma listesi yükle
        self.load_companies()
    
    def init_ui(self):
        """Arayüzü oluştur"""
        layout = QVBoxLayout(self)
        
        # Başlık
        title = QLabel("ProServis Firma Yönetimi")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2196F3;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel(f"Tüm verileriniz Google Drive'da güvenle saklanır")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Bağlantı durumu (basit)
        status_label = QLabel("✅ Google Drive bağlı")
        status_label.setStyleSheet("color: green; font-size: 11pt; font-weight: bold;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)
        
        # Firma listesi
        company_group = QGroupBox("🏢 Firmalar")
        company_layout = QVBoxLayout(company_group)
        
        self.company_list = QListWidget()
        self.company_list.itemDoubleClicked.connect(self.on_company_double_click)
        self.company_list.itemSelectionChanged.connect(self.on_selection_changed)
        company_layout.addWidget(self.company_list)
        
        # Yenile butonu
        refresh_btn = QPushButton("🔄 Listeyi Yenile")
        refresh_btn.clicked.connect(self.load_companies)
        company_layout.addWidget(refresh_btn)
        
        layout.addWidget(company_group)
        
        # Yeni firma
        new_company_group = QGroupBox("➕ Yeni Firma Oluştur")
        new_company_layout = QVBoxLayout(new_company_group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Firma Adı:"))
        self.new_company_input = QLineEdit()
        self.new_company_input.setPlaceholderText("Örn: Tekno Servis Ltd.")
        name_layout.addWidget(self.new_company_input)
        new_company_layout.addLayout(name_layout)
        
        create_btn = QPushButton("✨ Firma Oluştur")
        create_btn.clicked.connect(self.create_company)
        new_company_layout.addWidget(create_btn)
        
        layout.addWidget(new_company_group)
        
        # Seç/İptal butonları
        buttons_layout = QHBoxLayout()
        
        self.select_btn = QPushButton("✅ Seç ve Devam Et")
        self.select_btn.clicked.connect(self.select_company)
        self.select_btn.setEnabled(False)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        buttons_layout.addWidget(self.select_btn)
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
    
    def on_selection_changed(self):
        """Liste seçimi değiştiğinde"""
        current_item = self.company_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            self.select_btn.setEnabled(True)
        else:
            self.select_btn.setEnabled(False)
    
    def load_companies(self):
        """Firma listesini yükle"""
        progress = QProgressDialog("Firmalar yükleniyor...", "İptal", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        self.list_worker = CompanyListWorker(self.drive_manager)
        self.list_worker.finished.connect(lambda companies: self.on_companies_loaded(companies, progress))
        self.list_worker.error.connect(lambda err: self.on_list_error(err, progress))
        self.list_worker.start()
    
    def on_companies_loaded(self, companies, progress):
        """Firmalar yüklendi"""
        progress.close()
        
        self.company_list.clear()
        
        if not companies:
            item = QListWidgetItem("Henüz firma oluşturulmamış")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.company_list.addItem(item)
            return
        
        for company in companies:
            # Firma bilgisi
            name = company['name']
            size_mb = company['size'] / (1024 * 1024)
            modified = company.get('modified', '')
            
            if modified:
                try:
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                    modified_str = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    modified_str = modified
            else:
                modified_str = 'Bilinmiyor'
            
            # List item
            item = QListWidgetItem(
                f"🏢 {name}\n"
                f"   💾 {size_mb:.2f} MB | 🕒 {modified_str}"
            )
            item.setData(Qt.ItemDataRole.UserRole, company)
            self.company_list.addItem(item)
    
    def on_list_error(self, error, progress):
        """Liste yükleme hatası"""
        progress.close()
        QMessageBox.critical(
            self,
            "Hata",
            f"Firma listesi yüklenemedi:\n{error}"
        )
    
    def on_company_double_click(self, item):
        """Firmaya çift tıklandı"""
        company = item.data(Qt.ItemDataRole.UserRole)
        if company:
            self.select_btn.setEnabled(True)
    
    def create_company(self):
        """Yeni firma oluştur"""
        company_name = self.new_company_input.text().strip()
        
        if not company_name:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Lütfen firma adı girin!"
            )
            return
        
        # Onay
        reply = QMessageBox.question(
            self,
            "Yeni Firma",
            f"'{company_name}' adında yeni firma oluşturulacak.\n"
            f"Google Drive'da yeni veritabanı dosyası oluşturulacak.\n\n"
            f"Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        progress = QProgressDialog("Firma oluşturuluyor...", "İptal", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Firma oluştur
        file_id = self.drive_manager.create_company_database(company_name)
        
        progress.close()
        
        if file_id:
            QMessageBox.information(
                self,
                "Başarılı",
                f"'{company_name}' firması başarıyla oluşturuldu!"
            )
            self.new_company_input.clear()
            self.load_companies()
        else:
            QMessageBox.critical(
                self,
                "Hata",
                "Firma oluşturulamadı!"
            )
    
    def select_company(self):
        """Seçili firmayı aktif et"""
        current_item = self.company_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Lütfen bir firma seçin!"
            )
            return
        
        company = current_item.data(Qt.ItemDataRole.UserRole)
        
        if not company:
            return
        
        progress = QProgressDialog("Firma veritabanı indiriliyor...", "İptal", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Firma seç ve veritabanını indir
        db_path = self.drive_manager.select_company(company['name'])
        
        progress.close()
        
        if db_path:
            self.selected_company = company['name']
            self.selected_db_path = db_path
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Hata",
                "Firma veritabanı indirilemedi!"
            )


# Test
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys
    from pathlib import Path
    
    app = QApplication(sys.argv)
    
    # Mock drive manager
    data_dir = Path.cwd() / 'test_data'
    data_dir.mkdir(exist_ok=True)
    
    drive_manager = DriveDatabaseManager(data_dir)
    
    dialog = CompanySelectionDialog(drive_manager)
    
    if dialog.exec():
        print(f"Selected: {dialog.selected_company}")
        print(f"DB Path: {dialog.selected_db_path}")
    else:
        print("Cancelled")
    
    sys.exit(0)
