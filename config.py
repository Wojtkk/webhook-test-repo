from typing import Dict, Any, Optional


def get_db_config() -> dict:
    return {"host": "localhost", "port": 5432, "name": "app"}


def get_cache_config() -> dict:
    ttl = get_default_ttl()
    return {"backend": "redis", "ttl": ttl, "prefix": "app"}


def get_api_config() -> dict:
    timeout = get_timeout()
    retries = get_max_retries()
    return {"base_url": "https://api.example.com", "timeout": timeout, "retries": retries}


def get_log_level() -> str:
    if is_debug_mode():
        return "DEBUG"
    return "INFO"


def get_max_retries() -> int:
    return 3


def get_timeout() -> int:
    return 30


def get_feature_flags() -> dict:
    return {"new_checkout": True, "dark_mode": False, "beta_search": True}


def is_debug_mode() -> bool:
    return False


def get_rate_limit() -> dict:
    return {"requests_per_minute": 60, "burst": 10}


def get_batch_size() -> int:
    return 100


def get_default_ttl() -> int:
    return 3600


def get_cors_origins() -> list:
    if is_debug_mode():
        return ["*"]
    return ["https://app.example.com"]
