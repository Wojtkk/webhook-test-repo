from typing import List, Optional, Dict

_users_db: Dict[str, dict] = {}


def find_user_by_id(user_id: str) -> Optional[dict]:
    return _users_db.get(user_id)


def find_user_by_email(email: str) -> Optional[dict]:
    email_lower = normalize_email(email)
    for user in _users_db.values():
        if normalize_email(user.get("email", "")) == email_lower:
            return user
    return None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user_record(user: dict) -> dict:
    user_id = user["id"]
    _users_db[user_id] = user
    add_audit_entry(user_id, "created")
    return user


def update_user_record(user_id: str, updates: dict) -> Optional[dict]:
    user = find_user_by_id(user_id)
    if not user:
        return None
    for key, value in updates.items():
        if key != "id":
            user[key] = value
    add_audit_entry(user_id, "updated")
    return user


def delete_user_record(user_id: str) -> bool:
    if user_id in _users_db:
        del _users_db[user_id]
        add_audit_entry(user_id, "deleted")
        return True
    return False


def list_users(active_only: bool = True, limit: int = 100) -> List[dict]:
    users = list(_users_db.values())
    if active_only:
        users = filter_active(users)
    return users[:limit]


def filter_active(users: List[dict]) -> List[dict]:
    return [u for u in users if u.get("active", True)]


def count_users(active_only: bool = True) -> int:
    users = list_users(active_only=active_only, limit=999999)
    return len(users)


def search_users(query: str, fields: List[str] = None) -> List[dict]:
    if not fields:
        fields = ["name", "email"]
    query_lower = query.lower()
    results = []
    for user in _users_db.values():
        if match_user_fields(user, query_lower, fields):
            results.append(user)
    return results


def match_user_fields(user: dict, query: str, fields: List[str]) -> bool:
    for field in fields:
        value = user.get(field, "")
        if value and query in str(value).lower():
            return True
    return False


def user_exists(email: str) -> bool:
    return find_user_by_email(email) is not None


def get_user_roles(user_id: str) -> List[str]:
    user = find_user_by_id(user_id)
    if not user:
        return []
    return extract_roles(user)


def extract_roles(user: dict) -> List[str]:
    role = user.get("role", "user")
    if role == "admin":
        return ["admin", "user"]
    return [role]


_audit_log: List[dict] = []


def add_audit_entry(entity_id: str, action: str) -> None:
    _audit_log.append({"entity_id": entity_id, "action": action})


def get_audit_log(entity_id: str) -> List[dict]:
    return [e for e in _audit_log if e["entity_id"] == entity_id]
