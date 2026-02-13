"""
Aktivasyon anahtarı doğrulama işlemleri için yardımcı modül.

Bu modül, `key_generator.py` tarafından üretilen aktivasyon anahtarlarının
geçerliliğini kontrol etmek için kullanılır.
"""

import hashlib
import logging
logger = logging.getLogger(__name__)
from typing import Optional

# Logging yapılandırması

# DİKKAT: Bu gizli anahtar, `key_generator.py` içindeki anahtar ile birebir aynı olmalıdır.
# Güvenlik notu: Bu anahtarın kod içinde statik olarak bulunması ideal bir pratik değildir.
# Daha güvenli bir sistemde, bu anahtarın güvenli bir şekilde saklanması ve yönetilmesi gerekir.
SECRET_KEY: str = "ProServis_#2025_Kyocera_Antalya_!Kopier_&Validation"

def validate_key(activation_key: Optional[str]) -> bool:
    """
    Girilen bir aktivasyon anahtarının geçerli olup olmadığını kontrol eder.

    Anahtar formatı 'XXXX-XXXX-XXXX-XXXX' şeklinde olmalıdır. İlk 4 karakter
    bir ID'yi, geri kalan 12 karakter ise bu ID ve gizli anahtar ile oluşturulmuş
    bir SHA256 hash'inin ilk 12 karakterini temsil eder.

    Args:
        activation_key: Kullanıcının girdiği 16 haneli aktivasyon anahtarı.

    Returns:
        Anahtar geçerliyse True, aksi takdirde False.
    """
    if not activation_key:
        logging.warning("Doğrulama için boş bir anahtar girildi.")
        return False

    # Girdiyi temizle ve büyük harfe çevir
    key = activation_key.strip().upper()
    
    # Format kontrolü: 4 parça ve her parça 4 karakter olmalı
    parts = key.split('-')
    if len(parts) != 4 or not all(len(part) == 4 for part in parts):
        logging.warning(f"Geçersiz anahtar formatı: {key}")
        return False
        
    try:
        # Anahtarın parçalarını ayır
        flat_key = "".join(parts)
        id_part_str = flat_key[:4]
        hash_part_from_key = flat_key[4:]
        
        # ID kısmını sayıya çevir
        unique_id = int(id_part_str)
    except (ValueError, IndexError) as e:
        logging.error(f"Anahtar parçalara ayrılamadı veya ID dönüştürülemedi: {key} - Hata: {e}")
        return False

    # Doğrulama için beklenen hash'i yeniden oluştur
    try:
        seed = f"{unique_id}-{SECRET_KEY}"
        hasher = hashlib.sha256()
        hasher.update(seed.encode('utf-8'))
        full_hash = hasher.hexdigest().upper()
        
        # Üretilen hash'in ilgili kısmını al
        expected_hash_part = full_hash[:12]
        
        # Kullanıcının girdiği anahtarın hash kısmı ile beklenen hash eşleşiyor mu?
        is_valid = hash_part_from_key == expected_hash_part
        if is_valid:
            logging.info(f"Anahtar başarıyla doğrulandı (ID: {unique_id}).")
        else:
            logging.warning(f"Anahtar doğrulaması başarısız oldu (ID: {unique_id}). Beklenen hash uyuşmuyor.")
        
        return is_valid
    except Exception as e:
        logging.critical(f"Hash oluşturma sırasında beklenmedik bir hata oluştu: {e}", exc_info=True)
        return False

# --- Örnek Kullanım ve Test ---
if __name__ == '__main__':
    logger.info("Aktivasyon anahtarı doğrulama testi başlatılıyor...")
    
    # Örnek geçerli anahtarlar (key_generator.py ile üretilmiş)
    valid_key_1 = "0001-443B-2767-1647"
    valid_key_2 = "0500-D09D-A532-6A6F"
    
    # Örnek geçersiz anahtarlar
    invalid_key_1 = "0001-XXXX-YYYY-ZZZZ"  # Rastgele hash
    invalid_key_2 = "abcd-efgh-ijkl-mnop"  # Yanlış format
    invalid_key_3 = "1234-5678-9012-3456"  # Geçerli format ama yanlış hash
    empty_key = ""
    none_key = None

    # Test senaryoları
    test_cases = {
        valid_key_1: True,
        valid_key_2: True,
        invalid_key_1: False,
        invalid_key_2: False,
        invalid_key_3: False,
        empty_key: False,
        str(none_key): False, # None'ı str olarak test et
    }

    all_passed = True
    for key_to_test, expected_result in test_cases.items():
        # None'ı doğrudan geçirmek için özel durum
        actual_key = None if key_to_test == "None" else key_to_test
        result = validate_key(actual_key)
        status = "BAŞARILI" if result == expected_result else "BAŞARISIZ"
        logger.info(f"'{key_to_test}' testi: Beklenen={expected_result}, Alınan={result} -> {status}")
        if result != expected_result:
            all_passed = False
            
    logger.info("\nTest tamamlandı.")
    if all_passed:
        logger.info("Tüm testler başarıyla geçti!")
    else:
        logger.info("Bazı testler başarısız oldu!")

