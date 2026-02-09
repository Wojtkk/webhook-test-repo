from typing import List, Optional, Dict, Any
from utils import generate_id, deep_copy, sanitize_string


def create_user_model(name: str, email: str, role: str = "user") -> dict:
    return {
        "id": generate_id("usr"),
        "name": sanitize_string(name),
        "email": email,
        "role": role,
        "active": True,
    }


def create_order_model(user_id: str, items: List[dict], currency: str = "USD") -> dict:
    order_items = [create_order_item(item) for item in items]
    total = sum(i["subtotal"] for i in order_items)
    return {
        "id": generate_id("ord"),
        "user_id": user_id,
        "items": order_items,
        "total": total,
        "currency": currency,
        "status": "created",
    }


def create_order_item(item: dict) -> dict:
    qty = item.get("quantity", 1)
    price = item.get("price", 0)
    return {
        "product_id": item.get("product_id", ""),
        "quantity": qty,
        "price": price,
        "subtotal": qty * price,
    }


def create_product_model(name: str, sku: str, price: float, stock: int = 0) -> dict:
    return {
        "id": generate_id("prd"),
        "name": sanitize_string(name),
        "sku": sku,
        "price": price,
        "stock": stock,
        "active": True,
    }


def create_payment_model(order_id: str, amount: float, method: str) -> dict:
    return {
        "id": generate_id("pay"),
        "order_id": order_id,
        "amount": amount,
        "method": method,
        "status": "pending",
    }


def create_address_model(street: str, city: str, state: str, zip_code: str, country: str = "US") -> dict:
    return {
        "id": generate_id("addr"),
        "street": sanitize_string(street),
        "city": sanitize_string(city),
        "state": state,
        "zip": zip_code,
        "country": country,
    }


def create_notification_model(user_id: str, channel: str, subject: str, body: str) -> dict:
    return {
        "id": generate_id("ntf"),
        "user_id": user_id,
        "channel": channel,
        "subject": sanitize_string(subject),
        "body": sanitize_string(body),
        "read": False,
    }


def serialize_model(model: dict) -> str:
    import json
    cleaned = strip_none_values(model)
    return json.dumps(cleaned, default=str)


def strip_none_values(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def deserialize_model(data: str) -> dict:
    import json
    raw = json.loads(data)
    return deep_copy(raw)


def validate_model(model: dict, required_fields: List[str]) -> bool:
    for field in required_fields:
        if field not in model or model[field] is None:
            return False
    return True


def clone_model(model: dict, overrides: Optional[dict] = None) -> dict:
    copy = deep_copy(model)
    copy["id"] = generate_id()
    if overrides:
        copy.update(overrides)
    return copy
