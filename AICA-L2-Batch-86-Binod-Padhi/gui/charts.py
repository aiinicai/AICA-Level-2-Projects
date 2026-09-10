"""
gui/charts.py
Reusable Matplotlib chart widgets embedded in PyQt6 via FigureCanvasQTAgg.
"""

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    def __init__(self, width=5, height=3.2, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)


def price_vs_fair_value_chart(canvas: MplCanvas, asking_price, fair_low, fair_high):
    ax = canvas.ax
    ax.clear()
    labels = ["Fair Value\nRange (low-high)", "Asking Price"]
    ax.bar(labels[0], fair_high - fair_low, bottom=fair_low, color="#4CAF50", alpha=0.7)
    ax.bar(labels[1], asking_price, color="#FF7043" if asking_price > fair_high else "#42A5F5")
    ax.set_ylabel("₹")
    ax.set_title("Asking Price vs Estimated Fair Value")
    canvas.draw()


def rent_range_chart(canvas: MplCanvas, low, median, high):
    ax = canvas.ax
    ax.clear()
    ax.bar(["Low (P25)", "Median", "High (P75)"], [low, median, high], color=["#90CAF9", "#42A5F5", "#1E88E5"])
    ax.set_ylabel("₹ / month")
    ax.set_title("Estimated Market Rent Range")
    canvas.draw()


def yield_comparison_chart(canvas: MplCanvas, property_yield, locality_median_yield):
    ax = canvas.ax
    ax.clear()
    ax.bar(["This Property", "Locality Median"], [property_yield, locality_median_yield],
           color=["#FFB300", "#8E24AA"])
    ax.set_ylabel("Gross Rental Yield (%)")
    ax.set_title("Rental Yield Comparison")
    canvas.draw()


def city_comparison_chart(canvas: MplCanvas, city_names, values, ylabel, title):
    ax = canvas.ax
    ax.clear()
    ax.bar(city_names, values, color="#26A69A")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.tick_params(axis='x', rotation=30)
    canvas.draw()


def trend_chart(canvas: MplCanvas, periods, price_series=None, rent_series=None, title="Historical Trend"):
    ax = canvas.ax
    ax.clear()
    if price_series:
        ax.plot(periods, price_series, marker="o", label="Price", color="#3F51B5")
    if rent_series:
        ax2 = ax.twinx()
        ax2.plot(periods, rent_series, marker="s", label="Rent", color="#E53935")
        ax2.set_ylabel("Rent (₹)")
    ax.set_title(title)
    ax.set_ylabel("Price (₹)")
    ax.legend(loc="upper left")
    canvas.draw()
