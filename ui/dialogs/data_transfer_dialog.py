# ui/dialogs/data_transfer_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QPushButton,
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from decimal import Decimal
from utils.database import db_manager
from utils.workers import PANDAS_AVAILABLE

class DataTransferDialog(QDialog):
    """Excel/CSV dosyalarından veri içe aktarma ve dışa aktarma işlemlerini yöneten diyalog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("Veri Aktarım Merkezi")
        
        self._init_ui()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        self._create_import_group(main_layout)
        self._create_export_group(main_layout)
        
        self._check_pandas_availability()
        self._connect_signals()

    def _create_import_group(self, layout: QVBoxLayout):
        """İçe aktarma grubunu oluşturur."""
        import_group = QGroupBox("İçe Aktar")
        import_layout = QVBoxLayout()
        self.btn_import_excel = QPushButton("Excel/CSV'den Müşteri/Cihaz Aktar")
        self.btn_import_stock = QPushButton("Excel/CSV'den Stok Aktar")
        import_layout.addWidget(self.btn_import_excel)
        import_layout.addWidget(self.btn_import_stock)
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

    def _create_export_group(self, layout: QVBoxLayout):
        """Dışa aktarma grubunu oluşturur."""
        export_group = QGroupBox("Dışa Aktar")
        export_layout = QVBoxLayout()
        self.btn_export_customers_excel = QPushButton("Tüm Müşteri ve Cihaz Verilerini Excel'e Aktar")
        self.btn_export_customers_csv = QPushButton("Tüm Müşteri ve Cihaz Verilerini CSV'ye Aktar (HIZLI)")
        self.btn_export_stock_excel = QPushButton("Tüm Stok Verilerini Excel'e Aktar")
        self.btn_export_stock_csv = QPushButton("Tüm Stok Verilerini CSV'ye Aktar")
        export_layout.addWidget(self.btn_export_customers_excel)
        export_layout.addWidget(self.btn_export_customers_csv)
        export_layout.addWidget(self.btn_export_stock_excel)
        export_layout.addWidget(self.btn_export_stock_csv)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

    def _check_pandas_availability(self):
        """Pandas kütüphanesinin kullanılabilirliğini kontrol eder ve butonları ayarlar."""
        if not PANDAS_AVAILABLE:
            for btn in [self.btn_import_excel, self.btn_export_customers_excel]:
                btn.setEnabled(False)
                btn.setToolTip("Bu özellik için 'pandas' ve 'openpyxl' kütüphaneleri gereklidir.")
        
        # CSV export her zaman aktif (pandas gerekmez)
        self.btn_export_customers_csv.setEnabled(True)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        if PANDAS_AVAILABLE:
            self.btn_import_excel.clicked.connect(self._import_from_excel)
            self.btn_export_customers_excel.clicked.connect(self._export_to_excel)
            self.btn_import_stock.clicked.connect(self._import_stock_from_excel)
            self.btn_export_stock_excel.clicked.connect(self._export_stock_to_excel)
        # CSV export her zaman çalışır
        self.btn_export_customers_csv.clicked.connect(self._export_to_csv)
        self.btn_export_stock_csv.clicked.connect(self._export_stock_to_csv)

    def _import_stock_from_excel(self):
        import pandas as pd
        file_path, _ = QFileDialog.getOpenFileName(self, "Excel/CSV'den Stok Aktar", "", "Veri Dosyaları (*.xlsx *.csv)")
        if not file_path:
            return
        # Türkçe başlıklar
        turkish_columns = [
            "Ürün Tipi", "Ürün Adı", "Parça No", "Açıklama", "Adet", "Tedarikçi", "Renk Tipi", "Uyumlu Modeller", "Satış Fiyatı", "Satış Para Birimi", "Alış Fiyatı", "Alış Para Birimi", "Konsinye Mi"
        ]
        db_columns = [
            "item_type", "name", "part_number", "description", "quantity", "supplier", "color_type", "compatible_models", "sale_price", "sale_currency", "purchase_price", "purchase_currency", "is_consignment"
        ]
        try:
            df = pd.read_csv(file_path, dtype=str).fillna('') if file_path.lower().endswith('.csv') else pd.read_excel(file_path, dtype=str).fillna('')
            # Sütun eşleştirme
            missing = [col for col in turkish_columns if col not in df.columns]
            if missing:
                QMessageBox.critical(self, "Eksik Sütun", f"Excel/CSV dosyasında eksik sütunlar: {', '.join(missing)}")
                return
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE TRANSACTION")
            for _, row in df.iterrows():
                part_number = row["Parça No"]
                cursor.execute("SELECT id FROM stock_items WHERE part_number = ?", (part_number,))
                existing = cursor.fetchone()
                # Doğru eşleştirme
                value_map = {
                    "item_type": row["Ürün Tipi"],
                    "name": row["Ürün Adı"],
                    "part_number": row["Parça No"],
                    "description": row["Açıklama"],
                    "quantity": row["Adet"],
                    "supplier": row["Tedarikçi"],
                    "color_type": row["Renk Tipi"],
                    "compatible_models": row["Uyumlu Modeller"],
                    "sale_price": row["Satış Fiyatı"],
                    "sale_currency": row["Satış Para Birimi"],
                    "purchase_price": row["Alış Fiyatı"],
                    "purchase_currency": row["Alış Para Birimi"],
                    "is_consignment": row["Konsinye Mi"]
                }
                values = [value_map[col] for col in db_columns]
                if existing:
                    cursor.execute(
                        "UPDATE stock_items SET quantity = ?, purchase_price = ?, sale_price = ?, description = ?, supplier = ?, is_consignment = ? WHERE part_number = ?",
                        (
                            value_map["quantity"],
                            value_map["purchase_price"],
                            value_map["sale_price"],
                            value_map["description"],
                            value_map["supplier"],
                            value_map["is_consignment"],
                            part_number
                        )
                    )
                else:
                    cursor.execute(
                        f"INSERT INTO stock_items ({', '.join(db_columns)}) VALUES ({', '.join(['?' for _ in db_columns])})",
                        values
                    )
            conn.commit()
            QMessageBox.information(self, "Başarılı", "Stok verileri başarıyla içe aktarıldı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Stok içe aktarma sırasında hata oluştu: {e}")

    def _export_stock_to_excel(self):
        import pandas as pd
        file_path, _ = QFileDialog.getSaveFileName(self, "Stok Verilerini Excel'e Aktar", "stok_listesi.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path:
            return
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            # Türkçe başlıklar
            db_columns = ["item_type", "name", "part_number", "description", "quantity", "supplier", "color_type", "compatible_models", "sale_price", "sale_currency", "purchase_price", "purchase_currency", "is_consignment"]
            turkish_columns = ["Ürün Tipi", "Ürün Adı", "Parça No", "Açıklama", "Adet", "Tedarikçi", "Renk Tipi", "Uyumlu Modeller", "Satış Fiyatı", "Satış Para Birimi", "Alış Fiyatı", "Alış Para Birimi", "Konsinye Mi"]
            sql = f'SELECT {", ".join(db_columns)} FROM stock_items'
            rows = cursor.execute(sql).fetchall()
            df = pd.DataFrame(rows, columns=turkish_columns)
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Başarılı", f"Stok verileri başarıyla Excel'e aktarıldı:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Stok dışa aktarma sırasında hata oluştu: {e}")

    def _export_stock_to_csv(self):
        import csv
        file_path, _ = QFileDialog.getSaveFileName(self, "Stok Verilerini CSV'ye Aktar", "stok_listesi.csv", "CSV Dosyaları (*.csv)")
        if not file_path:
            return
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            db_columns = ["item_type", "name", "part_number", "description", "quantity", "supplier", "color_type", "compatible_models", "sale_price", "sale_currency", "purchase_price", "purchase_currency", "is_consignment"]
            turkish_columns = ["Ürün Tipi", "Ürün Adı", "Parça No", "Açıklama", "Adet", "Tedarikçi", "Renk Tipi", "Uyumlu Modeller", "Satış Fiyatı", "Satış Para Birimi", "Alış Fiyatı", "Alış Para Birimi", "Konsinye Mi"]
            sql = f'SELECT {", ".join(db_columns)} FROM stock_items'
            rows = cursor.execute(sql).fetchall()
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(turkish_columns)
                for row in rows:
                    writer.writerow(row)
            QMessageBox.information(self, "Başarılı", f"Stok verileri başarıyla CSV'ye aktarıldı:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Stok dışa aktarma sırasında hata oluştu: {e}")

    def _import_from_excel(self):
        """Excel veya CSV dosyasından veri içe aktarma işlemini başlatır (OPTIMIZE EDİLMİŞ)."""
        import logging
        from datetime import datetime
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Excel veya CSV Dosyası Seç", "", 
                                                   "Veri Dosyaları (*.xlsx *.csv)")
        if not file_path:
            return
            
        start_time = datetime.now()
        logging.info(f"Import başlatıldı: {file_path}")
        
        try:
            import pandas as pd
            df = pd.read_csv(file_path, dtype=str).fillna('') if file_path.lower().endswith('.csv') else pd.read_excel(file_path, dtype=str).fillna('')
            
            logging.info(f"Dosya yüklendi: {len(df)} satır, {len(df.columns)} sütun")
            
            if not self._validate_columns(df):
                logging.error("Sütun validasyonu başarısız")
                return

            logging.info("Veri işleme başlatılıyor...")
            self._process_import_data_optimized(df, start_time)
            
        except Exception as e:
            logging.error(f"Import hatası: {e}")
            QMessageBox.critical(self, "İçe Aktarma Hatası", f"Dosya işlenirken bir hata oluştu: {e}")

    def _validate_columns(self, df) -> bool:
        """DataFrame'in gerekli sütunları içerip içermediğini kontrol eder."""
        self.column_map = {
            "customer": ["Müşteri Adı", "Müşteri", "Customer", "Customer Name", "Firma Adı", "Şirket"],
            "model": ["Cihaz Modeli", "Model", "Device Model", "Cihaz", "Device"],
            "serial": ["Seri No", "serial_number", "Serial", "Seri Numarası", "Serial Number"],
            "type": ["Cihaz Türü", "Türü", "Device Type", "Type"],
            "cpc_type": ["Tipi", "Kopya Başı Mı?", "Müşteri Tipi", "Type", "Customer Type"],
            "phone": ["Telefon", "Phone", "Tel", "Telefon No", "Phone Number", "Cep Telefonu", "Sabit Telefon"],
            "email": ["E-posta", "Email", "E-Mail", "Mail"],
            "address": ["Adres", "Lokasyonu", "Address", "Location", "Adres Bilgisi"],
            "bw_price": ["S/B Birim Fiyat", "S/B", "BW Price", "Siyah-Beyaz Fiyat"],
            "color_price": ["Renkli Birim Fiyat", "Renkli", "Color Price", "Colour Price"],
            "bw_currency": ["S/B Para Birimi", "BW Currency", "S/B Currency"],
            "color_currency": ["Renkli Para Birimi", "Color Currency", "Colour Currency"],
            "customer_type": ["Müşteri Tipi", "Tip", "Customer Type"],
            "brand": ["Marka", "Brand", "Manufacturer"],
            "installation_date": ["Kurulum Tarihi", "Installation Date", "Montaj Tarihi"],
            "notes": ["Notlar", "Notes", "Açıklama", "Description"],
            "tax_id": ["Vergi No", "Tax ID", "Vergi Numarası"],
            "tax_office": ["Vergi Dairesi", "Tax Office"],
            "location_name": ["Lokasyon Adı", "Lokasyon", "Location Name", "Şube Adı", "Şube"],
            "location_address": ["Lokasyon Adresi", "Lokasyon Adres", "Location Address", "Şube Adresi"],
            "location_phone": ["Lokasyon Telefonu", "Lokasyon Tel", "Location Phone", "Şube Telefonu"]
        }
        self.found_columns = {key: next((name for name in names if name in df.columns), None) for key, names in self.column_map.items()}
        
        # Debug: Bulunan sütunları göster
        found_info = {k: v for k, v in self.found_columns.items() if v is not None}
        print(f"Excel'de bulunan sütunlar: {found_info}")
        missing_info = {k: v for k, v in self.found_columns.items() if v is None}
        if missing_info:
            print(f"Excel'de bulunmayan sütunlar: {list(missing_info.keys())}")
        
        required_keys = {"customer", "model", "serial"}
        if not all(self.found_columns.get(key) for key in required_keys):
            missing_keys = [self.column_map[key][0] for key in required_keys if not self.found_columns.get(key)]
            QMessageBox.critical(self, "Eksik Sütun Hatası", 
                                 f"Excel/CSV dosyasında zorunlu sütunlar bulunamadı:\n-> {', '.join(missing_keys)}")
            return False
        return True
    
    def _process_import_data_optimized(self, df, start_time):
        """DataFrame'i BATCH INSERT ile optimize edilmiş şekilde veritabanına aktarır."""
        import logging
        from datetime import datetime
        from PyQt6.QtWidgets import QProgressDialog
        
        stats = {'added_c': 0, 'added_d': 0, 'added_l': 0, 'skipped_d': 0, 'updated_c': 0, 'updated_d': 0}
        progress = QProgressDialog("Veriler aktarılıyor (optimize edilmiş)...", "İptal", 0, 100, self)
        progress.setWindowTitle("Yükleniyor")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        conn = None
        try:
            conn = self.db.get_connection()
            # SQLite optimizasyonları
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 saniye timeout
            conn.execute("PRAGMA journal_mode = WAL")     # Write-Ahead Logging (eşzamanlı okuma/yazma)
            cursor = conn.cursor()
            
            # Transaction başlat (IMMEDIATE = hemen write lock al)
            cursor.execute("BEGIN IMMEDIATE TRANSACTION")
            progress.setValue(10)
            
            # 1. Tüm müşterileri topla ve batch insert
            logging.info("Müşteriler toplanıyor...")
            customers_to_add = []
            customer_cache = {}  # Müşteri adı -> ID cache
            
            # Mevcut müşterileri cache'e al
            existing_customers = cursor.execute("SELECT id, name FROM customers").fetchall()
            for cust_id, cust_name in existing_customers:
                customer_cache[cust_name] = cust_id
            
            progress.setValue(20)
            
            # Yeni müşterileri topla
            for _, row in df.iterrows():
                cust_name = row.get(self.found_columns["customer"], '').strip()
                if not cust_name or cust_name in customer_cache:
                    continue
                
                # Yeni müşteri
                phone_col = self.found_columns.get("phone")
                phone = row.get(phone_col, '').strip() if phone_col else ''
                if not phone:
                    phone = self._generate_random_phone()
                
                email = row.get(self.found_columns.get("email"), '').strip() if self.found_columns.get("email") else ''
                address = row.get(self.found_columns.get("address"), '').strip() if self.found_columns.get("address") else ''
                
                customers_to_add.append((
                    cust_name,
                    phone,
                    email or "Bilinmiyor",
                    address or "Bilinmiyor",
                    "", "",  # tax_id, tax_office
                    0, None, None  # is_contract, contract_start, contract_end
                ))
                customer_cache[cust_name] = None  # Placeholder
            
            progress.setValue(30)
            
            # Batch insert müşteriler
            if customers_to_add:
                logging.info(f"{len(customers_to_add)} yeni müşteri ekleniyor (batch)...")
                cursor.executemany(
                    "INSERT INTO customers (name, phone, email, address, tax_id, tax_office, is_contract, contract_start_date, contract_end_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    customers_to_add
                )
                stats['added_c'] = len(customers_to_add)
                
                # Yeni eklenen müşterilerin ID'lerini cache'e ekle
                for cust_name in [c[0] for c in customers_to_add]:
                    cust_id = cursor.execute("SELECT id FROM customers WHERE name = ?", (cust_name,)).fetchone()
                    if cust_id:
                        customer_cache[cust_name] = cust_id[0]
            
            progress.setValue(50)
            
            # 2. Lokasyonları topla ve batch insert
            logging.info("Lokasyonlar toplanıyor...")
            location_cache = {}  # (customer_id, location_name) -> location_id
            locations_to_add = []
            
            # Mevcut lokasyonları cache'e al
            existing_locations = cursor.execute("SELECT id, customer_id, location_name FROM customer_locations").fetchall()
            for loc_id, cust_id, loc_name in existing_locations:
                location_cache[(cust_id, loc_name)] = loc_id
            
            # Yeni lokasyonları topla
            for _, row in df.iterrows():
                cust_name = row.get(self.found_columns["customer"], '').strip()
                location_name = row.get(self.found_columns.get("location_name"), '').strip()
                
                if not cust_name or not location_name:
                    continue
                
                cust_id = customer_cache.get(cust_name)
                if not cust_id:
                    continue
                
                # Zaten cache'de var mı?
                if (cust_id, location_name) in location_cache:
                    continue
                
                location_address = row.get(self.found_columns.get("location_address"), '').strip()
                location_phone = row.get(self.found_columns.get("location_phone"), '').strip()
                
                locations_to_add.append((
                    cust_id, location_name, location_address or '', location_phone or ''
                ))
                location_cache[(cust_id, location_name)] = None  # Placeholder
            
            progress.setValue(40)
            
            # Batch insert lokasyonlar
            if locations_to_add:
                logging.info(f"{len(locations_to_add)} yeni lokasyon ekleniyor (batch)...")
                cursor.executemany(
                    "INSERT INTO customer_locations (customer_id, location_name, address, phone) VALUES (?, ?, ?, ?)",
                    locations_to_add
                )
                stats['added_l'] = len(locations_to_add)
                
                # Yeni eklenen lokasyonların ID'lerini cache'e ekle
                for cust_id, loc_name, _, _ in locations_to_add:
                    loc_id = cursor.execute(
                        "SELECT id FROM customer_locations WHERE customer_id = ? AND location_name = ?", 
                        (cust_id, loc_name)
                    ).fetchone()
                    if loc_id:
                        location_cache[(cust_id, loc_name)] = loc_id[0]
            
            progress.setValue(50)
            
            # 3. Tüm cihazları topla ve batch insert
            logging.info("Cihazlar toplanıyor...")
            devices_to_add = []
            serial_counter = 1
            
            for _, row in df.iterrows():
                cust_name = row.get(self.found_columns["customer"], '').strip()
                model = row.get(self.found_columns["model"], '').strip()
                serial = row.get(self.found_columns["serial"], '').strip()
                
                if not cust_name or not model:
                    stats['skipped_d'] += 1
                    continue
                
                cust_id = customer_cache.get(cust_name)
                if not cust_id:
                    continue
                
                # Seri numarası kontrolü
                if not serial:
                    serial = f"AUTO_{serial_counter:07d}"
                    serial_counter += 1
                
                # Mevcut cihaz kontrolü
                existing = cursor.execute(
                    "SELECT id FROM customer_devices WHERE customer_id = ? AND serial_number = ?",
                    (cust_id, serial)
                ).fetchone()
                
                if existing:
                    stats['updated_d'] += 1
                    continue
                
                # Lokasyon ID'sini bul
                location_name = row.get(self.found_columns.get("location_name"), '').strip()
                location_id = None
                if location_name:
                    location_id = location_cache.get((cust_id, location_name))
                
                # Device type ve color type
                dev_type = self._determine_device_type(model, row)
                color_type = dev_type
                
                # CPC kontrolü
                cpc_col = self.found_columns.get("cpc_type")
                cpc_value = str(row.get(cpc_col, '') if cpc_col else '').strip().upper()
                is_cpc = cpc_value in ['ÜCRETLİ', 'EVET', 'CPC', 'KOPYA BAŞI', 'TRUE', '1', 'YES', 'SÖZLEŞMELİ', 'CONTRACT']
                
                # Fiyatlar
                bw_price_str = str(row.get(self.found_columns.get("bw_price"), '0') if self.found_columns.get("bw_price") else '0').replace(',', '.')
                color_price_str = str(row.get(self.found_columns.get("color_price"), '0') if self.found_columns.get("color_price") else '0').replace(',', '.')
                bw_price = float(Decimal(bw_price_str))
                color_price = float(Decimal(color_price_str))
                
                devices_to_add.append((
                    cust_id, model, serial,
                    row.get(self.found_columns.get('brand'), 'Kyocera').strip() if self.found_columns.get('brand') else 'Kyocera',
                    dev_type, color_type,
                    '', '',  # installation_date, notes
                    is_cpc, bw_price, 'TL', color_price, 'TL',
                    location_id
                ))
            
            progress.setValue(70)
            
            # Batch insert cihazlar
            if devices_to_add:
                logging.info(f"{len(devices_to_add)} yeni cihaz ekleniyor (batch)...")
                cursor.executemany(
                    """INSERT INTO customer_devices 
                    (customer_id, device_model, serial_number, brand, device_type, color_type, 
                     installation_date, notes, is_cpc, cpc_bw_price, cpc_bw_currency, cpc_color_price, cpc_color_currency, location_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    devices_to_add
                )
                stats['added_d'] = len(devices_to_add)
            
            progress.setValue(90)
            
            # Transaction commit
            conn.commit()
            logging.info("Transaction commit edildi")
            
            progress.setValue(100)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logging.info(f"Import tamamlandı: {elapsed:.2f} saniye")
            
            self._show_import_summary_optimized(stats, elapsed)
            
        except Exception as e:
            logging.error(f"Import hatası: {e}")
            if conn:
                try:
                    conn.rollback()
                    logging.info("Transaction rollback yapıldı")
                except:
                    pass
            QMessageBox.critical(self, "İçe Aktarma Hatası", f"Bir hata oluştu: {e}")
        finally:
            progress.close()

    def _process_import_data(self, df):
        """DataFrame'i işleyerek veritabanına aktarır."""
        print(f"_process_import_data çağrıldı, {len(df)} satır işlenecek")
        from PyQt6.QtWidgets import QProgressDialog
        stats = {'added_c': 0, 'added_d': 0, 'skipped_d': 0, 'updated_c': 0, 'updated_d': 0}
        progress = QProgressDialog("Veriler aktarılıyor...", "İptal", 0, len(df), self)
        progress.setWindowTitle("Yükleniyor")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        print(f"Toplam {len(df)} satır işlenecek")
        processed_count = 0
        progress.setValue(0)
        for i, row in enumerate(df.iterrows()):
            if progress.wasCanceled():
                break
            _, row = row
            cust_name = row.get(self.found_columns["customer"], '').strip()
            model = row.get(self.found_columns["model"], '').strip()
            serial = row.get(self.found_columns["serial"], '').strip()
            
            # Telefon sütunu varsa kontrol et, yoksa boş olarak kabul et
            phone_col = self.found_columns.get("phone")
            phone = row.get(phone_col, '').strip() if phone_col else ''
            
            # Debug: İlk 5 satır için detaylı bilgi göster
            if i < 5:
                print(f"Satır {i+1}: Müşteri='{cust_name}', Model='{model}', Seri='{serial}' (len={len(serial)}, boş mu={serial==' '}), Telefon='{phone}' (len={len(phone)}, boş mu={phone==' '}), TelefonSütunu={phone_col}")
            
            # ...existing code...
            
            device_should_be_imported = model_exists
            if device_should_be_imported:
                if cust_id:
                    self._create_device(cust_id, model, serial, row, stats, cust_name)
            else:
                # Detaylı atlama nedeni göster
                skip_reason = []
                if not model_exists:
                    skip_reason.append(f"Model boş: '{model}'")
                
                if i < 10:  # İlk 10 satır için atlama nedeni göster
                    print(f"❌ Cihaz atlandı {i+1}: {' | '.join(skip_reason)} (Müşteri: {cust_name}, Model: '{model}')")
                stats['skipped_d'] += 1
                    
            progress.setValue(i+1)
        print(f"Toplam müşteri satırı: {processed_count}, Atlanan cihaz satırı: {stats['skipped_d']}")
        self._show_import_summary(stats)

    def _get_or_create_customer(self, cust_name: str, row, stats: dict) -> int | None:
        """Müşteriyi veritabanında arar, yoksa oluşturur ve ID'sini döndürür."""
        # Özel debug: 1905 müşterisi için detaylı bilgi
        if "1905" in cust_name and "KULTUR" in cust_name:
            print(f"🔍 1905 müşteri kontrolü: '{cust_name}'")
        
        cust_data = self.db.fetch_one("SELECT id, phone, email, address, is_contract FROM customers WHERE name = ?", (cust_name,))
        
        if "1905" in cust_name and "KULTUR" in cust_name:
            print(f"📊 Veritabanı sorgu sonucu: {cust_data}")
        
        if not cust_data:
            # Müşteri tipini belirle
            customer_type_col = self.found_columns.get("customer_type")
            customer_type_value = str(row.get(customer_type_col, '') if customer_type_col else '').strip().upper()
            is_contract = customer_type_value in ['SÖZLEŞMELİ', 'CONTRACT', 'SÖZLEŞME', 'KONTRAT']
            
            # Telefon numarası için özel logic
            phone_value = ""
            if self.found_columns.get("phone"):
                excel_phone = row.get(self.found_columns.get("phone"), '').strip()
                if excel_phone:
                    phone_value = excel_phone
                else:
                    phone_value = self._generate_random_phone()
                    if "1905" in cust_name and "KULTUR" in cust_name:
                        print(f"📞 1905 müşteri için rastgele telefon üretildi: {phone_value}")
            else:
                # Telefon sütunu yoksa rastgele numara üret
                phone_value = self._generate_random_phone()
                if "1905" in cust_name and "KULTUR" in cust_name:
                    print(f"📞 1905 müşteri için telefon sütunu yok, rastgele üretildi: {phone_value}")
            
            cust_params = (
                cust_name,
                phone_value,
                (row.get(self.found_columns.get("email"), '').strip() if self.found_columns.get("email") else '') or "Bilinmiyor",
                (row.get(self.found_columns.get("address"), '').strip() if self.found_columns.get("address") else '') or "Bilinmiyor",
                (row.get(self.found_columns.get("tax_id"), '').strip() if self.found_columns.get("tax_id") else '') or "Bilinmiyor",
                (row.get(self.found_columns.get("tax_office"), '').strip() if self.found_columns.get("tax_office") else '') or "Bilinmiyor"
            )
            result = self.db.add_customer(*cust_params)
            cust_id = self.db.get_customer_id_by_name(cust_name)
            if cust_id:
                # Sözleşmeli müşteri ise güncelle
                if is_contract:
                    self.db.update_customer_details(cust_id, {'is_contract': 1})
                stats['added_c'] += 1
                if "1905" in cust_name and "KULTUR" in cust_name:
                    print(f"✅ 1905 MÜŞTERİ BAŞARIYLA EKLENDİ - ID: {cust_id}")
                print(f"✓ Müşteri eklendi: {cust_name} (ID: {cust_id})")
                return cust_id
            else:
                if "1905" in cust_name and "KULTUR" in cust_name:
                    print(f"❌ 1905 MÜŞTERİ EKLEME BAŞARISIZ")
                print(f"✗ Müşteri eklenemedi: {cust_name}")
                QMessageBox.critical(self, "Veritabanı Hatası", 
                                   f"Müşteri eklenirken hata oluştu: {cust_name}\nİçe aktarma durduruldu.")
                return None
        else:
            cust_id, db_phone, db_email, db_address, db_is_contract = cust_data
            if "1905" in cust_name and "KULTUR" in cust_name:
                print(f"📋 1905 MÜŞTERİ ZATEN MEVCUT - ID: {cust_id}")
            update_details = {}
            if not db_phone:
                phone_col = self.found_columns.get("phone")
                if phone_col:
                    excel_phone = row.get(phone_col, '').strip()
                    if excel_phone:  # Only update if Excel actually has phone data
                        update_details['phone'] = excel_phone
                else:
                    # If no phone column, generate random phone
                    update_details['phone'] = self._generate_random_phone()
            if not db_email:
                email_col = self.found_columns.get("email")
                new_email = (row.get(email_col, '').strip() if email_col else '') or "Bilinmiyor"
                if new_email != "Bilinmiyor":
                    update_details['email'] = new_email
            if not db_address:
                address_col = self.found_columns.get("address")
                new_address = (row.get(address_col, '').strip() if address_col else '') or "Bilinmiyor"
                if new_address != "Bilinmiyor":
                    update_details['address'] = new_address
            
            # Sözleşmeli müşteri durumunu da güncelle (eğer boş ise)
            if db_is_contract == 0:  # Henüz sözleşmeli olarak işaretlenmemişse
                customer_type_col = self.found_columns.get("customer_type")
                customer_type_value = str(row.get(customer_type_col, '') if customer_type_col else '').strip().upper()
                is_contract = customer_type_value in ['SÖZLEŞMELİ', 'CONTRACT', 'SÖZLEŞME', 'KONTRAT']
                if is_contract:
                    update_details['is_contract'] = 1
            
            if update_details:
                self.db.update_customer_details(cust_id, update_details)
                stats['updated_c'] += 1
            return cust_id

    def _create_device(self, cust_id: int, model: str, serial: str, row, stats: dict, cust_name: str) -> bool:
        """Yeni bir cihazı customer_devices tablosuna ekler veya mevcut olanı günceller."""
        # Mevcut cihazı kontrol et (orijinal seri numarası ile)
        existing_device = self.db.fetch_one("SELECT id, device_type, color_type FROM customer_devices WHERE serial_number = ?", (serial,))
        
        # Eğer seri numarası boşsa, benzersiz bir seri numarası oluştur
        original_serial = serial
        if not serial or serial.strip() == '':
            import uuid
            serial = f"AUTO_{str(uuid.uuid4())[:8].upper()}"
            print(f"Oto seri numarası oluşturuldu: {serial} (orijinal: '{original_serial}')")
        
        # Lokasyon bilgilerini al
        location_name = row.get(self.found_columns.get("location_name"), '').strip()
        location_address = row.get(self.found_columns.get("location_address"), '').strip()
        location_phone = row.get(self.found_columns.get("location_phone"), '').strip()
        
        # Lokasyon ID'sini belirle
        location_id = None
        if location_name:
            # Lokasyon adı varsa, bu müşteriye ait lokasyonu bul veya oluştur
            existing_location = self.db.fetch_one(
                "SELECT id FROM customer_locations WHERE customer_id = ? AND location_name = ?", 
                (cust_id, location_name)
            )
            
            if existing_location:
                location_id = existing_location['id']
                # Mevcut lokasyon bilgilerini güncelle
                if location_address or location_phone:
                    update_data = {}
                    if location_address:
                        update_data['address'] = location_address
                    if location_phone:
                        update_data['phone'] = location_phone
                    if update_data:
                        set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                        params = list(update_data.values()) + [existing_location['id']]
                        self.db.execute_query(f"UPDATE customer_locations SET {set_clause} WHERE id = ?", tuple(params))
            else:
                # Yeni lokasyon oluştur
                loc_result = self.db.execute_query(
                    "INSERT INTO customer_locations (customer_id, location_name, address, phone) VALUES (?, ?, ?, ?)",
                    (cust_id, location_name, location_address, location_phone)
                )
                if loc_result:
                    location_id = loc_result
                    print(f"Yeni lokasyon oluşturuldu: {location_name} (Müşteri: {cust_name})")
        else:
            # Lokasyon adı yoksa, varsayılan lokasyonu kullan
            default_location = self.db.fetch_one(
                "SELECT id FROM customer_locations WHERE customer_id = ? AND location_name LIKE ?",
                (cust_id, f"{cust_name}%Ana Lokasyon%")
            )
            if default_location:
                location_id = default_location['id']
            else:
                # Ana lokasyon oluştur
                default_loc_name = f"{cust_name} - Ana Lokasyon"
                loc_result = self.db.execute_query(
                    "INSERT INTO customer_locations (customer_id, location_name, address, phone) VALUES (?, ?, ?, ?)",
                    (cust_id, default_loc_name, '', '')
                )
                if loc_result:
                    location_id = loc_result
        
        try:
            # Device type'ı akıllıca belirle
            dev_type = self._determine_device_type(model, row)
            color_type = self._determine_color_type(model, row)
            
            # CPC durumunu belirle - sözleşmeli ve ücretli kontrolü
            cpc_col = self.found_columns.get("cpc_type")
            cpc_value = str(row.get(cpc_col, '') if cpc_col else '').strip().upper()
            # Sözleşmeli müşteri kontrolü
            is_contract = cpc_value in ['SÖZLEŞMELİ', 'CONTRACT', 'SÖZLEŞME', 'KONTRAT']
            # Ücretli/kopya başı kontrolü
            is_cpc = cpc_value in ['ÜCRETLİ', 'EVET', 'CPC', 'KOPYA BAŞI', 'TRUE', '1', 'YES']
            
            # Sözleşmeli ise CPC olarak işaretle
            if is_contract:
                is_cpc = True
            
            bw_price = float(Decimal(str(row.get(self.found_columns.get("bw_price"), '0') if self.found_columns.get("bw_price") else '0').replace(',', '.')))
            color_price = float(Decimal(str(row.get(self.found_columns.get("color_price"), '0') if self.found_columns.get("color_price") else '0').replace(',', '.')))
            
            # Para birimi sütunlarını oku, varsayılan TL
            bw_currency = str(row.get(self.found_columns.get("bw_currency"), 'TL') if self.found_columns.get("bw_currency") else 'TL').strip() or 'TL'
            color_currency = str(row.get(self.found_columns.get("color_currency"), 'TL') if self.found_columns.get("color_currency") else 'TL').strip() or 'TL'
            
            # Cihaz verilerini hazırla
            device_data = {
                'device_model': model,
                'serial_number': serial,  # Artık benzersiz seri numarası
                'brand': (row.get(self.found_columns.get('brand'), 'Kyocera').strip() if self.found_columns.get('brand') else 'Kyocera') or "Bilinmiyor",
                'device_type': dev_type,
                'color_type': color_type,
                'installation_date': (row.get(self.found_columns.get('installation_date'), '').strip() if self.found_columns.get('installation_date') else '') or "Bilinmiyor",
                'notes': (row.get(self.found_columns.get('notes'), '').strip() if self.found_columns.get('notes') else '') or "Bilinmiyor",
                'is_cpc': is_cpc,
                'bw_price': bw_price,
                'bw_currency': bw_currency,
                'color_price': color_price,
                'color_currency': color_currency,
                'location_id': location_id
            }
            
            if existing_device:
                # Mevcut cihazı güncelle
                device_id = existing_device['id']
                result = self.db.save_customer_device(cust_id, device_data, device_id)
                if result is not None:
                    stats['updated_d'] += 1
                    print(f"'{serial}' seri nolu cihaz güncellendi")
                    return True
                else:
                    print(f"✗ Cihaz güncellenemedi: {model}")
                    return False
            else:
                # Yeni cihaz ekle
                device_result = self.db.save_customer_device(cust_id, device_data)
                if device_result:
                    stats['added_d'] += 1
                    print(f"✓ Cihaz eklendi: {model} (Müşteri: {cust_name}, Seri: {serial})")
                    
                    # Sözleşmeli müşteri kontrolü ve otomatik toner ekleme
                    customer_contract = self.db.fetch_one("SELECT is_contract FROM customers WHERE id = ?", (cust_id,))
                    is_contract_customer = customer_contract and customer_contract['is_contract']
                    
                    if is_contract_customer:
                        print(f"DEBUG: Sözleşmeli müşteri için '{model}' cihazının tonerleri otomatik olarak stoğa eklenecek")
                        self._add_device_toners_to_stock(model)
                    
                    return True
                else:
                    print(f"✗ Cihaz eklenemedi: {model} (Müşteri: {cust_name})")
                    return False
                    
        except Exception as e:
            print(f"'{serial}' seri nolu '{model}' cihazı (Müşteri: {cust_name}) işlenirken hata: {e}")
            return False

    def _generate_random_phone(self) -> str:
        """7 haneli rastgele telefon numarası üretir."""
        import random
        # 7 haneli rastgele numara üret (1000000-9999999 arası)
        return str(random.randint(1000000, 9999999))

    def _add_device_toners_to_stock(self, device_model: str):
        """Cihazın tonerlerini otomatik olarak stoka ekler (import sırasında)."""
        try:
            from utils.kyocera_compatibility_scraper import suggest_missing_toners_for_device
            
            # Cihazın uyumlu tonerlerini bul
            missing_toners = suggest_missing_toners_for_device(device_model, self.db)
            
            if not missing_toners:
                print(f"Cihaz {device_model} için toner bulunamadı veya zaten stokta mevcut")
                return
            
            # Tonerleri stoka ekle
            added_count = 0
            for toner in missing_toners:
                try:
                    # Önce bu toner zaten stokta var mı kontrol et
                    existing_toner = self.db.fetch_one("SELECT id FROM stock_items WHERE name = ?", (toner['toner_code'],))
                    
                    if not existing_toner:
                        # Toner stok kartı oluştur
                        self.db.execute_query("""
                            INSERT INTO stock_items 
                            (item_type, name, part_number, description, purchase_price, sale_price, 
                             quantity, min_stock_level, color_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            'Toner',
                            toner['toner_code'],
                            toner['toner_code'],
                            f"Kyocera {toner['color_type']} Toner - {toner['print_capacity']} sayfa kapasiteli",
                            0.00,  # Varsayılan alış fiyatı
                            0.00,  # Varsayılan satış fiyatı
                            1,     # Başlangıç stok miktarı (1 adet olarak ayarla ki görünsün)
                            1,     # Min stok seviyesi
                            toner['color_type']
                        ))
                        added_count += 1
                        print(f"  + {toner['toner_code']} ({toner['color_type']}) toner stoğa eklendi")
                    
                except Exception as e:
                    print(f"Toner {toner['toner_code']} eklenirken hata: {e}")
            
            if added_count > 0:
                print(f"Toplam {added_count} toner stoğa eklendi")
            
        except Exception as e:
            print(f"Cihaz tonerleri eklenirken hata: {e}")

    def _determine_device_type(self, model: str, row) -> str:
        """Cihazın türünü (Renkli/Siyah-Beyaz) akıllıca belirler."""
        # Önce Excel'den gelen type sütununa bak
        type_col = self.found_columns.get("type")
        excel_type = row.get(type_col, '').strip() if type_col else ''
        if excel_type:
            if 'renkli' in excel_type.lower() or 'color' in excel_type.lower():
                return 'Renkli'
            elif 'siyah' in excel_type.lower() or 'mono' in excel_type.lower() or 'bw' in excel_type.lower():
                return 'Siyah-Beyaz'
        
        # Model adında renkli olduğunu gösteren kelimeler
        color_keywords = ['color', 'clr', 'c ', 'renkli', 'colour', ' clp', ' mfp']
        if any(keyword in model.lower() for keyword in color_keywords):
            return 'Renkli'
        
        # Model adında siyah-beyaz olduğunu gösteren kelimeler
        mono_keywords = ['mono', 'bw', 'siyah', ' m', ' p', 'fs-', 'ecosys m']
        if any(keyword in model.lower() for keyword in mono_keywords):
            return 'Siyah-Beyaz'
        
        # Özel durumlar
        if model.upper().startswith('FS-') and ('C' in model.upper() or 'CLP' in model.upper()):
            return 'Renkli'
        
        # Varsayılan olarak siyah-beyaz
        return 'Siyah-Beyaz'

    def _determine_color_type(self, model: str, row) -> str:
        """Cihazın renk tipini belirler."""
        # Önce Excel'den gelen color_type sütununa bak
        color_type_col = self.found_columns.get("color_type")
        excel_color_type = row.get(color_type_col, '').strip() if color_type_col else ''
        if excel_color_type:
            return excel_color_type
        
        # Device type'a göre belirle
        device_type = self._determine_device_type(model, row)
        return device_type

    def _show_import_summary(self, stats: dict):
        """İçe aktarma işleminin özetini gösterir."""
        summary_message = (
            f"İçe aktarma tamamlandı.\n\n"
            f"Eklenen/Güncellenen Müşteri: {stats['added_c'] + stats['updated_c']}\n"
            f"Eklenen Yeni Müşteri: {stats['added_c']}\n"
            f"Bilgisi Güncellenen Müşteri: {stats['updated_c']}\n"
            f"Eklenen Yeni Cihaz: {stats['added_d']}\n"
            f"Güncellenen Mevcut Cihaz: {stats.get('updated_d', 0)}\n"
            f"Model bilgisi olmadığı için atlanan cihaz: {stats['skipped_d']}\n\n"
            "Not: Tüm müşteriler ve modelleri olan tüm cihazlar içe aktarıldı.\n"
            "Boş seri numaraları için AUTO_XXXXXXXX formatında otomatik seri numaraları üretildi.\n"
            "Boş telefon numaraları için 7 haneli rastgele numaralar üretildi.\n"
            "Değişikliklerin yansıması için uygulamayı yeniden başlatmanız önerilir.\n"
            "Alternatif olarak, müşteri/cihaz listesini yenilemek için ilgili sekmeyi kapatıp tekrar açabilirsiniz."
        )
        QMessageBox.information(self, "İşlem Tamamlandı", summary_message)
    
    def _show_import_summary_optimized(self, stats: dict, elapsed_seconds: float):
        """Optimize edilmiş içe aktarma işleminin özetini gösterir (süre bilgisi ile)."""
        summary_message = (
            f"✅ İçe aktarma tamamlandı!\n\n"
            f"⏱️ Süre: {elapsed_seconds:.2f} saniye\n\n"
            f"👥 Müşteriler:\n"
            f"   • Eklenen: {stats['added_c']}\n"
            f"   • Güncellenen: {stats['updated_c']}\n\n"
            f"� Lokasyonlar:\n"
            f"   • Eklenen: {stats.get('added_l', 0)}\n\n"
            f"�🖨️ Cihazlar:\n"
            f"   • Eklenen: {stats['added_d']}\n"
            f"   • Güncellenen: {stats.get('updated_d', 0)}\n"
            f"   • Atlanan: {stats['skipped_d']}\n\n"
            f"📊 Toplam: {stats['added_c'] + stats.get('added_l', 0) + stats['added_d']} kayıt eklendi\n\n"
            "💡 Not: Batch insert optimizasyonu kullanıldı.\n"
            "Değişikliklerin görünmesi için listeyi yenileyin."
        )
        QMessageBox.information(self, "İşlem Tamamlandı", summary_message)

    def _export_to_excel(self):
        """Tüm müşteri ve cihaz verilerini bir Excel dosyasına aktarır."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Excel Olarak Kaydet", 
                                                   "tam_musteri_cihaz_listesi.xlsx", 
                                                   "Excel Dosyaları (*.xlsx)")
        if not file_path:
            return
        
        try:
            import pandas as pd
            customers_data = self.db.get_all_customers_and_devices()
            
            # Yapılandırılmış veriyi düz liste haline getir
            data = []
            customers_list = customers_data.get("customers", [])
            
            for customer in customers_list:
                devices = customer.get("devices", [])
                
                if not devices:
                    # Cihazı olmayan müşteri için boş cihaz satırı ekle
                    data.append([
                        customer.get('id'), customer.get('name', ''), customer.get('phone', ''), 
                        customer.get('email', ''), customer.get('address', ''),
                        None, '', '', '', False, 0, 'TL', 0, 'TL',
                        '', '', ''
                    ])
                else:
                    # Her cihaz için bir satır ekle
                    for device in devices:
                        data.append([
                            customer.get('id'), customer.get('name', ''), customer.get('phone', ''), 
                            customer.get('email', ''), customer.get('address', ''),
                            device.get('id'), device.get('device_model', ''), device.get('serial_number', ''), 
                            device.get('device_type', ''), device.get('is_cpc', False),
                            device.get('cpc_bw_price', 0), device.get('cpc_bw_currency', 'TL'),
                            device.get('cpc_color_price', 0), device.get('cpc_color_currency', 'TL'),
                            device.get('location_name', ''), device.get('location_address', ''), 
                            device.get('location_phone', '')
                        ])
            
            if not data:
                QMessageBox.information(self, "Bilgi", "Dışa aktarılacak veri bulunamadı.")
                return
            
            db_columns = [
                "Musteri ID", "Müşteri Adı", "Telefon", "E-posta", "Adres", 
                "Cihaz ID", "Cihaz Modeli", "Seri No", "Cihaz Türü", "Kopya Başı Mı?",
                "S/B Birim Fiyat", "S/B Para Birimi", "Renkli Birim Fiyat", "Renkli Para Birimi",
                "Lokasyon Adı", "Lokasyon Adresi", "Lokasyon Telefonu"
            ]
            df = pd.DataFrame(data, columns=db_columns)

            final_columns = [
                "Müşteri Adı", "Telefon", "E-posta", "Adres", "Cihaz Modeli", 
                "Seri No", "Cihaz Türü", "Kopya Başı Mı?", "S/B Birim Fiyat", "S/B Para Birimi",
                "Renkli Birim Fiyat", "Renkli Para Birimi", "Lokasyon Adı", "Lokasyon Adresi", "Lokasyon Telefonu"
            ]
            
            df_export = df[final_columns].copy()

            if "Kopya Başı Mı?" in df_export.columns:
                # Pandas uyarılarını önlemek için dtype'ı object'e çevirip map kullan
                df_export["Kopya Başı Mı?"] = df_export["Kopya Başı Mı?"].astype(object).map({True: "Evet", False: "Hayır", 1: "Evet", 0: "Hayır"})

            df_export.to_excel(file_path, index=False)
            
            QMessageBox.information(self, "Başarılı", f"Tüm veriler başarıyla dışa aktarıldı:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası", f"Bir hata oluştu: {e}")
    
    def _export_to_csv(self):
        """Tüm müşteri ve cihaz verilerini CSV dosyasına aktarır (HIZLI - pandas gerektirmez)."""
        import csv
        import logging
        from datetime import datetime
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSV Olarak Kaydet", 
            "tam_musteri_cihaz_listesi.csv", 
            "CSV Dosyaları (*.csv)"
        )
        if not file_path:
            return
        
        try:
            start_time = datetime.now()
            logging.info("CSV export başlatıldı")
            
            customers_data = self.db.get_all_customers_and_devices()
            customers_list = customers_data.get("customers", [])
            
            if not customers_list:
                QMessageBox.information(self, "Bilgi", "Dışa aktarılacak veri bulunamadı.")
                return
            
            # CSV başlıkları
            headers = [
                "Müşteri Adı", "Telefon", "E-posta", "Adres", 
                "Cihaz Modeli", "Seri No", "Cihaz Türü", "Kopya Başı Mı?",
                "S/B Birim Fiyat", "S/B Para Birimi", 
                "Renkli Birim Fiyat", "Renkli Para Birimi",
                "Lokasyon Adı", "Lokasyon Adresi", "Lokasyon Telefonu"
            ]
            
            row_count = 0
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                for customer in customers_list:
                    devices = customer.get("devices", [])
                    
                    if not devices:
                        # Cihazı olmayan müşteri için boş satır
                        writer.writerow([
                            customer.get('name', ''),
                            customer.get('phone', ''),
                            customer.get('email', ''),
                            customer.get('address', ''),
                            '', '', '', 'Hayır', 0, 'TL', 0, 'TL', '', '', ''
                        ])
                        row_count += 1
                    else:
                        # Her cihaz için bir satır
                        for device in devices:
                            writer.writerow([
                                customer.get('name', ''),
                                customer.get('phone', ''),
                                customer.get('email', ''),
                                customer.get('address', ''),
                                device.get('device_model', ''),
                                device.get('serial_number', ''),
                                device.get('device_type', ''),
                                'Evet' if device.get('is_cpc', False) else 'Hayır',
                                device.get('cpc_bw_price', 0),
                                device.get('cpc_bw_currency', 'TL'),
                                device.get('cpc_color_price', 0),
                                device.get('cpc_color_currency', 'TL'),
                                device.get('location_name', ''),
                                device.get('location_address', ''),
                                device.get('location_phone', '')
                            ])
                            row_count += 1
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logging.info(f"CSV export tamamlandı: {row_count} satır, {elapsed:.2f} saniye")
            
            QMessageBox.information(
                self, "Başarılı", 
                f"Tüm veriler başarıyla CSV'ye aktarıldı:\n{file_path}\n\n"
                f"Toplam {row_count} satır, {elapsed:.2f} saniye"
            )
        except Exception as e:
            logging.error(f"CSV export hatası: {e}")
            QMessageBox.critical(self, "Dışa Aktarma Hatası", f"Bir hata oluştu: {e}")