# SyllaClaw 📚
### Drop Your Syllabus. Organize Your Life.

**Built for College & Graduate Students. Free to build. Free to run.**

> Nobody warned you that the havoc of Week 8 was coming. SyllaClaw encodes that knowledge — and makes it available to every student, for free.

---

## What it does

You drop your syllabus files into a folder. SyllaClaw reads every one of them, extracts every deadline and exam, builds a complete time-blocked weekly schedule around your job and your life, flags your brutal weeks before they arrive, and outputs everything as a CSV that imports directly into Google Calendar.

**You get:**
- Every deadline, exam, project, and quiz loaded into Google Calendar with descriptions
- A complete time-blocked weekly schedule — study, sleep, work, meals, family calls, and free time
- Work shifts locked in as non-negotiable blocks — the agent will never schedule over them
- Heavy weeks flagged before they hit you, with specific reschedule suggestions
- A Sunday evening briefing that tells you exactly what to focus on next week
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

SyllaClaw runs six steps in sequence:

```
Step 1 — parse_syllabi        Read every file in your folder. Extract all deadlines with estimated study hours.
Step 2 — parse_work_schedule  Find your work schedule file. Lock those shifts as non-negotiable.
Step 3 — detect_conflicts     Find weeks where 3+ deliverables pile up. Flag them before you commit to anything.
Step 4 — build_schedule       Build your complete week: study blocks, sleep, work, meals, family calls, free time.
Step 5 — export_csv           Output Google Calendar-compatible CSV files.
Step 6 — weekly_briefing      Write a personalized Sunday evening briefing for the week ahead.
```

When something goes wrong the agent doesn't crash silently. It stops and tells you exactly what failed and what to do next — this is called an **ESCALATE**. You'll see it fire live when you run `python3 syllaclaw.py --break`.

---

## How SyllaClaw learns your behavior

After your first week, run the Sunday check-in:

```bash
python3 syllaclaw.py --checkin
```

Five questions. Two minutes. SyllaClaw updates your `student_profile.json` and uses it to build a smarter schedule next week.

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

After a few weeks SyllaClaw knows you work best Wednesday mornings, that your Starbucks shift always runs 30 minutes over, and that you'll always say yes to a SHPE event. It builds around that — not around who you wish you were.

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
git clone https://github.com/itsChanelML/syllaclaw
cd syllaclaw
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
python3 syllaclaw.py

# Add your name for personalized output
python3 syllaclaw.py --name "Alex Rivera"

# Point at a different folder
python3 syllaclaw.py --folder ./my_files

# Run on the sample syllabi to see how it works before using your own
python3 syllaclaw.py --demo

# Trigger the ESCALATE beat — shows what happens when a file is unreadable
python3 syllaclaw.py --break

# Sunday check-in — tell SyllaClaw how your week went
python3 syllaclaw.py --checkin
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
3. Name it `SyllaClaw`

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

A **SyllaClaw** menu will appear in your Sheet toolbar.

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

Click **SyllaClaw** in the menu and choose:
- **4. Full Run (Steps 1–3)** — does everything at once

Or step by step:
1. **1. Parse My Syllabi** — reads all Syllabus tabs, extracts deadlines into a `Deadlines` tab
2. **2. Build My Week** — builds your time-blocked schedule into a `Weekly Schedule` tab
3. **3. Push to Google Calendar** — creates real events in a new `SyllaClaw` calendar instantly

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

SyllaClaw will never schedule a study block during a shift. Work hours are locked.

---

## How the weekly schedule is built

SyllaClaw uses Meta's Llama 3.2 90B model via NVIDIA NIM to reason over your full week, one day at a time:

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

When SyllaClaw hits something it can't handle, it stops and tells you exactly what went wrong:

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
python3 syllaclaw.py --break
```

---

## Project structure

```
syllaclaw/
├── syllaclaw.py              # Entry point — run this
├── src/
│   ├── agent.py              # Main orchestrator — runs all 6 steps
│   ├── nim_client.py         # All NVIDIA NIM API calls
│   ├── reader.py             # Extracts text from PDF, DOCX, TXT, MD
│   ├── schedule.py           # Conflict detection and date logic
│   ├── exporter.py           # Google Calendar CSV output
│   ├── memory.py             # Student behavioral profile and weekly check-in
│   └── display.py            # Terminal colors and logging
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
├── output/                   # Generated CSV files and student_profile.json — gitignored
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Stack

| Component | What it does | Cost |
|-----------|-------------|------|
| NVIDIA NIM | Parses syllabi, builds schedule, writes Sunday briefing | Free tier |
| Google Calendar / Apps Script | Creates real calendar events | Free |
| Python (pdfminer, python-docx) | Reads PDF and Word files | Free |
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
| Apps Script: no SyllaClaw menu | Close and reload the Google Sheet after saving the script |
| `pip3: command not found` | Try `pip` instead of `pip3` |
| Files not found | Make sure your syllabus files are in the `syllabi/` folder, not a subfolder inside it |
| `--checkin` not updating schedule | Run `python3 syllaclaw.py` after check-in to rebuild next week with the new profile |

---

## Built by

**Chanel Power** — Senior ML Engineer, Startup Advisor, Founder of [Mentor Me Collective](https://mentormecollective.org)

Mentor Me Collective is a 501(c)(3) Technical Institute serving 40,000+ members across 120+ countries with 600+ documented career placements.

- GitHub: [@itsChanelML](https://github.com/itsChanelML)
- LinkedIn: [/in/powerc1](https://linkedin.com/in/powerc1)
- Community: [mentormecollective.org](https://mentormecollective.org)
- Twitter/X: [@itsChanelML](https://twitter.com/itsChanelML)

---

*Drop your syllabus. Organize your life.*