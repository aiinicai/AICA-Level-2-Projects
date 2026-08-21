from datetime import date, datetime


def parse_date(value):
    if isinstance(value, date):
        return value
    if value is None or value == "":
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except (ValueError, TypeError):
            continue
    raise ValueError(f"Unrecognised date format: {value}")


def format_date(d):
    if d is None:
        return ""
    if isinstance(d, str):
        d = parse_date(d)
    return d.strftime("%d-%b-%Y")


def to_iso(d):
    if d is None:
        return None
    if isinstance(d, str):
        d = parse_date(d)
    return d.isoformat()


def get_financial_year(d):
    """Indian financial year: 1-Apr to 31-Mar."""
    if isinstance(d, str):
        d = parse_date(d)
    if d is None:
        raise ValueError("Date required to determine financial year")
    start_year = d.year if d.month >= 4 else d.year - 1
    end_year = start_year + 1
    return f"FY {start_year}-{str(end_year)[-2:]}"


def financial_year_bounds(fy_label):
    """'FY 2026-27' -> (date(2026,4,1), date(2027,3,31))"""
    part = fy_label.replace("FY", "").strip()
    start_year_str, _ = part.split("-")
    start_year = int(start_year_str)
    end_year = start_year + 1
    return date(start_year, 4, 1), date(end_year, 3, 31)


def days_between(start_date, end_date):
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
    return (end_date - start_date).days + 1


def months_between(start_date, end_date):
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day >= start_date.day:
        months += 1
    return max(months, 0)


def days_in_financial_year(fy_label):
    start, end = financial_year_bounds(fy_label)
    return (end - start).days + 1