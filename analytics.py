from typing import List, Dict, Optional
from utils import generate_id, sanitize_string, chunk_list
from formatters import format_percentage, format_duration, format_response


_events: List[dict] = []
_sessions: Dict[str, dict] = {}


def track_event(event_name: str, metadata: dict, user_id: Optional[str] = None) -> dict:
    entry = create_event_entry(event_name, metadata, user_id)
    _events.append(entry)
    if user_id:
        update_session(user_id, event_name)
    return entry


def create_event_entry(event_name: str, metadata: dict, user_id: Optional[str]) -> dict:
    return {
        "id": generate_id("evt"),
        "event": sanitize_string(event_name),
        "data": metadata,
        "user_id": user_id,
    }


def update_session(user_id: str, event_name: str) -> None:
    if user_id not in _sessions:
        _sessions[user_id] = create_session(user_id)
    session = _sessions[user_id]
    session["event_count"] = session.get("event_count", 0) + 1
    session["last_event"] = event_name


def create_session(user_id: str) -> dict:
    return {
        "id": generate_id("ses"),
        "user_id": user_id,
        "event_count": 0,
        "last_event": None,
    }


def get_all_events(event_name: Optional[str] = None) -> List[dict]:
    if event_name:
        return filter_events_by_name(event_name)
    return list(_events)


def filter_events_by_name(name: str) -> List[dict]:
    return [e for e in _events if e.get("event") == name]


def get_user_events(user_id: str) -> List[dict]:
    return [e for e in _events if e.get("user_id") == user_id]


def compute_summary() -> dict:
    total = len(_events)
    by_type = count_by_type()
    unique_users = count_unique_users()
    return {
        "total_events": total,
        "by_type": by_type,
        "unique_users": unique_users,
    }


def count_by_type() -> Dict[str, int]:
    counts = {}
    for event in _events:
        name = event.get("event", "unknown")
        counts[name] = counts.get(name, 0) + 1
    return counts


def count_unique_users() -> int:
    users = set()
    for event in _events:
        uid = event.get("user_id")
        if uid:
            users.add(uid)
    return len(users)


def generate_report(period: str = "all") -> dict:
    events = get_all_events()
    summary = compute_summary()
    top = get_top_events(10)
    return format_response({
        "period": period,
        "summary": summary,
        "top_events": top,
        "total": len(events),
    })


def get_top_events(limit: int = 10) -> List[dict]:
    counts = count_by_type()
    sorted_events = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"event": name, "count": count} for name, count in sorted_events[:limit]]


def get_session_stats() -> dict:
    if not _sessions:
        return {"sessions": 0, "avg_events": 0}
    total_events = sum(s.get("event_count", 0) for s in _sessions.values())
    avg = total_events / len(_sessions) if _sessions else 0
    return {
        "sessions": len(_sessions),
        "avg_events_per_session": round(avg, 2),
        "total_events": total_events,
    }


def export_events(batch_size: int = 100) -> List[List[dict]]:
    return chunk_list(_events, batch_size)


def clear_events() -> int:
    count = len(_events)
    _events.clear()
    _sessions.clear()
    return count


def get_conversion_rate(target_event: str) -> dict:
    total_users = count_unique_users()
    if total_users == 0:
        return {"rate": 0, "formatted": format_percentage(0)}
    target_users = set()
    for event in _events:
        if event.get("event") == target_event and event.get("user_id"):
            target_users.add(event["user_id"])
    rate = len(target_users) / total_users * 100
    return {"rate": round(rate, 2), "formatted": format_percentage(rate)}
