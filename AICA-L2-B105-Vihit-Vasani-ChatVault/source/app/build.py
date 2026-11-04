"""Assemble ChatVault into one self-contained HTML file (dist/chatvault.html)."""
import base64, os, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
SAMPLES = os.path.join(HERE, "..", "samples")
os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)

# Wallpaper doodle: small line icons from the archive's world (bubble, paperclip, document, rupee, lock, tick)
doodle = """<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180' viewBox='0 0 180 180' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'>
<path d='M18 22h30a6 6 0 0 1 6 6v14a6 6 0 0 1-6 6H30l-8 6v-6h-4a6 6 0 0 1-6-6V28a6 6 0 0 1 6-6z'/>
<path d='m122 30-14 14a7 7 0 0 1-10-10l16-16a4.5 4.5 0 0 1 6.5 6.5L105 40'/>
<path d='M70 70h18l8 8v24H70z M88 70v8h8 M75 86h16 M75 93h12'/>
<path d='M140 78h14 M140 84h14 M146 78c6 0 6 6 0 6h-6l12 12'/>
<rect x='26' y='118' width='20' height='16' rx='3'/><path d='M30 118v-5a6 6 0 0 1 12 0v5'/>
<path d='m110 128 6 6 12-13 M104 128l6 6'/>
<circle cx='160' cy='150' r='3'/><circle cx='64' cy='160' r='2'/><circle cx='150' cy='14' r='2'/>
<path d='M70 140l4-8 4 8-4 8z'/>
</svg>"""
doodle_uri = "data:image/svg+xml," + urllib.parse.quote(" ".join(doodle.split()), safe="/:=' ")

css = open(os.path.join(SRC, "style.css"), encoding="utf-8").read()
css = css.replace(":root{", ":root{\n  --doodle-svg:url(\"" + doodle_uri + "\");", 1)
js = open(os.path.join(SRC, "app.js"), encoding="utf-8").read()

# Make the shipped page pure ASCII so it renders correctly whatever encoding the browser assumes.
def js_ascii(s):
    out = []
    for ch in s:
        o = ord(ch)
        if o < 128: out.append(ch)
        elif o <= 0xFFFF: out.append("\\u%04x" % o)
        else:
            o -= 0x10000; out.append("\\u%04x\\u%04x" % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
    return "".join(out)
css = "".join(ch if ord(ch) < 128 else "\\%x " % ord(ch) for ch in css)
js = js_ascii(js)

samples = []
import json
for name, extra in [("WhatsApp Chat with Mehta Traders - GST Audit.zip", {"me": "CA Vihit", "tags": ["GST audit", "FY 2026-27"]}),
                    ("WhatsApp Chat with Mehta Traders - GST Audit (4 Nov).zip", {"me": "CA Vihit", "mergeWithPrevious": True, "tags": ["GST audit", "FY 2026-27"],
                      "matter": {"client": "Mehta Traders", "gstin": "24AAAAA0000A1Z5", "pan": "AAAAA0000A", "matter": "GST audit and annual return", "fy": "2026-27", "ref": "VT/GST/112"},
                      "stars": [6, 11, 12, 27, 28], "notes": {"12": "Neha's acknowledgement, later deleted. Shows the follow-up was agreed on 1 Nov.", "28": "Fee confirmation for engagement letter."}}),
                    ("WhatsApp Chat - Anjali Shah (NRI).zip", {"me": "Vihit", "tags": ["NRI", "Capital gains"], "matter": {"client": "Anjali Shah", "matter": "Sale of Andheri flat – capital gains and TDS refund", "fy": "2026-27"}})]:
    b = open(os.path.join(SAMPLES, name), "rb").read()
    samples.append(json.dumps({"name": name, **extra, "b64": base64.b64encode(b).decode()}, ensure_ascii=True))

fonts = {k: base64.b64encode(open(os.path.join(HERE, "vendor", "fonts", f), "rb").read()).decode() for k, f in [("guj", "NotoSansGujarati-Regular.ttf"), ("deva", "NotoSansDevanagari-Regular.ttf")]}
icon_svg = open(os.path.join(HERE, "vendor", "icon", "chatvault.svg"), encoding="utf-8").read()
icon_uri = "data:image/svg+xml," + urllib.parse.quote(icon_svg, safe="/:=' ")
icon_png = "data:image/png;base64," + base64.b64encode(open(os.path.join(HERE, "vendor", "icon", "chatvault-256.png"), "rb").read()).decode()
page = f"""<title>ChatVault</title>
<link rel="icon" type="image/svg+xml" href="{icon_uri}">
<link rel="apple-touch-icon" href="{icon_png}">
<meta name="theme-color" content="#0d7a65">
<meta name="application-name" content="ChatVault">
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="Archive, read, search and export WhatsApp chat exports with role-based access and SHA-256 integrity fingerprints.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style id="cv-css">
{css}
</style>
<div id="app"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script>window.CV_SAMPLES=[{",".join(samples)}];</script>
<script>window.CV_FONTS={{guj:"{fonts["guj"]}",deva:"{fonts["deva"]}"}};</script>
<script>
{js}
</script>
"""
os.makedirs(os.path.join(HERE, "artifact"), exist_ok=True)
out = os.path.join(HERE, "artifact", "chatvault.html")  # page body for the hosted version (no <head>); not for opening directly
open(out, "w", encoding="utf-8").write(page)

# Standalone version (opens directly from disk / any web server)
standalone = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
              + f'<title>ChatVault</title><link rel="icon" type="image/svg+xml" href="{icon_uri}"><meta name="theme-color" content="#0d7a65">'
              '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
              'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'
              + page.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>',
                             "<script>" + open(os.path.join(HERE, "vendor", "jszip.min.js"), encoding="utf-8").read().replace("</script", "<\\/script") + "</script>")
              + "</body></html>")
open(os.path.join(HERE, "dist", "ChatVault.html"), "w", encoding="utf-8").write(standalone)
print(out, os.path.getsize(out))
