# ui/invoicing_tab.py
# type: ignore

import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QLabel, QGroupBox, QMessageBox, QAbstractItemView, QFileDialog, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal as Signal

from utils.database import db_manager
from utils.pdf_generator import create_professional_invoice_pdf, create_merged_invoice_pdf 
from .dialogs.payment_dialog import PaymentDialog
from .dialogs.invoice_preview_dialog import InvoicePreviewDialog

class InvoicingTab(QWidget):
    """Faturalandırma işlemlerini ve geçmişini yöneten sekme."""
    data_changed = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_customer_id = None
        self.init_ui()
        self.refresh_customers()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 750])
        main_layout.addWidget(splitter)
        
        self._connect_signals()
        
    def _create_left_panel(self):
        """Müşteri seçimi ve filtreleme panelini oluşturur."""
        panel = QGroupBox("Müşteri Seçimi")
        layout = QVBoxLayout(panel)
        
        customer_filter_layout = QHBoxLayout()
        self.customer_filter_input = QLineEdit()
        self.customer_filter_input.setPlaceholderText("Müşteri adıyla ara...")
        customer_filter_layout.addWidget(QLabel("Müşteri:"))
        customer_filter_layout.addWidget(self.customer_filter_input)
        
        serial_filter_layout = QHBoxLayout()
        self.serial_filter_input = QLineEdit()
        self.serial_filter_input.setPlaceholderText("Cihaz seri numarasıyla ara...")
        self.find_by_serial_btn = QPushButton("Bul")
        serial_filter_layout.addWidget(QLabel("Seri No:"))
        serial_filter_layout.addWidget(self.serial_filter_input)
        serial_filter_layout.addWidget(self.find_by_serial_btn)

        self.customer_table = QTableWidget(0, 2)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Ad Soyad"])
        self.customer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.customer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.customer_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.customer_table.hideColumn(0)
        
        layout.addLayout(customer_filter_layout)
        layout.addLayout(serial_filter_layout)
        layout.addWidget(self.customer_table)
        return panel

    def _create_right_panel(self):
        """Faturalandırma sekmelerini içeren sağ paneli oluşturur."""
        # FIXED: Add parent to prevent memory leak
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        
        self.tabs = QTabWidget()
        uninvoiced_widget = self._create_uninvoiced_tab()
        history_widget = self._create_history_tab()
        all_invoices_widget = self._create_all_invoices_tab()
        
        self.tabs.addTab(uninvoiced_widget, "Faturalandırılacak İşlemler")
        self.tabs.addTab(history_widget, "Kesilen Faturalar")
        self.tabs.addTab(all_invoices_widget, "Tüm Faturalar")
        
        layout.addWidget(self.tabs)
        return panel

    def _create_uninvoiced_tab(self):
        """Faturalandırılmayı bekleyen satışları gösteren sekmeyi oluşturur."""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Beklemede satışlar tablosu
        self.pending_sales_table = QTableWidget(0, 5)
        self.pending_sales_table.setHorizontalHeaderLabels(["ID", "Müşteri", "Tarih", "Tutar", "Para Birimi"])
        self.pending_sales_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.pending_sales_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pending_sales_table.hideColumn(0)
        self.pending_sales_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pending_sales_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.pending_sales_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.pending_sales_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(QLabel("Faturalandırılacak Satışlar:"))
        layout.addWidget(self.pending_sales_table)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.invoice_selected_btn = QPushButton("Seçilenleri Faturalandır")
        self.view_sale_details_btn = QPushButton("Satış Detayları")
        self.delete_pending_btn = QPushButton("Bekleyen Satışı Sil")
        
        button_layout.addWidget(self.invoice_selected_btn)
        button_layout.addWidget(self.view_sale_details_btn)
        button_layout.addWidget(self.delete_pending_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        return widget

    def _create_history_tab(self):
        """Geçmiş faturaları ve ilgili butonları gösteren sekmeyi oluşturur."""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        self.invoices_table = QTableWidget(0, 7)
        self.invoices_table.setHorizontalHeaderLabels(["Fatura ID", "Tarih", "Fatura Tipi", "Tutar", "Ödenen", "Kalan Bakiye", "Durum"])
        self.invoices_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoices_table.hideColumn(0)
        
        button_layout = QHBoxLayout()
        self.add_payment_btn = QPushButton("Ödeme Gir")
        self.print_invoice_btn = QPushButton("Seçili Faturayı Yazdır")
        self.merge_invoices_btn = QPushButton("Seçili Faturaların Dökümünü Ver")
        self.combine_invoices_btn = QPushButton("Faturaları Birleştir")
        self.delete_invoice_btn = QPushButton("Seçili Faturayı Sil")
        self.delete_invoice_btn.setStyleSheet("background-color: #D32F2F; color: white;")

        self.add_payment_btn.setEnabled(False)
        self.print_invoice_btn.setEnabled(False)
        self.delete_invoice_btn.setEnabled(False)
        
        button_layout.addWidget(self.add_payment_btn)
        button_layout.addWidget(self.print_invoice_btn)
        button_layout.addWidget(self.merge_invoices_btn)
        button_layout.addWidget(self.combine_invoices_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.delete_invoice_btn)
        
        layout.addWidget(self.invoices_table)
        layout.addLayout(button_layout)
        return widget

    def _create_all_invoices_tab(self):
        """Tüm faturaları müşteriden bağımsız gösteren sekmeyi oluşturur."""
        # FIXED: Add parent to prevent memory leak
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Tüm faturalar tablosu
        self.all_invoices_table = QTableWidget(0, 7)
        self.all_invoices_table.setHorizontalHeaderLabels(["Fatura ID", "Müşteri", "Tarih", "Fatura Tipi", "Tutar", "Para Birimi", "Durum"])
        self.all_invoices_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.all_invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.all_invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.all_invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.all_invoices_table.hideColumn(0)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.export_all_invoices_btn = QPushButton("📊 Tüm Faturalar Raporu (PDF)")
        self.export_all_invoices_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.export_all_invoices_btn)
        button_layout.addStretch()
        
        layout.addWidget(QLabel("Tüm Kesilen Faturalar:"))
        layout.addWidget(self.all_invoices_table)
        layout.addLayout(button_layout)
        return widget

    def _connect_signals(self):
        """Sinyalleri slotlara bağlar."""
        self.customer_filter_input.textChanged.connect(self.filter_customers)
        self.find_by_serial_btn.clicked.connect(self.find_by_serial)
        self.customer_table.itemSelectionChanged.connect(self.customer_selected)
        self.invoices_table.itemSelectionChanged.connect(self.update_button_states)
        
        self.add_payment_btn.clicked.connect(self.open_payment_dialog)
        self.print_invoice_btn.clicked.connect(self.print_selected_invoice)
        self.merge_invoices_btn.clicked.connect(self.merge_and_export_invoices)
        self.combine_invoices_btn.clicked.connect(self.combine_selected_invoices)
        self.delete_invoice_btn.clicked.connect(self.delete_selected_invoice)
        
        # Pending sales butonları
        self.invoice_selected_btn.clicked.connect(self.invoice_selected_pending_sales)
        self.view_sale_details_btn.clicked.connect(self.view_pending_sale_details)
        self.delete_pending_btn.clicked.connect(self.delete_pending_sale)
        
        # Tüm faturalar raporu butonu
        self.export_all_invoices_btn.clicked.connect(self.export_all_invoices_report)

    def update_button_states(self):
        """Seçime göre butonların durumunu günceller."""
        selected_count = len(self.invoices_table.selectionModel().selectedRows())
        is_single_selection = selected_count == 1
        self.add_payment_btn.setEnabled(is_single_selection)
        self.print_invoice_btn.setEnabled(is_single_selection)
        self.delete_invoice_btn.setEnabled(is_single_selection)

    def refresh_customers(self):
        """Müşteri listesini veritabanından yeniler."""
        current_id = self.selected_customer_id
        self.customer_table.setRowCount(0)
        try:
            customers = self.db.fetch_all("SELECT id, name FROM customers ORDER BY name")
            row_to_select = -1
            for i, (cust_id, name) in enumerate(customers):
                self.customer_table.insertRow(i)
                self.customer_table.setItem(i, 0, QTableWidgetItem(str(cust_id)))
                self.customer_table.setItem(i, 1, QTableWidgetItem(name))
                if cust_id == current_id:
                    row_to_select = i
            if row_to_select != -1:
                self.customer_table.selectRow(row_to_select)
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Müşteriler yüklenirken bir hata oluştu: {e}")

    def filter_customers(self):
        """Müşteri listesini arama kutusuna göre filtreler."""
        filter_text = self.customer_filter_input.text().lower()
        for row in range(self.customer_table.rowCount()):
            name_item = self.customer_table.item(row, 1)
            if name_item:
                self.customer_table.setRowHidden(row, filter_text not in name_item.text().lower())

    def find_by_serial(self):
        """Seri numarasına göre müşteriyi bulur ve seçer."""
        serial = self.serial_filter_input.text().strip()
        if not serial: return
        try:
            customer_info = self.db.find_customer_by_device_serial(serial)
            if customer_info:
                cust_id, cust_name = customer_info
                for row in range(self.customer_table.rowCount()):
                    if int(self.customer_table.item(row, 0).text()) == cust_id:
                        self.customer_table.selectRow(row)
                        self.customer_table.scrollToItem(self.customer_table.item(row, 0))
                        QMessageBox.information(self, "Müşteri Bulundu", f"'{serial}' seri numaralı cihaz '{cust_name}' adlı müşteriye aittir.")
                        return
                QMessageBox.warning(self, "Hata", "Müşteri veritabanında bulundu ancak listede görüntülenemiyor.")
            else:
                QMessageBox.warning(self, "Bulunamadı", f"'{serial}' seri numarasına sahip bir cihaz bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Arama Hatası", f"Seri numarası ile arama yapılırken bir hata oluştu: {e}")

    def customer_selected(self):
        """Müşteri seçildiğinde ilgili verileri yeniler."""
        selected = self.customer_table.selectionModel().selectedRows()
        if not selected:
            self.selected_customer_id = None
            self.pending_sales_table.setRowCount(0)
            self.invoices_table.setRowCount(0)
            return
        self.selected_customer_id = int(self.customer_table.item(selected[0].row(), 0).text())
        self.refresh_uninvoiced_items()
        self.refresh_invoices()

    def refresh_uninvoiced_items(self):
        """Beklemede olan satışları yeniler."""
        self.pending_sales_table.setRowCount(0)
        
        try:
            # Beklemede olan tüm satışları getir
            pending_sales = self.db.fetch_all("""
                SELECT ps.id, ps.customer_id, c.name as customer_name, ps.sale_date, 
                       ps.total_amount, ps.currency, ps.items_json
                FROM pending_sales ps
                JOIN customers c ON ps.customer_id = c.id
                WHERE ps.status = 'pending'
                ORDER BY ps.sale_date DESC
            """)
            
            for sale in pending_sales:
                row = self.pending_sales_table.rowCount()
                self.pending_sales_table.insertRow(row)
                
                self.pending_sales_table.setItem(row, 0, QTableWidgetItem(str(sale[0])))  # ID
                self.pending_sales_table.setItem(row, 1, QTableWidgetItem(sale[2]))     # Müşteri adı
                self.pending_sales_table.setItem(row, 2, QTableWidgetItem(sale[3][:16])) # Tarih (sadece tarih kısmı)
                self.pending_sales_table.setItem(row, 3, QTableWidgetItem(f"{sale[4]:.2f}")) # Tutar
                self.pending_sales_table.setItem(row, 4, QTableWidgetItem(sale[5]))     # Para birimi
                
        except Exception as e:
            QMessageBox.critical(self, "Veri Hatası", f"Beklemede satışlar yüklenirken hata: {e}")

    def refresh_invoices(self):
        """Geçmiş faturaları yeniler."""
        self.invoices_table.setRowCount(0)
        self.update_button_states()
        if not self.selected_customer_id: return
        try:
            invoices = self.db.get_invoices_for_customer(self.selected_customer_id)
            for row_data in invoices:
                row = self.invoices_table.rowCount()
                self.invoices_table.insertRow(row)
                inv_id = row_data.get('id', '')
                date = row_data.get('invoice_date', '')
                inv_type = row_data.get('invoice_type', '')
                total = row_data.get('total_amount', 0)
                paid = row_data.get('paid_amount', 0)
                balance = row_data.get('balance', 0)
                status = row_data.get('status', '')
                currency = row_data.get('currency', '')
                self.invoices_table.setItem(row, 0, QTableWidgetItem(str(inv_id)))
                self.invoices_table.setItem(row, 1, QTableWidgetItem(str(date)))
                self.invoices_table.setItem(row, 2, QTableWidgetItem(str(inv_type)))
                # Güvenli float formatlama
                try:
                    total_val = float(total)
                except (TypeError, ValueError):
                    total_val = 0.0
                try:
                    paid_val = float(paid)
                except (TypeError, ValueError):
                    paid_val = 0.0
                try:
                    balance_val = float(balance)
                except (TypeError, ValueError):
                    balance_val = 0.0
                self.invoices_table.setItem(row, 3, QTableWidgetItem(f"{total_val:.2f} {currency}"))
                self.invoices_table.setItem(row, 4, QTableWidgetItem(f"{paid_val:.2f} {currency}"))
                self.invoices_table.setItem(row, 5, QTableWidgetItem(f"{balance_val:.2f} {currency}"))
                self.invoices_table.setItem(row, 6, QTableWidgetItem(str(status)))
        except Exception as e:
            QMessageBox.critical(self, "Veri Hatası", f"Geçmiş faturalar yüklenirken bir hata oluştu: {e}")

    def open_invoice_creation_dialog(self):
        """Seçili faturalanmamış kalemler için fatura oluşturma diyalogunu açar."""
        selected_items = self.pending_sales_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen faturalandırmak için en az bir işlem seçin.")
            return
        
        selected_rows = sorted(list(set(item.row() for item in selected_items)))
        item_ids = [self.pending_sales_table.item(row, 0).text() for row in selected_rows]
        
        try:
            items_to_invoice = self.db.get_items_for_invoice_creation(item_ids)
            if not items_to_invoice:
                QMessageBox.warning(self, "Boş İşlemler", "Seçilen işlemlerin faturalandırılabilir bir içeriği bulunamadı.")
                return

            customer_info = {'id': self.selected_customer_id, 'name': self.customer_table.item(self.customer_table.currentRow(), 1).text()}
            
            dialog = InvoicePreviewDialog(self.db, customer_info, items_to_invoice, self)
            if dialog.exec():
                invoice_data = dialog.get_invoice_data()
                if invoice_data:
                    result = self.db.create_consolidated_invoice(**invoice_data)
                    if result is True:
                        QMessageBox.information(self, "Başarılı", "Fatura başarıyla oluşturuldu.")
                        self.refresh_data()
                    else:
                        QMessageBox.critical(self, "Hata", str(result))
        except Exception as e:
            QMessageBox.critical(self, "Diyalog Hatası", f"Fatura oluşturma penceresi açılamadı: {e}")

    def open_payment_dialog(self):
        """Ödeme giriş diyalogunu açar."""
        selected_rows = self.invoices_table.selectionModel().selectedRows()
        if not selected_rows: return
            
        try:
            row = selected_rows[0].row()
            invoice_id = int(self.invoices_table.item(row, 0).text())
            invoice_details = self.db.get_full_invoice_details(invoice_id)
            
            if not invoice_details:
                QMessageBox.critical(self, "Hata", "Fatura detayları alınamadı.")
                return

            dialog = PaymentDialog(invoice_details, self)
            if dialog.exec():
                data = dialog.get_data()
                if data and data['amount_paid'] > 0:
                    self.db.add_payment(invoice_id, **data)
                    self.refresh_invoices()
                elif data is not None:
                    QMessageBox.warning(self, "Geçersiz Giriş", "Ödeme miktarı 0'dan büyük bir sayı olmalıdır.")
        except Exception as e:
            QMessageBox.critical(self, "Diyalog Hatası", f"Ödeme penceresi açılamadı: {e}")

    def print_selected_invoice(self):
        """Seçili faturayı PDF olarak yazdırır."""
        selected_rows = self.invoices_table.selectionModel().selectedRows()
        if not selected_rows: return
        
        try:
            invoice_id = int(self.invoices_table.item(selected_rows[0].row(), 0).text())
            pdf_data = self.db.get_full_invoice_details(invoice_id)
            if not pdf_data:
                QMessageBox.critical(self, "Hata", "Fatura yazdırma verileri alınamadı.")
                return
            
            print(f"DEBUG: PDF data items count: {len(pdf_data.get('items', []))}")
            for i, item in enumerate(pdf_data.get('items', [])):
                print(f"DEBUG: Item {i}: {item}")
            
            # Firma ve müşteri bilgileri eksikse ayarlardan doldur
            if not pdf_data.get('company_info'):
                pdf_data['company_info'] = {
                    'name': self.db.get_setting('company_name', 'Firma Adı'),
                    'address': self.db.get_setting('company_address', 'Adres Bilgisi Yok'),
                    'phone': self.db.get_setting('company_phone', 'Telefon Bilgisi Yok'),
                    'tax_office': self.db.get_setting('company_tax_office', ''),
                    'tax_id': self.db.get_setting('company_tax_id', ''),
                    'email': self.db.get_setting('company_email', ''),
                    'bank_name': self.db.get_setting('company_bank_name', ''),
                    'bank_account_holder': self.db.get_setting('company_bank_account_holder', ''),
                    'bank_iban': self.db.get_setting('company_bank_iban', ''),
                    'logo_path': self.db.get_setting('company_logo_path', ''),
                }
            if not pdf_data.get('customer_info'):
                # Müşteri bilgisi yoksa, müşteri tablosundan çek
                cust_row = self.customer_table.currentRow()
                pdf_data['customer_info'] = {
                    'name': self.customer_table.item(cust_row, 1).text() if cust_row >= 0 else '',
                    'address': '',
                    'phone': '',
                    'tax_id': '',
                }
            
            # Müşteri adından güvenli dosya adı oluştur
            customer_name = pdf_data.get('customer_info', {}).get('name', 'Musteri')
            safe_customer_name = "".join(c for c in customer_name if c.isalnum() or c in " _-").strip()
            if not safe_customer_name:
                safe_customer_name = "Musteri"
            
            file_path, _ = QFileDialog.getSaveFileName(self, "Faturayı Kaydet", f"fatura_{safe_customer_name}_{invoice_id}.pdf", "PDF Dosyaları (*.pdf)")
            if not file_path: return
            create_professional_invoice_pdf(pdf_data, file_path)
            QMessageBox.information(self, "Başarılı", f"Fatura başarıyla kaydedildi:\n{file_path}")
            if os.name == 'nt':
                os.startfile(file_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulurken veya açılırken bir hata oluştu: {e}")

    def merge_and_export_invoices(self):
        """Seçili faturaları tek bir PDF'te birleştirir."""
        import logging
        selected_items = self.invoices_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen birleştirmek için en az bir fatura seçin.")
            return

        selected_rows = sorted(list(set(item.row() for item in selected_items)))
        invoice_ids = [int(self.invoices_table.item(row, 0).text()) for row in selected_rows]
        logging.info(f"Birleştirilecek fatura ID'leri: {invoice_ids}")

        try:
            invoices_data = [self.db.get_full_invoice_details(inv_id) for inv_id in invoice_ids if self.db.get_full_invoice_details(inv_id)]
            logging.info(f"Birleştirilecek fatura veri sayısı: {len(invoices_data)}")
            for idx, inv in enumerate(invoices_data):
                logging.info(f"Fatura {idx+1}: {inv.get('id') if inv else 'None'}")
            if not invoices_data:
                QMessageBox.critical(self, "Hata", "Seçili faturaların detayları alınamadı.")
                return

            customer_name = self.customer_table.item(self.customer_table.currentRow(), 1).text()
            safe_customer_name = "".join(c for c in customer_name if c.isalnum() or c in " _-").rstrip()
            file_path, _ = QFileDialog.getSaveFileName(self, "Birleştirilmiş Faturayı Kaydet", f"toplu_dokum_{safe_customer_name}.pdf", "PDF Dosyaları (*.pdf)")
            
            if not file_path: return

            create_merged_invoice_pdf(customer_name, invoices_data, file_path)
            QMessageBox.information(self, "Başarılı", f"Faturalar başarıyla birleştirildi:\n{file_path}")
            if os.name == 'nt': os.startfile(file_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"Birleştirilmiş PDF oluşturulurken bir hata oluştu: {e}")

    def combine_selected_invoices(self):
        """Seçili faturaları tek bir fatura içerisinde birleştirir."""
        import logging
        from utils.pdf_generator import create_combined_invoice_pdf
        
        selected_items = self.invoices_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen birleştirmek için en az bir fatura seçin.")
            return

        selected_rows = sorted(list(set(item.row() for item in selected_items)))
        invoice_ids = [int(self.invoices_table.item(row, 0).text()) for row in selected_rows]
        logging.info(f"Birleştirilecek fatura ID'leri: {invoice_ids}")

        try:
            invoices_data = [self.db.get_full_invoice_details(inv_id) for inv_id in invoice_ids if self.db.get_full_invoice_details(inv_id)]
            logging.info(f"Birleştirilecek fatura veri sayısı: {len(invoices_data)}")
            
            if not invoices_data:
                QMessageBox.critical(self, "Hata", "Seçili faturaların detayları alınamadı.")
                return

            customer_name = self.customer_table.item(self.customer_table.currentRow(), 1).text()
            safe_customer_name = "".join(c for c in customer_name if c.isalnum() or c in " _-").rstrip()
            file_path, _ = QFileDialog.getSaveFileName(self, "Birleştirilmiş Tek Faturayı Kaydet", f"birlesik_fatura_{safe_customer_name}.pdf", "PDF Dosyaları (*.pdf)")
            
            if not file_path: return

            create_combined_invoice_pdf(customer_name, invoices_data, file_path)
            QMessageBox.information(self, "Başarılı", f"Faturalar tek fatura içinde başarıyla birleştirildi:\n{file_path}")
            if os.name == 'nt': os.startfile(file_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"Birleştirilmiş tek fatura oluşturulurken bir hata oluştu: {e}")

    def delete_selected_invoice(self):
        """Seçili faturayı veritabanından siler."""
        selected_rows = self.invoices_table.selectionModel().selectedRows()
        if not selected_rows: return

        row = selected_rows[0].row()
        invoice_id = int(self.invoices_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, 'Faturayı Sil', 
                                     f"'{invoice_id}' numaralı faturayı kalıcı olarak silmek istediğinizden emin misiniz?\n"
                                     "Bu işlem geri alınamaz ve ilişkili servis/sayaç kayıtları tekrar 'faturalanmadı' olarak işaretlenir.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.db.delete_invoice(invoice_id)
                if result is True:
                    QMessageBox.information(self, "Başarılı", "Fatura başarıyla silindi.")
                    self.refresh_data()
                else:
                    QMessageBox.critical(self, "Silme Hatası", str(result))
            except Exception as e:
                QMessageBox.critical(self, "Silme Hatası", f"Fatura silinirken bir hata oluştu: {e}")

    def refresh_data(self):
        """Tüm sekme verilerini yeniler."""
        self.refresh_customers()
        self.refresh_uninvoiced_items()
        self.refresh_invoices()
        self.refresh_all_invoices()

    def invoice_selected_pending_sales(self):
        """Seçili beklemede olan satışları faturalandır."""
        selected_rows = self.pending_sales_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yok", "Lütfen faturalandırılacak satışları seçin.")
            return
            
        try:
            # Seçili satışları işle ve faturalandır
            for row in selected_rows:
                sale_id = int(self.pending_sales_table.item(row.row(), 0).text())
                result = self.db.convert_pending_sale_to_invoice(sale_id)
                if not isinstance(result, int):
                    QMessageBox.critical(self, "Faturalama Hatası", f"Satış ID {sale_id} faturalandırılamadı: {result}")
                    return
            
            QMessageBox.information(self, "Başarılı", f"{len(selected_rows)} satış başarıyla faturalandırıldı.")
            self.refresh_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Faturalama Hatası", f"Faturalama sırasında hata: {e}")

    def view_pending_sale_details(self):
        """Beklemede olan satışın detaylarını göster."""
        selected_rows = self.pending_sales_table.selectionModel().selectedRows()
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Seçim Hatası", "Lütfen bir satış seçin.")
            return
            
        try:
            sale_id = int(self.pending_sales_table.item(selected_rows[0].row(), 0).text())
            sale_data = self.db.fetch_one("SELECT * FROM pending_sales WHERE id = ?", (sale_id,))
            
            if not sale_data:
                QMessageBox.warning(self, "Veri Bulunamadı", "Satış verisi bulunamadı.")
                return
                
            # Satış detaylarını göster
            import json
            
            # Yeni format kontrolü - total_amount ve items_json sütunları varsa yeni format
            items_json = None
            total_amount = 0.0
            currency = "TL"
            
            if len(sale_data) > 6:  # Yeni format
                total_amount = sale_data[3] if sale_data[3] else 0.0
                currency = sale_data[4] if sale_data[4] else "TL"
                items_json = sale_data[5]  # items_json sütunu
                
                if not items_json and len(sale_data) > 6:
                    items_json = sale_data[6]  # sale_data_json sütunu
            else:  # Eski format
                # sale_data_json (migration ile eklenen) varsa onu kullan (indeks 8)
                if len(sale_data) > 8 and sale_data[8]:
                    items_json = sale_data[8]
                # yoksa items_json kullan (indeks 5)
                elif len(sale_data) > 5 and sale_data[5]:
                    items_json = sale_data[5]
            
            # JSON verisini temizle ve parse et
            if items_json:
                try:
                    # Eğer string ise parse et
                    if isinstance(items_json, str):
                        data = json.loads(items_json)
                    # Eğer zaten dict ise direkt kullan  
                    elif isinstance(items_json, dict):
                        data = items_json
                    # Eğer list ise direkt kullan
                    elif isinstance(items_json, list):
                        data = items_json
                    else:
                        # Başka tipte ise string'e çevir ve parse et
                        data = json.loads(str(items_json))
                        
                    # Yeni format kontrolü
                    if isinstance(data, dict) and 'items' in data:
                        # Yeni format: {'customer_id': x, 'items': [...]}
                        items = data['items']
                    elif isinstance(data, list):
                        # Direkt items listesi
                        items = data
                    else:
                        # Eski format: {'customer_id': x, 'devices': [], 'toners': [], 'consumables': []}
                        items = []
                        if isinstance(data, dict):
                            if 'devices' in data:
                                items.extend(data['devices'])
                            if 'toners' in data:
                                items.extend(data['toners'])
                            if 'consumables' in data:
                                items.extend(data['consumables'])
                        
                except json.JSONDecodeError as json_error:
                    import logging
                    logging.error(f"JSON parse hatası: {json_error}")
                    logging.error(f"Problematik JSON: '{items_json}'")
                    QMessageBox.critical(self, "JSON Hatası", f"Satış verisi geçersiz JSON formatında:\n{json_error}\n\nVeri: {items_json}")
                    return
            else:
                items = []
            
            # Detayları oluştur
            details = f"Satış ID: {sale_data[0]}\n"
            details += f"Müşteri ID: {sale_data[1]}\n"
            details += f"Tarih: {sale_data[2]}\n"
            
            if total_amount > 0:
                details += f"Toplam: {total_amount:.2f} {currency}\n\n"
            else:
                # Eski format için toplam hesapla
                calculated_total = 0.0
                for item in items:
                    if isinstance(item, dict):
                        quantity = item.get('quantity', 0)
                        unit_price = item.get('unit_price', item.get('price', 0))
                        calculated_total += quantity * unit_price
                details += f"Toplam: {calculated_total:.2f} {currency}\n\n"
            
            details += "Ürünler:\n"
            
            if isinstance(items, list) and items:
                for item in items:
                    if isinstance(item, dict):
                        name = item.get('description', item.get('name', item.get('model', 'Bilinmiyen ürün')))
                        quantity = item.get('quantity', 0)
                        unit_price = item.get('unit_price', item.get('price', 0))
                        item_currency = item.get('currency', currency)
                        
                        # Bedelsiz ürün kontrolü
                        if unit_price == 0:
                            details += f"- {name}: {quantity} adet x {unit_price:.2f} {item_currency} [BEDELSİZ]\n"
                        else:
                            details += f"- {name}: {quantity} adet x {unit_price:.2f} {item_currency}\n"
                            
                        # Seri numaraları varsa göster
                        serials = item.get('serial_numbers', [])
                        if serials:
                            details += f"  Seri No: {', '.join(serials)}\n"
                    else:
                        details += f"- {item}\n"
            else:
                details += "Ürün bulunamadı.\n"
                
            QMessageBox.information(self, "Satış Detayları", details)
            
        except Exception as e:
            QMessageBox.critical(self, "Detay Hatası", f"Satış detayları gösterilirken hata: {e}")
            import traceback
            print(f"Detay hatası: {traceback.format_exc()}")

    def delete_pending_sale(self):
        """Beklemede olan satışı sil."""
        selected_rows = self.pending_sales_table.selectionModel().selectedRows()
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Seçim Hatası", "Lütfen bir satış seçin.")
            return
            
        reply = QMessageBox.question(
            self, "Satış Sil", 
            "Beklemede olan satışı silmek istediğinizden emin misiniz?\n\nDikkat: Bu işlem geri alınamaz ve stok miktarları geri yüklenmeyecek.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                sale_id = int(self.pending_sales_table.item(selected_rows[0].row(), 0).text())
                self.db.execute_query("DELETE FROM pending_sales WHERE id = ?", (sale_id,))
                
                QMessageBox.information(self, "Başarılı", "Beklemede olan satış silindi.")
                self.refresh_uninvoiced_items()
                
            except Exception as e:
                QMessageBox.critical(self, "Silme Hatası", f"Satış silinirken hata: {e}")

    def refresh_all_invoices(self):
        """Tüm faturaları müşteriden bağımsız olarak yeniler."""
        self.all_invoices_table.setRowCount(0)
        
        try:
            # Tüm faturaları getir (müşteri bilgisi ile)
            invoices = self.db.fetch_all("""
                SELECT i.id, c.name, i.invoice_date, i.invoice_type, 
                       i.total_amount, i.currency, i.status
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                ORDER BY i.invoice_date DESC
            """)
            
            for invoice_data in invoices:
                row = self.all_invoices_table.rowCount()
                self.all_invoices_table.insertRow(row)
                
                inv_id = invoice_data[0]
                customer_name = invoice_data[1]
                date = invoice_data[2]
                inv_type = invoice_data[3]
                total = invoice_data[4]
                currency = invoice_data[5]
                status = invoice_data[6]
                
                self.all_invoices_table.setItem(row, 0, QTableWidgetItem(str(inv_id)))
                self.all_invoices_table.setItem(row, 1, QTableWidgetItem(str(customer_name)))
                self.all_invoices_table.setItem(row, 2, QTableWidgetItem(str(date)))
                self.all_invoices_table.setItem(row, 3, QTableWidgetItem(str(inv_type)))
                
                # Güvenli float formatlama
                try:
                    total_val = float(total)
                except (TypeError, ValueError):
                    total_val = 0.0
                
                self.all_invoices_table.setItem(row, 4, QTableWidgetItem(f"{total_val:.2f}"))
                self.all_invoices_table.setItem(row, 5, QTableWidgetItem(str(currency)))
                self.all_invoices_table.setItem(row, 6, QTableWidgetItem(str(status)))
                
        except Exception as e:
            QMessageBox.critical(self, "Veri Hatası", f"Tüm faturalar yüklenirken bir hata oluştu: {e}")

    def export_all_invoices_report(self):
        """Tüm faturaları PDF raporu olarak dışa aktarır."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from datetime import datetime
            import json
            
            # Font'ları kaydet
            from utils.pdf_generator import register_fonts
            register_fonts()
            
            # Dosya kaydetme dialog'u
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Tüm Faturalar Raporunu Kaydet", 
                f"tum_faturalar_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
                "PDF Dosyaları (*.pdf)"
            )
            
            if not file_path:
                return
            
            # PDF oluştur
            doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            story = []
            styles = getSampleStyleSheet()
            
            # Normal stil için Türkçe font ayarla
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName='DejaVuSans',
                fontSize=10
            )
            
            # Başlık stili
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1976D2'),
                spaceAfter=30,
                alignment=1,  # Center
                fontName='DejaVuSans-Bold'
            )
            
            # Başlık ekle
            story.append(Paragraph("TÜM FATURALAR RAPORU", title_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Firma bilgileri
            company_name = self.db.get_setting('company_name', 'Firma Adı')
            story.append(Paragraph(f"<b>Firma:</b> {company_name}", normal_style))
            story.append(Paragraph(f"<b>Rapor Tarihi:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
            story.append(Spacer(1, 1*cm))
            
            # Tüm faturaları getir
            invoices = self.db.fetch_all("""
                SELECT i.id, c.name, i.invoice_date, i.invoice_type, 
                       i.total_amount, i.currency, i.details_json, i.exchange_rate
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                ORDER BY i.invoice_date DESC
            """)
            
            # Tablo verileri hazırla
            table_data = [['Fatura No', 'Müşteri', 'Tarih', 'Tip', 'İçerik', 'Tutar (TL)']]
            
            total_sum_tl = 0.0
            
            for inv_data in invoices:
                inv_id = inv_data[0]
                customer_name = inv_data[1]
                date = inv_data[2]
                inv_type = inv_data[3]
                total_amount = float(inv_data[4])
                currency = inv_data[5]
                details_json = inv_data[6]
                exchange_rate = float(inv_data[7]) if inv_data[7] else 1.0
                
                # İçerik parse et
                content = ""
                try:
                    items = json.loads(details_json) if details_json else []
                    content_list = []
                    for item in items:
                        if isinstance(item, dict):
                            desc = item.get('description', item.get('name', 'Bilinmeyen'))
                            qty = item.get('quantity', 0)
                            content_list.append(f"{desc} ({qty} adet)")
                    content = ", ".join(content_list[:3])  # İlk 3 ürün
                    if len(items) > 3:
                        content += f" + {len(items) - 3} ürün"
                except:
                    content = "İçerik okunamadı"
                
                # TL'ye çevir
                if currency == 'TL':
                    amount_tl = total_amount
                else:
                    amount_tl = total_amount * exchange_rate
                
                total_sum_tl += amount_tl
                
                table_data.append([
                    str(inv_id),
                    customer_name[:30],
                    date[:10] if date else '',
                    inv_type,
                    content[:50],
                    f"{amount_tl:.2f}"
                ])
            
            # Toplam satırı ekle
            table_data.append(['', '', '', '', 'TOPLAM:', f"{total_sum_tl:.2f} TL"])
            
            # Tablo oluştur
            table = Table(table_data, colWidths=[2*cm, 4*cm, 2.5*cm, 2*cm, 5*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (5, 0), (5, -1), 'RIGHT'),  # Tutar kolonunu sağa hizala
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFE082')),
                ('FONTNAME', (0, -1), (-1, -1), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
            ]))
            
            story.append(table)
            
            # PDF'i oluştur
            doc.build(story)
            
            QMessageBox.information(self, "Başarılı", f"Tüm faturalar raporu oluşturuldu:\n{file_path}")
            
            # PDF'i aç
            if os.name == 'nt':
                os.startfile(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Rapor oluşturulurken hata: {e}")
            import traceback
            print(f"Rapor hatası: {traceback.format_exc()}")
