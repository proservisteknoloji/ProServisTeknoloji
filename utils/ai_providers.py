"""
AI Provider Base Class ve Implementasyonları

Bu modül, farklı AI sağlayıcılarını destekler.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

class AIProvider(ABC):
    """AI sağlayıcı için base class"""
    
    @abstractmethod
    def ask(self, question: str, context: Optional[str] = None) -> str:
        """
        AI'ya soru sorar ve cevap alır.
        
        Args:
            question: Kullanıcının sorusu
            context: Ek bağlam bilgisi (veritabanı sorguları vb.)
            
        Returns:
            AI'nın cevabı
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Provider'ın kullanılabilir olup olmadığını kontrol eder"""
        pass


class SimpleRuleBasedProvider(AIProvider):
    """Basit kural tabanlı provider (Tamamen ücretsiz, API key gerektirmez, veritabanı okur)"""
    
    def __init__(self):
        self._available = True
        # Arıza kodları veritabanı
        self.error_codes = {
            'C2557': 'Fuser ünitesi sıcaklık sensörü hatası. Fuser ünitesini kontrol edin ve gerekirse değiştirin.',
            'C2558': 'Fuser ünitesi aşırı ısınma hatası. Fuser lamba ve termostatı kontrol edin.',
            'C0660': 'Toner sensörü hatası. Toner kartuşunu çıkarıp tekrar takın.',
            'C0840': 'Kağıt sıkışması sensörü hatası. Kağıt yolunu temizleyin.',
            'C1003': 'Drum ünitesi hatası. Drum ünitesini değiştirin.',
            'C2801': 'Tarayıcı motoru hatası. Tarayıcı ünitesini kontrol edin.',
            'J1001': 'Kağıt sıkışması (Tray 1). Kağıt yolunu kontrol edin.',
            'J2001': 'Kağıt sıkışması (Tray 2). Kağıt yolunu kontrol edin.',
        }
        
    def is_available(self) -> bool:
        """Her zaman kullanılabilir"""
        return True
    
    def ask(self, question: str, context: Optional[str] = None) -> str:
        """Kural tabanlı cevap üretir - veritabanı bilgilerini kullanır"""
        question_lower = question.lower()
        
        # Arıza kodu sorguları
        for code, solution in self.error_codes.items():
            if code.lower() in question_lower:
                return f"**{code} Arıza Kodu:**\n\n{solution}\n\n**Genel Çözüm Adımları:**\n1. Makineyi kapatıp 30 saniye bekleyin\n2. İlgili ünitey kontrol edin\n3. Gerekirse parça değişimi yapın\n4. Makineyi yeniden başlatın"
        
        # Genel arıza kodu sorusu
        if 'arıza' in question_lower or 'hata' in question_lower or 'kod' in question_lower:
            return "Arıza kodu belirtirseniz size yardımcı olabilirim. Örneğin: 'C2557 arıza kodu nedir?'\n\n**Bilinen Arıza Kodları:**\n" + "\n".join([f"- {code}: {sol[:50]}..." for code, sol in list(self.error_codes.items())[:5]])
        
        # Veritabanı sorguları - context varsa kullan
        if context:
            if 'servis' in question_lower or 'kayıt' in question_lower:
                return f"**Servis Kayıtları:**\n\n{context}\n\nDaha detaylı bilgi için ilgili kayıtları inceleyebilirsiniz."
            
            if 'müşteri' in question_lower:
                return f"**Müşteri Bilgileri:**\n\n{context}"
            
            if 'cpc' in question_lower or 'fatura' in question_lower:
                return f"**CPC Bilgileri:**\n\n{context}"
        
        # CPC fatura oluşturma
        if 'cpc' in question_lower and 'fatura' in question_lower:
            return """**CPC Faturası Nasıl Oluşturulur:**

1. **Sayaç Okuma Sekmesi:**
   - Müşteri seçin
   - Cihaz sayaç değerlerini girin
   - Kaydet butonuna tıklayın

2. **Fatura Oluşturma:**
   - 'Sayaç Faturalandır' sekmesine gidin
   - Müşteri ve tarih aralığını seçin
   - 'Fatura Oluştur' butonuna tıklayın

3. **Fatura İnceleme:**
   - 'Faturalar' sekmesinden oluşturulan faturayı görüntüleyin
   - PDF olarak indirebilirsiniz"""
        
        # Fuser hatası
        if 'fuser' in question_lower:
            return """**Fuser Hatası Çözümleri:**

1. **Sıcaklık Sensörü Hatası (C2557):**
   - Fuser ünitesini kontrol edin
   - Sıcaklık sensörünü test edin
   - Gerekirse fuser ünitesini değiştirin

2. **Aşırı Isınma (C2558):**
   - Fuser lambayı kontrol edin
   - Termostatı test edin
   - Havalandırmayı kontrol edin

3. **Genel Kontroller:**
   - Fuser ünitesi temizliği
   - Kağıt kalitesi
   - Voltaj kontrolü"""
        
        # Kağıt sıkışması
        if 'kağıt' in question_lower and ('sıkış' in question_lower or 'jam' in question_lower):
            return """**Kağıt Sıkışması Çözümleri:**

1. **Kağıt Yolunu Kontrol Edin:**
   - Tüm kapakları açın
   - Sıkışan kağıdı yavaşça çıkarın
   - Kağıt sensörlerini temizleyin

2. **Kağıt Kalitesi:**
   - Doğru kağıt gramajı kullanın
   - Nemli kağıt kullanmayın
   - Kağıtları düzgün yerleştirin

3. **Tekrarlayan Sıkışma:**
   - Pickup roller temizliği
   - Separation pad değişimi
   - Kağıt yolu ayarları"""
        
        # Varsayılan cevap
        return """Merhaba! Size nasıl yardımcı olabilirim?

**Yapabileceklerim:**
- 🔧 Arıza kodu sorgulama (Örn: "C2557 nedir?")
- 📊 Servis kayıtları (Örn: "Bugün kaç servis kaydı girildi?")
- 👥 Müşteri bilgileri (Örn: "ABC Şirketi'ne ne işlemler yapıldı?")
- 💰 CPC fatura bilgileri (Örn: "CPC faturası nasıl oluşturulur?")
- 🛠️ Teknik destek (Örn: "Fuser hatası nasıl giderilir?")

Lütfen sorunuzu sorun!"""


class GeminiProvider(AIProvider):
    """Google Gemini API provider (API key gerektirir)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model_name = "gemini-pro"
        self._available = None
        
    def set_api_key(self, api_key: str):
        """API key'i ayarlar"""
        self.api_key = api_key
        self._available = None
        
    def is_available(self) -> bool:
        """Gemini API'nin kullanılabilir olup olmadığını kontrol eder"""
        if not self.api_key:
            return False
            
        if self._available is not None:
            return self._available
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            # Basit bir test sorgusu
            model.generate_content("test")
            self._available = True
            logging.info("Gemini provider kullanılabilir")
            return True
        except Exception as e:
            logging.warning(f"Gemini provider kullanılamıyor: {e}")
            self._available = False
            return False
    
    def ask(self, question: str, context: Optional[str] = None) -> str:
        """Gemini API'ye soru sorar"""
        if not self.api_key:
            return "Gemini kullanmak için API key girmeniz gerekiyor."
            
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            
            # Prompt hazırla
            if context:
                prompt = f"""Sen bir teknik servis asistanısın. Fotokopi makineleri, yazıcılar ve arıza kodları konusunda uzmansın.

Bağlam bilgisi:
{context}

Kullanıcı sorusu: {question}

Lütfen yukarıdaki bağlam bilgisini kullanarak soruyu Türkçe olarak cevapla. Kısa, öz ve profesyonel bir cevap ver."""
            else:
                prompt = f"""Sen bir teknik servis asistanısın. Fotokopi makineleri, yazıcılar ve arıza kodları konusunda uzmansın.

Kullanıcı sorusu: {question}

Lütfen soruyu Türkçe olarak cevapla. Kısa, öz ve profesyonel bir cevap ver."""
            
            response = model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logging.error(f"Gemini API hatası: {e}")
            return f"Üzgünüm, şu anda cevap veremiyorum. Hata: {str(e)}"


class AIProviderFactory:
    """AI provider oluşturmak için factory class"""
    
    @staticmethod
    def create_provider(provider_type: str, api_key: Optional[str] = None) -> AIProvider:
        """
        Belirtilen tipte AI provider oluşturur.
        
        Args:
            provider_type: 'simple' veya 'gemini'
            api_key: Gemini için API key (opsiyonel)
            
        Returns:
            AIProvider instance
        """
        if provider_type.lower() == 'gemini':
            return GeminiProvider(api_key)
        else:
            return SimpleRuleBasedProvider()
