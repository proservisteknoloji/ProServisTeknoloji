# ui/dialogs/stock_report_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QComboBox, QPushButton, QTextEdit, 
                             QMessageBox, QProgressBar, QGroupBox, QFrame)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
import pandas as pd
from pathlib import Path
import os
from datetime import datetime

class StockReportWorker(QThread):
    """Stok raporu oluşturma işlemini arka planda gerçekleştiren worker."""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(int)
    
    def __init__(self, db, report_type, export_format):
        super().__init__()
        self.db = db
        self.report_type = report_type
        self.export_format = export_format
        
    def run(self):
        try:
            self.progress.emit(10)
            
            # Veri çekme
            if self.report_type == "Tüm Stok":
                query = """
                SELECT 
                    item_type as 'Tip',
                    name as 'İsim/Model',
                    part_number as 'Parça No',
                    quantity as 'Miktar',
                    CASE 
                        WHEN purchase_currency = 'TL' THEN PRINTF('%.2f TL', purchase_price)
                        ELSE PRINTF('%.2f %s', purchase_price, purchase_currency)
                    END as 'Alış Fiyatı',
                    CASE 
                        WHEN sale_currency = 'TL' THEN PRINTF('%.2f TL', sale_price)
                        ELSE PRINTF('%.2f %s', sale_price, sale_currency)
                    END as 'Satış Fiyatı',
                    supplier as 'Tedarikçi'
                FROM stock_items 
                ORDER BY item_type, name
                """
            else:
                query = """
                SELECT 
                    name as 'İsim/Model',
                    part_number as 'Parça No',
                    quantity as 'Miktar',
                    CASE 
                        WHEN purchase_currency = 'TL' THEN PRINTF('%.2f TL', purchase_price)
                        ELSE PRINTF('%.2f %s', purchase_price, purchase_currency)
                    END as 'Alış Fiyatı',
                    CASE 
                        WHEN sale_currency = 'TL' THEN PRINTF('%.2f TL', sale_price)
                        ELSE PRINTF('%.2f %s', sale_price, sale_currency)
                    END as 'Satış Fiyatı',
                    supplier as 'Tedarikçi'
                FROM stock_items 
                WHERE item_type = ?
                ORDER BY name
                """
            
            self.progress.emit(30)
            
            if self.report_type == "Tüm Stok":
                data = self.db.fetch_all(query)
            else:
                data = self.db.fetch_all(query, (self.report_type,))
            
            if not data:
                self.finished.emit(False, "Rapor oluşturulacak veri bulunamadı.")
                return
                
            self.progress.emit(50)
            
            # DataFrame oluştur - Column bilgilerini manuel olarak tanımlayalım
            if self.report_type == "Tüm Stok":
                columns = ['Tip', 'İsim/Model', 'Parça No', 'Miktar', 'Alış Fiyatı', 'Satış Fiyatı', 'Tedarikçi']
            else:
                columns = ['İsim/Model', 'Parça No', 'Miktar', 'Alış Fiyatı', 'Satış Fiyatı', 'Tedarikçi']
            
            df = pd.DataFrame(data, columns=columns)
            
            self.progress.emit(70)
            
            # Dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Stok_Raporu_{self.report_type.replace(' ', '_')}_{timestamp}"
            
            # Desktop yolu
            desktop_path = Path.home() / "Desktop"
            
            if self.export_format == "Excel":
                file_path = desktop_path / f"{filename}.xlsx"
                df.to_excel(file_path, index=False, engine='openpyxl')
            else:  # PDF
                file_path = desktop_path / f"{filename}.pdf"
                self._create_pdf_report(df, file_path)
            
            self.progress.emit(100)
            self.finished.emit(True, f"Rapor başarıyla oluşturuldu:\n{file_path}")
            
        except Exception as e:
            self.finished.emit(False, f"Rapor oluşturulurken hata oluştu: {str(e)}")
    
    def _create_pdf_report(self, df, file_path):
        """PDF raporu oluşturur."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Font kaydı
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'resources/fonts/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'resources/fonts/DejaVuSans-Bold.ttf'))
        except:
            pass
        
        doc = SimpleDocTemplate(str(file_path), pagesize=landscape(A4))
        story = []
        
        # Stil tanımlamaları
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='DejaVuSans-Bold',
            fontSize=16,
            alignment=1  # Center
        )
        
        # Başlık
        title = Paragraph(f"{self.report_type} Stok Raporu", title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Tarih
        date_text = f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        date_para = Paragraph(date_text, styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 0.3*inch))
        
        # Tablo verisi hazırla
        data = [df.columns.tolist()]  # Header
        for _, row in df.iterrows():
            data.append([str(cell) for cell in row])
        
        # Tablo oluştur
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        doc.build(story)


class StockReportDialog(QDialog):
    """Stok raporu oluşturma diyalogu."""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Stok Raporu")
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self._init_ui()
        
    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        layout = QVBoxLayout(self)
        
        # Başlık
        title_label = QLabel("Stok Raporu Oluştur")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Ayırıcı çizgi
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Seçenekler grubu
        options_group = QGroupBox("Rapor Seçenekleri")
        options_layout = QGridLayout(options_group)
        
        # Rapor tipi
        options_layout.addWidget(QLabel("Rapor Tipi:"), 0, 0)
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["Tüm Stok", "Toner", "Yedek Parça", "Cihaz"])
        options_layout.addWidget(self.report_type_combo, 0, 1)
        
        # Export formatı
        options_layout.addWidget(QLabel("Dosya Formatı:"), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel", "PDF"])
        options_layout.addWidget(self.format_combo, 1, 1)
        
        layout.addWidget(options_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Durum metni
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Rapor Oluştur")
        self.close_btn = QPushButton("Kapat")
        
        button_layout.addStretch()
        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Sinyaller
        self.generate_btn.clicked.connect(self.generate_report)
        self.close_btn.clicked.connect(self.close)
        
        # İlk durum mesajı
        self.status_text.append("Rapor oluşturmak için seçenekleri belirleyin ve 'Rapor Oluştur' butonuna tıklayın.")
        
    def generate_report(self):
        """Rapor oluşturma işlemini başlatır."""
        report_type = self.report_type_combo.currentText()
        export_format = self.format_combo.currentText()
        
        self.status_text.append(f"\n{report_type} raporu oluşturuluyor...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.generate_btn.setEnabled(False)
        
        # Worker thread başlat
        self.worker = StockReportWorker(self.db, report_type, export_format)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_report_finished)
        self.worker.start()
        
    def on_report_finished(self, success, message):
        """Rapor oluşturma işlemi tamamlandığında çağrılır."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        if success:
            self.status_text.append(f"✅ {message}")
            QMessageBox.information(self, "Başarılı", message)
        else:
            self.status_text.append(f"❌ {message}")
            QMessageBox.warning(self, "Hata", message)