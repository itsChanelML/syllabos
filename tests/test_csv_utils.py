import csv
import tempfile
import unittest
from pathlib import Path

from . import _pathfix  # noqa: F401

from csv_utils import gc_date_to_iso, read_deadlines_csv, read_schedule_csv

FIELDNAMES = ["Subject", "Start Date", "Start Time", "End Date", "End Time",
              "All Day Event", "Description", "Location", "Private"]


def _write_csv(path: Path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class TestDateConversion(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(gc_date_to_iso("09/23/2026"), "2026-09-23")

    def test_invalid_date_returns_none(self):
        self.assertIsNone(gc_date_to_iso("not a date"))
        self.assertIsNone(gc_date_to_iso(""))
        self.assertIsNone(gc_date_to_iso(None))


class TestReadDeadlinesCsv(unittest.TestCase):
    def test_round_trip_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "semester_deadlines.csv"
            _write_csv(path, [{
                "Subject": "🔴 EXAM: CS4820 Machine Learning — Midterm Exam",
                "Start Date": "10/02/2026",
                "Start Time": "2:00 PM",
                "End Date": "10/02/2026",
                "End Time": "2:00 PM",
                "All Day Event": "False",
                "Description": "Course: CS4820 Machine Learning | Type: exam | "
                               "Weight: 20% | closed book | Estimated study time: 10 hour(s) | "
                               "Added by SyllabOS",
                "Location": "", "Private": "False",
            }])

            deadlines = read_deadlines_csv(path)

        self.assertEqual(len(deadlines), 1)
        d = deadlines[0]
        self.assertEqual(d["date"], "2026-10-02")
        self.assertEqual(d["title"], "Midterm Exam")
        self.assertEqual(d["course"], "CS4820 Machine Learning")
        self.assertEqual(d["type"], "exam")
        self.assertEqual(d["weight"], "20%")

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(read_deadlines_csv(Path("/nonexistent/semester_deadlines.csv")), [])

    def test_row_with_unparseable_date_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "semester_deadlines.csv"
            _write_csv(path, [{
                "Subject": "Broken row", "Start Date": "garbage", "Start Time": "",
                "End Date": "", "End Time": "", "All Day Event": "False",
                "Description": "", "Location": "", "Private": "False",
            }])
            self.assertEqual(read_deadlines_csv(path), [])


class TestReadScheduleCsv(unittest.TestCase):
    def test_round_trip_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weekly_schedule.csv"
            _write_csv(path, [{
                "Subject": "Study: CS4820 Reading Quiz 1",
                "Start Date": "09/21/2026", "Start Time": "8:00 AM",
                "End Date": "09/21/2026", "End Time": "9:00 AM",
                "All Day Event": "False",
                "Description": "Focus on the reading. | Course: CS4820 Machine Learning | "
                               "Type: study | Added by SyllabOS",
                "Location": "", "Private": "False",
            }])

            blocks = read_schedule_csv(path)

        self.assertEqual(len(blocks), 1)
        b = blocks[0]
        self.assertEqual(b["date"], "2026-09-21")
        self.assertEqual(b["start_time"], "8:00 AM")
        self.assertEqual(b["end_time"], "9:00 AM")
        self.assertEqual(b["type"], "study")
        self.assertEqual(b["course"], "CS4820 Machine Learning")


if __name__ == "__main__":
    unittest.main()
