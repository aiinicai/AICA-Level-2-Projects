def page_count(p):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(p); n = len(d); d.close(); return n
def format_pages(pages):
    pages = sorted(pages); out = []; i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1: j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}"); i = j + 1
    return ",".join(out)
def parse_pages(text, total):
    s = set()
    for part in text.replace(" ", "").split(","):
        if not part: continue
        if "-" in part:
            a, b = part.split("-"); s.update(range(int(a), int(b) + 1))
        else: s.add(int(part))
    return sorted(p for p in s if 1 <= p <= total)
