# ui/dialogs/technician_tasks_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget,
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel)
import logging
logger = logging.getLogger(__name__)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from utils.database import db_manager

class TechnicianTasksDialog(QDialog):
    """Saha teknisyenlerinin işlerini yöneten dialog."""

    def __init__(self, db, current_user_id=None, current_user_role=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self.setWindowTitle("Teknisyen İşleri")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self.init_ui()
        self.load_technicians()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)

        # Teknisyen seçimi
        tech_layout = QHBoxLayout()
        tech_layout.addWidget(QLabel("Teknisyen:"))
        self.technician_combo = QComboBox()
        self.technician_combo.currentIndexChanged.connect(self.load_tasks)
        tech_layout.addWidget(self.technician_combo)
        tech_layout.addStretch()
        layout.addLayout(tech_layout)

        # İşler tablosu
        self.tasks_table = QTableWidget(0, 6)
        self.tasks_table.setHorizontalHeaderLabels([
            "ID", "Müşteri", "Cihaz Model", "Seri No", "Arıza", "Tarih"
        ])
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tasks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tasks_table.hideColumn(0)
        self.tasks_table.itemDoubleClicked.connect(self.edit_service)
        self.tasks_table.itemSelectionChanged.connect(self.update_button_text)
        layout.addWidget(self.tasks_table)

        # Butonlar
        buttons_layout = QHBoxLayout()
        self.print_btn = QPushButton("Yazdır")
        self.complete_btn = QPushButton("İşi Tamamla")
        self.close_btn = QPushButton("Kapat")

        self.print_btn.clicked.connect(self.print_tasks)
        self.complete_btn.clicked.connect(self.complete_task)
        self.close_btn.clicked.connect(self.accept)

        buttons_layout.addWidget(self.print_btn)
        buttons_layout.addWidget(self.complete_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_btn)
        layout.addLayout(buttons_layout)

    def load_technicians(self):
        """Saha teknisyenlerini combo'ya yükler."""
        try:
            logger.debug(f"[DEBUG] load_technicians başladı")
            technicians = self.db.get_technicians()
            logger.debug(f"[DEBUG] get_technicians() sonucu: {technicians}")
            
            # Admin ve SuperAdmin tüm teknisyenleri görebilir
            self.technician_combo.addItem("Tüm Teknisyenler", None)
            for tech_id, tech_name in technicians:
                logger.debug(f"[DEBUG] Ekleniyor: {tech_name} (ID: {tech_id})")
                self.technician_combo.addItem(tech_name, tech_id)
            
            logger.debug(f"[DEBUG] ComboBox'a eklenen item sayısı: {self.technician_combo.count()}")
            
        except Exception as e:
            import traceback
            logger.debug(f"[DEBUG ERROR] load_technicians hatası:")
            traceback.print_exc()
            QMessageBox.critical(self, "Hata", f"Teknisyenler yüklenirken hata: {e}")

    def update_button_text(self):
        """Seçili işin durumuna göre buton metnini günceller."""
        selected_rows = self.tasks_table.selectionModel().selectedRows()
        if not selected_rows:
            self.complete_btn.setText("İşi Tamamla")
            return
        
        try:
            task_id = int(self.tasks_table.item(selected_rows[0].row(), 0).text())
            status = self.db.fetch_one(
                "SELECT status FROM service_records WHERE id = ?", 
                (task_id,)
            )
            
            if status and status[0] == "Teslimat Sürecinde":
                self.complete_btn.setText("Teslim Edildi")
            else:
                self.complete_btn.setText("İşi Tamamla")
        except:
            self.complete_btn.setText("İşi Tamamla")

    def load_tasks(self):
        """Seçili teknisyenin işlerini yükler."""
        self.tasks_table.setRowCount(0)
        technician_id = self.technician_combo.currentData()

        try:
            if technician_id:
                # Belirli teknisyenin işleri
                query = """
                    SELECT sr.id, c.name, cd.device_model, cd.serial_number,
                           sr.problem_description, sr.created_date
                    FROM service_records sr
                    JOIN customer_devices cd ON sr.device_id = cd.id
                    JOIN customers c ON cd.customer_id = c.id
                    WHERE sr.technician_id = ? AND sr.status NOT IN ('Onarıldı', 'Teslim Edildi', 'İptal edildi')
                    ORDER BY sr.created_date DESC
                """
                tasks = self.db.fetch_all(query, (technician_id,))
            else:
                # Tüm teknisyenlerin işleri
                query = """
                    SELECT sr.id, c.name, cd.device_model, cd.serial_number,
                           sr.problem_description, sr.created_date, t.name || ' ' || t.surname as technician_name
                    FROM service_records sr
                    JOIN customer_devices cd ON sr.device_id = cd.id
                    JOIN customers c ON cd.customer_id = c.id
                    LEFT JOIN technicians t ON sr.technician_id = t.id
                    WHERE sr.technician_id IS NOT NULL 
                    AND sr.status NOT IN ('Onarıldı', 'Teslim Edildi', 'İptal edildi')
                    ORDER BY sr.created_date DESC
                """
                tasks = self.db.fetch_all(query)

            self.tasks_table.setRowCount(len(tasks))
            for row, task in enumerate(tasks):
                for col, value in enumerate(task[:6]):  # İlk 6 sütun
                    self.tasks_table.setItem(row, col, QTableWidgetItem(str(value or "")))

            if technician_id:
                self.tasks_table.setColumnCount(6)
            else:
                # Tüm için teknisyen sütunu ekle
                self.tasks_table.setColumnCount(7)
                self.tasks_table.setHorizontalHeaderLabels([
                    "ID", "Müşteri", "Cihaz Model", "Seri No", "Arıza", "Tarih", "Teknisyen"
                ])
                for row, task in enumerate(tasks):
                    self.tasks_table.setItem(row, 6, QTableWidgetItem(str(task[6] or "Atanmadı")))

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşler yüklenirken hata: {e}")

    def print_tasks(self):
        """İş listesini yazdırır."""
        try:
            printer = QPrinter()
            dialog = QPrintDialog(printer, self)
            if dialog.exec():
                # Basit yazdırma - tabloyu yazdır
                technician = self.technician_combo.currentText()
                html = f"<h1>{technician} - İş Listesi</h1><table border='1'>"
                html += "<tr><th>Müşteri</th><th>Cihaz</th><th>Seri No</th><th>Arıza</th><th>Tarih</th></tr>"

                for row in range(self.tasks_table.rowCount()):
                    html += "<tr>"
                    for col in range(1, self.tasks_table.columnCount()):  # ID hariç
                        item = self.tasks_table.item(row, col)
                        html += f"<td>{item.text() if item else ''}</td>"
                    html += "</tr>"

                html += "</table>"

                from PyQt6.QtGui import QTextDocument
                doc = QTextDocument()
                doc.setHtml(html)
                doc.print(printer)

        except Exception as e:
            QMessageBox.critical(self, "Yazdırma Hatası", f"Yazdırma sırasında hata: {e}")

    def complete_task(self):
        """Seçili işi tamamlar veya teslim eder."""
        selected_rows = self.tasks_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen tamamlanacak işi seçin.")
            return

        task_id = int(self.tasks_table.item(selected_rows[0].row(), 0).text())
        
        # Servisin mevcut durumunu kontrol et
        current_status = self.db.fetch_one(
            "SELECT status FROM service_records WHERE id = ?", 
            (task_id,)
        )
        
        if not current_status:
            QMessageBox.warning(self, "Hata", "Servis kaydı bulunamadı.")
            return
        
        status = current_status[0]
        
        # Teslimat Sürecinde ise "Teslim Edildi" seçeneği sun
        if status == "Teslimat Sürecinde":
            reply = QMessageBox.question(
                self, "Teslim Et",
                "Bu cihaz teslimat sürecinde. Müşteriye teslim edildi mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Status'u Teslim Edildi yap
                    self.db.execute_query(
                        "UPDATE service_records SET status = 'Teslim Edildi' WHERE id = ?",
                        (task_id,)
                    )
                    QMessageBox.information(self, "Başarılı", "Cihaz 'Teslim Edildi' olarak işaretlendi.")
                    self.load_tasks()  # Listeyi yenile
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"İş güncellenirken hata: {e}")
        else:
            # Diğer durumlar için normal tamamlama
            reply = QMessageBox.question(
                self, "Onay",
                "Seçili işi 'Teslimat Sürecinde' olarak işaretlemek istediğinizden emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Status'u Teslimat Sürecinde yap
                    self.db.execute_query(
                        "UPDATE service_records SET status = 'Teslimat Sürecinde' WHERE id = ?",
                        (task_id,)
                    )
                    QMessageBox.information(self, "Başarılı", "İş 'Teslimat Sürecinde' olarak işaretlendi.")
                    self.load_tasks()  # Listeyi yenile
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"İş tamamlanırken hata: {e}")

    def edit_service(self, item):
        """Çift tıklanan servisi düzenleme dialog'u ile açar."""
        row = item.row()
        task_id = int(self.tasks_table.item(row, 0).text())

        try:
            from ui.dialogs.service_dialog import ServiceEditDialog
            dialog = ServiceEditDialog(self.db, None, record_id=task_id, technician_mode=True, parent=self)
            if dialog.exec():
                self.load_tasks()  # Listeyi yenile
                # Ana servis tab'ını da yenile
                if hasattr(self.parent(), 'refresh_data'):
                    self.parent().refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Servis düzenleme dialog'u açılamadı: {e}")
