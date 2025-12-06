# -*- coding: utf-8 -*-
"""
Plugin Manager - Eklenti yönetim sistemi
"""

import os
import json
import importlib
import importlib.util
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PluginInfo:
    """Eklenti bilgisi sınıfı"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    enabled: bool = True
    module_path: str = ""

class ProServisPlugin(ABC):
    """ProServis eklenti temel sınıfı"""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """Eklenti bilgilerini döndürür"""
        pass
    
    @abstractmethod
    def initialize(self, app_context: Any) -> bool:
        """Eklentiyi başlatır"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Eklentiyi kapatır"""
        pass
    
    def on_update_available(self, plugin_path: str) -> bool:
        """Eklenti güncellemesi mevcut olduğunda çağrılır"""
        return True
    
    def on_update_complete(self) -> bool:
        """Eklenti güncellemesi tamamlandığında çağrılır"""
        return True

class PluginManager:
    """Eklenti yönetici sınıfı"""
    
    def __init__(self, app_data_dir: str, plugins_dir: Optional[str] = None):
        self.app_data_dir = app_data_dir
        self.plugins_dir = plugins_dir or os.path.join(app_data_dir, "plugins")
        self.plugin_config_file = os.path.join(app_data_dir, "plugins_config.json")
        self.loaded_plugins: Dict[str, ProServisPlugin] = {}
        self.plugin_configs: Dict[str, PluginInfo] = {}
        
        os.makedirs(self.plugins_dir, exist_ok=True)
        self._load_plugin_configs()
    
    def install_plugin(self, plugin_file: str, enable: bool = True) -> bool:
        """Eklenti dosyasını yükler ve kurulumunu yapar"""
        try:
            import zipfile
            
            if not plugin_file.endswith('.zip'):
                logging.error("Eklenti dosyası .zip formatında olmalıdır")
                return False
            
            # Plugin ismini dosya adından al
            plugin_name = os.path.splitext(os.path.basename(plugin_file))[0]
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            
            # Eski sürümü varsa yedekle
            if os.path.exists(plugin_path):
                backup_path = f"{plugin_path}_backup"
                if os.path.exists(backup_path):
                    import shutil
                    shutil.rmtree(backup_path)
                os.rename(plugin_path, backup_path)
            
            # Zip dosyasını çıkart
            with zipfile.ZipFile(plugin_file, 'r') as zipf:
                zipf.extractall(plugin_path)
            
            # Plugin bilgilerini oku
            plugin_info = self._read_plugin_info(plugin_path)
            if not plugin_info:
                logging.error(f"Plugin bilgileri okunamadı: {plugin_name}")
                return False
            
            # Plugin'i kaydet
            plugin_info.enabled = enable
            self.plugin_configs[plugin_name] = plugin_info
            self._save_plugin_configs()
            
            logging.info(f"Plugin kuruldu: {plugin_name} v{plugin_info.version}")
            
            # Eğer etkinleştirilecekse yükle
            if enable:
                return self.load_plugin(plugin_name)
            
            return True
            
        except Exception as e:
            logging.error(f"Plugin kurulum hatası: {e}")
            return False
    
    def load_plugin(self, plugin_name: str, app_context: Any = None) -> bool:
        """Belirtilen eklentiyi yükler"""
        try:
            if plugin_name in self.loaded_plugins:
                logging.warning(f"Plugin zaten yüklü: {plugin_name}")
                return True
            
            plugin_config = self.plugin_configs.get(plugin_name)
            if not plugin_config or not plugin_config.enabled:
                logging.warning(f"Plugin devre dışı veya bulunamadı: {plugin_name}")
                return False
            
            # Plugin modülünü yükle
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            main_module = os.path.join(plugin_path, "main.py")
            
            if not os.path.exists(main_module):
                logging.error(f"Plugin main modülü bulunamadı: {main_module}")
                return False
            
            # Modülü dinamik olarak yükle
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}", main_module
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Plugin sınıfını bul
            plugin_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, ProServisPlugin) and 
                    obj != ProServisPlugin):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logging.error(f"Plugin sınıfı bulunamadı: {plugin_name}")
                return False
            
            # Plugin'i başlat
            plugin_instance = plugin_class()
            if plugin_instance.initialize(app_context):
                self.loaded_plugins[plugin_name] = plugin_instance
                logging.info(f"Plugin başarıyla yüklendi: {plugin_name}")
                return True
            else:
                logging.error(f"Plugin başlatılamadı: {plugin_name}")
                return False
                
        except Exception as e:
            logging.error(f"Plugin yükleme hatası: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Belirtilen eklentiyi kaldırır"""
        try:
            if plugin_name not in self.loaded_plugins:
                logging.warning(f"Plugin yüklü değil: {plugin_name}")
                return True
            
            plugin = self.loaded_plugins[plugin_name]
            if plugin.shutdown():
                del self.loaded_plugins[plugin_name]
                logging.info(f"Plugin kaldırıldı: {plugin_name}")
                return True
            else:
                logging.error(f"Plugin kapatılamadı: {plugin_name}")
                return False
                
        except Exception as e:
            logging.error(f"Plugin kaldırma hatası: {e}")
            return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Eklentiyi etkinleştirir"""
        if plugin_name in self.plugin_configs:
            self.plugin_configs[plugin_name].enabled = True
            self._save_plugin_configs()
            logging.info(f"Plugin etkinleştirildi: {plugin_name}")
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Eklentiyi devre dışı bırakır"""
        # Önce yüklüyse kaldır
        if plugin_name in self.loaded_plugins:
            self.unload_plugin(plugin_name)
        
        # Konfigürasyonu güncelle
        if plugin_name in self.plugin_configs:
            self.plugin_configs[plugin_name].enabled = False
            self._save_plugin_configs()
            logging.info(f"Plugin devre dışı bırakıldı: {plugin_name}")
            return True
        return False
    
    def remove_plugin(self, plugin_name: str) -> bool:
        """Eklentiyi tamamen kaldırır"""
        try:
            # Önce yüklüyse kaldır
            if plugin_name in self.loaded_plugins:
                self.unload_plugin(plugin_name)
            
            # Plugin klasörünü sil
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            if os.path.exists(plugin_path):
                import shutil
                shutil.rmtree(plugin_path)
            
            # Konfigürasyondan kaldır
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]
                self._save_plugin_configs()
            
            logging.info(f"Plugin tamamen kaldırıldı: {plugin_name}")
            return True
            
        except Exception as e:
            logging.error(f"Plugin kaldırma hatası: {e}")
            return False
    
    def get_plugin_list(self) -> List[PluginInfo]:
        """Tüm eklentilerin listesini döndürür"""
        return list(self.plugin_configs.values())
    
    def get_loaded_plugins(self) -> List[str]:
        """Yüklü eklentilerin listesini döndürür"""
        return list(self.loaded_plugins.keys())
    
    def load_all_plugins(self, app_context: Any = None):
        """Tüm etkin eklentileri yükler"""
        for plugin_name, config in self.plugin_configs.items():
            if config.enabled and plugin_name not in self.loaded_plugins:
                self.load_plugin(plugin_name, app_context)
    
    def update_plugin(self, plugin_name: str, plugin_file: str) -> bool:
        """Eklentiyi günceller"""
        try:
            # Önce mevcut plugin'i yedekle
            was_loaded = plugin_name in self.loaded_plugins
            if was_loaded:
                self.unload_plugin(plugin_name)
            
            # Eski kurulumu yedekle
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            backup_path = f"{plugin_path}_update_backup"
            
            if os.path.exists(plugin_path):
                if os.path.exists(backup_path):
                    import shutil
                    shutil.rmtree(backup_path)
                os.rename(plugin_path, backup_path)
            
            # Yeni sürümü kur
            success = self.install_plugin(plugin_file, enable=was_loaded)
            
            if success:
                # Yedek klasörü sil
                if os.path.exists(backup_path):
                    import shutil
                    shutil.rmtree(backup_path)
                logging.info(f"Plugin güncellendi: {plugin_name}")
            else:
                # Hata durumunda geri al
                if os.path.exists(backup_path):
                    if os.path.exists(plugin_path):
                        import shutil
                        shutil.rmtree(plugin_path)
                    os.rename(backup_path, plugin_path)
                logging.error(f"Plugin güncellemesi başarısız, geri alındı: {plugin_name}")
            
            return success
            
        except Exception as e:
            logging.error(f"Plugin güncelleme hatası: {e}")
            return False
    
    def _read_plugin_info(self, plugin_path: str) -> Optional[PluginInfo]:
        """Plugin bilgilerini dosyadan okur"""
        try:
            info_file = os.path.join(plugin_path, "plugin_info.json")
            if not os.path.exists(info_file):
                return None
            
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return PluginInfo(
                name=data['name'],
                version=data['version'],
                description=data['description'],
                author=data['author'],
                dependencies=data.get('dependencies', []),
                module_path=plugin_path
            )
            
        except Exception as e:
            logging.error(f"Plugin bilgisi okunamadı: {e}")
            return None
    
    def _load_plugin_configs(self):
        """Plugin konfigürasyonlarını yükler"""
        try:
            if os.path.exists(self.plugin_config_file):
                with open(self.plugin_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for plugin_data in data.get('plugins', []):
                    plugin_info = PluginInfo(
                        name=plugin_data['name'],
                        version=plugin_data['version'],
                        description=plugin_data['description'],
                        author=plugin_data['author'],
                        dependencies=plugin_data.get('dependencies', []),
                        enabled=plugin_data.get('enabled', True),
                        module_path=plugin_data.get('module_path', '')
                    )
                    self.plugin_configs[plugin_info.name] = plugin_info
                    
        except Exception as e:
            logging.error(f"Plugin konfigürasyonları yüklenemedi: {e}")
    
    def _save_plugin_configs(self):
        """Plugin konfigürasyonlarını kaydeder"""
        try:
            data = {'plugins': []}
            
            for plugin_info in self.plugin_configs.values():
                plugin_data = {
                    'name': plugin_info.name,
                    'version': plugin_info.version,
                    'description': plugin_info.description,
                    'author': plugin_info.author,
                    'dependencies': plugin_info.dependencies,
                    'enabled': plugin_info.enabled,
                    'module_path': plugin_info.module_path
                }
                data['plugins'].append(plugin_data)
            
            with open(self.plugin_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"Plugin konfigürasyonları kaydedilemedi: {e}")