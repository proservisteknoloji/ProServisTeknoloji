"""
Uygulama ayarlarını yönetmek için merkezi bir modül.

Bu modül, uygulama ayarlarını kullanıcının sistemindeki uygun bir konumda
(örn. AppData/Roaming) JSON formatında saklamak, yüklemek ve yönetmek için
bir `SettingsManager` sınıfı sağlar.
"""

import json
import os
import sys
import logging
from typing import Dict, Any, Optional

# Logging yapılandırması

class SettingsManager:
    """
    Uygulama ayarlarını bir JSON dosyasında yönetir.
    Ayarları yükler, kaydeder, günceller ve sıfırlar. Bu bir singleton sınıfıdır.
    """
    _instance: Optional['SettingsManager'] = None
    _config: Dict[str, Any] = {}
    _config_file_path: str = ""

    def __new__(cls) -> 'SettingsManager':
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """
        Ayarlar yöneticisini başlatır, dosya yolunu belirler ve ayarları yükler.
        """
        self._config_file_path = self._get_config_path("app_config.json")
        self.load_settings()

    def _get_config_path(self, filename: str) -> str:
        """
        İşletim sistemine uygun olarak ayar dosyasının tam yolunu döndürür.
        AppData/Roaming (Windows) veya ~/.config (Linux/macOS) kullanılır.
        """
        if sys.platform == "win32":
            app_data_dir = os.getenv('APPDATA')
        else:
            # Linux/macOS için XDG Base Directory Specification'a daha uygun
            app_data_dir = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))

        if not app_data_dir:
            # Fallback: programın çalıştığı dizin (acil durum)
            app_data_dir = os.path.dirname(os.path.abspath(__file__))
            logging.warning("APPDATA veya XDG_CONFIG_HOME bulunamadı. Ayarlar program dizinine kaydedilecek.")

        proservis_dir = os.path.join(app_data_dir, 'ProServis')

        try:
            if not os.path.exists(proservis_dir):
                os.makedirs(proservis_dir)
                logging.info(f"Ayar dizini oluşturuldu: {proservis_dir}")
        except OSError as e:
            logging.error(f"Ayar dizini oluşturulamadı: {e}", exc_info=True)
            # Hata durumunda programın yanına kaydet
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            
        return os.path.join(proservis_dir, filename)

    def load_settings(self) -> None:
        """
        Ayar dosyasından ayarları yükler. Dosya yoksa veya bozuksa boş bir sözlük kullanır.
        """
        if not os.path.exists(self._config_file_path):
            self._config = {}
            logging.info("Ayar dosyası bulunamadı, varsayılan (boş) ayarlar kullanılıyor.")
            return

        try:
            with open(self._config_file_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                logging.info(f"Ayarlar başarıyla yüklendi: {self._config_file_path}")
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            self._config = {}
            logging.error(f"Ayar dosyası okunurken hata oluştu: {e}. Varsayılan ayarlar kullanılacak.", exc_info=True)

    def save_settings(self) -> bool:
        """
        Mevcut ayarları dosyaya kaydeder.
        """
        try:
            with open(self._config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            logging.info("Ayarlar başarıyla kaydedildi.")
            return True
        except Exception as e:
            logging.error(f"Ayar dosyası kaydedilirken hata oluştu: {e}", exc_info=True)
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Belirli bir ayarı anahtar ile alır. Bulunamazsa varsayılan değeri döndürür.
        """
        return self._config.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """
        Belirli bir ayarı günceller ve hemen dosyaya kaydeder.
        Company ile ilgili ayarları aynı zamanda database'e de kaydeder.
        """
        self._config[key] = value
        self.save_settings()
        
        # Company ile ilgili ayarları database'e de kaydet
        if key.startswith('company_'):
            self._sync_company_setting_to_db(key, value)
    
    def _sync_company_setting_to_db(self, key: str, value: Any) -> None:
        """
        Company ayarlarını database'deki settings tablosuna senkronize eder.
        """
        try:
            from .database.connection import DatabaseManager
            db = DatabaseManager()
            
            # Önce ayarın var olup olmadığını kontrol et
            existing = db.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
            
            if existing:
                # Güncelle
                db.execute_query("UPDATE settings SET value = ? WHERE key = ?", (value, key))
            else:
                # Yeni kayıt ekle
                db.execute_query("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
            
            logging.info(f"Company ayarı database'e senkronize edildi: {key} = {value}")
            
        except Exception as e:
            logging.error(f"Company ayarı database'e senkronize edilirken hata: {e}", exc_info=True)

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Tüm ayarları bir sözlük olarak döndürür.
        """
        return self._config.copy()

    def reset_settings(self) -> bool:
        """
        Tüm ayarları sıfırlar ve ayar dosyasını siler.
        """
        self._config = {}
        if os.path.exists(self._config_file_path):
            try:
                os.remove(self._config_file_path)
                logging.info("Ayar dosyası başarıyla silindi.")
                return True
            except OSError as e:
                logging.error(f"Ayar dosyası silinirken hata: {e}", exc_info=True)
                return False
        return True

# Eski fonksiyonel arayüzü koruyarak geriye dönük uyumluluk sağla
# Yeni kodda bu fonksiyonlar yerine SettingsManager().get_setting() vb. kullanılmalıdır.

def save_app_config(config: Dict[str, Any]) -> bool:
    """Geriye dönük uyumluluk için. Ayarları kaydeder."""
    manager = SettingsManager()
    manager._config = config # Doğrudan config'i ayarla
    return manager.save_settings()

def load_app_config() -> Dict[str, Any]:
    """Geriye dönük uyumluluk için. Ayarları yükler."""
    manager = SettingsManager()
    manager.load_settings() # Yeniden yükle
    return manager.get_all_settings()

def reset_app_config() -> bool:
    """Geriye dönük uyumluluk için. Ayarları sıfırlar."""
    return SettingsManager().reset_settings()

def get_setting(key: str, default: Any = None) -> Any:
    """Geriye dönük uyumluluk için. Belirli bir ayarı anahtar ile alır."""
    return SettingsManager().get_setting(key, default)

def set_setting(key: str, value: Any) -> None:
    """Geriye dönük uyumluluk için. Belirli bir ayarı günceller."""
    return SettingsManager().set_setting(key, value)

def save_setting(key: str, value: Any) -> None:
    """Geriye dönük uyumluluk için. set_setting ile aynı işlevi yapar."""
    return SettingsManager().set_setting(key, value)
