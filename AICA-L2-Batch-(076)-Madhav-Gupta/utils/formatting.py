from decimal import Decimal, ROUND_HALF_UP


def to_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_decimal(value, places=2):
    value = to_decimal(value)
    quant = Decimal("1." + "0" * places) if places > 0 else Decimal("1")
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def format_indian_currency(value, places=2, symbol="\u20b9"):
    value = round_decimal(value, places)
    negative = value < 0
    value = abs(value)
    int_part, _, dec_part = str(value).partition(".")
    dec_part = (dec_part + "0" * places)[:places]
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups + [last3])
    formatted = f"{symbol}{int_part}"
    if places > 0:
        formatted += f".{dec_part}"
    return f"-{formatted}" if negative else formatted