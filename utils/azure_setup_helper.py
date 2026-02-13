"""
ProServis Azure SQL Setup Helper
Azure SQL bağlantısı için gerekli ODBC driver kontrolü ve kurulum yardımcısı
"""

import pyodbc
import logging
logger = logging.getLogger(__name__)
import webbrowser



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
    logger.info("\n" + "="*70)
    logger.info("🔧 AZURE SQL ODBC DRIVER KURULUMU")
    logger.info("="*70)
    
    has_driver, drivers = check_odbc_driver()
    
    if has_driver:
        logger.info("\n✅ Modern ODBC Driver bulundu!")
        logger.info("   Azure SQL bağlantısı yapılabilir.")
    else:
        logger.info("\n⚠️ Modern ODBC Driver bulunamadı!")
        logger.info("\n📥 Kurulum Adımları:")
        logger.info("1. Microsoft ODBC Driver 18 for SQL Server'ı indirin")
        logger.info(f"   URL: {get_download_url()}")
        logger.info("2. İndirilen .msi dosyasını çalıştırın")
        logger.info("3. Kurulum tamamlandıktan sonra sistemi yeniden başlatın")
        logger.info("4. ProServis'i tekrar çalıştırın")
        
        logger.warning("\n🌐 İndirme sayfasını açmak ister misiniz? (E/H): ", end='')
        choice = input().strip().upper()
        
        if choice == 'E':
            open_download_page()
            logger.info("✅ Tarayıcıda açıldı")
    
    logger.info("\n" + "="*70)
    logger.info("📋 Mevcut ODBC Driver'lar:")
    logger.info("="*70)
    for driver in drivers:
        marker = "✅" if any(x in driver for x in ['17', '18', '13']) else "  "
        logger.info(f"{marker} {driver}")
    
    logger.info("\n" + "="*70)
    logger.info("🔗 Connection String Template:")
    logger.info("="*70)
    logger.info(get_connection_string_template())
    logger.info("="*70 + "\n")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    show_setup_instructions()
