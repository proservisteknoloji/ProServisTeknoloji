import sqlite3, os

db_path = r"\\192.168.1.1\volume(sda2)\ProServisData\teknik_servis_local.db"
if not os.path.exists(db_path):
    print('DB not found:', db_path)
    raise SystemExit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

srv = c.execute('SELECT id, device_id, status, created_date FROM service_records ORDER BY id DESC LIMIT 1').fetchone()
print('\nLatest service_record: ', dict(srv) if srv else None)
if not srv:
    raise SystemExit(0)

dev_id = srv['device_id']
cd = c.execute('SELECT id, customer_id, device_model, serial_number FROM customer_devices WHERE id = ?', (dev_id,)).fetchone()
print('\nCustomer device for service device_id:', dict(cd) if cd else None)
if cd:
    serial = cd['serial_number']
    stk = c.execute('SELECT id, name, part_number, quantity FROM stock_items WHERE part_number = ? AND is_consignment=1', (serial,)).fetchone()
    print('\nMatching consignment stock for serial:', dict(stk) if stk else None)

conn.close()
