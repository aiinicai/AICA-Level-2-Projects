"""Repair of OCR spacing artefacts ("foraperiodof9years" -> "for a period of 9 years").

Strategy: (1) regex fixes for camel-case / digit / punctuation glue; (2) dictionary
segmentation of long unknown lower-case runs using a built-in legal/lease vocabulary
plus the words that appear correctly spaced elsewhere in the same document.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

BASE_WORDS = """
a about above accordance according act active addition additional address admeasuring advance after against agree agreed
agreement all allowed along also amount an and annexure annual any appear applicable apply are area as assign assigns at
authorised authorized available bank be bearing been before behalf being below between both breach building but by called
calendar can car carpet case cause certificate charges clause commence commencement commencing company companies compensation
completion condition conditions consent consideration consultant contained continue corporate cost costs date day days deed
deposit description determine due during each earlier effect either end ending english entered entitled equivalent escalated
escalation estate every excepted exclusive execute executed executing expiry expression extend extension extra facility fee
fees fifteen first fit five floor following for four free from further given giving gst hand handed handover hand have having
hereby hereafter hereinafter herein hereunder hereto however if in include including incorporated increase increased
industrial interest into is it its lakh lane last lease leased leases lessee lessees lessor lessors liability licence license
licensed licensee licensor limited llp lock made maintenance may means month monthly months more mutual mutually nagar nine no
not notice obligations of office on one only option or original other outs owner paid park parking part partnership parties
party pay payable payment payments penalty per period permitted plot possession premises prior private property provided
purchase purpose rate reasonable referred refund refundable refunded registered registration remove renew renewal rent rental
repugnant restore right road rupees said same schedule security seal seventy shall shed six sole square stamp successors such
tear term terminate termination terms than that the their thereof these this three thirty through till to together total
twelve two under unit unless until upon use used vacant was wear were whereas which whichever will with within without
witnesseth written year years
another together into onto within without hereby thereof upon herein hereto whereas therefore income inform
others otherwise nothing something anything everything whatever whenever wherever notwithstanding however moreover
warehouse blocks block percent fifteen twenty forty fifty sixty eighty ninety hundred thousand crore crores lakhs sum
about any as at be by do go he if in is it me my no of on or so to up us we an am as day days rent rents month each
every other same these those them then there where when what who whom whose why how than that this with from have has
had not but all can will would should could must shall may might also only just very more most less least much many
few several some such own new old good well back down over under again further once here both each few more most
lessee's lessor's licensee's licensor's owner's premises' shops shop godown office offices unit units floor floors
sq ft feet metres meters tenant tenants landlord landlords company private public limited deed deeds sale leave
electricity water charges taxes municipal property tax insurance repairs repair structural damage damages alteration
alterations additions fixtures fittings furniture equipment machinery vehicle vehicles store stores mall retail
gross sales revenue share turnover minimum guaranteed guarantee rental rentals invoice invoices pay payable monthly
quarter quarterly annually yearly half early late interest simple compound rate rates bank account cheque cheques
""".split()


@lru_cache(maxsize=1)
def _base_vocab() -> frozenset:
    return frozenset(BASE_WORDS)


def _segment(token: str, vocab: set, max_word: int = 20) -> list[str] | None:
    n = len(token)
    best: list[list[str] | None] = [None] * (n + 1)
    best[0] = []
    for i in range(1, n + 1):
        for j in range(max(0, i - max_word), i):
            w = token[j:i]
            if best[j] is not None and (w in vocab or (len(w) == 1 and w == "a")):
                cand = best[j] + [w]
                if best[i] is None or len(cand) < len(best[i]):
                    best[i] = cand
    return best[n]


def normalize_ocr_text(text: str) -> str:
    t = text.replace("（", "(").replace("）", ")").replace("，", ",").replace("：", ":")
    t = re.sub(r"(\d)\s*(st|nd|rd|th)(?=[a-z]{3,})", r"\1\2 ", t)      # "5 thdayof" -> "5th dayof"
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)                       # camelCase glue
    t = re.sub(r"([A-Z]{2,})([A-Z][a-z]{2,})", r"\1 \2", t)            # LMNRetail -> LMN Retail
    t = re.sub(r"([,;:])(?=[A-Za-z(])", r"\1 ", t)                      # ",a company"
    t = re.sub(r"\)(?=[A-Za-z0-9])", ") ", t)
    t = re.sub(r"(?<=[A-Za-z0-9])\((?=[A-Za-z])", " (", t)             # "9(nine)" -> "9 (nine)"
    t = re.sub(r"(?<=[A-Za-z])\((?=[0-9])", " (", t)
    t = re.sub(r"(\d)(?!(?:st|nd|rd|th)\b)([A-Za-z]{2,})", r"\1 \2", t)  # 2013having -> 2013 having (keeps 2nd)
    t = re.sub(r"(?<![A-Z\-/])([a-z]{2,})(\d)", r"\1 \2", t)           # every3 -> every 3
    t = re.sub(r"(?<=[a-z])\.(?=[A-Z][a-z])", ". ", t)                  # "each.The" -> "each. The"
    t = re.sub(r"(\d+)\.(?=[A-Z][a-z])", r"\1. ", t)                    # "1.The" -> "1. The"
    # dictionary segmentation of glued lower-case runs
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", t)]
    counts = Counter(words)
    doc_vocab = {w for w, c in counts.items() if 2 <= len(w) <= 14 and (c >= 2 or len(w) <= 6)}
    vocab = set(_base_vocab()) | doc_vocab

    base = _base_vocab()

    def fix(m: re.Match) -> str:
        tok = m.group(0)
        low = tok.lower()
        if len(tok) < 4 or low in base or (low in doc_vocab and counts[low] >= 2):
            return tok
        if len(tok) < 7:
            # short tokens: split only into base-vocabulary words ("toas" -> "to as", "rentof" -> "rent of")
            seg = _segment(low, set(base))
            if seg and len(seg) == 2 and all(len(w) >= 2 for w in seg):
                return tok[:len(seg[0])] + " " + tok[len(seg[0]):]
            return tok
        seg = _segment(low, vocab - {low})
        if seg and 2 <= len(seg) <= max(2, len(low) // 2):
            out, pos = [], 0
            for w in seg:
                out.append(tok[pos:pos + len(w)])
                pos += len(w)
            return " ".join(out)
        return tok

    t = re.sub(r"[A-Za-z]+", fix, t)
    # OCR digit confusions inside numbers: 40,0o0 -> 40,000 ; 1l,000 -> 11,000
    t = re.sub(r"(?<=[\d,])[oO](?=[\d,])", "0", t)
    t = re.sub(r"(?<=\d)[oO](?=\d)", "0", t)
    t = re.sub(r"(?<=[\d,])[lI](?=[\d,])", "1", t)
    t = re.sub(r"(\d)\s+(st|nd|rd|th)\b", r"\1\2", t)    # "5 th" -> "5th"
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t
