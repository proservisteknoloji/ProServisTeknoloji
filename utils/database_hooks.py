#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProServis Database Hooks
Veritabanı değişikliklerini izlemek için hook sistemi
"""

from typing import Callable, Dict, Any, List
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class DatabaseHookManager:
    """Veritabanı operasyonlarını izleyen hook sistemi"""
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {
            'after_insert': [],
            'after_update': [],
            'after_delete': []
        }
        self.enabled = True
    
    def register_hook(self, event: str, callback: Callable):
        """
        Hook ekle
        
        Args:
            event: 'after_insert', 'after_update', 'after_delete'
            callback: Çağrılacak fonksiyon (table_name, record_id, data)
        """
        if event not in self.hooks:
            raise ValueError(f"Invalid event: {event}")
        
        self.hooks[event].append(callback)
        logger.info(f"Registered hook for {event}")
    
    def trigger(self, event: str, table_name: str, record_id: int, data: Dict = None):
        """Hook'ları tetikle"""
        if not self.enabled:
            return
        
        if event not in self.hooks:
            return
        
        for callback in self.hooks[event]:
            try:
                callback(table_name, record_id, data or {})
            except Exception as e:
                logger.error(f"Hook error ({event}): {e}")
    
    def enable(self):
        """Hook'ları etkinleştir"""
        self.enabled = True
    
    def disable(self):
        """Hook'ları devre dışı bırak (bulk import sırasında)"""
        self.enabled = False
    
    def clear_hooks(self):
        """Tüm hook'ları temizle"""
        for event in self.hooks:
            self.hooks[event].clear()


# Global hook manager
_hook_manager = DatabaseHookManager()


def get_hook_manager() -> DatabaseHookManager:
    """Global hook manager'ı döndür"""
    return _hook_manager


def track_changes(table_name: str):
    """
    Decorator: Veritabanı operasyonlarını izle ve sync kuyruğuna ekle
    
    Kullanım:
        @track_changes('customers')
        def add_customer(self, data):
            cursor.execute("INSERT INTO customers ...")
            return cursor.lastrowid
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Önce orijinal fonksiyonu çalıştır
            result = func(*args, **kwargs)
            
            # Fonksiyon adına göre operasyonu belirle
            func_name = func.__name__.lower()
            
            if 'add' in func_name or 'insert' in func_name or 'create' in func_name:
                operation = 'INSERT'
                record_id = result  # Genelde lastrowid döner
            elif 'update' in func_name or 'edit' in func_name or 'modify' in func_name:
                operation = 'UPDATE'
                # İlk argüman genelde record_id'dir
                record_id = args[1] if len(args) > 1 else kwargs.get('id')
            elif 'delete' in func_name or 'remove' in func_name:
                operation = 'DELETE'
                record_id = args[1] if len(args) > 1 else kwargs.get('id')
            else:
                # Bilinmeyen operasyon, hook tetikleme
                return result
            
            # Hook'u tetikle
            if record_id:
                event_name = f"after_{operation.lower()}"
                data = kwargs.get('data') or (args[1] if len(args) > 1 else {})
                _hook_manager.trigger(event_name, table_name, record_id, data)
            
            return result
        
        return wrapper
    return decorator


def init_sync_hooks(sync_manager):
    """
    Sync manager için hook'ları kaydet
    
    Args:
        sync_manager: SyncManager instance
    """
    hook_manager = get_hook_manager()
    
    # INSERT hook
    def on_insert(table_name: str, record_id: int, data: Dict):
        sync_manager.add_to_sync_queue(table_name, record_id, 'INSERT', data)
    
    # UPDATE hook
    def on_update(table_name: str, record_id: int, data: Dict):
        sync_manager.add_to_sync_queue(table_name, record_id, 'UPDATE', data)
    
    # DELETE hook
    def on_delete(table_name: str, record_id: int, data: Dict):
        sync_manager.add_to_sync_queue(table_name, record_id, 'DELETE', data)
    
    hook_manager.register_hook('after_insert', on_insert)
    hook_manager.register_hook('after_update', on_update)
    hook_manager.register_hook('after_delete', on_delete)
    
    logger.info("Sync hooks initialized")
