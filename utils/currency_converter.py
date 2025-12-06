"""
Döviz kuru bilgilerini Türkiye Cumhuriyet Merkez Bankası (TCMB) üzerinden
almak için yardımcı fonksiyonlar içerir.
"""
import requests
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
import logging

# Logger'ı ayarla
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_exchange_rates() -> dict[str, Decimal]:
    """
    TCMB'den güncel USD ve EUR döviz alış kurlarını çeker.

    Returns:
        dict[str, Decimal]: Para birimi kodlarını (USD, EUR, TL) ve Decimal türünde
                            kur değerlerini içeren bir sözlük.
                            Başarısız olursa boş bir sözlük döner.
    
    Raises:
        requests.exceptions.RequestException: Ağ hatası veya HTTP hata durumu oluşursa.
        ET.ParseError: XML verisi bozuksa.
        Exception: Diğer beklenmedik hatalar için.
    """
    rates = {'TL': Decimal('1.0')}
    url = "https://www.tcmb.gov.tr/kurlar/today.xml"

    try:
        logging.info(f"TCMB'den döviz kurları çekiliyor: {url}")
        response = requests.get(url, timeout=5)  # Timeout'u 5 saniyeye düşür
        response.raise_for_status()  # HTTP 2xx dışındaki durumlar için hata fırlatır

        root = ET.fromstring(response.content)
        
        # Tarih bilgisini al
        tarih = root.get('Tarih', 'Bilinmiyor')
        
        usd_rate_str = root.findtext("./Currency[@Kod='USD']/ForexBuying")
        if usd_rate_str:
            rates['USD'] = Decimal(usd_rate_str)
        else:
            logging.warning("USD kuru XML'de bulunamadı")
            
        eur_rate_str = root.findtext("./Currency[@Kod='EUR']/ForexBuying")
        if eur_rate_str:
            rates['EUR'] = Decimal(eur_rate_str)
        else:
            logging.warning("EUR kuru XML'de bulunamadı")
        
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"✓ Güncel kurlar başarıyla çekildi ({timestamp}, TCMB Tarih: {tarih}): USD={rates.get('USD', 'N/A')}, EUR={rates.get('EUR', 'N/A')}")
        return rates

    except (requests.exceptions.RequestException, ET.ParseError, InvalidOperation, Exception) as e:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.error(f"⚠️ Döviz kurları TCMB'den alınamadı ({timestamp}). Hata: {type(e).__name__}: {e}")
        logging.warning(f"⚠️ VARSAYILAN KURLAR KULLANILACAK: USD=30.0, EUR=35.0 - Bu kurlar güncel olmayabilir!")
        
        # Hata durumunda varsayılan (yaklaşık) kurları döndür
        return {
            'TL': Decimal('1.0'),
            'USD': Decimal('30.0'),
            'EUR': Decimal('35.0')
        }
