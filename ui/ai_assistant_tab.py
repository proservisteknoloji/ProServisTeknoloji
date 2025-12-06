"""
AI Asistan Sekmesi

Kullanıcıların AI ile sohbet edebileceği arayüz.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import logging

from utils.ai_providers import AIProviderFactory
from utils.ai_database_helper import AIDatabaseHelper


class AIWorkerThread(QThread):
    """AI sorgularını arka planda çalıştıran thread"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, provider, question, context=None):
        super().__init__()
        self.provider = provider
        self.question = question
        self.context = context
    
    def run(self):
        try:
            response = self.provider.ask(self.question, self.context)
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AIAssistantTab(QWidget):
    """AI Asistan sekmesi"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.db_helper = AIDatabaseHelper(db_manager)
        
        # AI provider
        self.current_provider_type = 'simple'
        self.gemini_api_key = self.db.get_setting('gemini_api_key', '')
        self.provider = AIProviderFactory.create_provider(self.current_provider_type)
        
        # Worker thread
        self.worker = None
        
        self.init_ui()
        
    def init_ui(self):
        """UI'ı oluşturur"""
        layout = QVBoxLayout()
        
        # Üst panel: Provider seçimi ve ayarlar
        top_panel = self._create_top_panel()
        layout.addWidget(top_panel)
        
        # Chat alanı
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.chat_display, stretch=3)
        
        # Soru girişi
        input_layout = QHBoxLayout()
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Sorunuzu buraya yazın... (Örn: 'Bugün kaç servis kaydı girildi?')")
        self.question_input.returnPressed.connect(self.send_question)
        input_layout.addWidget(self.question_input, stretch=4)
        
        self.send_button = QPushButton("Gönder")
        self.send_button.clicked.connect(self.send_question)
        input_layout.addWidget(self.send_button)
        
        self.clear_button = QPushButton("Temizle")
        self.clear_button.clicked.connect(self.clear_chat)
        input_layout.addWidget(self.clear_button)
        
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
        # Hoş geldin mesajı
        self._add_system_message("AI Asistan'a hoş geldiniz! Veritabanı sorguları, arıza kodları ve teknik konularda sorularınızı sorabilirsiniz.")
        
    def _create_top_panel(self):
        """Üst panel (provider seçimi ve ayarlar)"""
        group = QGroupBox("AI Ayarları")
        layout = QHBoxLayout()
        
        # Provider seçimi
        layout.addWidget(QLabel("AI Sağlayıcı:"))
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Basit (Offline - Ücretsiz)", "Google Gemini (API Key Gerekli)"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        layout.addWidget(self.provider_combo)
        
        # Gemini API key girişi
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Gemini API Key (opsiyonel)")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.gemini_api_key)
        self.api_key_input.setVisible(False)
        layout.addWidget(self.api_key_input, stretch=2)
        
        self.save_key_button = QPushButton("Kaydet")
        self.save_key_button.clicked.connect(self._save_api_key)
        self.save_key_button.setVisible(False)
        layout.addWidget(self.save_key_button)
        
        # Durum göstergesi
        self.status_label = QLabel("✓ Hazır (Offline)")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _on_provider_changed(self, index):
        """Provider değiştiğinde çağrılır"""
        if index == 0:  # Basit (Offline)
            self.current_provider_type = 'simple'
            self.api_key_input.setVisible(False)
            self.save_key_button.setVisible(False)
            self.provider = AIProviderFactory.create_provider('simple')
            self.status_label.setText("✓ Hazır (Offline)")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self._add_system_message("Basit offline provider seçildi. Veritabanı sorguları ve arıza kodları desteklenir. API key gerektirmez.")
        else:  # Gemini
            self.current_provider_type = 'gemini'
            self.api_key_input.setVisible(True)
            self.save_key_button.setVisible(True)
            
            if self.gemini_api_key:
                self.provider = AIProviderFactory.create_provider('gemini', self.gemini_api_key)
                self._add_system_message("Gemini provider seçildi. API key kaydedilmiş.")
            else:
                self._add_system_message("Gemini provider seçildi. Lütfen API key girin ve kaydedin.")
    
    def _save_api_key(self):
        """Gemini API key'i kaydeder"""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Uyarı", "Lütfen API key girin.")
            return
        
        # Veritabanına kaydet
        self.db.save_setting('gemini_api_key', api_key)
        self.gemini_api_key = api_key
        
        # Provider'ı güncelle
        self.provider = AIProviderFactory.create_provider('gemini', api_key)
        
        # Kontrol et
        if self.provider.is_available():
            self._add_system_message("✓ Gemini API key başarıyla kaydedildi ve doğrulandı!")
            self.status_label.setText("✓ Gemini Hazır")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self._add_system_message("✗ API key kaydedildi ama doğrulanamadı. Lütfen key'in doğru olduğundan emin olun.")
            self.status_label.setText("✗ API Key Hatası")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def send_question(self):
        """Kullanıcının sorusunu AI'ya gönderir"""
        question = self.question_input.text().strip()
        
        if not question:
            return
        
        # Soruyu chat'e ekle
        self._add_user_message(question)
        self.question_input.clear()
        
        # Provider kontrolü
        if not self.provider.is_available():
            if self.current_provider_type == 'gemini':
                self._add_system_message("✗ Gemini kullanılamıyor. Lütfen geçerli bir API key girin.")
            return
        
        # Context hazırla (veritabanından bilgi çek)
        context = self.db_helper.get_context_for_question(question)
        
        # Loading göster
        self.status_label.setText("⏳ Cevap hazırlanıyor...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.send_button.setEnabled(False)
        
        # Worker thread'de AI'ya sor
        self.worker = AIWorkerThread(self.provider, question, context)
        self.worker.response_ready.connect(self._on_response_ready)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()
    
    def _on_response_ready(self, response):
        """AI cevabı hazır olduğunda çağrılır"""
        self._add_ai_message(response)
        if self.current_provider_type == 'simple':
            self.status_label.setText("✓ Hazır (Offline)")
        else:
            self.status_label.setText("✓ Hazır")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.send_button.setEnabled(True)
    
    def _on_error(self, error):
        """Hata oluştuğunda çağrılır"""
        self._add_system_message(f"✗ Hata: {error}")
        self.status_label.setText("✗ Hata")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.send_button.setEnabled(True)
    
    def _add_user_message(self, message):
        """Kullanıcı mesajını chat'e ekler"""
        self.chat_display.append(f"<div style='background-color: #E3F2FD; padding: 10px; margin: 5px; border-radius: 5px;'>"
                                 f"<b>Siz:</b> {message}</div>")
    
    def _add_ai_message(self, message):
        """AI mesajını chat'e ekler"""
        # Markdown formatını HTML'e çevir (basit)
        message = message.replace('\n', '<br>')
        message = message.replace('**', '<b>').replace('**', '</b>')
        
        self.chat_display.append(f"<div style='background-color: #F5F5F5; padding: 10px; margin: 5px; border-radius: 5px;'>"
                                 f"<b>AI Asistan:</b><br>{message}</div>")
    
    def _add_system_message(self, message):
        """Sistem mesajını chat'e ekler"""
        self.chat_display.append(f"<div style='background-color: #FFF9C4; padding: 8px; margin: 5px; border-radius: 5px; font-style: italic;'>"
                                 f"{message}</div>")
    
    def clear_chat(self):
        """Chat geçmişini temizler"""
        self.chat_display.clear()
        self._add_system_message("Chat geçmişi temizlendi.")
