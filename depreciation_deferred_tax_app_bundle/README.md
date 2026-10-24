# TaxShield CA — Multi-Company & Multi-Year WDV Roll-Forward Suite (v3.0)

This bundle includes both the **Interactive Browser Web Application** and the **Standalone Python Desktop Application (with 1-Click Windows `.exe` Compiler)**.

## 1. What's New in v3.0: Dynamic Multi-Year WDV Roll-Forward & Roll-Back
- **Change Financial Year (`FY 2022-23` to `FY 2034-35`)**:
  - Use the **Financial Year** dropdown or click **`← Prev` / `Next →`** in the top bar (or click **Switch to FY** on any row in Tab 5) to dynamically roll the entire fixed asset portfolio forward or backward across years.
  - **Prior Years (e.g., `FY 2022-23`, `2023-24`, `2024-25`)**: Assets acquired in later years (such as `2025-26`) are automatically marked as `Future Addition (Not Yet Active)` with ₹0 WDV/Depreciation, while earlier assets (such as the Factory Building acquired in `2022-04-01`, Furniture in `2023-04-01`, and Vehicle in `2024-04-01`) compute their exact historical Opening WDV, CY Depreciation, and Closing WDV from their acquisition date.
  - **Subsequent Years (e.g., `FY 2026-27`, `2027-28`, `2028-29`...)**: Every asset's Closing Book WDV and Closing Tax WDV from the previous year automatically roll forward as the Opening Book WDV and Opening Tax WDV of the next year, and Opening Net DTL/(DTA) updates automatically.

## 2. How to Build the Standalone Windows `.exe` File
1. Extract this ZIP folder on your Windows PC.
2. Double-click **`build_windows_exe.bat`** (or run `python build_exe.py`).
3. PyInstaller will compile `taxshield_ca_desktop.py` into `dist\TaxShield_CA_Depreciation_Suite.exe`.
