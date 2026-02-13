# ui/service_tab.py

import logging
logger = logging.getLogger(__name__)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLabel, QMessageBox, QComboBox,
                             QGroupBox, QGridLayout)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal as Signal
from .dialogs.service_dialog import ServiceEditDialog
from .dialogs.device_history_dialog import DeviceHistoryDialog
from .dialogs.customer_service_history_dialog import CustomerServiceHistoryDialog
from utils.database import db_manager

class ServiceTab(QWidget):
    """Servis kayıtlarını yöneten sekme."""
    data_changed = Signal()

    def __init__(self, db, status_bar, parent=None):
        super().__init__(parent)
        self.db = db
        self.status_bar = status_bar
        self.technician_user_id = None
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        filter_panel = self._create_filter_panel()
        self.service_table = self._create_service_table()
        
        main_layout.addWidget(filter_panel)
        main_layout.addWidget(self.service_table)

        self._connect_signals()

    def _create_filter_panel(self):
        """Filtreleme ve butonları içeren modern paneli oluşturur."""
        from PyQt6.QtWidgets import QGridLayout, QGroupBox

        filter_group = QGroupBox("Filtreler ve Aksiyonlar")
        filter_layout = QGridLayout(filter_group)

        # Arama
        filter_layout.addWidget(QLabel("Ara:"), 0, 0)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Müşteri, model, teknisyen veya arıza ile ara...")
        self.filter_input.setClearButtonEnabled(True)
        filter_layout.addWidget(self.filter_input, 0, 1, 1, 2)

        # Durum filtresi
        filter_layout.addWidget(QLabel("Durum:"), 1, 0)
        self.status_filter = QComboBox()
        self.status_filter.addItem("Tümü", "")
        statuses = [
            'Teknisyene ata',
            'İşleme alındı',
            'Servise alındı',
            'Müşteri Onayı Alınacak',
            'Parça bekleniyor',
            'Onarıldı',
            'Teslimat Sürecinde',
            'Teslim Edildi',
            'İptal edildi'
        ]
        for status in statuses:
            self.status_filter.addItem(status, status)
        filter_layout.addWidget(self.status_filter, 1, 1)

        # Teknisyen filtresi
        filter_layout.addWidget(QLabel("Teknisyen:"), 1, 2)
        self.technician_filter = QComboBox()
        self.technician_filter.addItem("Tümü", None)
        filter_layout.addWidget(self.technician_filter, 1, 3)

        # Butonlar
        buttons_layout = QHBoxLayout()
        self.add_service_btn = QPushButton("➕ Yeni Servis")
        self.history_btn = QPushButton("📜 Cihaz Geçmişi")
        self.customer_history_btn = QPushButton("👥 Müşteri Raporu")
        self.technician_tasks_btn = QPushButton("🔧 Teknisyen İşleri")
        self.deliver_btn = QPushButton("✅ Teslim Edildi")
        self.report_btn = QPushButton("📊 İş Geçmişi Raporu")
        self.delete_service_btn = QPushButton("🗑️ Servis Sil")

        self.history_btn.setEnabled(True)
        self.customer_history_btn.setEnabled(True)
        self.report_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.delete_service_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")

        buttons_layout.addWidget(self.add_service_btn)
        buttons_layout.addWidget(self.history_btn)
        buttons_layout.addWidget(self.customer_history_btn)
        buttons_layout.addWidget(self.technician_tasks_btn)
        buttons_layout.addWidget(self.deliver_btn)
        buttons_layout.addWidget(self.report_btn)
        buttons_layout.addWidget(self.delete_service_btn)
        buttons_layout.addStretch()

        filter_layout.addLayout(buttons_layout, 2, 0, 1, 4)

        # Teknisyenleri yükle
        self._load_technician_filter()

        return filter_group

    def _create_service_table(self):
        """Servis kayıtlarını gösteren tabloyu oluşturur."""
        table = QTableWidget(0, 8)
        table.setHorizontalHeaderLabels([
            "ID", "Müşteri", "Cihaz Model", "Seri No", 
            "Atanan Teknisyen", "Durum", "Arıza", "Tarih"
        ])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(6, 300)
        table.hideColumn(0)
        return table

    def _connect_signals(self):
        """Arayüz elemanlarının sinyallerini ilgili slotlara bağlar."""
        self.filter_input.textChanged.connect(self.filter_table)
        self.status_filter.currentIndexChanged.connect(self.filter_table)
        self.technician_filter.currentIndexChanged.connect(self.filter_table)
        self.service_table.cellDoubleClicked.connect(self.edit_service_dialog)
        self.service_table.itemSelectionChanged.connect(self.update_button_state)

        self.history_btn.clicked.connect(self.show_device_history)
        self.customer_history_btn.clicked.connect(self.show_customer_history)
        self.technician_tasks_btn.clicked.connect(self.show_technician_tasks)
        self.add_service_btn.clicked.connect(lambda: self.open_service_dialog())
        self.deliver_btn.clicked.connect(self.mark_as_delivered)
        self.report_btn.clicked.connect(self.show_service_reports)
        self.delete_service_btn.clicked.connect(self.delete_service_record)

    def _load_technician_filter(self):
        """Teknisyen filtresi için teknisyenleri yükler."""
        try:
            technicians = self.db.get_technicians()
            for tech_id, username in technicians:
                self.technician_filter.addItem(username, tech_id)
        except Exception as e:
            logger.error(f"Teknisyen filtresi yüklenirken hata: {e}")

    def set_technician_mode(self, user_id: int):
        """Teknisyen modunu ayarlar ve sadece ilgili kayıtları gösterir."""
        self.technician_user_id = user_id
        self.refresh_data()

    def update_button_state(self):
        """Seçime göre butonların durumunu günceller."""
        is_selected = bool(self.service_table.selectedItems())
        self.history_btn.setEnabled(is_selected)
        self.customer_history_btn.setEnabled(is_selected)
        self.deliver_btn.setEnabled(is_selected)

    def show_device_history(self):
        """Seçili kaydın cihaz geçmişini gösterir."""
        selected_rows = self.service_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        try:
            record_id = int(self.service_table.item(selected_rows[0].row(), 0).text())
            device_id_result = self.db.fetch_one("SELECT device_id FROM service_records WHERE id = ?", (record_id,))
            
            if not device_id_result or not device_id_result[0]:
                QMessageBox.warning(self, "Bilgi Yok", "Bu servis kaydına bağlı bir cihaz bulunamadı.")
                return
                
            dialog = DeviceHistoryDialog(device_id_result[0], self.db, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Cihaz geçmişi alınırken bir hata oluştu: {e}")

    def show_customer_history(self):
        """Seçili kaydın müşteri geçmişini gösterir."""
        selected_rows = self.service_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        try:
            customer_name = self.service_table.item(selected_rows[0].row(), 1).text()
            customer_id_result = self.db.fetch_one("SELECT id FROM customers WHERE name = ?", (customer_name,))
            
            if not customer_id_result or not customer_id_result[0]:
                QMessageBox.warning(self, "Bilgi Yok", "Bu müşteriye ait bir kayıt bulunamadı.")
                return
            
            dialog = CustomerServiceHistoryDialog(customer_id_result[0], self.db, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Müşteri geçmişi alınırken bir hata oluştu: {e}")
        
    def refresh_data(self):
        """Servis kayıtları listesini veritabanından yeniler."""
        if not self.db or not self.db.get_connection():
            self.status_bar.showMessage("Veritabanı bağlantısı yok.", 5000)
            return
            
        self.service_table.setRowCount(0)
        
        try:
            base_query = """
                SELECT sr.id, c.name, cd.device_model, cd.serial_number,
                       COALESCE(t.name || ' ' || t.surname, 'Atanmadı'), sr.status,
                       sr.problem_description, sr.created_date
                FROM service_records sr
                JOIN customer_devices cd ON sr.device_id = cd.id
                JOIN customers c ON cd.customer_id = c.id
                LEFT JOIN technicians t ON sr.technician_id = t.id
            """
            
            conditions = ["sr.problem_description != 'Periyodik Sayaç Okuma'"]
            params = []
            
            if self.technician_user_id:
                conditions.append("sr.technician_id = ?")
                params.append(self.technician_user_id)
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += " ORDER BY sr.id DESC"
            
            records = self.db.fetch_all(base_query, tuple(params))
            
            self.service_table.setRowCount(len(records))
            for row, data in enumerate(records):
                status = data[5]  # Durum sütunu
                if status == 'Onarıldı':
                    color = QColor('#d4edda')  # Açık yeşil
                elif status == 'İptal edildi':
                    color = QColor('#f8d7da')  # Açık kırmızı
                elif status == 'İşleme alındı':
                    color = QColor('#fff3cd')  # Açık sarı
                elif status == 'Teslim Edildi':
                    color = QColor('#d1ecf1')  # Açık turkuaz
                elif status == 'Teslimat Sürecinde':
                    color = QColor('#cfe2ff')  # Açık mavi
                else:
                    color = QColor('white')

                for col, val in enumerate(data):
                    item = QTableWidgetItem(str(val))
                    item.setBackground(color)
                    self.service_table.setItem(row, col, item)
            
            self.service_table.resizeRowsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Servis kayıtları yüklenirken bir hata oluştu: {e}")
        finally:
            self.update_button_state()
    
    def filter_table(self):
        """Arama, durum ve teknisyen filtresine göre tabloyu filtreler."""
        filter_text = self.filter_input.text().lower()
        status_filter = self.status_filter.currentData()
        technician_filter = self.technician_filter.currentData()

        for row in range(self.service_table.rowCount()):
            # Metin filtresi
            row_items = [self.service_table.item(row, i) for i in [1, 2, 3, 4, 6]]
            text_to_check = ' '.join([item.text().lower() for item in row_items if item])
            text_match = filter_text in text_to_check if filter_text else True

            # Durum filtresi - Tam eşleşme kontrolü
            status_item = self.service_table.item(row, 5)  # Durum sütunu
            if status_filter:  # Boş string değilse (Tümü seçili değilse)
                status_match = (status_item.text() == status_filter) if status_item else False
            else:
                status_match = True

            # Teknisyen filtresi
            technician_item = self.service_table.item(row, 4)  # Teknisyen sütunu
            technician_text = technician_item.text() if technician_item else ""
            technician_match = True
            if technician_filter:
                # Teknisyen ID'sini ad-soyad'dan eşleştir (technicians tablosu)
                try:
                    tech_result = self.db.fetch_one(
                        "SELECT name || ' ' || surname FROM technicians WHERE id = ?", 
                        (technician_filter,)
                    )
                    if tech_result:
                        technician_match = tech_result[0] in technician_text
                    else:
                        technician_match = False
                except:
                    technician_match = False

            # Tüm filtreleri uygula
            self.service_table.setRowHidden(row, not (text_match and status_match and technician_match))
    
    def edit_service_dialog(self, row, column):
        """Çift tıklanan servis kaydını düzenleme penceresini açar."""
        try:
            record_id = int(self.service_table.item(row, 0).text())
            self.open_service_dialog(record_id)
        except (ValueError, AttributeError):
            QMessageBox.warning(self, "Hata", "Geçerli bir servis kaydı seçilemedi.")
    
    def open_service_dialog(self, record_id=None):
        """Yeni veya mevcut bir servis kaydı için düzenleme penceresini açar."""
        try:
            dialog = ServiceEditDialog(self.db, self.status_bar, record_id, self)
            if dialog.exec():
                self.refresh_data()
                self.data_changed.emit() # Diğer sekmeleri bilgilendir
                self.status_bar.showMessage("Servis kaydı başarıyla işlendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Diyalog Hatası", f"Servis düzenleme penceresi açılırken bir hata oluştu: {e}")

    def show_technician_tasks(self):
        """Teknisyen işleri dialog'unu açar (sadece Admin ve SuperAdmin için)."""
        try:
            from ui.dialogs.technician_tasks_dialog import TechnicianTasksDialog
            
            dialog = TechnicianTasksDialog(self.db, parent=self)
            dialog.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Hata", f"Teknisyen işleri dialog'u açılamadı: {e}")

    def mark_as_delivered(self):
        """Seçili servisi 'Teslim Edildi' olarak işaretle."""
        selected_rows = self.service_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen teslim edilecek servisi seçin.")
            return

        record_id = int(self.service_table.item(selected_rows[0].row(), 0).text())
        
        # Mevcut durumu kontrol et
        current_status_data = self.db.fetch_one(
            "SELECT status FROM service_records WHERE id = ?",
            (record_id,)
        )
        
        if not current_status_data:
            QMessageBox.warning(self, "Uyarı", "Servis kaydı bulunamadı.")
            return
        
        current_status = current_status_data[0]

        reply = QMessageBox.question(
            self, "Teslim Edildi",
            f"Mevcut durum: {current_status}\n\nServisi 'Teslim Edildi' olarak işaretlemek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Status'u Teslim Edildi yap
                self.db.execute_query(
                    "UPDATE service_records SET status = 'Teslim Edildi' WHERE id = ?",
                    (record_id,)
                )
                
                QMessageBox.information(self, "Başarılı", "Servis 'Teslim Edildi' olarak işaretlendi.")
                self.refresh_data()
                self.data_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Servis güncellenirken hata: {e}")

    def show_service_reports(self):
        """Servis iş geçmişi raporlama dialog'unu açar."""
        try:
            from ui.dialogs.service_reports_dialog import ServiceReportsDialog
            dialog = ServiceReportsDialog(self.db, parent=self)
            dialog.exec()
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logging.error(f"Servis raporu dialog hatası: {error_detail}")
            QMessageBox.critical(self, "Hata", f"Raporlama dialog'u açılamadı:\n{e}\n\nDetay için log dosyasına bakın.")

    def delete_service_record(self):
        """Seçili servis kaydını siler."""
        selected_rows = self.service_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek servisi seçin.")
            return

        record_id = int(self.service_table.item(selected_rows[0].row(), 0).text())

        # Servis bilgilerini al
        service_info = self.db.fetch_one("""
            SELECT sr.status, c.name, cd.device_model, cd.serial_number
            FROM service_records sr
            JOIN customer_devices cd ON sr.device_id = cd.id
            JOIN customers c ON cd.customer_id = c.id
            WHERE sr.id = ?
        """, (record_id,))

        if not service_info:
            QMessageBox.warning(self, "Uyarı", "Servis kaydı bulunamadı.")
            return

        status, customer_name, device_model, serial_number = service_info

        # Silme onayı al
        reply = QMessageBox.question(
            self, "Servis Kaydını Sil",
            f"Servis kaydını silmek istediğinizden emin misiniz?\n\n"
            f"Müşteri: {customer_name}\n"
            f"Cihaz: {device_model} ({serial_number})\n"
            f"Durum: {status}\n\n"
            f"Bu işlem geri alınamaz!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Servis kaydını sil
                self.db.execute_query("DELETE FROM service_records WHERE id = ?", (record_id,))

                QMessageBox.information(self, "Başarılı", "Servis kaydı başarıyla silindi.")
                self.refresh_data()
                self.data_changed.emit()
                self.status_bar.showMessage("Servis kaydı silindi.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Servis kaydı silinirken hata: {e}")
