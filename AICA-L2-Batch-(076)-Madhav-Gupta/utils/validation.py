import datetime

class ValidationError(Exception):
    pass

def require(condition, message):
    if not condition:
        raise ValidationError(message)

def validate_date(date_text, field_name):
    """Ensures the date is in YYYY-MM-DD format and is a real date."""
    if not date_text or date_text.strip() == "":
        return None
    try:
        return datetime.datetime.strptime(date_text.strip(), '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError(f"Invalid date format for {field_name}. Please use YYYY-MM-DD (e.g., 2023-04-01).")

def validate_category_code(code, existing_codes=None):
    require(bool(code), "Category code cannot be blank.")
    code = code.strip().upper()
    require(2 <= len(code) <= 5, "Category code must be 2-5 characters.")
    require(code.isalnum(), "Category code must be alphanumeric.")
    if existing_codes is not None:
        require(code not in existing_codes, f"Category code '{code}' already exists.")
    return code

def validate_positive(value, field_name):
    try:
        if value is None or str(value).strip() == "":
            raise ValueError()
        val = float(value)
        require(val >= 0, f"{field_name} cannot be negative.")
        return val
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number.")

def validate_useful_life(value):
    try:
        val = float(value)
        require(val > 0, "Useful life must be greater than zero.")
        return val
    except (ValueError, TypeError):
        raise ValidationError("Useful life must be a valid number.")