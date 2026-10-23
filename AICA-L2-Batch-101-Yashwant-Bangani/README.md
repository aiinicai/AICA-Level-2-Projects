# CA Intermediate Paper 6 (FM & SM) Companion

Run locally: `pip install -r requirements.txt` then `streamlit run app.py`.

## API key (resolution order)
1. Session override typed into the in-app drawer
2. `st.secrets["GEMINI_API_KEY"]` (Streamlit Cloud > Settings > Secrets)
3. `GEMINI_API_KEY` environment variable or `.env` (cwd, project root, parent)

`.env` and `.streamlit/secrets.toml` are git-ignored.

## Things to verify before publishing
- Model id: `gemini-3.8-flash` is set in `modules/gemini_tutor.py` (`MODEL_ID`). If your account does not list it, the app shows the API error instead of crashing.
- ICAI URLs: the four hub links are as specified; confirm they still resolve. The "sugg-ans-inter-may2026" link is diet-specific and will need updating each diet.
- Chapter-level marks are an indicative teaching split that sums to the module averages; they are not ICAI-published.
- The SVG emblem is stylised artwork. The real ICAI logo is a registered mark; get ICAI permission before using it.
- Optional: put a handwriting TTF at `assets/fonts/handwriting.ttf` for a more handwritten PDF look.
