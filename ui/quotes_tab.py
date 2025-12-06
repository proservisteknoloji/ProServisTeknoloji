# ui/quotes_tab.py (PyQt6'ya güncellendi)

# Değişiklik: PySide6 -> PyQt6
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QHeaderView, QMessageBox, QTabWidget, QLabel,
                             QDateEdit, QFileDialog)
from PyQt6.QtCore import QDate, Qt
from utils.workers import PANDAS_AVAILABLE
from utils.database import db_manager

class QuotesTab(QWidget):
    def __init__(self, db, status_bar, parent=None):
        super().__init__(parent)
        self.db = db
        self.status_bar = status_bar
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Tarih Filtreleme Paneli
        filter_layout = QHBoxLayout()
        today = QDate.currentDate()
        self.start_date_edit = QDateEdit(today.addMonths(-1))
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit = QDateEdit(today)
        self.end_date_edit.setCalendarPopup(True)
        self.filter_btn = QPushButton("📅 Filtrele")
        
        filter_layout.addWidget(QLabel("Başlangıç Tarihi:"))
        filter_layout.addWidget(self.start_date_edit)
        filter_layout.addWidget(QLabel("Bitiş Tarihi:"))
        filter_layout.addWidget(self.end_date_edit)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addStretch()
        
        # Ana Alt-Sekme (Tab) Yapısı
        self.sub_tabs = QTabWidget()
        
        # Alt-Sekme 1: Servis Teklifleri
        # FIXED: Add parent to prevent memory leak
        self.quotes_widget = QWidget(self)
        quotes_layout = QVBoxLayout(self.quotes_widget)
        
        quotes_button_layout = QHBoxLayout()
        self.export_quotes_btn = QPushButton("📋 Listeyi Excel'e Aktar")
        if not PANDAS_AVAILABLE:
            self.export_quotes_btn.setEnabled(False)
        self.save_quote_pdf_btn = QPushButton("PDF olarak Kaydet")
        quotes_button_layout.addStretch()
        quotes_button_layout.addWidget(self.export_quotes_btn)
        quotes_button_layout.addWidget(self.save_quote_pdf_btn)
        
        self.quote_table = QTableWidget(0, 6)
        self.quote_table.setHorizontalHeaderLabels(["Servis ID", "Müşteri", "Cihaz", "Tarih", "Toplam Tutar (TL)", "Durum"])
        # Değişiklik: Enum güncellemeleri
        self.quote_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quote_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quote_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        quotes_layout.addLayout(quotes_button_layout)
        quotes_layout.addWidget(self.quote_table)

        # Alt-Sekme 2: Sayaç Faturaları (CPC)
        # FIXED: Add parent to prevent memory leak
        self.cpc_widget = QWidget(self)
        cpc_layout = QVBoxLayout(self.cpc_widget)
        cpc_button_layout = QHBoxLayout()
        self.export_cpc_btn = QPushButton("📋 Listeyi Excel'e Aktar")
        if not PANDAS_AVAILABLE: self.export_cpc_btn.setEnabled(False)
        cpc_button_layout.addStretch()
        cpc_button_layout.addWidget(self.export_cpc_btn)
        
        self.cpc_table = QTableWidget(0, 6)
        self.cpc_table.setHorizontalHeaderLabels(["Fatura ID", "Müşteri", "Dönem Başlangıç", "Dönem Bitiş", "Kesim Tarihi", "Toplam Tutar (TL)"])
        # Değişiklik: Enum güncellemeleri
        self.cpc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cpc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cpc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        cpc_layout.addLayout(cpc_button_layout)
        cpc_layout.addWidget(self.cpc_table)

        self.sub_tabs.addTab(self.quotes_widget, "Servis Teklifleri")
        self.sub_tabs.addTab(self.cpc_widget, "Sayaç Faturaları (CPC)")

        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.sub_tabs)

        # Sinyaller
    self.filter_btn.clicked.connect(self.refresh_data)
    self.export_cpc_btn.clicked.connect(self.export_cpc_invoices)
    self.export_quotes_btn.clicked.connect(self.export_quotes_to_excel)
    self.save_quote_pdf_btn.clicked.connect(self.save_selected_quote_as_pdf)
    def save_selected_quote_as_pdf(self):
        """Seçili teklif satırını PDF olarak müşteri adıyla kaydeder."""
        selected = self.quote_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seçim Yok", "PDF oluşturmak için bir teklif seçin.")
            return
        row = selected[0].row()
        # Teklif verilerini al
        def get_cell_text(table, row, col):
            item = table.item(row, col)
            return item.text() if item else ""
        teklif_id = get_cell_text(self.quote_table, row, 0)
        musteri_adi = get_cell_text(self.quote_table, row, 1)
        cihaz = get_cell_text(self.quote_table, row, 2)
        tarih = get_cell_text(self.quote_table, row, 3)
        toplam_tutar = get_cell_text(self.quote_table, row, 4)
        durum = get_cell_text(self.quote_table, row, 5)

        # Teklif detaylarını veritabanından al
        quote_details = self.db.get_quote_details(teklif_id) if hasattr(self.db, 'get_quote_details') else None
        if not quote_details:
            QMessageBox.warning(self, "Veri Yok", "Teklif detayları alınamadı.")
            return

        # PDF dosya adı
        safe_name = musteri_adi.replace(" ", "_").replace("/", "-")
        import os
        from utils.pdf_generator import create_quote_form_pdf
        # Masaüstü 'Müşteri Teklifleri' klasörü
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        teklif_dir = os.path.join(desktop_path, "Müşteri Teklifleri")
        if not os.path.exists(teklif_dir):
            os.makedirs(teklif_dir)
        pdf_filename = f"{musteri_adi}_teklif_{teklif_id}.pdf"
        file_path = os.path.join(teklif_dir, pdf_filename)

        pdf_data = {
            'main_info': {
                'id': teklif_id,
                'customer_name': musteri_adi,
                'customer_address': quote_details.get('customer_address', ''),
                'customer_phone': quote_details.get('customer_phone', ''),
                'customer_tax_id': quote_details.get('customer_tax_id', ''),
                'device_model': quote_details.get('device_model', ''),
                'device_serial': quote_details.get('device_serial', ''),
            },
            'company_info': quote_details.get('company_info', {}),
            'quote_items': quote_details.get('items', []),
            'vat_rate': quote_details.get('vat_rate', '20.0'),
        }
        
        try:
            success = create_quote_form_pdf(pdf_data, file_path)
            if success:
                QMessageBox.information(self, "Başarılı", f"Teklif PDF başarıyla kaydedildi:\n{file_path}")
                # PDF'i otomatik aç
                os.startfile(file_path)
            else:
                QMessageBox.critical(self, "Hata", "PDF oluşturulamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken hata: {e}")

    def refresh_data(self):
        """Her iki tabloyu da seçilen tarih aralığına göre yeniler."""
        if not self.db or not self.db.get_connection(): return
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        # Servis Teklifleri tablosunu yenile
        self.quote_table.setRowCount(0)
        quotes = self.db.get_all_quotes(start_date, end_date)
        for row, data in enumerate(quotes):
            self.quote_table.insertRow(row)
            for col, value in enumerate(data):
                item_text = f"{float(value):.2f}" if col == 4 and value is not None else str(value)
                item = QTableWidgetItem(item_text)
                # Değişiklik: Enum güncellemeleri
                if col == 4: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.quote_table.setItem(row, col, item)
        
        # Sayaç Faturaları tablosunu yenile
        self.cpc_table.setRowCount(0)
        cpc_invoices = self.db.get_cpc_invoices_by_date_range(start_date, end_date)
        for row, data in enumerate(cpc_invoices):
            self.cpc_table.insertRow(row)
            for col, value in enumerate(data):
                item_text = f"{float(value):.2f}" if col == 5 and value is not None else str(value)
                item = QTableWidgetItem(item_text)
                # Değişiklik: Enum güncellemeleri
                if col == 5: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.cpc_table.setItem(row, col, item)

        self.status_bar.showMessage("Raporlar güncellendi.", 3000)

    def export_quotes_to_excel(self):
        """Servis teklifleri tablosundaki verileri Excel'e aktarır."""
        if not PANDAS_AVAILABLE:
            QMessageBox.warning(self, "Eksik Kütüphane", "Bu özellik için 'pandas' ve 'openpyxl' kütüphaneleri gereklidir.")
            return
        if self.quote_table.rowCount() == 0:
            QMessageBox.information(self, "Bilgi", "Dışa aktarılacak veri bulunmuyor.")
            return
        
        start_date = self.start_date_edit.date().toString("yyyy_MM_dd")
        end_date = self.end_date_edit.date().toString("yyyy_MM_dd")
        file_path, _ = QFileDialog.getSaveFileName(self, "Excel Olarak Kaydet", f"servis_teklifleri_{start_date}_-__{end_date}.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path: return

        try:
            import pandas as pd
            data = []
            for row in range(self.quote_table.rowCount()):
                row_data = []
                for col in range(self.quote_table.columnCount()):
                    item = self.quote_table.item(row, col)
                    row_data.append(item.text() if item and item.text() else "")
                data.append(row_data)
            columns = []
            for i in range(self.quote_table.columnCount()):
                header_item = self.quote_table.horizontalHeaderItem(i)
                columns.append(header_item.text() if header_item and header_item.text() else "")
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Başarılı", f"Veriler başarıyla dışa aktarıldı:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma sırasında bir hata oluştu: {e}")

    def export_cpc_invoices(self):
        """Sayaç faturaları tablosundaki verileri Excel'e aktarır."""
        if not PANDAS_AVAILABLE:
            QMessageBox.warning(self, "Eksik Kütüphane", "Bu özellik için 'pandas' ve 'openpyxl' kütüphaneleri gereklidir.")
            return
        if self.cpc_table.rowCount() == 0:
            QMessageBox.information(self, "Bilgi", "Dışa aktarılacak veri bulunmuyor.")
            return
        
        start_date = self.start_date_edit.date().toString("yyyy_MM_dd")
        end_date = self.end_date_edit.date().toString("yyyy_MM_dd")
        file_path, _ = QFileDialog.getSaveFileName(self, "Excel Olarak Kaydet", f"sayac_faturalari_{start_date}_-__{end_date}.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path: return

        try:
            import pandas as pd
            data = []
            for row in range(self.cpc_table.rowCount()):
                row_data = []
                for col in range(self.cpc_table.columnCount()):
                    item = self.cpc_table.item(row, col)
                    row_data.append(item.text() if item and item.text() else "")
                data.append(row_data)
            
            columns = []
            for i in range(self.cpc_table.columnCount()):
                header_item = self.cpc_table.horizontalHeaderItem(i)
                columns.append(header_item.text() if header_item and header_item.text() else "")
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Başarılı", f"Veriler başarıyla dışa aktarıldı:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma sırasında bir hata oluştu: {e}")
