"""
First User Creation Dialog
İlk kurulum sırasında admin kullanıcı oluşturur
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class FirstUserDialog(QDialog):
    """İlk admin kullanıcı oluşturma dialogu"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.username = None
        self.password = None
        self.full_name = None
        self.init_ui()
        
    def init_ui(self):
        """UI'ı oluştur"""
        self.setWindowTitle("ProServis - İlk Kullanıcı Oluşturma")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Başlık
        title = QLabel("Admin Kullanıcı Oluştur")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Açıklama
        description = QLabel(
            "ProServis'e giriş yapabilmek için bir admin kullanıcı oluşturun.\n"
            "Bu kullanıcı tüm yetkilere sahip olacaktır."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("color: #666666;")
        layout.addWidget(description)
        
        layout.addSpacing(10)
        
        # Form grubu
        form_group = QGroupBox("Kullanıcı Bilgileri")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Ad Soyad
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Örn: Ahmet Yılmaz")
        self.fullname_input.setMinimumHeight(35)
        form_layout.addRow("👤 Ad Soyad:", self.fullname_input)
        
        # Kullanıcı Adı
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Örn: admin veya ahmet.yilmaz")
        self.username_input.setMinimumHeight(35)
        self.username_input.textChanged.connect(self.check_username_availability)
        form_layout.addRow("🔑 Kullanıcı Adı:", self.username_input)
        
        # Kullanıcı adı durum label'ı
        self.username_status = QLabel("")
        self.username_status.setWordWrap(True)
        form_layout.addRow("", self.username_status)
        
        # Şifre
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("En az 6 karakter")
        self.password_input.setMinimumHeight(35)
        self.password_input.textChanged.connect(self.check_password_strength)
        form_layout.addRow("🔒 Şifre:", self.password_input)
        
        # Şifre tekrar
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm_input.setPlaceholderText("Şifrenizi tekrar girin")
        self.password_confirm_input.setMinimumHeight(35)
        self.password_confirm_input.textChanged.connect(self.check_password_match)
        form_layout.addRow("🔒 Şifre Tekrar:", self.password_confirm_input)
        
        # Şifre durum label'ı
        self.password_status = QLabel("")
        self.password_status.setWordWrap(True)
        form_layout.addRow("", self.password_status)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        layout.addStretch()
        
        # Butonlar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.create_btn = QPushButton("Kullanıcı Oluştur")
        self.create_btn.setMinimumWidth(150)
        self.create_btn.setMinimumHeight(40)
        self.create_btn.setDefault(True)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.create_btn.clicked.connect(self.create_user)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def check_username_availability(self):
        """Kullanıcı adı uygunluğunu kontrol et"""
        username = self.username_input.text().strip()
        
        if not username:
            self.username_status.setText("")
            return
        
        # Minimum uzunluk kontrolü
        if len(username) < 3:
            self.username_status.setText("⚠️ Kullanıcı adı en az 3 karakter olmalı")
            self.username_status.setStyleSheet("color: #ff6b6b;")
            return
        
        # Geçersiz karakter kontrolü
        if not username.replace('_', '').replace('.', '').replace('-', '').isalnum():
            self.username_status.setText("⚠️ Sadece harf, rakam, _, ., - kullanılabilir")
            self.username_status.setStyleSheet("color: #ff6b6b;")
            return
        
        # Veritabanında kontrol et
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                self.username_status.setText("❌ Bu kullanıcı adı zaten kullanılıyor")
                self.username_status.setStyleSheet("color: #ff6b6b;")
            else:
                self.username_status.setText("✅ Kullanıcı adı uygun")
                self.username_status.setStyleSheet("color: #51cf66;")
        except Exception as e:
            self.username_status.setText("")
    
    def check_password_strength(self):
        """Şifre gücünü kontrol et"""
        password = self.password_input.text()
        
        if not password:
            self.password_status.setText("")
            return
        
        if len(password) < 6:
            self.password_status.setText("⚠️ Şifre en az 6 karakter olmalı")
            self.password_status.setStyleSheet("color: #ff6b6b;")
        elif len(password) < 8:
            self.password_status.setText("⚠️ Orta güçte şifre (8+ karakter önerilir)")
            self.password_status.setStyleSheet("color: #ffd43b;")
        else:
            self.check_password_match()
    
    def check_password_match(self):
        """Şifre eşleşmesini kontrol et"""
        password = self.password_input.text()
        confirm = self.password_confirm_input.text()
        
        if not confirm:
            if len(password) >= 8:
                self.password_status.setText("✅ Güçlü şifre")
                self.password_status.setStyleSheet("color: #51cf66;")
            return
        
        if password != confirm:
            self.password_status.setText("❌ Şifreler eşleşmiyor")
            self.password_status.setStyleSheet("color: #ff6b6b;")
        else:
            self.password_status.setText("✅ Şifreler eşleşiyor")
            self.password_status.setStyleSheet("color: #51cf66;")
    
    def validate_inputs(self) -> tuple:
        """
        Girişleri doğrula
        
        Returns:
            (bool, str): (Geçerli mi, Hata mesajı)
        """
        fullname = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.password_confirm_input.text()
        
        # Ad Soyad kontrolü
        if not fullname:
            return False, "Lütfen ad soyad girin"
        
        # Kullanıcı adı kontrolü
        if not username:
            return False, "Lütfen kullanıcı adı girin"
        
        if len(username) < 3:
            return False, "Kullanıcı adı en az 3 karakter olmalı"
        
        if not username.replace('_', '').replace('.', '').replace('-', '').isalnum():
            return False, "Kullanıcı adı sadece harf, rakam, _, ., - içerebilir"
        
        # Kullanıcı adı çakışma kontrolü
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if cursor.fetchone()[0] > 0:
                return False, "Bu kullanıcı adı zaten kullanılıyor"
        except:
            pass
        
        # Şifre kontrolü
        if not password:
            return False, "Lütfen şifre girin"
        
        if len(password) < 6:
            return False, "Şifre en az 6 karakter olmalı"
        
        if password != confirm:
            return False, "Şifreler eşleşmiyor"
        
        return True, ""
    
    def create_user(self):
        """Kullanıcı oluştur"""
        # Validasyon
        valid, error_msg = self.validate_inputs()
        if not valid:
            QMessageBox.warning(self, "Hata", error_msg)
            return
        
        try:
            import bcrypt
            
            fullname = self.fullname_input.text().strip()
            username = self.username_input.text().strip()
            password = self.password_input.text()
            
            # Şifreyi hash'le (bcrypt)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Veritabanına ekle (mevcut tablo yapısına uygun)
            cursor = self.db.get_connection().cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
            """, (username, password_hash, 'Admin'))
            
            self.db.get_connection().commit()
            
            # Sonuçları kaydet
            self.username = username
            self.password = password  # Plain password (login için)
            self.full_name = fullname
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"Admin kullanıcı '{username}' başarıyla oluşturuldu!\n\n"
                f"Bu bilgilerle giriş yapabilirsiniz."
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Hata",
                f"Kullanıcı oluşturulamadı:\n{str(e)}"
            )
    
    def get_user_info(self) -> dict:
        """
        Oluşturulan kullanıcı bilgilerini döndür
        
        Returns:
            dict: {'username': str, 'password': str, 'full_name': str}
        """
        return {
            'username': self.username,
            'password': self.password,
            'full_name': self.full_name
        }
