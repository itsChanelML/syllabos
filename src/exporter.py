"""
SyllabOS CSV exporter.
Produces Google Calendar-compatible CSV files that can be imported directly.

Google Calendar CSV format requires these columns:
  Subject, Start Date, Start Time, End Date, End Time,
  All Day Event, Description, Location, Private

Import instructions shown to student after export.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


# Google Calendar color name mapping (used in Description for reference)
COLOR_LABELS = {
    "teal":   "Sage",
    "purple": "Grape",
    "amber":  "Banana",
    "coral":  "Tomato",
    "green":  "Basil",
    "gray":   "Graphite",
    "pink":   "Flamingo",
}


def export_weekly_schedule(blocks: List[Dict], output_dir: Path,
                            student_name: str = "Student") -> Path:
    """
    Export time-blocked weekly schedule as Google Calendar CSV.
    Returns the path to the created CSV file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "weekly_schedule.csv"

    rows = []
    for block in blocks:
        date       = block.get("date", "")
        start_time = block.get("start_time", "09:00")
        end_time   = block.get("end_time",   "10:00")
        title      = block.get("title",      "SyllabOS Block")
        btype      = block.get("type",       "other")
        course     = block.get("course",     "")
        notes      = block.get("notes",      "")
        color      = block.get("color",      "gray")

        if not date:
            continue

        # Format date as MM/DD/YYYY for Google Calendar
        try:
            dt       = datetime.strptime(date, "%Y-%m-%d")
            gc_date  = dt.strftime("%m/%d/%Y")
        except ValueError:
            continue

        # Build description
        desc_parts = [f"Type: {btype}", "Added by SyllabOS"]
        if course:
            desc_parts.insert(0, f"Course: {course}")
        if notes:
            desc_parts.insert(0, notes)
        description = " | ".join(desc_parts)

        rows.append({
            "Subject":       title,
            "Start Date":    gc_date,
            "Start Time":    _fmt_time(start_time),
            "End Date":      gc_date,
            "End Time":      _fmt_time(end_time),
            "All Day Event": "False",
            "Description":   description,
            "Location":      "",
            "Private":       "False",
        })

    fieldnames = ["Subject", "Start Date", "Start Time", "End Date", "End Time",
                  "All Day Event", "Description", "Location", "Private"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def export_deadlines(deadlines: List[Dict], output_dir: Path) -> Path:
    """
    Export all semester deadlines as a reference CSV.
    Also formatted for Google Calendar import.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "semester_deadlines.csv"

    # Type to emoji mapping
    type_emoji = {
        "exam":     "🔴 EXAM",
        "homework": "📝 HW",
        "project":  "🔧 PROJECT",
        "quiz":     "⚡ QUIZ",
        "lab":      "🧪 LAB",
        "reading":  "📖 READING",
        "other":    "📌",
    }

    rows = []
    for d in deadlines:
        date   = d.get("date",  "")
        time   = d.get("time",  "23:59")
        title  = d.get("title", "")
        course = d.get("course","")
        dtype  = d.get("type",  "other")
        weight = d.get("weight","")
        notes  = d.get("notes", "")
        hours  = d.get("estimated_hours", 2)

        if not date or not title:
            continue

        try:
            dt      = datetime.strptime(date, "%Y-%m-%d")
            gc_date = dt.strftime("%m/%d/%Y")
        except ValueError:
            continue

        prefix   = type_emoji.get(dtype, "📌")
        subject  = f"{prefix}: {course} — {title}"

        desc_parts = [f"Course: {course}", f"Type: {dtype}"]
        if weight:
            desc_parts.append(f"Weight: {weight}")
        if notes:
            desc_parts.append(notes)
        desc_parts.append(f"Estimated study time: {hours} hour(s)")
        desc_parts.append("Added by SyllabOS")

        rows.append({
            "Subject":       subject,
            "Start Date":    gc_date,
            "Start Time":    _fmt_time(time),
            "End Date":      gc_date,
            "End Time":      _fmt_time(time),
            "All Day Event": "False",
            "Description":   " | ".join(desc_parts),
            "Location":      "",
            "Private":       "False",
        })

    fieldnames = ["Subject", "Start Date", "Start Time", "End Date", "End Time",
                  "All Day Event", "Description", "Location", "Private"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def export_conflict_report(conflicts: List[Dict], suggestions: List[Dict],
                            output_dir: Path) -> Path:
    """
    Export conflict weeks and reschedule suggestions as a readable CSV.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "conflict_report.csv"

    rows = []
    for c in conflicts:
        rows.append({
            "Week":         c.get("week_label", ""),
            "Severity":     c.get("severity", ""),
            "# Deliverables": c.get("deliverable_count", 0),
            "Has Exam":     "YES" if c.get("has_exam") else "NO",
            "Courses":      ", ".join(c.get("courses_affected", [])),
            "Items":        " | ".join(i.get("title","") for i in c.get("items",[])),
            "Action":       "Plan ahead — start work early in the week before",
        })

    for s in suggestions:
        rows.append({
            "Week":         s.get("current_week", ""),
            "Severity":     s.get("severity", ""),
            "# Deliverables": "",
            "Has Exam":     "",
            "Courses":      "",
            "Items":        f"RESCHEDULE: {s.get('event_title','')} on {s.get('event_date','')}",
            "Action":       s.get("suggestion", ""),
        })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Week","Severity","# Deliverables","Has Exam","Courses","Items","Action"])
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def _fmt_time(time_str: str) -> str:
    """
    Convert HH:MM to 12-hour format for Google Calendar CSV.
    e.g. "14:00" → "2:00 PM"
    """
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        return dt.strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return time_str


def print_import_instructions(schedule_path: Path, deadlines_path: Path):
    """Print clear instructions for importing CSVs to Google Calendar."""
    from display import banner, log_t, log_gr, TEAL, RESET, BOLD, GRAY

    print()
    banner("How to Import to Google Calendar")
    print(f"""
{TEAL}Your schedule is ready. Follow these steps to get it into Google Calendar:{RESET}

{BOLD}Step 1 — Open Google Calendar{RESET}
  Go to calendar.google.com in your browser.

{BOLD}Step 2 — Import your weekly schedule{RESET}
  Click the ⚙ gear icon (top right) → Settings
  Click "Import & Export" in the left sidebar
  Click "Select file from your computer"
  Choose: {TEAL}{schedule_path}{RESET}
  Select which calendar to add events to (your main calendar is fine)
  Click Import

{BOLD}Step 3 — Import your semester deadlines{RESET}
  Repeat Step 2 with: {TEAL}{deadlines_path}{RESET}

{BOLD}Done.{RESET} Your entire semester is now in Google Calendar.
All events include descriptions with course info and reminders context.

{GRAY}Tip: After importing, select all events and add a reminder
     (right-click → Edit → More Options → Add notification){RESET}
""")