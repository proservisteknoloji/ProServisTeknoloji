# utils/setup/license_manager.py
"""Lisans kontrolü ve aktivasyon yönetimi."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from utils.settings_manager import load_app_config


def check_license() -> bool:
    """
    Lisans durumunu kontrol eder ve gerekirse aktivasyon penceresini gösterir.
    
    Returns:
        bool: Lisans geçerli mi?
    """
    config = load_app_config()
    
    if config.get('is_activated', False):
        logging.info("Uygulama aktif lisansa sahip.")
        return True

    first_run_date_str = config.get('first_run_date')
    
    if not first_run_date_str:
        # İlk çalıştırma - Aktivasyon dialog'unu göster
        logging.info("İlk çalıştırma. Aktivasyon penceresi gösteriliyor.")
        from ui.dialogs.activation_dialog import ActivationDialog
        
        activation_dialog = ActivationDialog()
        if activation_dialog.exec():
            logging.info("Uygulama başarıyla aktive edildi veya deneme sürümü başlatıldı.")
            return True
        else:
            logging.info("Aktivasyon iptal edildi. Uygulama kapatılıyor.")
            return False

    # Deneme sürümü devam ediyor mu kontrol et
    try:
        start_date = datetime.strptime(first_run_date_str, "%Y-%m-%d")
        days_passed = (datetime.now() - start_date).days
        remaining_days = 15 - days_passed
        
        if remaining_days > 0:
            QMessageBox.information(
                None, 
                "Demo Sürümü", 
                f"Demo sürümünüzü kullanıyorsunuz.\nKalan gün sayısı: {remaining_days}"
            )
            logging.info(f"Demo sürümü devam ediyor. Kalan gün: {remaining_days}")
            return True
        else:
            logging.warning("Demo süresi doldu. Lisans gerekli.")
            QMessageBox.warning(
                None,
                "Demo Süresi Doldu",
                "15 günlük demo süreniz sona erdi. Lütfen uygulamayı lisanslayın."
            )

    except (ValueError, TypeError) as e:
        logging.error(f"Tarih formatı hatası: {e}. Aktivasyon penceresi gösterilecek.")
    
    # Deneme süresi bitmişse veya tarih hatalıysa aktivasyon penceresini göster
    from ui.dialogs.activation_dialog import ActivationDialog
    
    activation_dialog = ActivationDialog()
    if activation_dialog.exec():
        logging.info("Uygulama başarıyla aktive edildi.")
        return True
    else:
        logging.info("Aktivasyon iptal edildi. Uygulama kapatılıyor.")
        return False
