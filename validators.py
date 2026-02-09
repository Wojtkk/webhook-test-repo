from typing import Optional
import re


def validate_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    return validate_domain(parts[1])


def validate_domain(domain: str) -> bool:
    if not domain or "." not in domain:
        return False
    return len(domain) >= 3


def validate_phone(phone: str) -> bool:
    cleaned = strip_non_digits(phone)
    return len(cleaned) >= 10 and len(cleaned) <= 15


def strip_non_digits(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def validate_name(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    return not contains_special_chars(name)


def contains_special_chars(value: str) -> bool:
    return bool(re.search(r'[<>&\'"\\]', value))


def validate_address(street: str, city: str, state: str, zip_code: str) -> bool:
    if not street or not city or not state:
        return False
    return validate_zip(zip_code)


def validate_zip(zip_code: str) -> bool:
    cleaned = strip_non_digits(zip_code)
    return len(cleaned) == 5 or len(cleaned) == 9


def validate_country(country: str) -> bool:
    valid = get_valid_countries()
    return country.upper() in valid


def get_valid_countries() -> set:
    return {"US", "CA", "GB", "DE", "FR", "JP", "AU", "PL"}


def validate_currency(currency: str) -> bool:
    valid = get_valid_currencies()
    return currency.upper() in valid


def get_valid_currencies() -> set:
    return {"USD", "EUR", "GBP", "JPY", "PLN", "CAD"}


def validate_amount(amount: float, min_val: float = 0.01, max_val: float = 999999.99) -> bool:
    if amount < min_val or amount > max_val:
        return False
    return validate_decimal_places(amount, 2)


def validate_decimal_places(value: float, max_places: int) -> bool:
    str_val = f"{value:.10f}"
    decimal_part = str_val.split(".")[1].rstrip("0")
    return len(decimal_part) <= max_places


def validate_date(date_str: str) -> bool:
    parts = date_str.split("-")
    if len(parts) != 3:
        return False
    return all(p.isdigit() for p in parts)


def validate_quantity(quantity: int) -> bool:
    return isinstance(quantity, int) and 0 < quantity <= 10000


def validate_sku(sku: str) -> bool:
    if not sku or len(sku) < 3:
        return False
    return not contains_special_chars(sku)


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit
