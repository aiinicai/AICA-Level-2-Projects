# Reviewer Quick Guide — NiveshIQ

Welcome! Use this guide to quickly test and review this personal finance & risk-planning application.

---

### 1. Which File to Click / How to Run

- **Instant Browser Preview (Zero Setup)**:
  👉 Double-click **`1NiveshIQ.htm`**.
  It opens instantly in Chrome, Edge, or Firefox. No installations or terminal commands required.

- **Full React App (Developer Mode)**:
  Open a terminal in this folder and run:
  ```bash
  npm install
  npm run dev
  ```
  Then open **`http://localhost:5173`** in your browser.

---

### 2. Understanding the Folder Structure

All source logic lives inside **`src/`**:

- **`src/engines/`**: Core financial algorithms (risk capacity, appetite scoring, asset allocation, and goal calculators).
- **`src/screens/`**: 7 step-by-step user journey screens (Welcome, Profile, Portfolio, Risk Assessment, Strategy, Action Plan, and AI Explore).
- **`src/components/`**: Reusable UI widgets (risk gauge, portfolio charts, stepper, and AI panel).
- **`src/data/`**: Source mock data ([`demoInvestor.ts`](file:///c:/Users/happy/OneDrive/Desktop/capstone%20project/src/data/demoInvestor.ts)) and benchmark market assumptions ([`constants.ts`](file:///c:/Users/happy/OneDrive/Desktop/capstone%20project/src/data/constants.ts)).
- **`src/services/`**: Mock broker/banking integrations and AI provider logic.
- **`src/hooks/useAppState.ts`**: Centralized reactive state management.
- **`android/`**: Capacitor native Android wrapper to package the app as an APK.

---

### 3. Automated Tests
Run `npm test` to verify all 8 financial engine unit tests.
