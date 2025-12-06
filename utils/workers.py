"""
Arka plan işlemlerini yönetmek için QThread tabanlı worker sınıfları.

Bu modül, e-posta gönderme ve yapay zeka API'leriyle etkileşim gibi
uzun sürebilecek işlemleri ana uygulama arayüzünü (UI) dondurmadan
ayrı iş parçacıklarında çalıştırmak için sınıflar içerir.
"""

import smtplib
import logging
import unicodedata
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders, policy
from typing import Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

def normalize_email_address(email: str) -> str:
    """
    E-posta adresindeki özel Unicode karakterleri ASCII uyumlu hale getirir.
    """
    if not email:
        return email
    
    try:
        # Unicode combining karakterleri kaldır ve ASCII'ye dönüştür
        normalized = unicodedata.normalize('NFD', email)
        ascii_email = normalized.encode('ascii', 'ignore').decode('ascii')
        return ascii_email
    except Exception as e:
        logging.warning(f"E-posta adresi normalize edilemedi: {email}, hata: {e}")
        return email

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# İsteğe bağlı bağımlılıkları güvenli bir şekilde içe aktar
try:
    from openai import OpenAI, OpenAIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    OpenAIError = None

# Gemini için lazy import - Python 3.13 uyumsuzluğu nedeniyle
GEMINI_AVAILABLE = False
genai = None

try:
    # Lazy import - sadece kullanılacağı zaman yüklenecek
    import importlib.util
    gemini_spec = importlib.util.find_spec("google.generativeai")
    if gemini_spec is not None:
        GEMINI_AVAILABLE = True
        # genai modülü sadece gerektiğinde yüklenecek
    else:
        GEMINI_AVAILABLE = False
except (ImportError, AttributeError, Exception) as e:
    GEMINI_AVAILABLE = False
    genai = None
    # Sadece debug modunda warning göster
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug(f"Google Gemini kütüphanesi mevcut değil: {e}")

try:
    from utils.currency_converter import get_exchange_rates
    CURRENCY_AVAILABLE = True
except ImportError:
    CURRENCY_AVAILABLE = False
    get_exchange_rates = None

try:
    import pandas as pd
    import openpyxl
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    openpyxl = None

class BaseThread(QThread):
    """
    Tüm worker sınıfları için temel bir QThread sınıfı.
    Başarı ve hata sinyallerini standartlaştırır.
    """
    task_finished = pyqtSignal(object)  # Daha genel veri tipleri için object kullan
    task_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

class EmailThread(BaseThread):
    """
    SMTP üzerinden asenkron olarak e-posta gönderen worker.
    """
    def __init__(self, smtp_settings: Dict[str, Any], message_details: Dict[str, Any], parent=None):
        """
        Args:
            smtp_settings: {'host', 'port', 'user', 'password', 'encryption'} içeren sözlük.
            message_details: {'recipient', 'subject', 'body', 'sender_name', 'attachments'} içeren sözlük.
                             attachments: List of {'filename': str, 'data': bytes, 'content_type': str} dicts
        """
        super().__init__(parent)
        self.smtp_settings = smtp_settings
        self.message_details = message_details

    def run(self) -> None:
        """
        E-posta gönderme işlemini başlatır.
        """
        try:
            logging.info(f"E-posta gönderme işlemi başlatılıyor: {self.message_details['recipient']}")

            # E-posta adreslerini normalize et
            recipient_email = normalize_email_address(self.message_details['recipient'])
            sender_email = normalize_email_address(self.smtp_settings['user'])

            attachments = self.message_details.get('attachments', [])

            if attachments:
                # Multipart e-posta oluştur
                msg = MIMEMultipart('mixed', policy=policy.default)
                # HTML body ekle
                html_part = MIMEText(self.message_details['body'], 'html', 'utf-8')
                msg.attach(html_part)
                # Ekleri ekle
                for attachment in attachments:
                    filename = attachment['filename']
                    data = attachment['data']
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    main_type, sub_type = content_type.split('/', 1)
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(data)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
            else:
                # Basit HTML e-posta
                msg = MIMEText(self.message_details['body'], 'html', 'utf-8', policy=policy.default)

            msg['Subject'] = self.message_details['subject']

            # Gönderen ismini firma adı olarak ayarla
            sender_name = self.message_details.get('sender_name', '')
            if sender_name:
                msg['From'] = sender_name
            else:
                msg['From'] = sender_email

            msg['To'] = recipient_email

            use_ssl = self.smtp_settings.get('encryption') == 'SSL'
            smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

            with smtp_class(self.smtp_settings['host'], self.smtp_settings['port'], timeout=20) as server:
                server.set_debuglevel(0)  # Hata ayıklama için 1 yapılabilir
                if not use_ssl:
                    server.starttls()
                server.login(sender_email, self.smtp_settings['password'])
                # Normalize edilmiş e-posta adresleri kullan
                server.sendmail(sender_email, recipient_email, msg.as_string())

            success_message = f"E-posta başarıyla gönderildi.\nAlıcı: {recipient_email}"
            logging.info(success_message)
            self.task_finished.emit(success_message)

        except smtplib.SMTPAuthenticationError as e:
            error_message = f"SMTP kimlik doğrulama hatası: Kullanıcı adı veya şifre yanlış. (Hata: {e})"
            logging.error(error_message)
            self.task_error.emit(error_message)
        except smtplib.SMTPServerDisconnected as e:
            error_message = f"Sunucu bağlantısı kesildi. Lütfen ayarları ve internet bağlantınızı kontrol edin. (Hata: {e})"
            logging.error(error_message)
            self.task_error.emit(error_message)
        except ConnectionRefusedError as e:
            error_message = f"Bağlantı reddedildi. SMTP sunucusu veya port ayarları yanlış olabilir. (Hata: {e})"
            logging.error(error_message)
            self.task_error.emit(error_message)
        except TimeoutError as e:
            error_message = f"Bağlantı zaman aşımına uğradı. Sunucuya erişilemiyor veya ağ yavaş. (Hata: {e})"
            logging.error(error_message)
            self.task_error.emit(error_message)
        except Exception as e:
            error_message = f"E-posta gönderilirken genel bir hata oluştu: {e}"
            logging.error(error_message, exc_info=True)
            self.task_error.emit(error_message)


class AIThread(BaseThread):
    """
    OpenAI veya Google Gemini API'sine asenkron olarak istek gönderen worker.
    """
    def __init__(self, provider: str, api_key: str, prompt: str, parent=None):
        """
        Args:
            provider: "OpenAI" veya "Google Gemini".
            api_key: İlgili servis için API anahtarı.
            prompt: Yapay zeka modeline gönderilecek olan kullanıcı sorusu.
        """
        super().__init__(parent)
        self.provider = provider
        self.api_key = api_key
        
        # Modele rol ve talimatlar veren temel sistem prompt'u.
        self.base_prompt = (
            "Sen, fotokopi makineleri ve yazıcılar konusunda uzman bir teknik servis asistanı olan ProServis AI Asistanısın. "
            "Görevin, teknik servis sorunları için adımlar halinde, net ve anlaşılır çözüm önerileri sunmaktır. "
            "Cevapların her zaman kısa ve profesyonel olmalı. Çözüm adımlarını numaralandırılmış liste (1., 2., 3. gibi) formatında ver. "
            "Eğer bir sorunun çözümünü bilmiyorsan veya sorun donanımsal müdahale gerektiriyorsa, 'Bu sorun için yerinde servis veya deneyimli bir teknisyen müdahalesi gerekmektedir.' şeklinde cevap ver. "
            "Sana sorulan asıl soru şu: "
        )
        self.full_prompt = self.base_prompt + prompt

    def run(self) -> None:
        """
        Seçilen yapay zeka sağlayıcısına isteği gönderir.
        """
        logging.info(f"{self.provider} API'sine istek gönderiliyor...")
        try:
            if self.provider == "OpenAI":
                if not OPENAI_AVAILABLE:
                    raise ImportError("OpenAI kütüphanesi yüklü değil.")
                self._run_openai()
            
            elif self.provider == "Google Gemini":
                if not GEMINI_AVAILABLE:
                    raise ImportError("Google Gemini (google.generativeai) kütüphanesi yüklü değil veya Python 3.13 ile uyumsuz.")
                self._run_gemini()
            
            else:
                raise ValueError(f"Geçersiz AI sağlayıcısı: {self.provider}")

        except (ValueError, ImportError, Exception) as e:
            error_message = f"API Hatası ({self.provider}): {e}"
            logging.error(error_message, exc_info=True)
            self.task_error.emit(error_message)

    def _run_openai(self):
        """OpenAI API'sini çalıştırır."""
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": self.full_prompt}],
            max_tokens=350,
            temperature=0.2  # Daha tutarlı ve daha az rastgele cevaplar için
        )
        response_text = response.choices[0].message.content.strip()
        logging.info("OpenAI'den yanıt alındı.")
        self.task_finished.emit(response_text)

    def _run_gemini(self):
        """Google Gemini API'sini çalıştırır."""
        # Lazy import - sadece burada yükle
        try:
            import google.generativeai as genai_module
        except ImportError as e:
            raise ImportError(f"Google Gemini kütüphanesi yüklenemedi (Python 3.13 uyumsuzluk olabilir): {e}")
        
        # API key'i temizle (boşluk ve özel karakterleri kaldır)
        clean_api_key = self.api_key.strip()
        genai_module.configure(api_key=clean_api_key)
        
        generation_config = genai_module.GenerationConfig(
            temperature=0.2,
            top_p=0.9,
            top_k=30
        )
        
        # Gemini Pro modeli kullan (0.3.2 versiyonunda çalışıyor)
        model = genai_module.GenerativeModel(
            model_name='models/gemini-pro',
            generation_config=generation_config
        )
        
        response = model.generate_content(self.full_prompt)
        response_text = response.text.strip()
        logging.info("Google Gemini'den yanıt alındı.")
        self.task_finished.emit(response_text)


class CurrencyRateThread(BaseThread):
    """
    Merkez bankasından döviz kurlarını asenkron olarak çeken worker.
    """
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager

    def run(self) -> None:
        """
        Döviz kuru alma işlemini başlatır.
        """
        try:
            if not CURRENCY_AVAILABLE:
                raise ImportError("Döviz kuru modülü veya bağımlılıkları bulunamadı.")
            
            rates = get_exchange_rates()
            if rates:
                self.db.update_exchange_rates(rates)
                logging.info(f"Güncel kurlar çekildi: USD={rates.get('USD', 'N/A')}, EUR={rates.get('EUR', 'N/A')}")
                self.task_finished.emit(rates)
            else:
                self.task_error.emit("Kurlar alınamadı ancak hata oluşmadı.")

        except Exception as e:
            error_message = f"Kur bilgileri çekilemedi (Ağ Hatası): {e}"
            logging.error(error_message)
            self.task_error.emit(error_message)
