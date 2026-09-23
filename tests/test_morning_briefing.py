import csv
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import _pathfix  # noqa: F401

from morning_briefing import (
    BriefingData,
    build_demo_briefing_data,
    gather_deadlines_upcoming,
    gather_overload_assessment,
    gather_study_blocks_today,
    render_fallback_text,
)

TZ = "UTC"
DEADLINE_FIELDNAMES = ["Subject", "Start Date", "Start Time", "End Date", "End Time",
                       "All Day Event", "Description", "Location", "Private"]


def _write_deadlines_csv(path: Path, deadlines):
    """deadlines: list of (course, title, type, date_offset_days, weight)"""
    today = datetime.now(ZoneInfo(TZ))
    rows = []
    for course, title, dtype, offset, weight in deadlines:
        date_str = (today + timedelta(days=offset)).strftime("%m/%d/%Y")
        desc = f"Course: {course} | Type: {dtype}"
        if weight:
            desc += f" | Weight: {weight}"
        rows.append({
            "Subject": f"{dtype.upper()}: {course} — {title}",
            "Start Date": date_str, "Start Time": "11:59 PM",
            "End Date": date_str, "End Time": "11:59 PM",
            "All Day Event": "False", "Description": desc + " | Added by SyllabOS",
            "Location": "", "Private": "False",
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DEADLINE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class TestGatherDeadlinesUpcoming(unittest.TestCase):
    def test_missing_file_returns_warning_not_fabricated_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            deadlines, warning = gather_deadlines_upcoming(Path(tmp), TZ)
        self.assertEqual(deadlines, [])
        self.assertIsNotNone(warning)

    def test_only_returns_deadlines_within_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _write_deadlines_csv(tmp / "semester_deadlines.csv", [
                ("CS4820", "HW1", "homework", 2, "10%"),
                ("CS4820", "Final", "exam", 60, "40%"),   # far outside the 7-day window
            ])
            deadlines, warning = gather_deadlines_upcoming(tmp, TZ, days_ahead=7)

        self.assertIsNone(warning)
        titles = [d["title"] for d in deadlines]
        self.assertIn("HW1", titles)
        self.assertNotIn("Final", titles)


class TestGatherOverloadAssessment(unittest.TestCase):
    def test_light_week_is_not_overloaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _write_deadlines_csv(tmp / "semester_deadlines.csv", [
                ("CS4820", "HW1", "homework", 2, "10%"),
            ])
            overload, warning = gather_overload_assessment(tmp, TZ)

        self.assertFalse(overload["is_overloaded"])

    def test_heavy_week_with_exam_is_flagged_high(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # 3+ deliverables including an exam, all due today — guaranteed to
            # land in the same calendar week regardless of what day "today" is
            _write_deadlines_csv(tmp / "semester_deadlines.csv", [
                ("CS4820", "HW1", "homework", 0, "10%"),
                ("CS4820", "Quiz1", "quiz", 0, "5%"),
                ("ENGR3450", "Midterm", "exam", 0, "20%"),
            ])
            overload, warning = gather_overload_assessment(tmp, TZ)

        self.assertTrue(overload["is_overloaded"])
        self.assertEqual(overload["severity"], "HIGH")
        self.assertIn("exam", overload["reason"])


class TestGatherStudyBlocksToday(unittest.TestCase):
    def test_schedule_not_covering_today_is_reported_not_silently_stale(self):
        today = datetime.now(ZoneInfo(TZ))
        old_date = (today - timedelta(days=30)).strftime("%m/%d/%Y")
        fieldnames = ["Subject", "Start Date", "Start Time", "End Date", "End Time",
                      "All Day Event", "Description", "Location", "Private"]

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = tmp / "weekly_schedule.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({
                    "Subject": "Study block", "Start Date": old_date, "Start Time": "8:00 AM",
                    "End Date": old_date, "End Time": "9:00 AM", "All Day Event": "False",
                    "Description": "Type: study | Added by SyllabOS", "Location": "", "Private": "False",
                })
            blocks, warning = gather_study_blocks_today(tmp, TZ)

        self.assertEqual(blocks, [])
        self.assertIsNotNone(warning)
        self.assertIn("different week", warning)


class TestRenderFallbackText(unittest.TestCase):
    """
    The deterministic (non-LLM) fallback path. It must only ever say what's
    in the BriefingData it was given — never invent an event, deadline, or
    free block that wasn't passed in.
    """

    def _minimal_data(self, **overrides) -> BriefingData:
        base = dict(
            today_label="Wednesday, September 23",
            today_iso="2026-09-23",
            timezone=TZ,
            events_today=[],
            calendar_source="none",
            calendar_warning=None,
            deadlines_upcoming=[],
            deadlines_warning=None,
            study_blocks_today=[],
            study_warning=None,
            overload={"is_overloaded": False},
        )
        base.update(overrides)
        return BriefingData(**base)

    def test_empty_data_is_reported_honestly(self):
        text = render_fallback_text("Alex Rivera", self._minimal_data())
        self.assertIn("Nothing on your calendar today", text)
        self.assertIn("No study blocks scheduled today", text)
        self.assertIn("Nothing due in the next 7 days", text)
        self.assertIn("manageable", text)

    def test_only_mentions_given_events(self):
        data = self._minimal_data(events_today=[
            {"start": "10:00 AM", "end": "11:00 AM", "title": "CS4820 Lecture", "all_day": False},
        ])
        text = render_fallback_text("Alex Rivera", data)
        self.assertIn("CS4820 Lecture", text)
        # nothing fabricated: no mention of any other course/event name
        self.assertNotIn("ENGR3450", text)

    def test_overload_reason_is_surfaced(self):
        data = self._minimal_data(overload={
            "is_overloaded": True, "reason": "Week of October 2 has 4 things due including an exam",
            "severity": "HIGH",
        })
        text = render_fallback_text("Alex Rivera", data)
        self.assertIn("4 things due", text)

    def test_warnings_are_spoken_not_hidden(self):
        data = self._minimal_data(calendar_warning="Couldn't reach Google Calendar — using last export.")
        text = render_fallback_text("Alex Rivera", data)
        self.assertIn("Couldn't reach Google Calendar", text)

    def test_greets_by_first_name_only(self):
        text = render_fallback_text("Alex Rivera", self._minimal_data())
        self.assertIn("Alex", text)
        self.assertNotIn("Rivera", text)


class TestDemoBriefingData(unittest.TestCase):
    def test_demo_data_is_internally_consistent_and_labeled(self):
        data = build_demo_briefing_data(TZ)

        self.assertEqual(data.calendar_source, "demo_sample")
        self.assertIn("sample", data.calendar_warning.lower())
        self.assertTrue(data.events_today)
        self.assertTrue(data.study_blocks_today)
        self.assertTrue(data.deadlines_upcoming)
        self.assertTrue(data.overload["is_overloaded"])

        # deadline dates must be real, parseable, and in the future relative to "today"
        today = datetime.now(ZoneInfo(TZ))
        for d in data.deadlines_upcoming:
            due = datetime.strptime(d["date"], "%Y-%m-%d").replace(tzinfo=ZoneInfo(TZ))
            self.assertGreaterEqual(due, today - timedelta(days=1))


if __name__ == "__main__":
    unittest.main()
