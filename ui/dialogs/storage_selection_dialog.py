"""
Storage Selection Dialog
İlk kurulum sırasında kullanıcıya veri saklama yerini sorar
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QRadioButton, QButtonGroup, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon


class StorageSelectionDialog(QDialog):
    """Veri saklama yeri seçim dialogu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_storage = "local"  # Varsayılan: yerel
        self.init_ui()
        
    def init_ui(self):
        """UI'ı oluştur"""
        self.setWindowTitle("ProServis - Veri Saklama Ayarı")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Başlık
        title = QLabel("Hoş Geldiniz!")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Açıklama
        description = QLabel(
            "ProServis verilerinizi nerede saklamak istersiniz?"
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        layout.addSpacing(10)
        
        # Radio button grubu
        self.button_group = QButtonGroup()
        
        # Yerel Seçenek
        local_frame = self._create_option_frame(
            "💻 Yerel Bilgisayar",
            "Veriler sadece bu bilgisayarda saklanır.\n"
            "Hızlı ve güvenli, ancak diğer cihazlardan erişilemez.",
            "local"
        )
        layout.addWidget(local_frame)
        
        # Bulut Seçenek
        cloud_frame = self._create_option_frame(
            "☁️ Bulut Depolama",
            "Veriler güvenli bulut sunucusunda saklanır.\n"
            "Her yerden erişim, otomatik yedekleme ve senkronizasyon.",
            "cloud"
        )
        layout.addWidget(cloud_frame)
        
        layout.addStretch()
        
        # Butonlar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("Devam Et")
        self.ok_btn.setMinimumWidth(100)
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Varsayılan olarak yerel seçili
        self.local_radio.setChecked(True)
    
    def _create_option_frame(self, title: str, description: str, value: str):
        """Seçenek frame'i oluştur"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                border: 2px solid #cccccc;
                border-radius: 8px;
                padding: 15px;
                background-color: white;
            }
            QFrame:hover {
                border-color: #0078d4;
                background-color: #f0f8ff;
            }
        """)
        
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(10)
        
        # Radio button ve başlık
        header_layout = QHBoxLayout()
        
        radio = QRadioButton(title)
        radio.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.button_group.addButton(radio)
        
        if value == "local":
            self.local_radio = radio
        else:
            self.cloud_radio = radio
        
        # Radio button değiştiğinde
        radio.toggled.connect(lambda checked, v=value: self._on_selection_changed(v, checked))
        
        header_layout.addWidget(radio)
        header_layout.addStretch()
        frame_layout.addLayout(header_layout)
        
        # Açıklama
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; margin-left: 25px;")
        frame_layout.addWidget(desc_label)
        
        frame.setLayout(frame_layout)
        
        # Frame tıklanınca radio button'ı seç
        frame.mousePressEvent = lambda event: radio.setChecked(True)
        
        return frame
    
    def _on_selection_changed(self, value: str, checked: bool):
        """Seçim değiştiğinde"""
        if checked:
            self.selected_storage = value
    
    def get_selection(self) -> str:
        """
        Seçilen storage türünü döndür
        
        Returns:
            'local' veya 'cloud'
        """
        return self.selected_storage


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = StorageSelectionDialog()
    
    if dialog.exec():
        print(f"Seçilen: {dialog.get_selection()}")
    else:
        print("İptal edildi")
    
    sys.exit()
