# ui/ai_tab.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QMessageBox, QLineEdit, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from utils.database import db_manager
from utils.workers import AIThread, OPENAI_AVAILABLE, GEMINI_AVAILABLE
from utils.error_codes import get_error_description, format_error_response

class AITab(QWidget):
    """Yapay zeka destekli çözüm önerileri sunan sekme - Arıza kodu analizi."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.ai_thread = None
        self.init_ui()
        self.check_activation()

    def init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QVBoxLayout(self)
        
        # Bilgilendirme
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("padding: 10px; background: #e3f2fd; border-radius: 5px;")
        layout.addWidget(self.info_label)
        
        # Arıza Kodu Girişi
        code_group = QGroupBox("🔧 Arıza Kodu Analizi")
        code_layout = QVBoxLayout()
        
        code_input_layout = QHBoxLayout()
        code_input_layout.addWidget(QLabel("Arıza Kodu:"))
        self.error_code_input = QLineEdit()
        self.error_code_input.setPlaceholderText("Örn: C6000, F2-10, J7-00")
        code_input_layout.addWidget(self.error_code_input)
        
        code_input_layout.addWidget(QLabel("Cihaz Markası:"))
        self.brand_combo = QComboBox()
        self.brand_combo.addItems(["Kyocera", "Canon", "HP", "Ricoh", "Xerox", "Konica Minolta", "Brother", "Epson", "Diğer"])
        code_input_layout.addWidget(self.brand_combo)
        
        self.analyze_code_btn = QPushButton("🔍 Kodu Analiz Et")
        self.analyze_code_btn.setStyleSheet("background: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        code_input_layout.addWidget(self.analyze_code_btn)
        
        code_layout.addLayout(code_input_layout)
        code_group.setLayout(code_layout)
        layout.addWidget(code_group)
        
        # Genel Soru
        question_group = QGroupBox("💬 Genel Teknik Soru")
        question_layout = QVBoxLayout()
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Örn: Kyocera M2040dn fuser hatası veriyor, ne yapmalıyım?")
        self.prompt_input.setMaximumHeight(100)
        question_layout.addWidget(self.prompt_input)
        
        self.ask_btn = QPushButton("💡 Sor")
        self.ask_btn.setStyleSheet("background: #2196F3; color: white; padding: 8px; font-weight: bold;")
        question_layout.addWidget(self.ask_btn)
        
        question_group.setLayout(question_layout)
        layout.addWidget(question_group)
        
        # Cevap
        layout.addWidget(QLabel("📋 Çözüm Önerisi:"))
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setStyleSheet("background: #f5f5f5; border: 1px solid #ddd; padding: 10px;")
        layout.addWidget(self.response_output)
        
        self._connect_signals()

    def _connect_signals(self):
        """Sinyalleri slotlara bağlar."""
        self.ask_btn.clicked.connect(self.get_ai_response)
        self.analyze_code_btn.clicked.connect(self.analyze_error_code)

    def check_activation(self):
        """
        Seçili AI sağlayıcısına göre sekmenin aktif olup olmadığını kontrol eder
        ve kullanıcıya bilgilendirme mesajı gösterir.
        """
        try:
            if not self.db or not self.db.get_connection():
                raise ConnectionError("Veritabanı bağlantısı kurulamadı.")

            provider = self.db.get_setting('ai_provider', 'OpenAI')
            api_key = None
            library_available = False

            if provider == "OpenAI":
                api_key = self.db.get_setting('openai_api_key')
                library_available = OPENAI_AVAILABLE
            elif provider == "Google Gemini":
                api_key = self.db.get_setting('gemini_api_key')
                library_available = GEMINI_AVAILABLE

            if library_available and api_key:
                self.setEnabled(True)
                self.info_label.setText(f"Aktif model: <b>{provider}</b>. Teknik sorununuzu veya arıza kodunu yazarak çözüm önerisi alabilirsiniz.")
            else:
                self.setEnabled(False)
                if not library_available:
                    lib_name = 'openai' if provider == 'OpenAI' else 'google-generativeai'
                    self.info_label.setText(f"Bu özellik için '{lib_name}' kütüphanesi gerekli. Lütfen kurun: <code>pip install {lib_name}</code>")
                else:
                    self.info_label.setText(f"Lütfen Ayarlar sekmesinden geçerli bir <b>{provider}</b> API anahtarı girin.")
        except Exception as e:
            self.setEnabled(False)
            self.info_label.setText(f"Aktivasyon kontrolü sırasında bir hata oluştu: {e}")
            QMessageBox.critical(self, "Aktivasyon Hatası", f"Yapay zeka sekmesi etkinleştirilemedi: {e}")

    def get_ai_response(self):
        """
        Kullanıcının girdiği metni alarak, ayarlarda seçili olan yapay zeka
        sağlayıcısına bir istek gönderir ve cevabı ekranda gösterir.
        """
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir soru veya hata kodu girin.")
            return
        
        try:
            provider = self.db.get_setting('ai_provider', 'OpenAI')
            api_key = self.db.get_setting('openai_api_key') if provider == 'OpenAI' else self.db.get_setting('gemini_api_key')
            
            if not api_key:
                QMessageBox.critical(self, "API Anahtarı Eksik", f"Lütfen ayarlardan {provider} için bir API anahtarı girin.")
                return

            self.ask_btn.setEnabled(False)
            self.response_output.setText(f"{provider} düşünüyor...")
            
            self.ai_thread = AIThread(provider, api_key, prompt)
            self.ai_thread.task_finished.connect(self.on_ai_finish)
            self.ai_thread.task_error.connect(self.on_ai_error)
            self.ai_thread.start()
        except Exception as e:
            self.on_ai_error(f"İstek gönderilirken bir hata oluştu: {e}")

    def on_ai_finish(self, response: str):
        """Yapay zeka iş parçacığı başarıyla tamamlandığında çağrılır."""
        self.response_output.setText(response)
        self.ask_btn.setEnabled(True)
        self.analyze_code_btn.setEnabled(True)
    
    def on_ai_error(self, error: str):
        """Yapay zeka iş parçacığında bir hata oluştuğunda çağrılır."""
        self.response_output.setText(f"Hata: {error}")
        self.ask_btn.setEnabled(True)
        self.analyze_code_btn.setEnabled(True)
        QMessageBox.critical(self, "Yapay Zeka Hatası", f"Cevap alınırken bir sorun oluştu:\n{error}")
    
    def analyze_error_code(self):
        """Arıza kodunu analiz eder ve çözüm önerisi sunar."""
        error_code = self.error_code_input.text().strip().upper()
        if not error_code:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir arıza kodu girin.")
            return
        
        brand = self.brand_combo.currentText()
        
        # Önce yerel veritabanından kontrol et
        error_data = get_error_description(brand, error_code)
        
        if error_data.get("bulundu"):
            # Veritabanında bulundu, direkt göster
            formatted_response = format_error_response(error_data)
            self.response_output.setText(formatted_response)
            
            # Detaylı bilgi yoksa AI'ya da sorulabileceğini belirt
            if not error_data.get("detayli"):
                self.response_output.append("\n\n💡 Daha detaylı analiz için aşağıdaki 'Yapay Zeka ile Analiz Et' butonunu kullanabilirsiniz.")
            return
        
        # Veritabanında bulunamadı, AI'ya sor
        self.response_output.setText(f"⏳ {brand} {error_code} kodu yerel veritabanında bulunamadı.\nYapay zeka ile analiz ediliyor...")
        
        # Arıza kodu için özel prompt oluştur
        if brand == "Kyocera":
            prompt = f"""Sen bir Kyocera teknik servis uzmanısın. Aşağıdaki arıza kodunu analiz et:

ARIZA KODU: {error_code}

Bu kod için:
1. Kodun tam açıklamasını ver
2. Arızanın olası nedenlerini listele
3. Adım adım çözüm yollarını açıkla
4. Hangi parçaların kontrol edilmesi veya değiştirilmesi gerektiğini belirt
5. Benzer arızaları önlemek için öneriler sun

Kyocera fotokopi makineleri için standart hata kodları bilgi tabanını kullan.
Cevabını Türkçe, teknik ama anlaşılır şekilde ver.
Önemli: Eğer kod C6000 ise, fuser ünitesi sıcaklık sensörü sorunudur."""
        else:
            prompt = f"""Sen bir {brand} teknik servis uzmanısın. Aşağıdaki arıza kodunu analiz et:

Marka: {brand}
Arıza Kodu: {error_code}

Lütfen şu bilgileri ver:
1. Arıza kodunun anlamı
2. Olası nedenler
3. Adım adım çözüm önerileri
4. Değiştirilmesi gereken parçalar (varsa)
5. Önleyici tedbirler

Cevabını Türkçe, net ve anlaşılır şekilde ver."""
        
        try:
            provider = self.db.get_setting('ai_provider', 'OpenAI')
            api_key = self.db.get_setting('openai_api_key') if provider == 'OpenAI' else self.db.get_setting('gemini_api_key')
            
            if not api_key:
                QMessageBox.critical(self, "API Anahtarı Eksik", f"Lütfen ayarlardan {provider} için bir API anahtarı girin.")
                return

            self.analyze_code_btn.setEnabled(False)
            self.response_output.setText(f"🔍 {brand} {error_code} kodu analiz ediliyor...")
            
            self.ai_thread = AIThread(provider, api_key, prompt)
            self.ai_thread.task_finished.connect(self.on_ai_finish)
            self.ai_thread.task_error.connect(self.on_ai_error)
            self.ai_thread.start()
        except Exception as e:
            self.on_ai_error(f"İstek gönderilirken bir hata oluştu: {e}")
