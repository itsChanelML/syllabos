"""
Read-only Google Calendar access for the morning briefing, with a fallback
to SyllabOS's own last-exported weekly_schedule.csv when live Calendar
access isn't set up or isn't reachable.

The fallback is never presented as current without saying so: every
CalendarResult that isn't source == "google_calendar" carries a `warning`
string that gets spoken as part of the briefing, not just logged.

Setup: see README "Live Google Calendar setup". Scope is read-only —
SyllabOS never creates, edits, or deletes calendar events through this
integration; that already happens separately via CSV import / Apps Script.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from csv_utils import read_schedule_csv

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarError(Exception):
    pass


@dataclass
class CalendarResult:
    events: List[Dict]
    source: str                    # "google_calendar" | "csv_fallback" | "none"
    warning: Optional[str] = None
    as_of: Optional[datetime] = None


def _fmt12(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def get_calendar_credentials(creds_path: Path, token_path: Path):
    """
    Return valid, read-only Credentials, or None if Google Calendar hasn't
    been connected yet. Never launches the interactive OAuth flow — that
    only happens via `python3 syllabos.py --calendar-auth`.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError as e:
        raise GoogleCalendarError(
            "Google Calendar support needs extra packages.\n"
            "Fix: pip3 install -r requirements-voice.txt"
        ) from e

    if not token_path.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except Exception as e:
        raise GoogleCalendarError(f"{token_path} is unreadable or corrupted: {e}") from e

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            return creds
        except Exception as e:
            raise GoogleCalendarError(
                f"Your Google Calendar authorization expired and could not refresh: {e}\n"
                "Fix: run python3 syllabos.py --calendar-auth to reconnect."
            ) from e

    return None


def run_oauth_flow(creds_path: Path, token_path: Path):
    """One-time interactive setup — opens a browser, saves a local token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise GoogleCalendarError(
            "Google Calendar support needs extra packages.\n"
            "Fix: pip3 install -r requirements-voice.txt"
        ) from e

    if not creds_path.exists():
        raise GoogleCalendarError(
            f"Missing {creds_path}.\n"
            "Fix: see README 'Live Google Calendar setup' to download your OAuth "
            "client file from Google Cloud Console and save it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())


def fetch_today_events_google(creds, tz_name: str) -> List[Dict]:
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as e:
        raise GoogleCalendarError(
            "Google Calendar support needs extra packages.\n"
            "Fix: pip3 install -r requirements-voice.txt"
        ) from e

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = datetime(now.year, now.month, now.day, tzinfo=tz)
    end = start + timedelta(days=1)

    try:
        service = build("calendar", "v3", credentials=creds)
        result = service.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            timeZone=tz_name,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except HttpError as e:
        raise GoogleCalendarError(f"Google Calendar request failed: {e}") from e
    except Exception as e:
        raise GoogleCalendarError(f"Could not reach Google Calendar: {e}") from e

    events = []
    for item in result.get("items", []):
        start_info = item.get("start", {})
        end_info = item.get("end", {})
        all_day = "date" in start_info and "dateTime" not in start_info

        if all_day:
            start_str, end_str = "All day", ""
        else:
            try:
                start_dt = datetime.fromisoformat(start_info["dateTime"]).astimezone(tz)
                end_dt = datetime.fromisoformat(end_info["dateTime"]).astimezone(tz)
                start_str, end_str = _fmt12(start_dt), _fmt12(end_dt)
            except (KeyError, ValueError):
                start_str, end_str = "", ""

        events.append({
            "title":   item.get("summary", "(untitled event)"),
            "start":   start_str,
            "end":     end_str,
            "all_day": all_day,
        })

    return events


def _csv_fallback(output_dir: Path, tz_name: str, warning: str) -> CalendarResult:
    csv_path = output_dir / "weekly_schedule.csv"
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).strftime("%Y-%m-%d")

    if not csv_path.exists():
        return CalendarResult(
            events=[], source="none", as_of=None,
            warning=(
                f"{warning}\nNo weekly_schedule.csv found either — run python3 syllabos.py "
                "first, or python3 syllabos.py --calendar-auth to connect live Google Calendar."
            ),
        )

    all_blocks = read_schedule_csv(csv_path)
    today_blocks = [b for b in all_blocks if b["date"] == today and b["type"] != "sleep"]
    mtime = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=tz)
    age_days = (datetime.now(tz) - mtime).days

    if not any(b["date"] == today for b in all_blocks):
        return CalendarResult(
            events=[], source="csv_fallback", as_of=mtime,
            warning=(
                f"{warning}\nYour last export (from {mtime:%B %d}) doesn't cover today "
                "— it may be for a different week. Re-run python3 syllabos.py to refresh it."
            ),
        )

    staleness = f" This export is from {mtime:%B %d} ({age_days} day(s) old)." if age_days >= 1 else ""
    events = [
        {"title": b["title"], "start": b["start_time"], "end": b["end_time"], "all_day": False}
        for b in sorted(today_blocks, key=lambda b: b["start_time"])
    ]
    return CalendarResult(
        events=events, source="csv_fallback", as_of=mtime,
        warning=f"{warning}{staleness}",
    )


def get_today_events(output_dir: Path, tz_name: str, creds_path: Path, token_path: Path) -> CalendarResult:
    """
    Live Google Calendar first; a clearly-labeled CSV fallback second.
    Never returns Calendar data without source == "google_calendar", and
    never returns anything else without a `warning` explaining why.
    """
    try:
        creds = get_calendar_credentials(creds_path, token_path)
    except GoogleCalendarError as e:
        return _csv_fallback(output_dir, tz_name, warning=(
            f"Couldn't check your Google Calendar connection ({e}) — showing your last "
            "CSV export instead."
        ))

    if creds is None:
        return _csv_fallback(output_dir, tz_name, warning=(
            "Google Calendar isn't connected yet — showing your last CSV export instead.\n"
            "Fix: run python3 syllabos.py --calendar-auth to connect your real calendar."
        ))

    try:
        events = fetch_today_events_google(creds, tz_name)
        return CalendarResult(
            events=events, source="google_calendar", warning=None,
            as_of=datetime.now(ZoneInfo(tz_name)),
        )
    except GoogleCalendarError as e:
        return _csv_fallback(output_dir, tz_name, warning=(
            f"Couldn't reach Google Calendar just now ({e}) — showing your last CSV export instead."
        ))
