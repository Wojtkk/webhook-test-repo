from typing import Optional, List
from validators import validate_email, validate_name
from formatters import format_currency, format_response
from utils import generate_id, sanitize_string
from models import create_user_model


def create_user(name: str, email: str) -> dict:
    if not validate_name(name):
        raise ValueError("Invalid name")
    if not validate_email(email):
        raise ValueError("Invalid email")
    return create_user_model(name, email)


def deactivate_user(user: dict) -> dict:
    user["active"] = False
    return user


def process_order(user: dict, items: List[dict]) -> dict:
    if not user.get("active"):
        raise ValueError("User is not active")
    total = calculate_total(items)
    formatted = format_currency(total)
    return {
        "user": user["name"],
        "total": total,
        "display_total": formatted,
        "status": "pending",
    }


def calculate_total(items: List[dict]) -> float:
    total = 0.0
    for item in items:
        price = item.get("price", 0)
        quantity = item.get("quantity", 1)
        total += price * quantity
    return round(total, 2)


def get_user_orders(user: dict) -> List[dict]:
    if not user.get("active"):
        return []
    return [{"id": 1, "status": "completed"}]


def get_system_health() -> dict:
    return format_response({
        "status": "healthy",
        "services": check_all_services(),
    })


def check_all_services() -> dict:
    return {
        "database": "ok",
        "cache": "ok",
        "queue": "ok",
    }
