"""
Gathers today's briefing facts (calendar, deadlines, study time, workload
risk), renders them into a short spoken message via NVIDIA NIM, and hands
the result to a TextToSpeech provider (or just prints it).

Nothing in here invents data: every fact comes from the live Google
Calendar, SyllabOS's own exported CSVs, or — in --demo mode — a clearly
labeled synthetic fixture. If NIM itself fails, render_fallback_text()
produces a deterministic message built only from the same gathered facts.
"""

import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from calendar_source import get_today_events
from csv_utils import read_deadlines_csv, read_schedule_csv
from display import GRAY, RESET, banner, log_a, log_gr
from nim_client import NIMError, write_morning_briefing
from schedule import detect_conflicts, get_upcoming_deadlines
from voice.errors import VoiceError


@dataclass
class BriefingData:
    today_label: str
    today_iso: str
    timezone: str
    events_today: List[Dict]
    calendar_source: str
    calendar_warning: Optional[str]
    deadlines_upcoming: List[Dict]
    deadlines_warning: Optional[str]
    study_blocks_today: List[Dict]
    study_warning: Optional[str]
    overload: Dict = field(default_factory=lambda: {"is_overloaded": False})
    generated_at: str = ""


def _today_label(now: datetime, suffix: str = "") -> str:
    return now.strftime("%A, %B ") + str(now.day) + suffix


def gather_study_blocks_today(output_dir: Path, tz_name: str):
    path = output_dir / "weekly_schedule.csv"
    if not path.exists():
        return [], ("No weekly_schedule.csv found — run python3 syllabos.py first to "
                     "build your study schedule.")

    today = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")
    all_blocks = read_schedule_csv(path)
    todays = [b for b in all_blocks if b["date"] == today]
    study_blocks = [b for b in todays if b["type"] == "study"]

    if not todays:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=ZoneInfo(tz_name))
        return [], (f"Your exported schedule doesn't include today ({mtime:%B %d} export) "
                     "— it may be for a different week. Re-run python3 syllabos.py to refresh it.")

    return sorted(study_blocks, key=lambda b: b["start_time"]), None


def gather_deadlines_upcoming(output_dir: Path, tz_name: str, days_ahead: int = 7):
    path = output_dir / "semester_deadlines.csv"
    if not path.exists():
        return [], ("No semester_deadlines.csv found — run python3 syllabos.py first to "
                     "load your syllabi.")

    today = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")
    all_deadlines = read_deadlines_csv(path)
    upcoming = get_upcoming_deadlines(all_deadlines, today, days_ahead=days_ahead)
    return upcoming, None


def gather_overload_assessment(output_dir: Path, tz_name: str):
    path = output_dir / "semester_deadlines.csv"
    if not path.exists():
        return {"is_overloaded": False}, "No semester_deadlines.csv found — can't assess workload yet."

    all_deadlines = read_deadlines_csv(path)
    conflicts = detect_conflicts(all_deadlines, threshold=3)

    now = datetime.now(ZoneInfo(tz_name))
    this_week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    next_week_start = (now - timedelta(days=now.weekday()) + timedelta(days=7)).strftime("%Y-%m-%d")
    relevant = [c for c in conflicts if c["week_start"] in (this_week_start, next_week_start)]

    if not relevant:
        return {"is_overloaded": False}, None

    worst = max(relevant, key=lambda c: (c["severity"] == "HIGH", c["deliverable_count"]))
    reason = f"{worst['week_label']} has {worst['deliverable_count']} things due" + (
        " including an exam" if worst["has_exam"] else ""
    )
    return {"is_overloaded": True, "reason": reason, "severity": worst["severity"]}, None


def build_briefing_data(output_dir: Path, tz_name: str, creds_path: Path, token_path: Path) -> BriefingData:
    now = datetime.now(ZoneInfo(tz_name))
    cal = get_today_events(output_dir, tz_name, creds_path, token_path)
    study_blocks, study_warning = gather_study_blocks_today(output_dir, tz_name)
    deadlines, deadlines_warning = gather_deadlines_upcoming(output_dir, tz_name)
    overload, overload_warning = gather_overload_assessment(output_dir, tz_name)

    return BriefingData(
        today_label=_today_label(now),
        today_iso=now.strftime("%Y-%m-%d"),
        timezone=tz_name,
        events_today=cal.events,
        calendar_source=cal.source,
        calendar_warning=cal.warning,
        deadlines_upcoming=deadlines,
        deadlines_warning=deadlines_warning or overload_warning,
        study_blocks_today=study_blocks,
        study_warning=study_warning,
        overload=overload,
        generated_at=now.isoformat(),
    )


def build_demo_briefing_data(tz_name: str) -> BriefingData:
    """
    Synthetic, clearly-labeled sample data for workshop demos — never a
    student's real calendar. Dates are computed relative to "now" so the
    demo reads sensibly no matter what day it's run on.
    """
    now = datetime.now(ZoneInfo(tz_name))
    d = lambda days: (now + timedelta(days=days)).strftime("%Y-%m-%d")

    events_today = [
        {"start": "10:00 AM", "end": "11:15 AM", "title": "CS4820 Machine Learning — Lecture", "all_day": False},
        {"start": "2:00 PM",  "end": "3:15 PM",  "title": "ENGR3450 Thermodynamics — Lecture", "all_day": False},
        {"start": "6:00 PM",  "end": "9:00 PM",  "title": "Work Shift", "all_day": False},
    ]
    study_blocks_today = [
        {"start_time": "8:00 AM", "end_time": "9:00 AM", "title": "Study: CS4820 Reading Quiz 1"},
        {"start_time": "4:00 PM", "end_time": "5:30 PM", "title": "Study: ENGR3450 Problem Set 3"},
    ]
    deadlines_upcoming = [
        {"course": "CS4820 Machine Learning", "title": "Programming Assignment 1", "date": d(2), "type": "homework"},
        {"course": "ENGR3450 Thermodynamics", "title": "Midterm Exam", "date": d(4), "type": "exam"},
        {"course": "CS4820 Machine Learning", "title": "Reading Quiz 2", "date": d(6), "type": "quiz"},
    ]
    overload = {
        "is_overloaded": True,
        "reason": (f"the week of {(now + timedelta(days=4)):%B %d} has 3 things due, "
                   "including an exam"),
        "severity": "HIGH",
    }

    return BriefingData(
        today_label=_today_label(now, suffix=" (sample demo data)"),
        today_iso=now.strftime("%Y-%m-%d"),
        timezone=tz_name,
        events_today=events_today,
        calendar_source="demo_sample",
        calendar_warning="This is sample workshop data, not a real calendar.",
        deadlines_upcoming=deadlines_upcoming,
        deadlines_warning=None,
        study_blocks_today=study_blocks_today,
        study_warning=None,
        overload=overload,
        generated_at=now.isoformat(),
    )


def render_briefing_text(api_key: str, student_name: str, data: BriefingData) -> str:
    try:
        return write_morning_briefing(
            api_key, student_name, data.today_label,
            data.events_today, data.calendar_source, data.calendar_warning,
            data.deadlines_upcoming, data.deadlines_warning,
            data.study_blocks_today, data.study_warning,
            data.overload,
        )
    except NIMError:
        return render_fallback_text(student_name, data)


def render_fallback_text(student_name: str, data: BriefingData) -> str:
    """Deterministic, template-based briefing — used if the NIM call fails."""
    first = student_name.split()[0] if student_name else "there"
    lines = [f"Good morning, {first}. Here's {data.today_label}."]

    if data.events_today:
        ev = "; ".join(f"{e['start']} {e['title']}".strip() for e in data.events_today[:5])
        lines.append(f"On your calendar today: {ev}.")
    else:
        lines.append("Nothing on your calendar today.")

    if data.study_blocks_today:
        st = "; ".join(f"{b['start_time']}-{b['end_time']} {b['title']}" for b in data.study_blocks_today)
        lines.append(f"Study time today: {st}.")
    else:
        lines.append("No study blocks scheduled today.")

    if data.deadlines_upcoming:
        dl = "; ".join(f"{d['course']} {d['title']} due {d['date']}" for d in data.deadlines_upcoming[:4])
        lines.append(f"Coming up: {dl}.")
    else:
        lines.append("Nothing due in the next 7 days.")

    if data.overload.get("is_overloaded"):
        lines.append(f"Heads up — {data.overload['reason']}.")
    else:
        lines.append("The coming week looks manageable.")

    for w in (data.calendar_warning, data.deadlines_warning, data.study_warning):
        if w:
            lines.append(w.split("\n")[0])

    lines.append("Have a good one.")
    return " ".join(lines)


def speak_or_print(text: str, tts, tts_warning: Optional[str], text_only: bool):
    banner("Your Morning Briefing")
    print()
    for line in textwrap.wrap(text, width=76):
        print(f"  {GRAY}{line}{RESET}")
    print()

    if text_only:
        log_gr("  (--text-only — not speaking this aloud)")
        return

    if tts_warning:
        log_a(tts_warning)

    if tts is None:
        log_a("No speech output available — showing text only.")
        return

    try:
        tts.speak(text)
    except VoiceError as e:
        log_a(f"Could not speak the briefing aloud: {e}")
        log_a("Showing text only.")


def run_morning_briefing(api_key: str, student_name: str, output_dir: Path, tz_name: str,
                          tts, tts_warning: Optional[str], text_only: bool,
                          demo: bool = False, creds_path: Optional[Path] = None,
                          token_path: Optional[Path] = None):
    data = (
        build_demo_briefing_data(tz_name) if demo
        else build_briefing_data(output_dir, tz_name, creds_path, token_path)
    )
    text = render_briefing_text(api_key, student_name, data)
    speak_or_print(text, tts, tts_warning, text_only)
    return data, text
