# utils/predefined_stock.py

"""
Önceden tanımlanmış stok ürünleri ve uyumluluk veritabanı.
CPC müşteriler için otomatik toner sipariş sistemi.
"""

# Önceden tanımlanmış toner kartları
PREDEFINED_TONERS = []

PREDEFINED_CONSUMABLES = []

PREDEFINED_KITS = []

PREDEFINED_SPARE_PARTS = []

def normalize_model_name(name):
    """
    Model adını eşleşme için normalize eder (boşluk, tire vb. kaldırır).
    """
    import unicodedata
    name = name.lower().replace(" ", "").replace("-", "").replace("_", "").replace(".", "")
    # Türkçe karakterleri İngilizce'ye çevir
    name = name.replace('ç', 'c').replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o')
    # Unicode normalizasyonu
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])
    return name

def get_compatible_toners_for_device(device_model):
    """
    Verilen cihaz modeli için uyumlu tonerleri döndürür.
    
    Args:
        device_model (str): Cihaz modeli
        
    Returns:
        list: Uyumlu toner listesi
    """
    compatible_toners = []
    normalized_device = normalize_model_name(device_model)
    
    for toner in PREDEFINED_TONERS:
        for model in toner['compatible_models']:
            normalized_model = normalize_model_name(model)
            if (normalized_model in normalized_device or 
                normalized_device in normalized_model or
                # Ek esnek eşleşme
                model.lower() in device_model.lower() or 
                device_model.lower() in model.lower()):
                compatible_toners.append(toner)
                break  # Aynı toner için tekrar eklenmemesi için
    
    return compatible_toners

def get_compatible_kits_for_device(device_model):
    """
    Verilen cihaz modeli için uyumlu kitleri döndürür.
    
    Args:
        device_model (str): Cihaz modeli
        
    Returns:
        list: Uyumlu kit listesi
    """
    compatible_kits = []
    
    for kit in PREDEFINED_KITS:
        # Çoklu eşleşme stratejisi
        for model in kit['compatible_models']:
            if (normalize_model_name(model) == normalize_model_name(device_model) or
                # Esnek eşleşme - "kyocera" prefix'siz karşılaştır
                normalize_model_name(model.replace('Kyocera ', '')) == normalize_model_name(device_model) or
                normalize_model_name(device_model.replace('Kyocera ', '')) == normalize_model_name(model) or
                # Ek esnek eşleşme
                model.lower() in device_model.lower() or 
                device_model.lower() in model.lower()):
                compatible_kits.append(kit)
                break  # Aynı kit için tekrar eklenmemesi için
    
    return compatible_kits

def get_compatible_spare_parts_for_device(device_model):
    """
    Verilen cihaz modeli için uyumlu yedek parçaları döndürür.
    
    Args:
        device_model (str): Cihaz modeli
        
    Returns:
        list: Uyumlu yedek parça listesi
    """
    compatible_parts = []
    
    for part in PREDEFINED_SPARE_PARTS:
        # Evrensel parça kontrolü (*)
        if '*' in part['compatible_models']:
            compatible_parts.append(part)
            continue
            
        # Çoklu eşleşme stratejisi
        for model in part['compatible_models']:
            if (normalize_model_name(model) == normalize_model_name(device_model) or
                # Esnek eşleşme - "kyocera" prefix'siz karşılaştır
                normalize_model_name(model.replace('Kyocera ', '')) == normalize_model_name(device_model) or
                normalize_model_name(device_model.replace('Kyocera ', '')) == normalize_model_name(model) or
                # Ek esnek eşleşme
                model.lower() in device_model.lower() or 
                device_model.lower() in model.lower()):
                compatible_parts.append(part)
                break  # Aynı yedek parça için tekrar eklenmemesi için
    
    return compatible_parts

def get_compatible_products_for_device(device_model, product_types=None):
    """
    Verilen cihaz modeli için uyumlu tüm ürünleri döndürür.
    
    Args:
        device_model (str): Cihaz modeli
        product_types (list): Dahil edilecek ürün tipleri ['Toner', 'Kit', 'Yedek Parça']
        
    Returns:
        list: Uyumlu ürün listesi
    """
    if product_types is None:
        product_types = ['Toner', 'Kit', 'Yedek Parça']
    
    compatible_products = []
    
    if 'Toner' in product_types:
        compatible_products.extend(get_compatible_toners_for_device(device_model))
    
    if 'Kit' in product_types:
        compatible_products.extend(get_compatible_kits_for_device(device_model))
    
    if 'Yedek Parça' in product_types:
        compatible_products.extend(get_compatible_spare_parts_for_device(device_model))
    
    # Consumables da dahil et
    for consumable in PREDEFINED_CONSUMABLES:
        if any(model.lower() in device_model.lower() or device_model.lower() in model.lower() 
               for model in consumable['compatible_models']):
            compatible_products.append(consumable)
    
    return compatible_products

def get_compatible_consumables_for_device(device_model):
    """
    Verilen cihaz modeli için uyumlu sarf malzemelerini döndürür.
    
    Args:
        device_model (str): Cihaz modeli
        
    Returns:
        list: Uyumlu sarf malzemeleri listesi
    """
    compatible_consumables = []
    
    for consumable in PREDEFINED_CONSUMABLES:
        if any(model.lower() in device_model.lower() or device_model.lower() in model.lower() 
               for model in consumable['compatible_models']):
            compatible_consumables.append(consumable)
    
    return compatible_consumables

def get_all_predefined_items():
    """
    Tüm önceden tanımlanmış ürünleri döndürür.
    
    Returns:
        list: Tüm önceden tanımlanmış ürünler (tonerler, kitleri, yedek parçalar, consumables)
    """
    return PREDEFINED_TONERS + PREDEFINED_KITS + PREDEFINED_SPARE_PARTS + PREDEFINED_CONSUMABLES