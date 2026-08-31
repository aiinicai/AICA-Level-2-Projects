# FormMitra Desktop — KivyMD edition (`formmitra_desktop_kivy.py`)

This is a **UI/UX-focused rewrite** of the original Tkinter desktop app
(`formmitra_desktop.py`). Same purpose, same features, same underlying
logic (Gemini calls, form loaders, font handling, saved-copy rendering,
text-to-speech) — the whole application layer has been rebuilt on
**KivyMD** (Material Design widgets on top of Kivy) instead of Tkinter,
for a more modern look and feel. It is a separate file — nothing about
the original Tkinter version has changed, so use whichever you prefer.

## What's different from the Tkinter version

- **Modern Material Design UI**: proper elevated cards for guidance,
  themed raised/flat buttons, a top app bar, a light/dark theme toggle,
  and smoother visual feedback than Tkinter's plain widgets.
- **Embedded live camera preview**: scanning a form now happens inside
  the app window itself (tap "Camera" → live preview → "Capture" → review
  the photo, retaking if needed → "Use This Photo"), instead of popping
  open a separate OpenCV window.
- **One unified font system**: the Tkinter version had to juggle font
  *family names* (for on-screen Tk text) and font *files* (for the saved
  image) separately. Kivy uses font files everywhere, so this version
  registers one font file per language once and reuses it consistently
  for the live view, the guidance cards, and the saved copy.
- Everything else — click-to-reveal notes (tap a numbered badge to see
  just that field's note, tap again to hide it), the "Show all notes at
  once" switch, language switching, font size, high contrast, "Save
  Annotated Copy", and "Read All Aloud" — works exactly the same as the
  Tkinter version, described in detail in the main `README.md`.

### UI/UX pass (2026-08-25)

Real-world use turned up four rough edges, all fixed in this version:

- **The numbered badges on the form now actually show their number.**
  The digit label inside each badge wasn't tracking the badge's own
  position/size in every layout context, so it could render off in a
  corner instead of centered on the circle — now explicitly synced, the
  same reliable way the badge's colored circle already was.
- **The LISTEN button's speaker icon now renders.** It turns out KivyMD
  1.2.0's plain "flat" button silently drops an `icon=` argument — it has
  no icon slot at all — so the icon was never actually being drawn, only
  requested. Swapped to KivyMD's icon-capable button classes (a filled
  button for LISTEN, an outlined one for "Show on form"), so both now
  show a real icon next to their text.
- **The cramped toolbar row that overlapped itself is gone.** High
  contrast, Show all notes, font size, Save Annotated Copy, and Read All
  Aloud all used to be crammed into one fixed-height row that overlapped
  on anything but a very wide window. They're now grouped into a single
  "⋮" options menu next to the language button — tap it to reach any of
  them, with the on/off state shown right in the menu text. Save
  Annotated Copy is also still available as its own button at the bottom
  of the form view.
- **The language picker is now a proper Material dropdown menu**
  instead of a plain, visually mismatched combo box.
- A refreshed teal color scheme for the app's toolbar/buttons/top bar
  (the bright red/orange badges and yellow notes on the form itself are
  left as-is — those bold "alert" colors are deliberately chosen for
  visibility against a form, not a branding choice).

### Follow-up fixes (2026-08-25, round 2)

Real use on the user's own machine turned up three more issues, all fixed:

- **"Could not save file: unknown file extension:" when saving the
  annotated copy.** The Save dialog didn't tell the OS what extension to
  add if you typed a plain filename (like `myform`) and clicked Save
  without touching the file-type dropdown — so it came back with no
  extension at all, and Pillow's save() didn't know what format to write.
  Fixed two ways: the dialog now has a proper default extension (`.png`),
  the way "Save As" dialogs normally behave, and — as a second safety net
  — if a path with no `.png`/`.pdf` extension ever comes back anyway,
  `.png` is appended automatically instead of erroring.
- **"Could not start the camera: 'CameraOpenCV' object has no attribute
  'fps'."** This was a real bug in Kivy's own built-in camera widget: if
  the very first frame read right after opening the webcam fails — which
  is common while some Windows webcams and drivers are still "warming
  up," or if another app briefly held the camera — Kivy's OpenCV camera
  backend crashes with this exact error, because it only ever records the
  camera's frame rate *after* that first read succeeds. This version no
  longer uses Kivy's `Camera` widget at all: it talks to the webcam
  directly (opening it the more Windows-reliable way, and retrying for
  about 2.5 seconds if the first few frames aren't ready yet) and only
  shows the live preview once a real frame has come through — with a
  plain "camera didn't respond, check nothing else is using it" message
  if it genuinely can't get one, instead of crashing.
- **Menu options changed from a "⋮" dropdown into a visible ribbon.**
  Save/Download, Read All Aloud, A-/A+, High Contrast, Show All Notes,
  and the theme toggle are now their own always-visible buttons in a row
  under the main toolbar, per feedback that they should be visible
  up-front rather than tucked behind a menu. To guarantee this row can
  never overlap itself again (the original bug that led to the "⋮" menu
  in the first place), it scrolls sideways instead of wrapping if the
  window is ever too narrow to show every button at once — every option
  stays reachable, just a short scroll away, rather than colliding.

### Follow-up fixes (2026-08-25, round 3): camera Capture button + a guide box for the shot

After round 2's camera fix, the live preview itself worked, but two more
issues turned up:

- **The Cancel/Capture buttons were effectively unreachable.** The
  camera dialog was meant to be a full-window overlay, but it was being
  added as a regular row *inside* the app's main vertical layout — so it
  ended up sharing height with the form/cards area below it instead of
  covering the window, squeezed down into a sliver where the buttons
  could be missed or unusable depending on the window size. Fixed by
  restructuring the app so the camera dialog is added to a separate
  outer layer that sits on top of everything else and always fills the
  entire window, the way a proper full-screen dialog should — Cancel and
  Capture are now always at the bottom of the screen, clearly visible.
- **The very wide field of view on laptop webcams captured way more
  desk/background than form.** A bright guide rectangle (sized for a
  typical A4/letter document) is now drawn over the live preview, with
  everything outside it dimmed — line the document up inside the box,
  and the caption above it says exactly that. Capturing now crops the
  photo to that guide box instead of keeping the full wide-angle frame,
  which both frames the shot on the document and compensates for the
  camera's wide FOV. (While the recognition step is quite tolerant of
  some background, tightening the guide box gives more consistent
  results than depending on it.)

### Follow-up fixes (2026-08-25, round 4): Cancel/Capture moved to the top right

Round 3 made the camera dialog a genuine full-window overlay, but the
user reported the Cancel/Capture buttons were still not visible - most
likely because a row anchored to the very bottom of the window can end
up behind the Windows taskbar or off the visible screen depending on
window size and position, which a screenshot taken in this Linux sandbox
can't reproduce. Rather than keep guessing at the exact cause, the
buttons were moved somewhere far less likely to ever be obscured: a
translucent bar fixed to the **top** of the screen, with Cancel and
Capture on the right-hand side of it (a caption reminding you to line up
the document sits on the left of the same bar). The live camera preview
now fills the entire screen behind that bar instead of stopping short to
leave room for a bottom row, and the guide box's maximum size was
trimmed slightly so it stays clear of the top bar.

### Follow-up fixes (2026-08-25, round 5): a smaller camera window, renamed button, and Retake

Three more requests after trying the camera out:

- **The camera no longer takes over the whole screen.** Instead of a
  full-window preview, opening the camera now shows a smaller window
  (about 60% of the screen's width, 72% of its height) centered over the
  rest of the app, which is dimmed behind it — the same way a dialog box
  normally behaves, rather than a full-screen takeover. Cancel/Capture
  and the guide box all moved inside this smaller window along with the
  live preview.
- **The toolbar button is now labeled "Camera"** instead of "Scan".
- **A Retake option was added.** Tapping Capture no longer immediately
  hands the photo off to the app - it now shows the captured (already
  cropped-to-guide-box) photo full-size with two buttons: **Retake** (go
  back to the live preview and try again - the camera keeps running in
  the background so there's no re-opening delay) and **Use This Photo**
  (continue with this photo, exactly like the old behavior). This means
  a blurry, tilted, or badly-lit shot can just be retaken on the spot
  instead of restarting the whole scan from the toolbar.

### Follow-up fixes (2026-08-25, round 6): saved-copy layout — instructions flank the form, left and right

Real-world testing with a 20-field form (a Bangladeshi union-parishad-style
certificate) showed the saved annotated copy's guidance list, stacked below
the full-width form, made the file painfully long to scroll through. A
first attempt shortened it by splitting the list into two columns — but
still stacked *below* the form, which wasn't actually what was being
asked for. Based on a reference image showing the intended layout, the
saved copy is now built as one wide image with three regions side by
side: guidance boxes for the first half of the fields on the **left**,
the form itself (numbered badges only, no text on top of it) **centered**
in the middle, and guidance boxes for the second half on the **right** —
matching a typical printed reference-sheet layout. The form is shown at
its full size whenever the two guidance columns are at least as tall as
it is (the common case on a form with many fields), and is scaled down
gracefully — never below roughly half its original size — when there are
only a few short fields, so it doesn't dwarf a couple of small instruction
boxes. A form with no detected fields at all is saved unchanged, at full
size, with no columns.

### Follow-up fix (2026-08-29, round 7): field numbering showing as boxes ("Sr no error") in non-Latin languages

Real-world testing in Gujarati showed every guidance card's serial number,
plus the "Required" and "Example:" labels next to it, rendering as empty
boxes (□□) instead of readable text — even though the actual translated
Gujarati guidance right next to them displayed correctly. Root cause: this
app renders on-screen text and the saved copy's baked-in text using one
font *file* directly, with no OS-level "font linking" the way Windows'
own UI or a browser has — so any plain ASCII characters this app's own
code mixes into a string (the "1.", the "•" bullet, the English words
"Required" and "Example:") can end up missing from whatever script-specific
font file was resolved for that language, even when the actual translated
content displays fine. The fix stops mixing ASCII into script-language
text at all: field numbers are now rendered in that language's own native
digits (e.g. "3" becomes "૩" in Gujarati, "३" in Hindi, "۵" in Urdu), and
"Required"/"Example" are shown using a fixed translation into each of the
13 supported languages, instead of the literal English words. This applies
everywhere a field number appears: the on-screen guidance cards, the note
that pops up when tapping a badge on the form, and the saved copy's
legend boxes and round form badges. Also fixed as part of the same root
cause: a stray trailing "." at the end of Gemini's translated guidance
sentences (visible as one extra tofu box at the end of a sentence) is now
stripped for non-English languages, since that punctuation mark faced the
identical missing-glyph risk.

Verified by reproducing the reported bug directly: rebuilt the exact
Gujarati guidance text from the reported screenshot ("Name" / "Husband's
or wife's name", both required, each with an example) and rendered it
through the fixed code — confirmed via both a string-level check (no
ASCII characters at all in the built header text) and a rendered PNG that
the serial number, "Required", and "Example" now display as proper
Gujarati text with zero tofu boxes anywhere, including the previously
broken trailing-period spot. Also re-ran the full existing legend-layout
regression suite (round 6, above) to confirm the numbering fix didn't
disturb the two-column/centered-form composition, and re-confirmed the
Kivy and Tkinter versions produce the same (ASCII-free, correctly
localized) header text for the same input.

### Follow-up fix (2026-08-29, round 8): the round badge number ON the form was still plain ASCII

A second screenshot showed the round numbered badges drawn directly on the
form image itself (not the guidance cards) still reading "1", "2", "3" in
plain ASCII, with the request: "The guidance page should also have sr
numbers in user selected language." Round 7's fix covered the saved copy's
round badges (they already share the same script-specific font used for
the legend text) but deliberately left the **live, on-screen** badge as
plain ASCII, since it draws its digit with Kivy's own default font
(always has ASCII digits, never broke) and was read as a simple
page-reference index rather than "the instructions." That scoping call
turned out to be the wrong read of what was wanted — the user wants the
number on the form to visibly match the number on its instruction box,
in their own language, not just "not broken."

Fixed by giving `FieldBadge` the same treatment as everywhere else:
it now accepts the current `language` and a script-capable `font_name`
(the same one already resolved for the note bubble beside it), renders
its digit via `local_number()` instead of a raw index, and uses that font
instead of Kivy's default so the native digit glyph actually has
somewhere to come from. The Tkinter live view's on-canvas badge digit was
switched to `local_number()` too, for the same consistency, using its
existing family-based font (which already covers the script).

Verified with a real running `FormMitraApp` under Xvfb, given 3 fake
Gujarati fields and `language = "Gujarati"`: after `redraw_overlay()`,
each `FieldBadge`'s label text is asserted to equal
`local_number(1..3, "Gujarati")` (i.e. "૧", "૨", "૩") and to use the
Gujarati-registered font rather than Kivy's default — both checks would
have failed against the pre-fix code. A screenshot of the running app
also visually confirms the guidance cards read "૧ નામ જરૂરી", "૨
પિતાનું નામ", "૩ સરનામું જરૂરી" with no stray boxes, matching the badge
numbers next to them.

## What you need before you start

Same as the Tkinter version: Python 3.9+, an internet connection, and a
free Gemini API key from <https://aistudio.google.com/app/apikey>. You do
**not** need Tkinter/IDLE's Tk bundle for this version specifically, but
having the standard python.org installer (which includes it) is still
fine and won't conflict with anything — the file dialogs (Open/Save) for
this version borrow Tkinter's native file picker under the hood since
Kivy doesn't have a good native one, so please keep the standard
"tcl/tk and IDLE" option checked when installing Python.

A **webcam** is only needed for the "Camera" button — uploading a file
works without one.

## Running the app

1. Download `formmitra_desktop_kivy.py` to your computer.
2. Double-click it to open it in **IDLE**, then press **F5** — or run it
   from a terminal: `python formmitra_desktop_kivy.py`
3. **The very first run installs Kivy and KivyMD in addition to the same
   libraries the Tkinter version needs** (Pillow, OpenCV, PyMuPDF,
   python-docx, openpyxl, python-pptx, google-genai, gTTS, playsound).
   Kivy/KivyMD are bigger downloads than the others, so the first run can
   take a few minutes longer than the Tkinter version's first run — watch
   the Shell/terminal window for progress. Every later run starts quickly
   because everything is already installed.
4. A window titled **"FormMitra"** opens; paste in your Gemini API key
   when asked (saved only on your computer, same as the Tkinter version).

## Using the app

Identical workflow to the Tkinter version — see section 3 of the main
`README.md` for the full walkthrough (upload/scan → pick language → tap
badges to reveal notes → Listen / Read All / Save Annotated Copy). The
only interaction difference: the camera now opens as a smaller preview
window *inside* the app (tap **Capture** to take the photo, then
**Retake** if it's not clear or **Use This Photo** to continue, or
**Cancel** at any point to back out) rather than a separate popup.

## Testing notes

Before delivery this version was verified with an automated check that
builds the real app, loads sample field data, and confirms: badges are
drawn once per field with **zero notes visible until tapped** (the
overlapping-notes bug reported earlier is fixed here too), tapping a
badge shows exactly one note and tapping it again hides it, switching
between badges never leaves more than one note open, the "Show all
notes" switch reveals/hides every note correctly, the saved-copy image
still renders its legend panel correctly, and font registration doesn't
crash for Hindi/Odia/Tamil/Bengali/English. The embedded camera was also
verified to fail gracefully (with a friendly on-screen message) on a
machine with no webcam, rather than crashing the app.

**Today's (2026-08-25) UI/UX pass added its own checks**, on top of all
of the above: the badge's number label now has its position, size, and
text-wrap box asserted to move in lockstep with the badge's colored
circle in every layout pass (not just its position, which was the more
subtle part of the original bug); the LISTEN and "Show on form" buttons
are asserted to actually be icon-capable button classes with a non-empty
`icon` value, not just to have an `icon=` argument accepted and
silently ignored; and the language dropdown is asserted to list every
supported language and to actually update the app's active language on
selection. Beyond these structural (`isinstance`/property) checks, the
fixes were also confirmed **visually**: the running app was captured
with a real pixel-rendered screenshot (`Widget.export_to_png`, not a
black/blank `Window.screenshot`), which was inspected directly and shows
a legible white digit centered in its badge circle, both buttons' icon
glyphs rendered next to their text, and the new teal toolbar with no
overlapping controls.

**The follow-up round (2026-08-25, round 2) added checks of its own**:
the options ribbon is asserted to contain all 7 expected buttons (rather
than a menu that has to be opened), and the High Contrast / Show All
Notes buttons are asserted to flip both their text *and* their icon
between "Off"/blank-checkbox and "On"/checkmark when tapped, live, in the
running app. Saving with a filename that has no extension (simulating a
user who types a bare name and clicks Save without touching the file-type
dropdown) is asserted to default to `.png` and save successfully instead
of raising the old "unknown file extension" error. And, since this
sandbox has no webcam to test the fix against directly, the new
camera-opening code path was verified two ways: first, that it fails with
a plain "camera didn't respond" message rather than the old
`'CameraOpenCV' object has no attribute 'fps'` crash when no camera is
present (confirmed here, in this sandbox); second, the retry-loop logic
itself was exercised directly against a fake camera object engineered to
fail its first several reads and only succeed afterward, confirming the
warm-up retry recovers correctly rather than giving up too early — this
is the closest a webcam-less sandbox can get to reproducing the original
bug's trigger condition, but real webcam hardware on the user's machine
is still the real test.

**Round 3 (2026-08-25) added checks for the camera dialog's layout and
the guide box.** With a fake camera feeding in frames, the running app
is asserted to add the camera dialog to the outer overlay layer (not the
inner content layout) and to size it to exactly match the full window,
directly confirming the dialog is a true full-screen overlay rather than
a squeezed-in row — the structural cause of the missing-Capture-button
report. The guide box's remembered position is asserted to always stay
within the visible preview area (never extending past its edges) for a
resized camera widget, and capturing is asserted to produce a photo
smaller than the raw camera frame, confirming the crop-to-guide-box step
actually ran rather than silently keeping the full wide-angle shot. All
of this was also confirmed visually with an `export_to_png()` screenshot
of the live dialog (with a fake patterned camera feed standing in for a
real one, since this sandbox has no webcam) showing the dimmed area
outside the guide box, the bright rectangle and caption, and both
buttons clearly visible at the bottom of the screen.

**Round 4 (2026-08-25) checks the buttons' new position directly.** The
Cancel and Capture buttons are asserted to sit in the top 15% of the
window and on the right half of it, rather than just asserting they
exist somewhere - a check that would have caught round 3's placement not
matching what was actually visible on the user's screen. Re-confirmed
that the live preview now measures as exactly the full window size (no
strip reserved at the bottom), that the guide box still computes sane,
in-bounds coordinates against the now-taller preview, and that capture
and crop-to-guide-box still work correctly with the new layout. Visually
confirmed with a fresh `export_to_png()` screenshot showing Cancel and
Capture together in a translucent bar at the top right, clear of the
guide box below.

**Round 5 (2026-08-25) checks the smaller window, the renamed button, and
the Retake flow.** The camera panel's own size is asserted to be
meaningfully smaller than the full window (confirming it's a dialog, not
a takeover) while still being a usable size, not a sliver. The toolbar
button is asserted to read "Camera" with no leftover "Scan" text
anywhere. The capture flow is asserted step by step: tapping Capture
enters review mode and does *not* immediately hand the photo to the
app, the live camera feed is asserted to pause during review (so it's
not wastefully decoding frames nobody sees), tapping Retake is asserted
to return to live mode with the camera resumed and no pending image left
over, and only tapping "Use This Photo" is asserted to actually hand the
(still correctly cropped) image off. Confirmed visually with two fresh
`export_to_png()` screenshots — one of the live preview inside the
smaller centered window with the rest of the app visibly dimmed behind
it, and one of the review step showing the captured photo with Cancel,
Retake, and Use This Photo all clearly rendered (with their correct
colors and the checkmark icon on Use This Photo, once given enough
render frames to finish drawing — an early screenshot taken immediately
after the buttons were created showed them with their backgrounds not
yet drawn, which turned out to be purely a screenshot-timing quirk of
capturing a frame right as new widgets are created, not a real rendering
bug in the running app).

**Round 6 (2026-08-25) checks the redesigned saved-copy layout.** A
20-field synthetic form is rendered and the output is asserted to be
wider than the original form (confirming the two guidance columns sit
beside it rather than below it), with the marked form itself unchanged
in content and only its position/size in the canvas affected. A 2-field
case is checked to confirm the layout still works sensibly (one guidance
box on each side) without the form shrinking to an unreadable size, and a
0-field case is checked to confirm the form is saved at its original
full size with no columns and no crash. This round's `render_annotated_image`
function is confirmed byte-for-byte identical between this file and the
Tkinter version's `formmitra_desktop.py`, and both were run against the
same synthetic 20-field form to confirm they produce pixel-identical
output — this file was tested under Kivy/Python 3.11 as usual, and the
Tkinter file was separately tested under Python 3.12 (the interpreter in
this project's sandbox that has the `tkinter` module available).

As with the Tkinter version, this hasn't been used against a large
variety of real-world forms yet — please report anything that looks off
so it can be fixed quickly.

## Troubleshooting

| Problem | What to try |
|---|---|
| `ModuleNotFoundError: No module named 'kivy'` (even after the app said it would auto-install it) | This means the automatic `pip install` of Kivy failed in the background. Run the script from a **Command Prompt/terminal** instead of double-clicking or pressing F5 in IDLE — the current version of the app now prints pip's real error message and exits cleanly with specific guidance instead of crashing (see the two rows below for the most common causes it will point you to). |
| **You're on Python 3.14** and installing Kivy fails with something like `Could not find a version that satisfies the requirement kivy_deps.sdl2_dev` | Confirmed as of this writing: Kivy's Windows dependency `kivy_deps.sdl2_dev` has not published a Python 3.14 build yet, so **Kivy cannot currently be installed on Python 3.14 on Windows at all** — this is a gap in Kivy's own release, not something this script (or any pip flags) can work around. Fix: install **Python 3.12** alongside your existing Python (it will not remove or affect 3.14) — if you installed Python through the newer python.org/Microsoft Store installer, open a terminal and run `py install 3.12`; otherwise grab the Python 3.12 installer from [python.org/downloads](https://www.python.org/downloads/) (keep "tcl/tk and IDLE" checked). Then run this script specifically with that version: `py -3.12 formmitra_desktop_kivy.py` (or right-click the file → Open with → the Python 3.12 you just installed). If you'd rather not install another Python version, `formmitra_desktop.py` (the Tkinter edition) has no such dependency and runs fine on Python 3.14 as-is. |
| Kivy install fails on an **older or unusual** Python version with something like "no matching distribution" or it tries to build from source | Kivy only publishes pre-built wheels for a specific range of Python versions at a time. Check your Python version with `python --version`; installing **Python 3.11 or 3.12** from [python.org](https://www.python.org/downloads/) alongside your current install and running this script with that version's `python` usually resolves it. |
| A library other than Kivy/KivyMD fails to auto-install | The app will still start; open a terminal and run the `pip install ...` command it printed, then re-run. |
| Camera won't open / preview stays black | Make sure no other app (Zoom, Teams, etc.) is using the webcam, and that Python has camera permission in Windows' privacy settings. |
| "Gemini request failed" | Check your internet connection and that your API key was pasted correctly (⚙ button, top-right). Free API keys also have a daily usage limit. |

## Which version should I use?

Both are fully self-contained single files with the same feature set.
Pick **`formmitra_desktop_kivy.py`** if you want the more modern-looking
Material Design interface and embedded camera preview. Pick
**`formmitra_desktop.py`** if you'd rather keep the lighter, faster-to-
first-run Tkinter version (no extra Kivy/KivyMD download). Both read your
same saved API key and settings, so you can freely switch between them.
