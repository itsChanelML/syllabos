"""
SyllaClaw NIM client.
All NVIDIA API calls go through here.
One model. One key. Everything runs through this file.
"""

import json
import re
import time
from typing import Any, Optional

import requests

MODEL    = "meta/llama-3.2-90b-vision-instruct"
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
TIMEOUTS = [120, 150, 180]


class NIMError(Exception):
    pass


def _call(api_key: str, prompt: str, max_tokens: int = 2000,
          temperature: float = 0.1, system: str = "") -> str:
    """
    Make a direct NIM completion call.
    Retries with increasing timeouts on failure.
    Returns the raw text response.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       MODEL,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }

    last_error = None
    for attempt, timeout in enumerate(TIMEOUTS, 1):
        try:
            r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            last_error = f"Timeout after {timeout}s"
            if attempt < len(TIMEOUTS):
                time.sleep(3)
        except requests.exceptions.HTTPError as e:
            raise NIMError(f"NIM API error: {e}")
        except Exception as e:
            raise NIMError(f"Unexpected error: {e}")

    raise NIMError(f"NIM failed after {len(TIMEOUTS)} attempts: {last_error}")


def extract_json(raw: str) -> Any:
    """
    Extract JSON from a NIM response.
    Handles markdown fences and surrounding text.
    """
    # Strip markdown fences
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*",     "", raw).strip()

    # Find outermost JSON structure
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = raw.find(start_char)
        end   = raw.rfind(end_char) + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                continue

    raise json.JSONDecodeError("No valid JSON found", raw, 0)


def parse_syllabus(api_key: str, syllabus_text: str, course_name: str,
                   semester_start: str = "2026-01-12",
                   semester_end: str   = "2026-05-15") -> list:
    """
    Extract structured deadlines from a syllabus.
    Returns a list of deadline dicts.
    """
    prompt = f"""Extract every graded item and deadline from this syllabus.
Semester: {semester_start} to {semester_end}.
Course: {course_name}

Return a JSON array only. Each item must have exactly these fields:
- course: "{course_name}"
- title: short name (e.g. "Homework 1", "Midterm Exam", "Project Proposal")
- date: YYYY-MM-DD. If only a week number is given, use the Friday of that week.
- time: HH:MM if specified, else "23:59"
- type: exactly one of: homework | exam | project | quiz | lab | reading | other
- weight: grading % if mentioned (e.g. "20%"), else ""
- estimated_hours: realistic study/work hours needed as an integer (1–20)
- notes: key context (e.g. "closed book", "team project"), else ""

Return ONLY the JSON array. No explanation. No markdown. No code fences.

SYLLABUS TEXT:
{syllabus_text[:6000]}"""

    raw  = _call(api_key, prompt, max_tokens=2000, temperature=0.1)
    data = extract_json(raw)

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of deadlines")

    # Sort by date
    data.sort(key=lambda x: x.get("date", "9999-12-31"))
    return data


def parse_work_schedule(api_key: str, schedule_text: str) -> list:
    """
    Extract weekly work shifts from a schedule file.
    Returns a list of shift dicts.
    """
    prompt = f"""Extract the work schedule from this text as a JSON array.

Each shift must have:
- day: full day name (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
- start_time: HH:MM in 24-hour format
- end_time: HH:MM in 24-hour format
- hours: float (duration in hours)
- title: "Work Shift" or employer name if visible
- type: "work"

Return ONLY the JSON array. No explanation. No markdown.

SCHEDULE:
{schedule_text}"""

    raw  = _call(api_key, prompt, max_tokens=600, temperature=0.1)
    data = extract_json(raw)

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of shifts")

    return data


DAY_NAMES         = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FAMILY_CALL_DAYS  = {"Monday", "Thursday"}
PROTECTED_FREE_DAY = "Saturday"


def _build_day_schedule(api_key: str, student_name: str, day_name: str, day_date: str,
                         deadlines: list, day_shifts: list, student_orgs: list,
                         wake_time: str, sleep_time: str,
                         include_family_call: bool, include_protected_free: bool,
                         include_weekly_review: bool) -> list:
    """
    Build one day's time blocks. Called once per day by build_weekly_schedule
    so each NIM call stays small and fast instead of one call for the whole week.
    """
    from datetime import datetime

    deadlines_str = ""
    for d in deadlines[:20]:
        try:
            due = datetime.strptime(d.get("date",""), "%Y-%m-%d")
            today = datetime.strptime(day_date, "%Y-%m-%d")
            days_away = (due - today).days
            if days_away < 0:
                continue
            urgency = f" ⚠ DUE IN {days_away} DAYS" if days_away <= 7 else (f" (due in {days_away} days)" if days_away <= 14 else "")
        except Exception:
            urgency = ""
        deadlines_str += (
            f"- {d.get('course','')}: {d.get('title','')} | "
            f"Due: {d.get('date','')} | Type: {d.get('type','')} | "
            f"Est. hours: {d.get('estimated_hours', 2)}{urgency}\n"
        )

    shifts_str = "\n".join(
        f"- {s.get('start_time','')} – {s.get('end_time','')} ({s.get('hours',0)} hrs)"
        for s in day_shifts
    ) or "No work shift today"

    orgs_str = "\n".join(f"- {o}" for o in student_orgs) or "None"

    extra_rules = []
    if include_family_call:
        extra_rules.append('Add exactly one 10-minute family call block today, title: "Call home 📱".')
    if include_protected_free:
        extra_rules.append('Protect one 2-hour completely free/social block today — title "Free time — protect this".')
    else:
        extra_rules.append("Protect at least one free/social block today if it's not a full work day.")
    if include_weekly_review:
        extra_rules.append('Add a "Weekly Review" block this evening — 30 minutes to plan next week.')
    extra_rules_str = "\n".join(f"{i+7}. {r}" for i, r in enumerate(extra_rules))

    prompt = f"""You are a smart academic advisor building ONE DAY of a college student's weekly schedule.

Student: {student_name}
Day: {day_name}, {day_date}
Wake time: {wake_time}
Bedtime: {sleep_time}

UPCOMING DEADLINES (from today onward):
{deadlines_str or "None in the next two weeks"}

WORK SHIFT TODAY (non-negotiable — never schedule anything during this):
{shifts_str}

STUDENT ORGANIZATIONS:
{orgs_str}

RULES:
1. Work shift is locked — never overlap it
2. Sleep is locked — nothing before wake time or after bedtime
3. Study blocks: use 25-min Pomodoro for memorization/reading, 90-min deep work for problem sets/projects
4. Prioritize study time for items due soonest
5. If an exam is due tomorrow, add a review session this evening
6. Add meals: Breakfast 30 min, Lunch 45 min, Dinner 45 min
{extra_rules_str}

Return a JSON array of time blocks for TODAY ONLY. Each block:
- start_time: HH:MM (24-hour)
- end_time: HH:MM (24-hour)
- title: descriptive name (e.g. "Study: Thermo Problem Set 3", "Call home 📱", "Free time — protect this")
- type: study | work | sleep | social | family | meal | review | free | org
- course: course name if study block, else ""
- notes: one short coaching tip if relevant, else ""
- color: one of: teal | purple | amber | coral | green | gray | pink

Color guide: study=teal, work=amber, sleep=gray, social=green, family=purple, meal=pink, review=coral, free=green

Return ONLY the JSON array. Cover every hour from {wake_time} to {sleep_time}.
Do not leave unaccounted time gaps longer than 30 minutes."""

    raw  = _call(api_key, prompt, max_tokens=1500, temperature=0.15)
    data = extract_json(raw)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array of time blocks for {day_name}")

    return data


def build_weekly_schedule(api_key: str, student_name: str, week_start: str,
                           deadlines: list, work_shifts: list,
                           student_orgs: list = None,
                           wake_time: str = "07:00",
                           sleep_time: str = "23:00") -> list:
    """
    Build a complete time-blocked weekly schedule.
    Builds one day at a time (7 smaller NIM calls) instead of one call for the
    whole week — the full-week prompt is too large for the model to complete
    reliably before timing out.
    Returns a list of time block dicts.
    """
    from datetime import datetime, timedelta

    student_orgs  = student_orgs or []
    week_start_dt = datetime.strptime(week_start, "%Y-%m-%d")

    all_blocks = []
    for i, day_name in enumerate(DAY_NAMES):
        day_date   = (week_start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        day_shifts = [s for s in work_shifts if s.get("day") == day_name]

        day_blocks = _build_day_schedule(
            api_key, student_name, day_name, day_date,
            deadlines, day_shifts, student_orgs, wake_time, sleep_time,
            include_family_call=day_name in FAMILY_CALL_DAYS,
            include_protected_free=(day_name == PROTECTED_FREE_DAY),
            include_weekly_review=(day_name == "Sunday"),
        )
        for b in day_blocks:
            b["day"] = day_name

        all_blocks.extend(day_blocks)

    return all_blocks


def write_weekly_briefing(api_key: str, student_name: str, week_start: str,
                           conflicts: list, suggestions: list,
                           upcoming: list) -> str:
    """
    Write a personalized Sunday evening briefing message.
    Returns the message as plain text.
    """
    upcoming_str = "\n".join(
        f"- {d.get('course','')}: {d.get('title','')} due {d.get('date','')}"
        + (" [EXAM]" if d.get("type") == "exam" else "")
        for d in upcoming[:8]
    ) or "Nothing major due in the next 2 weeks."

    conflict_str = "\n".join(
        f"- {c.get('week_label','')}: {c.get('deliverable_count','')} things due ({c.get('severity','')} week)"
        for c in conflicts[:3]
    ) or "No overloaded weeks detected."

    suggestion_str = "\n".join(
        f"- {s.get('event_title','')}: {s.get('suggestion','')}"
        for s in suggestions[:3]
    ) or "No reschedule suggestions."

    prompt = f"""Write a Sunday evening weekly briefing for {student_name}.

Week of: {week_start}

UPCOMING DEADLINES (next 14 days):
{upcoming_str}

WORKLOAD CONFLICTS:
{conflict_str}

RESCHEDULE SUGGESTIONS:
{suggestion_str}

Rules for the message:
- Address them by first name: {student_name.split()[0] if student_name else 'hey'}
- Be direct and honest — don't sugarcoat heavy weeks
- Give one clear priority recommendation for the week
- If there are reschedule suggestions, mention them conversationally
- Sound like a smart friend who actually looked at their schedule
- Keep it under 180 words
- Write in paragraphs — no bullet points
- End with one sentence of encouragement
- Do NOT use a subject line or greeting header

Return only the message text."""

    return _call(api_key, prompt, max_tokens=500, temperature=0.4)