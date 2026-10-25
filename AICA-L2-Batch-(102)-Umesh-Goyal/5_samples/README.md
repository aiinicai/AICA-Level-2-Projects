# Sample data (all fictional)

| File | What it is |
|------|------------|
| `sample_scn_text.pdf` | Fictional Section 74 SCN, 2 pages, with a text layer. Table of demand and a digital-signature stamp. |
| `sample_scn_scanned.pdf` | The same notice turned into pictures with a slight tilt and noise, to test the OCR route. |
| `scn_output_example.json` | Hand-made stand-in for the AI Studio JSON of the text PDF (the fictional notice only), so `check_scn.py` can be run without AI Studio. |
| `demo_intake_answers.txt` | Fictional answers to the Skill's intake questions, so the demo runs without inventing facts on camera. |
| `expected_output/` | What the scripts print or save on these files (`check_scn.py` was run on 24-10-2026, so the "days left" line changes with the day). |

The notice carries the line "ILLUSTRATIVE SAMPLE - FICTIONAL - NOT A REAL NOTICE" on every page.
The GSTIN `00AAAAA0000A1Z0` is not a valid registration (state code 00).
Never put a real notice or its `_ocr.txt` / `_header.json` output into this repository.
