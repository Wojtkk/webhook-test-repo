from typing import List, Optional, Dict
from validators import validate_email, validate_phone
from formatters import format_response, format_error
from utils import generate_id, sanitize_string
from models import create_notification_model
from analytics import track_event


_notifications_db: Dict[str, dict] = {}
_queue: List[dict] = []
_templates: Dict[str, dict] = {}
_webhook_endpoints: Dict[str, str] = {}


def send_email(user_id: str, to_email: str, subject: str, body: str) -> dict:
    if not validate_email(to_email):
        return format_error("BAD_EMAIL", "Invalid email address")
    notification = create_notification_model(user_id, "email", subject, body)
    notification["to"] = to_email
    _notifications_db[notification["id"]] = notification
    track_event("notification_sent", {"channel": "email", "user_id": user_id}, user_id)
    return format_response({"sent": True, "id": notification["id"]})


def send_sms(user_id: str, phone: str, message: str) -> dict:
    if not validate_phone(phone):
        return format_error("BAD_PHONE", "Invalid phone number")
    notification = create_notification_model(user_id, "sms", "SMS", message)
    notification["to"] = phone
    notification["message"] = truncate_sms(message)
    _notifications_db[notification["id"]] = notification
    track_event("notification_sent", {"channel": "sms", "user_id": user_id}, user_id)
    return format_response({"sent": True, "id": notification["id"]})


def truncate_sms(message: str) -> str:
    if len(message) <= 160:
        return message
    return message[:157] + "..."


def send_push(user_id: str, title: str, body: str, data: Optional[dict] = None) -> dict:
    notification = create_notification_model(user_id, "push", title, body)
    if data:
        notification["data"] = data
    _notifications_db[notification["id"]] = notification
    track_event("notification_sent", {"channel": "push", "user_id": user_id}, user_id)
    return format_response({"sent": True, "id": notification["id"]})


def send_webhook(user_id: str, event_type: str, payload: dict) -> dict:
    endpoint = _webhook_endpoints.get(user_id)
    if not endpoint:
        return format_error("NO_ENDPOINT", "No webhook registered")
    delivery = create_webhook_delivery(user_id, event_type, payload, endpoint)
    result = execute_webhook(delivery)
    track_event("webhook_sent", {"event_type": event_type, "user_id": user_id}, user_id)
    return format_response(result)


def create_webhook_delivery(user_id: str, event_type: str, payload: dict, endpoint: str) -> dict:
    return {
        "id": generate_id("whd"),
        "user_id": user_id,
        "event_type": event_type,
        "payload": payload,
        "endpoint": endpoint,
        "status": "pending",
    }


def execute_webhook(delivery: dict) -> dict:
    delivery["status"] = "delivered"
    return {"delivered": True, "id": delivery["id"]}


def register_webhook(user_id: str, endpoint: str) -> dict:
    _webhook_endpoints[user_id] = sanitize_string(endpoint)
    return format_response({"registered": True, "endpoint": endpoint})


def queue_notification(notification: dict, priority: int = 5) -> dict:
    entry = {
        "id": generate_id("q"),
        "notification": notification,
        "priority": priority,
        "status": "queued",
    }
    _queue.append(entry)
    sort_queue()
    return entry


def sort_queue() -> None:
    _queue.sort(key=lambda x: x["priority"])


def process_queue(batch_size: int = 10) -> dict:
    processed = 0
    errors = 0
    batch = _queue[:batch_size]
    for entry in batch:
        result = dispatch_notification(entry["notification"])
        if result.get("success"):
            entry["status"] = "sent"
            processed += 1
        else:
            entry["status"] = "failed"
            errors += 1
    _queue[:batch_size] = [e for e in batch if e["status"] != "sent"]
    return {"processed": processed, "errors": errors, "remaining": len(_queue)}


def dispatch_notification(notification: dict) -> dict:
    channel = notification.get("channel", "")
    if channel == "email":
        return {"success": True}
    if channel == "sms":
        return {"success": True}
    if channel == "push":
        return {"success": True}
    if channel == "webhook":
        return {"success": True}
    return {"success": False, "reason": "Unknown channel"}


def get_notification_status(notification_id: str) -> dict:
    notification = _notifications_db.get(notification_id)
    if not notification:
        return format_error("NOT_FOUND", "Notification not found")
    return format_response({"status": "sent", "channel": notification.get("channel")})


def mark_read(notification_id: str) -> dict:
    notification = _notifications_db.get(notification_id)
    if not notification:
        return format_error("NOT_FOUND", "Notification not found")
    notification["read"] = True
    return format_response({"marked": True})


def list_notifications(user_id: str, unread_only: bool = False) -> dict:
    results = []
    for n in _notifications_db.values():
        if n.get("user_id") == user_id:
            if unread_only and n.get("read"):
                continue
            results.append(n)
    return format_response({"notifications": results, "count": len(results)})


def create_template(name: str, channel: str, subject_tpl: str, body_tpl: str) -> dict:
    template = {
        "id": generate_id("tpl"),
        "name": sanitize_string(name),
        "channel": channel,
        "subject": subject_tpl,
        "body": body_tpl,
    }
    _templates[template["id"]] = template
    return template


def render_template(template_id: str, variables: dict) -> dict:
    template = _templates.get(template_id)
    if not template:
        return format_error("NOT_FOUND", "Template not found")
    rendered_subject = substitute_variables(template["subject"], variables)
    rendered_body = substitute_variables(template["body"], variables)
    return {"subject": rendered_subject, "body": rendered_body}


def substitute_variables(text: str, variables: dict) -> str:
    result = text
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def get_unread_count(user_id: str) -> int:
    count = 0
    for n in _notifications_db.values():
        if n.get("user_id") == user_id and not n.get("read"):
            count += 1
    return count
