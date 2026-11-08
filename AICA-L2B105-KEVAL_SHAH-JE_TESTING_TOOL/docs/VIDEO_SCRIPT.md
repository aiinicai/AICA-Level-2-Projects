# Video Script: Journal Entry Testing Tool

**Target length:** about 6 minutes · **Format:** slides → live demo → slides

All numbers below come from the bundled demo file (`sample_data/sample_GL.xlsx`).
The demo data is generated with a fixed seed, so you will see the same results
on screen.

---

## Before you hit record (checklist)

- [ ] Delete `je_config.json` (if present) so the default settings load.
- [ ] Delete old files in `output/`.
- [ ] Close every other window. Set the screen to 1920×1080 and zoom Excel to about 110 %.
- [ ] Open a terminal in the project folder: `python je_testing_app.py`.
- [ ] Have the slide deck open in another window.
- [ ] Do one practice run, delete the output, then record.

---

## Scene 1: Introduction (0:00 – 0:40) · *Slide 1–2*

> "Hello, I'm Keval Shah, and this is my capstone project for the AICA Level 2
> batch: a **Journal Entry Testing tool built for auditors of SAP clients**.
>
> Under **SA 240**, every audit carries a presumed risk that management may
> override controls, and the standard asks us to test journal entries for it.
> In practice we export lakhs of GL lines from SAP and filter them by hand in
> Excel. That takes days, and the sample we pick is hard to justify to a reviewer."

## Scene 2: The idea (0:40 – 1:30) · *Slide 3–4*

> "So I built a tool that tests **100 % of the journals** against **12 simple
> rules**. Each rule answers one of four questions:
>
> - **When** was it posted? On a Sunday, a public holiday, at month-end, or
>   back-dated?
> - **Who** posted it? A privileged IT user, a super-user like the CFO, or was it
>   a manual journal?
> - **How much?** A round-sum amount, or a large amount above one crore?
> - **What** does the narration say? Is it missing, vague like 'adjustment', or
>   does it contain red-flag words like 'plug' or 'balancing figure'?
>
> Every rule has a weight. A journal's **risk score** is simply the total of the
> weights it triggers, so anyone can re-perform it on a calculator. The score
> places the entry in Low, Medium, High or Critical."

## Scene 3: Live demo, running the tool (1:30 – 3:00) · *Screen recording*

| Do this on screen | Say this |
|---|---|
| Show the app window | "This is the desktop app. It runs completely offline, so client data never leaves the laptop." |
| Click **Create sample GL** → OK | "For this demo I'll create a sample SAP GL. It's fictitious data in the standard SAP layout: Document Number, Posting Date, User Name, Text and so on." |
| Click **Check column mapping** | "The tool recognises SAP headings automatically. Document Number becomes the journal ID, User Name becomes the user, Text becomes the narration. Green means found." |
| Click **⚙ Settings** → show **Users** tab | "In Settings I enter the client's details: privileged IT users and super-users from the SAP access review. Here ADMIN01 and CFO01." |
| Show **Thresholds** tab | "Non-working day is Sunday. Large amount is one crore. Round sum is multiples of one lakh. These should be set from materiality." |
| Show **Risk Weights** tab → **Cancel** | "And here are the 12 weights, all editable. No coding needed." |
| Click **▶ Run JE Testing** | "Now I click Run." |
| Point at the result panel | "In a few seconds: **612 lines, 306 journal entries**, and debits equal credits, so the data is complete and balanced. **2 Critical, 1 High, 2 Medium** and 301 Low. So instead of 306 entries, the team focuses on 3 high-risk ones, plus a sample of **40** for coverage." |

## Scene 4: Live demo, the Excel workpaper (3:00 – 5:00)

| Do this on screen | Say this |
|---|---|
| Click **Open Workpaper** → **Summary** sheet | "The output is a ready-to-file Excel workpaper. The Summary shows the population, the balance check and journals by risk band." |
| **Data Quality** sheet | "Data Quality confirms the extract is reliable: no blank users, no blank dates, and every journal nets to zero. SA 500 requires us to check this before relying on the data." |
| **Risk Register** sheet | "The Risk Register lists every journal, sorted by score, with the rules it triggered." |
| **Explainability** sheet, row for **4900000301** | "This is the most important sheet. Journal **4900000301**: posted by **CFO01** on **31 March**, entered **10 days later**, a manual entry of exactly **₹1 crore**, narration 'Year end topside adjustment **as instructed**'. It scores **115**, Critical. The breakdown shows exactly why: month-end +10, back-dated +15, super-user +25, manual +15, round +10, large +15, red-flag keyword +25. It also gives the assertion at risk, the SA reference and the audit procedure to perform." |
| Second row (**ADMIN01**, 06-07-2025) | "The second Critical: an IT admin posting a manual ₹25 lakh entry on a **Sunday** with the narration just 'adjustment'. IT users shouldn't be posting journals at all." |
| **Samples** sheet | "Samples: the top 25 by risk score, plus 15 picked at random from the rest, so the selection is not fully predictable, as SA 240 expects." |
| **Rule Frequency** / **Methodology** | "Rule Frequency shows which rules fired most. The Methodology sheet documents the approach for the audit file." |

## Scene 5: Real-world use and close (5:00 – 6:00) · *Slide 5–6*

> "On a real engagement you export the GL from SAP using FBL3N or FAGLL03, set
> the client's users, holidays and thresholds, and run it. I tested it on a real
> SAP extract and it mapped every column automatically and finished in about
> ten seconds.
>
> To be clear, a flag is a **prompt to investigate, not a conclusion**. The tool
> does the filtering. The judgement stays with the auditor.
>
> The full code is on GitHub. It's open source, written in Python, and contains
> no client data. Thank you."

---

## Tips

- Speak slowly. Pause for one second after each click so viewers can follow.
- Zoom into the Explainability row (Ctrl + mouse wheel) while you read it out.
- If you go over time, trim Scene 4 to Summary → Explainability → Samples only.
