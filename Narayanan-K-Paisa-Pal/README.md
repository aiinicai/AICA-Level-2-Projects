# Paisa Pal - Smart Personal Finance & Budget Tracker

Paisa Pal is a fast, responsive, and private personal finance management application built for desktop, tablet, and mobile (including PWA installation on iOS and Android).

---

## 🚀 Quick Start Guide

### Prerequisites
Make sure you have [Node.js](https://nodejs.org/) installed (version 18+ or 20+ recommended).

### 1. Extract the Project
If you downloaded `paisa-pal-source-code.zip`, unzip the folder to your preferred directory.

### 2. Install Dependencies
Open your terminal inside the project directory and run:
```bash
npm install
```

### 3. Start Development Server
```bash
npm run dev
```
Open your browser at `http://localhost:3000` (or the port shown in your terminal).

### 4. Build for Production
```bash
npm run build
```
This produces an optimized production bundle inside the `dist/` directory ready for deployment.

---

## 🛠️ Tech Stack & Architecture

- **Framework:** React 19 + TypeScript
- **Bundler & Dev Server:** Vite 6
- **Styling:** Tailwind CSS (Modern `@tailwindcss/vite` configuration)
- **Icons:** Lucide React
- **PWA Support:** `vite-plugin-pwa` with offline caching and service worker registration
- **Animations & Delight:** `canvas-confetti`
- **Data Persistence:** Local Storage with automatic quota management, JSON export/import backup

---

## 📁 Project Structure

```text
paisa-pal/
├── index.html                   # HTML entry point with PWA meta tags & splash icons
├── vite.config.ts               # Vite configuration with PWA plugin & Tailwind
├── package.json                 # Project dependencies and npm scripts
├── tsconfig.json                # TypeScript compiler settings
├── public/                      # Static assets, icons, manifest, and download bundle
│   ├── manifest.webmanifest    # PWA web app manifest
│   ├── apple-touch-icon.png     # iOS home screen icon
│   ├── favicon.png              # Browser tab icon
│   └── pwa-192x192.png          # App icon for mobile install
└── src/
    ├── main.tsx                 # App bootstrap with Service Worker & ErrorBoundary
    ├── App.tsx                  # Main app state, navigation, and modal controllers
    ├── index.css                # Global styles, fonts, and dark mode setup
    ├── types.ts                 # TypeScript interfaces (Transaction, Category, Budget, etc.)
    ├── components/              # Modular UI components
    │   ├── Navigation.tsx       # Sidebar & mobile header with tab switches
    │   ├── ErrorBoundary.tsx    # Resilient error catching & recovery screen
    │   ├── PWAInstallButton.tsx # Native install prompt & iOS Safari instructions
    │   ├── ShareTrialModal.tsx  # Trial sharing & device access guide
    │   ├── ExportCodeModal.tsx  # Download project zip & GitHub instructions
    │   ├── TransactionModal.tsx # Add/Edit transaction form
    │   └── ...
    ├── views/                   # Main application views
    │   ├── DashboardView.tsx    # Overview cards, recent activity, financial health
    │   ├── TransactionsView.tsx # Filterable transaction ledger
    │   ├── BudgetsView.tsx      # Category budgets & progress trackers
    │   ├── AnalyticsView.tsx    # Charts, monthly breakdowns, savings rate
    │   └── SettingsView.tsx     # Currency, backup/restore, dark mode, code download
    ├── utils/                   # Helper functions
    │   ├── calculations.ts      # Financial calculations & analytics
    │   └── storage.ts           # Safe localStorage wrappers & backup logic
    └── hooks/                   # Custom React hooks
        └── usePWAInstall.ts     # PWA install prompt handler & iOS detection
```

---

## 🌐 Deploying to the Web

You can easily deploy Paisa Pal for free on any modern web host:

### Vercel
1. Push your repository to GitHub.
2. Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
3. Import your GitHub repository. Vercel automatically detects Vite.
4. Click **"Deploy"**.

### Netlify
1. Go to [netlify.com](https://netlify.com) and connect your GitHub repo.
2. Build command: `npm run build`
3. Publish directory: `dist`
4. Click **"Deploy"**.

### GitHub Pages / Cloudflare Pages
Follow standard static Vite hosting instructions (`dist` output directory).

---

## 🔒 Privacy & Data Storage
All transactions and settings are stored locally on the user's device in browser storage. No financial data is sent to external servers. Users can export their complete data anytime as a `.json` backup from the Settings screen.
