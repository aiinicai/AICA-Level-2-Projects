# Recording the capstone video of Office Manager (Windows)

ICAI's AICA Level 2 Capstone Project rules require a video that shows **both your face and the technical
content together**, uploaded to YouTube (Unlisted) or Google Drive, with the link submitted through the
same Google Form as the GitHub project link. A screen-only recording (e.g. plain Xbox Game Bar) does not
meet this requirement on its own.

**Recommended: OBS Studio (free, obsproject.com)** — gives a picture-in-picture layout with your face in a
corner over the app:
1. Install OBS Studio with default settings.
2. Sources > `+` > **Window Capture** → pick the Office Manager window.
3. Sources > `+` > **Video Capture Device** → pick your webcam, then drag/resize it into a corner (e.g.
   bottom-right) over the window capture. This is a one-time setup; OBS remembers it next time.
4. Click **Start Recording**, and **Stop Recording** when done. Check Settings > Output in OBS for where
   the file is saved.

**Do this before recording:** run the app and create a firm with a fake name and a couple of fake clients
only — never show a real client's PAN/GSTIN/phone number, or the Settings email password, on camera.

**Suggested 4–6 minute script**, explaining out loud which part of the 5-day AICA Level 2 course each
screen demonstrates:
1. Login / dashboard
2. Add a client (GST-portal lookup, PAN/pincode auto-fill)
3. Bulk-create GST/ITR/TDS returns for a month
4. Compliance calendar and Tasks board
5. Create an invoice, record a payment, show the PDF
6. Reports with your letterhead (PDF/Excel)
7. WhatsApp bulk reminders
8. Settings: logo, email, backup

**To install and start from scratch on camera:** `pip install -r requirements.txt` then
`python run_desktop.py`.

**After recording:** upload to YouTube as **Unlisted** (YouTube Studio > Upload, visibility = Unlisted) or
to Google Drive with "Anyone with the link" sharing turned on, then paste that link into the Google Form
(https://forms.gle/cucnBGn34bVHFaxt9) together with the GitHub project link.
