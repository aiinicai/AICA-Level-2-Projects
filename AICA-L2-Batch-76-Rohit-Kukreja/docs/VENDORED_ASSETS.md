# Vendored front-end assets

Build Prompt v2 §1 names HTMX 2.x and Alpine.js 3.x, vendored locally with no
CDN. §13 forbids any network fetch at runtime, so these are served from
`/static/vendor/` and nothing in the running application reaches the internet.

Downloaded 17 August 2026 from unpkg, on the partner's instruction. Versions
are pinned in the filename so an upgrade shows up in a diff rather than
happening silently.

| File | Bytes | SHA-256 | Source |
|---|---|---|---|
| `htmx-2.0.10.min.js` | 51,238 | `71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de` | https://unpkg.com/htmx.org@2.0.10/dist/htmx.min.js |
| `alpine-3.16.1.min.js` | 47,465 | `04656d770039b55ac7a37aeecb92191de2c7775f61f2d0183331cc16c13f3f1e` | https://unpkg.com/alpinejs@3.16.1/dist/cdn.min.js |

## What uses them

- **HTMX** does the autosave in `app/templates/workspace.html`: each
  `form.autosave` carries `hx-post`, `hx-trigger="change, blur"` and
  `hx-select=".preview-pane"`, so saving a field re-renders the preview
  without a page load.
- **Alpine** owns the save indicator in the topbar, driven by HTMX's own
  `htmx:before-request` and `htmx:after-request` events.
- `app/static/workspace.js` holds only what neither library provides: Ctrl+S
  on the focused field, and a warning if the window is closed mid-save. It
  replaced `autosave.js`, the dependency-free stand-in used before these
  libraries were vendored.

**None of it is required.** Every control is a real `<form>` with a real
submit button. With JavaScript switched off the page still works, which is
why the Phase 6 exit test passes without any of this running.

## Verifying

```bash
python scripts/check_vendored_assets.py
```

It recomputes each digest and fails if one has moved. A vendored library that
changes without a version bump is either a bad merge or something worse, and
neither should be invisible. `tests/test_vendored_assets.py` runs the same
check.
