# The Living AI Book

An interactive, child-friendly book about artificial intelligence for readers aged 10–12. This capstone includes a Python reader and a static Progressive Web App (PWA).

## Live book

The deployed book is available at [haritkumarca-web.github.io/AiBook](https://haritkumarca-web.github.io/AiBook/). Share this link to let others open the PWA in a browser.

## Project features

- Short, age-appropriate chapters, a source-linked AI timeline, original explanatory cartoons, and safe-use guidance.
- One applications chapter covering ChatGPT, Google Gemini, Claude, Lovable, and n8n, with a short “Use it when” note for each.
- A local prompt-building activity. It previews a prompt in the browser; it does not send it to an AI provider.
- Optional refreshing of public AI announcement feeds, with links to original publisher sources.
- Page-turn buttons, keyboard navigation, contents navigation, responsive layout, and PWA offline caching.

## Tools and technologies

- **Visual Studio Code** — edit and run the project.
- **Python 3** — local reader, local HTTP server, feed parsing, and PWA data generation.
- **Python standard library** — including `http.server`, `urllib`, `xml.etree.ElementTree`, `json`, and `unittest`. No third-party Python dependencies are required.
- **HTML, CSS, JavaScript** — interactive browser/PWA interface; no front-end framework is required.
- **Web App Manifest and Service Worker APIs** — installation metadata and caching for offline reading.
- **GitHub, GitHub Actions, GitHub Pages** — version control and optional scheduled publishing when enabled and permitted.

## Run the Python reader

Open PowerShell in this folder and run:

```powershell
py living_ai_book.py
```

The reader opens at `http://127.0.0.1:8765/`. Leave the terminal open while reading; press **Ctrl+C** to stop it.

## Run the static PWA locally

From this folder, run:

```powershell
py -m http.server 8000 --directory .\pwa
```

Then open `http://localhost:8000`. For installation on phones and public sharing, publish the PWA over HTTPS. A local `localhost` URL only works on the same computer.

## Run tests

```powershell
py -m unittest -v test_living_ai_book.py
```

## Folder contents

- `living_ai_book.py` — Python reader, feed handling, and static-edition exporter.
- `test_living_ai_book.py` — automated tests.
- `ai_updates.json` — locally saved public-feed edition state.
- `pwa/` — HTML, CSS, JavaScript, icons, generated book data, manifest, and service worker.
- `.github/workflows/` — optional GitHub Actions workflow for scheduled refresh and Pages deployment.
- `PROJECT_OVERVIEW.md` — project summary and architecture.
- `FLOWCHART.svg` — process and data-flow diagram.

## Important limitations

Feed entries are publisher descriptions, not independent fact-checks. Announcement-to-chapter matching uses simple keywords. AI answers can be wrong; readers should check important claims with a trusted adult and reliable sources. Mobile operating systems may pause background activity, so the PWA cannot guarantee updates while closed.
