"""
gui/main_window.py
Top-level QMainWindow: tabbed navigation across the app's screens.
"""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from config import APP_NAME, DISCLAIMER
from database.database import Database
from database.seed_data import run_full_seed

from gui.property_input import PropertyInputScreen
from gui.valuation_result import ValuationResultScreen
from gui.market_dashboard import MarketDataScreen, CityComparisonScreen
from valuation.calculations import run_valuation


class HomeScreen(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel(f"<h1>{APP_NAME}</h1>")
        subtitle = QLabel(
            "Estimate whether a residential property in India is overpriced, fairly "
            "priced, or underpriced — using comparable listings, rental yield, and "
            "price-to-rent analysis. Use the tabs above to get started."
        )
        subtitle.setWordWrap(True)
        disclaimer = QLabel(DISCLAIMER)
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("color:#777; font-style: italic; margin-top: 24px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(disclaimer)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 850)

        self.db = Database()
        run_full_seed(self.db, include_demo_listings=True)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.home_screen = HomeScreen()
        self.property_input_screen = PropertyInputScreen(self.db)
        self.valuation_result_screen = ValuationResultScreen()
        self.market_data_screen = MarketDataScreen(self.db)
        self.city_comparison_screen = CityComparisonScreen(self.db)

        self.tabs.addTab(self.home_screen, "Home")
        self.tabs.addTab(self.property_input_screen, "Property Valuation")
        self.tabs.addTab(self.valuation_result_screen, "Valuation Result")
        self.tabs.addTab(self.city_comparison_screen, "City Comparison")
        self.tabs.addTab(self.market_data_screen, "Market Data")

        self.property_input_screen.valuation_requested.connect(self._on_valuation_requested)

    def _on_valuation_requested(self, property_input, city_name):
        # Persist the subject property, then run the valuation pipeline.
        property_id = self.db.insert_property(property_input.to_db_dict())
        property_input.id = property_id

        locality_name = self.property_input_screen.locality_combo.currentText()

        output = run_valuation(property_input, self.db, city_name=city_name)
        output["result"].property_id = property_id
        self.db.save_valuation(output["result"].to_db_dict())

        self.valuation_result_screen.display(property_input, city_name, output, locality_name, db=self.db)
        self.tabs.setCurrentWidget(self.valuation_result_screen)
