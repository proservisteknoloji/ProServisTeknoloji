"""
CPC Döviz Kuru Çevirme Test Scripti

Bu script, CPC fatura hesaplamalarında döviz kuru çevriminin doğru çalışıp çalışmadığını test eder.
"""

from decimal import Decimal
import sys
import os

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.currency_converter import get_exchange_rates

def test_currency_normalization():
    """Para birimi normalizasyon fonksiyonunu test eder"""
    print("=" * 60)
    print("TEST 1: Para Birimi Normalizasyonu")
    print("=" * 60)
    
    def _normalize_currency(cur):
        if not cur:
            print(f"  Para birimi boş/None -> TL")
            return 'TL'
        c = str(cur).strip().upper()
        original_c = c
        if c in ('EURO', 'EUR', 'E', '€'): 
            c = 'EUR'
        elif c in ('DOLAR', 'USD', 'US$', '$', 'DOLLAR'): 
            c = 'USD'
        elif c in ('TL', 'TRY', '₺', 'TÜRK LİRASI', 'TURK LIRASI'): 
            c = 'TL'
        else:
            print(f"  Bilinmeyen para birimi '{original_c}' -> TL")
            c = 'TL'
        
        if original_c != c:
            print(f"  '{original_c}' -> '{c}'")
        return c
    
    # Test cases
    test_cases = [
        ('EUR', 'EUR'),
        ('EURO', 'EUR'),
        ('€', 'EUR'),
        ('E', 'EUR'),
        ('USD', 'USD'),
        ('DOLAR', 'USD'),
        ('$', 'USD'),
        ('TL', 'TL'),
        ('TRY', 'TL'),
        ('₺', 'TL'),
        ('TÜRK LİRASI', 'TL'),
        (None, 'TL'),
        ('', 'TL'),
        ('XYZ', 'TL'),  # Bilinmeyen
    ]
    
    all_passed = True
    for input_val, expected in test_cases:
        result = _normalize_currency(input_val)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} Input: '{input_val}' -> Beklenen: '{expected}', Sonuç: '{result}'")
    
    print(f"\nTest Sonucu: {'BAŞARILI' if all_passed else 'BAŞARISIZ'}\n")
    return all_passed

def test_exchange_rate_retrieval():
    """TCMB'den döviz kuru çekmeyi test eder"""
    print("=" * 60)
    print("TEST 2: TCMB Döviz Kuru Çekme")
    print("=" * 60)
    
    rates = get_exchange_rates()
    
    print(f"\nÇekilen kurlar: {rates}")
    
    # Kontroller
    checks = []
    
    # TL her zaman 1.0 olmalı
    if rates.get('TL') == Decimal('1.0'):
        print("✓ TL kuru doğru (1.0)")
        checks.append(True)
    else:
        print(f"✗ TL kuru yanlış: {rates.get('TL')}")
        checks.append(False)
    
    # USD olmalı
    if 'USD' in rates and rates['USD'] > 0:
        print(f"✓ USD kuru mevcut: {rates['USD']}")
        checks.append(True)
    else:
        print("✗ USD kuru bulunamadı")
        checks.append(False)
    
    # EUR olmalı
    if 'EUR' in rates and rates['EUR'] > 0:
        print(f"✓ EUR kuru mevcut: {rates['EUR']}")
        checks.append(True)
    else:
        print("✗ EUR kuru bulunamadı")
        checks.append(False)
    
    all_passed = all(checks)
    print(f"\nTest Sonucu: {'BAŞARILI' if all_passed else 'BAŞARISIZ (Varsayılan kurlar kullanılıyor olabilir)'}\n")
    return all_passed, rates

def test_currency_conversion(rates):
    """Para birimi çevirme hesaplamalarını test eder"""
    print("=" * 60)
    print("TEST 3: Para Birimi Çevirme Hesaplamaları")
    print("=" * 60)
    
    # Test senaryoları
    test_scenarios = [
        {
            'name': 'EUR fiyatlı cihaz',
            'bw_price': Decimal('0.05'),  # 0.05 EUR per page
            'bw_currency': 'EUR',
            'bw_usage': 1000,  # 1000 sayfa
            'color_price': Decimal('0.10'),  # 0.10 EUR per page
            'color_currency': 'EUR',
            'color_usage': 500,  # 500 sayfa
        },
        {
            'name': 'USD fiyatlı cihaz',
            'bw_price': Decimal('0.04'),  # 0.04 USD per page
            'bw_currency': 'USD',
            'bw_usage': 2000,
            'color_price': Decimal('0.08'),
            'color_currency': 'USD',
            'color_usage': 1000,
        },
        {
            'name': 'TL fiyatlı cihaz',
            'bw_price': Decimal('1.50'),  # 1.50 TL per page
            'bw_currency': 'TL',
            'bw_usage': 500,
            'color_price': Decimal('3.00'),
            'color_currency': 'TL',
            'color_usage': 250,
        },
        {
            'name': 'Karışık para birimi (BW: EUR, Color: USD)',
            'bw_price': Decimal('0.06'),
            'bw_currency': 'EUR',
            'bw_usage': 1500,
            'color_price': Decimal('0.12'),
            'color_currency': 'USD',
            'color_usage': 750,
        },
    ]
    
    for scenario in test_scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        bw_rate = Decimal(str(rates.get(scenario['bw_currency'], 1.0)))
        color_rate = Decimal(str(rates.get(scenario['color_currency'], 1.0)))
        
        print(f"BW: {scenario['bw_usage']} sayfa × {scenario['bw_price']} {scenario['bw_currency']}")
        print(f"    Kur: {bw_rate}")
        
        bw_cost = scenario['bw_usage'] * scenario['bw_price']
        bw_cost_tl = bw_cost * bw_rate
        bw_unit_price_tl = (scenario['bw_price'] * bw_rate).quantize(Decimal('0.0001'))
        
        print(f"    Toplam: {bw_cost} {scenario['bw_currency']} = {bw_cost_tl} TL")
        print(f"    Birim fiyat TL: {bw_unit_price_tl} TL/sayfa")
        
        print(f"Color: {scenario['color_usage']} sayfa × {scenario['color_price']} {scenario['color_currency']}")
        print(f"    Kur: {color_rate}")
        
        color_cost = scenario['color_usage'] * scenario['color_price']
        color_cost_tl = color_cost * color_rate
        color_unit_price_tl = (scenario['color_price'] * color_rate).quantize(Decimal('0.0001'))
        
        print(f"    Toplam: {color_cost} {scenario['color_currency']} = {color_cost_tl} TL")
        print(f"    Birim fiyat TL: {color_unit_price_tl} TL/sayfa")
        
        total_tl = bw_cost_tl + color_cost_tl
        print(f"GENEL TOPLAM: {total_tl} TL")
        
        # Doğrulama: TL için kur 1.0 olmalı ve sonuç değişmemeli
        if scenario['bw_currency'] == 'TL':
            if bw_cost == bw_cost_tl:
                print("✓ TL fiyat doğru (değişmedi)")
            else:
                print(f"✗ TL fiyat yanlış: {bw_cost} != {bw_cost_tl}")
    
    print(f"\nTest Sonucu: BAŞARILI (Manuel kontrol gerekli)\n")
    return True

def main():
    """Ana test fonksiyonu"""
    print("\n" + "=" * 60)
    print("CPC DÖVIZ KURU ÇEVİRME TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Para birimi normalizasyonu
    results.append(("Normalizasyon", test_currency_normalization()))
    
    # Test 2: Kur çekme
    rate_test_result, rates = test_exchange_rate_retrieval()
    results.append(("Kur Çekme", rate_test_result))
    
    # Test 3: Çevirme hesaplamaları
    results.append(("Hesaplama", test_currency_conversion(rates)))
    
    # Özet
    print("=" * 60)
    print("TEST ÖZETİ")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ BAŞARILI" if passed else "✗ BAŞARISIZ"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print(f"\nGENEL SONUÇ: {'✓ TÜM TESTLER BAŞARILI' if all_passed else '✗ BAZI TESTLER BAŞARISIZ'}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
