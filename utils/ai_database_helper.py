"""
AI Database Helper

Veritabanı sorgularını AI için context olarak hazırlar.
"""

from typing import Optional
from datetime import datetime, timedelta
import logging


class AIDatabaseHelper:
    """Veritabanı sorgularını AI için context olarak hazırlar"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        
    def get_context_for_question(self, question: str) -> Optional[str]:
        """
        Soruya göre ilgili veritabanı bilgilerini context olarak hazırlar.
        
        Args:
            question: Kullanıcının sorusu
            
        Returns:
            Context string veya None
        """
        question_lower = question.lower()
        
        # Servis kayıtları sorguları
        if any(word in question_lower for word in ['servis', 'kayıt', 'işlem', 'bugün', 'dün', 'hafta']):
            return self._get_recent_service_records_context(question_lower)
        
        # Müşteri sorguları
        if 'müşteri' in question_lower or 'firma' in question_lower:
            return self._get_customer_context(question_lower)
        
        # CPC sorguları
        if 'cpc' in question_lower or 'kopyabaşı' in question_lower or 'fatura' in question_lower:
            return self._get_cpc_context()
        
        # Arıza kodu sorguları - context gerekmez, AI direkt cevaplar
        if any(word in question_lower for word in ['arıza', 'hata', 'kod', 'error']):
            return None
        
        return None
    
    def _get_recent_service_records_context(self, question: str) -> str:
        """Son servis kayıtlarını context olarak hazırlar"""
        try:
            # Zaman aralığını belirle
            days = 7  # Varsayılan
            if 'bugün' in question:
                days = 1
            elif 'dün' in question:
                days = 2
            elif 'hafta' in question or '7 gün' in question:
                days = 7
            elif 'ay' in question or '30 gün' in question:
                days = 30
            
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            records = self.db.fetch_all("""
                SELECT 
                    sr.id,
                    sr.created_date,
                    c.name as customer_name,
                    cd.device_model,
                    cd.serial_number,
                    sr.problem_description,
                    sr.notes,
                    sr.status
                FROM service_records sr
                LEFT JOIN customer_devices cd ON sr.device_id = cd.id
                LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                LEFT JOIN customers c ON cl.customer_id = c.id
                WHERE sr.created_date >= ?
                ORDER BY sr.created_date DESC
                LIMIT 20
            """, (start_date,))
            
            if not records:
                return f"Son {days} günde hiç servis kaydı bulunamadı."
            
            context = f"Son {days} günde {len(records)} servis kaydı bulundu:\n\n"
            for rec in records:
                context += f"- {rec['created_date']}: {rec['customer_name']} - {rec['device_model']} ({rec['serial_number']})\n"
                if rec['problem_description']:
                    context += f"  Arıza: {rec['problem_description'][:100]}\n"
                context += f"  Durum: {rec['status']}\n\n"
            
            return context
            
        except Exception as e:
            logging.error(f"Servis kayıtları context hatası: {e}")
            return "Servis kayıtları sorgulanırken hata oluştu."
    
    def _get_customer_context(self, question: str) -> Optional[str]:
        """Müşteri bilgilerini context olarak hazırlar"""
        try:
            # Soru içinde müşteri adı var mı kontrol et
            customers = self.db.fetch_all("SELECT id, name FROM customers LIMIT 100")
            
            customer_id = None
            for customer in customers:
                if customer['name'].lower() in question:
                    customer_id = customer['id']
                    break
            
            if not customer_id:
                # Genel müşteri istatistikleri
                total_customers = self.db.fetch_one("SELECT COUNT(*) as count FROM customers")
                
                # CPC müşteri sayısı (customer_devices üzerinden)
                cpc_customers_count = self.db.fetch_one("""
                    SELECT COUNT(DISTINCT c.id) as count 
                    FROM customers c
                    INNER JOIN customer_locations cl ON c.id = cl.customer_id
                    INNER JOIN customer_devices cd ON cl.id = cd.location_id
                    WHERE cd.is_cpc = 1
                """)
                
                return f"Toplam {total_customers['count']} müşteri var. Bunların {cpc_customers_count['count']} tanesinin CPC cihazı var."
            
            # Belirli müşteri için detaylı bilgi
            customer = self.db.fetch_one("SELECT * FROM customers WHERE id = ?", (customer_id,))
            
            # Son işlemler
            recent_services = self.db.fetch_all("""
                SELECT sr.created_date, cd.device_model, sr.problem_description, sr.status
                FROM service_records sr
                LEFT JOIN customer_devices cd ON sr.device_id = cd.id
                LEFT JOIN customer_locations cl ON cd.location_id = cl.id
                WHERE cl.customer_id = ?
                ORDER BY sr.created_date DESC
                LIMIT 10
            """, (customer_id,))
            
            context = f"Müşteri: {customer['name']}\n"
            context += f"Telefon: {customer.get('phone', 'Yok')}\n\n"
            
            if recent_services:
                context += f"Son {len(recent_services)} işlem:\n"
                for svc in recent_services:
                    desc = svc['problem_description'] or 'Açıklama yok'
                    context += f"- {svc['created_date']}: {svc['device_model']} - {desc[:80]}\n"
            
            return context
            
        except Exception as e:
            logging.error(f"Müşteri context hatası: {e}")
            return "Müşteri bilgileri sorgulanırken hata oluştu."
    
    def _get_cpc_context(self) -> str:
        """CPC bilgilerini context olarak hazırlar"""
        try:
            # CPC cihazı olan müşteriler
            cpc_customers = self.db.fetch_all("""
                SELECT c.name, COUNT(cd.id) as device_count
                FROM customers c
                INNER JOIN customer_locations cl ON c.id = cl.customer_id
                INNER JOIN customer_devices cd ON cl.id = cd.location_id
                WHERE cd.is_cpc = 1
                GROUP BY c.id
                LIMIT 10
            """)
            
            if not cpc_customers:
                return "Henüz CPC müşterisi bulunmuyor."
            
            context = f"CPC (Kopyabaşı) Müşterileri:\n\n"
            for cust in cpc_customers:
                context += f"- {cust['name']}: {cust['device_count']} cihaz\n"
            
            context += "\n**CPC Faturası Oluşturma:**\n"
            context += "1. Sayaç Okuma sekmesinden müşteri seçin\n"
            context += "2. Cihaz sayaç değerlerini girin\n"
            context += "3. 'Fatura Oluştur' butonuna tıklayın\n"
            
            return context
            
        except Exception as e:
            logging.error(f"CPC context hatası: {e}")
            return "CPC bilgileri sorgulanırken hata oluştu."
