# SyllabOS 🎙️
### Dominate Your Semester with NVIDIA AI + Speech

**Built for College & Graduate Students. Free to build. Free to run.**

> Nobody warned you that the havoc of Week 8 was coming. SyllabOS encodes that knowledge — and makes it available to every student, for free.

---

## What it does

You drop your syllabus files into a folder. SyllabOS reads every one of them, extracts every deadline and exam, builds a complete time-blocked weekly schedule around your job and your life, flags your brutal weeks before they arrive, and outputs everything as a CSV that imports directly into Google Calendar.

**You get:**
- Every deadline, exam, project, and quiz loaded into Google Calendar with descriptions
- A complete time-blocked weekly schedule — study, sleep, work, meals, family calls, and free time
- Work shifts locked in as non-negotiable blocks — the agent will never schedule over them
- Heavy weeks flagged before they hit you, with specific reschedule suggestions
- A Sunday evening briefing that tells you exactly what to focus on next week
- A **spoken morning briefing** — say "Good morning, Sunshine" and SyllabOS tells you what's on
  today, what's due soon, when you have study time, and whether the week ahead is overloaded
- An ESCALATE alert when something is wrong — unreadable file, impossible schedule — with a precise fix
- A learning system that gets smarter every week based on how you actually live

**What it costs:** Nothing. One free NVIDIA NIM API key. The Google account your university already gave you.

---

## Two ways to use it

### Option A — Command Line
Drop syllabus files on your laptop. Run one command in your terminal. Best for students comfortable with Python.

### Option B — Google Apps Script
Works entirely in your browser. No installation. No terminal. Drop files in Google Drive, click a menu item in Google Sheets, and events appear directly in your Google Calendar. Best for everyone else.

**Both paths produce the same output. Both are completely free.**

---

## How the agent works

SyllabOS runs six steps in sequence:

```
Step 1 — parse_syllabi        Read every file in your folder. Extract all deadlines with estimated study hours.
Step 2 — parse_work_schedule  Find your work schedule file. Lock those shifts as non-negotiable.
Step 3 — detect_conflicts     Find weeks where 3+ deliverables pile up. Flag them before you commit to anything.
Step 4 — build_schedule       Build your complete week: study blocks, sleep, work, meals, family calls, free time.
Step 5 — export_csv           Output Google Calendar-compatible CSV files.
Step 6 — weekly_briefing      Write a personalized Sunday evening briefing for the week ahead.
```

When something goes wrong the agent doesn't crash silently. It stops and tells you exactly what failed and what to do next — this is called an **ESCALATE**. You'll see it fire live when you run `python3 syllabos.py --break`.

---

## How SyllabOS learns your behavior

After your first week, run the Sunday check-in:

```bash
python3 syllabos.py --checkin
```

Five questions. Two minutes. SyllabOS updates your `student_profile.json` and uses it to build a smarter schedule next week.

**What it observes:**
- Which study blocks you actually completed vs. skipped
- Whether your job shifts tend to run over
- What time of day you do your best work
- New commitments you took on

**What it adjusts:**
- Moves deep work blocks to your proven productive hours
- Stops scheduling blocks in time slots you always miss
- Adds buffer time around shifts that run late
- Blocks new commitments before building next week

After a few weeks SyllabOS knows you work best Wednesday mornings, that your Starbucks shift always runs 30 minutes over, and that you'll always say yes to a SHPE event. It builds around that — not around who you wish you were.

---

## Morning voice briefing

After your semester is set up (deadlines parsed, weekly schedule built — Option A or B, either
one), start SyllabOS's listener before you get ready in the morning and say:

> **"Good morning, Sunshine."**

SyllabOS speaks back a short, honest briefing: what's on your calendar today, what's due soon,
when you have study time today, and whether the coming week looks overloaded. It never invents an
event, deadline, or free block — if it doesn't have real data for something, it says so.

### Commands

```bash
# Speak today's briefing right now
python3 syllabos.py --morning

# Start listening for "Good morning, Sunshine" (mic + keyboard fallback — press ENTER any time)
python3 syllabos.py --listen

# Print instead of speaking (no speakers, or you just want to read it)
python3 syllabos.py --morning --text-only

# One-time: connect your real, read-only Google Calendar
python3 syllabos.py --calendar-auth
```

### Workshop demo — no real calendar, no mic required

```bash
# Speak a briefing built from safe, synthetic sample data
python3 syllabos.py --morning --demo

# Demonstrate the spoken trigger without depending on a working microphone —
# feeds text through the exact same wake-phrase matcher --listen uses
python3 syllabos.py --simulate-trigger "Good morning, Sunshine" --demo

# Full live demo: listen for real, but answer with sample data
python3 syllabos.py --listen --demo

# The most bulletproof option if venue wifi/audio is unreliable — no TTS, no mic, no network beyond NIM
python3 syllabos.py --morning --demo --text-only
```

### Where the data comes from

| What it tells you | Source | Fallback |
|---|---|---|
| Today's calendar events | Your live, read-only Google Calendar | Your last `weekly_schedule.csv` export, with a spoken warning that it may be stale |
| Deadlines coming up | `output/semester_deadlines.csv` (built by the main run) | none — tells you to run `python3 syllabos.py` first |
| Study time today | `output/weekly_schedule.csv` | none — tells you your export doesn't cover today |
| Overloaded week? | Recomputed live from your deadlines (same conflict logic as the main pipeline) | — |

SyllabOS never presents a fallback as if it were live data — every fallback carries an explicit,
spoken caveat ("heads up, I couldn't reach your live calendar, so this is from your last export").

### Live Google Calendar setup (read-only)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/), create (or pick) a project.
2. Enable the **Google Calendar API** for that project.
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**, choose
   **Desktop app**, and download the JSON file.
4. Save it in the SyllabOS project root as `credentials.json` (already gitignored — never commit it).
5. Run:
   ```bash
   python3 syllabos.py --calendar-auth
   ```
   A browser window opens for you to approve **read-only** access. This saves `token.json`
   locally (also gitignored) — SyllabOS never writes to your calendar through this integration.
6. Test it: `python3 syllabos.py --morning`

If you skip this, `--morning` / `--listen` automatically use your last CSV export instead, with a
spoken warning that it might be out of date.

### Live voice setup — NVIDIA speech

The morning briefing's spoken trigger (speech-to-text) and voice (text-to-speech) use NVIDIA's
hosted Riva speech models — reusing the same free `NIM_API_KEY` you already have. Unlike the
chat model used elsewhere in this project, NVIDIA's hosted speech models are gRPC services
addressed by a **function-id you copy yourself**, because NVIDIA's speech catalog changes over
time (this project has already had to swap out one retired NIM model — see the git history) and
function-ids are not something safe to hardcode.

1. `pip3 install -r requirements-voice.txt`
2. Go to [build.nvidia.com/explore/speech](https://build.nvidia.com/explore/speech)
3. Open an ASR (speech-to-text) model — recommended: `parakeet-tdt-0.6b-v2` — click **Try API** →
   **Python**, and copy that model's `function-id`
4. Do the same for a TTS (text-to-speech) model — recommended: `magpie-tts-multilingual`
5. Add both to `.env`:
   ```
   NVIDIA_ASR_FUNCTION_ID=your-asr-function-id
   NVIDIA_TTS_FUNCTION_ID=your-tts-function-id
   ```
6. Test it: `python3 syllabos.py --morning`

**If NVIDIA speech isn't set up, or the endpoint is unreachable**, SyllabOS automatically speaks
using your computer's built-in offline voice instead (`pyttsx3` — no API key, no network), with a
visible warning. It never fails silently, and it never blocks the demo. The spoken trigger
("Good morning, Sunshine") has no offline substitute — if the mic or NVIDIA ASR isn't available,
use the keyboard fallback (press **ENTER**) built into `--listen`, or set
`VOICE_PROVIDER=system` to skip NVIDIA speech entirely.

### Timezone

Set `STUDENT_TIMEZONE` in `.env` to your IANA zone (e.g. `America/New_York`,
`America/Los_Angeles`). This is what "today" means for the briefing, and it's what makes deadline
countdowns correct. If it's unset, SyllabOS tries to auto-detect your system's timezone and
otherwise defaults to UTC — set it explicitly for a live demo.

### Privacy

- Microphone audio is only ever held in memory for a single recognition request — SyllabOS never
  writes recordings to disk.
- `credentials.json` and `token.json` (Google Calendar) are gitignored — never commit them.
- The morning briefing never sends your calendar or schedule data anywhere except to NVIDIA's NIM
  API (to phrase the briefing) and, for the live calendar source, to Google's own Calendar API.

---

## Option A — Command Line Setup

### What you need
- Python 3.9 or higher
- A free NVIDIA NIM API key (no credit card required)

### Step 1 — Get your free NVIDIA NIM key
1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Sign in or create a free account
3. Search for `llama-3.2-90b-vision-instruct`
4. Click **Get API Key** — your key starts with `nvapi-`

### Step 2 — Clone and install
```bash
git clone https://github.com/itsChanelML/syllabos
cd syllabos
pip3 install -r requirements.txt
```

If you're on a university-managed machine:
```bash
pip3 install -r requirements.txt --user
```

### Step 3 — Set your API key
```bash
cp .env.example .env
```
Open `.env` in any text editor and replace `your_nim_api_key_here` with your real key:
```
NIM_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx
STUDENT_NAME=Your Full Name
STUDENT_EMAIL=your@email.com
```

### Step 4 — Add your syllabus files
Drop your syllabus files into the `syllabi/` folder.

Supported formats: `.pdf` `.docx` `.txt` `.md`

Also add a file named `work_schedule.txt` if you have a part-time job (see format below).

### Step 5 — Run
```bash
# Full run — reads everything in syllabi/
python3 syllabos.py

# Add your name for personalized output
python3 syllabos.py --name "Alex Rivera"

# Point at a different folder
python3 syllabos.py --folder ./my_files

# Run on the sample syllabi to see how it works before using your own
python3 syllabos.py --demo

# Trigger the ESCALATE beat — shows what happens when a file is unreadable
python3 syllabos.py --break

# Sunday check-in — tell SyllabOS how your week went
python3 syllabos.py --checkin
```

### Step 6 — Import to Google Calendar

After running, open the `output/` folder. You'll find:
- `weekly_schedule.csv` — your full time-blocked week
- `semester_deadlines.csv` — every deadline across all courses
- `conflict_report.csv` — your heavy weeks and reschedule suggestions
- `student_profile.json` — your behavioral profile (updated each Sunday check-in)

**To import:**
1. Go to [calendar.google.com](https://calendar.google.com)
2. Click ⚙ gear → **Settings**
3. Click **Import & Export** in the left sidebar
4. Click **Select file** → choose `weekly_schedule.csv`
5. Click **Import**
6. Repeat with `semester_deadlines.csv`

Your semester is in Google Calendar. Done.

---

## Option B — Google Apps Script Setup

No installation. No terminal. Works entirely in your browser.

### The Google Drive folder concept

Option B mirrors Option A exactly — instead of a local folder on your laptop, you use a Google Drive folder. You upload your syllabus files there, paste the text into Google Sheets tabs, and the Apps Script reads them the same way the Python CLI reads your local folder.

### Step 1 — Get your free NVIDIA NIM key
Same as Option A Step 1.

### Step 2 — Create your Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it `SyllabOS`

### Step 3 — Add the script
1. Click **Extensions → Apps Script**
2. Delete any existing code in the editor
3. Open `scripts/APPSCRIPT.js` from this repo — copy the entire file
4. Paste it into the Apps Script editor
5. Find the `CONFIG` block at the top and fill in your values:
```javascript
const CONFIG = {
  NIM_API_KEY:    "nvapi-xxxxxxxxxxxxxxxxxxxx",  // your free NIM key
  STUDENT_NAME:   "Alex Rivera",                 // your name
  SEMESTER_START: "2026-01-12",                  // first day of classes
  SEMESTER_END:   "2026-05-15",                  // last day of finals
  WAKE_TIME:      "07:00",                       // when you wake up
  SLEEP_TIME:     "23:00",                       // when you go to sleep
};
```
6. Click **Save** (Ctrl+S)
7. Close the Apps Script tab
8. Reload your Google Sheet

A **SyllabOS** menu will appear in your Sheet toolbar.

### Step 4 — Add your syllabi

**Option 1 — Paste text directly:**
Create sheet tabs named `Syllabus_1`, `Syllabus_2`, etc. Paste your syllabus text into cell A1 of each tab.

**Option 2 — From Google Drive (recommended for PDFs):**
Upload your PDF syllabus to Google Drive. Right-click → Open with → Google Docs. Google Docs extracts the text automatically. Select all (Cmd+A), copy, paste into your Syllabus tab.

### Step 5 — Add your work schedule (optional)

Create a sheet tab named `Work Schedule`. Paste your shifts in this format:
```
Monday:    OFF
Tuesday:   4:00 PM - 9:00 PM
Thursday:  4:00 PM - 9:00 PM
Saturday:  8:00 AM - 2:00 PM
Sunday:    10:00 AM - 3:00 PM
```

### Step 6 — Run

Click **SyllabOS** in the menu and choose:
- **4. Full Run (Steps 1–3)** — does everything at once

Or step by step:
1. **1. Parse My Syllabi** — reads all Syllabus tabs, extracts deadlines into a `Deadlines` tab
2. **2. Build My Week** — builds your time-blocked schedule into a `Weekly Schedule` tab
3. **3. Push to Google Calendar** — creates real events in a new `SyllabOS` calendar instantly

No CSV download needed. Events appear in Google Calendar the moment you run Step 3.

---

## Work schedule format

```
Monday:    OFF
Tuesday:   4:00 PM - 9:00 PM  (5 hrs)
Wednesday: OFF
Thursday:  4:00 PM - 9:00 PM  (5 hrs)
Friday:    OFF
Saturday:  8:00 AM - 2:00 PM  (6 hrs)
Sunday:    10:00 AM - 3:00 PM (5 hrs)
```

SyllabOS will never schedule a study block during a shift. Work hours are locked.

---

## How the weekly schedule is built

SyllabOS uses Meta's Llama 3.2 90B model via NVIDIA NIM to reason over your full week, one day at a time:

| What | How |
|------|-----|
| Work shifts | Locked — never overwritten |
| Sleep | Consistent wake and bedtime every day |
| Study blocks | 25-min Pomodoro for memorization/reading, 90-min deep work for problem sets |
| Deadline urgency | More study time allocated in the days before something is due |
| Exam prep | A review session added the evening before every exam |
| Meals | Breakfast, lunch, and dinner built into every day |
| Family calls | 10-minute "Call home 📱" blocks 2–3 times per week |
| Free time | At least one protected free/social block per day — labeled "Free time — protect this" |
| Weekly review | 30-minute Sunday evening planning block every week |
| Learned behavior | After check-ins, adjusts block timing based on your actual completion patterns |

The agent does not fill every hour. It protects the things that make you human.

---

## What ESCALATE looks like

When SyllabOS hits something it can't handle, it stops and tells you exactly what went wrong:

```
ESCALATE — Cannot extract text from CHEM_5500.pdf
Reason: File appears to be a scanned image or is empty.
Fix: Re-upload as a text-based PDF, or paste the syllabus as a .txt file.
```

```
ESCALATE — Cannot build a realistic schedule for Tuesday
Reason: Work shift 4–9pm + 3 hours of class leaves only 1.5 hours.
         Required study hours for this week need at least 6 hours Tuesday.
Fix: Consider shifting Wednesday's study block or reducing scope this week.
```

No silent failures. No crashes. A precise diagnosis and a clear next step every time.

Run the demo to see it fire live:
```bash
python3 syllabos.py --break
```

---

## Project structure

```
syllabos/
├── syllabos.py              # Entry point — run this
├── src/
│   ├── agent.py              # Main orchestrator — runs all 6 steps
│   ├── nim_client.py         # All NVIDIA NIM API calls (parsing, scheduling, briefings)
│   ├── reader.py             # Extracts text from PDF, DOCX, TXT, MD
│   ├── schedule.py           # Conflict detection and date logic
│   ├── exporter.py           # Google Calendar CSV output
│   ├── memory.py             # Student behavioral profile and weekly check-in
│   ├── display.py            # Terminal colors and logging
│   ├── csv_utils.py          # Reads SyllabOS's own exported CSVs back into data
│   ├── calendar_source.py    # Read-only Google Calendar OAuth + CSV fallback
│   ├── morning_briefing.py   # Gathers today's facts, renders + speaks the briefing
│   ├── trigger.py            # "Good morning, Sunshine" phrase matching + keyboard fallback
│   ├── listener.py           # --listen loop (mic + keyboard)
│   └── voice/                # Speech provider interface — swappable backends
│       ├── base.py           #   TextToSpeech / SpeechToText interfaces
│       ├── nvidia_riva.py    #   NVIDIA Riva (hosted ASR + TTS)
│       ├── system_voice.py   #   Offline fallback (pyttsx3, no API key)
│       └── errors.py
├── scripts/
│   ├── APPSCRIPT.js          # Google Apps Script — paste into Google Sheets
│   └── APPSCRIPT.md          # Apps Script setup notes
├── syllabi/
│   ├── samples/              # Two sample syllabi + work schedule for demo mode
│   │   ├── ENGR3450_Thermodynamics.txt
│   │   ├── CS4820_Machine_Learning.txt
│   │   └── work_schedule.txt
│   ├── samples_broken/       # Empty file that triggers the ESCALATE demo
│   └── (drop your files here)
├── tests/                    # unittest suite — python3 -m unittest discover -s tests -t . -v
├── output/                   # Generated CSV files and student_profile.json — gitignored
├── requirements.txt          # Core — syllabus parsing, scheduling, CSV export
├── requirements-voice.txt    # Optional — --morning / --listen / --calendar-auth
├── .env.example
├── .gitignore
└── README.md
```

---

## Stack

| Component | What it does | Cost |
|-----------|-------------|------|
| NVIDIA NIM | Parses syllabi, builds schedule, writes Sunday + morning briefings | Free tier |
| NVIDIA Riva (speech, optional) | Recognizes "Good morning, Sunshine" and speaks the briefing | Free tier |
| Google Calendar / Apps Script | Creates real calendar events; read-only source for `--morning` | Free |
| Python (pdfminer, python-docx) | Reads PDF and Word files | Free |
| pyttsx3 (optional) | Offline fallback voice — no API key, no network | Free |
| Apache Airflow (optional) | Automates the weekly Sunday briefing run | Free, open source |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `NIM_API_KEY not set` | Add your key to `.env` or run `export NIM_API_KEY=nvapi-xxxx` |
| `No text extracted from PDF` | PDF is a scanned image — open in Google Docs to extract text, save as `.txt` |
| `No deadlines found` | Check that your syllabus file has dates and assignment names in it |
| Timeout on first run | NIM can be slow on the first call — the agent retries at 120s, 150s, 180s automatically |
| Apps Script `401 error` | Your NIM API key in CONFIG is wrong or missing |
| Apps Script: no SyllabOS menu | Close and reload the Google Sheet after saving the script |
| `pip3: command not found` | Try `pip` instead of `pip3` |
| Files not found | Make sure your syllabus files are in the `syllabi/` folder, not a subfolder inside it |
| `--checkin` not updating schedule | Run `python3 syllabos.py` after check-in to rebuild next week with the new profile |
| `--morning` / `--listen` says a package is missing | `pip3 install -r requirements-voice.txt` |
| No microphone found | Connect one, or use the keyboard fallback — press ENTER during `--listen` |
| "NVIDIA speech recognition unavailable" | Check `NVIDIA_ASR_FUNCTION_ID` in `.env` (see "Live voice setup"); keyboard fallback still works |
| "NVIDIA text-to-speech unavailable" | SyllabOS automatically speaks with the offline voice instead — check `NVIDIA_TTS_FUNCTION_ID` in `.env` to fix NVIDIA speech |
| Briefing says "showing your last CSV export" | Google Calendar isn't connected — run `python3 syllabos.py --calendar-auth`, or it's expected if you haven't set it up yet |
| Briefing says your export "doesn't cover today" | Re-run `python3 syllabos.py` to rebuild `weekly_schedule.csv` for the current week |
| Unknown timezone error | Set `STUDENT_TIMEZONE` in `.env` to an IANA name, e.g. `America/New_York` |

---

## Running tests

```bash
python3 -m unittest discover -s tests -t . -v
```

Covers wake-phrase matching, CSV/date parsing, morning-briefing data assembly and its
deterministic fallback text, and the voice-provider failure/fallback paths. No extra dependencies
needed — the suite uses Python's built-in `unittest`.

---

## Built by

**Chanel Power** — Senior ML Engineer, Startup Advisor, Founder of [Mentor Me Collective](https://mentormecollective.org)

Mentor Me Collective is a 501(c)(3) Technical Institute serving 40,000+ members across 120+ countries with 600+ documented career placements.

- GitHub: [@itsChanelML](https://github.com/itsChanelML)
- LinkedIn: [/in/powerc1](https://linkedin.com/in/powerc1)
- Community: [mentormecollective.org](https://mentormecollective.org)
- Twitter/X: [@itsChanelML](https://twitter.com/itsChanelML)

---

*Dominate your semester with NVIDIA AI + speech.*