# CA_Buddy

A desktop-friendly tool with two parts:

1. **SafeAsk** (notice assistant: *AI need not know everything*) – reads a GST or income-tax notice, finds personal details (names, GSTIN, PAN, Aadhaar, TAN, CIN, address, PIN, phone, email, bank account, IFSC), lets you mask anything else, and then asks Claude, OpenAI or Gemini to **summarise the notice** or **draft a reply**. Only the masked text is sent. The real details are put back into the answer on your computer, and you can download it as a Word file.
2. **PDFsmith** (PDF all-in-one) – merge (with index page and bookmarks), split (by range, page count or file size), arrange pages, compress (with a target size), PDF to Word / Excel / images, images to PDF, Word or Excel to PDF, OCR, extract text, add or remove passwords, permanent redaction, page numbers, watermark, and "Certified true copy" stamp with signature/seal image.

Everything runs locally in your browser at `http://127.0.0.1:8765`. Nothing is uploaded anywhere except the masked notice text you choose to send to an AI provider.

## Start it

**Windows:** install [Python 3.10 or newer](https://www.python.org/downloads/) (tick *Add python.exe to PATH*), then double-click **Start CA_Buddy.bat**. The first start installs the packages (a few minutes, needs internet). After that it opens in seconds. Keep the black window open while you work; close it to stop.

**Mac / Linux:** run `./start.sh` in a terminal.

## Optional add-ons

| For | Install | Notes |
|---|---|---|
| Scanned notices and the OCR tool | [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Windows installer) | Use the default install folder. To read Hindi or Tamil notices, tick those languages during install. Restart the app afterwards. |
| Word / Excel to PDF | Microsoft Word (already on most office PCs) or the free [LibreOffice](https://www.libreoffice.org/) | Excel and PowerPoint need LibreOffice. |

Digital notices downloaded from the GST and income-tax portals work without Tesseract.

## API keys

Paste your own key in SafeAsk. Get one from:

- Claude: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys
- Gemini: https://aistudio.google.com/apikey

Keys are sent only to the provider you pick. They are kept in the browser only if you tick *Remember my keys on this computer*. Click **Load models** to see which models your key can use; the model box accepts any model name.

## How masking works

- Detected details are replaced with codes like `[NAME_1]`, `[GSTIN_1]`, `[PAN_1]`. The model is told to use the codes, and the app swaps the real values back in the answer.
- Untick anything the model needs to see as is. Add more with **Find and mask**, or select text in the preview and click **Mask this**.
- Notice reference numbers / DIN are detected but left visible by default (they're useful for the reply). Tick them to hide them.
- The model is given harmless hints such as "GSTIN_1 is registered in Tamil Nadu" and "PAN_1 belongs to a company" so it can reason about jurisdiction and entity type.
- Text you type in the instructions box is masked with the same codes.
- **Show what the AI returned** on the answer page shows the exact text the model sent back.
- **Redacted PDF** gives you a copy of the notice with the masked details permanently blacked out.

Automatic detection is a helper, not a guarantee. Always look at the preview before sending.

## Changing the prompts

The instructions given to the model are in `core/prompts.py` (summary structure, reply structure, tone options). Edit them to match your firm's style; restart the app to apply.

## Files

```
app.py              web server and routes
core/pdf_tools.py   all PDF operations (PyMuPDF)
core/pii.py         detection, masking and unmasking
core/notice.py      text extraction, OCR fallback, notice type detection
core/prompts.py     prompts sent to the model
core/llm.py         Claude / OpenAI / Gemini calls
core/mdconv.py      answer to HTML and Word
static/             the interface (HTML, CSS, JavaScript)
```

## Troubleshooting

- **Port already in use** – the app picks the next free port automatically and opens it.
- **Office proxy / SSL errors when calling the AI** – set `HTTPS_PROXY` and, if your firm uses its own certificate, `SSL_CERT_FILE` before starting.
- **"Model not recognised"** – click **Load models** and choose from the list.
