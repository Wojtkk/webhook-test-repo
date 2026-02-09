from typing import List, Dict, Optional
from utils import generate_id, chunk_list, sanitize_string
from formatters import format_currency, format_percentage, format_date, format_response
from analytics import compute_summary, get_top_events, get_session_stats, get_conversion_rate


_reports: Dict[str, dict] = {}


def create_report(title: str, report_type: str, data: dict) -> dict:
    report = {
        "id": generate_id("rpt"),
        "title": sanitize_string(title),
        "type": report_type,
        "data": data,
        "status": "draft",
    }
    _reports[report["id"]] = report
    return report


def generate_sales_report(orders: List[dict], currency: str = "USD") -> dict:
    total_revenue = sum(o.get("total", 0) for o in orders)
    avg_order = total_revenue / len(orders) if orders else 0
    formatted_revenue = format_currency(total_revenue, currency)
    formatted_avg = format_currency(avg_order, currency)

    data = {
        "total_orders": len(orders),
        "total_revenue": total_revenue,
        "formatted_revenue": formatted_revenue,
        "avg_order_value": avg_order,
        "formatted_avg": formatted_avg,
        "status_breakdown": breakdown_by_status(orders),
    }
    return create_report("Sales Report", "sales", data)


def breakdown_by_status(orders: List[dict]) -> Dict[str, int]:
    counts = {}
    for order in orders:
        status = order.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def generate_user_activity_report() -> dict:
    summary = compute_summary()
    sessions = get_session_stats()
    top_events = get_top_events(5)
    data = {
        "event_summary": summary,
        "session_stats": sessions,
        "top_events": top_events,
    }
    return create_report("User Activity Report", "activity", data)


def generate_conversion_report(funnel_events: List[str]) -> dict:
    rates = []
    for event in funnel_events:
        rate = get_conversion_rate(event)
        rates.append({"event": event, **rate})
    data = {
        "funnel": rates,
        "total_steps": len(funnel_events),
    }
    return create_report("Conversion Report", "conversion", data)


def get_report(report_id: str) -> Optional[dict]:
    return _reports.get(report_id)


def list_reports(report_type: Optional[str] = None) -> List[dict]:
    reports = list(_reports.values())
    if report_type:
        reports = [r for r in reports if r.get("type") == report_type]
    return reports


def publish_report(report_id: str) -> dict:
    report = get_report(report_id)
    if not report:
        return format_response({"error": "Report not found"})
    report["status"] = "published"
    return format_response(report)


def delete_report(report_id: str) -> bool:
    if report_id in _reports:
        del _reports[report_id]
        return True
    return False


def generate_inventory_summary(products: List[dict]) -> dict:
    total_stock = sum(p.get("stock", 0) for p in products)
    total_value = sum(p.get("price", 0) * p.get("stock", 0) for p in products)
    low_stock = [p for p in products if p.get("stock", 0) < 10]

    data = {
        "total_products": len(products),
        "total_stock": total_stock,
        "total_value": format_currency(total_value),
        "low_stock_count": len(low_stock),
        "low_stock_pct": format_percentage(
            len(low_stock) / len(products) * 100 if products else 0
        ),
    }
    return create_report("Inventory Summary", "inventory", data)


def aggregate_reports(report_ids: List[str]) -> dict:
    reports = []
    for rid in report_ids:
        report = get_report(rid)
        if report:
            reports.append(report)
    return format_response({
        "count": len(reports),
        "types": list(set(r["type"] for r in reports)),
        "reports": reports,
    })


def export_report(report_id: str, output_format: str = "json") -> dict:
    report = get_report(report_id)
    if not report:
        return {"error": "Report not found"}
    if output_format == "json":
        return format_as_json(report)
    return format_as_text(report)


def format_as_json(report: dict) -> dict:
    return {"format": "json", "content": report}


def format_as_text(report: dict) -> dict:
    title = report.get("title", "Untitled")
    return {"format": "text", "content": f"Report: {title}"}
