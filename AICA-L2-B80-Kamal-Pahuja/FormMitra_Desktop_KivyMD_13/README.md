# FormMitra Desktop — Assistive Form-Reading App

Helps elderly users, or anyone who finds official paperwork confusing,
understand a **blank** form (bank account opening, insurance, demat, KYC,
government forms, etc.) by scanning it and getting plain-language guidance
for every field — in a regional language of their choice, shown as bright
notes directly on the form.

This is a **single Python file** (`formmitra_desktop.py`) so it is easy to
run straight from IDLE, the editor that comes with every Python install.

---

## 1. What you need before you start

- **Python 3.9 or newer**, with **IDLE** and **Tkinter** included. These come
  bundled with the official Windows/macOS installer from
  [python.org](https://www.python.org/downloads/) — just make sure you don't
  uncheck "tcl/tk and IDLE" during installation.
  (On Linux, if `tkinter` is missing, install it once with e.g.
  `sudo apt install python3-tk`.)
- **An internet connection** — the app calls Google's Gemini AI to read the
  form and to translate guidance into your chosen language, and uses
  Google Text-to-Speech for the "Listen" buttons.
- **A free Google AI Studio (Gemini) API key.** Get one in under a minute:
  1. Go to <https://aistudio.google.com/app/apikey>
  2. Sign in with any Google account and click "Create API key".
  3. Copy the key — the app will ask for it the first time you run it.
- A **webcam**, only if you want to use the "Use Camera" scan option
  (uploading a file works without one).

You do **not** need to install any library yourself — see the next section.

---

## 2. Running the app

1. Download `formmitra_desktop.py` to your computer.
2. Double-click it to open it in **IDLE** (or right-click → "Edit with
   IDLE").
3. Press **F5** (or menu **Run → Run Module**).
4. The first time you run it, watch the **IDLE Shell** window: the app
   automatically checks for every third-party library it needs (Pillow,
   OpenCV, PyMuPDF, python-docx, openpyxl, python-pptx, google-genai, gTTS,
   playsound) and installs any that are missing with `pip`. This can take a
   few minutes on the very first run and needs internet access; on later
   runs it starts instantly because everything is already installed.
5. A window titled **"FormMitra"** will open, and you'll be asked to paste
   in your Gemini API key (see step above). It is saved only on your own
   computer, in a small settings file in your home folder, and is sent
   directly to Google's Gemini API — nowhere else.

If step 4 fails to install something automatically (for example, because
your network blocks `pip`), the Shell window will tell you exactly which
package failed and the plain `pip install <package>` command to run
yourself in a terminal — after that, just re-run the app.

---

## 3. Using the app

1. Click **"Upload a Form"** and choose a blank PDF, Word (.docx), Excel
   (.xlsx), PowerPoint (.pptx), or image (PNG/JPG) file — **or** click
   **"Use Camera"** to open a live webcam preview: line the form up and
   press **SPACE** to capture it (press **ESC** to cancel).
2. Pick your **Language** from the dropdown (13 common Indian languages are
   listed, plus "Other" if you'd like to try typing any other language
   name into the box).
3. Wait a few seconds while Gemini reads the form. Every field it finds
   gets a numbered red circle on the form (left panel) and a matching
   **guidance card** in the list on the right, with the field's label, a
   simple explanation of what to write, an example answer, whether it's
   required, and a **"🔊 Listen"** button.
4. **Click any numbered circle** on the form (or the **"📍 Show on form"**
   button on a card) to reveal just that field's bright note — click it
   again to hide it. This keeps busy, many-field forms (bank/KYC forms
   often have 20+ fields) readable instead of covering the whole page in
   overlapping notes at once. If you'd rather see every note simultaneously
   (fine for a short, sparse form), tick **"Show all notes at once"**.
5. Use **"🔊 Read All Aloud"** to have every field read out in order, or
   **A- / A+** to shrink or grow all the text, or **"High contrast"** for a
   black-background, high-visibility mode.
6. Click **"💾 Save Annotated Copy"** to save a PNG or PDF copy of the
   form: the form (with just numbered badges, nothing overlapping) sits in
   the middle, flanked on the left by guidance boxes for the first half of
   the fields and on the right by the second half — so even a long,
   20-field form reads as one wide page instead of a very long scroll —
   handy for printing or for someone to fill in later without needing the
   app open.
7. Changing the **Language** dropdown after a form is loaded re-uses the
   fields already found (fast) and just re-translates the guidance text
   into the new language.

---

## 4. How it works (for the curious / for grading)

- **Field detection & guidance**: the form image (or, for Word/Excel/
  PowerPoint files, a page we render ourselves from the extracted text so
  we know exactly where every line sits) is sent to Google's Gemini model
  with a structured-JSON prompt asking it to list every field, a short
  plain-English explanation, an example answer, whether it's required, and
  its position on the page. This detection call happens once per form and
  is cached — switching languages only makes a second, cheaper text-only
  translation call reusing the same field positions.
- **Word / Excel / PowerPoint** aren't naturally images, so the app extracts
  their text (paragraphs and tables for Word, rows for Excel, text boxes
  and their exact on-slide position for PowerPoint), lays that text out on
  a synthetic page it draws itself, and asks Gemini (in a text-only call)
  which lines are fillable fields — since the app drew the page, it already
  knows each line's exact position, which is more reliable than trying to
  guess positions from a picture.
- **On-screen guidance** is drawn with Tkinter, which needs to be told
  which font *family* to use — on Windows the app explicitly asks for
  "Nirmala UI" (which ships with Windows 10/11 and covers most Indian
  scripts) whenever the selected language needs it, instead of the normal
  UI font "Segoe UI", which does not have Hindi/Tamil/Bengali/etc. glyphs.
  This is why on-screen guidance shows up correctly even though it isn't
  baked into a picture.
- **The saved annotated copy**, on the other hand, is a picture with text
  baked into it by Pillow, which needs an actual font *file* with the
  right script's characters, not just a family name. On Windows the app
  automatically uses "Nirmala UI"'s font file; if that can't be found it
  downloads a matching Noto Sans font for that script automatically (from
  a public, no-login font mirror) and caches it locally so this only
  happens once per script. If every option fails (e.g. no internet on
  first use), it tells you plainly when you save that the image may show
  boxes instead of that script's letters — the on-screen view and side
  list are never affected by this.
- **Field numbering, and the "Required"/"Example" labels, are shown in
  the selected language too** — native digits (e.g. "3" is "૩" in
  Gujarati) and a translated word instead of the English text, rather
  than plain ASCII mixed into an otherwise-translated line. This isn't
  just cosmetic: a script-specific font file (see the point above) can
  easily be missing ordinary ASCII glyphs even while it renders the
  actual translated script correctly, which used to show up as stray
  empty boxes around the field number on non-Latin forms.
- **"Listen"** uses Google Text-to-Speech (gTTS), which needs internet.
- **Google renames Gemini models fairly often.** The app keeps a short
  list of current model names and automatically asks the API itself for a
  working one if every name in that list has since been retired, so it
  should keep working even after Google's next model refresh.

---

## 5. Known limitations

- This reads and explains **blank** forms — it does not fill the form in
  for you or validate what you've entered. A natural "next step" would be
  overlaying a filled-in preview or checking formats like PAN/Aadhaar.
- Field positions for photographed/scanned forms are Gemini's best guess
  and can be slightly off on a blurry or skewed photo; the guidance text
  itself is unaffected.
- Text-to-speech and translation quality depend on Gemini/gTTS's coverage
  of the chosen language.
- Everything needs an internet connection; there is currently no offline
  mode.
- Your Gemini API key is stored in plain text in a settings file in your
  home folder (`~/.formmitra/config.json` on Mac/Linux, or
  `C:\Users\<you>\.formmitra\config.json` on Windows) so you don't have to
  re-enter it every time — don't share this file, and use **⚙ Settings** in
  the app any time you want to change or clear it.

---

## 6. Troubleshooting

| Problem | What to try |
|---|---|
| "No module named tkinter" | Reinstall Python from python.org and make sure "tcl/tk and IDLE" is checked, or on Linux run `sudo apt install python3-tk`. |
| A library fails to auto-install | Open a terminal/Command Prompt and run the `pip install ...` command the Shell window showed, then re-run the app. |
| Camera won't open | Make sure no other app (Zoom, Teams, etc.) is using the webcam, and that you've allowed camera access for Python in your OS's privacy settings. |
| "Gemini request failed" | Check your internet connection and that your API key was pasted correctly (Settings button). Free API keys also have a daily usage limit. |
| Regional-language text looks like boxes in the **saved** file only | See "How it works" above — install a font for that script (e.g. Windows Optional Features → language pack) or note that the on-screen/side-list view is unaffected. |
