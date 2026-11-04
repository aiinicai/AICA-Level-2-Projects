"""Generate realistic sample WhatsApp exports (Android + iPhone) for testing.
All names and data are fictional."""
import os, io, zipfile, subprocess, random
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NB = " "   # narrow no-break space used by newer Android exports
LRM = "‎"  # left-to-right mark used by iOS exports


def img_bytes(title, lines, color, size=(900, 1200)):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, size[0], 140], fill=color)
    d.text((40, 45), title, font=ImageFont.truetype(FONTB, 44), fill="white")
    f = ImageFont.truetype(FONT, 30)
    y = 200
    for ln in lines:
        d.text((50, y), ln, font=f, fill="#222")
        y += 60
    d.rectangle([40, y + 20, size[0] - 40, y + 24], fill="#ccc")
    b = io.BytesIO(); im.save(b, "JPEG", quality=82); return b.getvalue()


def photo_bytes(seed, label):
    random.seed(seed)
    im = Image.new("RGB", (1200, 900))
    d = ImageDraw.Draw(im)
    top = (random.randint(40, 120), random.randint(90, 160), random.randint(150, 220))
    for y in range(900):
        t = y / 900
        d.line([(0, y), (1200, y)], fill=tuple(int(top[i] * (1 - t) + (230, 200, 150)[i] * t) for i in range(3)))
    for _ in range(14):
        x, y, r = random.randint(0, 1200), random.randint(300, 900), random.randint(40, 160)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(random.randint(30, 90), random.randint(80, 140), random.randint(40, 90)))
    d.text((40, 820), label, font=ImageFont.truetype(FONTB, 40), fill="white")
    b = io.BytesIO(); im.save(b, "JPEG", quality=80); return b.getvalue()


def pdf_bytes(title, rows):
    b = io.BytesIO(); c = canvas.Canvas(b, pagesize=A4)
    c.setFont("Helvetica-Bold", 18); c.drawString(60, 790, title)
    c.setFont("Helvetica", 11); y = 750
    for r in rows:
        c.drawString(60, y, r); y -= 22
    c.showPage(); c.setFont("Helvetica", 11); c.drawString(60, 790, "Page 2 - annexure"); c.save()
    return b.getvalue()


def media_bytes(kind, path):
    tmp = os.path.join(OUT, "_tmp" + os.path.splitext(path)[1])
    if kind == "audio":
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
               "-c:a", "libopus", "-b:a", "24k", tmp]
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=480x360:rate=15:duration=3",
               "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", tmp]
    subprocess.run(cmd, check=True)
    data = open(tmp, "rb").read(); os.remove(tmp); return data


# ---------------------------------------------------------------- Android group chat
def android(later=False):
    files = {}
    inv = img_bytes("TAX INVOICE  #MT/245", ["Mehta Traders", "GSTIN: 24AAAAA0000A1Z5", "Date: 28-10-2026",
                     "Steel rods  120 kg   Rs 84,000", "CGST 9%            Rs  7,560", "SGST 9%            Rs  7,560",
                     "Total              Rs 99,120"], "#1f6f5c")
    files["IMG-20261101-WA0003.jpg"] = inv
    files["IMG-20261101-WA0004.jpg"] = photo_bytes(4, "Godown stock - 01 Nov")
    files["DOC-20261101-WA0005.pdf"] = pdf_bytes("GSTR-2B Reconciliation - Oct 2026",
        ["Supplier  | Invoice   | ITC as per books | ITC as per 2B | Diff", "Shree Steels | SS/889 | 18,000 | 18,000 | 0",
         "Patel Agencies | PA/77 | 9,450 | 0 | 9,450", "Total ITC at risk: Rs 9,450"])
    files["PTT-20261102-WA0006.opus"] = media_bytes("audio", "x.opus")
    files["VID-20261102-WA0007.mp4"] = media_bytes("video", "x.mp4")
    files["IMG-20261103-WA0008.jpg"] = photo_bytes(9, "Signed board resolution")
    files["DOC-20261103-WA0009.pdf"] = pdf_bytes("Engagement Letter - FY 2026-27",
        ["Scope: GST audit and annual return", "Fees: as agreed", "Timeline: 30 days from receipt of data"])

    def L(d, t, who, msg):
        return f"{d}, {t.replace(' ', NB)} - {who}: {msg}"

    lines = [
        f"01/11/26, 9:58{NB}am - Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them. Learn more.",
        f"01/11/26, 9:58{NB}am - Rakesh Mehta created group \"Mehta Traders - GST Audit\"",
        f"01/11/26, 9:58{NB}am - Rakesh Mehta added CA Vihit",
        L("01/11/26", "10:02 am", "Rakesh Mehta", "Good morning sir 🙏 Creating this group for the GST audit work"),
        L("01/11/26", "10:04 am", "CA Vihit", "Good morning Rakesh bhai. Please share purchase invoices for October and the stock statement."),
        L("01/11/26", "10:20 am", "Rakesh Mehta", "IMG-20261101-WA0003.jpg (file attached)"),
        "Invoice from Mehta for steel rods",
        L("01/11/26", "10:21 am", "Rakesh Mehta", "IMG-20261101-WA0004.jpg (file attached)"),
        L("01/11/26", "10:22 am", "Rakesh Mehta", "Stock photo from godown"),
        L("01/11/26", "11:45 am", "Neha (Accounts)", "Sir, attaching the 2B reconciliation we prepared"),
        L("01/11/26", "11:45 am", "Neha (Accounts)", "DOC-20261101-WA0005.pdf (file attached)"),
        L("01/11/26", "12:10 pm", "CA Vihit", "Thanks Neha. Patel Agencies invoice PA/77 is not appearing in 2B.\nITC of ₹9,450 is at risk.\nPlease ask the supplier to file GSTR-1 before 11th."),
        L("01/11/26", "12:14 pm", "Neha (Accounts)", "Noted sir 👍 Will follow up today itself"),
        L("01/11/26", "6:30 pm", "Rakesh Mehta", "This message was deleted"),
        L("02/11/26", "9:15 am", "Rakesh Mehta", "PTT-20261102-WA0006.opus (file attached)"),
        L("02/11/26", "9:40 am", "CA Vihit", "Got your voice note. Yes, we can meet on Tuesday at 4 pm at our office."),
        L("02/11/26", "3:05 pm", "Neha (Accounts)", "VID-20261102-WA0007.mp4 (file attached)"),
        L("02/11/26", "3:06 pm", "Neha (Accounts)", "Screen recording of the portal error while downloading 2B"),
        L("02/11/26", "3:30 pm", "CA Vihit", "This is a portal-side issue. Try again after 8 pm, or download the Excel version from https://www.gst.gov.in"),
        L("02/11/26", "8:47 pm", "Neha (Accounts)", "Downloaded successfully ✅"),
        f"03/11/26, 10:00{NB}am - Rakesh Mehta added Suresh Patel",
        L("03/11/26", "10:05 am", "Suresh Patel", "Hello all. I'm from Patel Agencies. GSTR-1 for October has been filed today."),
        L("03/11/26", "10:12 am", "CA Vihit", "Thank you Suresh ji. We will re-check 2B after it updates."),
        L("03/11/26", "11:30 am", "Rakesh Mehta", "IMG-20261103-WA0008.jpg (file attached)"),
        "Board resolution signed and stamped",
        L("03/11/26", "4:45 pm", "CA Vihit", "DOC-20261103-WA0009.pdf (file attached)"),
        "Engagement letter for FY 2026-27. Kindly sign and return.",
        L("03/11/26", "4:50 pm", "Rakesh Mehta", "<Media omitted>"),
        L("03/11/26", "5:02 pm", "Rakesh Mehta", "Will sign and send by tomorrow. Thank you sir 🙏"),
    ]
    if later:
        # A second export taken a day later: one message edited, one deleted for everyone,
        # one removed with "delete for me", and new messages added.
        lines = [l for l in lines if "Good morning Rakesh bhai" not in l]          # deleted for me -> absent
        lines = [l.replace("Noted sir 👍 Will follow up today itself", "This message was deleted") for l in lines]
        i = next(i for i, l in enumerate(lines) if "Thanks Neha. Patel Agencies" in l)
        lines[i] = lines[i].replace("before 11th.", "by 10th, not 11th.") + " <This message was edited>"
        files["IMG-20261104-WA0010.jpg"] = img_bytes("SIGNED - Engagement Letter", ["Accepted for Mehta Traders", "Signed: R. Mehta", "Date: 04-11-2026"], "#8a5a1f")
        lines += [
            L("04/11/26", "11:20 am", "Rakesh Mehta", "IMG-20261104-WA0010.jpg (file attached)"),
            "Signed engagement letter attached",
            L("04/11/26", "11:42 am", "CA Vihit", "Received, thank you. *Fee of ₹45,000* will be billed on completion."),
            L("04/11/26", "12:05 pm", "Neha (Accounts)", "Sir, 2B now shows PA/77 ✅ ITC of ₹9,450 is safe."),
        ]
    files["WhatsApp Chat with Mehta Traders - GST Audit.txt"] = ("\n".join(lines) + "\n").encode()
    path = os.path.join(OUT, "WhatsApp Chat with Mehta Traders - GST Audit" + (" (4 Nov).zip" if later else ".zip"))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    return path


# ---------------------------------------------------------------- iPhone 1:1 chat
def iphone():
    files = {}
    files["00000004-PHOTO-2026-10-28-18-22-10.jpg"] = img_bytes("SALE DEED - Page 1", ["Flat No. 1204, Tower B", "Andheri (West), Mumbai",
        "Consideration: Rs 1,85,00,000", "Stamp duty paid: Rs 11,10,000", "Registered on 20-10-2026"], "#4a3f8f")
    files["00000007-Form 16A - Q2.pdf"] = pdf_bytes("Form 16A - Q2 FY 2026-27", ["Deductor: ABC Realty", "TDS: Rs 24,05,000", "Section: 195"])
    files["00000009-AUDIO-2026-10-29-09-02-55.opus"] = media_bytes("audio", "x.opus")
    files["00000011-PHOTO-2026-10-30-20-15-03.jpg"] = photo_bytes(21, "Bank credit advice")

    T = lambda d, t, who, msg: f"[{d}, {t}] {who}: {msg}"
    lines = [
        T("28/10/26", "6:20:01 PM", "Anjali Shah (NRI)", f"{LRM}Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them."),
        T("28/10/26", "6:20:44 PM", "Anjali Shah (NRI)", "Hi Vihit, the sale of the Andheri flat is done. Sending the deed."),
        T("28/10/26", "6:22:10 PM", "Anjali Shah (NRI)", f"{LRM}<attached: 00000004-PHOTO-2026-10-28-18-22-10.jpg>"),
        T("28/10/26", "6:40:15 PM", "Vihit", "Thanks Anjali. Did the buyer deduct TDS? Please share Form 16A once available."),
        T("29/10/26", "9:02:55 AM", "Anjali Shah (NRI)", f"{LRM}<attached: 00000009-AUDIO-2026-10-29-09-02-55.opus>"),
        T("29/10/26", "9:30:12 AM", "Vihit", "Understood. Since you held it for more than 2 years, it is long-term.\nWe can look at a lower deduction certificate for future cases,\nand claim the excess TDS as refund in your return."),
        T("29/10/26", "10:01:40 AM", "Anjali Shah (NRI)", "Perfect 👍"),
        T("30/10/26", "8:10:22 PM", "Anjali Shah (NRI)", f"{LRM}Form 16A - Q2.pdf • {LRM}1 page {LRM}<attached: 00000007-Form 16A - Q2.pdf>"),
        T("30/10/26", "8:15:03 PM", "Anjali Shah (NRI)", f"{LRM}<attached: 00000011-PHOTO-2026-10-30-20-15-03.jpg>"),
        T("30/10/26", "8:16:00 PM", "Anjali Shah (NRI)", "Credit advice from NRO account"),
        T("30/10/26", "9:00:00 PM", "Vihit", f"{LRM}This message was deleted."),
        T("31/10/26", "11:11:11 AM", "Vihit", "Can you also confirm the date you left India this year? Needed for residential status."),
        T("31/10/26", "11:30:45 AM", "Anjali Shah (NRI)", "Left on 14 April 2026. Was in India only 40 days this FY."),
        T("31/10/26", "11:31:02 AM", "Anjali Shah (NRI)", f"{LRM}image omitted"),
        T("31/10/26", "11:45:00 AM", "Vihit", "Noted, thank you. I'll send the computation by Monday."),
        T("31/10/26", "11:52:10 AM", "Anjali Shah (NRI)", "ધન્યવાદ સાહેબ! મમ્મી પૂછતાં હતાં કે રિફંડ ક્યારે આવશે?"),
        T("31/10/26", "12:05:30 PM", "Vihit", "रिफंड आयकर रिटर्न फाइल होने के बाद लगभग 4–6 सप्ताह में आ जाएगा।"),
    ]
    files["_chat.txt"] = ("\n".join(lines) + "\n").encode()
    path = os.path.join(OUT, "WhatsApp Chat - Anjali Shah (NRI).zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    return path


if __name__ == "__main__":
    for p in (android(), android(later=True), iphone()):
        print(p, os.path.getsize(p))
