# ui/dashboard_tab.py

import logging
logger = logging.getLogger(__name__)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal
from PyQt6.QtGui import QPainter, QColor

# Charts modülünü conditional import et
try:
    from PyQt6.QtCharts import QChart, QChartView, QPieSeries
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    # Dummy sınıflar oluştur
    class QChartView:
        def __init__(self, *args, **kwargs):
            pass
    class QChart:
        def __init__(self, *args, **kwargs):
            pass
    class QPieSeries:
        def __init__(self, *args, **kwargs):
            pass

from utils.database import db_manager
from datetime import datetime
from utils.currency_converter import get_exchange_rates
from .custom_widgets import ClickableStatCard
from .dialogs.monthly_report_dialog import MonthlyReportDialog

if CHARTS_AVAILABLE:
    class DonutChartView(QChartView):
        """Donut grafiği gösterimi için özelleştirilmiş widget."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.series = QPieSeries()
            self.series.setHoleSize(0.40)
            
            self.chart = QChart()
            self.chart.addSeries(self.series)
            self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
            self.chart.layout().setContentsMargins(0, 0, 0, 0)
            self.chart.setBackgroundRoundness(0)
            self.setChart(self.chart)
            
        def update_data(self, invoiced, paid):
            """Grafik verilerini günceller."""
            self.series.clear()
            total = invoiced + paid
            if total > 0:
                slice_invoiced = self.series.append(f"Faturalar ({invoiced:,.2f} TL)", invoiced)
                slice_paid = self.series.append(f"Tahsilat ({paid:,.2f} TL)", paid)
                slice_invoiced.setColor(QColor("#3B82F6"))
                slice_paid.setColor(QColor("#10B981"))
                for s in self.series.slices():
                    s.setLabelVisible(True)
                    s.setLabel(f"{s.percentage()*100:.1f}%")
            else:
                slice_empty = self.series.append("Veri Yok", 1)
                slice_empty.setColor(QColor("#E5E7EB"))
else:
    # Charts olmadan alternatif görünüm
    from PyQt6.QtWidgets import QLabel
    class DonutChartView(QLabel):
        """Charts yokken basit metin görünümü."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px; padding: 20px;")
            self.setText("Grafik görünümü için PyQt6-Charts gerekli")
            
        def update_data(self, invoiced, paid):
            """Basit metin güncellemesi."""
            self.setText(f"Faturalar: {invoiced:,.2f} TL\nTahsilat: {paid:,.2f} TL")

class DashboardTab(QWidget):
    """Ana gösterge paneli sekmesi."""
    data_changed = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self._start_timers()
        self.refresh_data()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self)
        
        header = self._create_header()
        
        content_layout = QHBoxLayout()
        left_column = self._create_left_column()
        
        # Chart view'i sadece charts mevcut ise oluştur
        if CHARTS_AVAILABLE:
            self.chart_view = DonutChartView()
        else:
            # Chart yerine basit bir label ekle
            self.chart_view = QLabel("Grafik görünümü için PyQt6-Charts gerekli")
            self.chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chart_view.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 20px;
                    background-color: #f5f5f5;
                    color: #666;
                }
            """)
        
        right_column = self._create_right_column()

        content_layout.addLayout(left_column, 1)
        content_layout.addWidget(self.chart_view, 2)
        content_layout.addLayout(right_column, 1)

        main_layout.addLayout(header)
        main_layout.addLayout(content_layout)
        
        self._connect_signals()

    def _create_header(self):
        """Başlık, saat ve yenileme butonunu içeren üst bölümü oluşturur."""
        header_layout = QHBoxLayout()
        title_label = QLabel("Finansal Rapor")
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4B5563;")
        self.refresh_btn = QPushButton("🔄 Verileri Yenile")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.clock_label)
        header_layout.addWidget(self.refresh_btn)
        return header_layout

    def _create_left_column(self):
        """Finansal istatistik kartlarını içeren sol sütunu oluşturur."""
        layout = QVBoxLayout()
        
        # Finansal kartlar
        self.invoiced_card = ClickableStatCard("Bu Ay Kesilen Faturalar")
        self.paid_card = ClickableStatCard("Bu Ayki Tahsilat")
        self.pending_card = ClickableStatCard("Bekleyen Tahsilat (Toplam)")
        
        # Müşteri yönetimi kartları
        customer_group = QGroupBox("Müşteri Yönetimi")
        customer_layout = QGridLayout(customer_group)
        self.total_customers_card = ClickableStatCard("Toplam Müşteri")
        self.contract_customers_card = ClickableStatCard("Sözleşmeli Müşteri")
        self.expiring_contracts_card = ClickableStatCard("Bu Ay Sona Eren Sözleşmeler")
        self.expired_contracts_card = ClickableStatCard("Süresi Dolan Sözleşmeler")
        
        customer_layout.addWidget(self.total_customers_card, 0, 0)
        customer_layout.addWidget(self.contract_customers_card, 0, 1)
        customer_layout.addWidget(self.expiring_contracts_card, 1, 0)
        customer_layout.addWidget(self.expired_contracts_card, 1, 1)
        
        layout.addWidget(self.invoiced_card)
        layout.addWidget(self.paid_card)
        layout.addWidget(self.pending_card)
        layout.addWidget(customer_group)
        layout.addStretch()
        return layout

    def _create_right_column(self):
        """Döviz kurları ve servis durumu kartlarını içeren sağ sütunu oluşturur."""
        layout = QVBoxLayout()
        
        self.currency_card = QGroupBox("Güncel Döviz Kurları")
        currency_layout = QVBoxLayout(self.currency_card)
        self.usd_label = QLabel("USD: Yükleniyor...")
        self.eur_label = QLabel("EUR: Yükleniyor...")
        for label in [self.usd_label, self.eur_label]:
            label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        currency_layout.addWidget(self.usd_label)
        currency_layout.addWidget(self.eur_label)
        
        ops_group = QGroupBox("Anlık Servis Durumu")
        ops_layout = QGridLayout(ops_group)
        self.monthly_new_card = ClickableStatCard("Bu Ay Açılan Servis")
        self.on_repair_card = ClickableStatCard("Onarımda Bekleyen")
        self.awaiting_part_card = ClickableStatCard("parça bekleniyor")
        self.awaiting_approval_card = ClickableStatCard("Müşteri Onayı Bekleyen")
        ops_layout.addWidget(self.monthly_new_card, 0, 0)
        ops_layout.addWidget(self.on_repair_card, 0, 1)
        ops_layout.addWidget(self.awaiting_part_card, 1, 0)
        ops_layout.addWidget(self.awaiting_approval_card, 1, 1)
        
        layout.addWidget(self.currency_card)
        layout.addWidget(ops_group)
        layout.addStretch()
        return layout

    def _connect_signals(self):
        """Sinyalleri slotlara bağlar."""
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.invoiced_card.clicked.connect(self.show_monthly_invoices)
        self.paid_card.clicked.connect(self.show_monthly_payments)
        self.pending_card.clicked.connect(self.show_pending_invoices)
        
        # Müşteri kartları bağlantıları
        self.total_customers_card.clicked.connect(self.show_all_customers)
        self.contract_customers_card.clicked.connect(self.show_contract_customers)
        self.expiring_contracts_card.clicked.connect(self.show_expiring_contracts)
        self.expired_contracts_card.clicked.connect(self.show_expired_contracts)
        
        self.data_changed.connect(self.refresh_data)

    def _start_timers(self):
        """Saat ve periyodik veri yenileme zamanlayıcılarını başlatır."""
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(300000) # 5 dakikada bir yenile

    def update_clock(self):
        """Saat etiketini günceller."""
        try:
            if hasattr(self, 'clock_label') and self.clock_label:
                now = datetime.now().strftime("%d %B %Y, %H:%M:%S")
                self.clock_label.setText(now)
        except Exception as e:
            # Clock güncellemesi hatası - sessizce geç
            pass

    def refresh_data(self):
        """Tüm gösterge paneli verilerini güvenli bir şekilde yeniler."""
        try:
            if not self.db or not self.db.get_connection():
                raise ConnectionError("Veritabanı bağlantısı mevcut değil.")

            # Finansal İstatistikler
            fin_stats = self.db.get_dashboard_financial_stats()
            self.invoiced_card.set_value(f"{fin_stats.get('total_invoiced', 0):,.2f} TL")
            self.invoiced_card.set_subtitle(f"Toplam {fin_stats.get('invoice_count', 0)} adet fatura")
            self.paid_card.set_value(f"{fin_stats.get('total_paid', 0):,.2f} TL")
            self.pending_card.set_value(f"{fin_stats.get('pending_balance', 0):,.2f} TL")
            
            self.chart_view.update_data(fin_stats.get('total_invoiced', 0), fin_stats.get('total_paid', 0)) if CHARTS_AVAILABLE and hasattr(self.chart_view, 'update_data') else None

            # Döviz Kurları (güvenli çekme)
            try:
                rates = get_exchange_rates()
                self.usd_label.setText(f"USD: {rates.get('USD', 'N/A')} TL")
                self.eur_label.setText(f"EUR: {rates.get('EUR', 'N/A')} TL")
            except Exception as e:
                logging.warning(f"Döviz kurları yüklenemedi: {e}")
                self.usd_label.setText("USD: Yüklenemedi")
                self.eur_label.setText("EUR: Yüklenemedi")
            
            # Operasyonel İstatistikler
            ops_stats = self.db.get_dashboard_stats()
            self.monthly_new_card.set_value(ops_stats.get('monthly_new', 0))
            self.on_repair_card.set_value(ops_stats.get('on_repair', 0))
            self.awaiting_part_card.set_value(ops_stats.get('awaiting_part', 0))
            self.awaiting_approval_card.set_value(ops_stats.get('awaiting_approval', 0))
            
            # Müşteri İstatistikleri
            customer_stats = self._get_customer_stats()
            self.total_customers_card.set_value(customer_stats.get('total', 0))
            self.contract_customers_card.set_value(customer_stats.get('contract', 0))
            self.expiring_contracts_card.set_value(customer_stats.get('expiring_this_month', 0))
            self.expired_contracts_card.set_value(customer_stats.get('expired', 0))

        except ConnectionError as e:
            self.usd_label.setText("USD: Bağlantı Hatası")
            self.eur_label.setText("EUR: Bağlantı Hatası")
            QMessageBox.warning(self, "Bağlantı Hatası", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Veri Yenileme Hatası", f"Gösterge paneli verileri yenilenirken bir hata oluştu: {e}")

    def _get_customer_stats(self):
        """Müşteri istatistiklerini hesaplar."""
        try:
            from datetime import datetime
            
            # Toplam müşteri
            total = self.db.fetch_one("SELECT COUNT(*) FROM customers")[0]
            
            # Sözleşmeli müşteri
            contract = self.db.fetch_one("SELECT COUNT(*) FROM customers WHERE is_contract = 1")[0]
            
            # Bu ay sona erecek sözleşmeler
            current_year_month = datetime.now().strftime("%Y-%m")
            expiring_this_month = self.db.fetch_one(
                "SELECT COUNT(*) FROM customers WHERE is_contract = 1 AND contract_end_date LIKE ?",
                (f"{current_year_month}%",)
            )[0]
            
            # Süresi dolan sözleşmeler
            current_date = datetime.now().strftime("%Y-%m-%d")
            expired = self.db.fetch_one(
                "SELECT COUNT(*) FROM customers WHERE is_contract = 1 AND contract_end_date < ?",
                (current_date,)
            )[0]
            
            return {
                'total': total,
                'contract': contract,
                'expiring_this_month': expiring_this_month,
                'expired': expired
            }
        except Exception as e:
            logger.error(f"Müşteri istatistikleri hesaplanırken hata: {e}")
            return {'total': 0, 'contract': 0, 'expiring_this_month': 0, 'expired': 0}

    def show_monthly_invoices(self):
        """Bu ay kesilen faturalar için bir rapor diyalogu gösterir."""
        try:
            invoices = self.db.get_invoices_for_current_month()
            if not invoices:
                QMessageBox.information(self, "Bilgi", "Bu ay için kesilmiş fatura bulunmamaktadır.")
                return
            
            # Güncel kurları al
            rates = get_exchange_rates()
            
            headers = ["Fatura ID", "Tarih", "Müşteri", "Fatura Tipi", "Orijinal Tutar", "TL Karşılığı (+KDV)", "Durum"]
            
            # Güvenli format string - None ve string değerleri kontrol et
            def safe_format_amount(amount):
                try:
                    if amount is None:
                        return "0.00"
                    if isinstance(amount, str):
                        amount = float(amount)
                    return f"{float(amount):,.2f}"
                except (ValueError, TypeError):
                    return "0.00"
            
            def convert_to_tl_with_tax(amount, currency, saved_rate):
                """Tutarı TL'ye çevirir ve %20 KDV ekler. Kaydedilmiş kur varsa onu kullanır."""
                try:
                    amount_val = float(amount) if amount else 0.0
                    if currency and currency != 'TL':
                        # Önce kaydedilmiş kura bak
                        if saved_rate and saved_rate > 0:
                            rate = float(saved_rate)
                        else:
                            # Yoksa güncel kuru kullan
                            rate = float(rates.get(currency, 1.0))
                        amount_tl = amount_val * rate
                    else:
                        amount_tl = amount_val
                    # %20 KDV ekle
                    amount_with_tax = amount_tl * 1.20
                    return f"{amount_with_tax:,.2f} TL"
                except:
                    return "0.00 TL"
            
            report_data = [[
                invoice['id'], 
                invoice['invoice_date'], 
                invoice['name'], 
                invoice['invoice_type'], 
                f"{safe_format_amount(invoice['total_amount'])} {invoice['currency']}", 
                convert_to_tl_with_tax(invoice['total_amount'], invoice['currency'], invoice.get('exchange_rate')),
                invoice['status']
            ] for invoice in invoices]
            
            dialog = MonthlyReportDialog("Bu Ay Kesilen Faturalar Raporu", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Aylık fatura raporu oluşturulurken bir hata oluştu: {e}")

    def show_monthly_payments(self):
        """Bu ayki tahsilatlar için bir rapor diyalogu gösterir."""
        try:
            payments = self.db.get_payments_for_current_month()
            if not payments:
                QMessageBox.information(self, "Bilgi", "Bu ay için yapılmış tahsilat bulunmamaktadır.")
                return
            headers = ["Ödeme Tarihi", "Müşteri", "İlgili Fatura No", "Tutar", "Para Birimi", "Yöntem"]
            
            # Güvenli format string - None ve string değerleri kontrol et
            def safe_format_amount(amount):
                try:
                    if amount is None:
                        return "0.00"
                    if isinstance(amount, str):
                        amount = float(amount)
                    return f"{float(amount):,.2f}"
                except (ValueError, TypeError):
                    return "0.00"
            
            report_data = [[payment['payment_date'], payment['name'], payment['invoice_id'], 
                           safe_format_amount(payment['amount_paid']), payment['currency'], payment['payment_method']]
                           for payment in payments]
            dialog = MonthlyReportDialog("Bu Ayki Tahsilatlar Raporu", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Aylık tahsilat raporu oluşturulurken bir hata oluştu: {e}")

    def show_all_customers(self):
        """Tüm müşterileri gösterir."""
        try:
            customers = self.db.fetch_all("SELECT id, name, phone, email, CASE WHEN is_contract = 1 THEN 'Sözleşmeli' ELSE 'Ücretli' END FROM customers ORDER BY name")
            if not customers:
                QMessageBox.information(self, "Bilgi", "Kayıtlı müşteri bulunmamaktadır.")
                return
            headers = ["ID", "Müşteri Adı", "Telefon", "E-posta", "Durum"]
            report_data = [[str(cid), name, phone or "-", email or "-", status] for cid, name, phone, email, status in customers]
            dialog = MonthlyReportDialog("Tüm Müşteriler Listesi", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Müşteri listesi oluşturulurken bir hata oluştu: {e}")

    def show_contract_customers(self):
        """Sözleşmeli müşterileri gösterir."""
        try:
            customers = self.db.fetch_all(
                "SELECT id, name, phone, contract_start_date, contract_end_date FROM customers WHERE is_contract = 1 ORDER BY name"
            )
            if not customers:
                QMessageBox.information(self, "Bilgi", "Sözleşmeli müşteri bulunmamaktadır.")
                return
            headers = ["ID", "Müşteri Adı", "Telefon", "Başlangıç", "Bitiş"]
            report_data = [[str(cid), name, phone or "-", start or "-", end or "-"] for cid, name, phone, start, end in customers]
            dialog = MonthlyReportDialog("Sözleşmeli Müşteriler Listesi", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Sözleşmeli müşteri listesi oluşturulurken bir hata oluştu: {e}")

    def show_expiring_contracts(self):
        """Bu ay sona erecek sözleşmeleri gösterir."""
        try:
            from datetime import datetime
            current_year_month = datetime.now().strftime("%Y-%m")
            customers = self.db.fetch_all(
                "SELECT id, name, phone, contract_end_date FROM customers WHERE is_contract = 1 AND contract_end_date LIKE ? ORDER BY contract_end_date",
                (f"{current_year_month}%",)
            )
            if not customers:
                QMessageBox.information(self, "Bilgi", "Bu ay sona erecek sözleşme bulunmamaktadır.")
                return
            headers = ["ID", "Müşteri Adı", "Telefon", "Sözleşme Bitiş"]
            report_data = [[str(cid), name, phone or "-", end] for cid, name, phone, end in customers]
            dialog = MonthlyReportDialog("Bu Ay Sona Erecek Sözleşmeler", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Sona erecek sözleşmeler listesi oluşturulurken bir hata oluştu: {e}")

    def show_expired_contracts(self):
        """Süresi dolan sözleşmeleri gösterir."""
        try:
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            customers = self.db.fetch_all(
                "SELECT id, name, phone, contract_end_date FROM customers WHERE is_contract = 1 AND contract_end_date < ? ORDER BY contract_end_date DESC",
                (current_date,)
            )
            if not customers:
                QMessageBox.information(self, "Bilgi", "Süresi dolan sözleşme bulunmamaktadır.")
                return
            headers = ["ID", "Müşteri Adı", "Telefon", "Sözleşme Bitiş"]
            report_data = [[str(cid), name, phone or "-", end] for cid, name, phone, end in customers]
            dialog = MonthlyReportDialog("Süresi Dolan Sözleşmeler", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Süresi dolan sözleşmeler listesi oluşturulurken bir hata oluştu: {e}")
        
    def show_pending_invoices(self):
        """Tüm zamanların ödenmemiş faturalarını listeleyen bir rapor diyalogu gösterir."""
        try:
            pending = self.db.get_pending_invoices()
            if not pending:
                QMessageBox.information(self, "Bilgi", "Ödenmemiş fatura bulunmamaktadır.")
                return

            headers = ["Fatura ID", "Tarih", "Müşteri", "Toplam Tutar", "Ödenen", "Kalan Bakiye", "Para Birimi"]
            
            # Güvenli format string - None ve string değerleri kontrol et
            def safe_format_amount(amount):
                try:
                    if amount is None:
                        return "0.00"
                    if isinstance(amount, str):
                        amount = float(amount)
                    return f"{float(amount):,.2f}"
                except (ValueError, TypeError):
                    return "0.00"
            
            report_data = [[pending_invoice['id'], pending_invoice['invoice_date'], pending_invoice['name'], 
                           safe_format_amount(pending_invoice['total_amount']), 
                           safe_format_amount(pending_invoice['paid_amount']), 
                           safe_format_amount(pending_invoice['balance']), pending_invoice['currency']]
                           for pending_invoice in pending]
            
            dialog = MonthlyReportDialog("Bekleyen Tahsilatlar Raporu", headers, report_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Bekleyen tahsilatlar raporu oluşturulurken bir hata oluştu: {e}")

    def cleanup(self):
        """Dashboard kapatılırken timer'ları temizler."""
        try:
            if hasattr(self, 'clock_timer') and self.clock_timer:
                self.clock_timer.stop()
                self.clock_timer.deleteLater()
                self.clock_timer = None
            
            if hasattr(self, 'refresh_timer') and self.refresh_timer:
                self.refresh_timer.stop()
                self.refresh_timer.deleteLater()
                self.refresh_timer = None
        except Exception:
            pass  # Cleanup hatalarını sessizce geç

    def closeEvent(self, event):
        """Dashboard kapatılırken cleanup işlemlerini yapar."""
        self.cleanup()
        super().closeEvent(event)
