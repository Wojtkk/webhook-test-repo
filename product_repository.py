from typing import List, Optional, Dict

_products_db: Dict[str, dict] = {}
_sku_index: Dict[str, str] = {}


def find_product_by_id(product_id: str) -> Optional[dict]:
    return _products_db.get(product_id)


def find_product_by_sku(sku: str) -> Optional[dict]:
    product_id = _sku_index.get(sku)
    if not product_id:
        return None
    return find_product_by_id(product_id)


def create_product_record(product: dict) -> dict:
    product_id = product["id"]
    _products_db[product_id] = product
    if "sku" in product:
        _sku_index[product["sku"]] = product_id
    return product


def update_product_record(product_id: str, updates: dict) -> Optional[dict]:
    product = find_product_by_id(product_id)
    if not product:
        return None
    for key, value in updates.items():
        if key != "id":
            product[key] = value
    return product


def delete_product_record(product_id: str) -> bool:
    product = find_product_by_id(product_id)
    if not product:
        return False
    if "sku" in product:
        _sku_index.pop(product["sku"], None)
    del _products_db[product_id]
    return True


def list_products(active_only: bool = True, limit: int = 100) -> List[dict]:
    products = list(_products_db.values())
    if active_only:
        products = filter_active_products(products)
    return products[:limit]


def filter_active_products(products: List[dict]) -> List[dict]:
    return [p for p in products if p.get("active", True)]


def search_products(query: str) -> List[dict]:
    query_lower = query.lower()
    results = []
    for product in _products_db.values():
        if matches_product(product, query_lower):
            results.append(product)
    return results


def matches_product(product: dict, query: str) -> bool:
    name = product.get("name", "").lower()
    sku = product.get("sku", "").lower()
    return query in name or query in sku


def get_product_categories() -> List[str]:
    categories = set()
    for product in _products_db.values():
        cat = product.get("category", "uncategorized")
        categories.add(cat)
    return sorted(categories)


def update_stock(product_id: str, quantity_change: int) -> Optional[int]:
    product = find_product_by_id(product_id)
    if not product:
        return None
    new_stock = product.get("stock", 0) + quantity_change
    if new_stock < 0:
        return None
    product["stock"] = new_stock
    return new_stock


def get_low_stock(threshold: int = 10) -> List[dict]:
    results = []
    for product in list_products(active_only=True, limit=9999):
        if is_low_stock(product, threshold):
            results.append(product)
    return results


def is_low_stock(product: dict, threshold: int) -> bool:
    return product.get("stock", 0) <= threshold


def get_stock_value() -> float:
    total = 0.0
    for product in _products_db.values():
        total += product.get("price", 0) * product.get("stock", 0)
    return total
