"""
Uygulama genelindeki yapılandırma ayarlarını ve sabitleri içerir.

Bu modül, veritabanı adı, uygulama adı, sürüm numarası ve arayüz için
kullanılan stil şablonu (stylesheet) gibi statik verileri barındırır.
"""

# --- Veritabanı Ayarları ---
# Proje, yerel bir SQLite veritabanı ile çalışır.
DB_NAME: str = "teknik_servis_local.db"

# --- Uygulama Ayarları ---
APP_NAME: str = "ProServis - Teknik Servis Yönetim Sistemi"
APP_VERSION: str = "2.3.0"  # Yeni sürüm - Docker desteği, geliştirilmiş kurulum sihirbazı

# --- Arayüz Stil Şablonu (Stylesheet) ---
# Modern bir görünüm için Tailwind CSS renk paletinden esinlenilmiş stil şablonu.
# PyQt6 ile tam uyumludur.
STYLESHEET: str = """
QWidget {
    background-color: #F3F4F6; /* gray-100 */
    color: #1F2937; /* gray-800 */
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow, QDialog {
    background-color: #F3F4F6; /* gray-100 */
}
QTabWidget::pane {
    border: 1px solid #D1D5DB; /* gray-300 */
    border-radius: 6px;
    background-color: #FFFFFF; /* white */
}
QTabBar::tab {
    background: #E5E7EB; /* gray-200 */
    color: #4B5563; /* gray-600 */
    padding: 10px 22px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #D1D5DB; /* gray-300 */
    border-bottom: none;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #FFFFFF; /* white */
    color: #1E40AF; /* blue-800 */
    font-weight: bold;
}
QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #FFFFFF; /* white */
    border: 1px solid #D1D5DB; /* gray-300 */
    gridline-color: #E5E7EB; /* gray-200 */
}
QTableWidget::item:selected, QTableView::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #F3F4F6; /* Hafif gri arka plan */
    color: #1F2937; /* Normal yazı rengi */
    border: 2px solid #3B82F6; /* Mavi border - Belirgin seçim */
}
QTableWidget::item:focus, QTableView::item:focus, QListWidget::item:focus, QTreeWidget::item:focus {
    background-color: #F3F4F6; /* Hafif gri arka plan */
    border: 2px solid #3B82F6; /* Mavi border */
    outline: none;
}
QHeaderView::section {
    background-color: #F9FAFB; /* gray-50 */
    color: #374151; /* gray-700 */
    padding: 6px;
    border: 1px solid #D1D5DB; /* gray-300 */
    font-weight: bold;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background-color: #FFFFFF; /* white */
    border: 1px solid #D1D5DB; /* gray-300 */
    padding: 6px;
    border-radius: 4px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
    border: 2px solid #3B82F6; /* blue-500 */
}
QPushButton {
    background-color: #3B82F6; /* blue-500 */
    color: white;
    border: none;
    padding: 8px 18px;
    border-radius: 5px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2563EB; /* blue-600 */
}
QPushButton:pressed {
    background-color: #1D4ED8; /* blue-700 */
}
QPushButton:disabled {
    background-color: #9CA3AF; /* gray-400 */
    color: #E5E7EB; /* gray-200 */
}
QStatusBar {
    background-color: #E5E7EB; /* gray-200 */
    color: #4B5563; /* gray-600 */
}
QGroupBox {
    border: 1px solid #D1D5DB; /* gray-300 */
    border-radius: 6px;
    margin-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    background-color: #F3F4F6; /* gray-100 */
}
"""