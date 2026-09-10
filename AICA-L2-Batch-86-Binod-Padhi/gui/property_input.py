"""
gui/property_input.py
Property Valuation input screen — collects location, property, and
financial details, then triggers the valuation pipeline.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton,
    QScrollArea, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from database.models import PropertyInput


class PropertyInputScreen(QWidget):
    valuation_requested = pyqtSignal(object, str)  # (PropertyInput, city_name)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()
        self._load_states()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, stretch=1)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)

        # --- Location group ---
        loc_box = QGroupBox("Location")
        loc_form = QFormLayout(loc_box)
        self.state_combo = QComboBox()
        self.city_combo = QComboBox()
        self.locality_combo = QComboBox()
        self.pincode_edit = QLineEdit()
        self.state_combo.currentIndexChanged.connect(self._load_cities)
        self.city_combo.currentIndexChanged.connect(self._load_localities)
        loc_form.addRow("State:", self.state_combo)
        loc_form.addRow("City:", self.city_combo)
        loc_form.addRow("Locality:", self.locality_combo)
        loc_form.addRow("Pin code (optional):", self.pincode_edit)
        layout.addWidget(loc_box)

        # --- Property group ---
        prop_box = QGroupBox("Property Details")
        prop_form = QFormLayout(prop_box)
        self.property_type_combo = QComboBox()
        self.property_type_combo.addItems(["Apartment", "Independent House", "Villa"])
        self.new_resale_combo = QComboBox()
        self.new_resale_combo.addItems(["Resale", "New"])
        self.bhk_combo = QComboBox()
        self.bhk_combo.addItems(["1", "2", "3", "4", "5+"])
        self.carpet_area = QDoubleSpinBox(); self.carpet_area.setRange(0, 50000); self.carpet_area.setSuffix(" sqft")
        self.builtup_area = QDoubleSpinBox(); self.builtup_area.setRange(0, 50000); self.builtup_area.setSuffix(" sqft")
        self.floor = QSpinBox(); self.floor.setRange(0, 150)
        self.total_floors = QSpinBox(); self.total_floors.setRange(0, 150)
        self.age_years = QDoubleSpinBox(); self.age_years.setRange(0, 100); self.age_years.setSuffix(" yrs")
        self.furnishing_combo = QComboBox()
        self.furnishing_combo.addItems(["Unfurnished", "Semi-furnished", "Furnished"])
        self.parking_check = QCheckBox("Parking available")
        self.lift_check = QCheckBox("Lift available")
        self.gated_check = QCheckBox("Gated community")

        prop_form.addRow("Property type:", self.property_type_combo)
        prop_form.addRow("New / Resale:", self.new_resale_combo)
        prop_form.addRow("BHK:", self.bhk_combo)
        prop_form.addRow("Carpet area:", self.carpet_area)
        prop_form.addRow("Built-up area:", self.builtup_area)
        prop_form.addRow("Floor:", self.floor)
        prop_form.addRow("Total floors:", self.total_floors)
        prop_form.addRow("Age of property:", self.age_years)
        prop_form.addRow("Furnishing:", self.furnishing_combo)
        prop_form.addRow("", self.parking_check)
        prop_form.addRow("", self.lift_check)
        prop_form.addRow("", self.gated_check)
        layout.addWidget(prop_box)

        # --- Financial group ---
        fin_box = QGroupBox("Financial Information")
        fin_form = QFormLayout(fin_box)

        def money_spin(maximum=1_000_000_000):
            s = QDoubleSpinBox(); s.setRange(0, maximum); s.setPrefix("₹ "); s.setGroupSeparatorShown(True)
            s.setDecimals(0)
            return s

        self.asking_price = money_spin()
        self.expected_rent = money_spin(10_000_000)
        self.maintenance_month = money_spin(1_000_000)
        self.property_tax_year = money_spin(1_000_000)
        self.insurance_year = money_spin(1_000_000)
        self.vacancy_pct = QDoubleSpinBox(); self.vacancy_pct.setRange(0, 100); self.vacancy_pct.setSuffix(" %"); self.vacancy_pct.setValue(5)
        self.brokerage = money_spin(10_000_000)
        self.stamp_duty = money_spin(50_000_000)
        self.renovation_cost = money_spin(50_000_000)

        fin_form.addRow("Asking price:", self.asking_price)
        fin_form.addRow("Expected monthly rent:", self.expected_rent)
        fin_form.addRow("Maintenance/month:", self.maintenance_month)
        fin_form.addRow("Property tax/year:", self.property_tax_year)
        fin_form.addRow("Insurance/year:", self.insurance_year)
        fin_form.addRow("Expected vacancy:", self.vacancy_pct)
        fin_form.addRow("Brokerage:", self.brokerage)
        fin_form.addRow("Registration/stamp duty:", self.stamp_duty)
        fin_form.addRow("Renovation cost:", self.renovation_cost)
        layout.addWidget(fin_box)
        layout.addStretch()

        # --- Submit button: fixed footer, ALWAYS visible (outside the
        # scroll area) so it never scrolls out of view on smaller windows.
        footer = QWidget()
        footer.setStyleSheet("background-color: #f0f0f0; border-top: 1px solid #ccc;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        self.validation_hint = QLabel("")
        self.validation_hint.setStyleSheet("color: #C62828;")
        self.submit_btn = QPushButton("Run Valuation Analysis")
        self.submit_btn.setMinimumHeight(36)
        self.submit_btn.setStyleSheet(
            "font-weight: bold; padding: 8px 20px; background-color: #1565C0; "
            "color: white; border-radius: 4px;"
        )
        self.submit_btn.clicked.connect(self._on_submit)
        footer_layout.addWidget(self.validation_hint)
        footer_layout.addStretch()
        footer_layout.addWidget(self.submit_btn)
        outer.addWidget(footer, stretch=0)

    # ------------------------------------------------------------------
    def _load_states(self):
        self.state_combo.clear()
        for s in self.db.get_states():
            self.state_combo.addItem(s["name"], s["id"])

    def _load_cities(self):
        self.city_combo.clear()
        state_id = self.state_combo.currentData()
        cities = [c for c in self.db.get_cities()]
        # get_cities returns all with state_name; filter client-side for simplicity
        state_name = self.state_combo.currentText()
        for c in cities:
            if c["state_name"] == state_name:
                self.city_combo.addItem(c["name"], c["id"])

    def _load_localities(self):
        self.locality_combo.clear()
        city_id = self.city_combo.currentData()
        if not city_id:
            return
        for loc in self.db.get_localities(city_id):
            self.locality_combo.addItem(loc["name"], loc["id"])

    # ------------------------------------------------------------------
    def _on_submit(self):
        self.validation_hint.setText("")
        if not self.city_combo.currentData() or not self.locality_combo.currentData():
            self.validation_hint.setText("Please select a city and locality.")
            QMessageBox.warning(self, "Missing information", "Please select a city and locality.")
            return
        if self.asking_price.value() <= 0:
            self.validation_hint.setText("Please enter an asking price.")
            QMessageBox.warning(self, "Missing information", "Please enter an asking price.")
            return

        bhk_text = self.bhk_combo.currentText().replace("+", "")
        try:
            bhk = int(bhk_text)
        except ValueError:
            bhk = 5

        prop = PropertyInput(
            city_id=self.city_combo.currentData(),
            locality_id=self.locality_combo.currentData(),
            property_type=self.property_type_combo.currentText(),
            bhk=bhk,
            carpet_area=self.carpet_area.value(),
            builtup_area=self.builtup_area.value() or self.carpet_area.value(),
            asking_price=self.asking_price.value(),
            expected_rent=self.expected_rent.value(),
            new_or_resale=self.new_resale_combo.currentText(),
            floor=self.floor.value(),
            total_floors=self.total_floors.value(),
            age_years=self.age_years.value(),
            furnishing=self.furnishing_combo.currentText(),
            parking=self.parking_check.isChecked(),
            lift=self.lift_check.isChecked(),
            gated_community=self.gated_check.isChecked(),
            pincode=self.pincode_edit.text() or None,
            maintenance_month=self.maintenance_month.value(),
            property_tax_year=self.property_tax_year.value(),
            insurance_year=self.insurance_year.value(),
            vacancy_pct=self.vacancy_pct.value(),
            brokerage=self.brokerage.value(),
            stamp_duty=self.stamp_duty.value(),
            renovation_cost=self.renovation_cost.value(),
        )
        self.valuation_requested.emit(prop, self.city_combo.currentText())
