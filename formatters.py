from typing import List, Optional


def format_currency(amount: float, currency: str = "USD") -> str:
    symbol = get_currency_symbol(currency)
    formatted = f"{amount:,.2f}"
    return f"{symbol}{formatted}"


def get_currency_symbol(currency: str) -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "PLN": "zł"}
    return symbols.get(currency.upper(), currency + " ")


def format_date(date_str: str, style: str = "us") -> str:
    parts = date_str.split("-")
    if len(parts) != 3:
        return date_str
    if style == "us":
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    return f"{parts[2]}.{parts[1]}.{parts[0]}"


def format_phone(phone: str, country: str = "US") -> str:
    digits = extract_digits(phone)
    if country == "US" and len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def extract_digits(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def format_address(street: str, city: str, state: str, zip_code: str) -> str:
    parts = [street, city, f"{state} {zip_code}"]
    return join_non_empty(parts, ", ")


def join_non_empty(parts: List[str], separator: str) -> str:
    return separator.join(p for p in parts if p and p.strip())


def format_name(first: str, last: str, title: Optional[str] = None) -> str:
    clean_first = capitalize_first(first.strip())
    clean_last = capitalize_first(last.strip())
    if title:
        return f"{title} {clean_first} {clean_last}"
    return f"{clean_first} {clean_last}"


def capitalize_first(value: str) -> str:
    if not value:
        return value
    return value[0].upper() + value[1:]


def format_error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": truncate_string(message, 500)}}


def truncate_string(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[:max_len - 3] + "..."


def format_response(data: dict, status: str = "success") -> dict:
    return {"status": status, "data": data, "meta": build_meta()}


def build_meta() -> dict:
    return {"version": "1.0", "format": "json"}


def format_list(items: list, separator: str = ", ") -> str:
    str_items = [str(item) for item in items]
    return join_non_empty(str_items, separator)


def format_percentage(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def format_file_size(bytes_count: int) -> str:
    if bytes_count < 1024:
        return f"{bytes_count} B"
    if bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    return f"{bytes_count / (1024 * 1024):.1f} MB"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes}m {remaining:.0f}s"


def format_order_summary(order_id: str, total: float, currency: str, item_count: int) -> str:
    price = format_currency(total, currency)
    return f"Order #{order_id}: {item_count} items, {price}"
