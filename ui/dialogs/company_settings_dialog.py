# ui/dialogs/company_settings_dialog.py

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QDialogButtonBox, 
                             QPushButton, QLabel, QFileDialog, QDoubleSpinBox, QMessageBox)
from PyQt6.QtCore import Qt
from utils.database import db_manager

def normalize_email(email):
    """Email adresini küçük harfe çevirir ve Türkçe karakterleri İngilizce karşılıklarıyla değiştirir"""
    if not email:
        return email
    
    # Küçük harfe çevir
    email = email.lower()
    
    # Türkçe karakterleri İngilizce karşılıklarıyla değiştir
    turkish_chars = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
    }
    
    for turkish, english in turkish_chars.items():
        email = email.replace(turkish, english)
    
    return email

class CompanySettingsDialog(QDialog):
    """Firma bilgileri ve genel ayarları (KDV vb.) yönetmek için diyalog."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Firma Bilgileri ve Genel Ayarlar")
        self.setMinimumWidth(500)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        
        # Form elemanları
        self.company_name = QLineEdit()
        self.company_phone = QLineEdit()
        self.company_email = QLineEdit()
        self.company_address = QLineEdit()
        self.tax_office = QLineEdit()
        self.tax_id = QLineEdit()
        self.logo_path_label = QLabel("Logo seçilmedi.")
        self.logo_path_label.setStyleSheet("font-style: italic; color: #555;")
        self.select_logo_btn = QPushButton("Logo Seç...")
        self.vat_rate_spinbox = QDoubleSpinBox()
        self.vat_rate_spinbox.focusInEvent = lambda event: (self.vat_rate_spinbox.selectAll(), super(QDoubleSpinBox, self.vat_rate_spinbox).focusInEvent(event))[-1]
        self.vat_rate_spinbox.setSuffix(" %")
        self.vat_rate_spinbox.setRange(0.0, 100.0)
        self.vat_rate_spinbox.setDecimals(2)

        # Layout'a ekleme
        layout.addRow("Firma Adı:", self.company_name)
        layout.addRow("Telefon:", self.company_phone)
        layout.addRow("E-posta:", self.company_email)
        
        # Email normalize etme
        def normalize_company_email():
            current_text = self.company_email.text()
            normalized = normalize_email(current_text)
            if normalized != current_text:
                self.company_email.setText(normalized)
        
        self.company_email.textChanged.connect(normalize_company_email)
        layout.addRow("Adres:", self.company_address)
        layout.addRow("Vergi Dairesi:", self.tax_office)
        layout.addRow("Vergi/TC Kimlik No:", self.tax_id)
        layout.addRow("Firma Logosu:", self.select_logo_btn)
        layout.addRow("", self.logo_path_label)
        layout.addRow("Varsayılan KDV Oranı:", self.vat_rate_spinbox)
        
        # Butonlar
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)
        
        self._connect_signals(buttons)

    def _connect_signals(self, buttons: QDialogButtonBox):
        """Sinyalleri slotlara bağlar."""
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        self.select_logo_btn.clicked.connect(self.select_logo_file)

    def load_settings(self):
        """Veritabanından mevcut ayarları yükler ve form alanlarına doldurur."""
        try:
            # company_info tablosundan firma bilgilerini çek
            try:
                company_info = db_manager.fetch_one("""
                    SELECT company_name, phone, email, address, tax_office, tax_number
                    FROM company_info 
                    WHERE id = 1
                """)
                
                if company_info:
                    self.company_name.setText(company_info[0] or '')
                    self.company_phone.setText(company_info[1] or '')
                    self.company_email.setText(company_info[2] or '')
                    self.company_address.setText(company_info[3] or '')
                    self.tax_office.setText(company_info[4] or '')
                    self.tax_id.setText(company_info[5] or '')
                else:
                    # Boş kayıt, varsayılan değerlerle doldur
                    logging.info("company_info tablosu boş - varsayılan değerler kullanılıyor")
            except Exception as e:
                # company_info tablosu yoksa veya hata varsa varsayılan değerleri kullan
                logging.warning(f"company_info tablosu okunamadı: {e}")
                # Formu boş bırak, kullanıcı dolduracak
            
            # KDV oranı ve logo için settings_manager kullanmaya devam et
            if hasattr(self.parent(), 'get_setting'):
                vat_rate = self.parent().get_setting('vat_rate', '20.0')
                logo_path = self.parent().get_setting('company_logo_path', 'Logo seçilmedi.')
            else:
                from utils.settings_manager import get_setting
                vat_rate = get_setting('vat_rate', '20.0')
                logo_path = get_setting('company_logo_path', 'Logo seçilmedi.')
                
            self.vat_rate_spinbox.setValue(float(vat_rate))
            self.logo_path_label.setText(logo_path)
        except Exception as e:
            QMessageBox.critical(self, "Ayar Yükleme Hatası", f"Firma ayarları yüklenirken bir hata oluştu: {e}")

    def select_logo_file(self):
        """Kullanıcının bir logo dosyası seçmesini sağlayan dosya diyalogunu açar."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Logo Dosyası Seç", "", 
                                                   "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.logo_path_label.setText(file_path)

    def save_and_accept(self):
        """Formdaki ayarları veritabanına kaydeder."""
        try:
            # Firma bilgilerini company_info tablosuna kaydet
            company_data = {
                'company_name': self.company_name.text(),
                'phone': self.company_phone.text(),
                'email': self.company_email.text(),
                'address': self.company_address.text(),
                'tax_office': self.tax_office.text(),
                'tax_number': self.tax_id.text()
            }
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO company_info 
                (id, company_name, phone, email, address, tax_office, tax_number, logo_path)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_data['company_name'],
                company_data['phone'],
                company_data['email'],
                company_data['address'],
                company_data['tax_office'],
                company_data['tax_number'],
                ''  # logo_path şimdilik boş
            ))
            
            # Firma bilgilerini settings tablosuna da kaydet (ana pencere için)
            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_name', ?)
            """, (company_data['company_name'],))
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_phone', ?)
            """, (company_data['phone'],))
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_email', ?)
            """, (company_data['email'],))
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_address', ?)
            """, (company_data['address'],))
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_tax_office', ?)
            """, (company_data['tax_office'],))
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_tax_number', ?)
            """, (company_data['tax_number'],))

            db_manager.execute_query("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('company_tax_id', ?)
            """, (company_data['tax_number'],))
            
            # KDV oranı ve logo için settings_manager kullanmaya devam et
            settings = {
                'vat_rate': str(self.vat_rate_spinbox.value())
            }
            
            logo_path = self.logo_path_label.text()
            settings['company_logo_path'] = logo_path if logo_path != "Logo seçilmedi." else ""

            for key, value in settings.items():
                # Parent SettingsTab'ın set_setting metodunu kullan
                if hasattr(self.parent(), 'set_setting'):
                    self.parent().set_setting(key, value)
                else:
                    # Fallback: settings_manager'ı doğrudan kullan
                    from utils.settings_manager import save_setting
                    save_setting(key, value)
            
            QMessageBox.information(self, "Başarılı", "Firma ayarları başarıyla kaydedildi.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Kayıt Hatası", f"Firma ayarları kaydedilirken bir hata oluştu: {e}")
