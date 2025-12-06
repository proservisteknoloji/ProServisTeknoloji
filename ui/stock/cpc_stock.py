"""CPC Stok Yönetim Modülü"""

import logging
from PyQt6.QtWidgets import QMessageBox


class CPCStockManager:
    """CPC stok işlemlerini yöneten sınıf."""
    
    def __init__(self, parent):
        self.parent_widget = parent
        self.db = parent.db
    
    def load_cpc_devices(self):
        """CPC müşterilerinin cihazlarını listeler."""
        try:
            self.parent_widget.cpc_device_table.setRowCount(0)
            
            # Müşteri filtresini al
            search_text = self.parent_widget.cpc_filter_input.text().strip()
            
            # CPC müşterileri ve cihazlarını getir
            if search_text:
                devices = self.db.fetch_all("""
                    SELECT 
                        cd.id,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        cl.location_name as location,
                        cd.brand as device_brand,
                        cd.device_model,
                        cd.device_type,
                        cd.color_type
                    FROM customer_devices cd
                    INNER JOIN customers c ON cd.customer_id = c.id
                    LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                    WHERE cd.is_cpc = 1 AND (
                        c.name LIKE ? OR
                        c.phone LIKE ? OR
                        cl.location_name LIKE ? OR
                        cd.device_model LIKE ?
                    )
                    ORDER BY c.name, cl.location_name
                """, (f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", f"%{search_text}%"))
            else:
                devices = self.db.fetch_all("""
                    SELECT 
                        cd.id,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        cl.location_name as location,
                        cd.brand as device_brand,
                        cd.device_model,
                        cd.device_type,
                        cd.color_type
                    FROM customer_devices cd
                    INNER JOIN customers c ON cd.customer_id = c.id
                    LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                    WHERE cd.is_cpc = 1
                    ORDER BY c.name, cl.location_name
                """)
            
            if not devices:
                logging.info("CPC cihazı bulunamadı")
                return
            
            # Tabloyu doldur
            self.parent_widget.cpc_device_table.setRowCount(len(devices))
            for row, device in enumerate(devices):
                from PyQt6.QtWidgets import QTableWidgetItem
                self.parent_widget.cpc_device_table.setItem(row, 0, QTableWidgetItem(str(device['id'])))
                self.parent_widget.cpc_device_table.setItem(row, 1, QTableWidgetItem(device['customer_name'] or ''))
                self.parent_widget.cpc_device_table.setItem(row, 2, QTableWidgetItem(device['customer_phone'] or ''))
                self.parent_widget.cpc_device_table.setItem(row, 3, QTableWidgetItem(device['location'] or ''))
                self.parent_widget.cpc_device_table.setItem(row, 4, QTableWidgetItem(device['device_brand'] or ''))
                self.parent_widget.cpc_device_table.setItem(row, 5, QTableWidgetItem(device['device_model'] or ''))
                self.parent_widget.cpc_device_table.setItem(row, 6, QTableWidgetItem(device['device_type'] or ''))
                self.parent_widget.cpc_device_table.setItem(row, 7, QTableWidgetItem(device['color_type'] or ''))
            
            # Sütun 0'ı gizle (ID)
            self.parent_widget.cpc_device_table.setColumnHidden(0, True)
            
        except Exception as e:
            logging.error(f"CPC cihazlar yüklenirken hata: {e}")
            QMessageBox.critical(self.parent_widget, "Hata", f"CPC cihazlar yüklenirken hata oluştu: {e}")
    
    def cpc_device_selected(self):
        """CPC cihaz seçildiğinde tonerleri listeler ve detayları gösterir."""
        try:
            current_row = self.parent_widget.cpc_device_table.currentRow()
            if current_row >= 0:
                device_id = int(self.parent_widget.cpc_device_table.item(current_row, 0).text())
                
                # Cihaz bilgilerini al
                customer_name = self.parent_widget.cpc_device_table.item(current_row, 1).text() if self.parent_widget.cpc_device_table.item(current_row, 1) else "N/A"
                customer_phone = self.parent_widget.cpc_device_table.item(current_row, 2).text() if self.parent_widget.cpc_device_table.item(current_row, 2) else "N/A"
                location = self.parent_widget.cpc_device_table.item(current_row, 3).text() if self.parent_widget.cpc_device_table.item(current_row, 3) else "N/A"
                brand = self.parent_widget.cpc_device_table.item(current_row, 4).text() if self.parent_widget.cpc_device_table.item(current_row, 4) else "N/A"
                model = self.parent_widget.cpc_device_table.item(current_row, 5).text() if self.parent_widget.cpc_device_table.item(current_row, 5) else "N/A"
                device_type = self.parent_widget.cpc_device_table.item(current_row, 6).text() if self.parent_widget.cpc_device_table.item(current_row, 6) else "N/A"
                color_type = self.parent_widget.cpc_device_table.item(current_row, 7).text() if self.parent_widget.cpc_device_table.item(current_row, 7) else "N/A"
                
                # Detayları göster
                details = f"""
📋 Cihaz Detayları
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Müşteri: {customer_name}
📞 Telefon: {customer_phone}
📍 Lokasyon: {location}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 Marka: {brand}
🖨️ Model: {model}
📦 Tip: {device_type}
🎨 Renk Tipi: {color_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """.strip()
                
                self.parent_widget.cpc_details_text.setPlainText(details)
                
                # Tonerleri yükle
                self.load_cpc_toners(device_id)
        except Exception as e:
            logging.error(f"CPC cihaz seçimi hatası: {e}")
    
    def load_cpc_toners(self, device_id: int):
        """Belirtilen cihazın CPC toner ve kitlerini listeler (cpc_stock_items tablosundan)."""
        try:
            # Cihaz bilgilerini al
            device_data = self.db.get_customer_device(device_id)
            if not device_data:
                return
                
            device_model = device_data['device_model']
            
            # cpc_stock_items tablosundan cihaza ait toner ve kitleri al
            cpc_items = self.db.fetch_all("""
                SELECT 
                    csi.id,
                    csi.toner_code,
                    csi.toner_name,
                    csi.color,
                    csi.quantity,
                    si.quantity as stock_quantity,
                    si.item_type as stock_type
                FROM cpc_stock_items csi
                LEFT JOIN stock_items si ON si.part_number = csi.toner_code
                WHERE csi.device_id = ?
                ORDER BY 
                    CASE WHEN csi.color = 'Kit' THEN 1 ELSE 0 END,
                    csi.toner_name
            """, (device_id,))
            
            if not cpc_items:
                logging.warning(f"Cihaz için toner/kit bulunamadı: {device_model}")
                self.parent_widget.cpc_toner_table.setRowCount(0)
                return
            
            # Toner/Kit tablosunu doldur
            self.parent_widget.cpc_toner_table.setRowCount(len(cpc_items))
            for row, item in enumerate(cpc_items):
                from PyQt6.QtWidgets import QTableWidgetItem
                self.parent_widget.cpc_toner_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
                self.parent_widget.cpc_toner_table.setItem(row, 1, QTableWidgetItem(item['toner_code'] or ''))
                self.parent_widget.cpc_toner_table.setItem(row, 2, QTableWidgetItem(item['toner_name'] or ''))
                
                # Tip göster (Toner veya Kit)
                display_color = item['color'] or ''
                if display_color == 'Kit':
                    display_color = '🔧 Kit'
                self.parent_widget.cpc_toner_table.setItem(row, 3, QTableWidgetItem(display_color))
                
                # CPC stok miktarı
                cpc_qty = item['quantity'] if item['quantity'] is not None else 0
                self.parent_widget.cpc_toner_table.setItem(row, 4, QTableWidgetItem(str(cpc_qty)))
                
                # Ana stok miktarı
                stock_qty = item['stock_quantity'] if item['stock_quantity'] is not None else 0
                self.parent_widget.cpc_toner_table.setItem(row, 5, QTableWidgetItem(str(stock_qty)))
            
            # ID sütununu gizle
            self.parent_widget.cpc_toner_table.setColumnHidden(0, True)
            
        except Exception as e:
            logging.error(f"CPC toner/kit listesi yükleme hatası: {e}")
            QMessageBox.critical(self.parent_widget, "Hata", f"CPC toner/kit listesi yüklenirken hata oluştu: {e}")
    
    def add_toners_for_cpc_device(self, device_id: int, device_model: str):
        """CPC cihazı için toner/kit ekler ve otomatik uyumlu tonerleri de stoka ekler."""
        try:
            from ..dialogs.cpc_toner_dialog import CPCTonerDialog
            from utils.kyocera_compatibility_scraper import suggest_missing_toners_for_device
            # Cihaz bilgilerini al
            device_data = self.db.get_customer_device(device_id)
            if not device_data:
                QMessageBox.warning(self.parent_widget, "Uyarı", "Cihaz bilgileri alınamadı!")
                return
            device_color_type = device_data.get('color_type', 'Siyah-Beyaz')

            # 1. Otomatik uyumlu tonerleri stoka ekle (normal cihaz ekleme mantığı)
            missing_toners = suggest_missing_toners_for_device(device_model, self.db)
            added_count = 0
            toner_names = []
            for toner in missing_toners:
                try:
                    toner_data = {
                        'item_type': 'Toner',
                        'name': toner['toner_code'],
                        'part_number': toner['toner_code'],
                        'description': f"Kyocera {toner['color_type']} Toner - {toner['print_capacity']} sayfa kapasiteli - {device_model} uyumlu",
                        'supplier': 'Kyocera',
                        'quantity': 0,
                        'purchase_price': 0.00,
                        'purchase_currency': 'TL',
                        'sale_price': 0.00,
                        'sale_currency': 'TL',
                        'color_type': toner['color_type']
                    }
                    saved_id = self.db.save_stock_item(toner_data, None)
                    if saved_id:
                        added_count += 1
                        toner_names.append(toner['toner_code'])
                        logging.info(f"CPC cihaz için otomatik toner eklendi: {toner['toner_code']}")
                except Exception as toner_error:
                    logging.warning(f"CPC cihaz için toner eklenemedi {toner['toner_code']}: {toner_error}")
                    continue
            if added_count > 0:
                QMessageBox.information(
                    self.parent_widget, "Otomatik Toner Eklendi",
                    f"✅ CPC cihaz '{device_model}' için {added_count} adet toner otomatik olarak stoka eklendi:\n\n"
                    f"📝 Tonerler: {', '.join(toner_names)}\n\n"
                    f"💡 Bu tonerlerin fiyatlarını ve stok miktarlarını güncelleyebilirsiniz."
                )

            # 2. Manuel ekleme dialog'u aç
            dialog = CPCTonerDialog(device_model, device_color_type, device_id, self.parent_widget)
            if dialog.exec():
                # Toner ve kit verilerini al
                toner_added_count = self.add_manual_toners_to_stock_for_cpc(dialog, device_id, device_model, device_color_type)
                kit_added_count = self.add_manual_kits_to_stock_for_cpc(dialog, device_id, device_model)
                if toner_added_count > 0 or kit_added_count > 0:
                    QMessageBox.information(
                        self.parent_widget, 
                        "Başarılı", 
                        f"{toner_added_count} toner ve {kit_added_count} kit stoka eklendi."
                    )
                    # Toner listesini güncelle
                    self.load_cpc_toners(device_id)
                else:
                    QMessageBox.warning(self.parent_widget, "Uyarı", "Eklenen toner veya kit bulunamadı!")
        except Exception as e:
            logging.error(f"CPC toner ekleme hatası: {e}")
            QMessageBox.critical(self.parent_widget, "Hata", f"Toner eklenirken hata oluştu: {e}")
    
    def add_manual_toners_to_stock_for_cpc(self, dialog, device_id: int, device_model: str, device_color_type: str) -> int:
        """CPC için dialog'dan girilen manuel toner kodlarını stoka VE cpc_stock_items tablosuna ekler."""
        try:
            toner_data = dialog.get_toner_data()
            color_type = device_color_type  # Cihazın gerçek renk tipini kullan
            added_count = 0
            
            # Debug log
            logging.info(f"add_manual_toners_to_stock_for_cpc çağrıldı - Cihaz: {device_model}, Renk Tipi: {color_type}")
            logging.info(f"Toner Data: {toner_data}")

            if color_type == 'Renkli':
                # Orijinal ve muadil tonerleri ekle
                toner_codes = [
                    ('black', 'Siyah', 'Orijinal', 'black'),
                    ('black_equivalent', 'Siyah', 'Muadil', 'black'),
                    ('cyan', 'Mavi', 'Orijinal', 'cyan'),
                    ('cyan_equivalent', 'Mavi', 'Muadil', 'cyan'),
                    ('magenta', 'Kırmızı', 'Orijinal', 'magenta'),
                    ('magenta_equivalent', 'Kırmızı', 'Muadil', 'magenta'),
                    ('yellow', 'Sarı', 'Orijinal', 'yellow'),
                    ('yellow_equivalent', 'Sarı', 'Muadil', 'yellow')
                ]

                for field, renk_ad, toner_type, color_code in toner_codes:
                    kod = toner_data.get(field, '').strip()
                    if kod:
                        # Toner adına renk kodu ve (muadil) ekle
                        if toner_type == 'Muadil':
                            toner_name = f"{kod} ({color_code}) (muadil)"
                            part_number = f"{kod} ({color_code}) (muadil)"
                        else:
                            toner_name = f"{kod} ({color_code})"
                            part_number = f"{kod} ({color_code})"

                        # Stokta var mı kontrol et - renk tipini de kontrol et
                        existing = self.db.fetch_one(
                            "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?) AND color_type = ?",
                            (toner_name, part_number, renk_ad)
                        )

                        if not existing:
                            new_toner_data = {
                                'item_type': 'Toner',
                                'name': toner_name,
                                'part_number': part_number,
                                'description': f"{renk_ad} Toner - {toner_type} - {device_model} için eklendi",
                                'quantity': 0,  # Başlangıç miktarı 0 yap
                                'purchase_price': 0.0,
                                'purchase_currency': 'TL',
                                'sale_price': 0.0,
                                'sale_currency': 'TL',
                                'supplier': '',
                                'is_consignment': 0,
                                'color_type': renk_ad,
                                'compatible_models': device_model  # Cihaz modelini otomatik ekle
                            }

                            saved_id = self.db.save_stock_item(new_toner_data, None)
                            if saved_id:
                                added_count += 1
                                logging.info(f"CPC toner eklendi: {toner_name} ({renk_ad}) - Cihaz: {device_model}")
                                # cpc_stock_items tablosuna da ekle
                                self.db.add_cpc_stock_item(
                                    device_id=device_id,
                                    toner_code=part_number,
                                    toner_name=toner_name,
                                    color=renk_ad,
                                    quantity=0,
                                    min_quantity=5
                                )

            else:
                # Siyah-beyaz cihaz için orijinal ve muadil siyah toner
                for field, toner_type in [('black', 'Orijinal'), ('black_equivalent', 'Muadil')]:
                    kod = toner_data.get(field, '').strip()
                    if kod:
                        # Toner adına renk kodu ve (muadil) ekle
                        if toner_type == 'Muadil':
                            toner_name = f"{kod} (black) (muadil)"
                            part_number = f"{kod} (black) (muadil)"
                        else:
                            toner_name = f"{kod} (black)"
                            part_number = f"{kod} (black)"

                        # Stokta var mı kontrol et - renk tipini de kontrol et
                        existing = self.db.fetch_one(
                            "SELECT id FROM stock_items WHERE item_type = 'Toner' AND (name = ? OR part_number = ?) AND color_type = 'Siyah'",
                            (toner_name, part_number)
                        )

                        if not existing:
                            new_toner_data = {
                                'item_type': 'Toner',
                                'name': toner_name,
                                'part_number': part_number,
                                'description': f"Siyah Toner - {toner_type} - {device_model} için eklendi",
                                'quantity': 0,  # Başlangıç miktarı 0 yap
                                'purchase_price': 0.0,
                                'purchase_currency': 'TL',
                                'sale_price': 0.0,
                                'sale_currency': 'TL',
                                'supplier': '',
                                'is_consignment': 0,
                                'color_type': 'Siyah',
                                'compatible_models': device_model  # Cihaz modelini otomatik ekle
                            }

                            saved_id = self.db.save_stock_item(new_toner_data, None)
                            if saved_id:
                                added_count += 1
                                logging.info(f"CPC toner eklendi: {toner_name} (Siyah) - Cihaz: {device_model}")
                                # cpc_stock_items tablosuna da ekle
                                self.db.add_cpc_stock_item(
                                    device_id=device_id,
                                    toner_code=part_number,
                                    toner_name=toner_name,
                                    color='Siyah',
                                    quantity=0,
                                    min_quantity=5
                                )
            
            return added_count

        except Exception as e:
            logging.error(f"CPC toner ekleme hatası: {e}")
            QMessageBox.critical(self.parent_widget, "Hata", f"Toner eklenirken hata oluştu: {e}")
            return 0

    def add_manual_kits_to_stock_for_cpc(self, dialog, device_id: int, device_model: str) -> int:
        """CPC için dialog'dan girilen manuel kit kodlarını stock_items VE cpc_stock_items tablosuna ekler.
        NOT: Kit'ler de cihaza özel olduğu için cpc_stock_items'a eklenir."""
        try:
            kit_data = dialog.get_kit_data()
            added_count = 0

            # Tüm kit girişlerini kontrol et
            kit_codes = [
                kit_data.get('kit1', '').strip(),
                kit_data.get('kit2', '').strip(),
                kit_data.get('kit3', '').strip(),
                kit_data.get('kit4', '').strip()
            ]

            for kit_code in kit_codes:
                if kit_code:  # Boş olmayan kit kodları için
                    kit_name = f"{kit_code}"
                    part_number = f"{kit_code}"

                    # Stokta var mı kontrol et
                    existing = self.db.fetch_one(
                        "SELECT id FROM stock_items WHERE item_type = 'Kit' AND part_number = ?",
                        (part_number,)
                    )

                    if not existing:
                        new_kit_data = {
                            'item_type': 'Kit',
                            'name': kit_name,
                            'part_number': part_number,
                            'description': f"Kit - {device_model} için eklendi",
                            'quantity': 0,  # Başlangıç miktarı 0
                            'purchase_price': 0.0,
                            'purchase_currency': 'TL',
                            'sale_price': 0.0,
                            'sale_currency': 'TL',
                            'supplier': '',
                            'is_consignment': 0,
                            'color_type': '',  # Kitler için renk tipi yok
                            'compatible_models': device_model  # Cihaz modelini otomatik ekle
                        }

                        saved_id = self.db.save_stock_item(new_kit_data, None)
                        if saved_id:
                            added_count += 1
                            logging.info(f"Kit stoka eklendi: {kit_name} - Cihaz: {device_model}")
                    
                    # cpc_stock_items tablosunda var mı kontrol et (bu cihaz için)
                    cpc_existing = self.db.fetch_one(
                        "SELECT id FROM cpc_stock_items WHERE device_id = ? AND toner_code = ?",
                        (device_id, part_number)
                    )
                    
                    if not cpc_existing:
                        # cpc_stock_items tablosuna ekle (cihaza özel)
                        self.db.add_cpc_stock_item(
                            device_id=device_id,
                            toner_code=part_number,
                            toner_name=kit_name,
                            color='Kit',  # Kit için özel işaret
                            quantity=0,
                            min_quantity=2
                        )
                        added_count += 1
                        logging.info(f"Kit CPC stoka eklendi: {kit_name} - Device ID: {device_id}")

            return added_count

        except Exception as e:
            logging.error(f"CPC kit ekleme hatası: {e}")
            QMessageBox.critical(self.parent_widget, "Hata", f"Kit eklenirken hata oluştu: {e}")
            return 0
    
    def filter_cpc_devices(self):
        """CPC cihaz filtresini uygular."""
        self.load_cpc_devices()
    
    def add_cpc_toner(self):
        """Seçili CPC cihazı için toner/kit ekler."""
        try:
            current_row = self.parent_widget.cpc_device_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self.parent_widget, "Uyarı", "Lütfen bir cihaz seçin!")
                return
            
            device_id = int(self.parent_widget.cpc_device_table.item(current_row, 0).text())
            device_model = self.parent_widget.cpc_device_table.item(current_row, 5).text()
            
            self.add_toners_for_cpc_device(device_id, device_model)
            
        except Exception as e:
            logging.error(f"CPC toner ekleme hatası: {e}")
            QMessageBox.critical(self.parent_widget, "Hata", f"Toner eklenirken hata oluştu: {e}")
    
    def view_cpc_history(self):
        """CPC cihaz geçmişini gösterir."""
        QMessageBox.information(self.parent_widget, "Bilgi", "CPC geçmiş görüntüleme özelliği yakında eklenecek.")
