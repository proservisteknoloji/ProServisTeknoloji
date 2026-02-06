# utils/email/templates.py
"""Email HTML template'leri."""

from typing import Dict


def create_setup_notification_template(setup_data: Dict, user_info: Dict) -> str:
    """Kurulum bildirimi email template'i."""
    company_name = setup_data.get('company_name', 'ProServis')
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Hoş Geldiniz {company_name}!</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">ProServis Kurulumunuz Başarıyla Tamamlandı</p>
        </div>

        <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Firma Bilgileri</h2>

            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; width: 150px;">Şirket Adı:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{company_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Adres:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{setup_data.get('address', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Telefon:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{setup_data.get('phone', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">E-posta:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{setup_data.get('email', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Vergi Dairesi:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{setup_data.get('tax_office', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Vergi No:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{setup_data.get('tax_number', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-weight: bold;">Depolama Tipi:</td>
                    <td style="padding: 10px; color: #667eea; font-weight: bold;">{setup_data.get('storage_type', 'local').upper()}</td>
                </tr>
            </table>

            <h3 style="color: #333;">Sistem Yöneticisi Bilgileri</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; width: 150px;">Kullanıcı Adı:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{user_info.get('username', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Şifre:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; color: #d32f2f; font-family: monospace;">{user_info.get('password', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-weight: bold;">Rol:</td>
                    <td style="padding: 10px; background: #d4edda; padding: 10px; border-radius: 3px; font-weight: bold;">System Administratör (Tam Yetkili)</td>
                </tr>
            </table>

            <div style="background: #f0f4ff; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
                <h3 style="color: #495057; margin-top: 0;">📋 Sonraki Adımlar</h3>
                <ul style="color: #495057; padding-left: 20px;">
                    <li>Yukarıdaki kullanıcı adı ve şifre ile sisteme giriş yapın</li>
                    <li>Ayarlar menüsünden firma bilgilerinizi güncelleyin</li>
                    <li>SMTP ayarlarını yapılandırarak e-posta gönderim özelliğini etkinleştirin</li>
                    <li>Müşterilerinizi ve cihazlarınızı sisteme ekleyin</li>
                </ul>
            </div>

            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #495057; margin-top: 0;">✅ Kurulum Başarıyla Tamamlandı</h3>
                <p style="margin: 10px 0 0 0; color: #6c757d;">
                    ProServis teknik servis yönetim sistemi artık kullanıma hazır. Sistemi verimli kullanmak için yönetim panelini keşfetmeyi unutmayın.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                <p style="color: #6c757d; margin: 5px 0;">
                    <strong>ProServis v2.2</strong> - Teknik Servis Yönetim Sistemi
                </p>
                <p style="color: #999; margin: 5px 0; font-size: 12px;">
                    Bu otomatik bildirimdir. Kurulum tamamlandığında gönderilmiştir.
                </p>
            </div>
        </div>
    </body>
    </html>
    """


def create_password_reminder_template(username: str, password: str) -> str:
    """Şifre hatırlatma email template'i."""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">🔐 ProServis Şifre Hatırlatma</h1>
        </div>

        <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Şifre Bilgileriniz</h2>

            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">Kullanıcı Adı:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{username}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Şifre:</td>
                        <td style="padding: 10px; font-family: monospace; font-size: 16px; color: #2563EB; font-weight: bold;">{password}</td>
                    </tr>
                </table>
            </div>

            <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 0; color: #856404; font-weight: bold;">
                    ⚠️ Güvenlik Uyarısı: Bu şifreyi kimseyle paylaşmayın ve güvenli bir yerde saklayın.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                <p style="color: #6c757d; margin: 0;">
                    Bu otomatik hatırlatma mesajıdır. Şifre değişikliği için sistem yöneticinizle iletişime geçin.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
