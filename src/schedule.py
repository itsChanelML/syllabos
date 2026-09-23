"""
SyllabOS conflict detection and schedule utilities.
Pure Python logic — no API calls needed.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


PERSONAL_KEYWORDS = {
    "game night", "hangout", "party", "dinner", "movie", "gym",
    "social", "club meeting", "birthday", "outing", "fun", "friends",
    "shopping", "brunch", "concert", "date", "chill",
}


def get_next_monday(from_date: Optional[str] = None) -> str:
    """Return the ISO date of the next Monday."""
    if from_date:
        try:
            today = datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            today = datetime.now()
    else:
        today = datetime.now()

    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    return next_monday.strftime("%Y-%m-%d")


def detect_conflicts(deadlines: List[Dict], calendar_events: List[Dict] = None,
                     threshold: int = 3) -> List[Dict]:
    """
    Find weeks where too many deliverables pile up.
    Returns a list of conflict week dicts.
    """
    calendar_events = calendar_events or []

    by_week: Dict[str, List] = defaultdict(list)
    for d in deadlines:
        date_str = d.get("date", "")
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            by_week[week_start].append(d)
        except ValueError:
            continue

    conflicts = []
    for week_start, items in by_week.items():
        if len(items) < threshold:
            continue

        ws   = datetime.strptime(week_start, "%Y-%m-%d")
        we   = (ws + timedelta(days=6)).strftime("%Y-%m-%d")

        personal_at_risk = [
            e for e in calendar_events
            if week_start <= e.get("date", "") <= we
            and any(kw in e.get("title", "").lower() for kw in PERSONAL_KEYWORDS)
        ]

        exam_count = sum(1 for i in items if i.get("type") == "exam")
        severity   = "HIGH" if exam_count >= 1 and len(items) >= 3 else "MODERATE"

        conflicts.append({
            "week_start":         week_start,
            "week_end":           we,
            "week_label":         ws.strftime("Week of %B %d"),
            "deliverable_count":  len(items),
            "items":              items,
            "personal_at_risk":   personal_at_risk,
            "severity":           severity,
            "has_exam":           exam_count > 0,
            "courses_affected":   list({i.get("course", "") for i in items}),
        })

    return sorted(conflicts, key=lambda x: (x["severity"] == "HIGH", x["deliverable_count"]), reverse=True)


def suggest_reschedules(conflicts: List[Dict], calendar_events: List[Dict]) -> List[Dict]:
    """
    For conflict weeks with personal events, suggest moving those events.
    Returns reschedule suggestion dicts.
    """
    brutal_weeks = {c["week_start"] for c in conflicts}
    suggestions  = []

    for conflict in conflicts:
        ws = conflict["week_start"]
        for event in calendar_events:
            if event.get("date", "") < ws:
                continue
            ws_dt = datetime.strptime(ws, "%Y-%m-%d")
            we_dt = ws_dt + timedelta(days=6)
            if event.get("date", "") > we_dt.strftime("%Y-%m-%d"):
                continue
            if not any(kw in event.get("title", "").lower() for kw in PERSONAL_KEYWORDS):
                continue

            # Find lighter week to suggest
            next_w  = (ws_dt + timedelta(weeks=1)).strftime("%Y-%m-%d")
            week2   = (ws_dt + timedelta(weeks=2)).strftime("%Y-%m-%d")
            alt     = next_w if next_w not in brutal_weeks else week2
            alt_dt  = ws_dt + timedelta(weeks=1 if next_w not in brutal_weeks else 2)
            alt_lbl = alt_dt.strftime("%B %d")

            deadline_titles = [i.get("title", "") for i in conflict["items"][:3]]
            suggestions.append({
                "event_title":  event.get("title", "Personal event"),
                "event_date":   event.get("date", ""),
                "current_week": conflict["week_label"],
                "reason":       f"{conflict['deliverable_count']} deliverables this week: {', '.join(deadline_titles)}.",
                "suggestion":   f"Consider moving to the week of {alt_lbl} — lighter workload.",
                "alt_week":     alt,
                "severity":     conflict["severity"],
            })

    return suggestions


def get_upcoming_deadlines(deadlines: List[Dict], week_start: str,
                            days_ahead: int = 14) -> List[Dict]:
    """Return deadlines due within days_ahead of week_start."""
    try:
        ws = datetime.strptime(week_start, "%Y-%m-%d")
    except ValueError:
        return deadlines[:10]

    cutoff = ws + timedelta(days=days_ahead)
    upcoming = []
    for d in deadlines:
        try:
            due = datetime.strptime(d.get("date", ""), "%Y-%m-%d")
            if ws <= due <= cutoff:
                upcoming.append(d)
        except ValueError:
            continue

    return sorted(upcoming, key=lambda x: x.get("date", ""))


def map_blocks_to_dates(blocks: List[Dict], week_start: str) -> List[Dict]:
    """
    Map day names to actual ISO dates based on week_start.
    Adds a 'date' field to each block.
    """
    day_offset = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6,
    }

    try:
        ws = datetime.strptime(week_start, "%Y-%m-%d")
        ws = ws - timedelta(days=ws.weekday())  # ensure Monday
    except ValueError:
        ws = datetime.now()

    dated = []
    for block in blocks:
        day    = block.get("day", "Monday")
        offset = day_offset.get(day, 0)
        date   = (ws + timedelta(days=offset)).strftime("%Y-%m-%d")
        dated.append({**block, "date": date})

    return sorted(dated, key=lambda x: (x.get("date", ""), x.get("start_time", "")))