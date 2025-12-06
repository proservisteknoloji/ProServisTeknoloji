# -*- coding: utf-8 -*-
"""
Backup Manager - Güncelleme öncesi yedekleme ve geri alma sistemi
"""

import os
import shutil
import json
import zipfile
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

class BackupManager:
    """Yedekleme ve geri alma yönetici sınıfı"""
    
    def __init__(self, app_data_dir: str, backup_dir: Optional[str] = None):
        self.app_data_dir = app_data_dir
        self.backup_dir = backup_dir or os.path.join(app_data_dir, "backups")
        self.backup_info_file = os.path.join(self.backup_dir, "backup_info.json")
        self.max_backups = 10  # Maksimum backup sayısı
        
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_full_backup(self, backup_name: str, source_paths: List[str]) -> bool:
        """Tam sistem yedeği oluşturur"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{backup_name}_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            logging.info(f"Tam yedekleme başlatılıyor: {backup_filename}")
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for source_path in source_paths:
                    if os.path.exists(source_path):
                        if os.path.isfile(source_path):
                            # Dosya yedeği
                            arcname = os.path.relpath(source_path, os.path.dirname(source_path))
                            zipf.write(source_path, arcname)
                        elif os.path.isdir(source_path):
                            # Klasör yedeği
                            for root, dirs, files in os.walk(source_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                                    zipf.write(file_path, arcname)
            
            # Backup bilgilerini kaydet
            backup_info = {
                'name': backup_name,
                'filename': backup_filename,
                'timestamp': timestamp,
                'created_date': datetime.now().isoformat(),
                'source_paths': source_paths,
                'type': 'full_backup',
                'size': os.path.getsize(backup_path)
            }
            
            self._save_backup_info(backup_info)
            self._cleanup_old_backups()
            
            logging.info(f"Tam yedekleme tamamlandı: {backup_filename}")
            return True
            
        except Exception as e:
            logging.error(f"Tam yedekleme hatası: {e}")
            return False
    
    def create_incremental_backup(self, backup_name: str, changed_files: List[str]) -> bool:
        """Artımlı yedekleme oluşturur (sadece değişen dosyalar)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{backup_name}_incremental_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            logging.info(f"Artımlı yedekleme başlatılıyor: {backup_filename}")
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in changed_files:
                    if os.path.exists(file_path):
                        arcname = os.path.relpath(file_path, os.path.dirname(file_path))
                        zipf.write(file_path, arcname)
            
            backup_info = {
                'name': backup_name,
                'filename': backup_filename,
                'timestamp': timestamp,
                'created_date': datetime.now().isoformat(),
                'changed_files': changed_files,
                'type': 'incremental_backup',
                'size': os.path.getsize(backup_path)
            }
            
            self._save_backup_info(backup_info)
            
            logging.info(f"Artımlı yedekleme tamamlandı: {backup_filename}")
            return True
            
        except Exception as e:
            logging.error(f"Artımlı yedekleme hatası: {e}")
            return False
    
    def restore_backup(self, backup_filename: str, target_dir: str) -> bool:
        """Yedeği geri yükler"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                logging.error(f"Yedek dosyası bulunamadı: {backup_filename}")
                return False
            
            logging.info(f"Yedek geri yükleniyor: {backup_filename}")
            
            # Hedef dizini temizle (isteğe bağlı)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)
            
            # Zip dosyasını çıkart
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            logging.info(f"Yedek başarıyla geri yüklendi: {backup_filename}")
            return True
            
        except Exception as e:
            logging.error(f"Yedek geri yükleme hatası: {e}")
            return False
    
    def get_backup_list(self) -> List[Dict]:
        """Mevcut yedeklerin listesini döndürür"""
        try:
            if not os.path.exists(self.backup_info_file):
                return []
            
            with open(self.backup_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Tarih sırasına göre sırala (en yeni önce)
            backups = data.get('backups', [])
            backups.sort(key=lambda x: x['created_date'], reverse=True)
            
            return backups
            
        except Exception as e:
            logging.error(f"Yedek listesi okunamadı: {e}")
            return []
    
    def delete_backup(self, backup_filename: str) -> bool:
        """Belirtilen yedeği siler"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if os.path.exists(backup_path):
                os.remove(backup_path)
                
                # Backup bilgilerinden de kaldır
                self._remove_backup_info(backup_filename)
                
                logging.info(f"Yedek silindi: {backup_filename}")
                return True
            else:
                logging.warning(f"Silinecek yedek bulunamadı: {backup_filename}")
                return False
                
        except Exception as e:
            logging.error(f"Yedek silme hatası: {e}")
            return False
    
    def _save_backup_info(self, backup_info: Dict):
        """Yedek bilgilerini dosyaya kaydeder"""
        try:
            data = {'backups': []}
            
            if os.path.exists(self.backup_info_file):
                with open(self.backup_info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data['backups'].append(backup_info)
            
            with open(self.backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"Yedek bilgisi kaydedilemedi: {e}")
    
    def _remove_backup_info(self, backup_filename: str):
        """Yedek bilgisini listeden kaldırır"""
        try:
            if not os.path.exists(self.backup_info_file):
                return
            
            with open(self.backup_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['backups'] = [b for b in data.get('backups', []) 
                             if b.get('filename') != backup_filename]
            
            with open(self.backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"Yedek bilgisi kaldırılamadı: {e}")
    
    def _cleanup_old_backups(self):
        """Eski yedekleri temizler (maksimum sayıyı aşarsa)"""
        try:
            backups = self.get_backup_list()
            
            if len(backups) > self.max_backups:
                # En eski yedekleri sil
                backups_to_delete = backups[self.max_backups:]
                
                for backup in backups_to_delete:
                    self.delete_backup(backup['filename'])
                    
                logging.info(f"{len(backups_to_delete)} eski yedek temizlendi")
                
        except Exception as e:
            logging.error(f"Eski yedek temizleme hatası: {e}")
    
    def verify_backup(self, backup_filename: str) -> bool:
        """Yedeğin bütünlüğünü kontrol eder"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return False
            
            # Zip dosyasının bütünlüğünü kontrol et
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                bad_file = zipf.testzip()
                if bad_file:
                    logging.error(f"Yedekte bozuk dosya: {bad_file}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Yedek doğrulama hatası: {e}")
            return False
    
    def get_backup_size(self, backup_filename: str) -> int:
        """Yedeğin boyutunu döndürür"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            if os.path.exists(backup_path):
                return os.path.getsize(backup_path)
            return 0
        except:
            return 0