from typing import List, Optional
from validators import validate_amount, validate_currency
from formatters import format_currency, format_response, format_error
from utils import generate_id, retry_operation
from models import create_payment_model


_payments_db = {}


def process_payment(order_id: str, amount: float, method: str, currency: str = "USD") -> dict:
    if not validate_amount(amount):
        return format_error("BAD_AMOUNT", "Invalid amount")
    if not validate_currency(currency):
        return format_error("BAD_CURRENCY", "Invalid currency")
    if not validate_payment_method(method):
        return format_error("BAD_METHOD", "Unsupported payment method")

    payment = create_payment_model(order_id, amount, method)
    result = execute_payment(payment)
    if result["success"]:
        payment["status"] = "completed"
    else:
        payment["status"] = "failed"
    _payments_db[payment["id"]] = payment
    return format_response(payment)


def validate_payment_method(method: str) -> bool:
    return method in get_supported_methods()


def get_supported_methods() -> list:
    return ["credit_card", "debit_card", "paypal", "bank_transfer"]


def execute_payment(payment: dict) -> dict:
    return retry_operation(f"payment_{payment['id']}", max_retries=3)


def refund_payment(payment_id: str, reason: str = "") -> dict:
    payment = get_payment_by_id(payment_id)
    if not payment:
        return format_error("NOT_FOUND", "Payment not found")
    if payment["status"] != "completed":
        return format_error("INVALID_STATE", "Can only refund completed payments")
    refund = create_refund(payment, reason)
    payment["status"] = "refunded"
    return format_response(refund)


def create_refund(payment: dict, reason: str) -> dict:
    return {
        "id": generate_id("ref"),
        "payment_id": payment["id"],
        "amount": payment["amount"],
        "reason": reason,
        "status": "processed",
    }


def get_payment_by_id(payment_id: str) -> Optional[dict]:
    return _payments_db.get(payment_id)


def verify_payment(payment_id: str) -> dict:
    payment = get_payment_by_id(payment_id)
    if not payment:
        return format_error("NOT_FOUND", "Payment not found")
    verified = check_payment_with_provider(payment)
    return format_response({"verified": verified, "status": payment["status"]})


def check_payment_with_provider(payment: dict) -> bool:
    return payment.get("status") == "completed"


def get_payment_status(payment_id: str) -> dict:
    payment = get_payment_by_id(payment_id)
    if not payment:
        return format_error("NOT_FOUND", "Payment not found")
    return format_response({"status": payment["status"], "amount": format_currency(payment["amount"])})


def list_payments(order_id: Optional[str] = None, limit: int = 50) -> dict:
    payments = list(_payments_db.values())
    if order_id:
        payments = filter_by_order(payments, order_id)
    return format_response({"payments": payments[:limit], "count": len(payments)})


def filter_by_order(payments: list, order_id: str) -> list:
    return [p for p in payments if p.get("order_id") == order_id]


def create_invoice(order_id: str, amount: float, currency: str = "USD") -> dict:
    invoice_id = generate_id("inv")
    formatted = format_currency(amount, currency)
    return {
        "id": invoice_id,
        "order_id": order_id,
        "amount": amount,
        "formatted_amount": formatted,
        "status": "issued",
    }


def validate_card(card_number: str, expiry: str, cvv: str) -> dict:
    number_valid = check_card_number(card_number)
    expiry_valid = check_expiry(expiry)
    cvv_valid = len(cvv) in (3, 4)
    return {
        "valid": number_valid and expiry_valid and cvv_valid,
        "card_type": detect_card_type(card_number),
    }


def check_card_number(number: str) -> bool:
    digits = number.replace(" ", "").replace("-", "")
    return len(digits) >= 13 and len(digits) <= 19 and digits.isdigit()


def check_expiry(expiry: str) -> bool:
    parts = expiry.split("/")
    return len(parts) == 2 and all(p.isdigit() for p in parts)


def detect_card_type(number: str) -> str:
    digits = number.replace(" ", "")
    if digits.startswith("4"):
        return "visa"
    if digits.startswith("5"):
        return "mastercard"
    return "unknown"


def calculate_tax(amount: float, rate: float = 0.08) -> dict:
    tax = round(amount * rate, 2)
    total = round(amount + tax, 2)
    return {"subtotal": amount, "tax": tax, "rate": rate, "total": total}


def get_payment_history(user_id: str) -> dict:
    payments = [p for p in _payments_db.values()]
    return format_response({"payments": payments, "total_spent": sum_payments(payments)})


def sum_payments(payments: list) -> float:
    return sum(p.get("amount", 0) for p in payments if p.get("status") == "completed")


def retry_failed_payment(payment_id: str) -> dict:
    payment = get_payment_by_id(payment_id)
    if not payment:
        return format_error("NOT_FOUND", "Payment not found")
    if payment["status"] != "failed":
        return format_error("INVALID_STATE", "Only failed payments can be retried")
    result = execute_payment(payment)
    if result["success"]:
        payment["status"] = "completed"
    return format_response(payment)
