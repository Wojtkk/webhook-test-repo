from typing import List, Optional
from validators import validate_amount, validate_quantity, validate_currency
from formatters import format_currency, format_response, format_error, format_order_summary
from utils import generate_id
from models import create_order_model, create_order_item, validate_model
from order_repository import (
    create_order_record, find_order_by_id, update_order_status,
    list_orders_by_user, get_order_items, calculate_order_total,
    get_order_history, count_orders,
)
from product_repository import find_product_by_id, update_stock
from user_repository import find_user_by_id


def create_order(user_id: str, items: List[dict], currency: str = "USD") -> dict:
    user = find_user_by_id(user_id)
    if not user:
        return format_error("USER_NOT_FOUND", "User does not exist")
    if not user.get("active"):
        return format_error("USER_INACTIVE", "User account is inactive")
    if not validate_currency(currency):
        return format_error("BAD_CURRENCY", "Unsupported currency")

    validation = validate_order_items(items)
    if not validation["valid"]:
        return format_error("INVALID_ITEMS", validation["reason"])

    order = create_order_model(user_id, items, currency)
    created = create_order_record(order)
    reserve_order_stock(created)
    return format_response(created)


def validate_order_items(items: List[dict]) -> dict:
    if not items:
        return {"valid": False, "reason": "No items"}
    for item in items:
        if not validate_quantity(item.get("quantity", 0)):
            return {"valid": False, "reason": "Invalid quantity"}
        if not validate_amount(item.get("price", 0)):
            return {"valid": False, "reason": "Invalid price"}
        if not check_product_exists(item.get("product_id", "")):
            return {"valid": False, "reason": f"Product {item.get('product_id')} not found"}
    return {"valid": True, "reason": ""}


def check_product_exists(product_id: str) -> bool:
    return find_product_by_id(product_id) is not None


def reserve_order_stock(order: dict) -> None:
    for item in order.get("items", []):
        update_stock(item["product_id"], -item["quantity"])


def cancel_order(order_id: str, user_id: str) -> dict:
    order = find_order_by_id(order_id)
    if not order:
        return format_error("NOT_FOUND", "Order not found")
    if order.get("user_id") != user_id:
        return format_error("FORBIDDEN", "Not your order")
    updated = update_order_status(order_id, "cancelled")
    if not updated:
        return format_error("INVALID_STATE", "Cannot cancel in current state")
    release_order_stock(order)
    return format_response(updated)


def release_order_stock(order: dict) -> None:
    for item in order.get("items", []):
        update_stock(item["product_id"], item["quantity"])


def update_order(order_id: str, updates: dict) -> dict:
    order = find_order_by_id(order_id)
    if not order:
        return format_error("NOT_FOUND", "Order not found")
    return format_response(order)


def get_order_details(order_id: str) -> dict:
    order = find_order_by_id(order_id)
    if not order:
        return format_error("NOT_FOUND", "Order not found")
    total = calculate_order_total(order_id)
    summary = format_order_summary(
        order_id, total, order.get("currency", "USD"), len(order.get("items", []))
    )
    return format_response({"order": order, "summary": summary})


def list_user_orders(user_id: str, limit: int = 20) -> dict:
    orders = list_orders_by_user(user_id, limit=limit)
    return format_response({"orders": orders, "count": len(orders)})


def process_refund(order_id: str, reason: str) -> dict:
    order = find_order_by_id(order_id)
    if not order:
        return format_error("NOT_FOUND", "Order not found")
    updated = update_order_status(order_id, "returned")
    if not updated:
        return format_error("INVALID_STATE", "Cannot refund in current state")
    release_order_stock(order)
    amount = calculate_order_total(order_id)
    return format_response({"refunded": amount, "reason": reason})


def calculate_shipping(items: List[dict], destination: str) -> dict:
    weight = sum(compute_item_weight(i) for i in items)
    cost = compute_shipping_cost(weight, destination)
    formatted = format_currency(cost)
    return {"cost": cost, "formatted": formatted, "weight": weight}


def compute_item_weight(item: dict) -> float:
    return item.get("quantity", 1) * item.get("weight", 0.5)


def compute_shipping_cost(weight: float, destination: str) -> float:
    base = 5.0
    per_kg = 2.0
    if destination != "US":
        per_kg = 5.0
    return base + weight * per_kg


def apply_discount(order_id: str, code: str) -> dict:
    order = find_order_by_id(order_id)
    if not order:
        return format_error("NOT_FOUND", "Order not found")
    discount = lookup_discount(code)
    if not discount:
        return format_error("INVALID_CODE", "Discount code not valid")
    new_total = order.get("total", 0) * (1 - discount["percentage"] / 100)
    return format_response({"original": order["total"], "discounted": new_total, "code": code})


def lookup_discount(code: str) -> Optional[dict]:
    codes = {"SAVE10": {"percentage": 10}, "SAVE20": {"percentage": 20}}
    return codes.get(code.upper())


def validate_order(order_id: str) -> dict:
    order = find_order_by_id(order_id)
    if not order:
        return {"valid": False, "reason": "Order not found"}
    items = get_order_items(order_id)
    if not items:
        return {"valid": False, "reason": "No items"}
    return {"valid": True, "order_id": order_id}


def submit_order(order_id: str) -> dict:
    validation = validate_order(order_id)
    if not validation["valid"]:
        return format_error("INVALID", validation["reason"])
    updated = update_order_status(order_id, "pending")
    if not updated:
        return format_error("STATE_ERROR", "Cannot submit")
    return format_response({"submitted": True, "order_id": order_id})
