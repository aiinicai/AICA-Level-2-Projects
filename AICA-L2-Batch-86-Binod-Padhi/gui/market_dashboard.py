"""
gui/market_dashboard.py
"Market Data" + "City Comparison" screens: import CSV/Excel/JSON,
view update history, and compare aggregate stats across cities.
"""

import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QListWidget,
    QComboBox, QCheckBox
)

from data.importer import import_market_data, export_template_csv
from data.data_sources import list_sources
from gui.charts import MplCanvas, city_comparison_chart


class MarketDataScreen(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()
        self._refresh_summary()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        import_box = QGroupBox("Update Market Data")
        import_layout = QVBoxLayout(import_box)
        btn_row = QHBoxLayout()
        self.import_btn = QPushButton("Import CSV / Excel / JSON")
        self.template_btn = QPushButton("Download Import Template (CSV)")
        btn_row.addWidget(self.import_btn)
        btn_row.addWidget(self.template_btn)
        import_layout.addLayout(btn_row)
        self.summary_label = QLabel("")
        import_layout.addWidget(self.summary_label)
        layout.addWidget(import_box)

        self.import_btn.clicked.connect(self._do_import)
        self.template_btn.clicked.connect(self._do_template)

        sources_box = QGroupBox("Configured Data Sources")
        sources_layout = QVBoxLayout(sources_box)
        self.sources_list = QListWidget()
        for s in list_sources():
            self.sources_list.addItem(f"{s['name']}  —  {s['access_method']}  —  {s['notes']}")
        sources_layout.addWidget(self.sources_list)
        layout.addWidget(sources_box)

        note = QLabel(
            "Note: this application does not scrape listing portals that restrict automated "
            "access. Use the portal's own export, or manually compiled data, and import it above."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#777; font-style: italic;")
        layout.addWidget(note)

        layout.addStretch()

    def _refresh_summary(self):
        summary = self.db.get_last_update_summary()
        total = self.db.count_listings()
        if summary:
            self.summary_label.setText(
                f"Last Updated: {summary['imported_at'][:19]}   |   "
                f"File: {summary['file_name']}   |   "
                f"New records: {summary['new_records']}   |   "
                f"Rejected: {summary['rejected_records']}   |   "
                f"Total records in database: {total}"
            )
        else:
            self.summary_label.setText(f"No imports yet. Total records in database: {total} (may include demo/sample data).")

    def _do_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select market data file", "", "Data files (*.csv *.xlsx *.xls *.json)")
        if not path:
            return
        try:
            result = import_market_data(path, self.db)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))
            return
        QMessageBox.information(
            self, "Import complete",
            f"Total rows: {result.total_rows}\nImported: {result.new_records}\nRejected: {result.rejected_records}"
        )
        self._refresh_summary()

    def _do_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save template", "market_data_template.csv", "*.csv")
        if path:
            export_template_csv(path)
            QMessageBox.information(self, "Saved", f"Template saved to:\n{path}")


class CityComparisonScreen(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Compare Indian Cities</b>"))

        controls = QHBoxLayout()
        self.bhk_filter = QComboBox()
        self.bhk_filter.addItems(["All", "1", "2", "3", "4"])
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Apartment", "Independent House", "Villa"])
        self.refresh_btn = QPushButton("Refresh")
        controls.addWidget(QLabel("BHK:")); controls.addWidget(self.bhk_filter)
        controls.addWidget(QLabel("Type:")); controls.addWidget(self.type_filter)
        controls.addWidget(self.refresh_btn)
        controls.addStretch()
        layout.addLayout(controls)
        self.refresh_btn.clicked.connect(self.refresh)

        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.chart = MplCanvas(height=3.5)
        layout.addWidget(self.chart)

        self.refresh()

    def refresh(self):
        cities = self.db.get_cities()
        headers = ["City", "Avg Price/sqft", "Avg Rent", "Rental Yield %", "Price/Rent (yrs)", "# Records"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(0)

        bhk = None if self.bhk_filter.currentText() == "All" else int(self.bhk_filter.currentText())
        ptype = None if self.type_filter.currentText() == "All" else self.type_filter.currentText()

        chart_names, chart_values = [], []

        for city in cities:
            sale = self.db.query_listings(city_id=city["id"], listing_kind="sale", property_type=ptype, bhk=bhk)
            rent = self.db.query_listings(city_id=city["id"], listing_kind="rent", property_type=ptype, bhk=bhk)
            if not sale and not rent:
                continue
            sale_df = pd.DataFrame(sale)
            rent_df = pd.DataFrame(rent)
            avg_price_sqft = sale_df["price_per_sqft"].dropna().mean() if not sale_df.empty and "price_per_sqft" in sale_df else None
            avg_rent = rent_df["monthly_rent"].dropna().mean() if not rent_df.empty and "monthly_rent" in rent_df else None
            if avg_price_sqft and avg_rent:
                # approximate using a representative area? use rent/sqft * area cancels -> use price/sqft * (rent / rent_per_sqft) not reliable.
                # Simple proxy: yield using average rent scaled to a 1000 sqft reference unit.
                avg_rent_per_sqft = rent_df["rent_per_sqft"].dropna().mean() if "rent_per_sqft" in rent_df else None
                if avg_rent_per_sqft:
                    annual_rent_per_sqft = avg_rent_per_sqft * 12
                    yield_pct = (annual_rent_per_sqft / avg_price_sqft) * 100
                    price_to_rent = avg_price_sqft / annual_rent_per_sqft if annual_rent_per_sqft else None
                else:
                    yield_pct = None
                    price_to_rent = None
            else:
                yield_pct = None
                price_to_rent = None

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(city["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"₹{avg_price_sqft:,.0f}" if avg_price_sqft else "—"))
            self.table.setItem(row, 2, QTableWidgetItem(f"₹{avg_rent:,.0f}" if avg_rent else "—"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{yield_pct:.2f}%" if yield_pct else "—"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{price_to_rent:.1f}" if price_to_rent else "—"))
            self.table.setItem(row, 5, QTableWidgetItem(str(len(sale) + len(rent))))

            if avg_price_sqft:
                chart_names.append(city["name"])
                chart_values.append(avg_price_sqft)

        if chart_names:
            city_comparison_chart(self.chart, chart_names, chart_values, "₹/sqft", "Average Sale Price/sqft by City")
