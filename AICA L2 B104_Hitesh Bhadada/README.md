# ECL Stage Migration Matrix & Commentary Narrator

**AICA Level 2 Capstone Project — Hitesh Bhadada, Financial Controller**

**Prebuilt Windows executable:** [Download ecl_gui.exe](https://drive.google.com/file/d/1tC18DdHfVCi3tpNmVScdrHC3KtjwgRpt/view?usp=drive_link)

A desktop tool that takes loan-level data across period-ends and produces a Board/Audit-Committee-ready ECL stage migration analysis — with loan-level drill-down, an Ind AS 107 para 35H loss-allowance reconciliation, and an RBI IRACP vs Ind AS 109 comparison.

Two files, used together:

| File | Role |
|---|---|
| `ecl_migration_matrix.py` | The calculation engine. All arithmetic, stage logic, and disclosure formats live here. Can also be run alone from the command line. |
| `ecl_gui.py` | A Tkinter desktop window on top of the engine. Adds no calculation logic of its own — it only lets you point at a folder, pick two periods, and click Run instead of using command-line flags. |

**Both files must be kept in the same folder.** `ecl_gui.py` imports `ecl_migration_matrix.py` directly and will not run without it.
