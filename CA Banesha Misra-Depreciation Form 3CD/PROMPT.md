Create a MINIMAL working Windows application named **Depreciation-3CB/3CD**.

IMPORTANT:
Do not explain anything.
Do not paste code in the chat.
Create the file directly.
Use the minimum possible code.
Do not create tests, database, elaborate architecture, documentation, multiple Python modules, or unnecessary features.

### REQUIREMENT

Create ONE file only:

**Depreciation-3CB-3CD.py**

Use:
- Python
- PyQt6
- openpyxl

The application must have a simple professional colourful GUI.

### INPUT

Provide a table where the user can enter:

1. Asset/Block
2. Depreciation Rate
3. Opening WDV
4. Addition Amount
5. Addition Date
6. Date Put To Use
7. Deduction Amount
8. Deduction Date
9. Sale Consideration
10. Business Use %
11. Remarks

Buttons:

**Add Row**
**Delete Row**
**Calculate**
**Generate Form 3CD Excel**

### CALCULATION

Calculate depreciation block-wise using the applicable Income-tax depreciation workflow.

Support:
- Opening WDV
- Additions
- Deductions
- Date put to use
- Applicable depreciation rate
- Reduced/half-rate treatment where applicable
- Closing WDV

Keep depreciation rates in a simple dictionary at the top of the Python file so they can be changed later.

Do not invent tax rules.

### EXCEL — MOST IMPORTANT

When **Generate Form 3CD Excel** is clicked, create:

**Form_3CD_Depreciation_Report.xlsx**

using openpyxl.

Create these sheets:

**Form 3CD Clause 18**
**Copy-Paste Data**
**Block Summary**
**Depreciation Working**
**Reconciliation**

The **Copy-Paste Data** sheet is the PRIMARY output.

It must contain clean Form 3CD Clause 18 depreciation particulars suitable for reviewing and copying into the current Form 3CD utility.

Include:

- Description of asset/block
- Rate
- Opening WDV/actual cost
- Additions
- Date of addition
- Date put to use
- Deductions
- Date of deduction
- Depreciation allowable
- Closing WDV
- Adjustments
- Remarks

Format the Excel professionally with headers, filters, freeze panes, widths, dates and numbers.

Add totals and reconciliation.

### DEPLOYMENT

Also create only:

**requirements.txt**
**run.bat**
**build_exe.bat**

Use PyInstaller in build_exe.bat.

### SAMPLE

Include a few fictional sample rows inside the application so it can immediately be tested.

### FINAL

Create:

**Depreciation-3CB-3CD.zip**

containing only:

Depreciation-3CB-3CD.py
requirements.txt
run.bat
build_exe.bat

Do NOT provide source code in chat.

Do NOT provide explanations.

Do NOT create additional files unless absolutely necessary.

Do NOT spend tokens on testing or documentation.

If you must choose between features, prioritize:

**Excel Form 3CD Clause 18 output > depreciation calculation > GUI appearance > everything else.**

CREATE THE ZIP NOW.