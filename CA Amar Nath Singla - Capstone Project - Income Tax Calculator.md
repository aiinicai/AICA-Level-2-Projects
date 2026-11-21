# 🧮 Income Tax Calculator App
### AI-Powered Capstone Project · ICAI AICA Level 2

> A standalone, interactive Income Tax Calculator built with **Gemini AI** from one natural-language prompt. It compares tax liability under the **Old** and **New Regimes** for **AY 2026-27**.

---

## 📌 Project Overview

| | |
|---|---|
| **Programme** | ICAI – AI for Chartered Accountants (AICA) Level 2 |
| **Project Type** | Capstone Project |
| **AI Tool Used** | Google Gemini |
| **Output** | Single-file HTML web app |
| **Assessment Year** | AY 2026-27 |
| **Prepared by** | Aayush, Chartered Accountant |

---

## 🎯 Problem Statement

Every year, individual taxpayers have to choose between the **Old Tax Regime** (with deductions) and the **New Tax Regime** (lower rates, few deductions). Working out both by hand takes time and invites mistakes.

**Goal:** Use AI to build, with no hand-written code, a simple tool that computes both regimes side by side and helps the user pick the better one.

---

## ✨ Key Features

- 👤 **User inputs:** name, gross income, deductions
- ⚖️ **Dual-regime calculation:** Old vs New Regime, side by side
- 📅 **Current law:** slabs for AY 2026-27
- 🎨 **Colourful, interactive UI** with instant results
- 💾 **Standalone HTML:** runs offline in any browser, no installation needed
- 🏷️ **Branded** with the creator's name and contact details

---

## 🛠️ Tools & Technology

| Tool | Purpose |
|---|---|
| Google Gemini | Generates the complete app code from a prompt |
| Notepad / any text editor | Saves the code as an `.html` file |
| Web browser (Chrome/Edge) | Runs the app |

---

## 💬 The Prompt

```text
Create a standalone HTML app where the user will input their name, income
and deductions, and the app will calculate their income tax liability under
the old regime and the new regime for AY 2026-27. Make it colourful and
interactive, with my name and telephone number.
```

---

## 🚀 How It Was Built

1. **Prompt:** Entered the prompt above in Gemini.
2. **Generate:** Gemini looked up current tax slabs and wrote the full HTML/CSS/JS code (about 2–3 minutes).
3. **Copy:** Copied the generated code.
4. **Save:** Pasted it into Notepad and chose *File → Save As* → `income-tax-calculator.html` (Save as type: *All Files*).
5. **Run:** Double-clicked the file to open it in a browser.
6. **Use:** Entered name, income and deductions to get the tax under both regimes.

```
Prompt ➜ Gemini generates code ➜ Save as .html ➜ Open in browser ➜ Calculate
```

---

## 🧪 Validation & Test Cases

Each output was checked against a manual computation and the Income Tax Department's online calculator.

| # | Gross Income | Deductions (Old) | Old Regime Tax | New Regime Tax | Better Option | Matches Manual? |
|---|---|---|---|---|---|---|
| 1 | ₹7,00,000 | ₹1,50,000 | | | | ☐ |
| 2 | ₹12,00,000 | ₹2,00,000 | | | | ☐ |
| 3 | ₹15,00,000 | ₹2,50,000 | | | | ☐ |
| 4 | ₹25,00,000 | ₹3,00,000 | | | | ☐ |

**Checklist of points verified:**
- [ ] Slab rates for both regimes
- [ ] Standard deduction
- [ ] Section 87A rebate
- [ ] Deduction caps (e.g. 80C ≤ ₹1.5 lakh), applied in the Old Regime only
- [ ] Surcharge (where applicable)
- [ ] Health & Education Cess @ 4%

---

## 🔁 Iterative Improvements (Prompt Refinement)

Follow-up prompts used to improve the first version:

| Version | Follow-up Prompt | Improvement |
|---|---|---|
| v1.0 | Base prompt | Working calculator for both regimes |
| v1.1 | *"Highlight the regime with lower tax and show the savings"* | Regime recommendation |
| v1.2 | *"Cap deductions at statutory limits and show a warning if exceeded"* | Accuracy and validation |
| v1.3 | *"Add age category (below 60 / senior / super senior)"* | Correct basic exemption |
| v1.4 | *"Add a print/download summary button"* | Client-ready output |

---

## 📸 Screenshots

| Input Screen | Result Screen |
|---|---|
| ![Input](screenshots/input.png) | ![Result](screenshots/result.png) |

> Replace with your own screenshots in a `screenshots/` folder.

---

## 📂 Project Structure

```
income-tax-calculator/
├── income-tax-calculator.html   # The app
├── README.md                    # This document
└── screenshots/
    ├── input.png
    └── result.png
```

---

## 💡 Learnings

- **Prompt quality drives output quality.** Clear inputs, outputs and constraints give better code.
- **AI speeds up the work, but the CA checks it.** The AI's output must be tested against the law before use.
- **Iterate.** Small follow-up prompts fix gaps faster than rewriting the whole prompt.
- **No coding background needed.** A CA can now build practical client tools on their own.

---

## ⚠️ Limitations

- Built for individual resident taxpayers. Special-rate income (capital gains, lottery etc.) is not covered.
- Results depend on the slab logic the AI generated, so re-verify after every Finance Act change.
- For illustration only. Not a substitute for professional tax advice.

---

## 🔮 Future Scope

- Separate heads of income (salary, house property, business, capital gains)
- HRA and home-loan interest calculators
- PDF tax computation for clients
- Multi-year comparison (AY 2025-26 vs 2026-27)
- Hosting online and sharing a link with clients

---

## 🏁 Conclusion

The project shows that **"Chartered Accountants with AI will lead Chartered Accountants without AI."** One well-structured prompt produced a working, client-friendly tax tool in minutes, with the CA's expertise making sure it is accurate.

---

<p align="center">
  <b>Aayush · Chartered Accountant</b><br>
  📞 +91-XXXXXXXXXX · ✉️ your.email@example.com<br>
  <i>ICAI AICA Level 2 – Capstone Project</i>
</p>
