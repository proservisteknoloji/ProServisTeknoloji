# ui/custom_widgets.py

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal as Signal, Qt
from PyQt6.QtGui import QMouseEvent

class ClickableStatCard(QGroupBox):
    """Üzerine tıklanabilen ve hover efekti olan modern istatistik kartı."""
    clicked = Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.main_layout = QVBoxLayout(self)
        self.value_label = QLabel("0")
        self.subtitle_label = QLabel("")
        
        # Stil
        self.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                color: #4B5563;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                margin-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 12px;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.value_label.setStyleSheet("font-size: 28pt; color: #1E40AF; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.subtitle_label.setStyleSheet("font-size: 9pt; color: #6B7280; font-weight: normal;")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(self.value_label)
        self.main_layout.addWidget(self.subtitle_label)

    def mousePressEvent(self, event: QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        # Basit bir hover efekti
        self.setStyleSheet(self.styleSheet() + "QGroupBox { border: 1px solid #3B82F6; }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("QGroupBox { border: 1px solid #3B82F6; }", ""))
        super().leaveEvent(event)

    def set_value(self, text):
        self.value_label.setText(str(text))
        
    def set_subtitle(self, text):
        self.subtitle_label.setText(str(text))