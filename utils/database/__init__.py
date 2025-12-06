"""
Veritabanı yönetimi için merkezi bir arayüz sağlar.

Bu paket, veritabanı işlemlerini yönetmek için `DatabaseManager` sınıfını
ve ilgili sorgu mixin'lerini içerir.

Uygulama genelinde kullanılacak tekil veritabanı nesnesi `db_manager`
doğrudan bu paketten içe aktarılabilir.
"""

from .connection import db_manager

# Bu __init__.py dosyası, `utils.database` paketinden içe aktarım yapıldığında
# `db_manager` nesnesinin kolayca erişilebilir olmasını sağlar.
# Örneğin: `from utils.database import db_manager`