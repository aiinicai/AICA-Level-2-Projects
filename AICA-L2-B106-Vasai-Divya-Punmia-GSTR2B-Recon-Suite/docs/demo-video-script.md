# Demo video script: GSTR-2B Recon Suite

**Length:** about 3 minutes  
**Format:** 1920×1080 screen recording, MP4, voice-over (or on-screen captions only)  
**For:** the GitHub README / repository page

> GitHub embeds an MP4 dragged into the README editor, but the file must be **under 10 MB** on a free account (100 MB on paid plans). A 3-minute 1080p recording usually needs compressing; see "Export" at the end.

---

## Before you record

1. **Use demo data, not a client's.** In the app, click **+** and create a client called **Demo Traders Pvt Ltd**, GSTIN `27AAAAA0000A1Z5`, period `Oct 2026`. Don't show any real client.
2. Keep these two files ready in a folder you can see:
   - `D:\Level 2\Day 5\gstr-2b-recon\sample-uploads\gstr2b-sample.xlsx`
   - `D:\Level 2\Day 5\gstr-2b-recon\sample-uploads\purchase-register-sample.csv`
3. In **Import & Settings → Your firm**, enter a demo firm (for example "ABC & Associates", "CA Demo", demo e-mail). It appears on the PDF notice.
4. Close other browser tabs, hide bookmarks (Ctrl+Shift+B), and set browser zoom to 110% so text is readable in the video.
5. Turn on Windows **Do not disturb** so no notifications pop up.
6. Recording tool: **Snipping Tool → Record** (Windows 11), **Xbox Game Bar** (Win+Alt+R) or **OBS Studio**.

---

## Scene list

| # | Time | On screen | Voice-over / caption |
|---|---|---|---|
| 1 | 0:00–0:12 | Title card (or the app's dashboard with a caption overlay): **GSTR-2B Recon Suite** | "GSTR-2B Recon Suite: reconcile your GSTR-2B with your purchase register on your own computer, with no cloud and no subscription." |
| 2 | 0:12–0:25 | File Explorer showing the suite folder. Double-click **1-Start-Localhost.bat**; the black window appears and the browser opens. | "Double-click one file to start. It sets up everything it needs the first time, and keeps your data in a local SQLite database." |
| 3 | 0:25–0:40 | Top bar: the client selector showing **Demo Traders Pvt Ltd · Oct 2026**. Hover the **Tolerance ₹** box. | "Each client and period has its own workspace. The tolerance sets how big a difference still counts as matched." |
| 4 | 0:40–1:05 | **Import & Settings** → drop `gstr2b-sample.xlsx` into box 1. The column-matching window opens. Point at the "Sure" badges and the preview row showing **04/10/2026**. Click **Import**. | "Drop in the GSTR-2B Excel straight from the portal. The app finds the columns itself, even with the portal's two-row headings, and shows a preview before saving. Dates are always read as Indian dd/mm/yyyy." |
| 5 | 1:05–1:15 | Drop `purchase-register-sample.csv` into box 2. Point at **Supplier Invoice No.** in the mapping. Click **Import**. | "Then your purchase register, from Tally, Busy, SAP or plain Excel. It picks the supplier's invoice number, not your voucher number." |
| 6 | 1:15–1:40 | **Compliance Dashboard**: pan over the six status cards, the donut chart, then scroll to the **GSTR-3B Table 4** table. | "Reconciliation runs instantly. Every invoice is counted exactly once: matched, smart-matched, mismatched, or missing on either side. Below, suggested GSTR-3B Table 4 figures, with reverse charge and blocked credit separated." |
| 7 | 1:40–1:58 | **Smart Match Runs** → Pass 1 shows `INV-88912` matched to `0INV-88912`. | "When invoice numbers don't match exactly, three smart passes look at the invoice core number, amount and date, and the tax values." |
| 8 | 1:58–2:15 | **Reconciliation Ledger** → filter **Missing in 2B** → click **Block** on the Larsen & Toubro row → choose **17(5)(c) Works contract** → **Block credit**. Then click **Note** on another row and type "Supplier to amend GSTR-1". | "Filter the ledger, block ineligible credit under Section 17(5), and add notes. Everything is saved and recorded in the audit log." |
| 9 | 2:15–2:35 | **Supplier Follow-ups** → Larsen & Toubro selected → click **PDF notice**; open the PDF briefly. Then click the **E-mail text** tab. | "For invoices still missing from GSTR-2B, generate a PDF notice or a ready e-mail for the supplier, including their MSME status." |
| 10 | 2:35–2:48 | **ITC Health Check**: click through the cards (GSTIN check, Sec 16(4), Non-filers). Then **Filing Reports → By month**. | "Health checks catch invalid GSTINs, duplicate invoice numbers, Section 16(4) time limits and non-filers. Reports by supplier and month." |
| 11 | 2:48–2:55 | Click the **Excel** button on a tab, then **Full export** in the top bar; show the workbook open in Excel with its sheet tabs. | "Every screen exports to Excel, or download everything in one workbook." |
| 12 | 2:55–3:05 | Phone view: in Chrome press F12 → device toolbar (Ctrl+Shift+M) → iPhone size, scroll the dashboard; or show the app on a real phone using the network link from **2-Start-Server-Host.bat**. | "It works on phones and tablets too. Share it on your office network with the server-host launcher." |
| 13 | 3:05–3:12 | End card: repository URL and "Download → double-click 1-Start-Localhost.bat". | "Download it from GitHub and double-click to start." |

---

## Tips while recording

- Move the mouse slowly and pause about one second on anything you point at.
- Record each scene as a separate clip; it is much easier to redo one scene than the whole video.
- If you record voice separately, read the narration column aloud once to check the timing, then record.
- Don't show the black server window for long; it shows the folder path and network IP addresses.

## Export for GitHub

1. Export from your editor (Clipchamp, which comes with Windows 11, works well) at **1080p, 30 fps**.
2. If the file is over 10 MB, compress it. In Clipchamp choose **720p**, or with ffmpeg:

   ```bash
   ffmpeg -i demo.mp4 -vf scale=1280:-2 -c:v libx264 -crf 30 -preset slow -an demo-small.mp4
   ```

   (`-an` drops the audio track; remove it to keep the voice-over.)
3. On GitHub, open `README.md` → edit (pencil icon) → drag the MP4 into the editor where you want it, near the top. GitHub uploads it and inserts a link that plays inline. Commit the change.
4. Optional: also save a 10-second GIF of scene 6 (the dashboard) as the README's first image, since GIFs autoplay in previews.
