# ui/dialogs/service_reports_dialog.py

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QComboBox, QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox,
                             QGroupBox, QDateEdit, QCheckBox, QTextEdit,
                             QProgressBar, QFileDialog, QLineEdit)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
import os
from utils.database import db_manager
from utils.pdf_generator import create_service_history_report_pdf

class ServiceReportsDialog(QDialog):
    """Servis iş geçmişi raporlama dialog'u."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("📊 Servis İş Geçmişi Raporları")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self.report_data = []
        self.filtered_data = []

        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)

        # Filtreler bölümü
        filters_group = self.create_filters_group()
        layout.addWidget(filters_group)

        # Tablo
        self.results_table = self.create_results_table()
        layout.addWidget(self.results_table)

        # İstatistikler ve butonlar
        bottom_layout = QHBoxLayout()

        # İstatistikler
        stats_group = self.create_stats_group()
        bottom_layout.addWidget(stats_group)

        # Butonlar
        buttons_layout = self.create_buttons_layout()
        bottom_layout.addLayout(buttons_layout)

        layout.addLayout(bottom_layout)

    def create_filters_group(self):
        """Filtreleme seçeneklerini içeren grup."""
        group = QGroupBox("📅 Rapor Filtreleri")
        layout = QVBoxLayout(group)

        # Tarih aralığı seçimi
        date_layout = QHBoxLayout()

        date_layout.addWidget(QLabel("Rapor Türü:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Günlük Rapor",
            "Haftalık Rapor",
            "Aylık Rapor",
            "Özel Tarih Aralığı"
        ])
        self.report_type_combo.currentTextChanged.connect(self.on_report_type_changed)
        date_layout.addWidget(self.report_type_combo)

        date_layout.addWidget(QLabel("Başlangıç:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)

        date_layout.addWidget(QLabel("Bitiş:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.end_date)

        date_layout.addStretch()
        layout.addLayout(date_layout)

        # Durum filtreleri
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Durum Filtreleri:"))

        self.status_checkboxes = {}
        statuses = [
            'Teknisyene ata', 'İşleme alındı', 'Servise alındı',
            'Müşteri Onayı Alınacak', 'Parça bekleniyor', 'Onarıldı',
            'Teslimat Sürecinde', 'Teslim Edildi', 'İptal edildi'
        ]

        for status in statuses:
            checkbox = QCheckBox(status)
            checkbox.setChecked(True)  # Varsayılan olarak hepsi seçili
            self.status_checkboxes[status] = checkbox
            status_layout.addWidget(checkbox)

        layout.addLayout(status_layout)

        # Diğer filtreler
        other_filters_layout = QHBoxLayout()

        other_filters_layout.addWidget(QLabel("Teknisyen:"))
        self.technician_filter = QComboBox()
        self.technician_filter.addItem("Tümü", None)
        other_filters_layout.addWidget(self.technician_filter)

        other_filters_layout.addWidget(QLabel("Müşteri Ara:"))
        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("Müşteri adı ile ara...")
        other_filters_layout.addWidget(self.customer_search)

        other_filters_layout.addStretch()
        layout.addLayout(other_filters_layout)

        # Rapor oluştur butonu
        button_layout = QHBoxLayout()
        self.generate_btn = QPushButton("🔍 Rapor Oluştur")
        self.generate_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        self.generate_btn.clicked.connect(self.generate_report)
        button_layout.addWidget(self.generate_btn)

        self.export_pdf_btn = QPushButton("📄 PDF'e Aktar")
        self.export_pdf_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)
        self.export_pdf_btn.setEnabled(False)
        button_layout.addWidget(self.export_pdf_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        return group

    def create_results_table(self):
        """Sonuçları gösteren tablo."""
        table = QTableWidget(0, 10)
        table.setHorizontalHeaderLabels([
            "ID", "Tarih", "Müşteri", "Telefon", "Cihaz Model",
            "Seri No", "Teknisyen", "Durum", "Arıza Açıklaması", "Çözüm"
        ])

        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(8, 250)  # Arıza açıklaması
        table.setColumnWidth(9, 250)  # Çözüm
        table.hideColumn(0)  # ID sütunu gizli

        return table

    def create_stats_group(self):
        """İstatistikleri gösteren grup."""
        group = QGroupBox("📈 İstatistikler")
        layout = QVBoxLayout(group)

        self.stats_labels = {}
        stats = [
            "Toplam Servis",
            "Onarılan",
            "Teslim Edilen",
            "İptal Edilen",
            "Devam Eden",
            "Ortalama Tamamlama Süresi"
        ]

        for stat in stats:
            label = QLabel(f"{stat}: -")
            self.stats_labels[stat] = label
            layout.addWidget(label)

        return group

    def create_buttons_layout(self):
        """Butonları içeren layout."""
        layout = QVBoxLayout()

        self.close_btn = QPushButton("Kapat")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        layout.addStretch()
        return layout

    def load_initial_data(self):
        """İlk verileri yükler."""
        try:
            # Kullanıcıları yükle (servis atanan kullanıcılar)
            users_query = """
                SELECT id, username 
                FROM users 
                WHERE role IN ('Admin', 'Kullanıcı')
                ORDER BY username
            """
            users = self.db.fetch_all(users_query)
            for user_id, username in users:
                self.technician_filter.addItem(username, user_id)

            # Bugünkü raporu varsayılan olarak göster
            self.on_report_type_changed("Günlük Rapor")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata: {e}")

    def on_report_type_changed(self, report_type):
        """Rapor türü değiştiğinde tarihleri ayarlar."""
        today = QDate.currentDate()

        if report_type == "Günlük Rapor":
            self.start_date.setDate(today)
            self.end_date.setDate(today)
        elif report_type == "Haftalık Rapor":
            week_start = today.addDays(-(today.dayOfWeek() - 1))  # Pazartesi
            self.start_date.setDate(week_start)
            self.end_date.setDate(today)
        elif report_type == "Aylık Rapor":
            month_start = QDate(today.year(), today.month(), 1)
            self.start_date.setDate(month_start)
            self.end_date.setDate(today)
        # Özel tarih aralığı için değişiklik yapma

    def generate_report(self):
        """Seçilen filtrelere göre raporu oluşturur."""
        try:
            # Tarih aralığını al (saat ekleyerek)
            start_date = self.start_date.date().toString("yyyy-MM-dd") + " 00:00:00"
            end_date = self.end_date.date().toString("yyyy-MM-dd") + " 23:59:59"

            # Durum filtrelerini al
            selected_statuses = []
            for status, checkbox in self.status_checkboxes.items():
                if checkbox.isChecked():
                    selected_statuses.append(status)

            if not selected_statuses:
                QMessageBox.warning(self, "Uyarı", "En az bir durum seçmelisiniz.")
                return

            # Diğer filtreler
            technician_id = self.technician_filter.currentData()
            customer_search = self.customer_search.text().strip()

            # SQL sorgusu oluştur (completed_date dahil et)
            query = """
                SELECT
                    sr.id,
                    sr.created_date,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    cd.device_model,
                    cd.serial_number,
                    COALESCE(u.username, 'Atanmadı') as technician_name,
                    sr.status,
                    sr.problem_description,
                    sr.notes as technician_report,
                    sr.completed_date
                FROM service_records sr
                JOIN customer_devices cd ON sr.device_id = cd.id
                JOIN customers c ON cd.customer_id = c.id
                LEFT JOIN users u ON sr.assigned_user_id = u.id
                WHERE sr.created_date BETWEEN ? AND ?
                AND sr.status IN ({})
            """.format(','.join(['?'] * len(selected_statuses)))

            params = [start_date, end_date] + selected_statuses

            # Teknisyen filtresi (assigned_user_id kullan)
            if technician_id:
                query += " AND sr.assigned_user_id = ?"
                params.append(technician_id)

            # Müşteri arama filtresi
            if customer_search:
                query += " AND c.name LIKE ?"
                params.append(f"%{customer_search}%")

            query += " ORDER BY sr.created_date DESC, sr.id DESC"

            # Veriyi çek
            self.report_data = self.db.fetch_all(query, tuple(params))
            self.apply_filters_to_table()

            # İstatistikleri hesapla
            self.calculate_statistics()

            # PDF butonunu etkinleştir
            self.export_pdf_btn.setEnabled(len(self.filtered_data) > 0)

            QMessageBox.information(
                self, "Başarılı",
                f"Toplam {len(self.filtered_data)} servis kaydı bulundu."
            )

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor oluşturulurken hata: {e}")

    def apply_filters_to_table(self):
        """Filtrelenmiş veriyi tabloya uygular."""
        self.results_table.setRowCount(0)

        if not self.report_data:
            return

        self.results_table.setRowCount(len(self.report_data))

        status_colors = {
            'Onarıldı': QColor('#d4edda'),  # Açık yeşil
            'İptal edildi': QColor('#f8d7da'),  # Açık kırmızı
            'İşleme alındı': QColor('#fff3cd'),  # Açık sarı
            'Teslim Edildi': QColor('#d1ecf1'),  # Açık turkuaz
            'Teslimat Sürecinde': QColor('#cfe2ff'),  # Açık mavi
            'Teknisyene ata': QColor('#f8f9fa'),  # Açık gri
            'Servise alındı': QColor('#e2e3e5'),  # Gri
            'Müşteri Onayı Alınacak': QColor('#ffeaa7'),  # Açık turuncu
            'Parça bekleniyor': QColor('#fdcb6e'),  # Turuncu
        }

        for row, data in enumerate(self.report_data):
            # Sadece ilk 10 kolonu tabloya ekle (completed_date hariç, o sadece istatistik için)
            for col, value in enumerate(data[:10]):
                item = QTableWidgetItem(str(value or ""))
                # Durum sütunu için renk
                if col == 7:  # status sütunu
                    color = status_colors.get(str(value), QColor('white'))
                    item.setBackground(color)
                self.results_table.setItem(row, col, item)

        self.results_table.resizeRowsToContents()
        self.filtered_data = self.report_data.copy()

    def calculate_statistics(self):
        """İstatistikleri hesaplar."""
        logging.info(f"calculate_statistics çağrıldı - report_data sayısı: {len(self.report_data) if self.report_data else 0}")
        
        if not self.report_data:
            for label in self.stats_labels.values():
                label.setText("-")
            logging.warning("İstatistikler hesaplanamadı: report_data boş")
            return

        total_services = len(self.report_data)
        logging.info(f"Toplam servis sayısı: {total_services}")

        # Durum bazlı sayımlar
        status_counts = {}
        for row in self.report_data:
            status = row[7]  # status sütunu
            status_counts[status] = status_counts.get(status, 0) + 1

        onarilan = status_counts.get('Onarıldı', 0)
        teslim_edilen = status_counts.get('Teslim Edildi', 0)
        iptal_edilen = status_counts.get('İptal edildi', 0)
        devam_eden = total_services - onarilan - teslim_edilen - iptal_edilen
        
        logging.info(f"Durum sayıları - Onarılan: {onarilan}, Teslim: {teslim_edilen}, İptal: {iptal_edilen}, Devam: {devam_eden}")

        # Ortalama tamamlama süresi hesaplama
        avg_completion_time = "-"
        try:
            # Teslim edilen servisleri al
            completed_services = [
                row for row in self.report_data 
                if row[7] == 'Teslim Edildi' and row[1]  # status ve created_date var
            ]
            
            if completed_services:
                total_days = 0
                valid_count = 0
                
                for row in completed_services:
                    created_str = row[1]  # created_date
                    completed_str = row[10] if len(row) > 10 else None  # completed_date
                    
                    if created_str:
                        try:
                            # Tarih formatını parse et (YYYY-MM-DD HH:MM:SS veya YYYY-MM-DD HH:MM)
                            if len(created_str) > 10:
                                created_date = datetime.strptime(created_str[:16], "%Y-%m-%d %H:%M")
                            else:
                                created_date = datetime.strptime(created_str, "%Y-%m-%d")
                            
                            # completed_date varsa kullan, yoksa bugünü kullan (eski kayıtlar için)
                            if completed_str:
                                if len(completed_str) > 10:
                                    completed_date = datetime.strptime(completed_str[:16], "%Y-%m-%d %H:%M")
                                else:
                                    completed_date = datetime.strptime(completed_str, "%Y-%m-%d")
                            else:
                                # Eski kayıtlar için: created_date'den 1 gün sonrasını varsayılan olarak kullan
                                # (Aynı gün teslim varsayımı)
                                completed_date = created_date
                            
                            # İki tarih arasındaki farkı hesapla
                            days_diff = (completed_date - created_date).days
                            if days_diff >= 0:  # Geçerlilik kontrolü
                                total_days += days_diff
                                valid_count += 1
                        except ValueError as ve:
                            logging.warning(f"Tarih parse hatası: {ve}")
                            continue
                
                if valid_count > 0:
                    avg_days = total_days / valid_count
                    if avg_days == 0:
                        avg_completion_time = "Aynı gün"
                    elif avg_days < 1:
                        avg_completion_time = "1 günden az"
                    else:
                        avg_completion_time = f"{avg_days:.1f} gün"
                else:
                    avg_completion_time = "Hesaplanamadı"
            else:
                avg_completion_time = "-"
        except Exception as e:
            logging.error(f"Ortalama tamamlama süresi hesaplama hatası: {e}")
            avg_completion_time = "Hata"

        # İstatistikleri güncelle
        logging.info(f"İstatistikler güncelleniyor - Label sayısı: {len(self.stats_labels)}")
        self.stats_labels["Toplam Servis"].setText(f"Toplam Servis: {total_services}")
        self.stats_labels["Onarılan"].setText(f"Onarılan: {onarilan}")
        self.stats_labels["Teslim Edilen"].setText(f"Teslim Edilen: {teslim_edilen}")
        self.stats_labels["İptal Edilen"].setText(f"İptal Edilen: {iptal_edilen}")
        self.stats_labels["Devam Eden"].setText(f"Devam Eden: {devam_eden}")
        self.stats_labels["Ortalama Tamamlama Süresi"].setText(f"Ortalama Tamamlama Süresi: {avg_completion_time}")
        logging.info(f"İstatistikler güncellendi - Ortalama süre: {avg_completion_time}")

    def export_to_pdf(self):
        """Raporu PDF olarak dışa aktarır."""
        if not self.filtered_data:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak veri bulunamadı.")
            return

        try:
            # Dosya kaydet dialog'u
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "PDF Raporu Kaydet",
                f"servis_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Dosyaları (*.pdf)"
            )

            if not file_path:
                return

            # PDF için veri hazırlama
            service_records = []
            for row in self.filtered_data:
                record = {
                    'date': row[1] or '',  # created_date
                    'customer_name': row[2] or '',  # customer_name
                    'device_model': row[4] or '',  # device_model
                    'serial_number': row[5] or '',  # serial_number
                    'technician': row[6] or '',  # technician_name
                    'status': row[7] or '',  # status
                    'description': row[8] or ''  # problem_description
                }
                service_records.append(record)

            report_data = {
                'report_title': f"{self.report_type_combo.currentText()} - Servis İş Geçmişi",
                'report_info': {
                    'date_range': f"{self.start_date.date().toString('dd.MM.yyyy')} - {self.end_date.date().toString('dd.MM.yyyy')}",
                    'total_records': len(self.filtered_data)
                },
                'statistics': {k: v.text() for k, v in self.stats_labels.items()},
                'service_records': service_records
            }

            create_service_history_report_pdf(report_data, file_path)

            QMessageBox.information(
                self, "Başarılı",
                f"Rapor başarıyla kaydedildi:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken hata: {e}")