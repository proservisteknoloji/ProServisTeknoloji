# ui/dialogs/device_analysis_dialog.py

"""
Cihaz-Toner uyumluluk analizi dialog'u.
Mevcut cihazlar için toner eksiklerini ve önerileri gösterir.
"""

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QGroupBox, QSplitter,
                             QMessageBox, QComboBox, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from utils.device_toner_compatibility import get_device_compatibility_info

class DeviceAnalysisDialog(QDialog):
    """Cihaz-Toner uyumluluk analizi dialog'u."""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🔍 Cihaz-Toner Uyumluluk Analizi")
        self.setMinimumSize(900, 700)
        self.init_ui()
        self.load_devices()
        
    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        main_layout = QVBoxLayout(self)
        
        # Üst panel: Kontroller
        controls_group = QGroupBox("Analiz Kontrolleri")
        controls_layout = QHBoxLayout(controls_group)
        
        # Cihaz filtresi
        self.device_filter = QLineEdit()
        self.device_filter.setPlaceholderText("Cihaz modeli filtresi...")
        self.device_filter.textChanged.connect(self.filter_devices)
        
        # CPC filtresi
        self.cpc_filter = QComboBox()
        self.cpc_filter.addItems(["Tüm Cihazlar", "Sadece CPC", "CPC Olmayan"])
        self.cpc_filter.currentTextChanged.connect(self.filter_devices)
        
        # Yenile butonu
        self.refresh_btn = QPushButton("🔄 Yenile")
        self.refresh_btn.clicked.connect(self.load_devices)
        
        # Analiz butonu
        self.analyze_btn = QPushButton("🔍 Tüm Cihazları Analiz Et")
        self.analyze_btn.clicked.connect(self.analyze_all_devices)
        
        controls_layout.addWidget(QLabel("Filtre:"))
        controls_layout.addWidget(self.device_filter)
        controls_layout.addWidget(QLabel("CPC:"))
        controls_layout.addWidget(self.cpc_filter)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.analyze_btn)
        
        main_layout.addWidget(controls_group)
        
        # Ana splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sol panel: Cihaz listesi
        devices_group = QGroupBox("Cihazlar")
        devices_layout = QVBoxLayout(devices_group)
        
        self.devices_table = QTableWidget(0, 6)
        self.devices_table.setHorizontalHeaderLabels([
            "ID", "Müşteri", "Model", "Seri No", "CPC", "Durum"
        ])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.devices_table.hideColumn(0)  # ID gizle
        
        devices_layout.addWidget(self.devices_table)
        
        # Sağ panel: Analiz sonuçları
        analysis_group = QGroupBox("Uyumluluk Analizi")
        analysis_layout = QVBoxLayout(analysis_group)
        
        # Seçili cihaz bilgisi
        self.selected_device_label = QLabel("Cihaz seçin...")
        self.selected_device_label.setStyleSheet("font-weight: bold; color: #1976D2;")
        
        # Analiz sonucu metni
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        self.analysis_result.setPlaceholderText("Cihaz seçtiğinizde uyumluluk analizi burada görünecek...")
        
        # Alt butonlar
        analysis_buttons = QHBoxLayout()
        
        self.analyze_selected_btn = QPushButton("🔍 Seçili Cihazı Analiz Et")
        self.analyze_selected_btn.clicked.connect(self.analyze_selected_device)
        self.analyze_selected_btn.setEnabled(False)
        
        self.create_missing_toners_btn = QPushButton("➕ Eksik Tonerleri Oluştur")
        self.create_missing_toners_btn.clicked.connect(self.create_missing_toners)
        self.create_missing_toners_btn.setEnabled(False)
        
        analysis_buttons.addWidget(self.analyze_selected_btn)
        analysis_buttons.addWidget(self.create_missing_toners_btn)
        analysis_buttons.addStretch()
        
        analysis_layout.addWidget(self.selected_device_label)
        analysis_layout.addWidget(self.analysis_result)
        analysis_layout.addLayout(analysis_buttons)
        
        splitter.addWidget(devices_group)
        splitter.addWidget(analysis_group)
        splitter.setSizes([400, 500])
        
        main_layout.addWidget(splitter)
        
        # Alt panel: Kapat butonu
        close_layout = QHBoxLayout()
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        
        main_layout.addLayout(close_layout)
        
        # Sinyaller
        self.devices_table.selectionModel().selectionChanged.connect(self.on_device_selected)
        
    def load_devices(self):
        """Cihazları veritabanından yükler."""
        try:
            query = """
                SELECT d.id, c.name as customer_name, d.model, d.serial_number, 
                       d.is_cpc, d.color_type
                FROM devices d
                LEFT JOIN customers c ON d.customer_id = c.id
                ORDER BY c.name, d.model
            """
            devices = self.db.fetch_all(query)
            
            self.devices_table.setRowCount(len(devices))
            
            for row, device in enumerate(devices):
                self.devices_table.setItem(row, 0, QTableWidgetItem(str(device['id'])))
                self.devices_table.setItem(row, 1, QTableWidgetItem(device['customer_name'] or 'Bilinmiyor'))
                self.devices_table.setItem(row, 2, QTableWidgetItem(device['model'] or ''))
                self.devices_table.setItem(row, 3, QTableWidgetItem(device['serial_number'] or ''))
                
                # CPC durumu
                cpc_status = "✅ CPC" if device['is_cpc'] else "❌ Normal"
                self.devices_table.setItem(row, 4, QTableWidgetItem(cpc_status))
                
                # Durum - başlangıçta boş
                self.devices_table.setItem(row, 5, QTableWidgetItem("Analiz edilmedi"))
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Cihazlar yüklenirken hata oluştu:\n{str(e)}")
            
    def filter_devices(self):
        """Cihazları filtreler."""
        filter_text = self.device_filter.text().lower()
        cpc_filter = self.cpc_filter.currentText()
        
        for row in range(self.devices_table.rowCount()):
            show_row = True
            
            # Metin filtresi
            if filter_text:
                model_item = self.devices_table.item(row, 2)
                customer_item = self.devices_table.item(row, 1)
                model_text = model_item.text().lower() if model_item else ""
                customer_text = customer_item.text().lower() if customer_item else ""
                
                if filter_text not in model_text and filter_text not in customer_text:
                    show_row = False
            
            # CPC filtresi
            if show_row and cpc_filter != "Tüm Cihazlar":
                cpc_item = self.devices_table.item(row, 4)
                cpc_text = cpc_item.text() if cpc_item else ""
                
                if cpc_filter == "Sadece CPC" and "✅ CPC" not in cpc_text:
                    show_row = False
                elif cpc_filter == "CPC Olmayan" and "❌ Normal" not in cpc_text:
                    show_row = False
            
            self.devices_table.setRowHidden(row, not show_row)
            
    def on_device_selected(self):
        """Cihaz seçildiğinde tetiklenir."""
        selected_rows = self.devices_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            device_id = self.devices_table.item(row, 0).text()
            customer_name = self.devices_table.item(row, 1).text()
            device_model = self.devices_table.item(row, 2).text()
            
            self.selected_device_id = int(device_id)
            self.selected_device_label.setText(f"Seçili: {customer_name} - {device_model}")
            
            self.analyze_selected_btn.setEnabled(True)
            
            # Otomatik analiz
            self.analyze_selected_device()
        else:
            self.selected_device_id = None
            self.selected_device_label.setText("Cihaz seçin...")
            self.analyze_selected_btn.setEnabled(False)
            self.create_missing_toners_btn.setEnabled(False)
            self.analysis_result.clear()
            
    def analyze_selected_device(self):
        """Seçili cihazı analiz eder."""
        if not hasattr(self, 'selected_device_id') or not self.selected_device_id:
            return
            
        try:
            # Cihaz bilgilerini al
            device_query = """
                SELECT d.model, d.serial_number, d.is_cpc, c.name as customer_name
                FROM devices d
                LEFT JOIN customers c ON d.customer_id = c.id
                WHERE d.id = ?
            """
            device = self.db.fetch_one(device_query, (self.selected_device_id,))
            
            if not device:
                self.analysis_result.setPlainText("❌ Cihaz bulunamadı!")
                return
                
            device_model = device['model']
            
            # Uyumluluk analizini yap
            compatibility_info = get_device_compatibility_info(device_model, self.db)
            
            # Sonuçları formatla
            result_text = f"🔍 CİHAZ ANALİZ RAPORU\n"
            result_text += f"=" * 50 + "\n\n"
            result_text += f"📱 Cihaz: {device_model}\n"
            result_text += f"👤 Müşteri: {device['customer_name']}\n"
            result_text += f"🏢 CPC: {'Evet' if device['is_cpc'] else 'Hayır'}\n"
            result_text += f"🔄 Normalleştirilmiş Model: {compatibility_info['normalized_model']}\n\n"
            
            # Uyumlu tonerler (stokta)
            if compatibility_info['compatible_toners']:
                result_text += "✅ UYUMLU TONERLER (Stokta Mevcut):\n"
                result_text += "-" * 40 + "\n"
                for toner in compatibility_info['compatible_toners']:
                    result_text += f"• {toner['name']}\n"
                    result_text += f"  Parça No: {toner['part_number']}\n"
                    result_text += f"  Stok: {toner['quantity']} adet\n"
                    result_text += f"  Fiyat: {toner['price']} {toner['currency']}\n\n"
            
            # Eksik tonerler
            if compatibility_info['missing_toners']:
                result_text += "⚠️ UYUMLU TONERLER (Stok Kartı Eksik):\n"
                result_text += "-" * 40 + "\n"
                for toner in compatibility_info['missing_toners']:
                    result_text += f"• {toner['part_number']} (Stok kartı oluşturulmalı)\n"
                result_text += "\n"
                self.create_missing_toners_btn.setEnabled(True)
            else:
                self.create_missing_toners_btn.setEnabled(False)
            
            # Sarf malzemeleri
            if compatibility_info['compatible_consumables']:
                result_text += "🔧 UYUMLU SARF MALZEMELERİ:\n"
                result_text += "-" * 40 + "\n"
                for consumable in compatibility_info['compatible_consumables']:
                    result_text += f"• {consumable['name']}\n"
                    result_text += f"  Parça No: {consumable['part_number']}\n"
                    result_text += f"  Stok: {consumable['quantity']} adet\n\n"
            
            # Öneriler
            if compatibility_info['suggestions']:
                result_text += "💡 ÖNERİLER:\n"
                result_text += "-" * 40 + "\n"
                for suggestion in compatibility_info['suggestions']:
                    result_text += f"• {suggestion}\n"
                result_text += "\n"
            
            # CPC özel durum
            if device['is_cpc']:
                result_text += "🏢 CPC MÜŞTERI UYARISI:\n"
                result_text += "-" * 40 + "\n"
                if compatibility_info['compatible_toners']:
                    result_text += "✅ Bu müşteri CPC sekmesinden otomatik toner siparişi verebilir.\n"
                else:
                    result_text += "⚠️ CPC sipariş sistemi için uyumlu toner stok kartları eksik!\n"
                    result_text += "💡 Eksik tonerleri eklemek için 'Eksik Tonerleri Oluştur' butonunu kullanın.\n"
                result_text += "\n"
            
            # Durum güncelle
            selected_rows = self.devices_table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                if compatibility_info['compatible_toners'] and not compatibility_info['missing_toners']:
                    status = "✅ Tamam"
                elif compatibility_info['compatible_toners'] and compatibility_info['missing_toners']:
                    status = "⚠️ Kısmi"
                else:
                    status = "❌ Eksik"
                self.devices_table.setItem(row, 5, QTableWidgetItem(status))
            
            self.analysis_result.setPlainText(result_text)
            
        except Exception as e:
            self.analysis_result.setPlainText(f"❌ Analiz sırasında hata oluştu:\n{str(e)}")
            logging.error(f"Cihaz analizi hatası: {e}")
            
    def analyze_all_devices(self):
        """Tüm cihazları analiz eder."""
        reply = QMessageBox.question(
            self, "Toplu Analiz",
            "Tüm cihazların toner uyumluluğu analiz edilsin mi?\n"
            "Bu işlem biraz zaman alabilir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            total_devices = 0
            compatible_devices = 0
            partial_devices = 0
            missing_devices = 0
            
            for row in range(self.devices_table.rowCount()):
                if self.devices_table.isRowHidden(row):
                    continue
                    
                total_devices += 1
                device_model = self.devices_table.item(row, 2).text()
                
                if device_model:
                    compatibility_info = get_device_compatibility_info(device_model, self.db)
                    
                    if compatibility_info['compatible_toners'] and not compatibility_info['missing_toners']:
                        status = "✅ Tamam"
                        compatible_devices += 1
                    elif compatibility_info['compatible_toners'] and compatibility_info['missing_toners']:
                        status = "⚠️ Kısmi"
                        partial_devices += 1
                    else:
                        status = "❌ Eksik"
                        missing_devices += 1
                else:
                    status = "❓ Belirsiz"
                    
                self.devices_table.setItem(row, 5, QTableWidgetItem(status))
            
            # Özet göster
            summary = f"📊 TOPLU ANALİZ SONUCU\n"
            summary += f"=" * 30 + "\n\n"
            summary += f"📱 Toplam Cihaz: {total_devices}\n"
            summary += f"✅ Tamam: {compatible_devices}\n"
            summary += f"⚠️ Kısmi: {partial_devices}\n"
            summary += f"❌ Eksik: {missing_devices}\n\n"
            summary += f"📈 Uyumluluk Oranı: %{(compatible_devices/total_devices*100):.1f}\n"
            
            self.analysis_result.setPlainText(summary)
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Toplu analiz sırasında hata oluştu:\n{str(e)}")
            
    def create_missing_toners(self):
        """Eksik tonerleri otomatik oluşturur."""
        QMessageBox.information(
            self, "Geliştirme Aşamasında",
            "Eksik toner kartlarını otomatik oluşturma özelliği\n"
            "gelecek sürümlerde eklenecektir.\n\n"
            "Şu anda manuel olarak stok kartı oluşturabilirsiniz."
        )