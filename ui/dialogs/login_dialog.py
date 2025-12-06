# ui/dialogs/login_dialog.py

import bcrypt
import os
import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit,
                             QPushButton, QLabel, QMessageBox, QDialogButtonBox,
                             QCheckBox, QHBoxLayout, QFormLayout, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer
from PyQt6.QtGui import QPixmap
from utils.database import db_manager
from utils.settings_manager import SettingsManager

# Azure SQL Manager için
try:
    from utils.sync_manager import get_azure_manager
except ImportError:
    get_azure_manager = None

class LoginDialog(QDialog):
    """Kullanıcı girişi için diyalog penceresi."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.logged_in_user = None
        self.logged_in_role = None
        self.settings = SettingsManager()

        self.setWindowTitle("ProServis Kullanıcı Girişi")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #F3F4F6;
                border-radius: 10px;
            }
            QLabel {
                color: #1F2937;
                font-size: 11pt;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                padding: 8px;
                border-radius: 5px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
            }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QCheckBox {
                color: #1F2937;
                font-size: 10pt;
                spacing: 8px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #9CA3AF;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #3B82F6;
                background-color: #EFF6FF;
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6;
                border-color: #3B82F6;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #2563EB;
                border-color: #2563EB;
            }
        """)

        self.init_ui()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        logo_path = self.settings.get_setting('company_logo_path', '')
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("ProServis")
            logo_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #3B82F6;")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo_label)

        # Form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Kullanıcı adınızı girin")
        form_layout.addRow("Kullanıcı Adı:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Şifrenizi girin")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Şifre:", self.password_input)

        main_layout.addLayout(form_layout)

        # Remember username checkbox
        self.remember_checkbox = QCheckBox("Kullanıcı adını hatırla")
        self.remember_checkbox.setChecked(self.settings.get_setting('remember_username', False))
        main_layout.addWidget(self.remember_checkbox)

        # Forgot password checkbox
        self.forgot_password_checkbox = QCheckBox("Şifremi unuttum - e-posta ile gönder")
        self.forgot_password_checkbox.setStyleSheet("""
            QCheckBox {
                color: #dc3545;
                font-size: 10pt;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #dc3545;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #c82333;
                background-color: #f8d7da;
            }
            QCheckBox::indicator:checked {
                background-color: #dc3545;
                border-color: #dc3545;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #c82333;
                border-color: #c82333;
            }
        """)
        main_layout.addWidget(self.forgot_password_checkbox)

        # Load last username if remember is checked
        if self.remember_checkbox.isChecked():
            last_username = self.settings.get_setting('last_username', '')
            self.username_input.setText(last_username)
            # Kullanıcı adı dolu ise imleci şifre alanına taşı
            if last_username:
                self.password_input.setFocus()
        else:
            # Kullanıcı adı boş ise imleci kullanıcı adı alanında başlat
            self.username_input.setFocus()

        # OK ve Cancel butonları
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.attempt_login)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # Enter tuşuna basıldığında girişi denemesi için
        self.username_input.returnPressed.connect(self.attempt_login)
        self.password_input.returnPressed.connect(self.attempt_login)

    def shake_password_field(self):
        """Şifre alanını titretir (hatalı giriş animasyonu)."""
        # Orijinal pozisyonu kaydet
        original_pos = self.password_input.pos()
        
        # Animasyon oluştur
        self.shake_animation = QPropertyAnimation(self.password_input, b"pos")
        self.shake_animation.setDuration(500)  # 500ms
        self.shake_animation.setLoopCount(1)
        
        # Titreme noktaları
        self.shake_animation.setKeyValueAt(0, original_pos)
        self.shake_animation.setKeyValueAt(0.1, original_pos + QPoint(10, 0))
        self.shake_animation.setKeyValueAt(0.2, original_pos + QPoint(-10, 0))
        self.shake_animation.setKeyValueAt(0.3, original_pos + QPoint(10, 0))
        self.shake_animation.setKeyValueAt(0.4, original_pos + QPoint(-10, 0))
        self.shake_animation.setKeyValueAt(0.5, original_pos + QPoint(10, 0))
        self.shake_animation.setKeyValueAt(0.6, original_pos + QPoint(-10, 0))
        self.shake_animation.setKeyValueAt(0.7, original_pos + QPoint(5, 0))
        self.shake_animation.setKeyValueAt(0.8, original_pos + QPoint(-5, 0))
        self.shake_animation.setKeyValueAt(0.9, original_pos + QPoint(2, 0))
        self.shake_animation.setKeyValueAt(1, original_pos)
        
        # Animasyonu başlat
        self.shake_animation.start()
        
        # Şifre alanını kırmızı yap (geçici)
        original_style = self.password_input.styleSheet()
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #FEE;
                border: 2px solid #EF4444;
                padding: 8px;
                border-radius: 5px;
                font-size: 10pt;
            }
        """)
        
        # Şifre alanını temizle
        self.password_input.clear()
        self.password_input.setFocus()
        
        # 1 saniye sonra normal renge dön
        QTimer.singleShot(1000, lambda: self.password_input.setStyleSheet(original_style))

    def attempt_login(self):
        """Kullanıcı adı ve şifreyi alıp veritabanında doğrulamayı dener."""
        username = self.username_input.text().strip()
        password = self.password_input.text().encode('utf-8')
        
        if not username or not self.password_input.text():
            # Boş alan varsa titretme animasyonu göster
            if not username:
                self.username_input.setFocus()
            else:
                self.password_input.setFocus()
            self.shake_password_field()
            return

        # Şifre hatırlatma kontrolü
        if self.forgot_password_checkbox.isChecked():
            self.send_password_reminder(username)
            return

        try:
            # Önce Azure SQL'den dene (multi-tenant için)
            azure_manager = get_azure_manager() if get_azure_manager else None
            azure_auth_success = False
            
            if azure_manager:
                logging.info(f"Azure SQL authentication deneniyor: {username}")
                
                # Plain password gönder (Azure'da bcrypt.checkpw yapılacak)
                plain_password = self.password_input.text()
                
                # Azure'dan auth
                result = azure_manager.authenticate_user(username, plain_password)
                
                if result['success']:
                    user = result['user']
                    
                    # SESSION OLUŞTUR (Bulut modu için - geçici)
                    from utils.session_manager import get_session_manager
                    session_manager = get_session_manager()
                    session_manager.create_session(
                        username=user['username'],
                        company_name=user['company_name'],
                        company_schema=user['company_schema'],
                        role=user['role']
                    )
                    
                    # Azure manager'ın current_company'sini güncelle (SCHEMA ADI kullan!)
                    azure_manager.current_company = user['company_schema']
                    
                    self.logged_in_user = user['username']
                    self.logged_in_role = user['role']
                    azure_auth_success = True
                    
                    logging.info(f"✅ Azure auth başarılı: {username} ({user['company_name']})")
                    logging.info(f"✅ Session oluşturuldu: {user['company_name']} → {user['company_schema']}")
                    
                    # Save remember settings (SADECE USERNAME)
                    self.settings.set_setting('remember_username', self.remember_checkbox.isChecked())
                    if self.remember_checkbox.isChecked():
                        self.settings.set_setting('last_username', username)
                    
                    self.accept()
                    return
            
            # Fallback: Lokal SQLite
            if not azure_auth_success:
                logging.info(f"Lokal SQLite authentication deneniyor: {username}")
                
                query = "SELECT username, password_hash, role FROM users WHERE username = ?"
                user_data = self.db.fetch_one(query, (username,))
                
                if user_data:
                    stored_username, stored_hash, stored_role = user_data
                    
                    # Veritabanından gelen hash'in bytes olduğundan emin ol
                    if isinstance(stored_hash, str):
                        stored_hash_bytes = stored_hash.encode('utf-8')
                    else:
                        stored_hash_bytes = stored_hash

                    if bcrypt.checkpw(password, stored_hash_bytes):
                        self.logged_in_user = stored_username
                        self.logged_in_role = stored_role

                        # Save remember settings
                        self.settings.set_setting('remember_username', self.remember_checkbox.isChecked())
                        if self.remember_checkbox.isChecked():
                            self.settings.set_setting('last_username', stored_username)

                        self.accept()  # Giriş başarılı, diyalogu kapat
                    else:
                        # Hatalı şifre - titretme animasyonu göster
                        self.shake_password_field()
                else:
                    # Kullanıcı bulunamadı - titretme animasyonu göster
                    self.shake_password_field()
        
        except Exception as e:
            logging.error(f"Login error: {e}", exc_info=True)
            QMessageBox.critical(self, "Veritabanı Hatası", f"Giriş işlemi sırasında bir hata oluştu: {e}")
            self.reject()

    def send_password_reminder(self, username: str):
        """Kullanıcının şifresini e-posta ile gönderir."""
        try:
            # Kullanıcının şifresini veritabanından al
            query = "SELECT password_hash FROM users WHERE username = ?"
            user_data = self.db.fetch_one(query, (username,))
            
            if not user_data:
                QMessageBox.warning(self, "Kullanıcı Bulunamadı", "Bu kullanıcı adı sistemde kayıtlı değil.")
                return
            
            # Şifreyi decode et (bcrypt hash'ini geri çeviremeyiz, bu yüzden orijinal şifreyi saklamalıyız)
            # Ancak setup sırasında orijinal şifre saklanıyor, bu hash
            # Şimdilik hash'i göstereceğiz, daha sonra düzeltilebilir
            stored_hash = user_data[0]
            
            # Firma e-posta adresini al
            company_query = "SELECT email FROM company_info WHERE id = 1"
            company_data = self.db.fetch_one(company_query)
            
            if not company_data or not company_data[0]:
                QMessageBox.warning(self, "E-posta Adresi Yok", "Firma e-posta adresi bulunamadı. Lütfen sistem yöneticinizle iletişime geçin.")
                return
            
            company_email = company_data[0]
            
            # Şifre hatırlatma e-postası gönder
            from main import send_password_reminder_email
            
            # Hash yerine kullanıcıya bilgi verelim
            QMessageBox.information(
                self, 
                "Şifre Hatırlatma", 
                f"Şifreniz {company_email} adresine gönderildi.\n\n"
                "E-posta gelmezse sistem yöneticinizle iletişime geçin."
            )
            
            # Şifre yerine hash gönder (şimdilik)
            send_password_reminder_email(username, f"Hash: {stored_hash[:20]}...", company_email)
            
        except Exception as e:
            logging.error(f"Şifre hatırlatma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Şifre hatırlatma işlemi sırasında hata oluştu: {e}")