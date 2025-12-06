# -*- coding: utf-8 -*-
"""
Update Manager - Ana güncelleme sistemi
"""

import os
import json
import shutil
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path

from .version_manager import VersionManager, Version, VersionInfo
from .backup_manager import BackupManager
from .plugin_manager import PluginManager

class UpdatePackage:
    """Güncelleme paketi sınıfı"""
    
    def __init__(self, package_path: str):
        self.package_path = package_path
        self.info = None
        self.files = []
        self.scripts = []
        self._load_package_info()
    
    def _load_package_info(self):
        """Güncelleme paketi bilgilerini yükler"""
        try:
            import zipfile
            
            if not os.path.exists(self.package_path):
                raise FileNotFoundError(f"Güncelleme paketi bulunamadı: {self.package_path}")
            
            with zipfile.ZipFile(self.package_path, 'r') as zipf:
                # update_info.json dosyasını oku
                if 'update_info.json' in zipf.namelist():
                    with zipf.open('update_info.json') as f:
                        self.info = json.load(f)
                else:
                    raise ValueError("Güncelleme paketi bilgi dosyası bulunamadı")
                
                # Dosya listesini al
                self.files = [f for f in zipf.namelist() 
                             if not f.startswith('scripts/') and f != 'update_info.json']
                
                # Script listesini al
                self.scripts = [f for f in zipf.namelist() 
                               if f.startswith('scripts/') and f.endswith('.py')]
                
        except Exception as e:
            logging.error(f"Güncelleme paketi yüklenemedi: {e}")
            raise
    
    def get_version(self) -> Version:
        """Güncelleme paketi sürümünü döndürür"""
        if self.info:
            return Version.from_string(self.info['version'])
        return Version(0, 0, 0)
    
    def get_info(self) -> Dict:
        """Güncelleme paketi bilgilerini döndürür"""
        return self.info or {}
    
    def extract_to(self, target_dir: str) -> bool:
        """Güncelleme paketini belirtilen dizine çıkarır"""
        try:
            import zipfile
            
            os.makedirs(target_dir, exist_ok=True)
            
            with zipfile.ZipFile(self.package_path, 'r') as zipf:
                # Sadece uygulama dosyalarını çıkar (script'ler hariç)
                for file in self.files:
                    zipf.extract(file, target_dir)
            
            return True
            
        except Exception as e:
            logging.error(f"Güncelleme paketi çıkarılamadı: {e}")
            return False

class UpdateManager:
    """Ana güncelleme yönetici sınıfı"""
    
    def __init__(self, app_data_dir: str, app_root_dir: str):
        self.app_data_dir = app_data_dir
        self.app_root_dir = app_root_dir
        self.temp_dir = os.path.join(app_data_dir, "update_temp")
        self.updates_dir = os.path.join(app_data_dir, "updates")
        
        # Alt sistemleri başlat
        self.version_manager = VersionManager(app_data_dir)
        self.backup_manager = BackupManager(app_data_dir)
        self.plugin_manager = PluginManager(app_data_dir)
        
        # Update durumu
        self.current_update_id = None
        self.update_status = "idle"  # idle, downloading, preparing, applying, completed, failed
        self.progress_callback: Optional[Callable[[str, int], None]] = None
        
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.updates_dir, exist_ok=True)
    
    def set_progress_callback(self, callback: Callable[[str, int], None]):
        """İlerleme durumu callback'ini ayarlar"""
        self.progress_callback = callback
    
    def _update_progress(self, message: str, percentage: int = 0):
        """İlerleme durumunu günceller"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        logging.info(f"Update Progress: {message} ({percentage}%)")
    
    def check_for_updates(self, update_file_path: str) -> Optional[UpdatePackage]:
        """Güncelleme dosyasını kontrol eder"""
        try:
            if not os.path.exists(update_file_path):
                return None
            
            package = UpdatePackage(update_file_path)
            current_version = self.version_manager.get_current_version()
            package_version = package.get_version()
            
            if self.version_manager.is_newer_version(package_version):
                logging.info(f"Yeni güncelleme bulundu: {package_version} (mevcut: {current_version})")
                return package
            else:
                logging.info("Güncelleme bulunamadı veya mevcut sürüm daha yeni")
                return None
                
        except Exception as e:
            logging.error(f"Güncelleme kontrolü hatası: {e}")
            return None
    
    def prepare_update(self, update_package: UpdatePackage) -> bool:
        """Güncellememi hazırlar"""
        try:
            self.update_status = "preparing"
            self._update_progress("Güncelleme hazırlanıyor...", 10)
            
            # Geçici dizini temizle
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Update ID oluştur
            self.current_update_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Güncelleme paketini çıkar
            self._update_progress("Güncelleme paketi çıkarılıyor...", 20)
            if not update_package.extract_to(self.temp_dir):
                raise Exception("Güncelleme paketi çıkarılamadı")
            
            # Gereksinimler kontrolü
            self._update_progress("Gereksinimler kontrol ediliyor...", 30)
            if not self._check_requirements(update_package):
                raise Exception("Gereksinim kontrolü başarısız")
            
            # Dosya bütünlük kontrolü
            self._update_progress("Dosya bütünlüğü kontrol ediliyor...", 40)
            if not self._verify_package_integrity(update_package):
                raise Exception("Dosya bütünlük kontrolü başarısız")
            
            self._update_progress("Güncelleme hazır", 50)
            return True
            
        except Exception as e:
            logging.error(f"Güncelleme hazırlama hatası: {e}")
            self.update_status = "failed"
            return False
    
    def apply_update(self, update_package: UpdatePackage, create_backup: bool = True) -> bool:
        """Güncellememi uygular"""
        try:
            self.update_status = "applying"
            self._update_progress("Güncelleme uygulanıyor...", 60)
            
            if create_backup:
                # Mevcut durumu yedekle
                self._update_progress("Sistem yedeği oluşturuluyor...", 65)
                backup_name = f"before_update_{self.current_update_id}"
                backup_paths = [
                    self.app_root_dir,
                    os.path.join(self.app_data_dir, "app_config.json")
                ]
                
                if not self.backup_manager.create_full_backup(backup_name, backup_paths):
                    raise Exception("Sistem yedeği oluşturulamadı")
            
            # Pre-update script'lerini çalıştır
            self._update_progress("Ön güncelleme işlemleri...", 70)
            if not self._run_update_scripts(update_package, "pre"):
                raise Exception("Ön güncelleme işlemleri başarısız")
            
            # Dosyaları güncelle
            self._update_progress("Dosyalar güncelleniyor...", 80)
            if not self._update_files(update_package):
                raise Exception("Dosya güncelleme başarısız")
            
            # Plugin'leri güncelle
            self._update_progress("Eklentiler güncelleniyor...", 85)
            self._update_plugins(update_package)
            
            # Post-update script'lerini çalıştır
            self._update_progress("Son işlemler...", 90)
            if not self._run_update_scripts(update_package, "post"):
                raise Exception("Son işlemler başarısız")
            
            # Sürüm bilgisini güncelle
            new_version = update_package.get_version()
            self.version_manager.update_current_version(new_version)
            
            # Yeni sürüm bilgisini kaydet
            package_info = update_package.get_info()
            version_info = VersionInfo(
                version=new_version,
                release_date=package_info.get('release_date', datetime.now().strftime("%Y-%m-%d")),
                description=package_info.get('description', ''),
                changelog=package_info.get('changelog', []),
                dependencies=package_info.get('dependencies', [])
            )
            self.version_manager.save_version_info(version_info)
            
            self.update_status = "completed"
            self._update_progress("Güncelleme tamamlandı!", 100)
            
            # Geçici dosyaları temizle
            self._cleanup_temp_files()
            
            logging.info(f"Güncelleme başarıyla tamamlandı: {new_version}")
            return True
            
        except Exception as e:
            logging.error(f"Güncelleme uygulama hatası: {e}")
            self.update_status = "failed"
            
            # Hata durumunda geri al
            if create_backup:
                self._update_progress("Hata! Geri alınıyor...", 0)
                self.rollback_update()
            
            return False
    
    def rollback_update(self) -> bool:
        """Son güncellememi geri alır"""
        try:
            self._update_progress("Sistem geri alınıyor...", 10)
            
            if not self.current_update_id:
                logging.error("Geri alınacak güncelleme bulunamadı")
                return False
            
            # Son yedeği bul
            backups = self.backup_manager.get_backup_list()
            rollback_backup = None
            
            for backup in backups:
                if backup['name'].startswith(f"before_update_{self.current_update_id}"):
                    rollback_backup = backup
                    break
            
            if not rollback_backup:
                logging.error("Geri alma yedeği bulunamadı")
                return False
            
            # Mevcut durumu yedekle (rollback öncesi)
            self._update_progress("Mevcut durum yedekleniyor...", 20)
            failed_backup_name = f"failed_update_{self.current_update_id}"
            self.backup_manager.create_full_backup(failed_backup_name, [self.app_root_dir])
            
            # Yedeği geri yükle
            self._update_progress("Yedek geri yükleniyor...", 50)
            if not self.backup_manager.restore_backup(
                rollback_backup['filename'], 
                os.path.dirname(self.app_root_dir)
            ):
                raise Exception("Yedek geri yüklenemedi")
            
            self._update_progress("Geri alma tamamlandı", 100)
            self.update_status = "rolled_back"
            
            logging.info("Güncelleme başarıyla geri alındı")
            return True
            
        except Exception as e:
            logging.error(f"Geri alma hatası: {e}")
            return False
    
    def _check_requirements(self, update_package: UpdatePackage) -> bool:
        """Güncelleme gereksinimlerini kontrol eder"""
        try:
            package_info = update_package.get_info()
            
            # Minimum sürüm kontrolü
            if 'min_version' in package_info:
                min_version = Version.from_string(package_info['min_version'])
                current_version = self.version_manager.get_current_version()
                
                if current_version < min_version:
                    logging.error(f"Minimum sürüm gereksinimi karşılanmıyor: {min_version}")
                    return False
            
            # Disk alanı kontrolü
            if 'required_space_mb' in package_info:
                required_space = package_info['required_space_mb'] * 1024 * 1024
                free_space = shutil.disk_usage(self.app_root_dir).free
                
                if free_space < required_space:
                    logging.error(f"Yetersiz disk alanı: {required_space} gerekli, {free_space} mevcut")
                    return False
            
            # Bağımlılık kontrolü
            dependencies = package_info.get('dependencies', [])
            for dep in dependencies:
                if not self._check_dependency(dep):
                    logging.error(f"Bağımlılık karşılanmıyor: {dep}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Gereksinim kontrolü hatası: {e}")
            return False
    
    def _check_dependency(self, dependency: str) -> bool:
        """Bağımlılık kontrolü yapar"""
        try:
            # Python modülü kontrolü
            if dependency.startswith('python:'):
                module_name = dependency.split(':', 1)[1]
                importlib.import_module(module_name)
                return True
            
            # Dosya varlığı kontrolü
            elif dependency.startswith('file:'):
                file_path = dependency.split(':', 1)[1]
                return os.path.exists(os.path.join(self.app_root_dir, file_path))
            
            # Plugin kontrolü
            elif dependency.startswith('plugin:'):
                plugin_name = dependency.split(':', 1)[1]
                return plugin_name in self.plugin_manager.loaded_plugins
            
            return True
            
        except Exception:
            return False
    
    def _verify_package_integrity(self, update_package: UpdatePackage) -> bool:
        """Güncelleme paketi bütünlüğünü kontrol eder"""
        try:
            package_info = update_package.get_info()
            
            if 'file_checksums' not in package_info:
                logging.warning("Dosya checksum'ları bulunamadı, bütünlük kontrolü atlanıyor")
                return True
            
            import zipfile
            
            with zipfile.ZipFile(update_package.package_path, 'r') as zipf:
                for filename, expected_checksum in package_info['file_checksums'].items():
                    if filename in zipf.namelist():
                        file_data = zipf.read(filename)
                        actual_checksum = hashlib.md5(file_data).hexdigest()
                        
                        if actual_checksum != expected_checksum:
                            logging.error(f"Dosya bütünlük hatası: {filename}")
                            return False
            
            return True
            
        except Exception as e:
            logging.error(f"Bütünlük kontrolü hatası: {e}")
            return False
    
    def _update_files(self, update_package: UpdatePackage) -> bool:
        """Dosyaları günceller"""
        try:
            # Temp dizinindeki dosyaları hedef dizine kopyala
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if file == 'update_info.json':
                        continue
                    
                    source_path = os.path.join(root, file)
                    relative_path = os.path.relpath(source_path, self.temp_dir)
                    target_path = os.path.join(self.app_root_dir, relative_path)
                    
                    # Hedef dizini oluştur
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    # Dosyayı kopyala
                    shutil.copy2(source_path, target_path)
            
            return True
            
        except Exception as e:
            logging.error(f"Dosya güncelleme hatası: {e}")
            return False
    
    def _update_plugins(self, update_package: UpdatePackage):
        """Plugin'leri günceller"""
        try:
            package_info = update_package.get_info()
            plugin_updates = package_info.get('plugin_updates', [])
            
            for plugin_update in plugin_updates:
                plugin_name = plugin_update['name']
                plugin_file = os.path.join(self.temp_dir, 'plugins', f"{plugin_name}.zip")
                
                if os.path.exists(plugin_file):
                    if plugin_update.get('action') == 'update':
                        self.plugin_manager.update_plugin(plugin_name, plugin_file)
                    elif plugin_update.get('action') == 'install':
                        self.plugin_manager.install_plugin(plugin_file)
                    
        except Exception as e:
            logging.error(f"Plugin güncelleme hatası: {e}")
    
    def _run_update_scripts(self, update_package: UpdatePackage, phase: str) -> bool:
        """Güncelleme script'lerini çalıştırır"""
        try:
            import zipfile
            
            script_pattern = f"scripts/{phase}_"
            
            with zipfile.ZipFile(update_package.package_path, 'r') as zipf:
                scripts = [s for s in update_package.scripts if s.startswith(script_pattern)]
                scripts.sort()  # Alphabetical order
                
                for script_path in scripts:
                    # Script'i geçici dizine çıkar
                    script_file = os.path.join(self.temp_dir, script_path)
                    os.makedirs(os.path.dirname(script_file), exist_ok=True)
                    
                    with zipf.open(script_path) as zf, open(script_file, 'wb') as f:
                        f.write(zf.read())
                    
                    # Script'i çalıştır
                    try:
                        import subprocess
                        result = subprocess.run([
                            'python', script_file, 
                            self.app_root_dir, 
                            self.app_data_dir
                        ], capture_output=True, text=True, timeout=300)
                        
                        if result.returncode != 0:
                            logging.error(f"Script hatası: {script_path}\n{result.stderr}")
                            return False
                            
                    except subprocess.TimeoutExpired:
                        logging.error(f"Script timeout: {script_path}")
                        return False
            
            return True
            
        except Exception as e:
            logging.error(f"Script çalıştırma hatası: {e}")
            return False
    
    def _cleanup_temp_files(self):
        """Geçici dosyaları temizler"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"Geçici dosya temizleme hatası: {e}")
    
    def get_update_status(self) -> Dict:
        """Güncelleme durumunu döndürür"""
        return {
            'status': self.update_status,
            'current_update_id': self.current_update_id,
            'current_version': str(self.version_manager.get_current_version())
        }