# -*- mode: python ; coding: utf-8 -*-
# ProServis v2.3.0 - PyInstaller Build Specification
# TEK DOSYA EXE BUILD - Tüm bağımlılıklar dahil

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# PyMuPDF (fitz) için tüm dosyaları topla
fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('fitz')
pymupdf_datas, pymupdf_binaries, pymupdf_hiddenimports = collect_all('pymupdf')

# Ek data dosyalarını topla
added_datas = [
    ('resources', 'resources'),
    ('resources/fonts', 'resources/fonts'),
]

# PyMuPDF data dosyalarını ekle
added_datas.extend(fitz_datas)
added_datas.extend(pymupdf_datas)

# .env dosyası varsa ekle
if os.path.exists('.env'):
    added_datas.append(('.env', '.'))

# ProServis.ico varsa ekle  
if os.path.exists('ProServis.ico'):
    added_datas.append(('ProServis.ico', '.'))

# credentials klasörü varsa ekle
if os.path.exists('credentials'):
    added_datas.append(('credentials', 'credentials'))

# Binary dosyalar
added_binaries = []
added_binaries.extend(fitz_binaries)
added_binaries.extend(pymupdf_binaries)

# Tüm gerekli modülleri topla
hidden_imports = [
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtCharts',
    'PyQt6.sip',
    
    # Veritabanı
    'sqlite3',
    'pyodbc',
    
    # PDF ve Raporlama
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'reportlab.lib.units',
    'reportlab.lib.colors',
    'reportlab.lib.utils',
    'reportlab.lib.rl_accel',
    'reportlab.platypus',
    'reportlab.platypus.flowables',
    'reportlab.platypus.tables',
    'reportlab.platypus.paragraph',
    'reportlab.pdfbase',
    'reportlab.pdfbase.ttfonts',
    'reportlab.pdfbase.pdfmetrics',
    'reportlab.graphics',
    'reportlab.graphics.shapes',
    
    # PDF Okuma ve Yazdırma
    'PyPDF2',
    'fitz',
    'pymupdf',
    
    # Görüntü İşleme
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    
    # Veri İşleme
    'pandas',
    'pandas.core',
    'pandas.io',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    
    # Şifreleme ve Güvenlik
    'bcrypt',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.hazmat.backends',
    
    # HTTP ve API
    'requests',
    'urllib3',
    
    # AI Providers (opsiyonel)
    'openai',
    'google',
    'google.generativeai',
    
    # Sistem
    'psutil',
    'wmi',
    'win32api',
    'win32con',
    'win32gui',
    'win32print',
    'pythoncom',
    'pywintypes',
    
    # Ortam Değişkenleri
    'dotenv',
    
    # Web Scraping
    'lxml',
    'bs4',
    
    # Email
    'smtplib',
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    
    # JSON ve Logging
    'json',
    'logging',
    
    # Uygulama modülleri
    'utils',
    'utils.config',
    'utils.database',
    'utils.ai_providers',
    'utils.pdf_generator',
    'utils.email_generator',
    'utils.settings_manager',
    'utils.sync_manager',
    'utils.auto_backup',
    'utils.system_notifier',
    'utils.currency_converter',
    'utils.validator',
    'utils.error_logger',
    'ui',
    'ui.main_window',
    'ui.dialogs',
    'ui.stock',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=added_binaries,
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy.distutils',
        'tkinter',
        '_tkinter',
        'tcl',
        'tk',
        'test',
        'unittest',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    name='ProServis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Terminal ekrani olmadan
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ProServis.ico',
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProServis',
)
