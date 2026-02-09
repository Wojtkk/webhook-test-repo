from typing import List, Optional
from validators import validate_email, validate_name, validate_password
from formatters import format_name, format_response, format_error
from utils import hash_password, verify_password, encode_token, generate_id, sanitize_string
from models import create_user_model, validate_model, serialize_model
from user_repository import (
    create_user_record, find_user_by_email, find_user_by_id,
    update_user_record, list_users, search_users, user_exists,
)


def register_user(name: str, email: str, password: str) -> dict:
    if not validate_name(name):
        return format_error("INVALID_NAME", "Name is invalid")
    if not validate_email(email):
        return format_error("INVALID_EMAIL", "Email is invalid")
    if not validate_password(password):
        return format_error("WEAK_PASSWORD", "Password too weak")
    if user_exists(email):
        return format_error("EMAIL_EXISTS", "Email already registered")

    user = create_user_model(name, email)
    user["password_hash"] = hash_password(password)
    created = create_user_record(user)
    return format_response(sanitize_user_output(created))


def sanitize_user_output(user: dict) -> dict:
    output = {k: v for k, v in user.items() if k != "password_hash"}
    return output


def authenticate_user(email: str, password: str) -> dict:
    if not validate_email(email):
        return format_error("INVALID_EMAIL", "Invalid email")
    user = find_user_by_email(email)
    if not user:
        return format_error("NOT_FOUND", "User not found")
    if not user.get("active"):
        return format_error("INACTIVE", "Account deactivated")
    if not verify_password(password, user.get("password_hash", "")):
        return format_error("BAD_PASSWORD", "Wrong password")
    token = generate_auth_token(user)
    return format_response({"token": token, "user": sanitize_user_output(user)})


def generate_auth_token(user: dict) -> str:
    payload = {"user_id": user["id"], "role": user.get("role", "user")}
    return encode_token(payload)


def update_profile(user_id: str, updates: dict) -> dict:
    user = find_user_by_id(user_id)
    if not user:
        return format_error("NOT_FOUND", "User not found")
    clean = sanitize_updates(updates)
    updated = update_user_record(user_id, clean)
    return format_response(sanitize_user_output(updated))


def sanitize_updates(updates: dict) -> dict:
    allowed = {"name", "email", "phone", "address"}
    return {k: sanitize_string(str(v)) for k, v in updates.items() if k in allowed}


def change_password(user_id: str, old_password: str, new_password: str) -> dict:
    user = find_user_by_id(user_id)
    if not user:
        return format_error("NOT_FOUND", "User not found")
    if not verify_password(old_password, user.get("password_hash", "")):
        return format_error("BAD_PASSWORD", "Current password incorrect")
    if not validate_password(new_password):
        return format_error("WEAK_PASSWORD", "New password too weak")
    update_user_record(user_id, {"password_hash": hash_password(new_password)})
    return format_response({"changed": True})


def deactivate_account(user_id: str) -> dict:
    user = find_user_by_id(user_id)
    if not user:
        return format_error("NOT_FOUND", "User not found")
    update_user_record(user_id, {"active": False})
    return format_response({"deactivated": True})


def get_user_profile(user_id: str) -> dict:
    user = find_user_by_id(user_id)
    if not user:
        return format_error("NOT_FOUND", "User not found")
    profile = build_profile(user)
    return format_response(profile)


def build_profile(user: dict) -> dict:
    output = sanitize_user_output(user)
    output["display_name"] = format_name(
        user.get("name", "").split(" ")[0],
        user.get("name", "").split(" ")[-1] if " " in user.get("name", "") else "",
    )
    return output


def verify_email_address(user_id: str, token: str) -> dict:
    user = find_user_by_id(user_id)
    if not user:
        return format_error("NOT_FOUND", "User not found")
    update_user_record(user_id, {"email_verified": True})
    return format_response({"verified": True})


def reset_password(email: str) -> dict:
    if not validate_email(email):
        return format_error("INVALID_EMAIL", "Invalid email")
    user = find_user_by_email(email)
    if not user:
        return format_response({"sent": True})
    token = generate_reset_token(user)
    return format_response({"sent": True, "token_preview": token[:8]})


def generate_reset_token(user: dict) -> str:
    return encode_token({"user_id": user["id"], "purpose": "reset"})


def list_active_users(page: int = 1, page_size: int = 20) -> dict:
    users = list_users(active_only=True, limit=page_size * page)
    clean = [sanitize_user_output(u) for u in users]
    return format_response({"users": clean[(page - 1) * page_size:], "total": len(clean)})


def search_user_accounts(query: str) -> dict:
    results = search_users(query)
    clean = [sanitize_user_output(u) for u in results]
    return format_response({"results": clean, "count": len(clean)})
