# ui/dialogs/monthly_report_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from utils.pdf_generator import create_table_report_pdf

class MonthlyReportDialog(QDialog):
    """Genel amaçlı, tablo formatında veri gösteren ve raporlayan bir diyalog."""
    
    def __init__(self, title: str, headers: list, data: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 500)
        
        self.title = title
        self.headers = headers
        self.data = data
        
        self._init_ui()
        self._populate_table()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        self.layout = QVBoxLayout(self)
        self._create_widgets()
        self._create_layout()
        self._connect_signals()

    def _create_widgets(self):
        """Arayüz elemanlarını (widget) oluşturur."""
        self.report_table = QTableWidget(0, len(self.headers))
        self.report_table.setHorizontalHeaderLabels(self.headers)
        self.report_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.report_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.pdf_button = QPushButton("PDF Olarak Kaydet")
        self.print_button = QPushButton("Yazdır")

    def _create_layout(self):
        """Widget'ları layout'a yerleştirir."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.pdf_button)
        button_layout.addWidget(self.print_button)
        
        self.layout.addWidget(self.report_table)
        self.layout.addLayout(button_layout)

    def _connect_signals(self):
        """Sinyalleri ilgili slotlara bağlar."""
        self.pdf_button.clicked.connect(self._export_to_pdf)
        self.print_button.clicked.connect(self._print_report)

    def _populate_table(self):
        """Gelen verileri tabloya doldurur."""
        try:
            for row_data in self.data:
                row = self.report_table.rowCount()
                self.report_table.insertRow(row)
                for col_index, col_data in enumerate(row_data):
                    item = QTableWidgetItem(str(col_data))
                    if isinstance(col_data, (int, float)):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.report_table.setItem(row, col_index, item)
        except Exception as e:
            QMessageBox.critical(self, "Tablo Oluşturma Hatası", f"Rapor verileri işlenirken bir hata oluştu: {e}")

    def _export_to_pdf(self):
        """Raporu bir PDF dosyası olarak kaydeder."""
        safe_title = "".join(c for c in self.title if c.isalnum() or c in " _-").rstrip()
        file_path, _ = QFileDialog.getSaveFileName(self, "Raporu PDF Olarak Kaydet", f"{safe_title}.pdf", "PDF Dosyaları (*.pdf)")
        if not file_path:
            return
            
        try:
            string_data = [[str(cell) for cell in row] for row in self.data]
            create_table_report_pdf(self.title, self.headers, string_data, file_path)
            QMessageBox.information(self, "Başarılı", f"Rapor başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "PDF Oluşturma Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")

    def _print_report(self):
        """Raporu bir yazıcıya gönderir."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            document = self._create_html_document_for_printing()
            document.print(printer)

    def _create_html_document_for_printing(self) -> QTextDocument:
        """Yazdırma işlemi için tablodan bir HTML dokümanı oluşturur."""
        html = f"<h1>{self.title}</h1>"
        html += "<table border='1' cellspacing='0' cellpadding='5' width='100%'>"
        html += "<thead><tr>"
        for header in self.headers:
            html += f"<th>{header}</th>"
        html += "</tr></thead>"
        html += "<tbody>"
        for row in self.data:
            html += "<tr>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>"
        html += "</tbody></table>"
        
        doc = QTextDocument()
        doc.setHtml(html)
        return doc