"""
ProServis Azure SQL Setup Helper
Azure SQL bağlantısı için gerekli ODBC driver kontrolü ve kurulum yardımcısı
"""

import pyodbc
import logging
import webbrowser

logger = logging.getLogger(__name__)


def check_odbc_driver():
    """
    Sistem ODBC driver'larını kontrol et
    
    Returns:
        tuple: (has_modern_driver: bool, drivers: list)
    """
    # Azure entegrasyonu askıya alındı
    return (False, [])


def get_download_url():
    """ODBC Driver 18 indirme URL'i"""
    # Azure entegrasyonu askıya alındı
    return "https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server"


def open_download_page():
    """ODBC Driver indirme sayfasını aç"""
    # Azure entegrasyonu askıya alındı
    try:
        webbrowser.open(get_download_url())
    except Exception:
        logger.exception("ODBC download page could not be opened")


def get_connection_string_template(driver_name='ODBC Driver 17 for SQL Server'):
    """
    Connection string template
    
    Args:
        driver_name: ODBC driver adı
        
    Returns:
        Connection string template
    """
    # Azure entegrasyonu askıya alındı
    return (
        f"DRIVER={{{driver_name}}};\n"
        "SERVER=proservis.database.windows.net,1433;\n"
        "DATABASE=Proservis-Database;\n"
        "UID=<kullanici_adi>;\n"
        "PWD=<sifre>;\n"
        "Encrypt=yes;\n"
        "TrustServerCertificate=no;\n"
        "Connection Timeout=30;"
    )


def show_setup_instructions():
    """Kurulum talimatlarını göster"""
    print("\n" + "="*70)
    print("🔧 AZURE SQL ODBC DRIVER KURULUMU")
    print("="*70)
    
    has_driver, drivers = check_odbc_driver()
    
    if has_driver:
        print("\n✅ Modern ODBC Driver bulundu!")
        print("   Azure SQL bağlantısı yapılabilir.")
    else:
        print("\n⚠️ Modern ODBC Driver bulunamadı!")
        print("\n📥 Kurulum Adımları:")
        print("1. Microsoft ODBC Driver 18 for SQL Server'ı indirin")
        print(f"   URL: {get_download_url()}")
        print("2. İndirilen .msi dosyasını çalıştırın")
        print("3. Kurulum tamamlandıktan sonra sistemi yeniden başlatın")
        print("4. ProServis'i tekrar çalıştırın")
        
        print("\n🌐 İndirme sayfasını açmak ister misiniz? (E/H): ", end='')
        choice = input().strip().upper()
        
        if choice == 'E':
            open_download_page()
            print("✅ Tarayıcıda açıldı")
    
    print("\n" + "="*70)
    print("📋 Mevcut ODBC Driver'lar:")
    print("="*70)
    for driver in drivers:
        marker = "✅" if any(x in driver for x in ['17', '18', '13']) else "  "
        print(f"{marker} {driver}")
    
    print("\n" + "="*70)
    print("🔗 Connection String Template:")
    print("="*70)
    print(get_connection_string_template())
    print("="*70 + "\n")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    show_setup_instructions()
