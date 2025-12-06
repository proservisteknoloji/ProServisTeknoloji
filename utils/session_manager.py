"""
Session Manager - Kullanıcı oturumu yönetimi (sadece bulut modu için)
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict


class SessionManager:
    """Kullanıcı oturumu yönetimi - Uygulama açık olduğu sürece geçerli"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.session_file = data_dir / 'session.json'
        self.session_data: Optional[Dict] = None
        self._load_session()
    
    def _load_session(self):
        """Mevcut session'ı yükle"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    self.session_data = json.load(f)
                logging.info(f"✅ Session yüklendi: {self.session_data.get('username')}")
            except Exception as e:
                logging.error(f"Session yükleme hatası: {e}")
                self.session_data = None
        else:
            self.session_data = None
    
    def create_session(self, username: str, company_name: str, company_schema: str, role: str = 'User'):
        """Yeni session oluştur (sadece bulut modu için)"""
        self.session_data = {
            'username': username,
            'company_name': company_name,
            'company_schema': company_schema,
            'role': role
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
            logging.info(f"✅ Session oluşturuldu: {username} ({company_name})")
        except Exception as e:
            logging.error(f"Session kaydetme hatası: {e}")
    
    def get_session(self) -> Optional[Dict]:
        """Aktif session'ı döndür"""
        return self.session_data
    
    def has_session(self) -> bool:
        """Aktif session var mı?"""
        return self.session_data is not None
    
    def get_username(self) -> Optional[str]:
        """Session'daki kullanıcı adı"""
        return self.session_data.get('username') if self.session_data else None
    
    def get_company_name(self) -> Optional[str]:
        """Session'daki firma adı"""
        return self.session_data.get('company_name') if self.session_data else None
    
    def get_company_schema(self) -> Optional[str]:
        """Session'daki firma schema"""
        return self.session_data.get('company_schema') if self.session_data else None
    
    def get_role(self) -> Optional[str]:
        """Session'daki rol"""
        return self.session_data.get('role') if self.session_data else None
    
    def clear_session(self):
        """Session'ı temizle (logout)"""
        self.session_data = None
        if self.session_file.exists():
            try:
                self.session_file.unlink()
                logging.info("✅ Session temizlendi (logout)")
            except Exception as e:
                logging.error(f"Session temizleme hatası: {e}")
    
    def update_session(self, **kwargs):
        """Session'ı güncelle"""
        if self.session_data:
            self.session_data.update(kwargs)
            try:
                with open(self.session_file, 'w', encoding='utf-8') as f:
                    json.dump(self.session_data, f, indent=2, ensure_ascii=False)
                logging.info(f"✅ Session güncellendi")
            except Exception as e:
                logging.error(f"Session güncelleme hatası: {e}")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(data_dir: Optional[Path] = None) -> SessionManager:
    """Global session manager instance'ını döndür"""
    global _session_manager
    
    if _session_manager is None:
        if data_dir is None:
            # AppData/Roaming/ProServis dizinini kullan
            import os
            import sys
            if sys.platform == "win32":
                app_data = os.getenv('APPDATA')
            else:
                app_data = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
            
            if not app_data:
                app_data = os.path.dirname(os.path.abspath(__file__))
            
            proservis_dir = os.path.join(app_data, 'ProServis')
            os.makedirs(proservis_dir, exist_ok=True)
            data_dir = Path(proservis_dir)
        
        _session_manager = SessionManager(data_dir)
    
    return _session_manager


def clear_session():
    """Global session'ı temizle"""
    global _session_manager
    if _session_manager:
        _session_manager.clear_session()
        _session_manager = None
