# ui/dialogs/stock_settings_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QComboBox, QPushButton, QTextEdit, 
                             QMessageBox, QProgressBar, QGroupBox, QFrame,
                             QTabWidget, QFileDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
import pandas as pd
from pathlib import Path
import os
from datetime import datetime

class StockExportWorker(QThread):
    """Stok dışa aktarma işlemini arka planda gerçekleştiren worker."""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(int)
    
    def __init__(self, db, report_type, export_format):
        super().__init__()
        self.db = db
        self.report_type = report_type
        self.export_format = export_format
        
    def run(self):
        try:
            self.progress.emit(10)
            
            # Veri çekme
            if self.report_type == "Tüm Stok":
                query = """
                SELECT 
                    item_type as 'Tip',
                    name as 'İsim/Model',
                    part_number as 'Parça No',
                    quantity as 'Miktar',
                    purchase_price as 'Alış Fiyatı',
                    purchase_currency as 'Alış Para Birimi',
                    sale_price as 'Satış Fiyatı',
                    sale_currency as 'Satış Para Birimi',
                    supplier as 'Tedarikçi',
                    location as 'Konum',
                    min_stock_level as 'Min Stok Seviyesi'
                FROM stock_items 
                ORDER BY item_type, name
                """
            else:
                query = """
                SELECT 
                    name as 'İsim/Model',
                    part_number as 'Parça No',
                    quantity as 'Miktar',
                    purchase_price as 'Alış Fiyatı',
                    purchase_currency as 'Alış Para Birimi',
                    sale_price as 'Satış Fiyatı',
                    sale_currency as 'Satış Para Birimi',
                    supplier as 'Tedarikçi',
                    location as 'Konum',
                    min_stock_level as 'Min Stok Seviyesi'
                FROM stock_items 
                WHERE item_type = ?
                ORDER BY name
                """
            
            self.progress.emit(30)
            
            if self.report_type == "Tüm Stok":
                data = self.db.fetch_all(query)
            else:
                data = self.db.fetch_all(query, (self.report_type,))
            
            if not data:
                self.finished.emit(False, "Dışa aktarılacak veri bulunamadı.")
                return
                
            self.progress.emit(50)
            
            # DataFrame oluştur
            if self.report_type == "Tüm Stok":
                columns = ['Tip', 'İsim/Model', 'Parça No', 'Miktar', 'Alış Fiyatı', 
                          'Alış Para Birimi', 'Satış Fiyatı', 'Satış Para Birimi', 
                          'Tedarikçi', 'Konum', 'Min Stok Seviyesi']
            else:
                columns = ['İsim/Model', 'Parça No', 'Miktar', 'Alış Fiyatı', 
                          'Alış Para Birimi', 'Satış Fiyatı', 'Satış Para Birimi', 
                          'Tedarikçi', 'Konum', 'Min Stok Seviyesi']
            
            df = pd.DataFrame(data, columns=columns)
            
            self.progress.emit(70)
            
            # Dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Stok_Verileri_{self.report_type.replace(' ', '_')}_{timestamp}"
            
            # Desktop yolu
            desktop_path = Path.home() / "Desktop"
            
            if self.export_format == "Excel":
                file_path = desktop_path / f"{filename}.xlsx"
                df.to_excel(file_path, index=False, engine='openpyxl')
            else:  # CSV
                file_path = desktop_path / f"{filename}.csv"
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            self.progress.emit(100)
            self.finished.emit(True, f"Veriler başarıyla dışa aktarıldı:\n{file_path}")
            
        except Exception as e:
            self.finished.emit(False, f"Dışa aktarma sırasında hata oluştu: {str(e)}")


class StockImportWorker(QThread):
    """Stok içe aktarma işlemini arka planda gerçekleştiren worker."""
    finished = pyqtSignal(bool, str, dict)  # success, message, stats
    progress = pyqtSignal(int)
    
    def __init__(self, db, file_path, update_existing):
        super().__init__()
        self.db = db
        self.file_path = file_path
        self.update_existing = update_existing
    
    def _parse_price(self, value):
        """Fiyat değerini parse eder - hem sayı hem string formatını destekler."""
        if pd.isna(value) or value is None:
            return 0.0
        
        # Zaten sayı ise direkt döndür
        if isinstance(value, (int, float)):
            return float(value)
        
        # String ise parse et
        value_str = str(value).strip()
        if not value_str or value_str.lower() in ['nan', 'none', '']:
            return 0.0
        
        try:
            # Virgülü noktaya çevir (Türkçe sayı formatı için)
            value_str = value_str.replace(',', '.')
            
            # Sadece sayıları ve noktayı tut
            import re
            number_str = re.sub(r'[^\d.]', '', value_str)
            
            if number_str:
                return float(number_str)
            else:
                return 0.0
        except:
            return 0.0
        
    def run(self):
        try:
            self.progress.emit(10)
            
            # Dosya uzantısına göre oku
            file_ext = Path(self.file_path).suffix.lower()
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(self.file_path)
            elif file_ext == '.csv':
                df = pd.read_csv(self.file_path, encoding='utf-8-sig')
            else:
                self.finished.emit(False, "Desteklenmeyen dosya formatı. Sadece Excel (.xlsx, .xls) veya CSV (.csv) dosyaları desteklenir.", {})
                return
            
            self.progress.emit(30)
            
            # Gerekli sütunları kontrol et
            required_columns = ['İsim/Model', 'Miktar']
            optional_columns = ['Tip', 'Parça No', 'Alış Fiyatı', 'Alış Para Birimi', 
                              'Satış Fiyatı', 'Satış Para Birimi', 'Tedarikçi', 
                              'Konum', 'Min Stok Seviyesi']
            
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                self.finished.emit(False, f"Gerekli sütunlar eksik: {', '.join(missing_required)}", {})
                return
            
            self.progress.emit(50)
            
            # İstatistikler
            stats = {
                'total': len(df),
                'inserted': 0,
                'updated': 0,
                'skipped': 0,
                'errors': []
            }
            
            # Her satırı işle
            row_counter = 0
            for idx, row in df.iterrows():
                row_counter += 1
                try:
                    # Gerekli alanlar
                    name = str(row['İsim/Model']).strip()
                    quantity = int(float(row['Miktar'])) if pd.notna(row['Miktar']) else 0
                    
                    if not name or name == 'nan':
                        stats['skipped'] += 1
                        stats['errors'].append(f"Satır {row_counter+1}: İsim boş")
                        continue
                    
                    # Opsiyonel alanlar
                    item_type = str(row.get('Tip', 'Diğer')).strip() if 'Tip' in df.columns and pd.notna(row.get('Tip')) else 'Diğer'
                    part_number = str(row.get('Parça No', '')).strip() if 'Parça No' in df.columns and pd.notna(row.get('Parça No')) else ''
                    
                    # Fiyat alanlarını parse et - hem sayı hem string formatını destekle
                    purchase_price = self._parse_price(row.get('Alış Fiyatı', 0)) if 'Alış Fiyatı' in df.columns else 0.0
                    purchase_currency = str(row.get('Alış Para Birimi', 'TL')).strip() if 'Alış Para Birimi' in df.columns and pd.notna(row.get('Alış Para Birimi')) else 'TL'
                    sale_price = self._parse_price(row.get('Satış Fiyatı', 0)) if 'Satış Fiyatı' in df.columns else 0.0
                    sale_currency = str(row.get('Satış Para Birimi', 'TL')).strip() if 'Satış Para Birimi' in df.columns and pd.notna(row.get('Satış Para Birimi')) else 'TL'
                    
                    supplier = str(row.get('Tedarikçi', '')).strip() if 'Tedarikçi' in df.columns and pd.notna(row.get('Tedarikçi')) else ''
                    location = str(row.get('Konum', '')).strip() if 'Konum' in df.columns and pd.notna(row.get('Konum')) else ''
                    min_stock = int(float(row.get('Min Stok Seviyesi', 0))) if 'Min Stok Seviyesi' in df.columns and pd.notna(row.get('Min Stok Seviyesi')) else 0
                    
                    # Mevcut kaydı kontrol et
                    check_query = "SELECT id FROM stock_items WHERE name = ?"
                    existing = self.db.fetch_one(check_query, (name,))
                    
                    if existing:
                        if self.update_existing:
                            # Güncelle
                            update_query = """
                            UPDATE stock_items 
                            SET item_type = ?, part_number = ?, quantity = ?, 
                                purchase_price = ?, purchase_currency = ?,
                                sale_price = ?, sale_currency = ?,
                                supplier = ?, location = ?, min_stock_level = ?
                            WHERE name = ?
                            """
                            self.db.execute_query(update_query, (
                                item_type, part_number, quantity,
                                purchase_price, purchase_currency,
                                sale_price, sale_currency,
                                supplier, location, min_stock,
                                name
                            ))
                            stats['updated'] += 1
                        else:
                            stats['skipped'] += 1
                            stats['errors'].append(f"Satır {row_counter+1}: '{name}' zaten mevcut (güncelleme yapılmadı)")
                    else:
                        # Yeni ekle
                        insert_query = """
                        INSERT INTO stock_items (
                            item_type, name, part_number, quantity,
                            purchase_price, purchase_currency,
                            sale_price, sale_currency,
                            supplier, location, min_stock_level
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        self.db.execute_query(insert_query, (
                            item_type, name, part_number, quantity,
                            purchase_price, purchase_currency,
                            sale_price, sale_currency,
                            supplier, location, min_stock
                        ))
                        stats['inserted'] += 1
                    
                except Exception as e:
                    stats['skipped'] += 1
                    stats['errors'].append(f"Satır {row_counter+1}: {str(e)}")
                
                # İlerleme güncelle
                progress = 50 + int(row_counter / len(df) * 50)
                self.progress.emit(progress)
            
            self.progress.emit(100)
            
            # Sonuç mesajı
            success_msg = f"İçe aktarma tamamlandı!\n\n"
            success_msg += f"Toplam: {stats['total']}\n"
            success_msg += f"Eklenen: {stats['inserted']}\n"
            success_msg += f"Güncellenen: {stats['updated']}\n"
            success_msg += f"Atlanan: {stats['skipped']}\n"
            
            if stats['errors'] and len(stats['errors']) <= 10:
                success_msg += f"\nHatalar:\n" + "\n".join(stats['errors'][:10])
            elif stats['errors']:
                success_msg += f"\n{len(stats['errors'])} hata oluştu (ilk 10 gösteriliyor):\n"
                success_msg += "\n".join(stats['errors'][:10])
            
            self.finished.emit(True, success_msg, stats)
            
        except Exception as e:
            self.finished.emit(False, f"İçe aktarma sırasında hata oluştu: {str(e)}", {})


class StockSettingsDialog(QDialog):
    """Stok ayarları diyalogu - İçe ve dışa aktarma."""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.export_worker = None
        self.import_worker = None
        self.setWindowTitle("Stok Ayarları")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tab widget
        tabs = QTabWidget()
        
        # Dışa aktarma sekmesi
        export_tab = self.create_export_tab()
        tabs.addTab(export_tab, "📤 Dışa Aktarma")
        
        # İçe aktarma sekmesi
        import_tab = self.create_import_tab()
        tabs.addTab(import_tab, "📥 İçe Aktarma")
        
        layout.addWidget(tabs)
        
        # Kapat butonu
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("Kapat")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def create_export_tab(self):
        """Dışa aktarma sekmesini oluşturur."""
        widget = QFrame()
        layout = QVBoxLayout()
        
        # Açıklama
        info_label = QLabel("Stok verilerinizi Excel veya CSV formatında dışa aktarabilirsiniz.")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        layout.addSpacing(20)
        
        # Ayarlar grubu
        settings_group = QGroupBox("Dışa Aktarma Ayarları")
        settings_layout = QGridLayout()
        
        # Rapor tipi
        settings_layout.addWidget(QLabel("Rapor Tipi:"), 0, 0)
        self.export_type_combo = QComboBox()
        self.export_type_combo.addItems(["Tüm Stok", "Toner", "Drum", "Yedek Parça", "Cihaz", "Diğer"])
        settings_layout.addWidget(self.export_type_combo, 0, 1)
        
        # Format
        settings_layout.addWidget(QLabel("Format:"), 1, 0)
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["Excel", "CSV"])
        settings_layout.addWidget(self.export_format_combo, 1, 1)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addSpacing(20)
        
        # Dışa aktar butonu
        export_btn = QPushButton("📤 Dışa Aktar")
        export_btn.setMinimumHeight(40)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        export_btn.clicked.connect(self.start_export)
        layout.addWidget(export_btn)
        
        # Progress bar
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        layout.addWidget(self.export_progress)
        
        # Log
        self.export_log = QTextEdit()
        self.export_log.setReadOnly(True)
        self.export_log.setMaximumHeight(150)
        layout.addWidget(self.export_log)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_import_tab(self):
        """İçe aktarma sekmesini oluşturur."""
        widget = QFrame()
        layout = QVBoxLayout()
        
        # Açıklama
        info_label = QLabel("Excel veya CSV dosyasından stok verilerini toplu olarak içe aktarabilirsiniz.")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Şablon indirme
        template_layout = QHBoxLayout()
        template_label = QLabel("💡 İpucu: Doğru formatta dosya hazırlamak için önce mevcut stok verilerinizi dışa aktarıp şablon olarak kullanabilirsiniz.")
        template_label.setWordWrap(True)
        template_label.setStyleSheet("color: #FF9800; background-color: #FFF3E0; padding: 10px; border-radius: 5px;")
        template_layout.addWidget(template_label)
        layout.addLayout(template_layout)
        
        layout.addSpacing(20)
        
        # Dosya seçimi
        file_group = QGroupBox("Dosya Seçimi")
        file_layout = QVBoxLayout()
        
        file_select_layout = QHBoxLayout()
        self.import_file_label = QLabel("Dosya seçilmedi")
        self.import_file_label.setStyleSheet("color: #666; font-style: italic;")
        file_select_layout.addWidget(self.import_file_label)
        
        browse_btn = QPushButton("📁 Dosya Seç")
        browse_btn.clicked.connect(self.select_import_file)
        file_select_layout.addWidget(browse_btn)
        
        file_layout.addLayout(file_select_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Ayarlar
        options_group = QGroupBox("İçe Aktarma Ayarları")
        options_layout = QVBoxLayout()
        
        self.update_existing_check = QCheckBox("  Mevcut kayıtları güncelle")
        self.update_existing_check.setChecked(True)
        self.update_existing_check.setToolTip("İşaretli ise aynı isme sahip kayıtlar güncellenir, değilse atlanır.")
        self.update_existing_check.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                spacing: 12px;
                color: #333;
            }
            QCheckBox::indicator {
                width: 28px;
                height: 28px;
                border: 3px solid #2196F3;
                border-radius: 5px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border: 3px solid #1976D2;
                background-color: #E3F2FD;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border: 3px solid #1565C0;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1976D2;
                border: 3px solid #0D47A1;
            }
        """)
        options_layout.addWidget(self.update_existing_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addSpacing(20)
        
        # İçe aktar butonu
        import_btn = QPushButton("📥 İçe Aktar")
        import_btn.setMinimumHeight(40)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        import_btn.clicked.connect(self.start_import)
        layout.addWidget(import_btn)
        
        # Progress bar
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        layout.addWidget(self.import_progress)
        
        # Log
        self.import_log = QTextEdit()
        self.import_log.setReadOnly(True)
        self.import_log.setMaximumHeight(150)
        layout.addWidget(self.import_log)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def select_import_file(self):
        """İçe aktarılacak dosyayı seçer."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "İçe Aktarılacak Dosyayı Seçin",
            str(Path.home()),
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*.*)"
        )
        
        if file_path:
            self.import_file_path = file_path
            self.import_file_label.setText(Path(file_path).name)
            self.import_file_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
    
    def start_export(self):
        """Dışa aktarmayı başlatır."""
        if self.export_worker and self.export_worker.isRunning():
            QMessageBox.warning(self, "Uyarı", "Bir dışa aktarma işlemi zaten devam ediyor.")
            return
        
        report_type = self.export_type_combo.currentText()
        export_format = self.export_format_combo.currentText()
        
        self.export_log.clear()
        self.export_log.append(f"Dışa aktarma başlatılıyor... ({report_type} - {export_format})")
        self.export_progress.setVisible(True)
        self.export_progress.setValue(0)
        
        self.export_worker = StockExportWorker(self.db, report_type, export_format)
        self.export_worker.progress.connect(self.export_progress.setValue)
        self.export_worker.finished.connect(self.export_finished)
        self.export_worker.start()
    
    def export_finished(self, success, message):
        """Dışa aktarma tamamlandığında çağrılır."""
        self.export_progress.setVisible(False)
        
        if success:
            self.export_log.append(f"\n✅ {message}")
            QMessageBox.information(self, "Başarılı", message)
        else:
            self.export_log.append(f"\n❌ {message}")
            QMessageBox.warning(self, "Hata", message)
    
    def start_import(self):
        """İçe aktarmayı başlatır."""
        if not hasattr(self, 'import_file_path') or not self.import_file_path:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir dosya seçin.")
            return
        
        if self.import_worker and self.import_worker.isRunning():
            QMessageBox.warning(self, "Uyarı", "Bir içe aktarma işlemi zaten devam ediyor.")
            return
        
        # Onay al
        reply = QMessageBox.question(
            self,
            "İçe Aktarma Onayı",
            f"Seçilen dosyadaki veriler stok tablonuza aktarılacak.\n\n"
            f"Dosya: {Path(self.import_file_path).name}\n"
            f"Mevcut kayıtlar: {'Güncellenecek' if self.update_existing_check.isChecked() else 'Atlanacak'}\n\n"
            f"Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.import_log.clear()
        self.import_log.append(f"İçe aktarma başlatılıyor...\nDosya: {Path(self.import_file_path).name}")
        self.import_progress.setVisible(True)
        self.import_progress.setValue(0)
        
        self.import_worker = StockImportWorker(
            self.db,
            self.import_file_path,
            self.update_existing_check.isChecked()
        )
        self.import_worker.progress.connect(self.import_progress.setValue)
        self.import_worker.finished.connect(self.import_finished)
        self.import_worker.start()
    
    def import_finished(self, success, message, stats):
        """İçe aktarma tamamlandığında çağrılır."""
        self.import_progress.setVisible(False)
        
        if success:
            self.import_log.append(f"\n✅ {message}")
            QMessageBox.information(self, "Başarılı", message)
            
            # Parent'ı refresh et
            if self.parent():
                try:
                    self.parent().refresh_data()
                except:
                    pass
        else:
            self.import_log.append(f"\n❌ {message}")
            QMessageBox.warning(self, "Hata", message)
