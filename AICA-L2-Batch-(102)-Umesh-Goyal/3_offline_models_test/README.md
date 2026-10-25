# 3. Offline model test

**Question:** can a model that runs on the office PC or a phone, with no data leaving the device, pull the key
fields out of an SCN?

**Setup.** The same SCN text and the same eight checks (SCN number, date, section, years, tax amount and so on) were given to
each model. Test machine: Windows 11 PC, AMD Ryzen 3 PRO 2200G, 16 GB RAM, no discrete GPU. LM Studio ran only after the
runtime was switched to CPU (AVX2). Test text was fictional.

| Model | Where it ran | Result | Remark |
|-------|--------------|--------|--------|
| Gemma 3 1B | LM Studio, CPU | 6 of 8 correct | Fast, but misses some fields |
| Gemma 4 E2B | LM Studio, CPU | 8 of 8 correct | Slow on this machine |
| 543 MB model | Google AI Edge Gallery, phone | Tax amount wrong by a factor of 10 | Fast, but a wrong amount is the worst kind of error |

**Reading of the result.** A small offline model is fine for a first pass on fields that are easy to check by eye.
It is not safe for amounts. That is why the amounts in this project are always re-added by a script
(`4_python_checks/check_scn.py`) and checked against the original PDF.
