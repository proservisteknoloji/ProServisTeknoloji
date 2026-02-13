"""
Döviz kuru bilgilerini Türkiye Cumhuriyet Merkez Bankası (TCMB) üzerinden
almak için yardımcı fonksiyonlar içerir.
"""
import requests
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
import logging
import time

# Logger'ı ayarla

_CACHED_RATES: dict[str, Decimal] | None = None
_CACHED_AT: float | None = None
_CACHE_TTL_SECONDS = 300  # 5 dakika


def get_exchange_rates(force_refresh: bool = False) -> dict[str, Decimal]:
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
    global _CACHED_RATES, _CACHED_AT

    now = time.time()
    if not force_refresh and _CACHED_RATES and _CACHED_AT and (now - _CACHED_AT) < _CACHE_TTL_SECONDS:
        return _CACHED_RATES

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
        logging.info(f"OK: Guncel kurlar cekildi ({timestamp}, TCMB Tarih: {tarih}): USD={rates.get('USD', 'N/A')}, EUR={rates.get('EUR', 'N/A')}")
        _CACHED_RATES = rates
        _CACHED_AT = now
        return rates

    except (requests.exceptions.RequestException, ET.ParseError, InvalidOperation, Exception) as e:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.error(f"WARN: TCMB kurlari alinamadi ({timestamp}). Hata: {type(e).__name__}: {e}")
        logging.warning("WARN: Varsayilan kurlar kullanilacak: USD=30.0, EUR=35.0")

        # Hata durumunda varsa cache'i dondur
        if _CACHED_RATES:
            return _CACHED_RATES

        # Hata durumunda varsay??lan (yakla????k) kurlar?? d??nd??r
        return {
            'TL': Decimal('1.0'),
            'USD': Decimal('30.0'),
            'EUR': Decimal('35.0')
        }

