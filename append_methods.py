
    def on_source_changed(self):
        """Cihaz kaynağı değiştiğinde tetiklenir."""
        is_from_stock = self.source_combo.currentText() == "Stoktan Seç"
        self.stock_filter_input.setVisible(is_from_stock)
        self.stock_table.setVisible(is_from_stock)
        if is_from_stock:
            self.load_stock_items()
        else:
            self.stock_table.setRowCount(0)

    def load_stock_items(self):
        """Stok öğelerini tablodan yükler."""
        try:
            self.stock_table.setRowCount(0)
            stock_items = self.db.fetch_all("SELECT id, name, brand, part_number FROM stock_items WHERE quantity > 0 ORDER BY name, brand")
            for item in stock_items:
                row = self.stock_table.rowCount()
                self.stock_table.insertRow(row)
                self.stock_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
                self.stock_table.setItem(row, 1, QTableWidgetItem(item['name'] or ''))
                self.stock_table.setItem(row, 2, QTableWidgetItem(item['brand'] or ''))
                self.stock_table.setItem(row, 3, QTableWidgetItem(item['part_number'] or ''))
        except Exception as e:
            logging.error(f'Stok öğeleri yüklenirken hata: {e}')

    def filter_stock_items(self):
        """Stok listesini filtreler."""
        filter_text = self.stock_filter_input.text().lower()
        for row in range(self.stock_table.rowCount()):
            model_item = self.stock_table.item(row, 1)
            brand_item = self.stock_table.item(row, 2)
            serial_item = self.stock_table.item(row, 3)
            model_text = model_item.text().lower() if model_item else ''
            brand_text = brand_item.text().lower() if brand_item else ''
            serial_text = serial_item.text().lower() if serial_item else ''
            match = filter_text in model_text or filter_text in brand_text or filter_text in serial_text
            self.stock_table.setRowHidden(row, not match)

    def on_stock_selected(self):
        """Stoktan bir ürün seçildiğinde form alanlarını doldur."""
        selected_rows = self.stock_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        try:
            row = selected_rows[0].row()
            stock_id = int(self.stock_table.item(row, 0).text())
            model = self.stock_table.item(row, 1).text()
            brand = self.stock_table.item(row, 2).text()
            serial = self.stock_table.item(row, 3).text()
            self.brand_input.setText(brand)
            self.model_input.setText(model)
            self.serial_input.setText(serial)
            self.type_combo.setCurrentText('Siyah-Beyaz')
            self.is_cpc_combo.setCurrentIndex(1)
            self.stock_table.setVisible(False)
            self.stock_filter_input.setVisible(False)
        except Exception as e:
            logging.error(f'Stok seçimi işlenirken hata: {e}')
