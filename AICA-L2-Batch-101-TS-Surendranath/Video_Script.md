# Video Presentation Script (about 11 minutes)
CA T S Surendranath · Batch AICA-L2B101, Chennai

**Set-up before recording**
- Open `YearEnd_Tax_Recompute_Model.xlsx` with the zoom at 110–120%.
- Open the **ICAI AI Agent** in a browser tab, with two different models ready (two tabs or two new chats). Start fresh chats so the answers are not influenced by earlier messages.
- Open a Command Prompt in the project folder for the Python check (Scene 6B).
- Turn on your webcam so your face shows in a small corner bubble while the screen is shared. OBS Studio, Loom, Zoom (record yourself) and PowerPoint's *Record* feature all do this.
- Speak slowly. You can read from this script on a second screen or on paper.
- Words in *[square brackets]* are actions; everything else is what you say.
- **Do a practice run first.** AI answers vary each time. Whatever the AI says, the *AI_Live_Demo* sheet tells you the correct treatment, so you will always know what to say.

---

## Scene 1: Introduction (face full screen, 45 sec)

"Good morning. I am CA T S Surendranath, membership number [______], from Chennai, Batch L2B101.

This is my capstone project for the AICA Level 2 course. The title is **AI-Assisted Year-End Adjustment Tracker with Automatic Income Tax Recomputation**.

Every year, while finalising accounts, we pass many entries after the draft is ready: management entries, auditor's observations and final closing entries. Each one changes profit, and so it changes the income tax computation, current tax and deferred tax. We usually redo the computation by hand every time. This takes hours, and sometimes the final Balance Sheet does not match the final tax computation.

My project solves this by combining **AI for judgement-heavy tasks** with **an Excel model for the calculations**. You will see the AI working live in this video.

One important point: as ICAI requires, **no client or confidential data** has been entered into any AI tool. Everything you see is dummy data."

## Scene 2: The idea (screen: Guide sheet, 40 sec)

*[Share screen. Show the Guide sheet.]*

"The model has one simple rule: **type each adjustment only once**. Everything else flows from it: the trial balance, Profit and Loss, Balance Sheet, income tax computation, deferred tax and the checks.

AI does three jobs: it **classifies the tax treatment** of each entry, it **helped build the formulas**, and it **writes the client explanation**."

## Scene 3: Settings and Trial Balance (50 sec)

*[Click Settings.]*

"This is a dummy company, Sunrise Textiles Private Limited, for FY 2025-26, under section 115BAA. The tax rate is 25.168%.

This is the **Tax Nature list**. Every adjustment gets one of these six natures. For example, 43B items are 100% added back as a timing difference, a TDS default is 30% added back, and penalties are permanent disallowances."

*[Click Trial_Balance.]*

"This is the unadjusted trial balance. The adjustments flow in automatically, and the total is zero."

## Scene 4: Adjustment Register (1 min)

*[Click Adjustments.]*

"This is the heart of the project. There are 12 year-end entries in three versions: V1 is the draft, V2 is the audit observations, and V3 is the final close.

For each entry I enter the ledgers, the amount and the tax nature. The model calculates the impact on profit, the tax add-back, the impact on taxable income and the impact on tax."

*[Scroll right to the 'AI suggestion' column.]*

"These tax natures were first suggested by AI, and I verified each one. Now let me show you this **live**."

## Scene 5: LIVE AI DEMO (2 min 30 sec) ⭐ the most important scene

*[Click AI_Live_Demo. Point to the four new entries.]*

"Suppose four more entries come in at the last minute: leave encashment, interest on late GST, agent commission without TDS, and a donation to a political party."

*[Copy the prompt in cell B11. Switch to the ICAI AI Agent and paste it into **Model 1**. Press Enter. Then paste the same prompt into **Model 2**.]*

"I am using the ICAI AI Agent, which gives access to several AI models. I have asked two different models to classify each entry, with the section and the deferred tax effect. Let us compare them."

*[Show both answers side by side. Read the key points briefly. Point out where the two models agree and where they differ.]*

"Leave encashment: 43B, allowed on payment. Agent commission: 30% disallowed under 40(a)(ia). Both are correct."

**Then check the two 'watch' items and say whichever applies:**

- **GST interest.** If the AI called it a penalty, say: *"Here I disagree with the AI. Interest for delayed GST is compensatory, not a penalty, so it is generally allowable. I will correct this."* If the AI said allowable, say: *"Correct. Interest is compensatory, not a penalty."*
- **Political donation.** If the AI suggested a deduction under 80GGB, say: *"This is where the CA's judgement matters. Our company has opted for 115BAA, and under 115BAA Chapter VI-A deductions like 80GGB are not available. So it is fully disallowed. The AI missed the link between the two sections."* If the AI got it right, say: *"Correct. It has correctly linked 115BAA with the denial of 80GGB. Still, I always verify this kind of point."*

*[Now paste the Trap 2 prompt from AI_Live_Demo cell B26 into one model.]*

"One more test: new looms of 40 lakh, put to use in February, for a 115BAA company."

- If the AI claims 20% additional depreciation, say: *"The AI correctly applied the half rate for less than 180 days, but it also claimed additional depreciation of 4 lakh. Under 115BAA, additional depreciation u/s 32(1)(iia) is not available. Accepting this would understate tax by about one lakh rupees."*
- If the AI gets it right, say: *"Correct. It has excluded additional depreciation because of 115BAA. Good, but still verified."*

"So AI gives me a fast first draft. I review it and take the final decision. **AI assists; the CA decides.**"

*[Go to Adjustments, rows 17–20 (entries A13–A16, marked LIVE DEMO). They are already filled in. In column J (Include?), change each N to Y.]*

## Scene 6: Everything updates (1 min 30 sec)

*[Click Checks.]*

"As soon as I switched them on, everything recalculated:
- Profit before tax went from 47.75 lakh to **43.57 lakh**.
- Total income went from 63.70 lakh to **62.12 lakh**.
- Current tax is now **15.63 lakh**.
- The deferred tax credit is **3.78 lakh**.
- All ten checks are still **ALL OK**."

*[Click Tax_Computation and scroll slowly.]*

"The computation picked up each disallowance by type, automatically. Manually, this would mean redoing the P&L, Balance Sheet, computation and deferred tax, and then checking them all again."

*[Click Version_Log.]*

"This shows how profit and tax moved in each version. In V2 the audit entries reduced profit by 20 lakh, but tax fell by only about 1.66 lakh, because most of those entries were disallowed."

## Scene 6B: Independent check with Python (45 sec)

*[Switch to the Command Prompt. Type `python check_model.py` and press Enter.]*

"As a final control, I wrote a short Python script that reads the trial balance and the adjustments directly from the Excel file, recomputes profit, total income, current tax and deferred tax on its own, and compares them with Excel. All four figures say **MATCH**, and all ten checks are OK. So the model has been verified two ways."

*(Save the Excel file before running the script so it reads the latest figures.)*

## Scene 7: AI writes the client note (1 min)

*[Select the Version_Log table, copy it, go back to the AI tab, paste the second prompt from AI_Live_Demo cell B21, and paste the table after it.]*

"Finally, the client always asks why the profit and tax changed. I ask AI to write a simple note for the managing director."

*[Show the AI's note. Read two lines.]*

"In seconds I have a clear explanation, which I would review before sending."

## Scene 8: Time saved and conclusion (face full screen, 1 min)

*[Show Time_Study briefly, then switch back to camera.]*

"In my time study, one revision took about 160 minutes manually and about 16 minutes with this model and AI. That is a 90% saving, or around 7 hours per client every year, with much better accuracy.

Three lessons from this project:
1. AI is excellent for a fast first draft of tax classification and client communication.
2. Different AI models can give different answers, and they can miss links between provisions, like 115BAA with 80GGB or with additional depreciation. Professional review is essential.
3. When AI and a well-designed Excel model are combined, the final accounts and the tax computation always stay in agreement.

Future scope includes MAT, interest under 234B and 234C, and updating the model for the new Income-tax Act, 2025.

Thank you."

---

**Before recording:**
- Replace the Time_Study figures with your own timings, and put your own numbers into the script.
- After recording, close Excel without saving, so rows 17–20 stay switched off (Include = N) in the submitted file.
