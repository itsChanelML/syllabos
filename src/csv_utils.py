"""
Read SyllabOS's own exported CSVs back into structured data. Used by the
morning briefing to find approaching deadlines, today's study blocks, and to
fall back to the last exported schedule when live Google Calendar isn't
available. Pure parsing — no network, no NIM calls.
"""

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_KNOWN_FIELDS = {"Course", "Type", "Weight", "Estimated study time"}


def _parse_description(desc: str) -> Dict[str, str]:
    """
    SyllabOS's exporters join fields as "Key: value | Key: value | notes |
    Added by SyllabOS". Split back out the known key/value fields; anything
    else (free-text notes) is kept under "Notes".
    """
    fields: Dict[str, str] = {}
    notes = []
    for part in desc.split(" | "):
        part = part.strip()
        if not part or part == "Added by SyllabOS":
            continue
        m = re.match(r"^([A-Za-z ]+):\s*(.*)$", part)
        if m and m.group(1).strip() in _KNOWN_FIELDS:
            fields[m.group(1).strip()] = m.group(2).strip()
        else:
            notes.append(part)
    if notes:
        fields["Notes"] = " ".join(notes)
    return fields


def gc_date_to_iso(date_str: str) -> Optional[str]:
    """Convert a Google-Calendar-CSV date ('MM/DD/YYYY') to ISO ('YYYY-MM-DD')."""
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def read_deadlines_csv(path: Path) -> List[Dict]:
    """Read semester_deadlines.csv back into deadline dicts."""
    if not path.exists():
        return []
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date = gc_date_to_iso(row.get("Start Date", ""))
            if not date:
                continue
            fields = _parse_description(row.get("Description", ""))
            title = row.get("Subject", "")
            title = title.rsplit("—", 1)[-1].strip() if "—" in title else title
            out.append({
                "date":   date,
                "title":  title,
                "course": fields.get("Course", ""),
                "type":   fields.get("Type", "other"),
                "weight": fields.get("Weight", ""),
            })
    return out


def read_schedule_csv(path: Path) -> List[Dict]:
    """Read weekly_schedule.csv back into time-block dicts."""
    if not path.exists():
        return []
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date = gc_date_to_iso(row.get("Start Date", ""))
            if not date:
                continue
            fields = _parse_description(row.get("Description", ""))
            out.append({
                "date":       date,
                "start_time": row.get("Start Time", ""),
                "end_time":   row.get("End Time", ""),
                "title":      row.get("Subject", ""),
                "type":       fields.get("Type", "other"),
                "course":     fields.get("Course", ""),
            })
    return out
