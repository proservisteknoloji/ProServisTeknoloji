# ui/main_window.py

import os
import logging
import traceback
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QLabel, QStatusBar, QMessageBox, QHeaderView, QTableWidget, QTableWidgetItem,
                             QSplitter, QGroupBox, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from PyQt6.QtGui import QPixmap, QIcon

from utils.database import db_manager
from ui.dashboard_tab import DashboardTab
from ui.customer_tab import CustomerDeviceTab
from ui.service_tab import ServiceTab
from ui.billing_tab import BillingTab
from ui.stock_tab import StockTab
from ui.invoicing_tab import InvoicingTab
from ui.cpc_tab import CPCTab
from ui.ai_assistant_tab import AIAssistantTab
from ui.settings_tab import SettingsTab
from utils.workers import (PANDAS_AVAILABLE, OPENAI_AVAILABLE, GEMINI_AVAILABLE, 
                             CurrencyRateThread)

class MainWindow(QMainWindow):
    """Ana uygulama penceresi."""
    def __init__(self, db_manager, logged_in_user: str, logged_in_role: str, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.logged_in_user = logged_in_user
        self.logged_in_role = logged_in_role
        
        # Current user bilgisini dictionary olarak oluştur
        self.current_user = {
            'username': logged_in_user,
            'role': logged_in_role,
            'is_admin': logged_in_role.lower() in ['admin', 'superadmin'] or logged_in_user.lower() == 'admin'
        }
        
        # Root kullanıcısı için özel yetki kontrolü
        self.is_super_admin = (logged_in_user == 'root' and logged_in_role == 'SuperAdmin')
        
        # Pencere başlığında root kullanıcısını gizle
        display_user = self.logged_in_user if not self.is_super_admin else "System Administrator"
        display_role = self.logged_in_role if not self.is_super_admin else "Admin"
        
        self.setWindowTitle(f"ProServis Yönetim Sistemi - Kullanıcı: {display_user} ({display_role})")
        self.setWindowIcon(QIcon("ProServis.ico"))
        
        # Başlangıç boyutu daha küçük (laptop dostu)
        self.resize(1024, 700)
        # Minimum boyut daha esnek
        self.setMinimumSize(800, 600)
        # Maksimum boyut sınırlaması tamamen kaldırıldı - tam ekran için
        
        # Pencereyi ekranın merkezine taşı (görünürlük sorunu için)
        self.center_window()
        
        # Pencereyi yeniden boyutlandırılabilir yap ve maximize özelliğini aktif et
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowType.WindowMaximizeButtonHint | 
            Qt.WindowType.WindowMinimizeButtonHint
        )
        
        # Farklı çözünürlükler için optimal boyut ayarla
        self.setup_screen_size()
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # FIXED: Add parent to prevent memory leak
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        
        self.init_ui()

        if self.db and self.db.get_connection():
            self.update_header()
            self.check_optional_dependencies()
            self.apply_role_permissions()
            self.start_background_tasks()
        else:
            self.enable_offline_mode()

        # Sürpriz yumurta: Space Invaders kısayolu
        self._setup_easter_egg_shortcut()

    def center_window(self):
        """Pencereyi ekranın merkezine yerleştirir"""
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                x = (screen_geometry.width() - self.width()) // 2
                y = (screen_geometry.height() - self.height()) // 2
                self.move(x, y)
        except Exception as e:
            logging.warning(f"Pencere merkezleme hatası: {e}")

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        main_layout = QVBoxLayout(self.main_widget)
        
        header_layout = self._create_header()
        self.tabs = self._create_tabs()
        
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.tabs)
        
        self._connect_signals()

    def setup_screen_size(self):
        """Ekran çözünürlüğüne göre pencere boyutunu optimize eder."""
        try:
            from PyQt6.QtWidgets import QApplication
            
            # Mevcut ekran geometrisini al
            screen = QApplication.primaryScreen()
            if screen is None:
                # Ekran bilgisi alınamazsa varsayılan boyutları kullan
                self.resize(1024, 700)
                self.setMinimumSize(800, 600)
                return
                
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            
            # Farklı çözünürlükler için optimal boyutlar
            # Tüm sekmelerin görünmesi için daha geniş başlangıç boyutu
            if screen_width >= 1920:  # Full HD ve üstü
                optimal_width = 1600
                optimal_height = 950
                min_width = 1200
                min_height = 800
            elif screen_width >= 1366:  # Laptop standart
                optimal_width = 1350
                optimal_height = 800
                min_width = 1100
                min_height = 700
            elif screen_width >= 1024:  # Küçük laptop/tablet
                optimal_width = 1000
                optimal_height = 700
                min_width = 950
                min_height = 650
            else:  # Çok küçük ekranlar
                optimal_width = min(screen_width - 50, 950)
                optimal_height = min(screen_height - 50, 650)
                min_width = 900
                min_height = 600
            
            # Pencere boyutlarını ayarla
            self.resize(optimal_width, optimal_height)
            self.setMinimumSize(min_width, min_height)
            
            # Maksimum boyut sınırlaması yok - tam ekran için serbest bırak
            # self.setMaximumSize() kullanılmıyor
            
            # Pencereyi ekranın ortasına yerleştir
            self.center_on_screen(screen_geometry)
            
        except Exception as e:
            # FIXED: Add try-catch for Type conversion
            try:
                print(f"Ekran boyutu ayarlanırken hata: {e}")
            except Exception as e:
                print(f'Error in Type conversion: {e}')
            # Varsayılan boyutlara geri dön
            self.resize(1024, 700)
            self.setMinimumSize(800, 600)
            # Maksimum boyut sınırlaması kaldırıldı - tam ekran için

    def center_on_screen(self, screen_geometry):
        """Pencereyi ekranın ortasına yerleştirir."""
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def _create_header(self):
        """Şirket logosu ve adını içeren başlık bölümünü oluşturur."""
        header_layout = QHBoxLayout()
        self.logo_label = QLabel()
        
        # Responsive logo boyutu - ekran boyutuna göre ayarla
        window_width = self.width()
        if window_width < 900:
            logo_width, logo_height = 100, 35
            font_size = "14pt"
        elif window_width < 1200:
            logo_width, logo_height = 120, 40
            font_size = "15pt"
        else:
            logo_width, logo_height = 150, 50
            font_size = "16pt"
            
        self.logo_label.setFixedSize(logo_width, logo_height)
        self.logo_label.setScaledContents(True)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.header_label = QLabel("ProServis")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setStyleSheet(f"font-size: {font_size}; font-weight: bold; color: #1E40AF;")
        
        header_layout.addWidget(self.logo_label)
        header_layout.addStretch()
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        # Sağa dayalı boş bir widget ekleyerek ortalamayı iyileştir
        # FIXED: Add parent to prevent memory leak
        header_layout.addWidget(QWidget(self), 1) 
        
        return header_layout

    def _create_tabs(self):
        """Uygulama sekmelerini oluşturur ve QTabWidget içine yerleştirir."""
        try:
            logging.info("Sekmeler oluşturuluyor...")
            tabs = QTabWidget()
            
            logging.info("Dashboard sekmesi oluşturuluyor...")
            self.dashboard_tab = DashboardTab(self.db, self)
            
            logging.info("Service sekmesi oluşturuluyor...")
            self.service_tab = ServiceTab(self.db, self.status_bar, self)
            
            logging.info("Stock sekmesi oluşturuluyor...")
            self.stock_tab = StockTab(self.db, self.current_user, self)
            
            logging.info("Billing sekmesi oluşturuluyor...")
            self.billing_tab = BillingTab(self.db, self)
            
            logging.info("Invoicing sekmesi oluşturuluyor...")
            self.invoicing_tab = InvoicingTab(self.db, self)
            
            logging.info("CPC sekmesi oluşturuluyor...")
            self.cpc_tab = CPCTab(self.db, self.status_bar, user_role=self.logged_in_role, parent=self)
            
            logging.info("AI Asistan sekmesi oluşturuluyor...")
            self.ai_tab = AIAssistantTab(self.db, self)
            
            logging.info("Settings sekmesi oluşturuluyor...")
            self.settings_tab = SettingsTab(self.status_bar, self)

            logging.info("Customer sekmesi oluşturuluyor...")
            self.customer_tab = CustomerDeviceTab(self.db, self.status_bar, user_role=self.logged_in_role, parent=self)
            
            # Sekmeleri tab widget'ına ekle
            tabs.addTab(self.dashboard_tab, "📊 Dashboard")
            tabs.addTab(self.customer_tab, "👥 Müşteri Yönetimi")
            tabs.addTab(self.service_tab, "🔧 Servis")
            tabs.addTab(self.cpc_tab, "📊 CPC Sipariş")
            tabs.addTab(self.stock_tab, "📦 Stok & Satış")
            tabs.addTab(self.billing_tab, "💰 Sayaç Faturalandır")
            tabs.addTab(self.invoicing_tab, "� Faturalar")
            tabs.addTab(self.ai_tab, "🤖 AI Asistan")
            tabs.addTab(self.settings_tab, "⚙️ Ayarlar")
            
            return tabs
            
        except Exception as e:
            logging.error(f"❌ Sekme oluşturma hatası: {e}")
            logging.error(f"Detay: {traceback.format_exc()}")
            
            # Hata durumunda boş tab widget döndür
            fallback_tabs = QTabWidget()
            # FIXED: Add parent to prevent memory leak
            error_widget = QWidget(self)
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"❌ Sekmeler yüklenemedi:\\n{str(e)}")
            error_label.setStyleSheet("color: red; padding: 20px; font-size: 14px;")
            error_layout.addWidget(error_widget)
            fallback_tabs.addTab(error_widget, "❌ Hata")
            return fallback_tabs

    def _connect_signals(self):
        """Sekmeler arası veri tutarlılığı için sinyal-slot bağlantılarını kurar."""
        if not hasattr(self, 'tabs') or self.tabs is None:
            return
            
        self.tabs.currentChanged.connect(self.on_tab_changed)
        if hasattr(self, 'settings_tab'):
            self.settings_tab.settings_saved.connect(self.update_header)
        
        # Bir sekmede veri değiştiğinde, diğer ilgili sekmelerin yenilenmesi
        if hasattr(self, 'service_tab') and self.service_tab:
            # Customer tab'ından service sekmesine bağlantı yok
            pass
        if hasattr(self, 'billing_tab') and self.billing_tab:
            pass
        if hasattr(self, 'invoicing_tab') and self.invoicing_tab:
            pass
        if hasattr(self, 'cpc_tab') and self.cpc_tab:
            pass

        if hasattr(self, 'stock_tab') and hasattr(self, 'service_tab') and self.stock_tab and self.service_tab:
            self.stock_tab.data_changed.connect(self.service_tab.refresh_data)
        if hasattr(self, 'stock_tab') and hasattr(self, 'dashboard_tab') and self.stock_tab and self.dashboard_tab:
            self.stock_tab.data_changed.connect(self.dashboard_tab.refresh_data)
        if hasattr(self, 'stock_tab') and hasattr(self, 'cpc_tab') and self.stock_tab and self.cpc_tab:
            self.stock_tab.data_changed.connect(self.cpc_tab.refresh_cpc_customers)
        
        if hasattr(self, 'service_tab') and hasattr(self, 'invoicing_tab') and self.service_tab and self.invoicing_tab:
            self.service_tab.data_changed.connect(self.invoicing_tab.refresh_data)
        if hasattr(self, 'service_tab') and hasattr(self, 'dashboard_tab') and self.service_tab and self.dashboard_tab:
            self.service_tab.data_changed.connect(self.dashboard_tab.refresh_data)

        if hasattr(self, 'billing_tab') and hasattr(self, 'invoicing_tab') and self.billing_tab and self.invoicing_tab:
            self.billing_tab.data_changed.connect(self.invoicing_tab.refresh_data)
        if hasattr(self, 'billing_tab') and hasattr(self, 'dashboard_tab') and self.billing_tab and self.dashboard_tab:
            self.billing_tab.data_changed.connect(self.dashboard_tab.refresh_data)

        if hasattr(self, 'invoicing_tab') and hasattr(self, 'dashboard_tab') and self.invoicing_tab and self.dashboard_tab:
            self.invoicing_tab.data_changed.connect(self.dashboard_tab.refresh_data)
        
        if hasattr(self, 'cpc_tab') and hasattr(self, 'stock_tab') and self.cpc_tab and self.stock_tab:
            self.cpc_tab.data_changed.connect(self.stock_tab.refresh_data)
        if hasattr(self, 'cpc_tab') and hasattr(self, 'dashboard_tab') and self.cpc_tab and self.dashboard_tab:
            self.cpc_tab.data_changed.connect(self.dashboard_tab.refresh_data)

    def start_background_tasks(self):
        """Uygulama başlangıcında çalışacak arka plan görevlerini başlatır."""
        self.currency_thread = CurrencyRateThread(self.db)
        self.currency_thread.task_finished.connect(self.on_currency_rates_updated)
        self.currency_thread.task_error.connect(self.on_currency_rates_error)
        self.currency_thread.start()
        self.status_bar.showMessage("Döviz kurları güncelleniyor...", 3000)

    def on_currency_rates_updated(self, rates):
        """Döviz kurları başarıyla güncellendiğinde tetiklenir."""
        self.status_bar.showMessage(f"Kurlar güncellendi: USD={rates.get('USD', 'N/A')}, EUR={rates.get('EUR', 'N/A')}", 10000)
        # Dashboard gibi kurları kullanan sekmeleri yenile
        if hasattr(self, 'dashboard_tab') and self.dashboard_tab.isVisible():
            self.dashboard_tab.refresh_data()

    def on_currency_rates_error(self, error_message):
        """Döviz kurları alınırken hata oluştuğunda tetiklenir."""
        self.status_bar.showMessage(f"Döviz kuru hatası: {error_message}", 15000)

    def apply_role_permissions(self):
        """Kullanıcı rolüne göre sekmelere erişimi kısıtlar."""
        role = self.logged_in_role.lower()
        
        # Rol bazlı erişim haritası
        # Hangi rolün hangi sekmelere erişebileceğini tanımlar
        role_permissions = {
            "admin": ["all"],
            "superadmin": ["all"],  # Root kullanıcısı için
            "ofis personeli": [
                getattr(self, 'dashboard_tab', None), getattr(self, 'customer_tab', None), getattr(self, 'service_tab', None),
                getattr(self, 'stock_tab', None), getattr(self, 'billing_tab', None), getattr(self, 'invoicing_tab', None), getattr(self, 'ai_tab', None)
            ],
            "teknisyen": [getattr(self, 'customer_tab', None), getattr(self, 'service_tab', None)]
        }

        allowed_tabs = role_permissions.get(role, [])
        # None değerleri filtrele
        allowed_tabs = [tab for tab in allowed_tabs if tab is not None]

        if "all" in allowed_tabs:
            logging.info(f"Kullanıcı '{self.logged_in_user}' ({self.logged_in_role}) tam yetkiye sahip - tüm sekmeler görünür")
            return # Admin/SuperAdmin tüm sekmeleri görür

        logging.info(f"Rol '{role}' için {len(allowed_tabs)} sekme izni veriliyor")

        # Sekmeleri ters sırada kontrol ederek silme
        if hasattr(self, 'tabs') and self.tabs is not None:
            for i in range(self.tabs.count() - 1, -1, -1):
                tab = self.tabs.widget(i)
                if tab not in allowed_tabs:
                    self.tabs.removeTab(i)
        
        # Teknisyen rolü için özel modları ayarla
        if role == "teknisyen":
            try:
                user_id_tuple = self.db.fetch_one("SELECT id FROM users WHERE username = ?", (self.logged_in_user,))
                if user_id_tuple:
                    user_id = user_id_tuple[0]
                    # Teknisyen modu için gerekli ayarlamalar yapılabilir
                    pass
            except Exception as e:
                QMessageBox.critical(self, "Yetki Hatası", f"Teknisyen modu ayarlanırken bir hata oluştu: {e}")
    
    def on_tab_changed(self, index: int):
        """Kullanıcı sekme değiştirdiğinde mevcut sekmenin verilerini yeniler."""
        if not hasattr(self, 'tabs') or self.tabs is None:
            return
            
        current_widget = self.tabs.widget(index)
        if current_widget and hasattr(current_widget, 'refresh_data'):
            try:
                current_widget.refresh_data()  # type: ignore
            except Exception as e:
                QMessageBox.warning(self, "Veri Yenileme Hatası",
                                    f"'{self.tabs.tabText(index)}' sekmesi yenilenirken bir hata oluştu:\n{e}")

    def update_header(self):
        """Veritabanından şirket adını ve logosunu alarak başlığı günceller."""
        try:
            if not self.db or not self.db.get_connection(): return
            
            # 🔐 MULTI-TENANT: Session'dan firma adını al
            from utils.session_manager import get_session_manager
            session_manager = get_session_manager()
            
            if session_manager.has_session():
                company_name = session_manager.get_company_name() or 'Test Company'
                # Multi-tenant modda logo gösterme (her firma için ayrı logo yönetimi TODO)
                self.logo_label.clear()
            else:
                # Session yoksa fallback
                company_name = self.db.get_setting('company_name', 'Firma Adı Belirtilmemiş')
                
                # Logo yükle (tek kullanıcılı mod)
                logo_path = self.db.get_setting('company_logo_path')
                if logo_path and os.path.exists(logo_path):
                    pixmap = QPixmap(logo_path)
                    self.logo_label.setPixmap(pixmap)
                else: 
                    self.logo_label.clear()
            
            self.header_label.setText(company_name)
        except Exception as e:
            self.logo_label.clear()
            self.header_label.setText("ProServis")
            QMessageBox.warning(self, "Başlık Güncelleme Hatası", f"Firma bilgileri yüklenirken bir hata oluştu: {e}")

    def check_optional_dependencies(self):
        """İsteğe bağlı kütüphanelerin durumunu kontrol eder ve kullanıcıyı bilgilendirir."""
        if not PANDAS_AVAILABLE:
            self.status_bar.showMessage("Excel aktarımı için 'pandas' ve 'openpyxl' kütüphaneleri gerekli.", 10000)
        
        ai_library_missing = False
        if not OPENAI_AVAILABLE and not GEMINI_AVAILABLE:
            ai_library_missing = True
        elif self.db.get_setting('ai_provider') == 'OpenAI' and not OPENAI_AVAILABLE:
            ai_library_missing = True
        elif self.db.get_setting('ai_provider') == 'Google Gemini' and not GEMINI_AVAILABLE:
            ai_library_missing = True
            
        if ai_library_missing:
            self.status_bar.showMessage("Yapay Zeka özellikleri için ilgili kütüphaneler eksik.", 10000)


        
    def enable_offline_mode(self):
        """Veritabanı bağlantısı olmadığında çevrimdışı modu etkinleştirir."""
        if not hasattr(self, 'tabs') or self.tabs is None:
            return
            
        self.status_bar.showMessage("Veritabanı bağlantısı yok. Sadece Ayarlar sekmesi aktif.")
        for i in range(self.tabs.count()):
            # settings_tab varsa kontrol et, yoksa Ayarlar sekmesi dışındaki tüm sekmeleri devre dışı bırak
            if hasattr(self, 'settings_tab') and self.tabs.widget(i) is not self.settings_tab:
                self.tabs.setTabEnabled(i, False)
            elif not hasattr(self, 'settings_tab') and "Ayarlar" not in self.tabs.tabText(i):
                self.tabs.setTabEnabled(i, False)

    def closeEvent(self, a0):
        """Uygulama kapatılırken yapılacak işlemler"""
        try:
            # Oturum bilgilerini temizle
            pass  # Session manager kaldırıldı
        except Exception as e:
            print(f"Session cleanup error: {e}")
        super().closeEvent(a0)

    def switch_to_billing_tab(self):
        """Billing sekmesine geçiş yapar ve seçili müşteriyi güncel tutar."""
        if not hasattr(self, 'tabs') or self.tabs is None:
            return
            
        try:
            # Customer sekmesinde seçili müşteriyi al
            current_customer_id = None
            # Customer tab'ında seçili müşteri bilgisini almak için customer_tab'ı kontrol et
            # TODO: CustomerDeviceTab'a get_selected_customer_id metodu eklenebilir
            
            # Billing sekmesinin indeksini bul
            for i in range(self.tabs.count()):
                if self.tabs.widget(i) is self.billing_tab:
                    self.tabs.setCurrentIndex(i)
                    
                    # Billing sekmesini refresh et
                    if hasattr(self.billing_tab, 'refresh_data'):
                        self.billing_tab.refresh_data()
                    
                    # Eğer customer sekmesinde bir müşteri seçiliyse, onu billing sekmesinde de seç
                    if current_customer_id:
                        idx = self.billing_tab.customer_combo.findData(current_customer_id)
                        if idx > -1:
                            self.billing_tab.customer_combo.setCurrentIndex(idx)
                            self.billing_tab.populate_devices_for_customer()
                            self.status_bar.showMessage(f"Billing sekmesine geçildi - müşteri seçildi ve hazır", 3000)
                        else:
                            self.status_bar.showMessage("Billing sekmesine geçildi - müşteri listesinde CPC cihazı yok", 3000)
                    else:
                        self.status_bar.showMessage("Billing sekmesine geçildi - sayaç okuma için hazır", 3000)
                    break
        except Exception as e:
            print(f"Billing sekmesine geçiş hatası: {e}")
            self.status_bar.showMessage("Billing sekmesine geçiş sırasında hata oluştu", 3000)

    def _setup_easter_egg_shortcut(self):
        from PyQt6.QtGui import QShortcut, QKeySequence
        # Kısayol: Ctrl+Alt+Shift+S
        shortcut = QShortcut(QKeySequence('Ctrl+Alt+Shift+S'), self)
        shortcut.activated.connect(self._launch_space_invaders)

    def _launch_space_invaders(self):
        import subprocess
        import sys
        import os
        game_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Space Invaders Game', 'spaceinvador.py')
        python_exe = sys.executable
        try:
            subprocess.run([python_exe, game_path], check=True)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Space Invaders Hatası", f"Oyun başlatılamadı: {e}")
