#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CPC cihaz ve stok verilerini kontrol eder"""

from utils.database import db_manager

print("=" * 60)
print("CPC CİHAZLARI VE TONER/KİT KODLARI")
print("=" * 60)

# Önce tablo yapısını kontrol et
print("\ncustomer_devices tablo kolonları:")
cols = db_manager.fetch_all('PRAGMA table_info(customer_devices)')
for col in cols:
    print(f"  {col['name']} ({col['type']})")

print("\n" + "=" * 60)

# CPC cihazları al
devices = db_manager.fetch_all("""
    SELECT * 
    FROM customer_devices 
    WHERE is_cpc = 1 
    LIMIT 10
""")

for device in devices:
    device_id = device['id']
    model = device['device_model']
    brand = device['brand']
    notes = device['notes']
    
    print(f"\n🖨️  Cihaz ID: {device_id} | Model: {model}")
    print(f"   Brand: {brand}")
    if notes:
        print(f"   Notes: {notes[:100]}...")
    
    # cpc_stock_items'da kayıt var mı?
    cpc_items = db_manager.fetch_all(
        "SELECT id, toner_code, toner_name FROM cpc_stock_items WHERE device_id = ?",
        (device_id,)
    )
    
    if cpc_items:
        print(f"   ✅ cpc_stock_items kayıtları ({len(cpc_items)} adet):")
        for item in cpc_items:
            print(f"      - {item['toner_code']}: {item['toner_name']}")
    else:
        print(f"   ❌ cpc_stock_items'da kayıt yok")

print("\n" + "=" * 60)
print("CPC_STOCK_ITEMS TOPLAM KAYIT SAYISI")
print("=" * 60)

total = db_manager.fetch_one("SELECT COUNT(*) as cnt FROM cpc_stock_items")
print(f"Toplam kayıt: {total['cnt'] if total else 0}")
