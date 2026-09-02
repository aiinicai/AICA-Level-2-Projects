# Contributing to GrantSetu

Thank you for your interest in contributing to **GrantSetu**! This project is designed as an open-source NGO Governance & Statutory Audit ERP for Indian non-profits.

## 🚀 How to Contribute

1. **Fork the Repository**: Create your own copy of the project on GitHub.
2. **Clone Locally**:
   ```bash
   git clone https://github.com/<your-username>/grantsetu-ngo-erp.git
   cd grantsetu-ngo-erp
   ```
3. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. **Install Dependencies**:
   ```bash
   npm install
   ```
5. **Make your changes & run linting**:
   ```bash
   npm run lint
   npm run build
   ```
6. **Commit & Push**:
   ```bash
   git commit -m "Add new feature description"
   git push origin feature/my-new-feature
   ```
7. **Submit a Pull Request**: Open a PR against the `main` branch with a clear summary of your changes.

## 📐 Coding Standards & Guidelines

- **Component Design**: Keep React components modular inside `src/components/`.
- **Styling**: Follow the custom CSS design system established in `src/index.css` (Glassmorphism, dark/light contrast tokens, responsive layouts).
- **Statutory Rules**: Ensure all new ledger or compliance features conform strictly to ICAI standards, FCRA 2010 regulations, or GFR 2017 rules.
- **Linting**: Ensure code passes `npm run lint` without errors.

## 🐛 Reporting Bugs

If you find a bug or issue, please open a GitHub Issue with:
- Clear steps to reproduce
- Expected vs actual behavior
- Browser / Desktop environment details
