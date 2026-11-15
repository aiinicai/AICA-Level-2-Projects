# Required final bounded retest —2.1.2

Prior2.1.1 Linux passes documented; these new changes remain unverified in GUI.
Use only synthetic fixtures. No real profiles, portal/OTP or print submission.

1. Fresh2.1.2 process. Open examples/SYNTHETIC_review_case_2.1.2.json. Use header
   Window1024 x578 then1280 x800. Click Report/Firm/Assets repeatedly: selected
   tab must not change strip geometry; wheel over strip must never switch tabs.
   Wheel over form fields must scroll only that form.
2. Report: Preview final PDF / Export Excel / Export Word / Export PDF bar must
   remain visible while scrolling to bottom and back. JSON Save stays separate.
3. Open preview at1280x800 and1024x578: initial window entirely on screen, toolbar
   accessible; actual page scrolls vertically/horizontally/wheel at100/200%.
4. Assets: Edit selected, change value/valuer, click Cancel edit ONCE. Expect
   Add item mode, cleared draft/supporting fields and original saved asset intact.
5. SaveAs JSON then immediately Open it: NO unsaved-change prompt. Change an
   applicant or committed asset then Open another case: prompt must appear.
   Unapplied inline amount changes must also prompt; Cancel edit clears them.
6. Brief regression: second ambiguous1,800,000 asset ->5assets3,126,200; annual
   620,000 separate; SaveAs/Open and actual3format dialogs; full watermark/footer.

Use examples/SAMPLE_whole_page_letterpad.png and
examples/SYNTHETIC_full_page_background_2.1.2.pdf as deterministic artwork proof.
Record per-item PASS/FAIL; new build is not desktop-accepted until retested.
