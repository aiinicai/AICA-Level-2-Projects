# WhatsApp Date Range Exporter

A Chrome extension (Manifest V3) that exports messages and attachments from **WhatsApp Web** for a date range you choose. It saves them to organised folders on your computer. It works in the Chrome tab where you are already signed in, and you need nothing except Chrome.

## Install

1. Extract the ZIP.
2. Open `chrome://extensions`.
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked**.
5. Select the folder that contains `manifest.json` (the `WhatsApp Date Range Exporter` folder).
6. Refresh your WhatsApp Web tab (F5).

Optional: pin the extension using the puzzle-piece icon in the Chrome toolbar.

### One-time Chrome settings

* **Allow multiple downloads (important).** Chrome lets a site download one file automatically, then holds the rest until you allow more. Set this in advance: open `chrome://settings/content/automaticDownloads`, click **Add** next to "Allowed to automatically download multiple files", and enter `web.whatsapp.com`. If you skip this, look for the blocked-download icon at the right end of the address bar during an export and choose **Always allow**. The extension warns you and keeps retrying for 3 minutes.
* **Turn off "Ask where to save each file"** at `chrome://settings/downloads`. If it stays on, Chrome opens a Save dialog for every file.

## Use

1. Open WhatsApp Web and, if you are exporting one chat, open that chat.
2. Click the extension icon.
3. **Chats:** choose *Current chat* (the default), *Selected chats or groups*, or *All chats*. For the last two, click **Load chat list**; WhatsApp's chat list scrolls briefly while it is read. The names that will be exported are listed above the Start button.
4. **Dates:** choose From and To. Both days are included in full, 00:00 to 23:59. The time zone defaults to **Asia/Dubai**. A one-day export uses the same date in both fields.
5. **Content:** *Messages and media*, *Messages only* or *Media only*.
   **Attachments to save:** choose *Sent and received*, *Received only* or *Sent only*, and tick the file types you want: Photos, Videos & GIFs, Voice notes & audio, Stickers, PDF, Word, Excel & CSV, PowerPoint, ZIP & archives, and Other files (anything else). Without the review step these rules are applied automatically. With it, they decide which files start ticked.
6. **Save to:** optionally type a client folder name. *Let me choose which attachments to save* is on by default. After each chat is read, the popup lists its attachments. Each is marked **Sent** or **Received** and shows its type, date, sender and file name. Narrow the list with the Received/Sent filter and the file-type boxes (with counts), tick or untick single files, and optionally type new file names. Unticked files are listed as "Not selected" in the index.
7. Click **Start export**. You can close the popup; the export keeps running in the WhatsApp tab, and a small panel there shows progress and a Cancel button. **Don't use that WhatsApp tab until the export finishes**, and keep it visible (it can be in its own window), because Chrome slows down background tabs.

## What you get

```
Downloads/WhatsApp Exports/[Client folder/]<Chat name>/<date range>/
    Transcript.html   searchable offline transcript (not created for "Media only")
    Index.html        attachment index: chat, sender, sent/received, message date, type, original and saved filename, status
    Index.csv         the same index for Excel (UTF-8, so Arabic displays correctly)
    Media/            the downloaded files
```

* The date range folder is named `2026-11-01` for one day, or `2026-11-01 to 2026-11-05` for a range.
* Exports with several chats also write `Export summary <date time>.html` in the export folder.
* Files are never overwritten. If a name already exists, Chrome adds ` (1)`, ` (2)` and so on, and the transcript and index link to the exact saved name.
* A file counts as saved only after Chrome reports the download complete. Totals for messages, saved files, skipped items and failed items are shown in the popup and in each index.
* Messages are matched by their own timestamp, including the message that carries an attachment.

### Attachments

Photos, videos, GIFs, voice notes, audio, stickers, PDFs, Office files, ZIPs and other documents are saved as real files. The extension uses WhatsApp Web's own **Download** controls: the message menu first, then the media viewer's download button. If WhatsApp provides no file, the item is listed as *Failed* with the reason. A thumbnail is never counted as a saved file.

* **View once** media is skipped and marked as such. WhatsApp does not allow it to be saved.
* Renamed files keep their original extension, and the original name stays in the index.

### "Partial" exports

WhatsApp Web keeps only part of your history. The extension loads earlier messages until it passes your start date or reaches the beginning of the chat. If WhatsApp stops providing history first, the chat is labelled **Partial** in the popup, transcript and index, with the **earliest date reached**. For older messages, use the phone or WhatsApp's own *Export chat*.

## Privacy and permissions

Everything stays on your computer. The extension sends nothing anywhere, uses no private WhatsApp APIs, and never reads cookies, keys or credentials.

| Permission | Why it is needed |
|---|---|
| `web.whatsapp.com` | Read the WhatsApp page you have open and click its normal controls |
| `downloads` | Save files into the export folders and confirm when each download finishes |
| `storage` | Remember your settings and show progress after you reopen the popup |
| `offscreen` | Build the transcript and index files locally before saving them |

## Important notes

* **WhatsApp's terms prohibit automated access to the service.** This tool only reads what your own WhatsApp Web session displays and clicks WhatsApp's normal buttons, but WhatsApp could still restrict an account it believes is automated. Use it at your own discretion, and export in reasonable batches.
* WhatsApp changes its web page often. Version 1.3.0 supports both the 2026 WhatsApp Web layout and the older one. If an export stops finding messages or files after a WhatsApp update, open a chat and use **Advanced → Check this WhatsApp page** in the popup. It reports what the extension can detect and contains no message text.
* After updating the extension files, click the reload arrow on its card in `chrome://extensions` (the card must show the new version), then press F5 in the WhatsApp tab. The popup header shows the version it is running, and it warns you if the WhatsApp tab still has an older copy.
* Not affiliated with or endorsed by WhatsApp or Meta.

## First live run: checklist

These checks need your signed-in WhatsApp session and could not be run without it:

1. After installing and refreshing, the popup shows **● Connected to WhatsApp Web**.
2. With a chat open, run **Advanced → Check this WhatsApp page**. You should see `messagesInDom` above 0, `withDatePrefix` above 0, `scrollContainer: true` and `menuButtonOnLast: true`.
3. Run a one-day export of a chat you know, with messages just before and after midnight. Allow multiple downloads when Chrome asks. In `Transcript.html`, confirm the first and last messages are the right ones.
4. Pick a day with a **PDF** and a **voice note**. Click both links in the transcript and check they open.
5. If two attachments share a filename, confirm they are saved as `name.ext` and `name (1).ext` and both appear in `Index.csv`.
6. Export a **group** day and check that photo-only messages show the correct sender.
7. Export a chat with a From date far in the past. If WhatsApp Web lacks that history, it should be labelled **Partial** with the earliest date reached.
8. Open `Index.csv` in Excel and check that Arabic names display correctly.

If a check fails, note which one and copy the output of *Check this WhatsApp page*.
