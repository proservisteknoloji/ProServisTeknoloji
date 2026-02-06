# utils/email/smtp_manager.py
"""SMTP ayarları ve email gönderim yönetimi."""

import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Gömülü ProServis desteği SMTP ayarları (kullanıcı görmez)
DEFAULT_SMTP_SETTINGS = {
    'host': 'smtp.gmail.com',
    'port': 587,
    'user': 'proservisteknoloji@gmail.com',
    'password': 'bpnq ruys mase ooef',
    'encryption': 'TLS'
}

# Hata bildirimleri için fallback alıcı
FALLBACK_RECIPIENT = 'proservisteknoloji@gmail.com'


def get_smtp_settings() -> Dict[str, any]:
    """
    Kullanıcı veya varsayılan SMTP ayarlarını döndürür.
    
    Returns:
        dict: SMTP ayarları (host, port, user, password, encryption)
    """
    from utils.settings_manager import load_app_config
    
    config = load_app_config()
    
    # Önce kullanıcının SMTP ayarlarını kontrol et
    user_smtp_settings = {
        'host': config.get('smtp_host', ''),
        'port': config.get('smtp_port', 587),
        'user': config.get('smtp_user', ''),
        'password': config.get('smtp_password', ''),
        'encryption': config.get('smtp_encryption', 'TLS')
    }
    
    # Kullanıcı SMTP ayarları varsa kullan
    if user_smtp_settings['host'] and user_smtp_settings['user'] and user_smtp_settings['password']:
        logging.info("Kullanıcı SMTP ayarları kullanılıyor")
        return user_smtp_settings
    
    # Gömülü ProServis desteği SMTP ayarlarını kullan
    logging.info("Gömülü ProServis SMTP ayarları kullanılıyor")
    return DEFAULT_SMTP_SETTINGS


def send_email(recipient: str, subject: str, body: str, sender_name: str = 'ProServis',
               smtp_settings: Optional[Dict] = None, async_send: bool = True) -> bool:
    """
    Email gönderir (asenkron veya senkron).
    
    Args:
        recipient: Alıcı email adresi
        subject: Email konusu
        body: Email içeriği (HTML)
        sender_name: Gönderen adı
        smtp_settings: SMTP ayarları (None ise otomatik alınır)
        async_send: True ise asenkron, False ise senkron gönderir
        
    Returns:
        bool: Gönderim başarı durumu
    """
    try:
        # SMTP ayarlarını al
        if smtp_settings is None:
            smtp_settings = get_smtp_settings()
        
        if not smtp_settings:
            logging.error("SMTP ayarları bulunamadı")
            # Fallback: gömülü ayarları kullan
            smtp_settings = DEFAULT_SMTP_SETTINGS
            if not smtp_settings:
                return False
        
        message_details = {
            'recipient': recipient,
            'subject': subject,
            'body': body,
            'sender_name': sender_name
        }
        
        if async_send:
            # Asenkron gönderim (EmailThread ile)
            from PyQt6.QtWidgets import QApplication
            from utils.workers import EmailThread
            
            app = QApplication.instance()
            if app:
                email_thread = EmailThread(smtp_settings, message_details)
                email_thread.start()
                email_thread.wait(10000)  # 10 saniye bekle
                
                if email_thread.isFinished():
                    logging.info(f"Email gönderildi (asenkron): {recipient}")
                    return True
                else:
                    logging.warning("Email gönderimi zaman aşımına uğradı")
                    return False
        
        # Senkron gönderim (doğrudan SMTP)
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText(body, 'html', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = smtp_settings['user']
        msg['To'] = recipient
        
        with smtplib.SMTP(smtp_settings['host'], smtp_settings['port']) as server:
            server.starttls()
            server.login(smtp_settings['user'], smtp_settings['password'])
            server.sendmail(smtp_settings['user'], recipient, msg.as_string())
        
        logging.info(f"Email gönderildi (senkron): {recipient}")
        return True
        
    except Exception as e:
        logging.error(f"Email gönderilemedi: {e}")
        return False
