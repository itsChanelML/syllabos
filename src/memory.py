"""
SyllabOS student memory — learns how you actually live.

Stores a student_profile.json that gets updated every Sunday
when the student runs: python3 syllabos.py --checkin

The profile tracks:
- Study block completion rates by time of day and day of week
- Which block types get skipped most
- Known schedule overruns (job always runs late, etc.)
- Commitment reliability (orgs, social events)
- Preferred study style based on observed behavior

This data feeds back into time_block_week so the schedule
gets smarter every week — not just the first time.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROFILE_FILE = Path(__file__).parent.parent / "output" / "student_profile.json"


def load_profile(student_name: str = "Student") -> Dict:
    """Load existing profile or create a fresh one."""
    if PROFILE_FILE.exists():
        try:
            return json.loads(PROFILE_FILE.read_text())
        except Exception:
            pass

    return {
        "student_name":       student_name,
        "created":            datetime.now().isoformat(),
        "last_updated":       datetime.now().isoformat(),
        "weeks_tracked":      0,

        # What time of day does this student actually study?
        "productive_times": {
            "morning":   0,   # 6am–12pm completions
            "afternoon": 0,   # 12pm–6pm completions
            "evening":   0,   # 6pm–10pm completions
            "night":     0,   # 10pm+ completions
        },

        # Which days have the highest study completion?
        "productive_days": {
            "Monday": 0, "Tuesday": 0, "Wednesday": 0,
            "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0,
        },

        # Block type completion rates (0.0 – 1.0)
        "completion_rates": {
            "study_deep_work":  [],   # 90-min blocks
            "study_pomodoro":   [],   # 25-min blocks
            "review":           [],
            "free":             [],
            "social":           [],
            "family":           [],
        },

        # Known overruns — job always runs late, etc.
        "known_overruns": [],

        # New commitments added since last run
        "new_commitments": [],

        # What got skipped most often
        "frequently_skipped": [],

        # Inferred preferences
        "inferred_preferences": {
            "study_style":      "mixed",     # pomodoro | deep_work | mixed
            "best_study_time":  "morning",   # morning | afternoon | evening | night
            "buffer_needed":    15,          # minutes to add around work shifts
            "social_priority":  "moderate",  # low | moderate | high
        },

        # Weekly check-in history
        "checkin_history": [],
    }


def save_profile(profile: Dict):
    """Save profile to disk."""
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    profile["last_updated"] = datetime.now().isoformat()
    PROFILE_FILE.write_text(json.dumps(profile, indent=2))


def run_checkin(profile: Dict) -> Dict:
    """
    Run the Sunday evening check-in.
    Asks 5 quick questions and updates the profile.
    Returns the updated profile.
    """
    from display import banner, log_t, log_p, log_g, log_gr, TEAL, PURPLE, GREEN, AMBER, RESET, BOLD, GRAY

    banner("SyllabOS — Weekly Check-In")
    print(f"{GRAY}Five quick questions. Takes 2 minutes.{RESET}\n")

    checkin = {
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "completed_blocks": [],
        "skipped_blocks":   [],
        "new_commitments":  [],
        "overruns":         [],
        "notes":            "",
    }

    # Q1 — What study blocks did you actually complete?
    print(f"{TEAL}1. Which study blocks did you actually complete this week?{RESET}")
    print(f"{GRAY}   Enter time slots (e.g. 'Monday 9am, Wednesday 7pm') or press Enter to skip:{RESET}")
    completed = input(f"   {TEAL}>{RESET} ").strip()
    if completed:
        checkin["completed_blocks"] = [b.strip() for b in completed.split(",")]
        print(f"   {GREEN}✓ Logged{RESET}\n")

    # Q2 — What got skipped?
    print(f"{TEAL}2. What study blocks did you skip or miss?{RESET}")
    print(f"{GRAY}   Same format — or press Enter to skip:{RESET}")
    skipped = input(f"   {TEAL}>{RESET} ").strip()
    if skipped:
        checkin["skipped_blocks"] = [b.strip() for b in skipped.split(",")]
        # Update frequently skipped list
        for block in checkin["skipped_blocks"]:
            existing = next((x for x in profile["frequently_skipped"] if x["block"] == block), None)
            if existing:
                existing["count"] += 1
            else:
                profile["frequently_skipped"].append({"block": block, "count": 1})
        print(f"   {GREEN}✓ Logged{RESET}\n")

    # Q3 — Any new commitments next week?
    print(f"{TEAL}3. Any new commitments coming up next week?{RESET}")
    print(f"{GRAY}   (e.g. 'SHPE meeting Tuesday 6pm', 'extra Starbucks shift Saturday') or Enter to skip:{RESET}")
    new_commits = input(f"   {TEAL}>{RESET} ").strip()
    if new_commits:
        checkin["new_commitments"] = [c.strip() for c in new_commits.split(",")]
        profile["new_commitments"] = checkin["new_commitments"]
        print(f"   {GREEN}✓ Logged{RESET}\n")

    # Q4 — Did any shifts or classes run over?
    print(f"{TEAL}4. Did your job or any classes run over their scheduled time?{RESET}")
    print(f"{GRAY}   (e.g. 'Starbucks always runs 30 min late') or Enter to skip:{RESET}")
    overruns = input(f"   {TEAL}>{RESET} ").strip()
    if overruns:
        checkin["overruns"] = [o.strip() for o in overruns.split(",")]
        for overrun in checkin["overruns"]:
            if overrun not in profile["known_overruns"]:
                profile["known_overruns"].append(overrun)
        print(f"   {GREEN}✓ Logged — SyllabOS will add buffer time around these{RESET}\n")

    # Q5 — Anything else?
    print(f"{TEAL}5. Anything you want SyllabOS to know for next week?{RESET}")
    print(f"{GRAY}   Free text — or press Enter to skip:{RESET}")
    notes = input(f"   {TEAL}>{RESET} ").strip()
    if notes:
        checkin["notes"] = notes
        print(f"   {GREEN}✓ Noted{RESET}\n")

    # Update inferred preferences based on history
    profile = _update_preferences(profile, checkin)

    # Save checkin to history
    profile["checkin_history"].append(checkin)
    profile["weeks_tracked"] += 1

    save_profile(profile)

    # Summary
    print(f"\n{TEAL}{'─'*54}{RESET}")
    print(f"{BOLD}{TEAL}  Check-in complete. Week {profile['weeks_tracked']} logged.{RESET}")
    print(f"{TEAL}{'─'*54}{RESET}")
    print()

    prefs = profile["inferred_preferences"]
    print(f"{GRAY}  What SyllabOS learned about you so far:{RESET}")
    print(f"  Best study time  : {TEAL}{prefs['best_study_time']}{RESET}")
    print(f"  Study style      : {TEAL}{prefs['study_style']}{RESET}")
    print(f"  Buffer needed    : {TEAL}{prefs['buffer_needed']} min around work shifts{RESET}")

    if profile["frequently_skipped"]:
        top_skipped = sorted(profile["frequently_skipped"], key=lambda x: x["count"], reverse=True)[:2]
        print(f"  Often skipped    : {AMBER}{', '.join(s['block'] for s in top_skipped)}{RESET}")
        print(f"  {GRAY}SyllabOS will reschedule these to better times next week.{RESET}")

    if profile["new_commitments"]:
        print(f"  New commitments  : {PURPLE}{', '.join(profile['new_commitments'])}{RESET}")
        print(f"  {GRAY}These will be blocked in next week's schedule.{RESET}")

    print()
    print(f"  {TEAL}Run python3 syllabos.py to build next week's schedule.{RESET}")
    print()

    return profile


def _update_preferences(profile: Dict, checkin: Dict) -> Dict:
    """
    Infer study preferences from check-in data.
    Updates inferred_preferences based on patterns across weeks.
    """
    prefs = profile["inferred_preferences"]

    # Infer best study time from completed blocks
    time_hits = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    for block in checkin.get("completed_blocks", []):
        block_lower = block.lower()
        try:
            # Try to extract hour from block description
            import re
            hour_match = re.search(r'(\d+)(am|pm)', block_lower)
            if hour_match:
                hour = int(hour_match.group(1))
                suffix = hour_match.group(2)
                if suffix == "pm" and hour != 12:
                    hour += 12
                if 6 <= hour < 12:
                    time_hits["morning"] += 1
                    profile["productive_times"]["morning"] += 1
                elif 12 <= hour < 18:
                    time_hits["afternoon"] += 1
                    profile["productive_times"]["afternoon"] += 1
                elif 18 <= hour < 22:
                    time_hits["evening"] += 1
                    profile["productive_times"]["evening"] += 1
                else:
                    time_hits["night"] += 1
                    profile["productive_times"]["night"] += 1
        except Exception:
            pass

    # Update best study time if we have enough data
    total_productive = sum(profile["productive_times"].values())
    if total_productive >= 3:
        best = max(profile["productive_times"], key=profile["productive_times"].get)
        prefs["best_study_time"] = best

    # Infer buffer needed from overruns
    if checkin.get("overruns"):
        # If overruns are mentioned, add 15 minutes buffer
        prefs["buffer_needed"] = min(prefs.get("buffer_needed", 15) + 15, 45)

    # Infer study style from skip patterns
    # If deep work blocks are frequently skipped, switch to pomodoro
    skipped = [s["block"].lower() for s in profile.get("frequently_skipped", [])]
    deep_work_skips  = sum(1 for s in skipped if "deep work" in s or "90" in s)
    pomodoro_skips   = sum(1 for s in skipped if "pomodoro" in s or "25" in s)

    if deep_work_skips > 2 and pomodoro_skips == 0:
        prefs["study_style"] = "pomodoro"
    elif pomodoro_skips > 2 and deep_work_skips == 0:
        prefs["study_style"] = "deep_work"
    else:
        prefs["study_style"] = "mixed"

    profile["inferred_preferences"] = prefs
    return profile


def get_profile_context(profile: Dict) -> str:
    """
    Format profile data as context for NIM prompt injection.
    This gets passed into time_block_week so the schedule
    reflects learned behavior, not just defaults.
    """
    if not profile or profile.get("weeks_tracked", 0) == 0:
        return ""

    prefs    = profile.get("inferred_preferences", {})
    skipped  = profile.get("frequently_skipped", [])
    overruns = profile.get("known_overruns", [])
    new_commits = profile.get("new_commitments", [])

    lines = [f"LEARNED STUDENT BEHAVIOR (from {profile['weeks_tracked']} week(s) of check-ins):"]

    if prefs.get("best_study_time"):
        lines.append(f"- Best study time: {prefs['best_study_time']} — schedule deep work blocks here")
    if prefs.get("study_style"):
        lines.append(f"- Preferred study style: {prefs['study_style']}")
    if prefs.get("buffer_needed", 0) > 15:
        lines.append(f"- Add {prefs['buffer_needed']} min buffer after work shifts — they tend to run over")
    if skipped:
        top = sorted(skipped, key=lambda x: x["count"], reverse=True)[:2]
        lines.append(f"- Frequently skipped: {', '.join(s['block'] for s in top)} — reschedule to better times")
    if overruns:
        lines.append(f"- Known overruns: {', '.join(overruns[:2])}")
    if new_commits:
        lines.append(f"- New commitments next week: {', '.join(new_commits)}")

    return "\n".join(lines)