# ⚡ Netcrafty AI · Advertising Costing & AI Diagnostic Studio

A modern, colorful Python software application that implements the canonical **Netcrafty 12-Month Multi-Channel Advertising Product-Costing Engine** with automated unit economics diagnostics and **Google Gemini Generative AI** financial auditing.

---

## 🌟 Key Highlights

1. **Exact Netcrafty Calculation Engine**:
   - **4 Channels**: Website COD (`wc`), Website Prepaid (`wp`), WhatsApp COD (`ac`), WhatsApp Prepaid (`ap`).
   - **Lead Split Automation**: Sourcing lead pools automatically derive COD and Prepaid lead counts from Prepaid % input.
   - **Prepaid Linking**: Prepaid channels share critical operational parameters (`confirm`, `ad`, `product`, `packing`, `postage`, `salary`, `capacity`, `uplift`) with their COD channel for the same month, keeping delivery % and price independent.
   - **Staff Allocation**: Website and WhatsApp staffing isolated with integer ceiling headcount `ceil(leads / capacity)`.
   - **Transit Uplift & Cash-Flow Deferral**: Accounts for transit damage buffer and gross delivery revenue carried to subsequent months.
   - **Shared Overhead**: Dynamically allocated by delivered order proportions (with fallback to equal share when deliveries are 0).

2. **Automated AI Diagnostic Engine ("Figures to Take Care Of")**:
   - **Algorithmic Heuristic Audit**: Instantly scores financial viability (0–100) and detects:
     - 🚨 **Critical Red Flags**: Severe RTO leaks (delivery < 60%), high CAC burn (ad spend > 40% of revenue), fixed overhead dilution (> ₹300/order), 12-month net loss traps.
     - ⚠️ **Operational Warnings**: Staffing discontinuities (e.g., 51 leads requiring 2 full employees), transit revenue lag.
     - 💡 **Strategic Opportunities**: Quantified profit upside from shifting COD to Prepaid.
   - **Live Generative AI (Google Gemini)**: Complete CFO turnaround roadmap, ranked figure intervention priorities, and interactive Q&A chat.

3. **Vibrant & Engaging Dashboard GUI**:
   - Built with **Streamlit** and **Plotly**.
   - Glassmorphism dark header, color-coded channel badges, glowing metric cards.
   - Cumulative profit curve with break-even zero line, monthly revenue vs. cost comparisons, cost composition donut, and funnel conversion waterfalls.

4. **API Integration Key Tab**:
   - Secure local storage for **Google Gemini API Key** (`api_config.json`).
   - Live **Test Connection** button.
   - Model selection (`gemini-3.8-flash` [default], `gemini-3.8-pro`, `gemini-2.5-flash`, custom).
   - Customizable AI advisor tone and persona.

5. **Export Capabilities**:
   - One-click export to **Detailed CSV** and formatted **Microsoft Excel (.xlsx)**.

---

## 🚀 How to Run

### Method 1: 1-Click Windows Launcher (Easiest)
Double-click `run.bat` in this folder. It will launch the Streamlit server and open your default browser.

### Method 2: Terminal / Command Line
Run the following in PowerShell or Command Prompt:

```powershell
python -m streamlit run app.py
```

The application will start and automatically open at `http://localhost:8501`.

---

## 📑 Application Tabs

| Tab | Purpose |
| :--- | :--- |
| **📊 Executive Dashboard** | High-level KPIs, 12-month cumulative P&L trajectory, revenue vs cost comparison, cost composition donut, and multi-channel conversion funnels. |
| **🎛️ Scenario & Month Studio** | Month selector, lead splits, channel unit economics, preset scenario picker (Baseline, D2C Scale Engine, High COD Crisis, Prepaid-First Strategy), and Month 1 cascade. |
| **📑 12-Month Detailed Matrix** | Month-by-month financial sheet matching the Netcrafty table with mathematical calculation formulas side-by-side with values in ₹. CSV and Excel downloads. |
| **🤖 AI Financial Doctor** | Live diagnostic health score (0–100), Red Flags, Warnings, Growth Opportunities, and Live Gemini AI CFO Audit + Interactive Chat. |
| **🔑 API Integration & AI Setup** | Configure Google Gemini API key, test connection, choose AI model and advisor persona. |

---

## 🔑 Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com).
2. Sign in with your Google account.
3. Click **Get API key** and generate a new key.
4. Open the **🔑 API Integration & AI Setup** tab in Netcrafty AI, paste your key, click **Test Connection**, and click **Save API Configuration**.

---

## 📁 File Structure

```
netcrafty/ai/
│
├── app.py              # Main Streamlit Dashboard Application
├── engine.py           # Netcrafty 4-channel, 12-month calculation engine
├── ai_analyzer.py      # Heuristic diagnostics + Gemini Generative AI
├── presets.py          # Scenario templates (D2C Scale, COD Crisis, etc.)
├── run.bat             # 1-click Windows launcher
├── requirements.txt    # Python dependencies
├── api_config.json     # Saved local API settings (created on save)
└── README.md           # Documentation
```
