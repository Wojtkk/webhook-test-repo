from typing import List, Optional, Dict
from formatters import format_response, format_error, format_percentage
from utils import generate_id, chunk_list
from product_repository import (
    find_product_by_id, update_stock, get_low_stock, list_products,
    find_product_by_sku, get_stock_value,
)
from notification_service import send_email, queue_notification
from models import create_notification_model


def check_availability(product_id: str, quantity: int) -> dict:
    product = find_product_by_id(product_id)
    if not product:
        return format_error("NOT_FOUND", "Product not found")
    available = product.get("stock", 0) >= quantity
    return format_response({
        "available": available,
        "requested": quantity,
        "in_stock": product.get("stock", 0),
    })


def reserve_stock(product_id: str, quantity: int) -> dict:
    availability = check_availability(product_id, quantity)
    if availability.get("data", {}).get("available") is not True:
        return format_error("OUT_OF_STOCK", "Insufficient stock")
    new_stock = update_stock(product_id, -quantity)
    if new_stock is None:
        return format_error("RESERVE_FAILED", "Could not reserve stock")
    check_reorder_needed(product_id)
    return format_response({"reserved": quantity, "remaining": new_stock})


def release_stock(product_id: str, quantity: int) -> dict:
    new_stock = update_stock(product_id, quantity)
    if new_stock is None:
        return format_error("RELEASE_FAILED", "Could not release stock")
    return format_response({"released": quantity, "current_stock": new_stock})


def update_inventory(product_id: str, new_quantity: int) -> dict:
    product = find_product_by_id(product_id)
    if not product:
        return format_error("NOT_FOUND", "Product not found")
    diff = new_quantity - product.get("stock", 0)
    update_stock(product_id, diff)
    return format_response({"product_id": product_id, "new_stock": new_quantity})


def get_stock_level(product_id: str) -> dict:
    product = find_product_by_id(product_id)
    if not product:
        return format_error("NOT_FOUND", "Product not found")
    return format_response({
        "product_id": product_id,
        "stock": product.get("stock", 0),
        "status": classify_stock_level(product.get("stock", 0)),
    })


def classify_stock_level(stock: int) -> str:
    if stock <= 0:
        return "out_of_stock"
    if stock <= 10:
        return "low"
    if stock <= 50:
        return "medium"
    return "high"


def check_reorder_needed(product_id: str) -> bool:
    product = find_product_by_id(product_id)
    if not product:
        return False
    if product.get("stock", 0) <= 10:
        trigger_reorder_alert(product)
        return True
    return False


def trigger_reorder_alert(product: dict) -> None:
    notification = create_notification_model(
        "system", "email",
        f"Low stock: {product.get('name', '')}",
        f"Product {product.get('sku', '')} has only {product.get('stock', 0)} units left."
    )
    queue_notification(notification, priority=1)


def reorder_check() -> dict:
    low_stock = get_low_stock(threshold=10)
    alerts = []
    for product in low_stock:
        alerts.append({
            "product_id": product["id"],
            "name": product.get("name"),
            "stock": product.get("stock", 0),
        })
    return format_response({"low_stock_count": len(alerts), "items": alerts})


def process_reorder(product_id: str, quantity: int) -> dict:
    product = find_product_by_id(product_id)
    if not product:
        return format_error("NOT_FOUND", "Product not found")
    order = create_reorder_record(product, quantity)
    return format_response(order)


def create_reorder_record(product: dict, quantity: int) -> dict:
    return {
        "id": generate_id("ro"),
        "product_id": product["id"],
        "sku": product.get("sku"),
        "quantity": quantity,
        "status": "submitted",
    }


def get_inventory_report() -> dict:
    products = list_products(active_only=True, limit=9999)
    total_value = get_stock_value()
    total_items = sum(p.get("stock", 0) for p in products)
    low_stock = get_low_stock(threshold=10)
    return format_response({
        "total_products": len(products),
        "total_items": total_items,
        "total_value": total_value,
        "low_stock_count": len(low_stock),
    })


def sync_inventory(external_data: List[dict]) -> dict:
    synced = 0
    errors = 0
    for item in external_data:
        result = sync_single_product(item)
        if result:
            synced += 1
        else:
            errors += 1
    return format_response({"synced": synced, "errors": errors})


def sync_single_product(item: dict) -> bool:
    sku = item.get("sku")
    if not sku:
        return False
    product = find_product_by_sku(sku)
    if not product:
        return False
    new_qty = item.get("quantity", 0)
    diff = new_qty - product.get("stock", 0)
    update_stock(product["id"], diff)
    return True


def audit_inventory() -> dict:
    products = list_products(active_only=False, limit=9999)
    discrepancies = []
    for product in products:
        expected = product.get("expected_stock", product.get("stock", 0))
        actual = product.get("stock", 0)
        if expected != actual:
            discrepancies.append({
                "product_id": product["id"],
                "expected": expected,
                "actual": actual,
                "diff": actual - expected,
            })
    return format_response({
        "total_checked": len(products),
        "discrepancies": len(discrepancies),
        "details": discrepancies,
    })
