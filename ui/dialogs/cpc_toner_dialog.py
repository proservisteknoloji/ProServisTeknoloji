"""
CPC Toner/Kit Ekleme Dialog'u
CPC cihazları için toner ve kit eklemek veya görüntülemek için dialog.
Veritabanından mevcut toner/kit bilgilerini otomatik yükler.
"""

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QFormLayout, QMessageBox,
                             QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.database import db_manager
from utils.error_logger import log_info, log_error  # 👈 loglama modülü

class CPCTonerDialog(QDialog):
    """CPC cihazı için toner/kit ekleme ve düzenleme dialog'u."""
    
    def __init__(self, device_model: str, device_color_type: str, device_id: int, parent=None):
        super().__init__(parent)
        self.device_model = device_model
        self.device_color_type = device_color_type
        self.device_id = device_id
        
        self.setWindowTitle(f"🖨️ CPC Toner/Kit Ekle - {device_model}")
        self.setMinimumWidth(600)
        
        log_info("CPCTonerDialog", f"Dialog başlatılıyor. Cihaz ID: {device_id}, Model: {device_model}")
        
        self.init_ui()
        self.load_existing_toner_data()
    
    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"🖨️ {self.device_model}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel(f"Renk Tipi: {self.device_color_type}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Toner Grubu
        toner_group = QGroupBox("🎨 Toner Kodları")
        toner_layout = QFormLayout()
        
        if self.device_color_type == 'Renkli':
            self.black_toner = QLineEdit()
            self.black_toner.setPlaceholderText("Siyah toner kodu (örn: TK-3100)")
            toner_layout.addRow("⬛ Siyah:", self.black_toner)
            
            self.cyan_toner = QLineEdit()
            self.cyan_toner.setPlaceholderText("Cyan toner kodu")
            toner_layout.addRow("🔵 Cyan:", self.cyan_toner)
            
            self.magenta_toner = QLineEdit()
            self.magenta_toner.setPlaceholderText("Magenta toner kodu")
            toner_layout.addRow("🔴 Magenta:", self.magenta_toner)
            
            self.yellow_toner = QLineEdit()
            self.yellow_toner.setPlaceholderText("Yellow toner kodu")
            toner_layout.addRow("🟡 Yellow:", self.yellow_toner)
            
            self.black_eq = QLineEdit()
            self.black_eq.setPlaceholderText("Muadil siyah toner kodu")
            toner_layout.addRow("⬛ Siyah (Muadil):", self.black_eq)
            
            self.cyan_eq = QLineEdit()
            self.cyan_eq.setPlaceholderText("Muadil cyan toner kodu")
            toner_layout.addRow("🔵 Cyan (Muadil):", self.cyan_eq)
            
            self.magenta_eq = QLineEdit()
            self.magenta_eq.setPlaceholderText("Muadil magenta toner kodu")
            toner_layout.addRow("🔴 Magenta (Muadil):", self.magenta_eq)
            
            self.yellow_eq = QLineEdit()
            self.yellow_eq.setPlaceholderText("Muadil yellow toner kodu")
            toner_layout.addRow("🟡 Yellow (Muadil):", self.yellow_eq)
        else:
            self.black_toner = QLineEdit()
            self.black_toner.setPlaceholderText("Siyah toner kodu (örn: TK-3100)")
            toner_layout.addRow("⬛ Siyah:", self.black_toner)
            
            self.black_eq = QLineEdit()
            self.black_eq.setPlaceholderText("Muadil siyah toner kodu")
            toner_layout.addRow("⬛ Siyah (Muadil):", self.black_eq)
        
        toner_group.setLayout(toner_layout)
        layout.addWidget(toner_group)
        
        # Kit Grubu
        kit_group = QGroupBox("🔧 Kit Kodları")
        kit_layout = QFormLayout()
        
        self.kit1 = QLineEdit()
        self.kit1.setPlaceholderText("Kit kodu (örn: MK-3100)")
        kit_layout.addRow("Kit 1:", self.kit1)
        
        self.kit2 = QLineEdit()
        self.kit2.setPlaceholderText("Kit kodu")
        kit_layout.addRow("Kit 2:", self.kit2)
        
        self.kit3 = QLineEdit()
        self.kit3.setPlaceholderText("Kit kodu")
        kit_layout.addRow("Kit 3:", self.kit3)
        
        self.kit4 = QLineEdit()
        self.kit4.setPlaceholderText("Kit kodu")
        kit_layout.addRow("Kit 4:", self.kit4)
        
        kit_group.setLayout(kit_layout)
        layout.addWidget(kit_group)
        
        # Butonlar
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Kaydet")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_existing_toner_data(self):
        """cpc_stock_items tablosundan mevcut toner ve kit bilgilerini yükler."""
        log_info("CPCTonerDialog", f"Toner verisi yükleniyor. Cihaz ID: {self.device_id}")
        try:
            query = "SELECT toner_code, color FROM cpc_stock_items WHERE device_id = ?"
            items = db_manager.fetch_all(query, (self.device_id,))
            log_info("CPCTonerDialog", f"cpc_stock_items'tan {len(items)} kayıt bulundu.")
            
            color_map = {
                'Siyah': 'black',
                'Mavi': 'cyan',
                'Kırmızı': 'magenta',
                'Sarı': 'yellow',
                'Kit': 'kit'
            }
            
            toners = {}
            kits = []
            for item in items:
                code = item['toner_code']
                color_tr = item['color']
                color_en = color_map.get(color_tr, 'kit')
                if color_en == 'kit':
                    kits.append(code)
                else:
                    toners[color_en] = code
                log_info("CPCTonerDialog", f"Bulunan öğe: {color_tr} → {code}")
            
            # UI'ye doldur
            if self.device_color_type == 'Renkli':
                self.black_toner.setText(toners.get('black', ''))
                self.cyan_toner.setText(toners.get('cyan', ''))
                self.magenta_toner.setText(toners.get('magenta', ''))
                self.yellow_toner.setText(toners.get('yellow', ''))
                self.black_eq.setText(toners.get('black_equivalent', ''))
                self.cyan_eq.setText(toners.get('cyan_equivalent', ''))
                self.magenta_eq.setText(toners.get('magenta_equivalent', ''))
                self.yellow_eq.setText(toners.get('yellow_equivalent', ''))
            else:
                self.black_toner.setText(toners.get('black', ''))
                self.black_eq.setText(toners.get('black_equivalent', ''))
            
            for i in range(1, 5):
                if i <= len(kits):
                    getattr(self, f'kit{i}').setText(kits[i-1])
                else:
                    getattr(self, f'kit{i}').setText('')
            
            log_info("CPCTonerDialog", "Toner/kit bilgileri başarıyla UI'ya dolduruldu.")
                    
        except Exception as e:
            log_error("CPCTonerDialog", e)
            QMessageBox.warning(self, "Uyarı", f"Toner bilgileri yüklenirken hata oluştu:\n{str(e)}")

    def get_toner_data(self):
        data = {}
        if self.device_color_type == 'Renkli':
            data['black'] = self.black_toner.text().strip()
            data['cyan'] = self.cyan_toner.text().strip()
            data['magenta'] = self.magenta_toner.text().strip()
            data['yellow'] = self.yellow_toner.text().strip()
            data['black_equivalent'] = self.black_eq.text().strip()
            data['cyan_equivalent'] = self.cyan_eq.text().strip()
            data['magenta_equivalent'] = self.magenta_eq.text().strip()
            data['yellow_equivalent'] = self.yellow_eq.text().strip()
        else:
            data['black'] = self.black_toner.text().strip()
            data['black_equivalent'] = self.black_eq.text().strip()
        return data

    def get_kit_data(self):
        return {
            'kit1': self.kit1.text().strip(),
            'kit2': self.kit2.text().strip(),
            'kit3': self.kit3.text().strip(),
            'kit4': self.kit4.text().strip()
        }