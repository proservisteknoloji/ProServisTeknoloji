import sqlite3, os

db_path = r"\\192.168.1.1\volume(sda2)\ProServisData\teknik_servis_local.db"
if not os.path.exists(db_path):
    print('DB not found:', db_path)
    raise SystemExit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print('\nRecent service_records (last 10):')
for row in c.execute('SELECT id, device_id, status, created_date FROM service_records ORDER BY id DESC LIMIT 10'):
    print(dict(row))

print('\nRecent customer_devices (last 20):')
for row in c.execute('SELECT id, customer_id, device_model, serial_number FROM customer_devices ORDER BY id DESC LIMIT 20'):
    print(dict(row))

print('\nRecent stock_items is_consignment=1 (last 20):')
for row in c.execute("SELECT id, name, part_number, quantity, is_consignment FROM stock_items WHERE is_consignment=1 ORDER BY id DESC LIMIT 20"):
    print(dict(row))

print('\nChecking consignment stock -> customer_device matches:')
for row in c.execute("SELECT id, name, part_number FROM stock_items WHERE is_consignment=1"):
    part = row['part_number']
    cd = c.execute('SELECT id, customer_id FROM customer_devices WHERE serial_number = ? LIMIT 1', (part,)).fetchone()
    print({'stock_id':row['id'], 'part_number':part, 'customer_device': dict(cd) if cd else None})

conn.close()

# Run the same query used by refresh_emanet_stock
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
query = '''
    SELECT s.id, s.name, s.part_number as serial_number, s.quantity,
           sr.id as service_id, sr.problem_description, sr.notes,
           (SELECT GROUP_CONCAT(description, ', ') FROM quote_items WHERE service_record_id = sr.id AND unit_price IS NULL) as waiting_parts
    FROM stock_items s
    LEFT JOIN service_records sr ON sr.device_id = (
        SELECT cd.id FROM customer_devices cd WHERE cd.serial_number = s.part_number LIMIT 1
    ) AND sr.status IN ('Servise alındı', 'Parça bekleniyor', 'İşleme alındı')
    WHERE s.item_type = 'Cihaz' AND s.is_consignment = 1 AND sr.id IS NOT NULL
    ORDER BY s.name
'''
print('\nResult of emanet query:')
for r in cur.execute(query):
    print(dict(r))
conn.close()
