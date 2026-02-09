from user_service import (
    register_user, authenticate_user, update_profile, get_user_profile,
    deactivate_account, change_password, reset_password, list_active_users,
    search_user_accounts,
)
from order_service import (
    create_order, cancel_order, get_order_details, list_user_orders,
    submit_order, calculate_shipping, apply_discount, process_refund,
)
from payment_service import (
    process_payment, get_payment_status, list_payments, validate_card,
    create_invoice, retry_failed_payment,
)
from notification_service import (
    send_email, send_push, list_notifications, mark_read,
    get_unread_count,
)
from inventory_service import (
    check_availability, get_inventory_report, reorder_check,
    get_stock_level, sync_inventory,
)
from middleware import (
    authenticate_request, authorize_request, rate_limit_check,
    log_request, log_response, create_request_context,
)
from formatters import format_response, format_error
from config import get_feature_flags


def handle_register(request: dict) -> dict:
    log_request("POST", "/register", request.get("headers", {}))
    result = register_user(
        request.get("name", ""),
        request.get("email", ""),
        request.get("password", ""),
    )
    return result


def handle_login(request: dict) -> dict:
    log_request("POST", "/login", request.get("headers", {}))
    result = authenticate_user(
        request.get("email", ""),
        request.get("password", ""),
    )
    return result


def handle_create_order(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    rate = rate_limit_check(context["auth"]["user"].get("user_id", ""))
    if not rate["allowed"]:
        return format_error("RATE_LIMITED", "Too many requests")
    result = create_order(
        request.get("user_id", ""),
        request.get("items", []),
        request.get("currency", "USD"),
    )
    return result


def handle_get_orders(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    return list_user_orders(request.get("user_id", ""))


def handle_payment(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    card_validation = validate_card(
        request.get("card_number", ""),
        request.get("expiry", ""),
        request.get("cvv", ""),
    )
    if not card_validation["valid"]:
        return format_error("INVALID_CARD", "Card validation failed")
    result = process_payment(
        request.get("order_id", ""),
        request.get("amount", 0),
        "credit_card",
        request.get("currency", "USD"),
    )
    return result


def handle_notification_preferences(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    user_id = request.get("user_id", "")
    unread = get_unread_count(user_id)
    notifications = list_notifications(user_id, unread_only=True)
    return format_response({"unread": unread, "notifications": notifications})


def run_health_check() -> dict:
    flags = get_feature_flags()
    inventory = get_inventory_report()
    return format_response({
        "status": "ok",
        "features": flags,
        "inventory_summary": inventory,
    })


def handle_inventory_check(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    auth_check = authorize_request(context["auth"]["user"], "admin")
    if not auth_check["authorized"]:
        return format_error("FORBIDDEN", "Admin access required")
    return reorder_check()


def handle_search(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    query = request.get("query", "")
    users = search_user_accounts(query)
    return format_response({"results": users})


def handle_user_profile(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    return get_user_profile(request.get("user_id", ""))


def handle_password_change(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")
    return change_password(
        request.get("user_id", ""),
        request.get("old_password", ""),
        request.get("new_password", ""),
    )


def handle_checkout(request: dict) -> dict:
    context = create_request_context(request.get("headers", {}))
    if not context["auth"]["authenticated"]:
        return format_error("UNAUTHORIZED", "Login required")

    order_id = request.get("order_id", "")
    shipping = calculate_shipping(request.get("items", []), request.get("country", "US"))

    discount_code = request.get("discount_code")
    if discount_code:
        apply_discount(order_id, discount_code)

    submit_result = submit_order(order_id)
    if submit_result.get("status") != "success":
        return submit_result

    payment_result = process_payment(
        order_id, request.get("total", 0), "credit_card"
    )
    invoice = create_invoice(order_id, request.get("total", 0))

    send_email(
        request.get("user_id", ""),
        request.get("email", ""),
        "Order Confirmation",
        f"Your order {order_id} has been placed.",
    )

    return format_response({
        "order": submit_result,
        "payment": payment_result,
        "invoice": invoice,
        "shipping": shipping,
    })
