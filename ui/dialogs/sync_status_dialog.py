#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProServis Sync Status Dialog
Gerçek zamanlı senkronizasyon durumu ve yönetimi
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressBar, QTextEdit, QCheckBox,
    QSpinBox, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from datetime import datetime
import os

from utils.sync_manager import SyncManager


class SyncStatusDialog(QDialog):
    """Senkronizasyon durumu ve yönetim arayüzü"""
    
    sync_triggered = pyqtSignal()
    
    def __init__(self, sync_manager: SyncManager, parent=None):
        super().__init__(parent)
        self.sync_manager = sync_manager
        
        self.setWindowTitle("📡 Bulut Senkronizasyon Durumu")
        self.setMinimumSize(700, 500)
        self.setModal(False)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(2000)  # Her 2 saniyede bir güncelle
        
        self.init_ui()
        self.refresh_status()
    
    def init_ui(self):
        """Arayüzü oluştur"""
        layout = QVBoxLayout(self)
        
        # Durum göstergesi
        status_group = QGroupBox("📊 Anlık Durum")
        status_layout = QVBoxLayout(status_group)
        
        # Online/Offline durumu
        self.online_label = QLabel("🔴 Offline")
        self.online_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        status_layout.addWidget(self.online_label)
        
        # Senkronizasyon durumu
        info_layout = QHBoxLayout()
        
        self.sync_status_label = QLabel("Bekleniyor...")
        info_layout.addWidget(QLabel("Durum:"))
        info_layout.addWidget(self.sync_status_label)
        info_layout.addStretch()
        
        status_layout.addLayout(info_layout)
        
        # Bekleyen değişiklikler
        pending_layout = QHBoxLayout()
        
        self.pending_label = QLabel("0")
        self.pending_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #ff9800;")
        pending_layout.addWidget(QLabel("Bekleyen Değişiklikler:"))
        pending_layout.addWidget(self.pending_label)
        pending_layout.addStretch()
        
        status_layout.addLayout(pending_layout)
        
        # Son senkronizasyon
        last_sync_layout = QHBoxLayout()
        
        self.last_sync_label = QLabel("-")
        last_sync_layout.addWidget(QLabel("Son Senkronizasyon:"))
        last_sync_layout.addWidget(self.last_sync_label)
        last_sync_layout.addStretch()
        
        status_layout.addLayout(last_sync_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # Ayarlar
        settings_group = QGroupBox("⚙️ Senkronizasyon Ayarları")
        settings_layout = QVBoxLayout(settings_group)
        
        self.auto_sync_check = QCheckBox("Otomatik senkronizasyon aktif")
        self.auto_sync_check.stateChanged.connect(self.on_auto_sync_changed)
        settings_layout.addWidget(self.auto_sync_check)
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Senkronizasyon aralığı (saniye):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(30, 3600)
        self.interval_spin.setValue(300)
        self.interval_spin.valueChanged.connect(self.on_interval_changed)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        settings_layout.addLayout(interval_layout)
        
        layout.addWidget(settings_group)
        
        # Manuel kontroller
        controls_group = QGroupBox("🎮 Manuel Kontrol")
        controls_layout = QHBoxLayout(controls_group)
        
        sync_now_btn = QPushButton("🔄 Şimdi Senkronize Et")
        sync_now_btn.clicked.connect(self.sync_now)
        controls_layout.addWidget(sync_now_btn)
        
        clear_queue_btn = QPushButton("🗑️ Senkronize Edilenleri Temizle")
        clear_queue_btn.clicked.connect(self.clear_synced)
        controls_layout.addWidget(clear_queue_btn)
        
        reset_failed_btn = QPushButton("♻️ Başarısızları Sıfırla")
        reset_failed_btn.clicked.connect(self.reset_failed)
        controls_layout.addWidget(reset_failed_btn)
        
        layout.addWidget(controls_group)
        
        # Son aktiviteler
        activity_group = QGroupBox("📜 Son Aktiviteler")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(5)
        self.activity_table.setHorizontalHeaderLabels([
            "Tarih/Saat", "Tip", "Durum", "Kayıt Sayısı", "Detay"
        ])
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        activity_layout.addWidget(self.activity_table)
        
        layout.addWidget(activity_group)
        
        # Bekleyen değişiklikler detayı
        pending_group = QGroupBox("📋 Bekleyen Değişiklikler")
        pending_layout_widget = QVBoxLayout(pending_group)
        
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(5)
        self.pending_table.setHorizontalHeaderLabels([
            "Tablo", "Kayıt ID", "İşlem", "Tarih", "Deneme"
        ])
        self.pending_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        pending_layout_widget.addWidget(self.pending_table)
        
        layout.addWidget(pending_group)
        
        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def refresh_status(self):
        """Durumu yenile"""
        try:
            status = self.sync_manager.get_sync_status()
            
            # Online/Offline durumu
            if status['is_online']:
                self.online_label.setText("🟢 Online - Bulut Bağlantısı Aktif")
                self.online_label.setStyleSheet(
                    "font-size: 14pt; font-weight: bold; color: green;"
                )
            else:
                self.online_label.setText("🔴 Offline - Yerel Modda")
                self.online_label.setStyleSheet(
                    "font-size: 14pt; font-weight: bold; color: red;"
                )
            
            # Senkronizasyon durumu
            if status['is_syncing']:
                self.sync_status_label.setText("🔄 Senkronize ediliyor...")
                self.sync_status_label.setStyleSheet("color: blue;")
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # Indeterminate
            else:
                self.sync_status_label.setText("✅ Hazır")
                self.sync_status_label.setStyleSheet("color: green;")
                self.progress_bar.setVisible(False)
            
            # Bekleyen değişiklikler
            pending_count = status['pending_changes']
            self.pending_label.setText(str(pending_count))
            
            if pending_count == 0:
                self.pending_label.setStyleSheet(
                    "font-size: 18pt; font-weight: bold; color: green;"
                )
            elif pending_count < 10:
                self.pending_label.setStyleSheet(
                    "font-size: 18pt; font-weight: bold; color: orange;"
                )
            else:
                self.pending_label.setStyleSheet(
                    "font-size: 18pt; font-weight: bold; color: red;"
                )
            
            # Son senkronizasyon
            if status['last_sync_time']:
                try:
                    dt = datetime.fromisoformat(status['last_sync_time'])
                    self.last_sync_label.setText(dt.strftime("%d.%m.%Y %H:%M:%S"))
                except:
                    self.last_sync_label.setText(status['last_sync_time'])
            else:
                self.last_sync_label.setText("Henüz senkronize edilmedi")
            
            # Ayarlar
            self.auto_sync_check.blockSignals(True)
            self.auto_sync_check.setChecked(status['auto_sync_enabled'])
            self.auto_sync_check.blockSignals(False)
            
            self.interval_spin.blockSignals(True)
            self.interval_spin.setValue(status['sync_interval'])
            self.interval_spin.blockSignals(False)
            
            # Son aktiviteler
            self.refresh_activity_table(status.get('recent_history', []))
            
            # Bekleyen değişiklikler detayı
            self.refresh_pending_table()
        
        except Exception as e:
            self.online_label.setText(f"❌ Hata: {e}")
            self.online_label.setStyleSheet("color: red;")
    
    def refresh_activity_table(self, history: list):
        """Aktivite tablosunu güncelle"""
        self.activity_table.setRowCount(len(history))
        
        for i, record in enumerate(history):
            # Tarih
            started = record.get('started_at', '')
            if started:
                try:
                    dt = datetime.fromisoformat(started)
                    date_str = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    date_str = started
            else:
                date_str = "-"
            
            self.activity_table.setItem(i, 0, QTableWidgetItem(date_str))
            
            # Tip
            sync_type = record.get('sync_type', '-')
            type_map = {
                'auto': '🤖 Otomatik',
                'manual': '👆 Manuel',
                'forced': '⚡ Zorlanmış'
            }
            self.activity_table.setItem(i, 1, QTableWidgetItem(
                type_map.get(sync_type, sync_type)
            ))
            
            # Durum
            status = record.get('status', '-')
            status_item = QTableWidgetItem(status.upper())
            
            if status == 'success':
                status_item.setForeground(QColor('green'))
            elif status == 'failed':
                status_item.setForeground(QColor('red'))
            elif status == 'partial':
                status_item.setForeground(QColor('orange'))
            
            self.activity_table.setItem(i, 2, status_item)
            
            # Kayıt sayısı
            count = record.get('records_synced', 0)
            self.activity_table.setItem(i, 3, QTableWidgetItem(str(count)))
            
            # Detay
            completed = record.get('completed_at', '')
            if started and completed:
                try:
                    start_dt = datetime.fromisoformat(started)
                    end_dt = datetime.fromisoformat(completed)
                    duration = (end_dt - start_dt).total_seconds()
                    detail = f"{duration:.1f} saniye"
                except:
                    detail = "-"
            else:
                detail = "Devam ediyor..."
            
            self.activity_table.setItem(i, 4, QTableWidgetItem(detail))
        
        self.activity_table.resizeColumnsToContents()
    
    def refresh_pending_table(self):
        """Bekleyen değişiklikler tablosunu güncelle"""
        pending = self.sync_manager.get_pending_changes(limit=50)
        
        self.pending_table.setRowCount(len(pending))
        
        for i, change in enumerate(pending):
            # Tablo
            self.pending_table.setItem(i, 0, QTableWidgetItem(
                change['table_name']
            ))
            
            # Kayıt ID
            self.pending_table.setItem(i, 1, QTableWidgetItem(
                str(change['record_id'])
            ))
            
            # İşlem
            operation = change['operation']
            op_map = {
                'INSERT': '➕ Ekleme',
                'UPDATE': '✏️ Güncelleme',
                'DELETE': '❌ Silme'
            }
            self.pending_table.setItem(i, 2, QTableWidgetItem(
                op_map.get(operation, operation)
            ))
            
            # Tarih
            created = change.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    date_str = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    date_str = created
            else:
                date_str = "-"
            
            self.pending_table.setItem(i, 3, QTableWidgetItem(date_str))
            
            # Deneme sayısı
            retry = change.get('retry_count', 0)
            retry_item = QTableWidgetItem(str(retry))
            
            if retry > 0:
                retry_item.setForeground(QColor('orange'))
            
            self.pending_table.setItem(i, 4, retry_item)
        
        self.pending_table.resizeColumnsToContents()
    
    def on_auto_sync_changed(self, state):
        """Otomatik senkronizasyon değiştirildi"""
        enabled = state == Qt.CheckState.Checked.value
        self.sync_manager.set_setting('auto_sync_enabled', str(enabled).lower())
        
        if enabled:
            self.sync_manager.start_auto_sync()
            QMessageBox.information(
                self,
                "Otomatik Senkronizasyon",
                "Otomatik senkronizasyon etkinleştirildi."
            )
        else:
            self.sync_manager.stop_auto_sync()
            QMessageBox.information(
                self,
                "Otomatik Senkronizasyon",
                "Otomatik senkronizasyon devre dışı bırakıldı."
            )
    
    def on_interval_changed(self, value):
        """Senkronizasyon aralığı değiştirildi"""
        self.sync_manager.set_setting('sync_interval_seconds', value)
        
        # Eğer otomatik sync aktifse yeniden başlat
        if self.sync_manager.is_auto_sync_enabled():
            self.sync_manager.stop_auto_sync()
            self.sync_manager.start_auto_sync()
    
    def sync_now(self):
        """Manuel senkronizasyon başlat"""
        reply = QMessageBox.question(
            self,
            "Manuel Senkronizasyon",
            "Bekleyen tüm değişiklikler buluta gönderilecek.\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.sync_manager.force_sync()
            
            if result['success']:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"Senkronizasyon tamamlandı!\n"
                    f"Kalan bekleyen değişiklik: {result['pending_count']}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Hata",
                    f"Senkronizasyon başarısız:\n{result['message']}"
                )
            
            self.refresh_status()
    
    def clear_synced(self):
        """Senkronize edilmiş kayıtları temizle"""
        reply = QMessageBox.question(
            self,
            "Temizle",
            "Başarıyla senkronize edilmiş tüm kayıtlar kuyruktan silinecek.\n"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self.sync_manager.clear_sync_queue()
            QMessageBox.information(
                self,
                "Temizlendi",
                f"{count} kayıt kuyruktan silindi."
            )
            self.refresh_status()
    
    def reset_failed(self):
        """Başarısız senkronizasyonları sıfırla"""
        reply = QMessageBox.question(
            self,
            "Sıfırla",
            "Başarısız senkronizasyonlar sıfırlanacak ve yeniden denenecek.\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self.sync_manager.reset_failed_syncs()
            QMessageBox.information(
                self,
                "Sıfırlandı",
                f"{count} başarısız senkronizasyon sıfırlandı."
            )
            self.refresh_status()
    
    def closeEvent(self, event):
        """Dialog kapatılırken timer'ı durdur"""
        self.refresh_timer.stop()
        super().closeEvent(event)


# Test
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Mock sync manager
    class MockSyncManager:
        def get_sync_status(self):
            return {
                'is_syncing': False,
                'is_online': True,
                'auto_sync_enabled': True,
                'pending_changes': 5,
                'last_sync_time': datetime.now().isoformat(),
                'sync_interval': 300,
                'recent_history': []
            }
        
        def get_pending_changes(self, limit=50):
            return []
    
    dialog = SyncStatusDialog(MockSyncManager())
    dialog.show()
    
    sys.exit(app.exec())
