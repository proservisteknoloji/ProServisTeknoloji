import sqlite3
from datetime import datetime

conn = sqlite3.connect('C:/Users/umits/OneDrive/Desktop/proje datalar/teknik_servis_local.db')
cursor = conn.cursor()

print("=== Tüm Servis Kayıtları ===")
cursor.execute('SELECT id, created_date, status FROM service_records ORDER BY id')
rows = cursor.fetchall()
for row in rows:
    print(row)

print("\n=== Toplam Servis Sayısı ===")
cursor.execute('SELECT COUNT(*) FROM service_records')
total = cursor.fetchone()[0]
print(f'Toplam servis: {total}')

print("\n=== Aktif (Tamamlanmamış) Servisler ===")
cursor.execute("SELECT COUNT(*) FROM service_records WHERE status NOT IN ('Tamamlandı', 'İptal edildi', 'Teslim Edildi', 'Onarıldı')")
active = cursor.fetchone()[0]
print(f'Aktif servis: {active}')

print("\n=== Bu Ay Açılan Servis (strftime) ===")
cursor.execute("SELECT COUNT(*) FROM service_records WHERE strftime('%Y-%m', created_date) = strftime('%Y-%m', 'now')")
this_month = cursor.fetchone()[0]
print(f'Bu ay (strftime): {this_month}')

print("\n=== Şu anki tarih ===")
now = datetime.now()
print(f"Şimdi: {now}")
print(f"YYYY-MM formatı: {now.strftime('%Y-%m')}")

print("\n=== Durumlara Göre Dağılım ===")
cursor.execute("SELECT status, COUNT(*) FROM service_records GROUP BY status")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
