#!/usr/bin/env python3
"""
SyllabOS — Academic Life Management Agent
==========================================
Drop your syllabi in a folder. Run one command.
Get your entire semester organized in Google Calendar.

Usage:
  python3 syllabos.py                    # reads syllabi/ folder
  python3 syllabos.py --folder ./myfiles # custom folder
  python3 syllabos.py --demo             # runs on sample syllabi
  python3 syllabos.py --break            # ESCALATE demo beat
  python3 syllabos.py --checkin          # Sunday check-in — update your profile
  python3 syllabos.py --morning          # speak today's morning briefing now
  python3 syllabos.py --listen           # listen for "Good morning, Sunshine"
  python3 syllabos.py --calendar-auth    # one-time Google Calendar (read-only) setup

Requirements:
  pip3 install -r requirements.txt
  NIM_API_KEY in your .env file (free at build.nvidia.com)
  For --morning / --listen voice + live calendar: pip3 install -r requirements-voice.txt

Output:
  output/weekly_schedule.csv    → import directly to Google Calendar
  output/semester_deadlines.csv → full deadline list
  output/conflict_report.csv    → heavy weeks and reschedule suggestions
  output/student_profile.json   → your behavioral profile (created after first --checkin)

Free to use. Free to run. Open source.
github.com/itsChanelML/syllabos
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from agent import SyllabOSAgent
from display import banner, log_t, log_g, log_r, log_gr, log_a, TEAL, RESET, BOLD, AMBER


def main():
    parser = argparse.ArgumentParser(
        description="SyllabOS — Dominate your semester with NVIDIA AI + speech.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 syllabos.py                       # reads syllabi/ folder
  python3 syllabos.py --folder ./my_docs    # custom folder
  python3 syllabos.py --demo                # run on sample syllabi
  python3 syllabos.py --break               # trigger ESCALATE demo beat
  python3 syllabos.py --name "Alex Rivera"  # personalize output
  python3 syllabos.py --checkin             # Sunday check-in
  python3 syllabos.py --morning              # speak today's briefing now
  python3 syllabos.py --morning --demo       # workshop demo, sample data
  python3 syllabos.py --listen               # listen for the spoken trigger
  python3 syllabos.py --calendar-auth        # one-time Google Calendar setup
        """
    )
    parser.add_argument("--folder",   type=str, default=str(ROOT / "syllabi"),
                        help="Folder containing your syllabus files (PDF, DOCX, TXT)")
    parser.add_argument("--name",     type=str, default=os.environ.get("STUDENT_NAME", "Student"),
                        help="Your name (for personalized output)")
    parser.add_argument("--email",    type=str, default=os.environ.get("STUDENT_EMAIL", ""),
                        help="Your email (for the CSV import)")
    parser.add_argument("--demo",     action="store_true", help="Run on sample syllabi")
    parser.add_argument("--break",    dest="broken", action="store_true",
                        help="Demo ESCALATE beat — simulates a broken syllabus file")
    parser.add_argument("--checkin",  action="store_true",
                        help="Sunday evening check-in — tell SyllabOS how your week went. Creates/updates output/student_profile.json")
    parser.add_argument("--week",     type=str, default="",
                        help="Target week start date YYYY-MM-DD (default: next Monday)")
    parser.add_argument("--output",   type=str, default=str(ROOT / "output"),
                        help="Output folder for CSV files")
    parser.add_argument("--morning",  action="store_true",
                        help="Generate and speak today's morning briefing right now")
    parser.add_argument("--listen",   action="store_true",
                        help='Listen for the spoken trigger "Good morning, Sunshine" '
                             "(microphone + keyboard fallback)")
    parser.add_argument("--simulate-trigger", type=str, default=None, metavar="TEXT",
                        help="Feed TEXT through the wake-phrase matcher to demo the "
                             "trigger without a microphone, then run the briefing")
    parser.add_argument("--calendar-auth", action="store_true",
                        help="One-time Google Calendar (read-only) OAuth setup")
    parser.add_argument("--voice-provider", type=str,
                        default=os.environ.get("VOICE_PROVIDER", "nvidia"),
                        choices=["nvidia", "system"],
                        help="Speech backend for --morning / --listen (default: nvidia, "
                             "auto-falls back to system with a warning)")
    parser.add_argument("--text-only", action="store_true",
                        help="Print the briefing instead of speaking it aloud")
    parser.add_argument("--timezone", type=str,
                        default=os.environ.get("STUDENT_TIMEZONE", ""),
                        help="IANA timezone for the morning briefing (default: STUDENT_TIMEZONE "
                             "in .env, else your system timezone)")
    parser.add_argument("--once",     action="store_true",
                        help="With --listen: handle one trigger, then exit")
    args = parser.parse_args()

    # ── Check-in mode — no API key required ───────────────────────────────────
    if args.checkin:
        _run_checkin(
            student_name=args.name,
            output_dir=Path(args.output),
        )
        return

    # ── Google Calendar setup — no NIM API key required ───────────────────────
    if args.calendar_auth:
        _run_calendar_auth()
        return

    # ── API key required for all other modes ──────────────────────────────────
    api_key = os.environ.get("NIM_API_KEY")
    if not api_key:
        print(f"\n{BOLD}Error: NIM_API_KEY not set.{RESET}")
        print(f"  Get your free key at: https://build.nvidia.com")
        print(f"  Then: export NIM_API_KEY=nvapi-xxxx")
        print(f"  Or add it to your .env file.\n")
        sys.exit(1)

    # ── Morning briefing modes ─────────────────────────────────────────────────
    if args.morning:
        _run_morning(args, api_key)
        return

    if args.listen:
        _run_listen(args, api_key)
        return

    if args.simulate_trigger is not None:
        _run_simulate_trigger(args, api_key)
        return

    # ── Demo / ESCALATE mode ──────────────────────────────────────────────────
    if args.demo or args.broken:
        folder = ROOT / "syllabi" / ("samples_broken" if args.broken else "samples")
        if not folder.exists():
            log_r(f"Sample folder not found: {folder}")
            log_r("Make sure syllabi/samples/ and syllabi/samples_broken/ exist.")
            sys.exit(1)
        args.folder = str(folder)

    # ── Run the agent ─────────────────────────────────────────────────────────
    agent = SyllabOSAgent(
        api_key=api_key,
        student_name=args.name,
        student_email=args.email,
        output_dir=Path(args.output),
        week_start=args.week,
    )

    agent.run(folder=Path(args.folder))


def _run_checkin(student_name: str, output_dir: Path):
    """
    Sunday evening check-in.
    Loads or creates student_profile.json, asks 5 questions,
    saves updated profile. No API key needed.
    """
    from memory import load_profile, run_checkin as do_checkin, save_profile

    output_dir.mkdir(parents=True, exist_ok=True)

    # Override default profile path to use the output dir
    import memory as mem_module
    mem_module.PROFILE_FILE = output_dir / "student_profile.json"

    profile = load_profile(student_name=student_name)
    updated = do_checkin(profile)
    save_profile(updated)

    print(f"\n  Profile saved to: {mem_module.PROFILE_FILE}")
    print(f"  Run python3 syllabos.py to build next week with your updated profile.\n")


def _resolve_timezone(explicit: str) -> str:
    """STUDENT_TIMEZONE / --timezone wins; otherwise best-effort auto-detect."""
    if explicit:
        return explicit
    try:
        import tzlocal
        return tzlocal.get_localzone_name()
    except Exception:
        log_a("Could not auto-detect your timezone — defaulting to UTC.")
        log_a("Fix: set STUDENT_TIMEZONE=America/New_York (or your IANA zone) in .env")
        return "UTC"


def _validate_timezone(tz_name: str):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        log_r(f"\nESCALATE — Unknown timezone '{tz_name}'.")
        log_r("Fix: set STUDENT_TIMEZONE in .env to an IANA name, e.g. America/New_York\n")
        sys.exit(1)


def _calendar_paths():
    creds_path = Path(os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json"))
    token_path = Path(os.environ.get("GOOGLE_CALENDAR_TOKEN", "token.json"))
    return creds_path, token_path


def _run_calendar_auth():
    from calendar_source import GoogleCalendarError, run_oauth_flow

    creds_path, token_path = _calendar_paths()

    banner("SyllabOS — Google Calendar Setup (read-only)")
    print(f"  Credentials file       : {creds_path}")
    print(f"  Token will be saved to : {token_path}\n")

    try:
        run_oauth_flow(creds_path, token_path)
    except GoogleCalendarError as e:
        log_r(f"\nESCALATE — {e}\n")
        sys.exit(1)

    log_g(f"\n  Connected. {token_path} saved locally — never commit this file.")
    log_gr("  Run python3 syllabos.py --morning to test your live morning briefing.\n")


def _run_morning(args, api_key: str):
    import morning_briefing as mb
    from voice import get_tts

    tz_name = _resolve_timezone(args.timezone)
    _validate_timezone(tz_name)

    tts, tts_warning = (None, None) if args.text_only else get_tts(args.voice_provider, api_key)
    creds_path, token_path = _calendar_paths()

    banner(f"SyllabOS — Morning Briefing for {args.name}")
    mb.run_morning_briefing(
        api_key=api_key, student_name=args.name, output_dir=Path(args.output),
        tz_name=tz_name, tts=tts, tts_warning=tts_warning, text_only=args.text_only,
        demo=args.demo, creds_path=creds_path, token_path=token_path,
    )


def _run_listen(args, api_key: str):
    import morning_briefing as mb
    from listener import run_listen_loop
    from voice import get_stt, get_tts

    tz_name = _resolve_timezone(args.timezone)
    _validate_timezone(tz_name)

    tts, tts_warning = (None, None) if args.text_only else get_tts(args.voice_provider, api_key)
    stt, stt_warning = get_stt(args.voice_provider, api_key)
    if stt_warning:
        log_a(stt_warning)

    creds_path, token_path = _calendar_paths()

    banner(f"SyllabOS — Listening for {args.name}")

    def on_trigger():
        mb.run_morning_briefing(
            api_key=api_key, student_name=args.name, output_dir=Path(args.output),
            tz_name=tz_name, tts=tts, tts_warning=tts_warning, text_only=args.text_only,
            demo=args.demo, creds_path=creds_path, token_path=token_path,
        )

    run_listen_loop(stt, on_trigger, once=args.once)


def _run_simulate_trigger(args, api_key: str):
    from trigger import matches_trigger

    heard = args.simulate_trigger
    log_t(f'\n  Simulated microphone input: "{heard}"')

    if not matches_trigger(heard):
        log_a('  Not recognized as "Good morning, Sunshine" — try wording it closer to the trigger phrase.\n')
        sys.exit(1)

    log_g("  Trigger recognized! Generating the morning briefing...")
    _run_morning(args, api_key)


if __name__ == "__main__":
    main()