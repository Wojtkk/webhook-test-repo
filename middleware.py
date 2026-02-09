from typing import Dict, Optional, List
from utils import decode_token, sanitize_string, encode_token
from config import get_rate_limit, get_cors_origins, is_debug_mode, get_log_level
from validators import validate_email


_rate_limits: Dict[str, List[float]] = {}
_metrics: List[dict] = []


def authenticate_request(headers: dict) -> dict:
    token = extract_token(headers)
    if not token:
        return {"authenticated": False, "error": "No token"}
    payload = decode_token(token)
    if not payload:
        return {"authenticated": False, "error": "Invalid token"}
    return {"authenticated": True, "user": payload}


def extract_token(headers: dict) -> Optional[str]:
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def authorize_request(user: dict, required_role: str) -> dict:
    user_role = user.get("role", "user")
    allowed = check_role_hierarchy(user_role, required_role)
    return {"authorized": allowed, "role": user_role, "required": required_role}


def check_role_hierarchy(user_role: str, required_role: str) -> bool:
    hierarchy = {"admin": 3, "moderator": 2, "user": 1, "guest": 0}
    user_level = hierarchy.get(user_role, 0)
    required_level = hierarchy.get(required_role, 0)
    return user_level >= required_level


def rate_limit_check(client_id: str) -> dict:
    config = get_rate_limit()
    max_requests = config.get("requests_per_minute", 60)
    import time
    now = time.time()
    if client_id not in _rate_limits:
        _rate_limits[client_id] = []
    window = [t for t in _rate_limits[client_id] if now - t < 60]
    _rate_limits[client_id] = window
    if len(window) >= max_requests:
        return {"allowed": False, "remaining": 0, "retry_after": 60}
    _rate_limits[client_id].append(now)
    return {"allowed": True, "remaining": max_requests - len(window) - 1}


def log_request(method: str, path: str, headers: dict) -> dict:
    level = get_log_level()
    entry = {
        "type": "request",
        "method": method,
        "path": sanitize_string(path),
        "level": level,
    }
    if level == "DEBUG":
        entry["headers"] = sanitize_headers(headers)
    return entry


def sanitize_headers(headers: dict) -> dict:
    sensitive = {"Authorization", "Cookie", "X-API-Key"}
    return {k: ("***" if k in sensitive else v) for k, v in headers.items()}


def log_response(status_code: int, duration_ms: float, path: str) -> dict:
    entry = {
        "type": "response",
        "status": status_code,
        "duration_ms": round(duration_ms, 2),
        "path": path,
    }
    track_metric("response_time", duration_ms, {"path": path, "status": status_code})
    return entry


def validate_content_type(headers: dict, expected: str = "application/json") -> bool:
    content_type = headers.get("Content-Type", "")
    return content_type.startswith(expected)


def parse_headers(raw_headers: dict) -> dict:
    parsed = {}
    for key, value in raw_headers.items():
        parsed[key.lower()] = sanitize_string(str(value))
    return parsed


def handle_cors(origin: str) -> dict:
    allowed = get_cors_origins()
    if "*" in allowed or origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    return {}


def compress_response(data: str, min_size: int = 1024) -> dict:
    if len(data) < min_size:
        return {"compressed": False, "data": data, "size": len(data)}
    compressed_size = estimate_compressed_size(data)
    return {"compressed": True, "original_size": len(data), "compressed_size": compressed_size}


def estimate_compressed_size(data: str) -> int:
    unique_chars = len(set(data))
    ratio = max(0.1, unique_chars / 256)
    return int(len(data) * ratio)


def track_metric(name: str, value: float, tags: Optional[dict] = None) -> None:
    _metrics.append({"name": name, "value": value, "tags": tags or {}})


def get_metrics_summary() -> dict:
    if not _metrics:
        return {"count": 0}
    values = [m["value"] for m in _metrics]
    return {
        "count": len(values),
        "avg": sum(values) / len(values),
        "max": max(values),
        "min": min(values),
    }


def create_request_context(headers: dict) -> dict:
    auth = authenticate_request(headers)
    parsed = parse_headers(headers)
    return {
        "auth": auth,
        "headers": parsed,
        "debug": is_debug_mode(),
    }
