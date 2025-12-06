# utils/device_toner_compatibility.py

"""
Cihaz-Toner uyumluluk sistemi.
Yeni cihazlar eklenirken otomatik toner önerisi ve uyumluluk kontrolü.
"""

import logging
from typing import List, Dict, Any, Optional
import re

# Cihaz modellerinin toner uyumluluk veritabanı
DEVICE_TONER_COMPATIBILITY = {
    # Kyocera ECOSYS M Serisi
    "ECOSYS M 2135": ["TK-1150"],
    "ECOSYS M 2635": ["TK-1150"],
    "ECOSYS M 2735": ["TK-1150"],
    "ECOSYS M 2040": ["TK-1170"],
    "ECOSYS M 2540": ["TK-1170"],
    "ECOSYS M 2640": ["TK-1170"],
    "ECOSYS M 3550": ["TK-3130"],
    "ECOSYS M 3560": ["TK-3130"],
    "ECOSYS M 3145": ["TK-3190"],
    "ECOSYS M 3645": ["TK-3190"],
    "ECOSYS M 5526": ["TK-5240K", "TK-5240C", "TK-5240M", "TK-5240Y"],
    
    # Kyocera ECOSYS P Serisi
    "ECOSYS P 2200": ["TK-1150"],
    "ECOSYS P 2235": ["TK-1150"],
    "ECOSYS P 3055": ["TK-3190"],
    "ECOSYS P 3060": ["TK-3190"],
    "ECOSYS P 5026": ["TK-5240K", "TK-5240C", "TK-5240M", "TK-5240Y"],
    
    # Kyocera TASKalfa Serisi
    "TASKalfa 4500X": ["TK-3300"],
    "TASKalfa 4501i": ["TK-3300"],
    "TASKalfa 5500i": ["TK-3300"],
    "TASKalfa 5501i": ["TK-3300"],
    "TASKalfa 3010i": ["TK-7205"],
    "TASKalfa 3510i": ["TK-7205"],
    
    # Kyocera FS Serisi
    "FS-4200": ["TK-3130"],
    "FS-4300": ["TK-3130"],
    
    # HP LaserJet Serisi (örnek)
    "LaserJet Pro M404": ["CF276A"],
    "LaserJet Pro M428": ["CF276A"],
    "LaserJet Pro P1102": ["CE285A"],
    
    # Canon Serisi (örnek)
    "imageRUNNER 1435": ["C-EXV50"],
    "imageRUNNER ADVANCE C3330": ["C-EXV49"],
}

# Cihaz modellerinin sarf malzeme uyumluluğu
DEVICE_CONSUMABLES_COMPATIBILITY = {
    "ECOSYS M 2135": ["DK-1150", "FK-1150"],
    "ECOSYS M 2635": ["DK-1150", "FK-1150"],
    "ECOSYS M 2735": ["DK-1150", "FK-1150"],
    "TASKalfa 4500X": ["DK-3300", "WT-3300"],
    "TASKalfa 4501i": ["DK-3300", "WT-3300"],
    "TASKalfa 5500i": ["DK-3300", "WT-3300"],
    "TASKalfa 5501i": ["DK-3300", "WT-3300"],
}

def normalize_device_model(model: str) -> str:
    """
    Cihaz modelini normalize eder (büyük/küçük harf, boşluk vb.)
    
    Args:
        model: Ham cihaz modeli
        
    Returns:
        Normalize edilmiş model adı
    """
    if not model:
        return ""
    
    # Küçük harfe çevir ve fazla boşlukları temizle
    normalized = re.sub(r'\s+', ' ', model.strip().upper())
    
    # Yaygın marka kısaltmalarını standardize et
    normalized = normalized.replace('KYOCERA ', '')
    normalized = normalized.replace('HP ', '')
    normalized = normalized.replace('CANON ', '')
    
    return normalized

def find_compatible_toners(device_model: str) -> List[str]:
    """
    Verilen cihaz modeli için uyumlu tonerleri bulur.
    
    Args:
        device_model: Cihaz modeli
        
    Returns:
        Uyumlu toner listesi (part_number)
    """
    normalized_model = normalize_device_model(device_model)
    compatible_toners = []
    
    # Tam eşleşme ara
    for db_model, toners in DEVICE_TONER_COMPATIBILITY.items():
        if normalize_device_model(db_model) == normalized_model:
            compatible_toners.extend(toners)
            break
    
    # Eğer tam eşleşme bulunamadıysa, kısmi eşleşme ara
    if not compatible_toners:
        for db_model, toners in DEVICE_TONER_COMPATIBILITY.items():
            normalized_db_model = normalize_device_model(db_model)
            # Model adının bir kısmı eşleşiyor mu?
            if any(word in normalized_db_model for word in normalized_model.split() if len(word) > 3):
                compatible_toners.extend(toners)
    
    return list(set(compatible_toners))  # Tekrarları kaldır

def find_compatible_consumables(device_model: str) -> List[str]:
    """
    Verilen cihaz modeli için uyumlu sarf malzemelerini bulur.
    
    Args:
        device_model: Cihaz modeli
        
    Returns:
        Uyumlu sarf malzeme listesi (part_number)
    """
    normalized_model = normalize_device_model(device_model)
    compatible_consumables = []
    
    # Tam eşleşme ara
    for db_model, consumables in DEVICE_CONSUMABLES_COMPATIBILITY.items():
        if normalize_device_model(db_model) == normalized_model:
            compatible_consumables.extend(consumables)
            break
    
    # Kısmi eşleşme ara
    if not compatible_consumables:
        for db_model, consumables in DEVICE_CONSUMABLES_COMPATIBILITY.items():
            normalized_db_model = normalize_device_model(db_model)
            if any(word in normalized_db_model for word in normalized_model.split() if len(word) > 3):
                compatible_consumables.extend(consumables)
    
    return list(set(compatible_consumables))

def get_device_compatibility_info(device_model: str, db_manager) -> Dict[str, Any]:
    """
    Cihaz için kapsamlı uyumluluk bilgisini döndürür.
    
    Args:
        device_model: Cihaz modeli
        db_manager: Veritabanı yöneticisi
        
    Returns:
        Uyumluluk bilgileri dictionary'si
    """
    compatible_toner_codes = find_compatible_toners(device_model)
    compatible_consumable_codes = find_compatible_consumables(device_model)
    
    result = {
        'device_model': device_model,
        'normalized_model': normalize_device_model(device_model),
        'compatible_toners': [],
        'compatible_consumables': [],
        'missing_toners': [],
        'missing_consumables': [],
        'suggestions': []
    }
    
    # Tonerleri kontrol et
    for toner_code in compatible_toner_codes:
        stock_item = db_manager.fetch_one(
            "SELECT id, name, part_number, quantity, sale_price, sale_currency FROM stock_items WHERE part_number = ?",
            (toner_code,)
        )
        
        if stock_item:
            result['compatible_toners'].append({
                'part_number': toner_code,
                'name': stock_item['name'],
                'quantity': stock_item['quantity'],
                'price': stock_item['sale_price'],
                'currency': stock_item['sale_currency'],
                'in_stock': True
            })
        else:
            result['missing_toners'].append({
                'part_number': toner_code,
                'in_stock': False
            })
    
    # Sarf malzemelerini kontrol et
    for consumable_code in compatible_consumable_codes:
        stock_item = db_manager.fetch_one(
            "SELECT id, name, part_number, quantity, sale_price, sale_currency FROM stock_items WHERE part_number = ?",
            (consumable_code,)
        )
        
        if stock_item:
            result['compatible_consumables'].append({
                'part_number': consumable_code,
                'name': stock_item['name'],
                'quantity': stock_item['quantity'],
                'price': stock_item['sale_price'],
                'currency': stock_item['sale_currency'],
                'in_stock': True
            })
        else:
            result['missing_consumables'].append({
                'part_number': consumable_code,
                'in_stock': False
            })
    
    # Öneriler oluştur
    if result['missing_toners']:
        result['suggestions'].append(
            f"Eksik tonerler: {', '.join([t['part_number'] for t in result['missing_toners']])}"
        )
    
    if result['missing_consumables']:
        result['suggestions'].append(
            f"Eksik sarf malzemeler: {', '.join([c['part_number'] for c in result['missing_consumables']])}"
        )
    
    if not compatible_toner_codes and not compatible_consumable_codes:
        result['suggestions'].append(
            "Bu cihaz modeli için otomatik uyumluluk bulunamadı. Manuel olarak toner bilgisi ekleyebilirsiniz."
        )
    
    return result

def add_device_toner_compatibility(device_model: str, toner_codes: List[str]) -> bool:
    """
    Yeni cihaz-toner uyumluluğu ekler.
    
    Args:
        device_model: Cihaz modeli
        toner_codes: Uyumlu toner kod listesi
        
    Returns:
        Başarı durumu
    """
    try:
        normalized_model = normalize_device_model(device_model)
        
        # Global dictionary'ye ekle
        DEVICE_TONER_COMPATIBILITY[normalized_model] = toner_codes
        
        logging.info(f"Yeni cihaz-toner uyumluluğu eklendi: {normalized_model} -> {toner_codes}")
        return True
        
    except Exception as e:
        logging.error(f"Cihaz-toner uyumluluğu eklenirken hata: {e}")
        return False

def suggest_toners_for_new_device(device_model: str, db_manager) -> List[Dict[str, Any]]:
    """
    Yeni cihaz için toner önerileri sunar.
    
    Args:
        device_model: Yeni cihaz modeli
        db_manager: Veritabanı yöneticisi
        
    Returns:
        Önerilen toner listesi
    """
    # Önce mevcut uyumluluğu kontrol et
    compatibility_info = get_device_compatibility_info(device_model, db_manager)
    
    if compatibility_info['compatible_toners']:
        return compatibility_info['compatible_toners']
    
    # Benzer cihazlardan öneriler bul
    suggestions = []
    normalized_new_model = normalize_device_model(device_model)
    
    for db_model, toners in DEVICE_TONER_COMPATIBILITY.items():
        normalized_db_model = normalize_device_model(db_model)
        
        # Benzer kelimeler var mı?
        new_words = set(normalized_new_model.split())
        db_words = set(normalized_db_model.split())
        common_words = new_words.intersection(db_words)
        
        if len(common_words) >= 1:  # En az 1 ortak kelime
            for toner_code in toners:
                stock_item = db_manager.fetch_one(
                    "SELECT id, name, part_number, quantity, sale_price, sale_currency FROM stock_items WHERE part_number = ?",
                    (toner_code,)
                )
                
                if stock_item:
                    suggestions.append({
                        'part_number': toner_code,
                        'name': stock_item['name'],
                        'quantity': stock_item['quantity'],
                        'price': stock_item['sale_price'],
                        'currency': stock_item['sale_currency'],
                        'similar_device': db_model,
                        'confidence': len(common_words) / max(len(new_words), len(db_words))
                    })
    
    # Güven skoruna göre sırala
    suggestions.sort(key=lambda x: x['confidence'], reverse=True)
    
    return suggestions[:5]  # En iyi 5 öneriyi döndür