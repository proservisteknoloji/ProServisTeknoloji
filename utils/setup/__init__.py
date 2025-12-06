# utils/setup/__init__.py
"""Kurulum ve lisans yönetim modülleri."""

from .first_run import check_first_run
from .license_manager import check_license

__all__ = [
    'check_first_run',
    'check_license'
]
