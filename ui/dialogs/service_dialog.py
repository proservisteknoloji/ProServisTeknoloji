from utils.pdf_generator import create_quote_form_pdf
# ui/dialogs/service_dialog.py

from datetime import datetime
from PyQt6.QtWidgets import (QDialog, QFormLayout, QComboBox, QTextEdit, QLineEdit,
                             QDialogButtonBox, QMessageBox, QLabel, QFileDialog, QPushButton)
from utils.workers import EmailThread
from .quote_form_dialog import QuoteFormDialog
from utils.database import db_manager
from utils.email_generator import generate_repaired_email_html, generate_ready_for_delivery_email_html

class ServiceEditDialog(QDialog):
    """Servis kayıtlarını oluşturmak ve düzenlemek için kullanılan diyalog."""

    def __init__(self, db, status_bar=None, record_id: int = None, technician_mode: bool = False, parent=None):
        super().__init__(parent)
        self.db = db
        self.status_bar = status_bar
        self.record_id = record_id
        self.technician_mode = technician_mode
        self.device_id = None
        self.device_type = None
        self.email_thread = None

        self.setWindowTitle("Servis Kaydı Düzenle" if self.record_id else "Yeni Servis Kaydı")
        self.setMinimumWidth(600)

        self._init_ui()
        self._load_initial_data()
        self._connect_signals()
        self._update_device_button()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QFormLayout(self)
        self._create_widgets()
        self._create_layout(layout)

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.customer_combo = QComboBox()
        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("Müşteri ara...")
        self.device_combo = QComboBox()
        self.technician_combo = QComboBox()
        self.problem_input = QTextEdit()
        self.notes_input = QTextEdit()
        self.status_combo = QComboBox()
        if self.technician_mode:
            self.status_combo.addItems([
                'Teknisyene ata',
                'İşleme alındı', 
                'Servise alındı',
                'Parça bekleniyor',
                'Onarıldı',
                'Teslimat Sürecinde',
                'Teslim Edildi',
                'İptal edildi'
            ])
        else:
            self.status_combo.addItems([
                'Teknisyene ata',
                'İşleme alındı',
                'Servise alındı', 
                'Parça bekleniyor',
                'Onarıldı',
                'İptal edildi'
            ])
        self.bw_counter_input = QLineEdit()
        self.color_counter_input = QLineEdit()

        # Teknisyen raporu ve servis formu
        self.technician_report_input = QTextEdit()
        self.technician_report_input.setMaximumHeight(80)
        self.service_form_path = None
        self.upload_form_btn = QPushButton("Servis Formu Yükle")
        self.view_form_btn = QPushButton("Formu Görüntüle")
        self.view_form_btn.setEnabled(False)
        
        # Yazdır ve Mail butonları (Onarıldı durumunda görünür)
        self.print_report_btn = QPushButton("📄 Raporu Yazdır")
        self.print_report_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.print_report_btn.setVisible(False)
        self.send_email_btn = QPushButton("📧 Mail Gönder")
        self.send_email_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.send_email_btn.setVisible(False)
        
        # Parça giriş butonu (sadece "Parça bekleniyor" durumunda görünür)
        self.add_parts_btn = QPushButton("🔧 Parça Giriş/Teklif")
        self.add_parts_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_parts_btn.setVisible(False)  # Başlangıçta gizli

        self.bw_row_label = QLabel("Siyah-Beyaz Sayaç:")
        self.color_row_label = QLabel("Renkli Sayaç:")

        # Yeni müşteri ekleme butonu
        self.add_customer_btn = QPushButton("Yeni Müşteri Ekle")
        self.add_device_btn = QPushButton("Cihaz Ekle")
        self.add_device_btn.setEnabled(False)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)

    def _create_layout(self, layout: QFormLayout):
        """Widget'ları layout'a yerleştirir."""
        # Müşteri arama
        layout.addRow("Müşteri Ara:", self.customer_search)

        # Müşteri satırı - basit tasarım
        from PyQt6.QtWidgets import QHBoxLayout, QWidget
        customer_widget = QWidget()
        customer_layout = QHBoxLayout(customer_widget)
        customer_layout.addWidget(self.customer_combo, 1)
        customer_layout.addWidget(self.add_customer_btn)
        customer_layout.addWidget(self.add_device_btn)
        layout.addRow("Müşteri:", customer_widget)

        layout.addRow("Cihaz:", self.device_combo)
        layout.addRow("Atanan Teknisyen:", self.technician_combo)
        layout.addRow("Bildirilen Arıza:", self.problem_input)
        layout.addRow("Yapılan İşlemler/Notlar:", self.notes_input)
        layout.addRow("Durum:", self.status_combo)
        
        # Parça giriş butonu (Parça bekleniyor durumunda görünür)
        layout.addRow("", self.add_parts_btn)
        
        layout.addRow(self.bw_row_label, self.bw_counter_input)
        layout.addRow(self.color_row_label, self.color_counter_input)
        layout.addRow("Teknisyen Raporu:", self.technician_report_input)

        # Servis formu butonları
        # FIXED: Add parent to prevent memory leak
        form_widget = QWidget(self)
        form_layout = QHBoxLayout(form_widget)
        form_layout.addWidget(self.upload_form_btn)
        form_layout.addWidget(self.view_form_btn)
        form_layout.addStretch()
        layout.addRow("Servis Formu:", form_widget)

        # Yazdır ve Mail butonları (Onarıldı durumunda görünür)
        action_widget = QWidget(self)
        action_layout = QHBoxLayout(action_widget)
        action_layout.addWidget(self.print_report_btn)
        action_layout.addWidget(self.send_email_btn)
        action_layout.addStretch()
        layout.addRow("", action_widget)

        layout.addRow(self.buttons)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.device_combo.currentIndexChanged.connect(self._on_device_selected)
        self.customer_combo.currentIndexChanged.connect(self._update_device_button)
        self.customer_search.textChanged.connect(self._filter_customers)
        self.add_customer_btn.clicked.connect(self._add_new_customer)
        self.add_device_btn.clicked.connect(self._add_device)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        # Servis formu butonları
        self.upload_form_btn.clicked.connect(self._upload_service_form)
        self.view_form_btn.clicked.connect(self._view_service_form)
        
        # Yazdır ve Mail butonları
        self.print_report_btn.clicked.connect(self._print_service_report)
        self.send_email_btn.clicked.connect(self._send_service_email)
        
        # Parça giriş butonu
        self.add_parts_btn.clicked.connect(self._open_quote_dialog)
        
        # Durum değişikliğinde parça butonu görünürlüğünü kontrol et
        self.status_combo.currentTextChanged.connect(self._update_parts_button_visibility)
        self.status_combo.currentTextChanged.connect(self._update_action_buttons_visibility)

        if not self.record_id:
            self.customer_combo.currentIndexChanged.connect(self._update_devices_combo)

    def _load_initial_data(self):
        """Başlangıç verilerini (müşteriler, teknisyenler, kayıt bilgileri) yükler."""
        self._load_combos()
        if self.record_id:
            self._load_record_data()
        else:
            self._update_devices_combo()

    def _load_combos(self):
        """ComboBox'ları veritabanından doldurur."""
        try:
            self._all_customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
            self._update_customer_combo("")

            self.technician_combo.addItem("Atanmadı", None)
            technicians = self.db.get_technicians()
            for tech_id, username in technicians:
                self.technician_combo.addItem(username, tech_id)
        except Exception as e:
            QMessageBox.critical(self, "Veri Yükleme Hatası", f"Müşteri veya teknisyen listesi yüklenemedi: {e}")

    def _update_customer_combo(self, filter_text):
        """Müşteri ComboBox'ını günceller."""
        self.customer_combo.clear()
        for cust_id, name in self._all_customers:
            if filter_text.lower() in name.lower():
                self.customer_combo.addItem(name, cust_id)

    def _filter_customers(self):
        """Müşteri listesini filtreler."""
        filter_text = self.customer_search.text()
        self._update_customer_combo(filter_text)

    def _update_device_button(self):
        """Müşteri seçimine göre cihaz ekle butonunu güncelle."""
        customer_id = self.customer_combo.currentData()
        self.add_device_btn.setEnabled(customer_id is not None)

    def _update_devices_combo(self):
        """Seçili müşteriye ait cihazları ComboBox'a yükler."""
        self.device_combo.clear()
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            self._on_device_selected()
            return

        try:
            query = "SELECT id, device_model, serial_number, device_type FROM customer_devices WHERE customer_id = ?"
            devices = self.db.fetch_all(query, (customer_id,))
            for dev_id, model, serial, dev_type in devices:
                self.device_combo.addItem(f"{model} ({serial})", (dev_id, dev_type))
        except Exception as e:
            QMessageBox.critical(self, "Cihaz Yükleme Hatası", f"Cihazlar yüklenirken bir hata oluştu: {e}")
        finally:
            self._on_device_selected()

    def _on_device_selected(self):
        """Cihaz seçimi değiştiğinde sayaç alanlarının görünürlüğünü ayarlar."""
        data = self.device_combo.currentData()
        if data:
            self.device_id, self.device_type = data
            is_color = self.device_type == "Renkli"
            self.bw_row_label.setVisible(True)
            self.bw_counter_input.setVisible(True)
            self.color_row_label.setVisible(is_color)
            self.color_counter_input.setVisible(is_color)
        else:
            self.device_id, self.device_type = None, None
            self.bw_row_label.setVisible(False)
            self.bw_counter_input.setVisible(False)
            self.color_row_label.setVisible(False)
            self.color_counter_input.setVisible(False)

    def _load_record_data(self):
        """Mevcut bir servis kaydının verilerini forma yükler."""
        self.customer_combo.setEnabled(False)
        self.device_combo.setEnabled(False)
        
        try:
            query = """SELECT c.id, cd.id, cd.device_type, sr.technician_id, sr.problem_description,
                       sr.notes, sr.status, sr.bw_counter, sr.color_counter, sr.technician_report, sr.service_form_pdf_path
                       FROM service_records sr
                       JOIN customer_devices cd ON sr.device_id = cd.id
                       JOIN customers c ON cd.customer_id = c.id
                       WHERE sr.id = ?"""
            data = self.db.fetch_one(query, (self.record_id,))
            if not data:
                QMessageBox.critical(self, "Hata", "Servis kaydı bulunamadı.")
                self.reject()
                return

            cust_id, dev_id, dev_type, tech_id, problem, notes, status, bw, color, technician_report, service_form_path = data
            
            cust_index = self.customer_combo.findData(cust_id)
            if cust_index > -1: self.customer_combo.setCurrentIndex(cust_index)
            
            self._update_devices_combo()
            
            # Cihazı bulmak için daha güvenilir yöntem
            target_device = (dev_id, dev_type.strip() if dev_type else "")
            dev_index = -1
            
            for i in range(self.device_combo.count()):
                item_data = self.device_combo.itemData(i)
                if item_data and len(item_data) == 2:
                    item_dev_id, item_dev_type = item_data
                    # String karşılaştırması için strip ve case-insensitive yap
                    if item_dev_id == dev_id and (item_dev_type or "").strip().lower() == (dev_type or "").strip().lower():
                        dev_index = i
                        break
            
            if dev_index > -1: 
                self.device_combo.setCurrentIndex(dev_index)
                print(f"DEBUG: Cihaz seçildi: {self.device_combo.currentText()}")
            else:
                print(f"DEBUG: Cihaz bulunamadı! Servis kaydındaki cihaz ID {dev_id} ({dev_type}) combo box'ta yok.")
                # Alternatif: İlk cihazı seç
                if self.device_combo.count() > 0:
                    self.device_combo.setCurrentIndex(0)
                    print(f"DEBUG: İlk cihaz seçildi: {self.device_combo.currentText()}")
            
            if dev_index > -1: 
                self.device_combo.setCurrentIndex(dev_index)
                print(f"DEBUG: Cihaz seçildi: {self.device_combo.currentText()}")
            else:
                print(f"DEBUG: Cihaz bulunamadı! Servis kaydındaki cihaz ID {dev_id} combo box'ta yok.")
                # Alternatif: İlk cihazı seç
                if self.device_combo.count() > 0:
                    self.device_combo.setCurrentIndex(0)
                    print(f"DEBUG: İlk cihaz seçildi: {self.device_combo.currentText()}")

            tech_index = self.technician_combo.findData(tech_id)
            if tech_index > -1: self.technician_combo.setCurrentIndex(tech_index)
                
            self.problem_input.setText(problem or "")
            self.notes_input.setText(notes or "")
            self.status_combo.setCurrentText(status)
            self.bw_counter_input.setText(str(bw or ''))
            self.color_counter_input.setText(str(color or ''))
            self.technician_report_input.setText(technician_report or "")
            self.service_form_path = service_form_path
            if self.service_form_path:
                self.view_form_btn.setEnabled(True)
            
            # Parça butonu görünürlüğünü ayarla
            self._update_parts_button_visibility()
            # Aksiyon butonları görünürlüğünü ayarla
            self._update_action_buttons_visibility()
            
        except Exception as e:
            QMessageBox.critical(self, "Veri Yükleme Hatası", f"Servis kaydı verileri yüklenemedi: {e}")
            self.reject()

    def accept(self):
        """Form verilerini doğrular ve kaydeder."""
        if not self._validate_inputs():
            return

        previous_status = self._get_previous_status()

        if self.record_id:
            success = self._update_service_record()
        else:
            success = self._create_service_record()

        if success:
            # Emanet stok sekmesini canlı güncelle
            try:
                main_window = self.parent()
                if hasattr(main_window, 'stock_tab') and hasattr(main_window.stock_tab, 'refresh_emanet_stock'):
                    main_window.stock_tab.refresh_emanet_stock()
            except Exception as e:
                print(f"Emanet stok güncelleme hatası: {e}")
            QMessageBox.information(self, "Başarılı", "Servis kaydı başarıyla kaydedildi.")
            self._handle_status_change(previous_status, self.status_combo.currentText())
            super().accept()

    def _validate_inputs(self) -> bool:
        """Kullanıcı girdilerini doğrular."""
        if not self.device_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir cihaz seçin.")
            return False
        
        try:
            int(self.bw_counter_input.text() or 0)
            if self.device_type == "Renkli":
                int(self.color_counter_input.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "Geçersiz Değer", "Sayaç değerleri sayı olmalıdır.")
            return False
        
        return True

    def _get_previous_status(self):
        if not self.record_id:
            return None
        try:
            result = self.db.fetch_one("SELECT status FROM service_records WHERE id = ?", (self.record_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"Önceki durum alınamadı: {e}")
            return None

    def _collect_data_from_form(self) -> dict:
        """Formdaki verileri bir sözlük olarak toplar."""
        return {
            "device_id": self.device_id,
            "technician_id": self.technician_combo.currentData(),
            "assigned_user_id": self.technician_combo.currentData(),  # Eski uyumluluk için
            "problem_description": self.problem_input.toPlainText(),
            "notes": self.notes_input.toPlainText(),
            "status": self.status_combo.currentText(),
            "bw_counter": int(self.bw_counter_input.text() or 0),
            "color_counter": int(self.color_counter_input.text() or 0) if self.device_type == "Renkli" else None,
            "technician_report": self.technician_report_input.toPlainText(),
            "service_form_pdf_path": self.service_form_path,
        }

    def _create_service_record(self) -> bool:
        """Yeni bir servis kaydı oluşturur ve cihazı emanet stoğa ekler."""
        data = self._collect_data_from_form()
        data["created_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            query = """INSERT INTO service_records (device_id, assigned_user_id, technician_id, problem_description, notes, status, bw_counter, color_counter, created_date, technician_report, service_form_pdf_path)
                       VALUES (:device_id, :assigned_user_id, :technician_id, :problem_description, :notes, :status, :bw_counter, :color_counter, :created_date, :technician_report, :service_form_pdf_path)"""
            new_id = self.db.execute_query(query, data)
            if not new_id:
                raise Exception("Yeni servis ID'si alınamadı.")
            self.record_id = new_id

            # Emanet stok entegrasyonu: Cihazı emanet stoğa ekle
            device_info = self.db.fetch_one("SELECT serial_number, device_model FROM customer_devices WHERE id = ?", (self.device_id,))
            if device_info:
                serial, name = device_info
                if hasattr(self.db, 'add_consignment_device_to_stock'):
                    self.db.add_consignment_device_to_stock({'serial': serial, 'name': name})
            return True
        except Exception as e:
            QMessageBox.critical(self, "Kayıt Hatası", f"Yeni servis kaydı oluşturulamadı: {e}")
            return False

    def _update_service_record(self) -> bool:
        """Mevcut bir servis kaydını günceller."""
        data = self._collect_data_from_form()
        data["id"] = self.record_id
        
        # Eğer durum "Teslim Edildi" ise completed_date güncelle, değilse None
        if data["status"] == "Teslim Edildi":
            data["completed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            data["completed_date"] = None
        
        try:
            query = """UPDATE service_records SET device_id=:device_id, assigned_user_id=:assigned_user_id, technician_id=:technician_id,
                       problem_description=:problem_description, notes=:notes, status=:status, 
                       bw_counter=:bw_counter, color_counter=:color_counter, technician_report=:technician_report, 
                       service_form_pdf_path=:service_form_pdf_path, completed_date=:completed_date WHERE id=:id"""
            self.db.execute_query(query, data)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Güncelleme Hatası", f"Servis kaydı güncellenemedi: {e}")
            return False

    def _handle_status_change(self, previous_status: str, new_status: str):
        """Servis durum değişikliğini işler."""
        if previous_status is None:
            previous_status = ""

        if new_status == previous_status:
            return

        if new_status == "Onarıldı":
            self._process_repaired_service()

        if new_status == "Teslimat Sürecinde":
            self._process_ready_for_delivery()

        if new_status == "İptal edildi":
            self._unassign_technician()
            self._remove_device_from_stock()

        if new_status == "Müşteri Onayı Alınacak":
            self._open_quote_dialog()

        if new_status == "Parça bekleniyor":
            self._open_quote_dialog()
    
    def _update_parts_button_visibility(self):
        """Durum 'Parça bekleniyor' ise parça giriş butonunu göster."""
        current_status = self.status_combo.currentText()
        self.add_parts_btn.setVisible(current_status == "Parça bekleniyor")

    def _update_action_buttons_visibility(self):
        """Durum 'Onarıldı' ise yazdır ve mail butonlarını göster."""
        current_status = self.status_combo.currentText()
        is_repaired = current_status == "Onarıldı"
        self.print_report_btn.setVisible(is_repaired)
        self.send_email_btn.setVisible(is_repaired)

    def _process_repaired_service(self):
        """'Onarıldı' durumuna geçen servis için işlemleri yürütür."""
        self._deduct_stock_for_service()
        try:
            device_info_tuple = self.db.fetch_one("SELECT serial_number FROM customer_devices WHERE id = ?", (self.device_id,))
            if device_info_tuple:
                serial = device_info_tuple[0]
                if hasattr(self.db, 'remove_consignment_device_from_stock'):
                    self.db.remove_consignment_device_from_stock(serial, self.record_id)
            self.db.create_invoice_for_service(self.record_id)
            self._send_repaired_email()
        except Exception as e:
            QMessageBox.warning(self, "Tamamlama Hatası", f"Servis tamamlama işlemleri sırasında bir hata oluştu: {e}")

    def _process_ready_for_delivery(self):
        """'Teslimat Sürecinde' durumuna geçen servis için işlemleri yürütür."""
        try:
            # Emanet stoktan çıkar
            device_info_tuple = self.db.fetch_one("SELECT serial_number FROM customer_devices WHERE id = ?", (self.device_id,))
            if device_info_tuple:
                serial = device_info_tuple[0]
                if hasattr(self.db, 'remove_consignment_device_from_stock'):
                    self.db.remove_consignment_device_from_stock(serial, self.record_id)
            self._remove_device_from_stock()
            self._send_ready_for_delivery_email()
        except Exception as e:
            QMessageBox.warning(self, "Teslimat İşlemleri Hatası", f"Teslimat işlemleri sırasında bir hata oluştu: {e}")

    def _unassign_technician(self):
        """Teknisyeni servisten çıkarır."""
        try:
            self.db.execute_query("UPDATE service_records SET assigned_user_id = NULL WHERE id = ?", (self.record_id,))
        except Exception as e:
            QMessageBox.warning(self, "Teknisyen Çıkarma Hatası", f"Teknisyen servisten çıkarılamadı: {e}")

    def _remove_device_from_stock(self):
        """İptal edilen servis için cihazı stoktan çıkarır."""
        try:
            device_info_tuple = self.db.fetch_one("SELECT serial_number FROM customer_devices WHERE id = ?", (self.device_id,))
            if device_info_tuple:
                self.db.remove_consignment_device_from_stock(device_info_tuple[0], self.record_id)
        except Exception as e:
            QMessageBox.warning(self, "Stok Güncelleme Hatası", f"Cihaz stoktan çıkarılamadı: {e}")

    def _deduct_stock_for_service(self):
        """Serviste kullanılan parçaları stoktan düşer."""
        try:
            items = self.db.get_quote_items(self.record_id)
            if not items: return
            
            errors = []
            for item in items:
                stock_id = item.get('stock_item_id')
                if stock_id:
                    result = self.db.add_stock_movement(
                        item_id=stock_id,
                        movement_type='Çıkış',
                        quantity=int(item.get('quantity', 0)),
                        notes=f"Servis No {self.record_id} için kullanıldı.",
                        related_service_id=self.record_id
                    )
                    if result == "Yetersiz Stok":
                        errors.append(f"- {item.get('description')}: Yetersiz stok!")
            
            if errors:
                QMessageBox.warning(self, "Stok Uyarısı", 
                                    "Servis tamamlandı ancak bazı parçalar stoktan düşülemedi:\n\n" + 
                                    "\n".join(errors) + "\n\nLütfen stok durumunu kontrol edin.")
        except Exception as e:
            QMessageBox.warning(self, "Stok Düşme Hatası", f"Stok düşme işlemi sırasında bir hata oluştu: {e}")

    def _open_quote_dialog(self):
        """Fiyat teklifi formunu açar. CPC cihazları için bedelsiz uyarısı verir."""
        try:
            # CPC kontrolü yap
            is_cpc = False
            if self.device_id:
                device_data = self.db.fetch_one(
                    "SELECT is_cpc FROM customer_devices WHERE id = ?", 
                    (self.device_id,)
                )
                if device_data and device_data[0] == 1:
                    is_cpc = True
                    QMessageBox.information(
                        self, 
                        "CPC Cihaz Uyarısı", 
                        "Bu cihaz CPC sözleşmeli bir cihazdır.\n\n"
                        "Lütfen parça ve işlem girişlerini BEDELSIZ (0 TL) olarak yapınız.\n"
                        "Müşteriden ücret talep edilmeyecektir."
                    )
            
            quote_dialog = QuoteFormDialog(self.record_id, self.db, self.status_bar, self)
            quote_dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Teklif formu açılamadı: {e}")

    def _send_repaired_email(self):
        """'Onarıldı' durumu için detaylı servis tamamlama e-postasını gönderir."""
        try:
            data = self.db.get_full_service_form_data(self.record_id)
            print(f"DEBUG: Service data keys: {list(data.keys()) if data else 'None'}")
            if data and 'main_info' in data:
                print(f"DEBUG: Main info keys: {list(data['main_info'].keys())}")
            if not data:
                QMessageBox.warning(self, "E-posta Hatası", "E-posta için servis verileri alınamadı.")
                return
            
            customer_email = data['main_info'].get('customer_email')
            if not customer_email:
                QMessageBox.information(self, "Bilgi", "Müşterinin kayıtlı bir e-posta adresi yok, e-posta gönderilmedi.")
                return
            
            smtp_settings = self.db.get_all_smtp_settings()
            required_fields = ['smtp_host', 'smtp_port', 'smtp_user']
            missing_fields = [field for field in required_fields if not smtp_settings.get(field)]
            if missing_fields:
                QMessageBox.critical(self, "SMTP Hatası", "Lütfen Ayarlar menüsünden SMTP bilgilerini eksiksiz doldurun.")
                return
            
            email_smtp_settings = {
                'host': smtp_settings['smtp_host'],
                'port': smtp_settings['smtp_port'],
                'user': smtp_settings['smtp_user'],
                'password': smtp_settings['smtp_password'],
                'encryption': smtp_settings['smtp_encryption']
            }
            
            # HTML mail içeriği oluştur
            html_body = generate_repaired_email_html(data)
            subject = f"{data['company_info']['company_name']} - Servis Tamamlama Raporu (Servis No: {self.record_id})"
            
            # PDF eki oluştur (ReportLab ile)
            import tempfile
            import os
            from utils.pdf_generator import create_service_report_pdf
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_pdf_path = temp_file.name
            
            # PDF'i ReportLab ile oluştur
            if not create_service_report_pdf(data, temp_pdf_path):
                QMessageBox.warning(self, "Uyarı", "PDF eki oluşturulamadı, sadece mail gönderilecek.")
                temp_pdf_path = None
            
            # PDF verisini oku
            attachments = []
            if temp_pdf_path:
                try:
                    with open(temp_pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    customer_name = data.get('main_info', {}).get('customer_name', 'Musteri')
                    import re
                    customer_name_clean = re.sub(r'[^\w\s-]', '', customer_name).strip().replace(' ', '_')
                    pdf_filename = f"{customer_name_clean}_servis_raporu_{self.record_id}.pdf"
                    
                    attachments = [{
                        'filename': pdf_filename,
                        'data': pdf_data,
                        'content_type': 'application/pdf'
                    }]
                    
                    os.unlink(temp_pdf_path)
                except Exception as e:
                    print(f"PDF eki hatası: {e}")
            message_details = {
                'recipient': customer_email, 
                'subject': subject, 
                'body': html_body,
                'sender_name': data['company_info']['company_name'],
                'attachments': attachments
            }
            
            self.email_thread = EmailThread(email_smtp_settings, message_details)
            if self.status_bar:
                self.email_thread.task_finished.connect(lambda msg: self.status_bar.showMessage(msg, 5000))
            self.email_thread.task_error.connect(lambda err: QMessageBox.critical(self, "E-posta Gönderme Hatası", err))
            self.email_thread.start()

            if self.status_bar:
                self.status_bar.showMessage(f"Onarım bilgisi e-postası {customer_email} adresine gönderiliyor...", 5000)
        except Exception as e:
            QMessageBox.critical(self, "E-posta Hatası", f"E-posta gönderimi sırasında beklenmedik bir hata oluştu: {e}")

    def _send_ready_for_delivery_email(self):
        """'Teslimat Sürecinde' durumu için e-posta gönderir."""
        try:
            data = self.db.get_full_service_form_data(self.record_id)
            if not data:
                QMessageBox.warning(self, "E-posta Hatası", "E-posta için servis verileri alınamadı.")
                return
            
            customer_email = data['main_info'].get('customer_email')
            if not customer_email:
                QMessageBox.information(self, "Bilgi", "Müşterinin kayıtlı bir e-posta adresi yok, e-posta gönderilmedi.")
                return
            
            smtp_settings = self.db.get_all_smtp_settings()
            required_fields = ['smtp_host', 'smtp_port', 'smtp_user']
            missing_fields = [field for field in required_fields if not smtp_settings.get(field)]
            if missing_fields:
                QMessageBox.critical(self, "SMTP Hatası", "Lütfen Ayarlar menüsünden SMTP bilgilerini eksiksiz doldurun.")
                return
            
            email_smtp_settings = {
                'host': smtp_settings['smtp_host'],
                'port': smtp_settings['smtp_port'],
                'user': smtp_settings['smtp_user'],
                'password': smtp_settings['smtp_password'],
                'encryption': smtp_settings['smtp_encryption']
            }
            
            html_body = generate_ready_for_delivery_email_html(data)
            subject = f"{data['company_info']['company_name']} - Cihazınız Teslim Edilecek (Servis No: {self.record_id})"
            message_details = {
                'recipient': customer_email, 
                'subject': subject, 
                'body': html_body,
                'sender_name': data['company_info']['company_name']
            }
            
            self.email_thread = EmailThread(email_smtp_settings, message_details)
            if self.status_bar:
                self.email_thread.task_finished.connect(lambda msg: self.status_bar.showMessage(msg, 5000))
            self.email_thread.task_error.connect(lambda err: QMessageBox.critical(self, "E-posta Gönderme Hatası", err))
            self.email_thread.start()

            if self.status_bar:
                self.status_bar.showMessage(f"Teslimat bilgisi e-postası {customer_email} adresine gönderiliyor...", 5000)
        except Exception as e:
            QMessageBox.critical(self, "E-posta Hatası", f"E-posta gönderimi sırasında beklenmedik bir hata oluştu: {e}")

    def _send_completion_email(self):
        """Geriye dönük uyumluluk için - artık _send_repaired_email kullanılıyor."""
        self._send_repaired_email()

    def _print_service_report(self):
        """Servis raporunu yazdır veya kaydet."""
        try:
            from utils.pdf_generator import create_service_report_pdf
            import os
            from datetime import datetime
            
            # Servis verilerini al
            data = self.db.get_full_service_form_data(self.record_id)
            if not data:
                QMessageBox.warning(self, "Hata", "Rapor için servis verileri alınamadı.")
                return
            
            # Müşteri adını al ve dosya adı oluştur
            customer_name = data.get('main_info', {}).get('customer_name', 'Musteri')
            # Özel karakterleri temizle
            import re
            customer_name_clean = re.sub(r'[^\w\s-]', '', customer_name).strip().replace(' ', '_')
            
            # Varsayılan masaüstü yolu
            default_desktop = os.path.expanduser('~/Desktop')
            
            # Kullanıcıya kayıt yeri seçtirt
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Servis Raporunu Kaydet", 
                os.path.join(default_desktop, f"{customer_name_clean}_servis_raporu_{self.record_id}.pdf"), 
                "PDF Dosyaları (*.pdf)"
            )
            
            if not file_path:
                return  # Kullanıcı vazgeçti
            
            # PDF oluştur
            if create_service_report_pdf(data, file_path):
                QMessageBox.information(self, "Başarılı", f"Servis raporu başarıyla kaydedildi:\n{file_path}")
                
                # PDF'i otomatik aç
                try:
                    if os.name == 'nt':
                        os.startfile(file_path)
                    else:
                        os.system(f'xdg-open "{file_path}"')
                except Exception as e:
                    QMessageBox.warning(self, "Uyarı", f"PDF otomatik açılamadı: {e}\nDosya kaydedildi.")
            else:
                QMessageBox.critical(self, "Hata", "PDF raporu oluşturulamadı.")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor kaydedilirken hata: {e}")

    def _send_service_email(self):
        """Servis raporunu mail olarak gönder."""
        try:
            # Mevcut _send_repaired_email fonksiyonunu kullan
            self._send_repaired_email()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Mail gönderilirken hata: {e}")

    def _upload_service_form(self):
        """Servis formu PDF'ini yükler."""
        import os
        import shutil
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Servis Formu PDF'ini Seç", "", "PDF Dosyaları (*.pdf)"
        )
        
        if file_path:
            try:
                # service_forms dizinini oluştur
                forms_dir = os.path.join(os.path.dirname(__file__), "..", "..", "service_forms")
                os.makedirs(forms_dir, exist_ok=True)
                
                # Dosyayı kopyala
                filename = f"servis_formu_{self.record_id or 'yeni'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                dest_path = os.path.join(forms_dir, filename)
                shutil.copy2(file_path, dest_path)
                
                self.service_form_path = dest_path
                self.view_form_btn.setEnabled(True)
                QMessageBox.information(self, "Başarılı", "Servis formu başarıyla yüklendi.")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Servis formu yüklenirken hata: {e}")

    def _view_service_form(self):
        """Yüklenmiş servis formunu görüntüler."""
        import os

        if self.service_form_path and os.path.exists(self.service_form_path):
            try:
                if os.name == 'nt':
                    os.startfile(self.service_form_path)
                else:
                    os.system(f'xdg-open "{self.service_form_path}"')
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"PDF açılırken hata: {e}")
        else:
            QMessageBox.warning(self, "Hata", "Görüntülenecek servis formu bulunamadı.")

    def _add_new_customer(self):
        """Yeni müşteri ekleme dialog'unu açar."""
        try:
            from ui.dialogs.customer_dialog import CustomerDialog
            dialog = CustomerDialog(self.db, customer_id=None, parent=self)
            if dialog.exec():
                # Müşteri eklendi - müşteri listesini yeniden yükle
                self._all_customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
                self._update_customer_combo("")
                
                # Yeni müşteriyi seç (son eklenen müşteri en yüksek ID'ye sahip)
                if self._all_customers:
                    # En yüksek ID'li müşteriyi bul (en son eklenen)
                    last_customer_id = max(cust[0] for cust in self._all_customers)
                    index = self.customer_combo.findData(last_customer_id)
                    if index >= 0:
                        self.customer_combo.setCurrentIndex(index)
                        # Cihaz listesini de güncelle
                        self._update_devices_combo()
                
                # Customer tab'ı yenile
                try:
                    main_window = self.parent()
                    if hasattr(main_window, 'customer_device_tab'):
                        main_window.customer_device_tab.refresh_customers()
                        main_window.customer_device_tab.data_changed.emit()
                except Exception as e:
                    print(f"Customer tab refresh hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yeni müşteri eklenirken hata: {e}")

    def _add_device(self):
        """Seçili müşteriye cihaz ekleme dialog'unu açar."""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "Uyarı", "Önce bir müşteri seçin.")
            return

        try:
            from ui.dialogs.device_dialog import DeviceDialog
            dialog = DeviceDialog(self.db, customer_id, parent=self)
            if dialog.exec():
                # Cihaz eklendi, cihaz listesini yenile
                self._update_devices_combo()
                # Yeni eklenen cihazı seç (son eklenen)
                if self.device_combo.count() > 0:
                    self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
                # Customer tab'ı yenile
                try:
                    main_window = self.parent()
                    if hasattr(main_window, 'customer_device_tab'):
                        main_window.customer_device_tab.refresh_customers()
                        main_window.customer_device_tab.data_changed.emit()
                except Exception as e:
                    print(f"Customer tab refresh hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Cihaz Diyaloğu Hatası", f"Cihaz ekleme/düzenleme penceresi açılamadı: {e}")
