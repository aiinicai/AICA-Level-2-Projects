#2.1.2 bounded patch QA

Linux Python3.12.16.249headless tests pass in working tree and exact extracted
release; JUnit docs/test_results.xml and external
_verification/2.1.2_test_results.xml. Exact ZIP manifest/CRC and import location
verified; compileall passed. No new GUI launch/automation through Shell.

Actual2.1.1 Linux GUI acceptance passed prior compact-layout repairs, wheel,
Paper/Orientation, full-page preview, second asset append and SaveAs/Open/3exports.
See GUI_ACCEPTANCE_2.1.1.md for precise passes, remaining issues, actual financial
file-content inspection and verified existing screenshot paths.

Bounded2.1.2 fixes, fresh desktop retest PENDING:
- Explicit identical selected/unselected tab font/padding/expansion; Notebook
  wheel events blocked so they cannot change selected tab.
- Preview initial client rectangle centred/bounded with decoration allowance;
  minimum no larger than available rectangle; page canvas has scrollbars/wheel.
- Pinned Report Preview/Excel/Word/PDF bar outside long scrolling form.
- Guarded one-callback Cancel clears editing mode/draft/supporting fields and
  restores Add item without mutating saved asset records.
- Saved/opened/new clean-case fingerprints; unsaved prompts only for real model
  differences or unapplied inline changes. Save/SaveAs refresh clean baseline;
  cancelling a file dialog does not mark changed data saved.

New regressions cover preview sizes1024x578/1280x800/1920x1080, invariant tab state
maps, wheel blocking, pinned Report controls, single cancel, clean/dirty prompts,
save-as and unapplied edit protection. Prior full parsing/export/rounding/images/
removal/CA persistence/rates/UDIN fake-DOM/privacy regression suite retained.

No runtime claim for these new GUI changes or Windows3.14/EXE. No live UDIN,
OTP, real profile deletion or print job. Native Office background rendering is
structurally verified only; PDF actual full-background output was rendered.
No file-dialog typing-lag fix claimed. Existing limits unchanged: one owner per
row (no fractional joint allocation), eight currencies, source/OCR uncertainty,
reviewed income policy and separate PDF versus Office pagination.
