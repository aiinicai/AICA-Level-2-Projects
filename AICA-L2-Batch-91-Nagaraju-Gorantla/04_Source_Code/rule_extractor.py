import re


def extract_file_reference(text):

    match = re.search(
        r"\b[A-Z]{2,6}-\d{3,6}-(?:\d{2}|\d{4})\b",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(0).upper()

    return None


def extract_containers(text):

    matches = re.findall(
        r"\b[A-Z]{4}\d{7}\b",
        text,
        re.IGNORECASE
    )

    return list(
        dict.fromkeys(
            item.upper()
            for item in matches
        )
    )


def clean_charge_name(name):

    name = re.sub(
        r"^\s*\d+\s*[\.\)\-:]?\s*",
        "",
        name
    )

    name = re.sub(
        r"[-–—_:]+$",
        "",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    name = name.strip(
        " -–—_:."
    )

    name = re.sub(
        r"\bFERRI\b",
        "FERRY",
        name,
        flags=re.IGNORECASE
    )

    return name.upper()


def extract_charges(text):

    charges = []

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # $316 / USD 316
        match = re.search(
            r"""
            ^(?P<label>.*?)
            (?:
                USD\s*\$?
                |
                US\$\s*
                |
                \$\s*
            )
            (?P<amount>\d[\d,]*(?:\.\d{1,2})?)
            \s*$
            """,
            line,
            re.IGNORECASE | re.VERBOSE
        )

        if match:

            label = clean_charge_name(
                match.group("label")
            )

            amount = float(
                match.group("amount").replace(",", "")
            )

            if amount > 0 and label:

                charges.append({
                    "description": label,
                    "amount": amount
                })

            continue

        # 316$ / 316 USD
        match = re.search(
            r"""
            ^(?P<label>.*?)
            (?P<amount>\d[\d,]*(?:\.\d{1,2})?)
            \s*
            (?:
                USD
                |
                US\$
                |
                \$
            )
            \s*$
            """,
            line,
            re.IGNORECASE | re.VERBOSE
        )

        if match:

            label = clean_charge_name(
                match.group("label")
            )

            amount = float(
                match.group("amount").replace(",", "")
            )

            if amount > 0 and label:

                charges.append({
                    "description": label,
                    "amount": amount
                })

    return charges


def extract_email(text):

    file_ref = extract_file_reference(text)

    containers = extract_containers(text)

    charges = extract_charges(text)

    total = sum(
        item["amount"]
        for item in charges
    )

    return {
        "file_reference": file_ref,
        "containers": containers,
        "charges": charges,
        "total": total,
    }