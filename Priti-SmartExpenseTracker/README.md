# Smart Expense Tracker (PWA)
> **AICA Level 2 Capstone Project**  
> **Student / Author:** Priti  
> **Target Repository:** [aiinicai/AICA-Level-2-Projects](https://github.com/aiinicai/AICA-Level-2-Projects)  
> **Live App Demo (Instant AI Testing):** [https://ais-pre-5ravbre5yjxbjldwt2tmbe-913383300241.asia-east1.run.app](https://ais-pre-5ravbre5yjxbjldwt2tmbe-913383300241.asia-east1.run.app)

---

## 🌐 Live Evaluation Link (No Setup Required)
For instant evaluation with live **Gemini AI Vision** and **AI Insights**, the ICAI team can test the fully deployed live application directly in their web browser:  
👉 **[Open Live App: Smart Expense Tracker](https://ais-pre-5ravbre5yjxbjldwt2tmbe-913383300241.asia-east1.run.app)**  
*(Includes 4 built-in test sample bills: Handwritten tea bill, shopping receipt, mutual fund SIP statement, and flight tax invoice)*

---

## 📌 Project Overview
**Smart Expense Tracker** is a full-featured Progressive Web App (PWA) designed for modern personal finance and investment management. It combines **offline-first local browser persistence** with **Gemini AI Vision** to instantly extract dates, merchants, amounts, and itemized lines from physical receipts, handwritten bills, UPI payment screenshots, and investment statements.

---

## 🚀 Key Features

1. **AI Vision Invoice & Receipt Scanner**:
   - Upload receipt photos or snap pictures with camera.
   - Extracts date, merchant name, total INR amount, and itemized line items.
   - Intelligent edge-case detection (handwritten slips, multi-item supermarket bills, blurry photo detection, duplicate alert).
   - User confirmation workflow: data is prefilled into an editable form before saving.

2. **Distinct Investment & Wealth Tracker**:
   - Keeps wealth-building SIPs, mutual funds, and equities separate from lifestyle expenses.
   - Tracks monthly and cumulative wealth accumulation.

3. **Interactive Financial Analytics & Charts**:
   - **Month-over-Month Comparison**: Compares current month spending vs. previous month with percentage badges.
   - **Category Donut Chart**: Hover-interactive SVG donut chart with category distribution and progress bars.
   - **Daily Spending Trend**: Visualizes daily outflow spikes.

4. **AI-Powered Monthly Insights & Advisory**:
   - Objective, factual plain-language monthly summary.
   - Highlights top 3 spending categories and anomalous spikes.
   - Provides 2–3 actionable, non-judgmental savings tips with estimated savings.

5. **PWA Compliance & Full Offline Functionality**:
   - Installable on desktop (Chrome/Edge) and mobile (Android/iOS).
   - Operates completely offline with local browser storage.
   - Real-time offline detection banner and CSV data export.

---

## 🛠️ Tech Stack & Architecture

- **Frontend**: React 18, TypeScript, Tailwind CSS, Lucide React Icons
- **PWA & Offline**: `vite-plugin-pwa`, Service Workers, Web App Manifest
- **Backend / API**: Express, Node.js (`server.ts`)
- **AI Engine**: `@google/genai` TypeScript SDK (`gemini-3.8-flash`)
- **Data Storage**: Client-side LocalStorage (persistent & zero-server dependency)

---

## 📦 Project Structure

```text
├── public/                 # Static assets, PWA icons, Web App Manifest
│   ├── samples/            # Test sample bills (tea bill, shopping, SIP, flight)
│   ├── icon.svg
│   └── pwa-192x192.png
├── src/
│   ├── components/         # React UI Components
│   │   ├── Dashboard.tsx
│   │   ├── DashboardCharts.tsx
│   │   ├── ScanInvoiceModal.tsx
│   │   ├── ManualExpenseModal.tsx
│   │   ├── TransactionHistory.tsx
│   │   ├── AIInsightsSection.tsx
│   │   └── PWAInstallButton.tsx
│   ├── hooks/              # Custom hooks (PWA install prompt)
│   ├── types.ts            # TypeScript interfaces
│   ├── utils/              # Storage, currency formatting, CSV export
│   ├── App.tsx             # Root Application Component
│   └── main.tsx            # React DOM Entry
├── server.ts               # Express API proxy for Gemini AI Vision & Insights
├── package.json            # Dependencies & scripts
└── vite.config.ts          # Vite & PWA configuration
```

---

## 💻 How to Run Locally

### 1. Prerequisites
- [Node.js](https://nodejs.org/) (v18 or newer)
- npm or bun

### 2. Setup
```bash
# Clone or copy project folder
cd Priti-SmartExpenseTracker

# Install dependencies
npm install

# Configure API Key (optional for AI vision features)
# Create a .env file with:
# GEMINI_API_KEY=your_api_key_here

# Run development server
npm run dev
```

Visit `http://localhost:3000` in your browser.
