import csv
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import _pathfix  # noqa: F401

from calendar_source import get_today_events

FIELDNAMES = ["Subject", "Start Date", "Start Time", "End Date", "End Time",
              "All Day Event", "Description", "Location", "Private"]
TZ = "UTC"


def _write_schedule_csv(path: Path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class TestCsvFallback(unittest.TestCase):
    """
    These exercise the CSV fallback path. Since credentials.json/token.json
    never exist in a fresh checkout (and are gitignored), get_today_events
    always falls back to the CSV here — which is exactly the "no live
    calendar connected yet" scenario every fresh student setup starts in.
    """

    def _fake_calendar_paths(self, tmp: Path):
        return tmp / "credentials.json", tmp / "token.json"

    def test_no_csv_and_no_calendar_yields_source_none_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            creds_path, token_path = self._fake_calendar_paths(tmp)
            result = get_today_events(tmp, TZ, creds_path, token_path)

        self.assertEqual(result.source, "none")
        self.assertIsNotNone(result.warning)
        self.assertEqual(result.events, [])

    def test_csv_covering_today_is_used_with_staleness_warning(self):
        today = datetime.now(ZoneInfo(TZ))
        gc_date = today.strftime("%m/%d/%Y")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            creds_path, token_path = self._fake_calendar_paths(tmp)
            csv_path = tmp / "weekly_schedule.csv"
            _write_schedule_csv(csv_path, [
                {
                    "Subject": "Sleep", "Start Date": gc_date, "Start Time": "11:00 PM",
                    "End Date": gc_date, "End Time": "7:00 AM", "All Day Event": "False",
                    "Description": "Type: sleep | Added by SyllabOS", "Location": "", "Private": "False",
                },
                {
                    "Subject": "Study: CS4820 Reading Quiz 1", "Start Date": gc_date,
                    "Start Time": "8:00 AM", "End Date": gc_date, "End Time": "9:00 AM",
                    "All Day Event": "False",
                    "Description": "Course: CS4820 Machine Learning | Type: study | Added by SyllabOS",
                    "Location": "", "Private": "False",
                },
            ])
            result = get_today_events(tmp, TZ, creds_path, token_path)

        self.assertEqual(result.source, "csv_fallback")
        self.assertIsNotNone(result.warning)
        # sleep blocks are noise for "what's on my calendar" and are excluded
        titles = [e["title"] for e in result.events]
        self.assertNotIn("Sleep", titles)
        self.assertIn("Study: CS4820 Reading Quiz 1", titles)

    def test_csv_not_covering_today_reports_missing_data_not_stale_data(self):
        old_date = (datetime.now(ZoneInfo(TZ)) - timedelta(days=30)).strftime("%m/%d/%Y")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            creds_path, token_path = self._fake_calendar_paths(tmp)
            csv_path = tmp / "weekly_schedule.csv"
            _write_schedule_csv(csv_path, [{
                "Subject": "Study block", "Start Date": old_date, "Start Time": "8:00 AM",
                "End Date": old_date, "End Time": "9:00 AM", "All Day Event": "False",
                "Description": "Type: study | Added by SyllabOS", "Location": "", "Private": "False",
            }])
            result = get_today_events(tmp, TZ, creds_path, token_path)

        # must never silently present this old week's events as today's
        self.assertEqual(result.events, [])
        self.assertIn("different week", result.warning)

    def test_stale_export_mentions_its_age(self):
        today = datetime.now(ZoneInfo(TZ))
        gc_date = today.strftime("%m/%d/%Y")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            creds_path, token_path = self._fake_calendar_paths(tmp)
            csv_path = tmp / "weekly_schedule.csv"
            _write_schedule_csv(csv_path, [{
                "Subject": "Study block", "Start Date": gc_date, "Start Time": "8:00 AM",
                "End Date": gc_date, "End Time": "9:00 AM", "All Day Event": "False",
                "Description": "Type: study | Added by SyllabOS", "Location": "", "Private": "False",
            }])
            # backdate the file's mtime by 3 days to simulate a stale export
            three_days_ago = (today - timedelta(days=3)).timestamp()
            os.utime(csv_path, (three_days_ago, three_days_ago))

            result = get_today_events(tmp, TZ, creds_path, token_path)

        self.assertIn("day(s) old", result.warning)


if __name__ == "__main__":
    unittest.main()
