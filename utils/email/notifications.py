# utils/email/notifications.py
"""Email bildirimleri (kurulum, şifre hatırlatma vb.)."""

import logging
from typing import Dict
from .smtp_manager import get_smtp_settings, send_email
from .templates import create_setup_notification_template, create_password_reminder_template


def send_setup_notification(setup_data: Dict, user_info: Dict) -> bool:
    """
    Kurulum tamamlandığında geliştiriciye bildirim e-postası gönderir.
    
    Args:
        setup_data: Kurulum verileri (firma bilgileri)
        user_info: Kullanıcı bilgileri (username, password, role)
        
    Returns:
        bool: Gönderim başarı durumu
    """
    try:
        smtp_settings = get_smtp_settings()
        if not smtp_settings:
            logging.warning("SMTP ayarları eksik - kurulum bildirimi gönderilemedi")
            return False
        
        subject = f"ProServis Kurulum Tamamlandı - {setup_data['company_name']}"
        body = create_setup_notification_template(setup_data, user_info)
        developer_email = 'umitsagdic77@gmail.com'
        
        success = send_email(
            recipient=developer_email,
            subject=subject,
            body=body,
            sender_name=setup_data.get('company_name', 'ProServis Kurulum'),
            smtp_settings=smtp_settings,
            async_send=True
        )
        
        if success:
            logging.info("Kurulum bildirimi email gönderildi")
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
