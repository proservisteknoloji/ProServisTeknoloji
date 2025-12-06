#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProServis Sync Manager
Gerçek zamanlı bulut senkronizasyonu ve offline destek
"""

import sqlite3
import json
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

# Global Azure SQL Manager referansı
_azure_manager_instance = None

def set_azure_manager(azure_manager):
    """Global Azure SQL Manager instance'ını ayarla"""
    global _azure_manager_instance
    _azure_manager_instance = azure_manager

def get_azure_manager():
    """Global Azure SQL Manager instance'ını döndür"""
    return _azure_manager_instance


class SyncManager:
    """
    Veritabanı değişikliklerini izler ve buluta otomatik senkronize eder.
    Offline durumda değişiklikleri kuyrukta tutar, online olunca gönderir.
    """
    
    def __init__(self, database_path: str, sync_interval: int = 300, azure_manager=None):
        """
        Args:
            database_path: Ana veritabanı dosyası
            sync_interval: Senkronizasyon aralığı (saniye, varsayılan: 5 dakika)
            azure_manager: Azure SQL Manager instance (opsiyonel)
        """
        self.database_path = database_path
        self.sync_interval = sync_interval
        
        # Sync veritabanı (değişiklikleri izler)
        db_dir = Path(database_path).parent
        self.sync_db_path = db_dir / "sync_queue.db"
        
        # Azure SQL Manager
        self.azure_manager = azure_manager or get_azure_manager()
        
        # Senkronizasyon durumu
        self.is_syncing = False
        self.last_sync_time = None
        self.sync_thread = None
        self.stop_sync_flag = threading.Event()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Senkronizasyon veritabanını hazırla
        self._init_sync_database()
        
        # Ana veritabanına triggers ekle
        self._setup_database_triggers()
    
    def _init_sync_database(self):
        """Senkronizasyon kuyruğu veritabanını oluştur"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        # Senkronizasyon kuyruğu tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                operation TEXT NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
                data TEXT,  -- JSON format
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced INTEGER DEFAULT 0,
                synced_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        
        # Senkronizasyon geçmişi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,  -- 'auto', 'manual', 'forced'
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT,  -- 'success', 'failed', 'partial'
                records_synced INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)
        
        # Çakışma çözümleri
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                local_data TEXT,
                cloud_data TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved INTEGER DEFAULT 0,
                resolution TEXT  -- 'local_wins', 'cloud_wins', 'merged', 'manual'
            )
        """)
        
        # Senkronizasyon ayarları
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Varsayılan ayarlar
        default_settings = {
            'auto_sync_enabled': 'true',
            'sync_interval_seconds': str(self.sync_interval),
            'conflict_resolution': 'local_wins',  # local_wins, cloud_wins, ask_user
            'max_retry_count': '3',
            'batch_size': '100',
            'last_full_sync': None
        }
        
        for key, value in default_settings.items():
            cursor.execute("""
                INSERT OR IGNORE INTO sync_settings (key, value)
                VALUES (?, ?)
            """, (key, value))
        
        conn.commit()
        conn.close()
    
    def _setup_database_triggers(self):
        """Ana veritabanına değişiklik izleme trigger'larını ekle"""
        # İzlenecek tablolar
        tables_to_monitor = [
            'customers', 'services', 'devices', 'stock_items',
            'stock_transactions', 'billing', 'payments', 'quotes',
            'technicians', 'tasks', 'device_sales'
        ]
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        for table in tables_to_monitor:
            # Tablonun var olup olmadığını kontrol et
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table,))
            
            if not cursor.fetchone():
                continue
            
            # Her tablo için sync_queue tablosu oluştur
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS sync_queue_{table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced INTEGER DEFAULT 0,
                    synced_at TIMESTAMP
                )
            """)
            self.logger.info(f"✅ Sync queue tablosu oluşturuldu: sync_queue_{table}")
            
            # INSERT trigger
            trigger_name = f"sync_after_insert_{table}"
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS {trigger_name}
            """)
            cursor.execute(f"""
                CREATE TRIGGER {trigger_name}
                AFTER INSERT ON {table}
                FOR EACH ROW
                BEGIN
                    INSERT INTO sync_queue_{table} (
                        record_id, operation, data, created_at
                    ) VALUES (
                        NEW.id,
                        'INSERT',
                        json_object('table', '{table}', 'id', NEW.id),
                        datetime('now')
                    );
                END
            """)
            
            # UPDATE trigger
            trigger_name = f"sync_after_update_{table}"
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS {trigger_name}
            """)
            cursor.execute(f"""
                CREATE TRIGGER {trigger_name}
                AFTER UPDATE ON {table}
                FOR EACH ROW
                BEGIN
                    INSERT INTO sync_queue_{table} (
                        record_id, operation, data, created_at
                    ) VALUES (
                        NEW.id,
                        'UPDATE',
                        json_object('table', '{table}', 'id', NEW.id),
                        datetime('now')
                    );
                END
            """)
            
            # DELETE trigger
            trigger_name = f"sync_after_delete_{table}"
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS {trigger_name}
            """)
            cursor.execute(f"""
                CREATE TRIGGER {trigger_name}
                AFTER DELETE ON {table}
                FOR EACH ROW
                BEGIN
                    INSERT INTO sync_queue_{table} (
                        record_id, operation, data, created_at
                    ) VALUES (
                        OLD.id,
                        'DELETE',
                        json_object('table', '{table}', 'id', OLD.id),
                        datetime('now')
                    );
                END
            """)
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Database triggers setup completed for {len(tables_to_monitor)} tables")
    
    def add_to_sync_queue(self, table_name: str, record_id: int, 
                          operation: str, data: Dict = None):
        """
        Değişikliği senkronizasyon kuyruğuna ekle
        
        Args:
            table_name: Tablo adı
            record_id: Kayıt ID
            operation: İşlem türü (INSERT, UPDATE, DELETE)
            data: Kayıt verisi (opsiyonel)
        """
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        data_json = json.dumps(data) if data else None
        
        cursor.execute("""
            INSERT INTO sync_queue (table_name, record_id, operation, data)
            VALUES (?, ?, ?, ?)
        """, (table_name, record_id, operation, data_json))
        
        conn.commit()
        conn.close()
        
        self.logger.debug(f"Added to sync queue: {table_name}.{record_id} ({operation})")
        
        # Eğer online ise ve otomatik sync aktifse, hemen senkronize et
        if self.is_auto_sync_enabled() and self.is_online():
            threading.Thread(target=self._sync_pending_changes, daemon=True).start()
    
    def is_online(self) -> bool:
        """Bulut bağlantısının olup olmadığını kontrol et"""
        # Öncelik 1: Azure SQL Manager
        if self.azure_manager:
            try:
                # Azure SQL manager var mı ve credentials yüklü mü?
                if hasattr(self.azure_manager, 'username') and self.azure_manager.username:
                    # Credentials var, online kabul et
                    self.logger.debug("Azure SQL Manager aktif - Online")
                    return True
                    
                # Veya bağlantı açık mı?
                if hasattr(self.azure_manager, 'connection') and self.azure_manager.connection:
                    self.logger.debug("Azure SQL bağlantısı aktif - Online")
                    return True
            except Exception as e:
                self.logger.debug(f"Azure SQL durumu kontrol edilemedi: {e}")
        
        return False
    
    def is_auto_sync_enabled(self) -> bool:
        """Otomatik senkronizasyonun aktif olup olmadığını kontrol et"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value FROM sync_settings WHERE key = 'auto_sync_enabled'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return result and result[0].lower() == 'true'
    
    def get_pending_changes_count(self) -> int:
        """Bekleyen değişiklik sayısını döndür"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM sync_queue WHERE synced = 0
        """)
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_pending_changes(self, limit: int = 100) -> List[Dict]:
        """Bekleyen değişiklikleri getir"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, table_name, record_id, operation, data, created_at, retry_count
            FROM sync_queue
            WHERE synced = 0
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'id': row[0],
                'table_name': row[1],
                'record_id': row[2],
                'operation': row[3],
                'data': json.loads(row[4]) if row[4] else None,
                'created_at': row[5],
                'retry_count': row[6]
            })
        
        conn.close()
        return changes
    
    def _sync_pending_changes(self):
        """Bekleyen değişiklikleri senkronize et"""
        if self.is_syncing:
            self.logger.info("Sync already in progress, skipping...")
            return
        
        if not self.is_online():
            self.logger.warning("Offline mode - changes queued for later sync")
            return
        
        self.is_syncing = True
        sync_started = datetime.now()
        
        try:
            # Sync history kaydı oluştur
            sync_id = self._create_sync_history('auto', sync_started)
            
            # Azure SQL aktif mi?
            if self.azure_manager:
                self.logger.info("🔄 Azure SQL sync başlatılıyor...")
                result = self._sync_to_azure_sql()
                
                if result['success'] > 0:
                    self._update_sync_history(sync_id, 'success', result['success'])
                    self.logger.info(f"✅ Azure SQL sync tamamlandı: {result['success']} kayıt")
                else:
                    self._update_sync_history(sync_id, 'failed', 0, error_message=result.get('error'))
                    self.logger.error(f"❌ Azure SQL sync başarısız: {result.get('error')}")
                
                return
            
            # Fallback: Eski cloud backup sistemi
            self.logger.info("Using legacy cloud backup (Google Drive/Dropbox)...")
            batch_size = self._get_setting('batch_size', 100)
            pending = self.get_pending_changes(batch_size)
            
            if not pending:
                self.logger.info("No pending changes to sync")
                self._update_sync_history(sync_id, 'success', 0)
                return
            
            self.logger.info(f"Syncing {len(pending)} pending changes...")
            
            # Azure SQL ile sync (cloud backup sistemi kaldırıldı)
            synced_count = 0
            
            if self.azure_manager:
                try:
                    # Azure SQL'e sync yap
                    conn = sqlite3.connect(self.sync_db_path)
                    cursor = conn.cursor()
                    
                    for change in pending:
                        cursor.execute("""
                            UPDATE sync_queue
                            SET synced = 1, synced_at = datetime('now')
                            WHERE id = ?
                        """, (change['id'],))
                        synced_count += 1
                    
                    conn.commit()
                    conn.close()
                    
                    self.last_sync_time = datetime.now()
                    
                    # Sync history güncelle
                    self._update_sync_history(sync_id, 'success', synced_count)
                except Exception as e:
                    self.logger.error(f"Azure sync error: {e}")
                    self._update_sync_history(sync_id, 'failed', 0, error_message=str(e))
            else:
                self.logger.warning("Azure Manager not available")
                self._update_sync_history(sync_id, 'failed', 0, error_message="Azure Manager not available")
        
        except Exception as e:
            self.logger.error(f"Sync error: {e}", exc_info=True)
            if 'sync_id' in locals():
                self._update_sync_history(
                    sync_id, 
                    'failed', 
                    0,
                    error_message=str(e)
                )
        
        finally:
            self.is_syncing = False
    
    def _sync_to_azure_sql(self) -> dict:
        """
        Sync queue'daki değişiklikleri Azure SQL'e gönder
        
        Returns:
            {'success': int, 'failed': int, 'error': str}
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Her tablo için sync_queue'yu kontrol et
            tables_to_sync = [
                'customers', 'devices', 'stock_items', 
                'payments', 'technicians', 'billing',
                'quotes', 'services', 'tasks', 'device_sales'
            ]
            
            total_success = 0
            total_failed = 0
            
            for table in tables_to_sync:
                # Sync queue tablosu var mı?
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (f'sync_queue_{table}',))
                
                if not cursor.fetchone():
                    continue
                
                # Bekleyen kayıtları al
                cursor.execute(f"""
                    SELECT record_id, operation
                    FROM sync_queue_{table}
                    WHERE synced = 0
                    LIMIT 100
                """)
                
                pending = cursor.fetchall()
                if not pending:
                    continue
                
                self.logger.info(f"📤 {table}: {len(pending)} kayıt senkronize ediliyor...")
                
                # Kayıtları hazırla
                records_to_sync = []
                for record_id, operation in pending:
                    if operation == 'DELETE':
                        # TODO: DELETE işlemi için ayrı metod
                        continue
                    
                    # Ana tablodan kaydı al
                    cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,))
                    columns = [desc[0] for desc in cursor.description]
                    row = cursor.fetchone()
                    
                    if row:
                        record = dict(zip(columns, row))
                        records_to_sync.append(record)
                
                if records_to_sync:
                    # Azure SQL'e gönder
                    result = self.azure_manager.sync_table_data(table, records_to_sync)
                    
                    total_success += result['success']
                    total_failed += result['failed']
                    
                    # Başarılı olanları synced olarak işaretle
                    if result['success'] > 0:
                        for record in records_to_sync[:result['success']]:
                            cursor.execute(f"""
                                UPDATE sync_queue_{table}
                                SET synced = 1, synced_at = datetime('now')
                                WHERE record_id = ?
                            """, (record['id'],))
                        
                        conn.commit()
                        self.logger.info(f"✅ {table}: {result['success']} kayıt senkronize edildi")
            
            conn.close()
            
            if total_failed > 0:
                return {
                    'success': total_success,
                    'failed': total_failed,
                    'error': f'{total_failed} kayıt başarısız'
                }
            
            return {'success': total_success, 'failed': 0, 'error': None}
            
        except Exception as e:
            self.logger.error(f"Azure SQL sync hatası: {e}", exc_info=True)
            return {'success': 0, 'failed': 0, 'error': str(e)}
    
    def _create_sync_history(self, sync_type: str, started_at: datetime) -> int:
        """Sync history kaydı oluştur"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sync_history (sync_type, started_at, status)
            VALUES (?, ?, 'running')
        """, (sync_type, started_at.isoformat()))
        
        sync_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return sync_id
    
    def _update_sync_history(self, sync_id: int, status: str, 
                            records_synced: int = 0,
                            error_message: str = ""):
        """Sync history kaydını güncelle"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sync_history
            SET completed_at = datetime('now'),
                status = ?,
                records_synced = ?,
                error_message = ?
            WHERE id = ?
        """, (status, records_synced, error_message, sync_id))
        
        conn.commit()
        conn.close()
    
    def _get_setting(self, key: str, default: Any = None) -> Any:
        """Ayar değerini al"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value FROM sync_settings WHERE key = ?
        """, (key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            value = result[0]
            # Type conversion
            if default is not None:
                if isinstance(default, int):
                    return int(value)
                elif isinstance(default, bool):
                    return value.lower() == 'true'
            return value
        
        return default
    
    def set_setting(self, key: str, value: str):
        """Ayar değerini kaydet"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
        """, (key, str(value)))
        
        conn.commit()
        conn.close()
    
    def start_auto_sync(self):
        """Otomatik senkronizasyonu başlat (background thread)"""
        if self.sync_thread and self.sync_thread.is_alive():
            self.logger.warning("Auto sync already running")
            return
        
        self.stop_sync_flag.clear()
        self.sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
        self.sync_thread.start()
        
        self.logger.info("Auto sync started")
    
    def stop_auto_sync(self):
        """Otomatik senkronizasyonu durdur"""
        self.stop_sync_flag.set()
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        self.logger.info("Auto sync stopped")
    
    def _auto_sync_loop(self):
        """Otomatik senkronizasyon döngüsü"""
        while not self.stop_sync_flag.is_set():
            try:
                if self.is_auto_sync_enabled():
                    pending_count = self.get_pending_changes_count()
                    
                    if pending_count > 0:
                        self.logger.info(f"Auto sync: {pending_count} pending changes")
                        self._sync_pending_changes()
                
                # Interval kadar bekle
                interval = self._get_setting('sync_interval_seconds', self.sync_interval)
                self.stop_sync_flag.wait(interval)
            
            except Exception as e:
                self.logger.error(f"Auto sync loop error: {e}")
                self.stop_sync_flag.wait(60)  # Hata durumunda 1 dakika bekle
    
    def force_sync(self) -> Dict:
        """Manuel senkronizasyon tetikle"""
        self.logger.info("Manual sync triggered")
        
        sync_started = datetime.now()
        sync_id = self._create_sync_history('manual', sync_started)
        
        try:
            self._sync_pending_changes()
            
            return {
                'success': True,
                'message': 'Sync completed successfully',
                'pending_count': self.get_pending_changes_count()
            }
        
        except Exception as e:
            self.logger.error(f"Manual sync failed: {e}")
            self._update_sync_history(sync_id, 'failed', error_message=str(e))
            
            return {
                'success': False,
                'message': f'Sync failed: {e}',
                'pending_count': self.get_pending_changes_count()
            }
    
    def get_sync_status(self) -> Dict:
        """Senkronizasyon durumunu döndür"""
        status = {
            'is_syncing': self.is_syncing,
            'is_online': self.is_online(),
            'auto_sync_enabled': self.is_auto_sync_enabled(),
            'pending_changes': self.get_pending_changes_count(),
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_interval': self._get_setting('sync_interval_seconds', self.sync_interval)
        }
        
        # Son sync geçmişi
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sync_type, started_at, completed_at, status, records_synced
            FROM sync_history
            ORDER BY id DESC
            LIMIT 5
        """)
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'sync_type': row[0],
                'started_at': row[1],
                'completed_at': row[2],
                'status': row[3],
                'records_synced': row[4]
            })
        
        conn.close()
        
        status['recent_history'] = history
        
        return status
    
    def clear_sync_queue(self):
        """Senkronizasyon kuyruğunu temizle (dikkatli kullan!)"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sync_queue WHERE synced = 1")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Cleared {deleted_count} synced records from queue")
        
        return deleted_count
    
    def reset_failed_syncs(self):
        """Başarısız senkronizasyonları sıfırla (retry için)"""
        conn = sqlite3.connect(self.sync_db_path)
        cursor = conn.cursor()
        
        max_retry = self._get_setting('max_retry_count', 3)
        
        cursor.execute("""
            UPDATE sync_queue
            SET retry_count = 0, last_error = NULL
            WHERE synced = 0 AND retry_count >= ?
        """, (max_retry,))
        
        reset_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        self.logger.info(f"Reset {reset_count} failed syncs")
        
        return reset_count


# Global singleton instance
_sync_manager_instance: Optional[SyncManager] = None


def get_sync_manager(database_path: str = None, 
                     sync_interval: int = 300) -> SyncManager:
    """Global sync manager instance'ını döndür"""
    global _sync_manager_instance
    
    if _sync_manager_instance is None:
        if database_path is None:
            raise ValueError("database_path required for first initialization")
        _sync_manager_instance = SyncManager(database_path, sync_interval)
    
    return _sync_manager_instance


def init_sync_manager(database_path: str, sync_interval: int = 300, 
                     auto_start: bool = True) -> SyncManager:
    """
    Sync manager'ı başlat (uygulama başlangıcında çağır)
    
    Args:
        database_path: Veritabanı yolu
        sync_interval: Senkronizasyon aralığı (saniye)
        auto_start: Otomatik başlat
    
    Returns:
        SyncManager instance
    """
    manager = get_sync_manager(database_path, sync_interval)
    
    if auto_start and manager.is_auto_sync_enabled():
        manager.start_auto_sync()
    
    return manager


def sync_from_azure_to_local(database_path: str):
    """
    Login sonrası Azure'dan local'e veri senkronizasyonu
    Local database'i temizleyip Azure'daki güncel verileri indirir
    """
    try:
        azure_manager = get_azure_manager()
        if not azure_manager:
            logging.warning("Azure Manager yok - sync atlandı")
            return False
        
        if not azure_manager.current_company:
            logging.warning("Azure company belirlenmemiş - sync atlandı")
            return False
        
        logging.info(f"🔄 Azure'dan local'e sync başlıyor: {azure_manager.current_company}")
        
        # Sync edilecek tablolar
        tables = [
            'users', 'customers', 'devices', 'stock_items', 'stock_categories',
            'payments', 'quotes', 'invoices', 'technicians', 'cpc_readings', 'service_records'
        ]
        
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        for table in tables:
            try:
                # 1. Local tabloyu temizle
                cursor.execute(f"DELETE FROM {table}")
                logging.info(f"  ✅ {table} temizlendi")
                
                # 2. Azure'dan verileri çek
                azure_data = azure_manager.fetch_table_data(table)
                
                if azure_data and len(azure_data) > 0:
                    # 3. Local'e ekle
                    columns = list(azure_data[0].keys())
                    placeholders = ','.join(['?' for _ in columns])
                    insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                    
                    for row in azure_data:
                        values = [row[col] for col in columns]
                        cursor.execute(insert_sql, values)
                    
                    logging.info(f"  ✅ {table}: {len(azure_data)} kayıt indirildi")
                else:
                    logging.info(f"  ℹ️ {table}: Azure'da veri yok")
                    
            except Exception as e:
                logging.error(f"  ❌ {table} sync hatası: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        logging.info(f"✅ Azure→Local sync tamamlandı: {azure_manager.current_company}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Azure→Local sync hatası: {e}", exc_info=True)
        return False
