# utils/kyocera_compatibility_scraper.py

"""
Kyocera toner-cihaz uyumluluk verilerini işleyen modül.
Web sitesinden çekilen veriler ile otomatik eşleştirme yapar.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional

# Kyocera uyumluluk verilerini içeren sözlük
KYOCERA_COMPATIBILITY_DATA = {
    "TK-17": {
        "compatible_devices": ["FS-1000", "FS-1010", "FS-1010N", "FS-1050", "FS-1010+"],
        "print_capacity": 6000,
        "type": "Siyah-Beyaz"
    },
    "TK-18": {
        "compatible_devices": ["FS-1020D", "FS-1020N"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-50A": {
        "compatible_devices": ["FS-1900"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-50X": {
        "compatible_devices": ["FS-1900"],
        "print_capacity": 19000,
        "type": "Siyah-Beyaz"
    },
    "TK-55": {
        "compatible_devices": ["FS-1920"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-60": {
        "compatible_devices": ["FS-1800", "FS-3800"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-65": {
        "compatible_devices": ["FS-3820N", "FS-3830N"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-70": {
        "compatible_devices": ["FS-9520DN", "FS-9120DN"],
        "print_capacity": 40000,
        "type": "Siyah-Beyaz"
    },
    "TK-100": {
        "compatible_devices": ["FS-KM-1500"],
        "print_capacity": 6000,
        "type": "Siyah-Beyaz"
    },
    "TK-110": {
        "compatible_devices": ["FS-720", "FS-820", "FS-920", "FS-1116MFP", "FS-1016MFP", "FS-1116MFP"],
        "print_capacity": 6000,
        "type": "Siyah-Beyaz"
    },
    "TK-120": {
        "compatible_devices": ["FS-1030"],
        "print_capacity": 6000,
        "type": "Siyah-Beyaz"
    },
    "TK-130": {
        "compatible_devices": ["FS-1300D", "FS-1300DN", "FS-1128MFP"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-135": {
        "compatible_devices": ["KM-2810", "KM-2810DP", "KM-2820"],
        "print_capacity": 6000,
        "type": "Siyah-Beyaz"
    },
    "TK-140": {
        "compatible_devices": ["FS-1100D"],
        "print_capacity": 4500,
        "type": "Siyah-Beyaz"
    },
    "TK-160": {
        "compatible_devices": ["FS-1120D"],
        "print_capacity": 4500,
        "type": "Siyah-Beyaz"
    },
    "TK-170": {
        "compatible_devices": ["FS-1320D", "FS-1370DN"],
        "print_capacity": 6000,
        "type": "Siyah-Beyaz"
    },
    "TK-310": {
        "compatible_devices": ["FS-2000D", "FS-3820N", "FS-3830N", "FS-4000DN"],
        "print_capacity": 10000,
        "type": "Siyah-Beyaz"
    },
    "TK-320": {
        "compatible_devices": ["FS-3900DN", "FS-4000DN"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-330": {
        "compatible_devices": ["FS-4000DN"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-340": {
        "compatible_devices": ["FS-2020D"],
        "print_capacity": 8000,
        "type": "Siyah-Beyaz"
    },
    "TK-350": {
        "compatible_devices": ["FS-3920DN"],
        "print_capacity": 10000,
        "type": "Siyah-Beyaz"
    },
    "TK-360": {
        "compatible_devices": ["FS-4020D"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-410": {
        "compatible_devices": ["KM-1635", "KM-2035", "KM-1650", "KM-2050"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-418": {
        "compatible_devices": ["KM-1620", "KM-2035", "KM-2050"],
        "print_capacity": 18000,
        "type": "Siyah-Beyaz"
    },
    "TK-420": {
        "compatible_devices": ["KM-2250"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-428": {
        "compatible_devices": ["KM-2250", "KM-1635"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-435": {
        "compatible_devices": ["TASKalfa-180", "TASKalfa-181", "TASKalfa-220", "TASKalfa-221"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-438": {
        "compatible_devices": ["KM-1648"],
        "print_capacity": 10000,
        "type": "Siyah-Beyaz"
    },
    "TK-440": {
        "compatible_devices": ["FS-6950DN"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-450": {
        "compatible_devices": ["FS-6970DN"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-448": {
        "compatible_devices": ["TASKalfa-180", "TASKalfa-181", "TASKalfa-220", "TASKalfa-221"],
        "print_capacity": 10000,
        "type": "Siyah-Beyaz"
    },
    "TK-458": {
        "compatible_devices": ["TASKalfa-180", "TASKalfa-181", "TASKalfa-220", "TASKalfa-221"],
        "print_capacity": 10000,
        "type": "Siyah-Beyaz"
    },
    "TK-475": {
        "compatible_devices": ["TASKalfa-475", "TASKalfa-476", "TASKalfa-478", "TASKalfa-479"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-601": {
        "compatible_devices": ["KM-4530", "KM-5530", "KM-7530", "KM-6330"],
        "print_capacity": 30000,
        "type": "Siyah-Beyaz"
    },
    "TK-675": {
        "compatible_devices": ["KM-2540", "KM-2560", "KM-3040", "KM-3060", "TASKalfa 300i"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-685": {
        "compatible_devices": ["TASKalfa-300i", "TASKalfa-400i"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-710": {
        "compatible_devices": ["FS-9130DN", "FS-9530DN"],
        "print_capacity": 40000,
        "type": "Siyah-Beyaz"
    },
    "TK-715": {
        "compatible_devices": ["KM-3050", "KM-4050", "KM-5050", "TASKalfa-420i", "TASKalfa-520i"],
        "print_capacity": 40000,
        "type": "Siyah-Beyaz"
    },
    "TK-725": {
        "compatible_devices": ["TASKalfa 420i", "TASKalfa 450i"],
        "print_capacity": 40000,
        "type": "Siyah-Beyaz"
    },
    "TK-1100": {
        "compatible_devices": ["FS-1110MFP", "FS-1024MFP", "FS-1124MFP"],
        "print_capacity": 2100,
        "type": "Siyah-Beyaz"
    },
    "TK-1110": {
        "compatible_devices": ["FS-1020MFP", "FS-1040", "FS-1120MFP"],
        "print_capacity": 2500,
        "type": "Siyah-Beyaz"
    },
    "TK-1115": {
        "compatible_devices": ["FS-1041", "FS-1220MFP"],
        "print_capacity": 1600,
        "type": "Siyah-Beyaz"
    },
    "TK-1120": {
        "compatible_devices": ["FS-1025MFP", "FS-1060", "FS-1125MFP"],
        "print_capacity": 3000,
        "type": "Siyah-Beyaz"
    },
    "TK-1125": {
        "compatible_devices": ["FS-1061", "FS-1320MFP", "FS-1325MFP"],
        "print_capacity": 2100,
        "type": "Siyah-Beyaz"
    },
    "TK-1130": {
        "compatible_devices": ["FS-1030MFP", "FS-1130MFP"],
        "print_capacity": 3000,
        "type": "Siyah-Beyaz"
    },
    "TK-1140": {
        "compatible_devices": ["FS-1035MFP", "FS-1135MFP"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-1150": {
        "compatible_devices": ["ECOSYS P2235DN", "ECOSYS P2235DW", "ECOSYS M2135dn", "ECOSYS M2635DN", "ECOSYS M2735DW"],
        "print_capacity": 3000,
        "type": "Siyah-Beyaz"
    },
    "TK-1160": {
        "compatible_devices": ["ECOSYS P2040DN", "ECOSYS P2040DW"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-1170": {
        "compatible_devices": ["ECOSYS M2040dn", "ECOSYS M2540dn", "ECOSYS M2640idw"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-1505": {
        "compatible_devices": ["KM-1505", "KM-1510", "KM-1810"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-1530": {
        "compatible_devices": ["KM-1525", "KM-1530", "KM-1570", "KM-2030", "KM-2070"],
        "print_capacity": 10000,
        "type": "Siyah-Beyaz"
    },
    "TK-2530": {
        "compatible_devices": ["KM-2530", "KM-3035", "KM-4035", "KM-5035"],
        "print_capacity": 34000,
        "type": "Siyah-Beyaz"
    },
    "TK-3035": {
        "compatible_devices": ["KM-2530", "KM-3031", "KM-3035", "KM-3530", "KM-4030", "KM-4035", "KM-5035"],
        "print_capacity": 40000,
        "type": "Siyah-Beyaz"
    },
    "TK-3100": {
        "compatible_devices": ["FS-2100", "FS-4100", "FS-4200", "FS-4300"],
        "print_capacity": 12500,
        "type": "Siyah-Beyaz"
    },
    "TK-3110": {
        "compatible_devices": ["FS-4100", "FS-4200", "FS-4300"],
        "print_capacity": 15500,
        "type": "Siyah-Beyaz"
    },
    "TK-3120": {
        "compatible_devices": ["FS-4200DN"],
        "print_capacity": 21000,
        "type": "Siyah-Beyaz"
    },
    "TK-3130": {
        "compatible_devices": ["FS-4200", "FS-4300"],
        "print_capacity": 25000,
        "type": "Siyah-Beyaz"
    },
    "TK-3150": {
        "compatible_devices": ["ECOSYS M3040idn", "ECOSYS M3540idn"],
        "print_capacity": 14500,
        "type": "Siyah-Beyaz"
    },
    "TK-3160": {
        "compatible_devices": ["ECOSYS P3045DN", "ECOSYS P3050DN", "ECOSYS P3055DN", "ECOSYS P3060DN"],
        "print_capacity": 12500,
        "type": "Siyah-Beyaz"
    },
    "TK-3170": {
        "compatible_devices": ["ECOSYS P3050DN", "ECOSYS P3055DN", "ECOSYS P3060DN"],
        "print_capacity": 15500,
        "type": "Siyah-Beyaz"
    },
    "TK-3190": {
        "compatible_devices": ["ECOSYS P3055DN", "ECOSYS P3060DN"],
        "print_capacity": 25000,
        "type": "Siyah-Beyaz"
    },
    "TK-3300": {
        "compatible_devices": ["TASKalfa 4500X"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-4105": {
        "compatible_devices": ["TASKalfa 1800", "TASKalfa 1801", "TASKalfa 2200", "TASKalfa 2201"],
        "print_capacity": 18000,
        "type": "Siyah-Beyaz"
    },
    "TK-4108": {
        "compatible_devices": ["TASKalfa 1800", "TASKalfa 1801", "TASKalfa 2200", "TASKalfa 2201"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-4128": {
        "compatible_devices": ["TASKalfa 2010", "TASKalfa 2011"],
        "print_capacity": 7200,
        "type": "Siyah-Beyaz"
    },
    "TK-4138": {
        "compatible_devices": ["TASKalfa 2210", "TASKalfa 2211"],
        "print_capacity": 18000,
        "type": "Siyah-Beyaz"
    },
    "TK-6105": {
        "compatible_devices": ["TASKalfa 3010i"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-6108": {
        "compatible_devices": ["ECOSYS M4028idn"],
        "print_capacity": 18000,
        "type": "Siyah-Beyaz"
    },
    "TK-6115": {
        "compatible_devices": ["ECOSYS M4125", "ECOSYS M4132"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    "TK-6305": {
        "compatible_devices": ["TASKalfa 3500i", "TASKalfa 4500i", "TASKalfa 5500i"],
        "print_capacity": 35000,
        "type": "Siyah-Beyaz"
    },
    "TK-6325": {
        "compatible_devices": ["TASKalfa 4002i", "TASKalfa 5002i", "TASKalfa 6002i"],
        "print_capacity": 35000,
        "type": "Siyah-Beyaz"
    },
    "TK-6725": {
        "compatible_devices": ["TASKalfa 7002i", "TASKalfa 8002i"],
        "print_capacity": 70000,
        "type": "Siyah-Beyaz"
    },
    "TK-7105": {
        "compatible_devices": ["TASKalfa 3010i"],
        "print_capacity": 20000,
        "type": "Siyah-Beyaz"
    },
    "TK-7205": {
        "compatible_devices": ["TASKalfa 3510i"],
        "print_capacity": 35000,
        "type": "Siyah-Beyaz"
    },
    "TK-7300": {
        "compatible_devices": ["P4040dn"],
        "print_capacity": 15000,
        "type": "Siyah-Beyaz"
    },
    # Renkli tonerler
    "TK-500K": {
        "compatible_devices": ["FS-C5016N"],
        "print_capacity": 8000,
        "type": "Siyah"
    },
    "TK-500C": {
        "compatible_devices": ["FS-C5016N"],
        "print_capacity": 8000,
        "type": "Cyan"
    },
    "TK-500M": {
        "compatible_devices": ["FS-C5016N"],
        "print_capacity": 8000,
        "type": "Magenta"
    },
    "TK-500Y": {
        "compatible_devices": ["FS-C5016N"],
        "print_capacity": 8000,
        "type": "Yellow"
    },
    "TK-5240K": {
        "compatible_devices": ["ECOSYS M5526cdw", "ECOSYS P5026cdw", "ECOSYS P5026"],
        "print_capacity": 4000,
        "type": "Siyah"
    },
    "TK-5240C": {
        "compatible_devices": ["ECOSYS M5526cdw", "ECOSYS P5026cdw", "ECOSYS P5026"],
        "print_capacity": 3000,
        "type": "Cyan"
    },
    "TK-5240M": {
        "compatible_devices": ["ECOSYS M5526cdw", "ECOSYS P5026cdw", "ECOSYS P5026"],
        "print_capacity": 3000,
        "type": "Magenta"
    },
    "TK-5240Y": {
        "compatible_devices": ["ECOSYS M5526cdw", "ECOSYS P5026cdw", "ECOSYS P5026"],
        "print_capacity": 3000,
        "type": "Yellow"
    }
}


def normalize_device_name(device_name: str) -> str:
    """Cihaz adını normalize eder."""
    if not device_name:
        return ""
    
    # Temizleme işlemleri
    normalized = device_name.strip().upper()
    
    # PRINTER, COPIER kelimelerini kaldır
    normalized = re.sub(r'\b(PRINTER|COPIER)\s+', '', normalized)
    
    # Fazla boşlukları temizle
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Kyocera prefix'lerini kaldır
    normalized = re.sub(r'^(KYOCERA\s+)?', '', normalized)
    
    return normalized.strip()


def find_compatible_toners_for_device(device_name: str) -> List[Dict]:
    """Verilen cihaz için uyumlu tonerleri bulur."""
    normalized_device = normalize_device_name(device_name)
    compatible_toners = []
    
    for toner_code, toner_info in KYOCERA_COMPATIBILITY_DATA.items():
        for compatible_device in toner_info["compatible_devices"]:
            normalized_compatible = normalize_device_name(compatible_device)
            
            # Fuzzy matching
            if (normalized_device in normalized_compatible or 
                normalized_compatible in normalized_device or
                _similarity_match(normalized_device, normalized_compatible)):
                
                compatible_toners.append({
                    "toner_code": toner_code,
                    "toner_name": f"TK-{toner_code.replace('TK-', '')} TONER",
                    "color_type": toner_info["type"],
                    "print_capacity": toner_info["print_capacity"],
                    "compatible_device": compatible_device,
                    "confidence": _calculate_confidence(normalized_device, normalized_compatible)
                })
                break
    
    # Güven skoruna göre sırala
    compatible_toners.sort(key=lambda x: x["confidence"], reverse=True)
    
    return compatible_toners


def _similarity_match(device1: str, device2: str) -> bool:
    """İki cihaz adı arasında benzerlik kontrolü yapar."""
    # Temel model numarası eşleştirmesi
    model_pattern = r'(\d+[A-Z]*)'
    
    models1 = re.findall(model_pattern, device1)
    models2 = re.findall(model_pattern, device2)
    
    for model1 in models1:
        for model2 in models2:
            if model1 == model2:
                return True
    
    return False


def _calculate_confidence(device1: str, device2: str) -> float:
    """İki cihaz adı arasındaki benzerlik skorunu hesaplar."""
    if device1 == device2:
        return 1.0
    
    if device1 in device2 or device2 in device1:
        return 0.8
    
    # Model numarası eşleşmesi
    if _similarity_match(device1, device2):
        return 0.6
    
    return 0.3


def get_stock_compatible_toners(device_name: str, db) -> List[Dict]:
    """Stokta bulunan uyumlu tonerleri döndürür."""
    compatible_toners = find_compatible_toners_for_device(device_name)
    stock_toners = []
    
    for toner in compatible_toners:
        # Stokta var mı kontrol et
        query = """
        SELECT id, name, part_number, quantity, sale_price, sale_currency 
        FROM stock_items 
        WHERE part_number LIKE ? AND quantity > 0 AND item_type = 'Toner'
        """
        
        # TK-3300 gibi pattern'leri ara
        search_pattern = f"%{toner['toner_code']}%"
        stock_items = db.fetch_all(query, (search_pattern,))
        
        for stock_item in stock_items:
            stock_toners.append({
                "stock_id": stock_item["id"],
                "name": stock_item["name"],
                "part_number": stock_item["part_number"],
                "quantity": stock_item["quantity"],
                "sale_price": stock_item["sale_price"],
                "sale_currency": stock_item["sale_currency"],
                "toner_code": toner["toner_code"],
                "color_type": toner["color_type"],
                "print_capacity": toner["print_capacity"],
                "confidence": toner["confidence"]
            })
    
    return stock_toners


def suggest_missing_toners_for_device(device_name: str, db) -> List[Dict]:
    """Cihaz için uyumlu ama stokta olmayan tonerleri önerir."""
    all_compatible = find_compatible_toners_for_device(device_name)
    stock_compatible = get_stock_compatible_toners(device_name, db)
    
    # Stokta bulunan toner kodları
    stock_codes = {item["toner_code"] for item in stock_compatible}
    
    # Stokta olmayan uyumlu tonerler
    missing_toners = []
    for toner in all_compatible:
        if toner["toner_code"] not in stock_codes:
            missing_toners.append(toner)
    
    return missing_toners


def create_missing_toner_stock_card(toner_info: Dict, db) -> bool:
    """Eksik toner için otomatik stok kartı oluşturur."""
    try:
        # Varsayılan fiyat hesaplama (baskı kapasitesine göre)
        base_price = max(150.0, toner_info["print_capacity"] * 0.01)
        
        insert_query = """
        INSERT INTO stock_items (item_type, name, part_number, description, 
                                color_type, quantity, sale_price, sale_currency, 
                                supplier, purchase_price, purchase_currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        db.execute_query(insert_query, (
            'Toner',
            toner_info["toner_name"],
            toner_info["toner_code"],
            f"Otomatik oluşturulan toner kartı - Kapasite: {toner_info['print_capacity']} sayfa",
            toner_info["color_type"],
            0,  # Başlangıç stok 0
            base_price,
            'TL',
            'Kyocera',
            base_price * 0.7,  # %30 kar marjı
            'TL'
        ))
        
        return True
        
    except Exception as e:
        logging.error(f"Toner stok kartı oluşturma hatası: {e}")
        return False


# Test fonksiyonu
if __name__ == "__main__":
    # Test
    test_devices = [
        "TASKalfa 4500X",
        "ECOSYS M2135dn",
        "FS-1300DN",
        "KM-2530"
    ]
    
    for device in test_devices:
        print(f"\n--- {device} ---")
        compatible = find_compatible_toners_for_device(device)
        for toner in compatible[:3]:  # İlk 3 sonucu göster
            print(f"  {toner['toner_code']} - {toner['color_type']} - Güven: %{toner['confidence']*100:.0f}")