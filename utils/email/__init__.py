# utils/email/__init__.py
"""Email yönetimi ve gönderim modülleri."""

from .smtp_manager import get_smtp_settings, send_email
from .notifications import send_setup_notification, send_password_reminder

__all__ = [
    'get_smtp_settings',
    'send_email',
    'send_setup_notification',
    'send_password_reminder'
]
