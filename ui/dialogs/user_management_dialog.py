# ui/dialogs/user_management_dialog.py

import bcrypt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QMessageBox, QHeaderView, QFormLayout, QLineEdit,
                             QDialogButtonBox, QComboBox)
from typing import Optional
from utils.database import db_manager

class UserDialog(QDialog):
    """Yeni kullanıcı eklemek veya rolünü düzenlemek için kullanılan yardımcı diyalog."""
    def __init__(self, current_username: str = None, current_role: str = None, parent=None):
        super().__init__(parent)
        self.is_editing = current_username is not None
        
        title = f"'{current_username}' için Rol Ata" if self.is_editing else "Yeni Kullanıcı Ekle"
        self.setWindowTitle(title)
        
        layout = QFormLayout(self)
        
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Teknisyen", "Ofis Personeli", "Admin"])
        
        if self.is_editing:
            self.user_input.setText(current_username)
            self.user_input.setReadOnly(True)
            self.pass_input.hide()
            layout.addRow("Kullanıcı Adı:", self.user_input)
            self.role_combo.setCurrentText(current_role)
        else:
            layout.addRow("Kullanıcı Adı:", self.user_input)
            layout.addRow("Şifre:", self.pass_input)

        layout.addRow("Rol:", self.role_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> Optional[dict]:
        """Form verilerini toplar ve doğrular."""
        username = self.user_input.text().strip()
        password = self.pass_input.text()
        
        if not self.is_editing and (not username or not password):
            QMessageBox.warning(self, "Eksik Bilgi", "Kullanıcı adı ve şifre boş bırakılamaz.")
            return None
            
        return {
            "username": username,
            "password": password,
            "role": self.role_combo.currentText()
        }

class ChangePasswordDialog(QDialog):
    """Kullanıcı şifresini değiştirmek için kullanılan yardımcı diyalog."""
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"'{username}' için Yeni Şifre")
        
        layout = QFormLayout(self)
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addRow("Yeni Şifre:", self.pass_input)
        layout.addRow("Yeni Şifre (Tekrar):", self.confirm_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_password(self) -> str | None:
        """Yeni şifreyi alır ve doğrular."""
        new_password = self.pass_input.text()
        confirm_password = self.confirm_input.text()
        
        if not new_password:
            QMessageBox.warning(self, "Eksik Bilgi", "Şifre alanı boş bırakılamaz.")
            return None
        if new_password != confirm_password:
            QMessageBox.critical(self, "Uyumsuz Şifreler", "Girilen şifreler uyuşmuyor.")
            return None
        return new_password


class UserManagementDialog(QDialog):
    """Kullanıcıları yönetmek için kullanılan ana diyalog penceresi."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kullanıcı Yönetimi")
        self.setMinimumSize(600, 400)
        self._init_ui()
        self.load_users()

    def _init_ui(self):
        """Kullanıcı arayüzünü oluşturur ve ayarlar."""
        layout = QVBoxLayout(self)
        self.user_table = self._create_table()
        button_layout = self._create_buttons()
        layout.addWidget(self.user_table)
        layout.addLayout(button_layout)
        self._connect_signals()

    def _create_table(self) -> QTableWidget:
        """Kullanıcıları listeleyen tabloyu oluşturur."""
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["ID", "Kullanıcı Adı", "Rol", "Şifre Durumu"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.hideColumn(0)
        return table

    def _create_buttons(self) -> QHBoxLayout:
        """Yönetim butonlarını içeren layout'u oluşturur."""
        button_layout = QHBoxLayout()
        self.add_user_btn = QPushButton("Yeni Kullanıcı")
        self.edit_user_btn = QPushButton("Rol Değiştir")
        self.change_pass_btn = QPushButton("Şifre Değiştir")
        self.delete_user_btn = QPushButton("Kullanıcıyı Sil")
        
        button_layout.addWidget(self.add_user_btn)
        button_layout.addWidget(self.edit_user_btn)
        button_layout.addWidget(self.change_pass_btn)
        button_layout.addWidget(self.delete_user_btn)
        return button_layout

    def _connect_signals(self):
        """Buton sinyallerini ilgili slotlara bağlar."""
        self.add_user_btn.clicked.connect(self._add_user)
        self.edit_user_btn.clicked.connect(self._edit_user_role)
        self.delete_user_btn.clicked.connect(self._delete_user)
        self.change_pass_btn.clicked.connect(self._change_password)

    def load_users(self):
        """Kullanıcıları veritabanından yükler ve tabloya ekler (root kullanıcısı hariç)."""
        try:
            self.user_table.setRowCount(0)
            # Root kullanıcısını gizle
            users = db_manager.fetch_all("SELECT id, username, role, password_hash FROM users WHERE username != 'root' ORDER BY username")
            for user_id, username, role, password_hash in users:
                row_pos = self.user_table.rowCount()
                self.user_table.insertRow(row_pos)
                self.user_table.setItem(row_pos, 0, QTableWidgetItem(str(user_id)))
                self.user_table.setItem(row_pos, 1, QTableWidgetItem(username))
                self.user_table.setItem(row_pos, 2, QTableWidgetItem(role))
                # Şifre durumu
                password_status = "Ayarlandı" if password_hash else "Ayarlanmadı"
                self.user_table.setItem(row_pos, 3, QTableWidgetItem(password_status))
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Kullanıcılar yüklenirken bir hata oluştu: {e}")

    def _get_selected_user_info(self) -> tuple | None:
        """Tablodan seçili olan kullanıcının bilgilerini döndürür."""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen işlem yapmak için bir kullanıcı seçin.")
            return None
        
        row = selected_rows[0].row()
        user_id = self.user_table.item(row, 0).text()
        username = self.user_table.item(row, 1).text()
        current_role = self.user_table.item(row, 2).text()
        return user_id, username, current_role

    def _add_user(self):
        """Yeni bir kullanıcı ekler."""
        dialog = UserDialog(parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if not data: return

            try:
                password_bytes = data["password"].encode('utf-8')
                hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
                
                db_manager.execute_query("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                                      (data["username"], hashed_password, data["role"]))
                QMessageBox.information(self, "Başarılı", f"'{data['username']}' kullanıcısı başarıyla eklendi.")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Kullanıcı eklenirken bir hata oluştu: {e}")
    
    def _edit_user_role(self):
        """Seçili kullanıcının rolünü değiştirir."""
        selected_user = self._get_selected_user_info()
        if not selected_user: return
        
        user_id, username, current_role = selected_user
        
        if username == 'admin':
            QMessageBox.warning(self, "İşlem Reddedildi", "Admin kullanıcısının rolü değiştirilemez.")
            return
            
        dialog = UserDialog(username, current_role, self)
        if dialog.exec():
            data = dialog.get_data()
            if not data: return
            
            try:
                db_manager.execute_query("UPDATE users SET role = ? WHERE id = ?", (data["role"], user_id))
                QMessageBox.information(self, "Başarılı", f"'{username}' kullanıcısının rolü '{data['role']}' olarak güncellendi.")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Kullanıcı rolü güncellenirken bir hata oluştu: {e}")

    def _delete_user(self):
        """Seçili kullanıcıyı siler."""
        selected_user = self._get_selected_user_info()
        if not selected_user: return
            
        user_id, username, _ = selected_user
        
        if username == 'admin':
            QMessageBox.warning(self, "İşlem Reddedildi", "Admin kullanıcısı silinemez.")
            return
            
        reply = QMessageBox.question(self, "Kullanıcıyı Sil", 
                                     f"'{username}' kullanıcısını kalıcı olarak silmek istediğinizden emin misiniz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db_manager.execute_query("DELETE FROM users WHERE id = ?", (user_id,))
                QMessageBox.information(self, "Başarılı", f"'{username}' kullanıcısı silindi.")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Kullanıcı silinirken bir hata oluştu: {e}")

    def _change_password(self):
        """Seçili kullanıcının şifresini değiştirir."""
        selected_user = self._get_selected_user_info()
        if not selected_user: return
            
        user_id, username, _ = selected_user
        
        dialog = ChangePasswordDialog(username, self)
        if dialog.exec():
            new_password = dialog.get_password()
            if not new_password: return
                
            try:
                password_bytes = new_password.encode('utf-8')
                hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
                
                db_manager.execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
                QMessageBox.information(self, "Başarılı", f"'{username}' kullanıcısının şifresi güncellendi.")
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Şifre güncellenirken bir hata oluştu: {e}")