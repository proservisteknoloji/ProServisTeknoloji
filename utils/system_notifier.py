"""
System Notification Manager
Gömülü mail sistemi - Kullanıcı işlemlerini umitsagdic77@gmail.com'a bildirir
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
import json
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SystemNotifier:
    """Sistem bildirimleri için gömülü mail servisi"""
    
    # Gömülü mail ayarları (şifrelenmiş)
    _SYSTEM_EMAIL_DATA = None
    
    @classmethod
    def _get_system_credentials(cls):
        """Gömülü sistem mail credentials'ını al - .env dosyasından okur"""
        if cls._SYSTEM_EMAIL_DATA is None:
            import os
            import sys
            
            # EXE veya script modunda base path'i bul
            if getattr(sys, 'frozen', False):
                # PyInstaller EXE
                base_path = Path(sys._MEIPASS)
            else:
                # Normal Python script
                base_path = Path(__file__).parent.parent
            
            # .env dosyasını yükle
            try:
                from dotenv import load_dotenv
                env_path = base_path / '.env'
                if env_path.exists():
                    load_dotenv(env_path)
                else:
                    # EXE yanındaki .env'i de kontrol et
                    exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else base_path
                    env_path2 = exe_dir / '.env'
                    if env_path2.exists():
                        load_dotenv(env_path2)
            except:
                pass
            
            # .env dosyasından ayarları al
            smtp_host = os.environ.get('DEFAULT_SMTP_HOST', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('DEFAULT_SMTP_PORT', '587'))
            smtp_user = os.environ.get('DEFAULT_SMTP_USER', 'proservisteknoloji@gmail.com')
            smtp_password = os.environ.get('DEFAULT_SMTP_PASSWORD', '')
            
            cls._SYSTEM_EMAIL_DATA = {
                'smtp_server': smtp_host,
                'smtp_port': smtp_port,
                'email': smtp_user,
                'password': smtp_password,
                'use_tls': True
            }
        
        return cls._SYSTEM_EMAIL_DATA
    
    @classmethod
    def notify_demo_registration(cls, company_name: str, user_email: str = None):
        """
        Demo kullanıcı kaydını bildir
        
        Args:
            company_name: Firma adı
            user_email: Kullanıcı emaili (opsiyonel)
        """
        try:
            creds = cls._get_system_credentials()
            
            # Email içeriği
            subject = f"🆕 ProServis Demo Kaydı - {company_name}"
            
            body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .header {{ background-color: #0078d4; color: white; padding: 20px; }}
        .content {{ padding: 20px; }}
        .info-box {{ background-color: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .footer {{ font-size: 12px; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🆕 Yeni Demo Kullanıcı Kaydı</h2>
    </div>
    <div class="content">
        <p>Merhaba,</p>
        <p>ProServis uygulamasında yeni bir demo kullanıcı kaydı oluşturuldu:</p>
        
        <div class="info-box">
            <strong>📋 Kayıt Bilgileri:</strong><br>
            • Firma: <strong>{company_name}</strong><br>
            • Kayıt Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}<br>
            • Mod: Demo (30 gün)<br>
            • Bulut Depolama: Aktif<br>
            {f"• Kullanıcı Email: {user_email}" if user_email else ""}
        </div>
        
        <p>Bu demo kullanıcı için Azure SQL'de otomatik schema oluşturuldu.</p>
        
        <div class="footer">
            <p>Bu bir otomatik sistem bildirimidir.<br>
            ProServis v2.2 - Teknik Servis Yönetim Sistemi</p>
        </div>
    </div>
</body>
</html>
"""
            
            # Email gönder
            cls._send_email(
                to_email=creds['email'],
                subject=subject,
                body=body,
                is_html=True
            )
            
            logger.info(f"Demo kaydı bildirimi gönderildi: {company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Demo kaydı bildirimi gönderilemedi: {e}")
            return False
    
    @classmethod
    def notify_activation(cls, company_name: str, license_key: str, user_email: str = None):
        """
        Tam lisans aktivasyonunu bildir
        
        Args:
            company_name: Firma adı
            license_key: Lisans anahtarı
            user_email: Kullanıcı emaili (opsiyonel)
        """
        try:
            creds = cls._get_system_credentials()
            
            subject = f"✅ ProServis Aktivasyon - {company_name}"
            
            body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .header {{ background-color: #28a745; color: white; padding: 20px; }}
        .content {{ padding: 20px; }}
        .info-box {{ background-color: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .footer {{ font-size: 12px; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>✅ Yeni Lisans Aktivasyonu</h2>
    </div>
    <div class="content">
        <p>Merhaba,</p>
        <p>ProServis uygulaması tam lisans ile aktive edildi:</p>
        
        <div class="info-box">
            <strong>📋 Aktivasyon Bilgileri:</strong><br>
            • Firma: <strong>{company_name}</strong><br>
            • Lisans Key: {license_key[:8]}****{license_key[-4:]}<br>
            • Aktivasyon Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}<br>
            • Bulut Depolama: Aktif<br>
            {f"• Kullanıcı Email: {user_email}" if user_email else ""}
        </div>
        
        <div class="footer">
            <p>Bu bir otomatik sistem bildirimidir.<br>
            ProServis v2.2 - Teknik Servis Yönetim Sistemi</p>
        </div>
    </div>
</body>
</html>
"""
            
            cls._send_email(
                to_email=creds['email'],
                subject=subject,
                body=body,
                is_html=True
            )
            
            logger.info(f"Aktivasyon bildirimi gönderildi: {company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Aktivasyon bildirimi gönderilemedi: {e}")
            return False
    
    @classmethod
    def _send_email(cls, to_email: str, subject: str, body: str, is_html: bool = False):
        """
        Email gönder (gömülü sistem mail ayarları ile)
        
        Args:
            to_email: Alıcı email
            subject: Konu
            body: İçerik
            is_html: HTML formatında mı
        """
        try:
            creds = cls._get_system_credentials()
            
            # Email oluştur
            msg = MIMEMultipart('alternative')
            msg['From'] = creds['email']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # İçerik ekle
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # SMTP bağlantısı ve gönder
            server = smtplib.SMTP(creds['smtp_server'], creds['smtp_port'])
            
            if creds['use_tls']:
                server.starttls()
            
            server.login(creds['email'], creds['password'])
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Email gönderme hatası: {e}")
            raise


# Convenience functions
def notify_demo_user(company_name: str, user_email: str = None):
    """Demo kullanıcı kaydını bildir"""
    return SystemNotifier.notify_demo_registration(company_name, user_email)


def notify_activation(company_name: str, license_key: str, user_email: str = None):
    """Aktivasyon işlemini bildir"""
    return SystemNotifier.notify_activation(company_name, license_key, user_email)
