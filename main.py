import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from datetime import datetime
from dotenv import load_dotenv
from time import perf_counter

# .env dosyasını yükle (varsayılan SMTP ayarları için)
load_dotenv()

def setup_program_directories():
    app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    program_data = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'))
    use_programdata = False
    try:
        proservis_data = program_data / 'ProServis'
        test_dir = proservis_data / 'test'
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / 'write_test.txt'
        test_file.write_text('test', encoding='utf-8')
        test_file.unlink()
        test_dir.rmdir()
        use_programdata = True
    except (PermissionError, OSError):
        pass
    if use_programdata:
        base_dir = program_data / 'ProServis'
    else:
        base_dir = app_dir / 'data'
    directories = [
        base_dir,
        base_dir / 'database',
        base_dir / 'backups',
        base_dir / 'logs',
        base_dir / 'temp',
        base_dir / 'cloud'
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return base_dir

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    import traceback
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        import logging
        logging.getLogger('global').error(f"GLOBAL EXCEPTION: {error_msg}")
    except Exception:
        pass

sys.excepthook = handle_exception

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

PROSERVIS_DATA_DIR = setup_program_directories()

from utils.logging_config import setup_logging

setup_logging(Path(PROSERVIS_DATA_DIR) / 'logs', os.getenv('PROSERVIS_LOG_LEVEL', 'INFO'))

import logging
logger = logging.getLogger(__name__)

from utils.config import STYLESHEET
from utils.settings_manager import load_app_config, save_app_config
from ui.main_window import MainWindow
from ui.dialogs.login_dialog import LoginDialog
from utils.database import db_manager
from utils.setup import check_first_run, check_license

def main():
    perf_enabled = os.getenv("PROSERVIS_PERF_LOG") == "1"
    t0 = perf_counter()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    if perf_enabled:
        logger.info(f"[PERF] QApplication init: {(perf_counter() - t0) * 1000:.1f} ms")
    
    first_run_success, first_user_info, is_existing_user = check_first_run()
    if not first_run_success:
        sys.exit(1)
    if not is_existing_user:
        if not check_license():
            sys.exit(0)
    if perf_enabled:
        logger.info(f"[PERF] First-run/license: {(perf_counter() - t0) * 1000:.1f} ms")
            
    try:
        if not db_manager.get_connection():
            raise Exception("Veritabanına bağlanılamadı!")
    except Exception as e:
        QMessageBox.critical(None, "Veritabanı Hatası", f"Veritabanı yüklenemedi:\n{str(e)}")
        sys.exit(1)

    if perf_enabled:
        logger.info(f"[PERF] DB connect/migrations: {(perf_counter() - t0) * 1000:.1f} ms")
        

    logged_in_user = ""
    logged_in_role = ""
    if first_user_info:
        logged_in_user = first_user_info['username']
        logged_in_role = 'admin'
    else:
        login_dialog = LoginDialog(db_manager)
        if login_dialog.exec():
            logged_in_user = login_dialog.logged_in_user or ""
            logged_in_role = login_dialog.logged_in_role or ""
        else:
            sys.exit(0)
            
    window = MainWindow(db_manager, logged_in_user, logged_in_role)
    window.show()
    window.raise_()
    window.activateWindow()
    if perf_enabled:
        logger.info(f"[PERF] Main window show: {(perf_counter() - t0) * 1000:.1f} ms")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
