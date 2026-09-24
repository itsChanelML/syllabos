# SyllabOS

**A more thoughtful way to plan the semester.**

SyllabOS turns course syllabi into a workable academic schedule. It brings deadlines, exams, study time, and work commitments into one plan, then gives students a spoken briefing to help them start the day with clarity.

Students are often asked to manage several courses while also working, caring for family, and finding time to rest. SyllabOS was built for that reality. Its purpose is to make the planning work lighter, surface demanding weeks early, and help students decide where to focus their time.

Built with Python, NVIDIA NIM and Speech AI, Google Calendar, and an optional Google Apps Script interface.

## What it does

| Capability | How it helps |
| --- | --- |
| Syllabus reading | Extracts assignments, exams, quizzes, and due dates from PDF, Word, and text files. |
| Semester planning | Produces a weekly schedule with study blocks around work shifts and other commitments. |
| Early workload signals | Identifies weeks with clustered deadlines and suggests where to adjust the plan. |
| Calendar integration | Exports Google Calendar compatible CSVs or creates events through Google Apps Script. |
| Weekly reflection | Uses a short check-in to inform the following week's schedule. |
| Morning briefing | Summarizes today's events, upcoming deadlines, study time, and the week ahead in text or speech. |

SyllabOS is an aid to planning. Review extracted dates and proposed blocks before relying on them, especially when a syllabus changes during the term.

## Choose how to start

| Path | Best for | Calendar output |
| --- | --- | --- |
| **Python command line** | Students who want to work with files on their computer and use the voice briefing. | CSV files to import into Google Calendar. |
| **Google Apps Script** | Students who prefer to prepare syllabi in Google Sheets and use a browser. | Events created in a dedicated Google Calendar. |

The spoken briefing runs from the Python application. The Apps Script path handles syllabus and schedule planning in the browser; it does not listen for a voice phrase.

## Get started with Python

**You need:** Python 3.9 or later and an NVIDIA API key from [build.nvidia.com](https://build.nvidia.com). Hosted API availability and usage limits may change; check the terms for the model you select.

```bash
git clone https://github.com/itsChanelML/syllabos.git
cd syllabos
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Add your key to `.env`:

```dotenv
NIM_API_KEY=your_nvidia_api_key
STUDENT_NAME=Your Name
STUDENT_TIMEZONE=America/New_York
```

Put your `.pdf`, `.docx`, `.txt`, or `.md` syllabi in `syllabi/`. If you work during the semester, add a `work_schedule.txt` file in the same folder. The [sample work schedule](syllabi/samples/work_schedule.txt) shows the expected format.

```bash
python3 syllabos.py --demo   # Explore the project with sample syllabi
python3 syllabos.py          # Build a schedule from your own files
```

The application writes `weekly_schedule.csv`, `semester_deadlines.csv`, and `conflict_report.csv` to `output/`. Import the first two files through **Google Calendar → Settings → Import & export**. Calendar CSV imports are snapshots: changes you make later in Google Calendar are not automatically written back to the exported files.

At the end of the week, run `python3 syllabos.py --checkin` to record which study blocks worked and what changed. Run `python3 syllabos.py` again to build a new schedule using that information.

## Add the morning briefing

The voice features have separate dependencies:

```bash
python3 -m pip install -r requirements-voice.txt
python3 syllabos.py --morning --demo --text-only
```

The second command uses clearly labeled sample data, so you can preview the briefing before connecting your own calendar. To use your own schedule, run the main planning command first and then choose one of these options:

```bash
python3 syllabos.py --morning             # Generate and speak today's briefing
python3 syllabos.py --morning --text-only # Read it on screen
python3 syllabos.py --listen              # Listen for "Good morning, Sunshine"
```

`--listen` runs only while the script is open. Press **Enter** to trigger the same briefing if a microphone is unavailable or the room is noisy. For a reliable workshop demonstration, `python3 syllabos.py --simulate-trigger "Good morning, Sunshine" --demo` exercises the phrase trigger with sample data.

### Connect Google Calendar for current events

The spoken briefing can read today's events from your **primary Google Calendar** with read-only permission. The OAuth connection does not create, edit, or delete calendar events.

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select a project and enable the Google Calendar API.
2. Create an OAuth client ID for a **Desktop app** and download its credentials JSON.
3. Save the file as `credentials.json` in the project directory.
4. Run `python3 syllabos.py --calendar-auth` and complete the browser authorization.
5. Run `python3 syllabos.py --morning` to hear or read your briefing.

The local token is saved as `token.json`. Both credential files are excluded from Git. Without a live connection, SyllabOS uses its last schedule export for calendar events and marks that information as potentially out of date. The briefing also draws upcoming deadlines and study blocks from the generated CSV files. If you use the Apps Script path, note that it creates a separate SyllabOS calendar; the live briefing currently queries your **primary** calendar and will not include events from that separate calendar unless you copy them to the primary calendar or extend the integration.

### Configure NVIDIA speech

SyllabOS uses NVIDIA hosted speech recognition for the trigger phrase and text-to-speech for the spoken response. NVIDIA's speech models require their own model function IDs in addition to the API key:

1. Open the [NVIDIA speech catalog](https://build.nvidia.com/explore/speech).
2. Select an available speech-to-text model and a text-to-speech model, then copy each model's `function-id` from its Python API example.
3. Add them to `.env`:

```dotenv
NVIDIA_ASR_FUNCTION_ID=your_asr_function_id
NVIDIA_TTS_FUNCTION_ID=your_tts_function_id
VOICE_PROVIDER=nvidia
```

Speech endpoint availability and access may vary. If NVIDIA text-to-speech is unavailable, the application attempts to use the computer's system voice and shows a warning. Spoken trigger recognition requires NVIDIA speech; the **Enter** fallback remains available. You can set `VOICE_PROVIDER=system` for local speech output without configuring NVIDIA speech models.

## Prefer a browser? Use Google Apps Script

1. Create a Google Sheet and open **Extensions → Apps Script**.
2. Copy the contents of [`scripts/APPSCRIPT.js`](scripts/APPSCRIPT.js) into the script editor and fill in the `CONFIG` values, including your NVIDIA API key and semester dates.
3. Return to the Sheet and add `Syllabus_1`, `Syllabus_2`, and other syllabus tabs. Paste the text of each syllabus into cell A1. For a PDF, open it with Google Docs first to extract selectable text.
4. Optionally add a `Work Schedule` tab using the same format as the sample work schedule.
5. Run the **SyllabOS** menu's full workflow, or run **Parse My Syllabi**, **Build My Week**, and **Push to Google Calendar** in order.

The script creates events in a SyllabOS calendar, or reuses a calendar named SyllaClaw for students who used the earlier version. Keep a Sheet containing an API key private, and review its sharing settings before inviting collaborators.

## How the system is organized

The Python application separates file reading (`src/reader.py`), orchestration (`src/agent.py`), scheduling (`src/schedule.py`), calendar export (`src/exporter.py`), and student preferences (`src/memory.py`). Morning briefings use `src/morning_briefing.py` and `src/calendar_source.py`; speech providers live under `src/voice/`. NVIDIA NIM handles syllabus interpretation, schedule generation, and briefing language. The voice provider handles speech recognition and playback.

When a file cannot be read or the requested plan cannot be completed, SyllabOS surfaces an **ESCALATE** message with an explanation and suggested next step. You can see the sample error path with `python3 syllabos.py --break`.

## Privacy and practical limits

- Syllabus files, work schedules, and exported calendars can contain personal information. Review what you submit to hosted AI services and follow your institution's guidance for sensitive information.
- The optional listener captures short microphone clips while it is running and sends them to NVIDIA speech recognition when configured. It does not run in the background after you close the script.
- Calendar access for the morning briefing is read-only. The planning paths can still create events through CSV import or Apps Script.
- A generated schedule is a proposal. Verify due dates, time zones, and conflicts against your course materials and actual calendar.
- Hosted model access, free usage, and voice availability depend on the provider's current terms and endpoint status.

## Troubleshooting and testing

| If you see… | Try this |
| --- | --- |
| `NIM_API_KEY not set` | Add your key to `.env` in the project directory. |
| A PDF yields no text | Use a text-based PDF or extract its text with Google Docs and save it as `.txt`. |
| The briefing says its calendar data may be stale | Connect the read-only Calendar API or rebuild and reimport your schedule. |
| No microphone is available | Use `--morning` or press **Enter** during `--listen`. |
| Speech support is missing | Install `requirements-voice.txt` and check the function IDs in `.env`. |
| The day or deadline countdown seems wrong | Set `STUDENT_TIMEZONE` to your IANA time zone, such as `America/New_York`. |
| NVIDIA speech fails with a `grpc` version error | On Python 3.9, `grpcio` caps at 1.80.0, but `nvidia-riva-client` releases newer than 2.16.0 need `grpcio>=1.81.0` and fail to import. `requirements-voice.txt` pins `nvidia-riva-client==2.16.0` for this reason — reinstall with `pip3 install -r requirements-voice.txt` if you've since upgraded it. On Python 3.10+ this doesn't apply. |
| A NIM call is unusually slow or times out | Model availability/load on NVIDIA's hosted endpoints can vary. Check `MODEL` in `src/nim_client.py`, and try an alternate model from your account's list (`GET https://integrate.api.nvidia.com/v1/models` with your API key) if it's persistent. |

Run the included unit tests with:

```bash
python3 -m unittest discover -s tests -t . -v
```

## About the project

SyllabOS is an open-source project by **Chanel Power**, an ML engineer and founder of [Mentor Me Collective](https://mentormecollective.org). Her work focuses on making technical learning and career opportunities more accessible. The project is designed to help students spend less energy assembling a plan and more energy acting on it.

Questions, improvements, and contributions are welcome through the [repository](https://github.com/itsChanelML/syllabos).
