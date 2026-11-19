

# ===========================================================================
# SECTION 5B - REPLIES, MATCHING AND RECONCILIATION
# ---------------------------------------------------------------------------
# A confirmation is sent, the party replies, and the reply has to be tied back
# to the right party and the confirmed figure read out of it.  Everything in
# this section is pure logic over plain dictionaries, so it works the same
# whether the reply arrived through the Gmail bridge, was pulled from a shared
# sheet, or was keyed in by hand.
#
# Reply record (one per message received):
#   {id, received_at, from_email, from_name, subject, body, thread_id,
#    in_reply_to, reference, attachments:[{name, text}], bounced}
#
# Match result added by match_reply():
#   {matched_document, match_method, match_confidence, client_run}
# ===========================================================================

REFERENCE_PREFIX = "BCG"
REFERENCE_RE = re.compile(r"\b" + REFERENCE_PREFIX + r"-([0-9A-HJ-NP-Z]{6})\b",
                          re.I)
# I, O, 0 and 1 are left out so a code read off a printed page is unambiguous
_REF_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def new_reference():
    """A short code printed in the subject and in the letter, e.g. BCG-7F3K2A."""
    import random
    return REFERENCE_PREFIX + "-" + "".join(
        random.choice(_REF_ALPHABET) for _ in range(6))


def find_reference(*texts):
    for text in texts:
        found = REFERENCE_RE.search(str(text or ""))
        if found:
            return (REFERENCE_PREFIX + "-" + found.group(1)).upper()
    return ""


def _norm_name(text):
    """Fold a party name for comparison: case, punctuation and the usual
    company suffixes all fall away."""
    value = str(text or "").lower()
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    value = re.sub(r"\b(private|pvt|limited|ltd|llp|inc|co|company|and|&|the)\b",
                   " ", value)
    return re.sub(r"\s+", " ", value).strip()


def name_similarity(a, b):
    """0-100.  A token-set ratio, so word order and extra words do not matter.
    Written out rather than pulled from a library to keep the file standalone."""
    first, second = _norm_name(a), _norm_name(b)
    if not first or not second:
        return 0
    if first == second:
        return 100
    one, two = set(first.split()), set(second.split())
    shared = one & two
    if not shared:
        return 0
    # Jaccard over tokens, lifted when one name is wholly inside the other
    score = 100.0 * len(shared) / len(one | two)
    if one <= two or two <= one:
        score = max(score, 92.0)
    return int(round(score))


MATCH_THREAD = "thread"
MATCH_REFERENCE = "reference"
MATCH_SENDER = "sender address"
MATCH_NAME = "party name"
MATCH_DOMAIN = "sender's domain"
MATCH_MANUAL = "assigned by hand"
MATCH_NONE = "unmatched"

# a reply the auditor has marked as not being a confirmation for any party
SET_ASIDE = "__set_aside__"

NAME_MATCH_THRESHOLD = 90

# A shared mail service says nothing about which company a sender works for,
# so only a company's own domain is used as evidence of who replied.
PUBLIC_MAIL_DOMAINS = frozenset((
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "yahoo.in",
    "ymail.com", "rocketmail.com", "outlook.com", "outlook.in", "hotmail.com",
    "hotmail.co.in", "live.com", "live.in", "msn.com", "icloud.com",
    "me.com", "mac.com", "aol.com", "rediffmail.com", "rediff.com",
    "zoho.com", "zohomail.com", "zohomail.in", "protonmail.com", "proton.me",
    "pm.me", "gmx.com", "gmx.net", "mail.com", "yandex.com", "yandex.ru",
    "tutanota.com", "fastmail.com", "hey.com", "sify.com", "vsnl.net",
    "vsnl.com", "bsnl.in", "airtelmail.in", "indiatimes.com"))

_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_LEGAL_SUFFIX = (r"(?:pvt|private|ltd|limited|llp|inc|co|company|corp|"
                 r"corporation|plc|llc|gmbh|bhd)")
_DROPPED_WORDS = r"(?:and|the|co|company|private|pvt|limited|ltd|llp|inc)"


def addresses_in(text):
    """Every e-mail address in a field, lower-cased.  A party's e-mail cell
    may hold more than one address."""
    return {found.lower().rstrip(".")
            for found in _ADDRESS_RE.findall(str(text or ""))}


def document_key(document):
    return document.get("id") or document.get("filename")


def _party_key(document):
    return _norm_name(document.get("party_name")) or str(document_key(document))


def _message_id(value):
    return str(value or "").strip().strip("<>").strip().lower()


def _fold(text):
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _name_pattern(party_name):
    """A pattern that finds a party's name as a whole phrase.

    'ABC Pvt Ltd' must not be found inside 'ABCD' or in the word 'abc' in
    passing, so a one-word name only counts when a legal suffix follows it
    ('ABC Pvt Ltd', 'ABC Limited').  Longer names count as a phrase."""
    tokens = _norm_name(party_name).split()
    if not tokens:
        return None
    joiner = r"(?:\s+" + _DROPPED_WORDS + r")*\s+"
    phrase = joiner.join(re.escape(token) for token in tokens)
    if len(tokens) == 1:
        phrase += r"(?:\s+" + _DROPPED_WORDS + r")*\s+" + _LEGAL_SUFFIX
    return re.compile(r"\b" + phrase + r"\b")


def parties_named_in(text, documents):
    """{party key: [documents]} for every party whose name is written in the
    text.  Where one name sits inside a longer one ('ABC' within 'ABC
    Exports'), only the longer, more specific name counts."""
    folded = _fold(text)
    if not folded:
        return {}
    spans = {}
    for document in documents:
        pattern = _name_pattern(document.get("party_name"))
        if pattern is None:
            continue
        found = [(m.start(), m.end()) for m in pattern.finditer(folded)]
        if found:
            spans.setdefault(_party_key(document), {"spans": found,
                                                    "documents": []})
            spans[_party_key(document)]["documents"].append(document)
    named = {}
    for key, entry in spans.items():
        inside_longer = all(
            any(other_key != key and o_start <= start and end <= o_end and
                (o_end - o_start) > (end - start)
                for other_key, other in spans.items()
                for o_start, o_end in other["spans"])
            for start, end in entry["spans"])
        if not inside_longer:
            named[key] = entry["documents"]
    return named


def _names_of(documents):
    seen, out = set(), []
    for document in documents:
        name = document.get("party_name") or str(document_key(document))
        if name not in seen:
            seen.add(name)
            out.append(name)
    return ", ".join(out)


def _describe(document):
    category = document.get("category") or ""
    return "%s%s" % (document.get("party_name", ""),
                     " (%s)" % category if category else "")


def assess_reply(reply, documents):
    """Work out which sent confirmation a reply answers, on evidence only.

    Two separate questions are asked of every reply:

      who sent it   - the sender's address registered for a party, the
                      party's name written in the party's OWN words (not in
                      our letter quoted underneath), or a company's own
                      domain;
      what it answers - the request it is a reply to (In-Reply-To or the
                      thread), our reference code, or the returned letter.

    The reply is recorded against a party only when the evidence points to
    exactly one confirmation.  Evidence that disagrees, or no evidence at
    all, sends the reply to the exception queue: it is never given to the
    first party on the list, and the order replies arrive in plays no part.

    Returns {document, method, confidence, basis, note, reason, candidates}.
    """
    result = {"document": None, "method": MATCH_NONE, "confidence": 0.0,
              "basis": "", "note": "", "reason": "", "candidates": ""}
    documents = [d for d in documents if document_key(d)]
    by_key = {document_key(d): d for d in documents}

    # -- the auditor's own decision overrides everything
    assigned = str(reply.get("assigned_to") or "")
    if assigned and assigned != SET_ASIDE:
        document = by_key.get(assigned)
        if document is not None:
            who = str(reply.get("decided_by") or "").strip()
            when = fmt_date_long(str(reply.get("decided_at")
                                     or reply.get("assigned_at") or "")[:10])
            basis = "Accepted%s%s for %s" % (
                " by " + who if who else " by hand",
                " on " + when if when else "", _describe(document))
            if reply.get("decision_note"):
                basis += " - " + str(reply["decision_note"])
            result.update(document=document, method=MATCH_MANUAL,
                          confidence=1.0, basis=basis)
            return result
        result["reason"] = ("Assigned by hand to a confirmation that is no "
                            "longer on record - assign it again")
        return result

    subject = str(reply.get("subject") or "")
    body = str(reply.get("body") or "")
    own_words = strip_quoted(body)
    attachment_texts = [str(a.get("text") or "")
                        for a in (reply.get("attachments") or [])]
    sender = next(iter(sorted(addresses_in(reply.get("from_email")))), "")
    bounced = bool(reply.get("bounced")) or looks_like_bounce(reply)

    # ------------------------------------------------ who sent the reply
    sender_hits = [d for d in documents
                   if sender and sender in addresses_in(d.get("email"))]
    domain_hits = []
    if sender and not sender_hits and not bounced:
        domain = sender.rsplit("@", 1)[-1]
        if domain not in PUBLIC_MAIL_DOMAINS:
            domain_hits = [d for d in documents if any(
                address.rsplit("@", 1)[-1] == domain
                for address in addresses_in(d.get("email")))]
    named = {} if bounced else parties_named_in(
        own_words + "\n" + str(reply.get("from_name") or ""), documents)
    name_hits = [d for docs in named.values() for d in docs]

    identity_signals = []
    if sender_hits:
        identity_signals.append(
            (MATCH_SENDER, {_party_key(d) for d in sender_hits},
             "sent from %s, the address on record for %s"
             % (sender, _names_of(sender_hits))))
    if name_hits:
        identity_signals.append(
            (MATCH_NAME, set(named),
             "the reply names %s in the party's own words"
             % _names_of(name_hits)))
    if domain_hits:
        identity_signals.append(
            (MATCH_DOMAIN, {_party_key(d) for d in domain_hits},
             "sent from the domain %s, used only by %s"
             % (sender.rsplit("@", 1)[-1], _names_of(domain_hits))))

    identity, identity_kind = set(), ""
    if identity_signals:
        identity = set(identity_signals[0][1])
        identity_kind = identity_signals[0][0]
        for _kind, parties, _words in identity_signals[1:]:
            identity &= parties
        if not identity:
            result["reason"] = (
                "The evidence of who replied disagrees: %s - decide which "
                "party this reply belongs to"
                % "; ".join(words for _k, _p, words in identity_signals))
            result["candidates"] = _names_of(
                [d for _k, parties, _w in identity_signals
                 for d in documents if _party_key(d) in parties])
            return result
    identity_words = "; ".join(words for _k, _p, words in identity_signals)

    # ------------------------------------------- which letter it answers
    letter, letter_words = {}, []

    def note_letter(found, kind, words):
        for document in found:
            letter.setdefault(document_key(document), (document, kind))
        if found:
            letter_words.append(words % _names_of(found))

    thread = str(reply.get("thread_id") or "").strip()
    parent = _message_id(reply.get("in_reply_to"))
    by_thread = [d for d in documents
                 if (thread and str(d.get("thread_id") or "") == thread) or
                 (parent and _message_id(d.get("message_id")) == parent)]
    note_letter(by_thread, MATCH_THREAD,
                "it is a reply to the request sent to %s")

    explicit_codes = set()
    for text in [subject, own_words] + attachment_texts:
        explicit_codes |= {(REFERENCE_PREFIX + "-" + m).upper()
                           for m in REFERENCE_RE.findall(text)}
    by_code = [d for d in documents
               if str(d.get("reference") or "").upper() in explicit_codes]
    note_letter(by_code, MATCH_REFERENCE,
                "it carries the reference code of the letter to %s")

    strong_letter = dict(letter)
    if not strong_letter:
        # weaker: a code only in the quoted text, the party named on the
        # returned letter, or the failed address inside a bounce
        quoted_codes = {(REFERENCE_PREFIX + "-" + m).upper()
                        for m in REFERENCE_RE.findall(body)}
        if reply.get("reference"):
            quoted_codes.add(str(reply["reference"]).upper())
        by_quoted = [d for d in documents
                     if str(d.get("reference") or "").upper() in quoted_codes]
        note_letter(by_quoted, MATCH_REFERENCE,
                    "the letter to %s is quoted in it")
        on_letter = parties_named_in("\n".join(attachment_texts), documents)
        if len(on_letter) == 1:
            note_letter(list(on_letter.values())[0], MATCH_NAME,
                        "the returned letter is addressed to %s")
        if bounced:
            failed = addresses_in(body)
            note_letter([d for d in documents
                         if addresses_in(d.get("email")) & failed],
                        MATCH_THREAD, "the failed address is the one for %s")

    def choose(document, method, confidence, basis, note=""):
        result.update(document=document, method=method,
                      confidence=confidence, basis=basis, note=note)
        return result

    def basis_of(*parts):
        text = "; ".join(p for p in parts if p)
        return text[:1].upper() + text[1:]

    letter_text = "; ".join(letter_words)

    if identity:
        candidates = [d for d in documents if _party_key(d) in identity]
        if letter:
            within = [d for d in candidates if document_key(d) in letter]
            if len(within) == 1:
                document = within[0]
                method = letter[document_key(document)][1]
                if method == MATCH_NAME:
                    method = identity_kind
                return choose(document, method, 0.97,
                              basis_of(identity_words, letter_text))
            if len(within) > 1:
                result["reason"] = (
                    "The reply could answer more than one confirmation for "
                    "%s (%s) - decide which" % (_names_of(within), ", ".join(
                        d.get("category", "") for d in within)))
                result["candidates"] = "; ".join(_describe(d) for d in within)
                return result
            # who replied and what they replied to point to different parties
            others = [entry[0] for entry in letter.values()]
            parties_in_identity = {_party_key(d) for d in candidates}
            # The sender's own registered address is the one thing that says
            # who is speaking; a reply-all on another party's request says
            # only which e-mail they pressed Reply on.
            if identity_kind == MATCH_SENDER and len(candidates) == 1 and \
                    len(parties_in_identity) == 1:
                document = candidates[0]
                return choose(
                    document, MATCH_SENDER, 0.80,
                    basis_of(identity_words, letter_text),
                    note=("Sent from the address on record for %s, but as a "
                          "reply to the request sent to %s; recorded against "
                          "%s - confirm before relying on it"
                          % (document.get("party_name", ""),
                             _names_of(others),
                             document.get("party_name", ""))))
            result["reason"] = ("Who replied (%s) and what the reply answers "
                                "(%s) point to different parties - decide "
                                "which" % (identity_words, letter_text))
            result["candidates"] = _names_of(candidates + others)
            return result
        if len(candidates) == 1:
            confidence = {MATCH_SENDER: 0.92, MATCH_NAME: 0.75,
                          MATCH_DOMAIN: 0.72}.get(identity_kind, 0.7)
            return choose(candidates[0], identity_kind, confidence,
                          basis_of(identity_words))
        if len({_party_key(d) for d in candidates}) == 1:
            result["reason"] = (
                "%s has %d confirmations (%s) and the reply does not show "
                "which one it answers" % (
                    candidates[0].get("party_name", ""), len(candidates),
                    ", ".join(d.get("category", "") for d in candidates)))
        else:
            result["reason"] = ("The reply could be from more than one party "
                                "(%s) - decide which" % identity_words)
        result["candidates"] = "; ".join(_describe(d) for d in candidates)
        return result

    if len(letter) == 1:
        document, kind = list(letter.values())[0]
        confidence = 0.95 if strong_letter else 0.80
        if kind == MATCH_NAME:
            confidence = 0.70
        return choose(document, kind, confidence, basis_of(letter_text))
    if len(letter) > 1:
        result["reason"] = ("The reply points to more than one letter (%s) "
                            "- decide which" % letter_text)
        result["candidates"] = "; ".join(
            _describe(entry[0]) for entry in letter.values())
        return result

    result["reason"] = (
        "Nothing in the reply shows which party sent it: the sender's "
        "address is not on the party list, it is not a reply to one of the "
        "requests sent, and it carries no reference code or party name")
    return result


def match_reply(reply, documents):
    """Tie one reply to one sent confirmation.

    Returns (document or None, method, confidence 0-1).  See assess_reply
    for the evidence used and for why a reply may be left unmatched."""
    found = assess_reply(reply, documents)
    return found["document"], found["method"], found["confidence"]


# ------------------------------------------------------- reading the figure
# The slip the party completes reads:
#   "We hereby confirm that the amount payable by us to <client> as on
#    <date> is <CCY> ______________"
# and the letter above it STATES the client's own figure ("According to our
# records, the amount due from you ... is INR 35,00,000.00").  So a figure
# equal to the books proves nothing by itself: it may simply be our own
# letter coming back.  Every figure in the reply is therefore collected, and
# one that differs from the books always outranks an echo of the figure sent.
_CCY = r"(?:INR|USD|EUR|GBP|AED|SGD|AUD|CAD|JPY|CHF|Rs\.?|₹|\$|€|£)"
_FIGURE_RE = re.compile(
    r"(?P<ccy>" + _CCY + r")?[ \t]*"
    r"(?P<num>\(?-?\d(?:[\d,.]*\d)?\)?)"
    r"(?P<scale>[ \t]*(?:lakhs?|lacs?|crores?|millions?|thousands?)\b)?",
    re.I)
_SCALES = {"lakh": 1e5, "lac": 1e5, "crore": 1e7, "million": 1e6,
           "thousand": 1e3}
_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
           "oct", "nov", "dec")
_KEYWORDS = ("balance", "amount", "outstanding", "payable", "receivable",
             "our books", "our records", "our ledger", "confirm", "advance",
             "due ")
_CONNECTOR_RE = re.compile(
    r"(?:\bis\b|\bof\b|\bbeing\b|\bwas\b|\bas\b|\bto be\b|\bshows?\b|"
    r"\bstands at\b|\bcomes to\b|[:=\-–])\s*$", re.I)
_SLIP_BEFORE_RE = re.compile(r"we\s+hereby\s+confirm[\s\S]{0,240}$", re.I)

# "as per our books" is deliberately absent: it introduces the party's own
# figure as often as it signals agreement
AGREE_WORDS = ["agree", "agreed", "in agreement", "confirmed", "confirm the "
               "balance", "tally", "tallies", "matches", "is correct"]
DISAGREE_WORDS = ["not in agreement", "do not agree", "does not agree",
                  "don't agree", "disagree", "difference", "differs",
                  "mismatch", "not tally", "does not tally", "discrepancy",
                  "not correct", "incorrect", "not matching", "does not match",
                  "do not match"]

BOUNCE_MARKERS = ["mailer-daemon", "postmaster", "delivery status "
                  "notification", "undeliverable", "address not found",
                  "delivery has failed", "returned to sender"]


def looks_like_bounce(reply):
    blob = " ".join([str(reply.get("from_email") or ""),
                     str(reply.get("from_name") or ""),
                     str(reply.get("subject") or ""),
                     str(reply.get("body") or "")]).lower()
    return any(marker in blob for marker in BOUNCE_MARKERS)


def strip_quoted(text):
    """The party's own words: the reply with the quoted original removed.

    A reply normally carries our covering e-mail underneath it, and that
    e-mail states the client's figure.  Read as the party's words, it would
    'confirm' the balance on its own."""
    text = str(text or "").replace("\r\n", "\n")
    cut = re.search(r"^[ \t>]*On\b[^\n]{0,240}(?:\n[^\n]{0,120})?\bwrote:[ \t]*$",
                    text, re.I | re.M)
    if cut:
        text = text[:cut.start()]
    kept = []
    for line in text.split("\n"):
        bare = line.strip()
        if bare.startswith(">"):
            continue
        if re.match(r"^-{2,}\s*(original|forwarded) message\s*-{2,}", bare,
                    re.I):
            break
        if re.match(r"^_{10,}$", bare):                    # Outlook divider
            break
        if kept and re.match(r"^from:\s.+", bare, re.I):   # Outlook header
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _alone_on_line(blob, match):
    """True when a figure is all there is on its line (bar 'Rs', '/-',
    'only' and punctuation)."""
    line_start = blob.rfind("\n", 0, match.start()) + 1
    line_end = blob.find("\n", match.end())
    line = blob[line_start:line_end if line_end >= 0 else len(blob)]
    rest = line.replace(match.group(0), " ", 1)
    rest = re.sub(r"(?i)\b(rs|inr|only|rupees)\b|[\s./\-:=*₹]", "", rest)
    return rest == ""


_WELL_FORMED_RE = re.compile(
    r"^\(?-?(?:\d{1,2}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d{1,2})?\)?$")


def _doubtful_reading(blob, start, end, raw, digits, scale):
    """True when OCR has plainly not read a figure whole.

    Handwriting comes back broken - '25, 00,0.00' for 25,00,000 - and the
    first fragment on its own would be recorded as 25.  A figure is trusted
    only if it is grouped like one and nothing figure-like hangs off it."""
    if not _WELL_FORMED_RE.match(raw):
        return True
    if re.match(r"^\s*[,.]\s*\d|^\s+\d", blob[end:end + 6]):
        return True                       # more digits follow after a gap
    if re.search(r"\d\s*[,.]\s+$|\d\s+[,.]\s*$", blob[max(0, start - 4):start]):
        return True                       # it is the tail of a broken figure
    if len(digits) < 4 and not scale:
        return True                       # '25' is not a balance
    return False


def find_figures(text, source, strict=False):
    """Every monetary figure in a piece of text, with how it was recognised.

    Returns [{amount, currency, confidence, source, kind, note}].  A bare
    number is only accepted where the wording around it says it is a balance;
    dates, pincodes and telephone numbers are left alone."""
    blob = re.sub(r"[ \t]+", " ", str(text or ""))
    found = []
    for match in _FIGURE_RE.finditer(blob):
        raw = match.group("num")
        start, end = match.start("num"), match.end("num")
        lead = blob[max(0, match.start() - 260):match.start()]
        after = blob[end:end + 14].lower()
        symbol = (match.group("ccy") or "").strip()
        scale = (match.group("scale") or "").strip().lower()
        digits = re.sub(r"\D", "", raw)

        # --- things that are not money
        if re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$", raw):   # 31.03.2026
            continue
        if not symbol and start > 1 and blob[start - 1] in "/-.@#" and \
                blob[start - 2].isalnum():                        # 31/03, BCG-7
            continue
        # "25,00,000/-" is how a rupee figure is commonly written, so a
        # trailing "/-" is money; any other slash is a date or a fraction
        if (after[:1] == "/" and not after.startswith("/-")) or \
                after[:1] in ("%", "@") or re.match(r"^-\d", after):
            continue
        if after.strip()[:3] in _MONTHS and len(digits) <= 2:     # 31 March
            continue
        if lead.rstrip().lower()[-3:] in _MONTHS or re.search(
                r"(january|february|march|april|june|july|august|september|"
                r"october|november|december)\s*,?\s*$", lead, re.I):
            if len(digits) <= 4 and "," not in raw:               # March 2026
                continue
        if not symbol and start and blob[start - 1].isalpha():    # ABC123
            continue
        if not symbol and re.match(r"^[a-z]", after):             # 10th road
            continue

        if not symbol and "," not in raw and re.match(r"^[6-9]\d{9}$", raw):
            continue                                              # a mobile

        grouped = bool(re.match(r"^\(?-?\d{1,3}(,\d{2,3})+(\.\d+)?\)?$", raw))
        marked = bool(symbol) or grouped or bool(scale)
        nearby = lead[-90:].lower()

        if _SLIP_BEFORE_RE.search(lead) and \
                re.search(r"\bis\b[\s:]*$", lead):
            kind, confidence = "slip", 0.95
        elif any(word in nearby for word in _KEYWORDS) and (
                marked or (5 <= len(digits) <= 12 and
                           _CONNECTOR_RE.search(lead[-40:]))):
            kind, confidence = "statement", 0.80
        elif symbol and (grouped or scale or len(digits) >= 4):
            kind, confidence = "figure", 0.60
        elif grouped and len(digits) >= 5 and _alone_on_line(blob, match):
            # a reply that is nothing but a figure: weak, but it is the
            # party's own, and a differing one must not be lost
            kind, confidence = "figure", 0.55
        else:
            continue

        value, currency_from_text, note = parse_amount(raw)
        if value is None:
            continue
        for word, factor in _SCALES.items():
            if scale.startswith(word):
                value *= factor
                break
        found.append({
            "amount": value,
            "currency": (currency_from_text or _CURRENCY_FROM_SYMBOL.get(
                symbol.upper().rstrip("."), "")),
            "confidence": confidence, "source": source, "kind": kind,
            "note": note or "",
            "doubtful": bool(strict and _doubtful_reading(
                blob, start, end, raw, digits, scale)),
            "seen": blob[start:end + 12].split("\n")[0].strip(),
        })
    return found


def extract_confirmation(reply, books=None, tolerance=1.0):
    """Read the confirmed figure and the party's stance out of a reply.

    books is the figure our letter carried.  When it is known, a figure in
    the reply that DIFFERS from it is the party's own and always wins; a
    figure that merely repeats it counts as agreement only if the party has
    not said otherwise.

    Returns {amount, currency, confidence, source, stance, confirmed_on,
             signed, note}.  A None amount means nothing could be relied on,
            which sends the reply to the exception queue rather than guessing.
    """
    result = {"amount": None, "currency": "", "confidence": 0.0,
              "source": "", "stance": "", "confirmed_on": "",
              "signed": False, "note": "", "method": ""}

    if reply.get("accepted_amount") is not None:
        # the reviewer read the reply and accepted this figure: it is used
        # exactly, and the trail says who accepted it
        result.update(amount=float(reply["accepted_amount"]), confidence=1.0,
                      source="accepted by %s" % (reply.get("decided_by")
                                                 or "the reviewer"),
                      method="accepted by hand")
        return result

    own_words = strip_quoted(reply.get("body", ""))
    candidates = []
    # the attachment is the signed slip, so it is read before the covering note
    for attachment in (reply.get("attachments") or []):
        by_ocr = "OCR" in str(attachment.get("method") or "")
        for figure in find_figures(attachment.get("text", ""),
                                   attachment.get("name", "attachment"),
                                   strict=by_ocr):
            figure["method"] = attachment.get("method", "")
            candidates.append(figure)
    candidates += find_figures(own_words, "email body")

    # A figure OCR could not read whole is never used.  Nor is one that is
    # out of all proportion to the balance asked about: that is a misread
    # digit or a telephone number, not a confirmation.
    for figure in candidates:
        if "OCR" in str(figure.get("method") or "") and books and \
                not figure["doubtful"]:
            ratio = abs(figure["amount"]) / abs(books)
            if ratio < 0.01 or ratio > 100:
                figure["doubtful"] = True
    doubtful = [c for c in candidates if c.get("doubtful")]
    candidates = [c for c in candidates if not c.get("doubtful")]

    lowered = own_words.lower()
    if any(word in lowered for word in DISAGREE_WORDS):
        result["stance"] = "not in agreement"
    elif any(word in lowered for word in AGREE_WORDS):
        result["stance"] = "agreed"

    chosen = None
    if candidates and books is not None:
        differing = [c for c in candidates
                     if abs(c["amount"] - books) > tolerance]
        if differing:
            # the party's own covering words outrank a figure on a document,
            # because the document may carry our pre-printed amount as well
            differing.sort(key=lambda c: (c["source"] == "email body",
                                          c["confidence"]), reverse=True)
            chosen = dict(differing[0])
            chosen["note"] = "Party states a figure different from the letter"
        elif result["stance"] == "not in agreement":
            result["note"] = ("Party says the balance is not in agreement but "
                              "gives no figure of its own")
        else:
            # Every figure found equals the books.  That is the party's own
            # confirmation only if it sits on the completed slip or in the
            # party's own words; the same figure in the body of the returned
            # letter is merely our own statement coming back.
            own = [c for c in candidates
                   if c["kind"] == "slip" or c["source"] == "email body"]
            if own:
                chosen = max(own, key=lambda c: c["confidence"])
            elif result["stance"] == "agreed":
                chosen = dict(max(candidates, key=lambda c: c["confidence"]))
                chosen["confidence"] = min(chosen["confidence"], 0.70)
                chosen["note"] = ("Party's covering words agree; the figure "
                                  "is the one stated in the letter")
            else:
                result["note"] = ("The letter came back, but the figure the "
                                  "party entered on the slip could not be "
                                  "read - open the reply")
    elif candidates:
        chosen = max(candidates, key=lambda c: c["confidence"])

    # The slip holds something OCR could not make out.  Unless the party has
    # stated its figure in its own words, that is for a person to read.
    unread_slip = [c for c in doubtful if c["kind"] == "slip"]
    if doubtful and (chosen is None or
                     (unread_slip and chosen["source"] != "email body")):
        seen = (unread_slip or doubtful)[0]
        chosen = None
        result["note"] = ("A figure is written on %s but could not be read "
                          "with certainty (OCR saw \"%s\") - open the "
                          "document" % (seen["source"], seen["seen"]))

    if chosen:
        result["method"] = chosen.get("method", "")
        result.update({"amount": chosen["amount"],
                       "currency": chosen["currency"],
                       "confidence": chosen["confidence"],
                       "source": chosen["source"],
                       "note": chosen.get("note", "")})
        if result["stance"] == "not in agreement":
            result["confidence"] = max(0.0, result["confidence"] - 0.05)

    blob = " ".join([str(reply.get("body") or "")] +
                    [str(a.get("text") or "")
                     for a in (reply.get("attachments") or [])]).lower()
    found_date = re.search(r"as on\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4}"
                           r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", blob, re.I)
    if found_date:
        result["confirmed_on"] = iso_date(found_date.group(1))

    if re.search(r"\b(signed|signature|authorised signatory|"
                 r"authorized signatory|stamp|seal)\b", blob):
        result["signed"] = True
        if result["amount"] is not None:
            result["confidence"] = min(1.0, result["confidence"] + 0.02)

    return result


def is_own_request(reply, documents, own_addresses=()):
    """True when a 'reply' is really our own outgoing request.

    The request is copied to the engagement team, so it lands in the very
    mailbox the bridge reads - carrying a letter that states the client's own
    figure.  Counted as a reply it would 'agree' every balance by itself."""
    if reply.get("own_request"):
        return True
    message_id = str(reply.get("message_id") or "").strip()
    if message_id and any(str(d.get("message_id") or "").strip() == message_id
                          for d in documents):
        return True
    sender = str(reply.get("from_email") or "").strip().lower()
    own = {str(a or "").strip().lower() for a in own_addresses if a}
    if sender and sender in own:
        subject = str(reply.get("subject") or "").strip().lower()
        answered = bool(str(reply.get("in_reply_to") or "").strip()) or \
            bool(re.match(r"^(re|fw|fwd)\s*:", subject))
        if not answered:
            return True
    return False


_CURRENCY_FROM_SYMBOL = {"RS": "INR", "₹": "INR", "$": "USD",
                         "€": "EUR", "£": "GBP", "INR": "INR",
                         "USD": "USD", "EUR": "EUR", "GBP": "GBP",
                         "AED": "AED", "SGD": "SGD", "AUD": "AUD",
                         "CAD": "CAD", "JPY": "JPY", "CHF": "CHF"}


# -------------------------------------------------------- reconciliation
STATUS_AGREED = "Matched"
STATUS_VARIANCE = "Mismatch"
STATUS_PENDING = "Pending"
STATUS_RETURNED = "Returned"
STATUS_REVIEW = "Needs Review"
STATUS_NOT_SENT = "Not sent"

STATUS_ORDER = [STATUS_VARIANCE, STATUS_REVIEW, STATUS_RETURNED,
                STATUS_PENDING, STATUS_AGREED, STATUS_NOT_SENT]

DEFAULT_TOLERANCE = 1.0          # INR; a rounding difference is not a variance
DEFAULT_REMINDERS = (15, 30, 45)  # days after sending


def days_between(earlier, later=None):
    start = to_date(earlier)
    if not start:
        return None
    end = to_date(later) if later else date.today()
    return (end - start).days


def reminder_stage(age_days, stages=DEFAULT_REMINDERS):
    """Which reminder is due for a confirmation this old (0 = none yet)."""
    if age_days is None:
        return 0
    due = 0
    for index, threshold in enumerate(sorted(stages), start=1):
        if age_days >= threshold:
            due = index
    return due


def reconcile(document, reply=None, tolerance=DEFAULT_TOLERANCE,
              reminders=DEFAULT_REMINDERS, today=None):
    """Compare one sent confirmation with the reply received for it.

    The sign convention is already handled by the letter wording: whatever the
    category, the party confirms the same balance the client has recorded, so
    the two figures are compared directly and never reversed.
    """
    books = document.get("amount")
    currency = document.get("currency") or ""
    sent_on = document.get("sent_at") or document.get("generated_at")
    age = days_between(sent_on, today)

    row = {
        "document_id": document.get("id") or document.get("filename"),
        "party_name": document.get("party_name", ""),
        "category": document.get("category", ""),
        "email": document.get("email", ""),
        "reference": document.get("reference", ""),
        "filename": document.get("filename", ""),
        "currency": currency,
        "books_amount": books,
        "confirmed_amount": None,
        "variance": None,
        "variance_pct": None,
        "status": STATUS_PENDING,
        "delivery": str(document.get("email_status") or "not sent"),
        "sent_at": sent_on or "",
        "received_at": "",
        "age_days": age,
        "reminder_stage": 0,
        "match_method": "",
        "match_confidence": 0.0,
        "extract_confidence": 0.0,
        "extract_source": "",
        "stance": "",
        "signed": False,
        "message_link": "",
        "note": "",
        # the trail from request to recorded figure, kept on every row
        "reply_id": "",
        "reply_from": "",
        "reply_subject": "",
        "match_basis": "",
        "replies_count": 0,
        "reply_ids": "",
        "reply_name": "",
        "decided_by": "",
        "decided_at": "",
        "decision_note": "",
    }

    delivery = str(document.get("email_status") or "").lower()
    if delivery in ("", "not sent"):
        row["status"] = STATUS_NOT_SENT
        row["note"] = "Letter produced but not e-mailed"
        return row
    if delivery == "failed":
        row["status"] = STATUS_RETURNED
        row["note"] = "Delivery failed"
        return row

    if reply is None:
        row["reminder_stage"] = reminder_stage(age, reminders)
        return row

    row["received_at"] = reply.get("received_at", "")
    row["match_method"] = reply.get("match_method", "")
    row["match_confidence"] = reply.get("match_confidence", 0.0)
    row["message_link"] = reply.get("message_link", "")
    row["reply_id"] = reply.get("id", "")
    row["reply_from"] = reply.get("from_email", "")
    row["reply_subject"] = reply.get("subject", "")
    row["match_basis"] = reply.get("match_basis", "")
    row["reply_name"] = reply.get("from_name", "")
    row["decided_by"] = reply.get("decided_by", "")
    row["decided_at"] = reply.get("decided_at", "")
    row["decision_note"] = reply.get("decision_note", "")

    if reply.get("bounced") or looks_like_bounce(reply):
        row["status"] = STATUS_RETURNED
        row["note"] = "Mail returned undelivered"
        return row

    # always read against the figure our letter carried: the letter coming
    # back must not be mistaken for the party's own confirmation
    extraction = extract_confirmation(reply, books, tolerance)
    row["extract_confidence"] = extraction.get("confidence", 0.0)
    row["extract_source"] = extraction.get("source", "")
    row["stance"] = extraction.get("stance", "")
    row["signed"] = extraction.get("signed", False)
    if extraction.get("currency"):
        row["currency"] = extraction["currency"]

    confirmed = extraction.get("amount")
    if confirmed is None:
        row["status"] = STATUS_REVIEW
        row["note"] = extraction.get("note") or \
            "Reply received but no amount could be read"
        if reply.get("files_error"):
            row["note"] += " - attachment not read: " + \
                str(reply["files_error"])[:160]
        elif reply_has_unread_files(reply):
            row["note"] += " - it has a PDF or scan that has not been read " \
                           "yet (Read attached PDFs)"
        return row

    row["confirmed_amount"] = confirmed
    if books is None:
        row["status"] = STATUS_REVIEW
        row["note"] = "No balance on record to compare with"
        return row

    variance = confirmed - books
    row["variance"] = variance
    row["variance_pct"] = (abs(variance) / abs(books) * 100.0) if books else None
    if abs(variance) <= tolerance:
        row["status"] = STATUS_AGREED
        row["note"] = "Agrees with the books"
    else:
        row["status"] = STATUS_VARIANCE
        row["note"] = "Party confirms %s the books by %s" % (
            "less than" if variance < 0 else "more than",
            fmt_amount(abs(variance), row["currency"]) or abs(variance))
    if "OCR" in str(extraction.get("method") or ""):
        # how the figure was obtained travels with it into every report
        row["note"] += " (read by OCR from %s - check against the document)" \
            % (row["extract_source"] or "the attachment")
    if reply.get("match_note"):
        row["note"] += ". " + reply["match_note"]
    return row


EXCEPTION_UNMATCHED = "unmatched"      # no party could be identified
EXCEPTION_CONFLICT = "conflict"        # replies for one party disagree
EXCEPTION_UNREADABLE = "unreadable"    # matched, but no figure to rely on
EXCEPTION_LEFTOVER = "leftover"        # undecided after another was accepted


def _exception(reason, reply, extraction=None, candidates="",
               party="", kind=EXCEPTION_UNMATCHED, document=None):
    extraction = extraction or {}
    return {
        "kind": kind,
        "reason": reason,
        "from_email": reply.get("from_email", ""),
        "from_name": reply.get("from_name", ""),
        "subject": reply.get("subject", ""),
        "received_at": reply.get("received_at", ""),
        "amount": extraction.get("amount"),
        "currency": extraction.get("currency", ""),
        "confidence": extraction.get("confidence", 0.0),
        "candidates": candidates,
        "party": party,
        "document_id": document_key(document) if document else "",
        "evidence": reply.get("match_basis", ""),
        "reply_id": reply.get("id", ""),
        "message_link": reply.get("message_link", ""),
        "suggested_to": "",
        "suggestion": "",
        "review": "Review",
    }


def suggest_party(entry, documents, tolerance=DEFAULT_TOLERANCE):
    """A match to OFFER the reviewer - never applied without them.

    Returns (document id or "", reason).  The requested balance is itself a
    detail of the request: a reply whose figure is exactly the balance asked
    of one party, and of no other, most likely answers that request."""
    amount = entry.get("amount")
    if amount is not None:
        same = [d for d in documents if d.get("amount") is not None and
                abs(abs(d["amount"]) - abs(amount)) <= tolerance]
        if len(same) == 1:
            return document_key(same[0]), (
                "the figure in the reply equals the balance requested from "
                "%s" % same[0].get("party_name", ""))
    if entry.get("kind") == EXCEPTION_UNREADABLE and entry.get("document_id"):
        return entry["document_id"], (
            "it was matched to %s; only the figure needs your reading"
            % entry.get("party", ""))
    return "", ""


def _arrival(reply):
    return (str(reply.get("received_at") or ""), str(reply.get("id") or ""))


def settle_replies(matched, tolerance=DEFAULT_TOLERANCE):
    """Choose the reply that stands for one confirmation.

    Returns (reply or None, conflict, leftover).

    conflict is a sentence when the replies matched to the party give
    different figures: that is for the reviewer to decide, so neither figure
    is used.  A later reply never silently replaces an earlier one.

    leftover lists replies matched automatically whose figure differs from
    the one the reviewer accepted: they stay in the exception queue until
    each is given to another party or set aside."""
    if not matched:
        return None, "", []
    by_hand = [r for r in matched if r.get("match_method") == MATCH_MANUAL]
    pool = by_hand or list(matched)
    answers = [r for r in pool
               if not (r.get("bounced") or looks_like_bounce(r))]
    if not answers:
        return max(pool, key=_arrival), "", []
    readable = [r for r in answers
                if (r.get("extraction") or {}).get("amount") is not None]
    if not readable:
        return max(answers, key=_arrival), "", []
    first = readable[0]["extraction"]["amount"]
    if all(abs(r["extraction"]["amount"] - first) <= tolerance
           for r in readable):
        chosen = max(readable, key=_arrival)
        leftover = []
        if by_hand:
            leftover = [
                r for r in matched
                if r.get("match_method") != MATCH_MANUAL
                and not (r.get("bounced") or looks_like_bounce(r))
                and (r.get("extraction") or {}).get("amount") is not None
                and abs(r["extraction"]["amount"] - first) > tolerance]
        return chosen, "", sorted(leftover, key=_arrival)
    readable.sort(key=_arrival)
    parts = ["%s on %s from %s" % (
        fmt_amount(r["extraction"]["amount"],
                   r["extraction"].get("currency") or "INR")
        or r["extraction"]["amount"],
        fmt_date_long(str(r.get("received_at") or "")[:10])
        or r.get("received_at") or "an unknown date",
        r.get("from_email") or "an unknown sender") for r in readable]
    return max(readable, key=_arrival), (
        "%d replies matched to this party give different figures (%s) - "
        "decide which one counts" % (len(readable), "; ".join(parts))), []


def build_reconciliation(documents, replies, tolerance=DEFAULT_TOLERANCE,
                         reminders=DEFAULT_REMINDERS, today=None,
                         own_addresses=(), ignored=None, set_aside=None):
    """Match every reply, then reconcile every sent confirmation.

    Returns (rows, exceptions).  Exceptions are replies that could not be tied
    to a party on the evidence, replies whose evidence disagrees, replies
    that disagree with one another, and replies whose figure could not be
    read - they are never folded into the numbers silently.
    """
    by_document, exceptions = {}, []

    for reply in replies:
        if is_own_request(reply, documents, own_addresses):
            if ignored is not None:          # our own letter, not an answer
                ignored.append(reply)
            continue
        if reply.get("assigned_to") == SET_ASIDE:
            if set_aside is not None:        # the reviewer said: not a reply
                set_aside.append(reply)
            continue
        found = assess_reply(reply, documents)
        document = found["document"]
        enriched = dict(reply)
        enriched["match_method"] = found["method"]
        enriched["match_confidence"] = found["confidence"]
        enriched["match_basis"] = found["basis"]
        enriched["match_note"] = found["note"]
        enriched["extraction"] = extract_confirmation(
            reply, document.get("amount") if document else None, tolerance)
        if document is None:
            exceptions.append(_exception(
                found["reason"] or "Sender could not be matched to a party",
                enriched, enriched["extraction"], found["candidates"]))
            continue
        by_document.setdefault(document_key(document), []).append(enriched)

    rows = []
    for document in documents:
        key = document_key(document)
        matched = by_document.get(key, [])
        chosen, conflict, leftover = settle_replies(matched, tolerance)
        row = reconcile(document, chosen, tolerance, reminders, today)
        row["replies_count"] = len(matched)
        row["reply_ids"] = ", ".join(str(r.get("id") or "")
                                     for r in sorted(matched, key=_arrival))
        rows.append(row)
        if conflict:
            row.update(status=STATUS_REVIEW, confirmed_amount=None,
                       variance=None, variance_pct=None, note=conflict,
                       extract_confidence=0.0, extract_source="")
            for reply in sorted(matched, key=_arrival):
                exceptions.append(_exception(
                    "Replies matched to %s disagree - decide which one "
                    "counts" % row["party_name"], reply,
                    reply.get("extraction"), row["party_name"],
                    row["party_name"], EXCEPTION_CONFLICT, document))
        elif row["status"] == STATUS_REVIEW and chosen:
            exceptions.append(_exception(
                row["note"] or STATUS_REVIEW, chosen,
                {"amount": chosen.get("extraction", {}).get("amount"),
                 "currency": row["currency"],
                 "confidence": chosen.get("extraction", {}).get(
                     "confidence", 0.0)},
                row["party_name"], row["party_name"],
                EXCEPTION_UNREADABLE, document))
        for reply in leftover:
            exceptions.append(_exception(
                "The confirmation for %s has been accepted from another "
                "reply (%s). This reply gives a different figure and is "
                "still undecided - give it to the party it belongs to, or "
                "set it aside" % (
                    row["party_name"],
                    fmt_amount(row["confirmed_amount"], row["currency"])
                    or row["confirmed_amount"]),
                reply, reply.get("extraction"), "", "",
                EXCEPTION_LEFTOVER, document))

    names = {document_key(d): d.get("party_name", "") for d in documents}
    for entry in exceptions:
        entry["suggested_to"], entry["suggestion"] = suggest_party(
            entry, documents, tolerance)
        entry["suggested_party"] = names.get(entry["suggested_to"], "")

    rows.sort(key=lambda r: (STATUS_ORDER.index(r["status"])
                             if r["status"] in STATUS_ORDER else 99,
                             r["party_name"].lower()))
    return rows, exceptions


# ------------------------------------------------- received date, as local
_STAMP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?"
    r"\s*(Z|[+-]\d{2}:?\d{2})$")


def local_stamp(value):
    """A received date as the reviewer's own calendar shows it.

    The bridge's spreadsheet keeps the date as a date cell, and Google
    hands that back as an instant in universal time: midnight on 10
    November in India arrives as '2026-11-09T18:30:00.000Z'.  Reading the
    first ten characters of that shows the day before.  Such a value is
    converted to local time; anything else is returned as it came."""
    text = str(value or "").strip()
    match = _STAMP_RE.match(text)
    if not match:
        return text
    try:
        zone = match.group(3)
        zone = "+00:00" if zone == "Z" else (
            zone if ":" in zone else zone[:3] + ":" + zone[3:])
        instant = datetime.fromisoformat(
            "%sT%s:00%s" % (match.group(1), match.group(2), zone))
        local = instant.astimezone()
    except Exception:
        return text
    if local.hour == 0 and local.minute == 0:
        return local.strftime("%Y-%m-%d")
    return local.strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------- audit-status records
# One record per confirmation that needs following up.  It ties together the
# party, the request that was sent and the reply that came back, and holds
# what the audit team did about the difference.
AUDIT_STATES = ["Open", "Under follow-up", "Explained - no adjustment",
                "Adjustment proposed", "Alternative procedures performed",
                "Closed"]
AUDIT_OPEN_STATES = ("Open", "Under follow-up")
AUDIT_NATURES = ["Not yet determined",
                 "Timing difference - payment in transit",
                 "Timing difference - goods or invoice in transit",
                 "Disputed item", "Error in the client's books",
                 "Error in the party's books",
                 "Reply could not be matched or read", "Other"]


def needs_audit_status(row):
    return row.get("status") in (STATUS_VARIANCE, STATUS_REVIEW)


def audit_record_for(records, document_id):
    for record in records or []:
        if record.get("document_id") == document_id:
            return record
    return None


def audit_snapshot(row):
    """What a record takes from the reconciliation at the moment it is
    saved: the request, the reply and the figures it is following up."""
    return {
        "document_id": row.get("document_id", ""),
        "party_name": row.get("party_name", ""),
        "category": row.get("category", ""),
        "reference": row.get("reference", ""),
        "request_sent_at": row.get("sent_at", ""),
        "request_email": row.get("email", ""),
        "currency": row.get("currency", ""),
        "books_amount": row.get("books_amount"),
        "confirmed_amount": row.get("confirmed_amount"),
        "variance": row.get("variance"),
        "confirmation_status": row.get("status", ""),
        "reply_id": row.get("reply_id", ""),
        "reply_ids": row.get("reply_ids", ""),
        "reply_from": row.get("reply_from", ""),
        "reply_received_at": row.get("received_at", ""),
        "message_link": row.get("message_link", ""),
    }


def attach_audit_status(rows, records):
    """Put each row's follow-up position on the row, for every report."""
    for row in rows:
        record = audit_record_for(records, row.get("document_id"))
        if record:
            row["audit_state"] = record.get("state", "Open")
            row["audit_state_link"] = "Open record: %s" % row["audit_state"]
        elif needs_audit_status(row):
            row["audit_state"] = "Not yet recorded"
            row["audit_state_link"] = "Create record"
        else:
            row["audit_state"] = ""
            row["audit_state_link"] = ""
    return rows


def summarise(rows):
    """Headline figures for the dashboard and the variance report."""
    def total(selector):
        return sum(abs(r["books_amount"]) for r in rows
                   if selector(r) and r["books_amount"] is not None)

    received = [r for r in rows if r["status"] in
                (STATUS_AGREED, STATUS_VARIANCE)]
    requested_value = total(lambda r: r["status"] != STATUS_NOT_SENT)
    confirmed_value = sum(abs(r["books_amount"]) for r in received
                          if r["books_amount"] is not None)
    return {
        "sent": len([r for r in rows if r["status"] != STATUS_NOT_SENT]),
        "received": len(received),
        "agreed": len([r for r in rows if r["status"] == STATUS_AGREED]),
        "variance": len([r for r in rows if r["status"] == STATUS_VARIANCE]),
        "pending": len([r for r in rows if r["status"] == STATUS_PENDING]),
        "returned": len([r for r in rows if r["status"] == STATUS_RETURNED]),
        "review": len([r for r in rows if r["status"] == STATUS_REVIEW]),
        "not_sent": len([r for r in rows if r["status"] == STATUS_NOT_SENT]),
        "requested_value": requested_value,
        # books value of the balances that were answered: the coverage basis
        "confirmed_value": confirmed_value,
        # what the parties themselves confirmed
        "amount_confirmed": sum(abs(r["confirmed_amount"]) for r in received
                                if r["confirmed_amount"] is not None),
        "coverage_pct": (confirmed_value / requested_value * 100.0)
                        if requested_value else 0.0,
        "returned": len([r for r in rows if r["status"] == STATUS_RETURNED]),
        "review": len([r for r in rows if r["status"] == STATUS_REVIEW]),
        "net_variance": sum(r["variance"] for r in rows
                            if r["variance"] is not None),
        "gross_variance": sum(abs(r["variance"]) for r in rows
                              if r["variance"] is not None),
    }


def summarise_by_category(rows):
    """The same figures split by balance category - the working-paper view."""
    out = []
    for category in CATEGORIES:
        subset = [r for r in rows if r["category"] == category]
        if not subset:
            continue
        stats = summarise(subset)
        stats["category"] = category
        stats["parties"] = len(subset)
        out.append(stats)
    return out
