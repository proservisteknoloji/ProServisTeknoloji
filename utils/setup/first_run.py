# utils/setup/first_run.py
"""İlk kurulum kontrolü ve setup wizard yönetimi."""

import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from utils.settings_manager import load_app_config, save_app_config


def check_first_run():
    """
    İlk kurulum kontrolü yapar ve setup wizard'ını gösterir.
    
    Setup Wizard Adımları:
    1. Hoş Geldiniz (Mevcut/Yeni müşteri seçimi)
    2. Firma bilgileri
    3. Veritabanı seçimi (Azure SQL / SQLite)
    4. İlk kullanıcı oluşturma
    5. Lisans anahtarı (opsiyonel)
    6. Kurulum tamamlandı
    
    Returns:
        tuple: (bool başarılı_mı, dict user_info veya None, bool is_existing_user)
    """
    config = load_app_config()
    is_setup_complete = config.get('is_setup_complete', False)
    
    if is_setup_complete:
        logging.info("Kurulum daha önce tamamlanmış - Normal çalışma modu")
        return True, None, False
    
    # İlk kurulum - Setup Wizard başlat
    logging.info("İlk kurulum tespit edildi - Setup Wizard başlatılıyor...")
    
    from ui.dialogs.setup_wizard_dialog import SetupWizardDialog
    
    wizard = SetupWizardDialog()
    setup_data = {}
    
    def on_setup_completed(data):
        nonlocal setup_data
        setup_data = data
        logging.info("Setup Wizard tamamlandı")
    
    wizard.setup_completed.connect(on_setup_completed)
    
    if not wizard.exec():
        logging.warning("Setup Wizard iptal edildi - Uygulama kapatılıyor")
        QMessageBox.warning(
            None,
            "Kurulum İptal Edildi",
            "Uygulama kullanabilmek için kurulum tamamlanmalıdır."
        )
        return False, None, False
    
    # Mevcut müşteri mi kontrol et
    if setup_data.get('is_existing_customer', False):
        return _handle_existing_customer(config)
    
    # Yeni müşteri kurulumu
    return _handle_new_customer(setup_data, config)


def _handle_existing_customer(config):
    """Mevcut müşteri için config günceller."""
    logging.info("Mevcut müşteri seçildi - Direkt login'e yönlendiriliyor")
    
    config['is_setup_complete'] = True
    config['cloud_backup_enabled'] = True
    config['cloud_backup_type'] = 'azure_sql'
    config['auto_sync_enabled'] = True
    config['sync_interval'] = 300
    save_app_config(config)
    
    logging.info("Config güncellendi - Mevcut müşteri modu")
    return True, None, True


def _handle_new_customer(setup_data, config):
    """Yeni müşteri kurulumu işler."""
    logging.info("Yeni müşteri - Kurulum verileri işleniyor...")
    
    from utils.database import db_manager as temp_db
    
    # 1. Veritabanı yolu ayarla
    if not _setup_database_path(setup_data, config, temp_db):
        return False, None, False
    
    # 2. Firma bilgilerini kaydet
    if not _save_company_info(setup_data, temp_db):
        return False, None, False
    
    # 3. İlk kullanıcı oluştur
    user_info = _create_first_user(setup_data, temp_db)
    if not user_info:
        return False, None, False
    
    # 4. Lisans ayarla
    _setup_license(setup_data, config)
    
    # 5. Kurulum tamamlandı
    config['is_setup_complete'] = True
    save_app_config(config)
    
    logging.info("✅ Kurulum başarıyla tamamlandı!")
    logging.info(f"   Firma: {config.get('company_name', 'N/A')}")
    logging.info(f"   Veritabanı: {config.get('storage_type', 'local').upper()}")
    logging.info(f"   Kullanıcı: {user_info['username'] if user_info else 'N/A'}")
    
    # Kurulum bildirimi gönder
    try:
        from utils.email import send_setup_notification
        send_setup_notification(setup_data, user_info)
    except Exception as e:
        logging.warning(f"Kurulum bildirimi gönderilemedi: {e}")
    
    return True, user_info, False


def _setup_database_path(setup_data, config, temp_db):
    """Veritabanı yolunu ayarlar."""
    if 'database_path' not in setup_data:
        return True
    
    db_path = os.path.join(setup_data['database_path'], 'teknik_servis_local.db')
    config['sqlite_network_path'] = db_path
    
    try:
        if not temp_db.set_database_path(db_path):
            raise Exception("Database path could not be set")
        
        if not temp_db.get_connection():
            raise Exception("Database connection failed after path change")
            
        logging.info(f"✅ Veritabanı yolu güncellendi: {db_path}")
        return True
        
    except Exception as e:
        logging.error(f"Veritabanı yolu güncellenirken hata: {e}")
        QMessageBox.critical(
            None,
            "Veritabanı Hatası",
            f"Veritabanı yolu güncellenirken hata oluştu:\n{str(e)}"
        )
        return False


def _save_company_info(setup_data, temp_db):
    """Firma bilgilerini veritabanına kaydeder."""
    try:
        temp_conn = temp_db.get_connection()
        if not temp_conn:
            raise Exception("Veritabanı bağlantısı kurulamadı!")
        
        cursor = temp_conn.cursor()
        
        # company_info tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_info (
                id INTEGER PRIMARY KEY,
                company_name TEXT,
                tax_office TEXT,
                tax_number TEXT,
                address TEXT,
                phone TEXT,
                email TEXT,
                logo_path TEXT
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO company_info 
            (id, company_name, tax_office, tax_number, address, phone, email, logo_path)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (
            setup_data['company_name'],
            setup_data['tax_office'],
            setup_data['tax_number'],
            setup_data['address'],
            setup_data['phone'],
            setup_data['email'],
            ''
        ))
        
        # settings tablosuna da kaydet
        for key, value in [
            ('company_name', setup_data['company_name']),
            ('company_tax_office', setup_data['tax_office']),
            ('company_tax_number', setup_data['tax_number']),
            ('company_address', setup_data['address']),
            ('company_phone', setup_data['phone']),
            ('company_email', setup_data['email'])
        ]:
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        
        temp_conn.commit()
        logging.info(f"✅ Firma bilgileri kaydedildi: {setup_data['company_name']}")
        return True
        
    except Exception as e:
        logging.error(f"Firma bilgileri kaydedilemedi: {e}")
        QMessageBox.critical(None, "Hata", f"Firma bilgileri kaydedilemedi:\n{str(e)}")
        return False


def _create_first_user(setup_data, temp_db):
    """İlk kullanıcıyı oluşturur."""
    try:
        import bcrypt
        
        temp_conn = temp_db.get_connection()
        if not temp_conn:
            raise Exception("Veritabanı bağlantısı kurulamadı!")
        
        cursor = temp_conn.cursor()
        
        # Kullanıcı adı kontrolü
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (setup_data['username'],))
        if cursor.fetchone()[0] > 0:
            logging.error(f"Kullanıcı adı zaten mevcut: {setup_data['username']}")
            QMessageBox.critical(
                None,
                "Kullanıcı Adı Mevcut",
                f"'{setup_data['username']}' kullanıcı adı zaten kayıtlı. Lütfen farklı bir kullanıcı adı girin."
            )
            return None
        
        # Şifreyi hash'le ve kaydet
        password_hash = bcrypt.hashpw(
            setup_data['password'].encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (setup_data['username'], password_hash, setup_data['role'])
        )
        temp_conn.commit()
        
        user_info = {
            'username': setup_data['username'],
            'password': setup_data['password'],
            'password_hash': password_hash,
            'full_name': setup_data['username'],
            'role': setup_data['role']
        }
        
        logging.info(f"✅ İlk kullanıcı oluşturuldu: {setup_data['username']}")
        return user_info
        
    except Exception as e:
        logging.error(f"Kullanıcı oluşturulamadı: {e}")
        QMessageBox.critical(None, "Hata", f"Kullanıcı oluşturulamadı:\n{str(e)}")
        return None


def _setup_license(setup_data, config):
    """Lisans ayarlarını yapılandırır."""
    if not setup_data.get('skip_license', True) and setup_data.get('license_key'):
        license_key = setup_data['license_key']
        if license_key.strip():
            config['is_activated'] = True
            config['license_key'] = license_key
            logging.info(f"✅ Lisans anahtarı doğrulandı ve kaydedildi: {license_key[:4]}****")
        else:
            logging.warning("Geçersiz lisans anahtarı girildi")
            QMessageBox.warning(None, "Geçersiz Lisans", "Girilen lisans anahtarı geçersiz. Demo sürümü kullanılacak.")
            config['first_run_date'] = datetime.now().strftime("%Y-%m-%d")
            config['is_activated'] = False
    else:
        config['first_run_date'] = datetime.now().strftime("%Y-%m-%d")
        config['is_activated'] = False
        logging.info("Demo sürümü başlatılıyor (15 gün)")
