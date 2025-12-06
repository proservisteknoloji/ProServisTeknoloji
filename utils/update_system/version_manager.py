# -*- coding: utf-8 -*-
"""
Version Manager - Sürüm kontrolü ve yönetimi
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class Version:
    """Sürüm bilgisi sınıfı"""
    major: int
    minor: int
    patch: int
    build: int = 0
    tag: str = ""
    
    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.build > 0:
            version += f".{self.build}"
        if self.tag:
            version += f"-{self.tag}"
        return version
    
    def __lt__(self, other: 'Version') -> bool:
        return (self.major, self.minor, self.patch, self.build) < \
               (other.major, other.minor, other.patch, other.build)
    
    def __eq__(self, other: 'Version') -> bool:
        return (self.major, self.minor, self.patch, self.build) == \
               (other.major, other.minor, other.patch, other.build)
    
    @classmethod
    def from_string(cls, version_str: str) -> 'Version':
        """String'den Version objesi oluşturur"""
        tag = ""
        if "-" in version_str:
            version_str, tag = version_str.split("-", 1)
        
        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        build = int(parts[3]) if len(parts) > 3 else 0
        
        return cls(major, minor, patch, build, tag)

@dataclass
class VersionInfo:
    """Detaylı sürüm bilgisi"""
    version: Version
    release_date: str
    description: str
    changelog: List[str]
    dependencies: List[str]
    is_critical: bool = False
    rollback_supported: bool = True

class VersionManager:
    """Sürüm yönetimi sınıfı"""
    
    def __init__(self, app_data_dir: str):
        self.app_data_dir = app_data_dir
        self.version_file = os.path.join(app_data_dir, "version_info.json")
        self.current_version = Version(2, 0, 0, 1)  # ProServis v2.0.0.1
        self._ensure_version_file()
    
    def _ensure_version_file(self):
        """Sürüm dosyasının var olduğundan emin olur"""
        if not os.path.exists(self.version_file):
            self._create_initial_version_file()
    
    def _create_initial_version_file(self):
        """İlk sürüm dosyasını oluşturur"""
        initial_info = VersionInfo(
            version=self.current_version,
            release_date=datetime.now().strftime("%Y-%m-%d"),
            description="ProServis Teknik Servis Yönetim Sistemi v2.0",
            changelog=[
                "İlk sürüm",
                "Teknik servis yönetimi",
                "Müşteri takibi",
                "Stok yönetimi",
                "Faturalama sistemi",
                "Sayaç okuma",
                "CPC yönetimi"
            ],
            dependencies=[]
        )
        
        self.save_version_info(initial_info)
        logging.info(f"İlk sürüm dosyası oluşturuldu: {self.current_version}")
    
    def get_current_version(self) -> Version:
        """Mevcut sürümü döndürür"""
        return self.current_version
    
    def get_version_info(self, version: Optional[Version] = None) -> Optional[VersionInfo]:
        """Belirtilen sürümün bilgilerini döndürür"""
        if version is None:
            version = self.current_version
        
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for version_data in data.get('versions', []):
                v = Version.from_string(version_data['version'])
                if v == version:
                    return VersionInfo(
                        version=v,
                        release_date=version_data['release_date'],
                        description=version_data['description'],
                        changelog=version_data['changelog'],
                        dependencies=version_data.get('dependencies', []),
                        is_critical=version_data.get('is_critical', False),
                        rollback_supported=version_data.get('rollback_supported', True)
                    )
        except Exception as e:
            logging.error(f"Sürüm bilgisi okunamadı: {e}")
        
        return None
    
    def save_version_info(self, version_info: VersionInfo):
        """Sürüm bilgisini kaydeder"""
        try:
            # Mevcut dosyayı oku
            data = {'versions': []}
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Yeni sürümü ekle veya güncelle
            version_str = str(version_info.version)
            version_data = {
                'version': version_str,
                'release_date': version_info.release_date,
                'description': version_info.description,
                'changelog': version_info.changelog,
                'dependencies': version_info.dependencies,
                'is_critical': version_info.is_critical,
                'rollback_supported': version_info.rollback_supported
            }
            
            # Aynı sürüm varsa güncelle, yoksa ekle
            found = False
            for i, existing in enumerate(data['versions']):
                if existing['version'] == version_str:
                    data['versions'][i] = version_data
                    found = True
                    break
            
            if not found:
                data['versions'].append(version_data)
            
            # Sürümleri sırala (en yeni önce)
            data['versions'].sort(
                key=lambda x: Version.from_string(x['version']), 
                reverse=True
            )
            
            # Dosyaya yaz
            os.makedirs(os.path.dirname(self.version_file), exist_ok=True)
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"Sürüm bilgisi kaydedildi: {version_str}")
            
        except Exception as e:
            logging.error(f"Sürüm bilgisi kaydedilemedi: {e}")
    
    def get_all_versions(self) -> List[VersionInfo]:
        """Tüm sürümlerin listesini döndürür"""
        versions = []
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for version_data in data.get('versions', []):
                version_info = VersionInfo(
                    version=Version.from_string(version_data['version']),
                    release_date=version_data['release_date'],
                    description=version_data['description'],
                    changelog=version_data['changelog'],
                    dependencies=version_data.get('dependencies', []),
                    is_critical=version_data.get('is_critical', False),
                    rollback_supported=version_data.get('rollback_supported', True)
                )
                versions.append(version_info)
        
        except Exception as e:
            logging.error(f"Sürüm listesi okunamadı: {e}")
        
        return versions
    
    def is_newer_version(self, other_version: Version) -> bool:
        """Verilen sürümün mevcut sürümden daha yeni olup olmadığını kontrol eder"""
        return other_version > self.current_version
    
    def update_current_version(self, new_version: Version):
        """Mevcut sürümü günceller"""
        self.current_version = new_version
        logging.info(f"Mevcut sürüm güncellendi: {new_version}")