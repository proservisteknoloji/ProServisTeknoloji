
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Mock database before importing StockTab to avoid DB connection issues
sys.modules['utils.database'] = MagicMock()
sys.modules['utils.database.db_manager'] = MagicMock()

# Mock other dependencies that might cause issues
sys.modules['ui.dialogs.stock_dialogs'] = MagicMock()
sys.modules['ui.dialogs.stock_settings_dialog'] = MagicMock()
sys.modules['ui.dialogs.price_settings_dialog'] = MagicMock()
sys.modules['ui.dialogs.device_analysis_dialog'] = MagicMock()
sys.modules['utils.cpc_stock_manager'] = MagicMock()

# Now import StockTab
# We need to make sure we import the class we want to test
# Since we mocked ui.dialogs.stock_dialogs, StockTab import might fail if it imports from there
# But StockTab imports *from* there.
# Let's try to import StockTab and see if it works with mocks
try:
    from ui.stock_tab import StockTab
except ImportError:
    # If import fails, we might need to mock the module structure better
    # But let's try to patch the specific file content if needed
    pass

class TestStockTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.mock_db = MagicMock()
        # Mock save_stock_item to return a fake ID (simulating success)
        self.mock_db.save_stock_item.return_value = 123
        
        # Instantiate StockTab with mock DB
        # We patch CPCStockManager inside StockTab
        with patch('ui.stock_tab.CPCStockManager'):
            self.stock_tab = StockTab(self.mock_db)

    def test_add_device_no_auto_toner(self):
        """Test that adding a device does NOT trigger auto toner addition."""
        
        # We need to mock StockItemDialog which is used inside open_item_dialog
        # Since we mocked the module ui.dialogs.stock_dialogs, we can configure it
        from ui.dialogs.stock_dialogs import StockItemDialog
        
        mock_dialog_instance = StockItemDialog.return_value
        mock_dialog_instance.exec.return_value = True # Simulate user clicking Save
        
        # Simulate data returned from dialog
        mock_dialog_instance.get_data.return_value = {
            'name': 'Test Device',
            'item_type': 'Cihaz',
            'quantity': 1,
            'purchase_price': 100,
            'sale_price': 200
        }
        
        # Mock the methods we want to verify are NOT called
        with patch.object(self.stock_tab, 'add_device_toners_to_stock') as mock_add_toners, \
             patch.object(self.stock_tab, 'add_device_kits_to_stock') as mock_add_kits, \
             patch.object(self.stock_tab, 'add_manual_toners_to_stock') as mock_add_manual_toners, \
             patch.object(self.stock_tab, 'add_manual_kits_to_stock') as mock_add_manual_kits:
            
            # Simulate manual toners NOT being added
            mock_add_manual_toners.return_value = False
            
            # Call the method under test
            self.stock_tab.open_item_dialog(item_type='Cihaz')
            
            # VERIFICATION
            
            # 1. Verify dialog was opened
            StockItemDialog.assert_called()
            
            # 2. Verify DB save was called
            self.mock_db.save_stock_item.assert_called()
            
            # 3. Verify auto toner addition was NOT called
            mock_add_toners.assert_not_called()
            
            # 4. Verify auto kit addition was NOT called
            mock_add_kits.assert_not_called()
            
            print("\n✅ SUCCESS: add_device_toners_to_stock was NOT called.")
            print("✅ SUCCESS: add_device_kits_to_stock was NOT called.")

if __name__ == '__main__':
    unittest.main()
