from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, 
                            QTextEdit, QPushButton, QListWidget, QHBoxLayout, QMessageBox, QWidget, QCheckBox)
from PyQt6.QtCore import Qt

class BankSettingsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Banka ve IBAN Bilgileri")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        main_layout = QHBoxLayout(self)
        
        # Left side - Bank list
        # FIXED: Add parent to prevent memory leak
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        self.bank_list = QListWidget()
        self.bank_list.currentRowChanged.connect(self.load_bank_details)
        
        add_button = QPushButton("Yeni Banka Ekle")
        delete_button = QPushButton("Bankayı Sil")
        add_button.clicked.connect(self.add_new_bank)
        delete_button.clicked.connect(self.delete_bank)
        
        left_layout.addWidget(self.bank_list)
        left_layout.addWidget(add_button)
        left_layout.addWidget(delete_button)
        
        # Right side - Bank details form
        # FIXED: Add parent to prevent memory leak
        right_widget = QWidget(self)
        self.form_layout = QFormLayout(right_widget)
        
        self.bank_name_input = QLineEdit()
        self.account_holder_input = QLineEdit()
        self.iban_input = QLineEdit()
        self.notes_edit = QTextEdit()
        self.default_checkbox = QCheckBox("Varsayılan Banka")
        
        self.form_layout.addRow("Banka Adı:", self.bank_name_input)
        self.form_layout.addRow("Hesap Sahibi:", self.account_holder_input)
        self.form_layout.addRow("IBAN:", self.iban_input)
        self.form_layout.addRow("Ek Notlar:", self.notes_edit)
        self.form_layout.addRow(self.default_checkbox)
        
        # Add both sides to main layout
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        
        # Add save/cancel buttons at the bottom
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        self.form_layout.addRow(buttons)
        
        # Disable form fields initially
        self.set_form_enabled(False)
        
        # Load existing banks
        self.load_banks()
        
        # Import old settings if no banks exist
        cursor = self.db.get_connection().cursor()
        cursor.execute("SELECT COUNT(*) FROM banks")
        if cursor.fetchone()[0] == 0:
            self.import_old_settings()

    def import_old_settings(self):
        """Import bank settings from the old settings system"""
        bank_name = self.db.get_setting('bank_name', '')
        if bank_name:
            cursor = self.db.get_connection().cursor()
            cursor.execute("""
                INSERT INTO banks (bank_name, account_holder, iban, notes, is_default)
                VALUES (?, ?, ?, ?, 1)
            """, (
                bank_name,
                self.db.get_setting('bank_account_holder', ''),
                self.db.get_setting('bank_iban', ''),
                self.db.get_setting('bank_notes', '')
            ))
            self.db.get_connection().commit()
            
            # Remove old settings
            self.db.delete_setting('bank_name')
            self.db.delete_setting('bank_account_holder')
            self.db.delete_setting('bank_iban')
            self.db.delete_setting('bank_notes')
            
            self.load_banks()

    def set_form_enabled(self, enabled):
        """Enable or disable all form fields"""
        self.bank_name_input.setEnabled(enabled)
        self.account_holder_input.setEnabled(enabled)
        self.iban_input.setEnabled(enabled)
        self.notes_edit.setEnabled(enabled)
        self.default_checkbox.setEnabled(enabled)

    def load_banks(self):
        """Load all banks from database into the list widget"""
        self.bank_list.clear()
        cursor = self.db.get_connection().cursor()
        cursor.execute("SELECT bank_name FROM banks ORDER BY is_default DESC, bank_name")
        banks = cursor.fetchall()
        for bank in banks:
            self.bank_list.addItem(bank[0])

    def load_bank_details(self, row):
        """Load details of selected bank into form"""
        if row >= 0:
            bank_name = self.bank_list.item(row).text()
            cursor = self.db.get_connection().cursor()
            cursor.execute("""
                SELECT bank_name, account_holder, iban, notes, is_default 
                FROM banks WHERE bank_name = ?
            """, (bank_name,))
            bank = cursor.fetchone()
            
            if bank:
                self.bank_name_input.setText(bank[0])
                self.account_holder_input.setText(bank[1])
                self.iban_input.setText(bank[2])
                self.notes_edit.setText(bank[3] or '')
                self.default_checkbox.setChecked(bank[4])
                self.set_form_enabled(True)

    def add_new_bank(self):
        """Add a new blank bank to the list"""
        self.bank_list.addItem("Yeni Banka")
        self.bank_list.setCurrentRow(self.bank_list.count() - 1)
        
        # Clear and enable form fields
        self.bank_name_input.clear()
        self.account_holder_input.clear()
        self.iban_input.clear()
        self.notes_edit.clear()
        self.default_checkbox.setChecked(False)
        self.set_form_enabled(True)

    def delete_bank(self):
        """Delete selected bank from database"""
        current_row = self.bank_list.currentRow()
        if current_row >= 0:
            bank_name = self.bank_list.item(current_row).text()
            
            # Check if this is the default bank
            cursor = self.db.get_connection().cursor()
            cursor.execute("SELECT is_default FROM banks WHERE bank_name = ?", (bank_name,))
            is_default = cursor.fetchone()[0]
            
            if is_default:
                QMessageBox.warning(self, "Hata", "Varsayılan banka silinemez!")
                return
            
            reply = QMessageBox.question(self, 'Onay', 
                                       f'"{bank_name}" bankasını silmek istediğinizden emin misiniz?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                cursor = self.db.get_connection().cursor()
                cursor.execute("DELETE FROM banks WHERE bank_name = ?", (bank_name,))
                self.db.get_connection().commit()
                self.load_banks()
                self.set_form_enabled(False)
                self.clear_form()

    def clear_form(self):
        """Clear all form fields"""
        self.bank_name_input.clear()
        self.account_holder_input.clear()
        self.iban_input.clear()
        self.notes_edit.clear()
        self.default_checkbox.setChecked(False)

    def save_and_accept(self):
        """Save all bank details to database"""
        current_row = self.bank_list.currentRow()
        if current_row >= 0:
            old_bank_name = self.bank_list.item(current_row).text()
            new_bank_name = self.bank_name_input.text().strip()
            
            if not new_bank_name:
                QMessageBox.warning(self, "Hata", "Banka adı boş olamaz!")
                return
            
            # Check if a bank with this name already exists (except for the current bank)
            cursor = self.db.get_connection().cursor()
            cursor.execute("SELECT COUNT(*) FROM banks WHERE bank_name = ? AND bank_name != ?", 
                         (new_bank_name, old_bank_name))
            if cursor.fetchone()[0] > 0:
                QMessageBox.warning(self, "Hata", f"'{new_bank_name}' adında bir banka zaten var!")
                return
            
            # If this is being set as default, unset any existing default
            if self.default_checkbox.isChecked():
                cursor.execute("UPDATE banks SET is_default = 0")
            
            # Update or insert bank details
            cursor.execute("""
                INSERT OR REPLACE INTO banks 
                (bank_name, account_holder, iban, notes, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (
                new_bank_name,
                self.account_holder_input.text().strip(),
                self.iban_input.text().strip(),
                self.notes_edit.toPlainText().strip(),
                self.default_checkbox.isChecked()
            ))
            
            # If this was the old default and is no longer default, set another bank as default
            if not self.default_checkbox.isChecked():
                cursor.execute("SELECT COUNT(*) FROM banks WHERE is_default = 1")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("UPDATE banks SET is_default = 1 WHERE bank_name = ?", (new_bank_name,))
            
            self.db.get_connection().commit()
            
        self.accept()