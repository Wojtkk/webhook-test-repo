from typing import List, Optional, Dict

_orders_db: Dict[str, dict] = {}


def find_order_by_id(order_id: str) -> Optional[dict]:
    return _orders_db.get(order_id)


def create_order_record(order: dict) -> dict:
    order_id = order["id"]
    _orders_db[order_id] = order
    index_order_by_user(order)
    return order


_user_order_index: Dict[str, List[str]] = {}


def index_order_by_user(order: dict) -> None:
    user_id = order.get("user_id", "")
    if user_id not in _user_order_index:
        _user_order_index[user_id] = []
    _user_order_index[user_id].append(order["id"])


def update_order_status(order_id: str, status: str) -> Optional[dict]:
    order = find_order_by_id(order_id)
    if not order:
        return None
    if not is_valid_status_transition(order["status"], status):
        return None
    order["status"] = status
    return order


def is_valid_status_transition(current: str, target: str) -> bool:
    valid = {
        "created": ["pending", "cancelled"],
        "pending": ["processing", "cancelled"],
        "processing": ["shipped", "cancelled"],
        "shipped": ["delivered"],
        "delivered": ["returned"],
    }
    return target in valid.get(current, [])


def delete_order_record(order_id: str) -> bool:
    if order_id in _orders_db:
        del _orders_db[order_id]
        return True
    return False


def list_orders_by_user(user_id: str, limit: int = 50) -> List[dict]:
    order_ids = _user_order_index.get(user_id, [])
    orders = []
    for oid in order_ids:
        order = find_order_by_id(oid)
        if order:
            orders.append(order)
    return sort_by_date(orders)[:limit]


def sort_by_date(orders: List[dict]) -> List[dict]:
    return sorted(orders, key=lambda o: o.get("created_at", ""), reverse=True)


def count_orders(user_id: Optional[str] = None) -> int:
    if user_id:
        return len(list_orders_by_user(user_id, limit=999999))
    return len(_orders_db)


def get_recent_orders(limit: int = 10) -> List[dict]:
    all_orders = list(_orders_db.values())
    return sort_by_date(all_orders)[:limit]


def get_order_items(order_id: str) -> List[dict]:
    order = find_order_by_id(order_id)
    if not order:
        return []
    return order.get("items", [])


def calculate_order_total(order_id: str) -> float:
    items = get_order_items(order_id)
    return sum(item.get("subtotal", 0) for item in items)


def get_order_history(user_id: str) -> List[dict]:
    orders = list_orders_by_user(user_id, limit=999)
    return [summarize_order(o) for o in orders]


def summarize_order(order: dict) -> dict:
    return {
        "id": order["id"],
        "status": order.get("status"),
        "total": order.get("total", 0),
        "item_count": len(order.get("items", [])),
    }
