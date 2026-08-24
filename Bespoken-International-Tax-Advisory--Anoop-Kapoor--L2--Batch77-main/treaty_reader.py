"""
DTAA Advisor - Treaty Reader Engine
Reads and extracts text from treaty PDFs stored in treaties/ folder
"""

import os
import re
import PyPDF2
from pathlib import Path


TREATIES_FOLDER = Path(__file__).parent / "treaties"

# Country name mapping for smart detection
COUNTRY_MAP = {
    "usa": ["usa", "united states", "america", "us-india", "india-us"],
    "uk": ["uk", "united kingdom", "britain", "england", "india-uk", "uk-india"],
    "uae": ["uae", "united arab emirates", "dubai", "abu dhabi"],
    "singapore": ["singapore", "sing"],
    "mauritius": ["mauritius"],
    "australia": ["australia", "australian"],
    "canada": ["canada", "canadian"],
    "germany": ["germany", "german", "deutschland"],
    "china": ["china", "chinese", "peoples republic"],
    "japan": ["japan", "japanese"],
    "netherlands": ["netherlands", "dutch", "holland"],
    "hong kong": ["hong-kong", "hong kong", "hk", "india-hong-kong"],
    "malaysia": ["malaysia", "malaysian"],
    "new zealand": ["new-zealand", "new zealand", "nz"],
    "france": ["france", "french"],
    "switzerland": ["switzerland", "swiss"],
    "sweden": ["sweden", "swedish"],
    "denmark": ["denmark", "danish"],
    "norway": ["norway", "norwegian"],
    "finland": ["finland", "finnish"],
    "south africa": ["south africa"],
    "sri lanka": ["sri lanka", "ceylon"],
    "bangladesh": ["bangladesh"],
    "thailand": ["thailand", "thai"],
    "italy": ["italy", "italian"],
    "spain": ["spain", "spanish"],
    "russia": ["russia", "russian"],
    "brazil": ["brazil", "brazilian"],
}


def get_available_treaties():
    """Scan treaties folder and return list of available PDFs"""
    folder = TREATIES_FOLDER
    if not folder.exists():
        return []
    pdfs = list(folder.glob("*.pdf"))
    return sorted([p.name for p in pdfs])


def detect_country_from_filename(filename):
    """Detect country from PDF filename"""
    fname = filename.lower()
    for country, keywords in COUNTRY_MAP.items():
        for kw in keywords:
            if kw in fname:
                return country.title()
    return filename.replace(".pdf", "").replace("-", " ").replace("_", " ")


def extract_text_from_pdf(pdf_path, max_pages=None):
    """Extract full text from a PDF file"""
    try:
        text = ""
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            pages_to_read = min(total_pages, max_pages) if max_pages else total_pages
            for i in range(pages_to_read):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def extract_key_articles(text):
    """Extract key articles from treaty text"""
    articles = {}
    article_pattern = re.compile(
        r"(ARTICLE\s+\d+[A-Z]?\s*\n[A-Z\s]+\n)(.*?)(?=ARTICLE\s+\d+[A-Z]?\s*\n|$)",
        re.DOTALL | re.IGNORECASE
    )
    matches = article_pattern.findall(text)
    for header, content in matches:
        article_name = header.strip().replace("\n", " ")
        articles[article_name] = content.strip()[:2000]
    return articles


def find_relevant_sections(text, query_keywords):
    """Find sections of treaty text relevant to a query"""
    relevant_chunks = []
    query_lower = query_keywords.lower()
    keywords = [kw for kw in query_lower.split() if len(kw) > 2]

    # Split by article boundaries first for better targeting
    import re
    # Try to split on ARTICLE headings
    article_splits = re.split(r'(ARTICLE\s+\d+[A-Z]?\b[^\n]*)', text, flags=re.IGNORECASE)

    # If article splitting worked, score each article section
    if len(article_splits) > 3:
        sections = []
        i = 0
        while i < len(article_splits):
            if re.match(r'ARTICLE\s+\d+', article_splits[i], re.IGNORECASE) and i + 1 < len(article_splits):
                header = article_splits[i].strip()
                body = article_splits[i + 1] if i + 1 < len(article_splits) else ""
                sections.append(header + "\n" + body)
                i += 2
            else:
                i += 1

        for section in sections:
            section_lower = section.lower()
            score = sum(2 for kw in keywords if kw in section_lower)
            # Bonus for keyword in header/first line
            first_line = section.split('\n')[0].lower()
            score += sum(3 for kw in keywords if kw in first_line)
            if score >= 2 and len(section.strip()) > 50:
                relevant_chunks.append((score, section.strip()))
    else:
        # Fallback to paragraph splitting
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            para_lower = para.lower()
            score = sum(1 for kw in keywords if kw in para_lower)
            if score >= 2 and len(para.strip()) > 100:
                relevant_chunks.append((score, para.strip()))

    relevant_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for _, chunk in relevant_chunks[:5]]

    if not top_chunks:
        return ""

    return "\n\n" + "─"*60 + "\n\n".join(top_chunks)


def get_treaty_text_for_country(country_name, max_chars=8000):
    """Get treaty text for a specific country"""
    folder = TREATIES_FOLDER
    if not folder.exists():
        return None, f"Treaties folder not found: {TREATIES_FOLDER}"

    country_lower = country_name.lower()
    best_file = None
    best_score = 0

    # Exclude non-DTAA files
    exclude_keywords = [
        "intergovernmental", "fatca", "iga", "country-by-country",
        "countrybycount", "cbc", "cbcr", "exchange-of-information",
        "tiea", "administrative"
    ]

    for pdf_file in folder.glob("*.pdf"):
        fname_lower = pdf_file.name.lower()

        # Skip non-DTAA files
        if any(excl in fname_lower for excl in exclude_keywords):
            continue

        keywords = COUNTRY_MAP.get(country_lower, [country_lower])
        country_score = sum(1 for kw in keywords if kw in fname_lower)

        # Must match at least one country keyword
        if country_score == 0:
            continue

        score = country_score

        # Prefer synthesised text (MLI modified) over comprehensive
        if "synthes" in fname_lower:
            score += 3
        if "comprehensive" in fname_lower:
            score += 2
        if "dtaa" in fname_lower or "agreement" in fname_lower:
            score += 1

        if score > best_score:
            best_score = score
            best_file = pdf_file

    if not best_file:
        return None, f"No treaty found for {country_name}"

    text = extract_text_from_pdf(best_file)
    if len(text) > max_chars:
        text = text[:max_chars]

    return text, best_file.name


def get_all_treaty_names():
    """Return list of countries with available treaties"""
    available = get_available_treaties()
    countries = []
    for fname in available:
        country = detect_country_from_filename(fname)
        if country not in countries and "afghanistan" not in country.lower():
            countries.append(country)
    return sorted(set(countries))


def search_treaty_for_topic(country_name, topic, max_chars=6000):
    """Search treaty text for a specific topic (dividends, royalty, FTS etc.)"""
    text, source = get_treaty_text_for_country(country_name, max_chars=15000)
    if text is None:
        return None, source

    relevant = find_relevant_sections(text, topic)
    if not relevant:
        relevant = text[:max_chars]

    return relevant[:max_chars], source
