"""
SyllabOS Agent — main orchestrator.
Ties together file reading, NIM parsing, schedule building, and CSV export.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from display import (
    banner, div, log_t, log_p, log_g, log_a, log_r, log_gr,
    log_status, TEAL, RESET, BOLD, AMBER, GREEN, GRAY
)
from reader import extract_text, get_syllabus_files
from nim_client import (
    NIMError, parse_syllabus, parse_work_schedule,
    build_weekly_schedule, write_weekly_briefing
)
from schedule import (
    detect_conflicts, suggest_reschedules,
    get_upcoming_deadlines, map_blocks_to_dates, get_next_monday
)
from exporter import (
    export_weekly_schedule, export_deadlines, export_conflict_report,
    print_import_instructions
)


class SyllabOSAgent:

    def __init__(self, api_key: str, student_name: str = "Student",
                 student_email: str = "", output_dir: Path = None,
                 week_start: str = ""):
        self.api_key      = api_key
        self.name         = student_name
        self.email        = student_email
        self.output_dir   = output_dir or Path("output")
        self.week_start   = week_start or get_next_monday()

        self.all_deadlines: List[dict] = []
        self.work_shifts:   List[dict] = []
        self.conflicts:     List[dict] = []
        self.suggestions:   List[dict] = []
        self.blocks:        List[dict] = []

    # ── Entry point ────────────────────────────────────────────────────────────

    def run(self, folder: Path):
        banner(f"SyllabOS — Starting for {self.name}")
        log_t(f"Folder   : {folder}")
        log_t(f"Week of  : {self.week_start}")
        log_t(f"Output   : {self.output_dir}")
        div()

        files = get_syllabus_files(folder)
        if not files:
            log_r(f"No syllabus files found in {folder}")
            log_a("Supported formats: .pdf, .docx, .txt, .md")
            log_a("Drop your files there and re-run.")
            sys.exit(1)

        log_t(f"Found {len(files)} file(s):")
        for f in files:
            log_gr(f"  {f.name}")
        div()

        # Step 1 — Parse all syllabi
        self._parse_syllabi(files)

        # Step 2 — Check for work schedule in the same folder
        self._parse_work_schedule(folder)

        # Step 3 — Detect conflicts
        self._detect_conflicts()

        # Step 4 — Build time-blocked week
        self._build_schedule()

        # Step 5 — Export CSVs
        self._export()

        # Step 6 — Print summary
        self._summary()

    # ── Steps ──────────────────────────────────────────────────────────────────

    def _parse_syllabi(self, files: List[Path]):
        log_p("[Step 1/6] Parsing syllabi with NVIDIA NemoClaw…")
        div()

        for f in files:
            log_t(f"→ Reading: {f.name}")

            text = extract_text(f)

            if text is None:
                log_r(f"  ESCALATE — Cannot extract text from {f.name}")
                log_r(f"  Reason: File appears to be a scanned image or is empty.")
                log_r(f"  Fix: Re-upload as a text-based PDF, or paste the syllabus as a .txt file.")
                div()
                continue

            course_name = f.stem.replace("_", " ").replace("-", " ").title()

            try:
                deadlines = parse_syllabus(
                    self.api_key, text, course_name,
                    semester_start="2026-08-24",
                    semester_end="2026-12-12"
                )
                self.all_deadlines.extend(deadlines)
                exam_count = sum(1 for d in deadlines if d.get("type") == "exam")
                hw_count   = sum(1 for d in deadlines if d.get("type") == "homework")
                log_status("SUCCESS")
                log_gr(f"  {course_name}: {len(deadlines)} deadlines parsed | {exam_count} exams | {hw_count} homework")
            except NIMError as e:
                log_status("RETRY")
                log_a(f"  NIM error parsing {f.name}: {e}")
                log_a(f"  Skipping this file — re-run to retry.")
            except (ValueError, json.JSONDecodeError) as e:
                log_status("RETRY")
                log_a(f"  Could not parse response for {f.name}: {e}")
            div()

        if not self.all_deadlines:
            log_r("ESCALATE — No deadlines found across all files.")
            log_r("Check that your syllabus files contain readable text.")
            sys.exit(1)

        log_g(f"Total: {len(self.all_deadlines)} deadlines across all courses.")
        div()

    def _parse_work_schedule(self, folder: Path):
        log_p("[Step 2/6] Looking for work schedule…")

        # Common work schedule filenames
        work_filenames = [
            "work_schedule", "schedule", "starbucks", "work", "shifts",
            "my_schedule", "job_schedule", "part_time"
        ]

        work_file = None
        for f in folder.iterdir():
            stem = f.stem.lower().replace("-","_").replace(" ","_")
            if any(name in stem for name in work_filenames):
                work_file = f
                break

        if not work_file:
            log_gr("  No work schedule file found — building schedule without work shifts.")
            log_gr("  Tip: Add a file named 'work_schedule.txt' to your syllabi folder.")
            div()
            return

        log_t(f"→ Reading: {work_file.name}")
        text = extract_text(work_file)

        if not text:
            log_a(f"  Could not read {work_file.name} — skipping.")
            div()
            return

        try:
            self.work_shifts = parse_work_schedule(self.api_key, text)
            total_hours = sum(float(s.get("hours", 0)) for s in self.work_shifts)
            work_days   = [s.get("day", "") for s in self.work_shifts]
            log_status("SUCCESS")
            log_gr(f"  {len(self.work_shifts)} shifts/week | {total_hours:.0f} hrs/week | Days: {', '.join(work_days)}")
        except (NIMError, ValueError, json.JSONDecodeError) as e:
            log_a(f"  Could not parse work schedule: {e}")
            log_a(f"  Building schedule without work shifts.")
        div()

    def _detect_conflicts(self):
        log_p("[Step 3/6] Detecting conflict weeks…")

        self.conflicts   = detect_conflicts(self.all_deadlines, threshold=3)
        self.suggestions = suggest_reschedules(self.conflicts, [])

        if not self.conflicts:
            log_status("SUCCESS")
            log_gr(f"  No conflict weeks detected. Workload looks manageable.")
        else:
            log_status("SUCCESS")
            log_gr(f"  {len(self.conflicts)} conflict week(s) flagged:")
            for c in self.conflicts[:5]:
                severity_color = f"\033[38;5;196m" if c["severity"] == "HIGH" else f"\033[38;5;214m"
                log_gr(f"  {severity_color}  ⚠ {c['week_label']}: {c['deliverable_count']} deliverables "
                       f"({'includes exam' if c['has_exam'] else 'no exams'}, {c['severity']})\033[0m")
        div()

    def _build_schedule(self):
        log_p("[Step 4/6] Building your time-blocked week with NVIDIA NemoClaw…")
        log_gr(f"  Week of {self.week_start} | Wake: 07:00 | Sleep: 23:00")

        upcoming = get_upcoming_deadlines(self.all_deadlines, self.week_start, days_ahead=14)
        log_gr(f"  {len(upcoming)} deadlines in the next 14 days")

        try:
            raw_blocks   = build_weekly_schedule(
                self.api_key,
                student_name=self.name,
                week_start=self.week_start,
                deadlines=upcoming,
                work_shifts=self.work_shifts,
            )
            self.blocks = map_blocks_to_dates(raw_blocks, self.week_start)

            study_hours  = 0.0
            family_calls = 0
            free_blocks  = 0
            for b in self.blocks:
                if b.get("type") == "study":
                    try:
                        s = datetime.strptime(b["start_time"], "%H:%M")
                        e = datetime.strptime(b["end_time"],   "%H:%M")
                        study_hours += (e - s).seconds / 3600
                    except Exception:
                        pass
                if b.get("type") == "family":
                    family_calls += 1
                if b.get("type") in ("free", "social"):
                    free_blocks += 1

            log_status("SUCCESS")
            log_gr(f"  {len(self.blocks)} time blocks built across 7 days")
            log_gr(f"  Study hours planned: {study_hours:.0f}")
            log_gr(f"  Family call blocks: {family_calls}")
            log_gr(f"  Free/social blocks protected: {free_blocks}")

        except NIMError as e:
            log_r(f"ESCALATE — Could not build schedule: {e}")
            log_r("Check your NIM_API_KEY and internet connection.")
            sys.exit(1)
        except (ValueError, json.JSONDecodeError) as e:
            log_r(f"ESCALATE — Schedule response was malformed: {e}")
            sys.exit(1)
        div()

    def _export(self):
        log_p("[Step 5/6] Exporting CSV files for Google Calendar…")

        schedule_path  = export_weekly_schedule(self.blocks, self.output_dir, self.name)
        deadlines_path = export_deadlines(self.all_deadlines, self.output_dir)
        conflict_path  = export_conflict_report(self.conflicts, self.suggestions, self.output_dir)

        log_status("SUCCESS")
        log_gr(f"  {schedule_path.name}   — {len(self.blocks)} time blocks")
        log_gr(f"  {deadlines_path.name}  — {len(self.all_deadlines)} semester deadlines")
        log_gr(f"  {conflict_path.name}   — {len(self.conflicts)} conflict weeks")
        div()

    def _summary(self):
        log_p("[Step 6/6] Generating weekly briefing…")

        try:
            upcoming  = get_upcoming_deadlines(self.all_deadlines, self.week_start, days_ahead=14)
            briefing  = write_weekly_briefing(
                self.api_key,
                student_name=self.name,
                week_start=self.week_start,
                conflicts=self.conflicts[:3],
                suggestions=self.suggestions[:3],
                upcoming=upcoming,
            )
            log_status("SUCCESS")
        except Exception:
            briefing = (
                f"Your semester is organized. "
                f"{len(self.all_deadlines)} deadlines loaded. "
                f"{len(self.conflicts)} heavy weeks flagged. "
                f"Your weekly schedule is ready to import."
            )

        div()
        banner("SyllabOS Complete", width=64)
        print()
        print(f"{TEAL}  Your Weekly Briefing:{RESET}")
        print()
        for line in briefing.split("\n"):
            print(f"  {GRAY}{line}{RESET}")
        print()

        schedule_path  = self.output_dir / "weekly_schedule.csv"
        deadlines_path = self.output_dir / "semester_deadlines.csv"
        print_import_instructions(schedule_path, deadlines_path)

        # Print schedule preview
        self._print_schedule_preview()

    def _print_schedule_preview(self):
        if not self.blocks:
            return

        type_colors = {
            "study":  f"\033[38;5;43m",
            "work":   f"\033[38;5;214m",
            "sleep":  f"\033[38;5;245m",
            "social": f"\033[38;5;82m",
            "family": f"\033[38;5;135m",
            "meal":   f"\033[38;5;33m",
            "review": f"\033[38;5;196m",
            "free":   f"\033[38;5;82m",
            "org":    f"\033[38;5;135m",
        }

        banner("Your Week at a Glance", width=64)

        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        by_day = {d: [] for d in days}
        for b in self.blocks:
            day = b.get("day", "")
            if day in by_day:
                by_day[day].append(b)

        for day in days:
            day_blocks = sorted(by_day[day], key=lambda x: x.get("start_time", ""))
            if not day_blocks:
                continue
            print(f"\n  {BOLD}{day}{RESET}")
            for b in day_blocks:
                color = type_colors.get(b.get("type","other"), GRAY)
                print(f"  {color}{b.get('start_time','')}–{b.get('end_time','')}  {b.get('title','')}{RESET}")

        print()
        print(f"  {TEAL}Drop your syllabus. Get your life.{RESET}")
        print(f"  {GRAY}github.com/itsChanelML/syllabos{RESET}")
        print()