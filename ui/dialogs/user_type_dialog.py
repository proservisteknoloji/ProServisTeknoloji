"""
User Type Selection Dialog - Mevcut mi yoksa Yeni kullanici mi?
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QRadioButton, QButtonGroup, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon


class UserTypeDialog(QDialog):
    """Kullanıcı tipi seçim dialog'u - Mevcut veya Yeni kullanıcı"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_type = None  # 'existing' veya 'new'
        self.setup_ui()
        
    def setup_ui(self):
        """UI elemanlarını oluştur"""
        self.setWindowTitle("ProServis v2.2 - Hoş Geldiniz")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # ============================================
        # Başlık
        # ============================================
        title_label = QLabel("🎉 ProServis v2.2'a Hoş Geldiniz!")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # ============================================
        # Açıklama
        # ============================================
        desc_label = QLabel(
            "Lütfen durumunuzu seçin:\n\n"
            "• Mevcut kullanıcıysanız, Azure SQL'e kayıtlı bilgilerinizle\n"
            "  giriş yapabilirsiniz.\n\n"
            "• Yeni kullanıcıysanız, kurulum sihirbazı ile firma ve\n"
            "  kullanıcı bilgilerinizi kaydedebilirsiniz."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; font-size: 11pt;")
        layout.addWidget(desc_label)
        
        layout.addSpacing(10)
        
        # ============================================
        # Radio Buttons
        # ============================================
        radio_widget = QWidget()
        radio_layout = QVBoxLayout(radio_widget)
        radio_layout.setSpacing(15)
        
        self.button_group = QButtonGroup(self)
        
        # Mevcut kullanıcı radio button
        self.existing_radio = QRadioButton("👤 Mevcut Kullanıcıyım")
        self.existing_radio.setStyleSheet("""
            QRadioButton {
                font-size: 12pt;
                padding: 10px;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.button_group.addButton(self.existing_radio, 1)
        radio_layout.addWidget(self.existing_radio)
        
        existing_desc = QLabel("  → Daha önce kaydoldum, giriş yapmak istiyorum")
        existing_desc.setStyleSheet("color: #666; font-size: 10pt; margin-left: 30px;")
        radio_layout.addWidget(existing_desc)
        
        radio_layout.addSpacing(5)
        
        # Yeni kullanıcı radio button
        self.new_radio = QRadioButton("✨ Yeni Kullanıcıyım")
        self.new_radio.setStyleSheet("""
            QRadioButton {
                font-size: 12pt;
                padding: 10px;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.button_group.addButton(self.new_radio, 2)
        radio_layout.addWidget(self.new_radio)
        
        new_desc = QLabel("  → İlk kez kullanıyorum, kurulum yapmak istiyorum")
        new_desc.setStyleSheet("color: #666; font-size: 10pt; margin-left: 30px;")
        radio_layout.addWidget(new_desc)
        
        layout.addWidget(radio_widget)
        
        layout.addStretch()
        
        # ============================================
        # Butonlar
        # ============================================
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.setFixedSize(120, 40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        continue_btn = QPushButton("✅ Devam Et")
        continue_btn.setFixedSize(120, 40)
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        continue_btn.clicked.connect(self.on_continue)
        button_layout.addWidget(continue_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # İlk durumda devam butonu disabled
        continue_btn.setEnabled(False)
        
        # Radio button değiştiğinde devam butonunu enable et
        self.button_group.buttonClicked.connect(lambda: continue_btn.setEnabled(True))
        
    def on_continue(self):
        """Devam butonuna tıklandığında"""
        if self.existing_radio.isChecked():
            self.user_type = 'existing'
        elif self.new_radio.isChecked():
            self.user_type = 'new'
        else:
            return  # Hiçbiri seçilmemişse
        
        self.accept()
    
    def get_user_type(self):
        """Seçilen kullanıcı tipini döndür"""
        return self.user_type
