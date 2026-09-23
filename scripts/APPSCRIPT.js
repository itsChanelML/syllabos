/**
 * SyllabOS — Google Apps Script Implementation
 * ==============================================
 * For students who prefer to work entirely in Google Drive
 * without installing anything on their computer.
 *
 * HOW TO SET UP (one time):
 * 1. Create a new Google Sheet
 * 2. Click Extensions → Apps Script
 * 3. Paste this entire file into the editor
 * 4. Replace YOUR_NIM_API_KEY_HERE with your free NVIDIA NIM key
 *    Get it at: https://build.nvidia.com (no credit card required)
 * 5. Click Save (Ctrl+S)
 * 6. Reload your Google Sheet
 * 7. A new "SyllabOS" menu will appear in your Sheet
 *
 * HOW TO USE:
 * 1. Put your syllabus text in Sheet tabs named "Syllabus_1", "Syllabus_2", etc.
 *    OR paste your syllabus text directly into the "Input" tab
 * 2. Click SyllabOS → Parse My Syllabi
 * 3. Your deadlines appear in the "Deadlines" tab
 * 4. Click SyllabOS → Build My Week
 * 5. Your weekly schedule appears in the "Weekly Schedule" tab
 * 6. Click SyllabOS → Push to Google Calendar (events are created instantly!)
 *
 * FREE TO USE. Open source. github.com/itsChanelML/syllabos
 */

// ─────────────────────────────────────────────────────────────────────────────
// CONFIGURATION — change these to match your semester
// ─────────────────────────────────────────────────────────────────────────────
const CONFIG = {
  NIM_API_KEY:     "YOUR_NIM_API_KEY_HERE",   // Get free at build.nvidia.com
  STUDENT_NAME:    "Your Name",               // Your first and last name
  SEMESTER_START:  "2026-01-12",              // First day of classes
  SEMESTER_END:    "2026-05-15",              // Last day of finals
  WAKE_TIME:       "07:00",                   // What time you wake up
  SLEEP_TIME:      "23:00",                   // What time you go to sleep
  CALENDAR_NAME:   "SyllabOS",               // Name of calendar to create
};

const NIM_MODEL    = "nvidia/llama-3.3-nemotron-super-49b-v1";
const NIM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions";

// ─────────────────────────────────────────────────────────────────────────────
// MENU SETUP — runs when the Sheet opens
// ─────────────────────────────────────────────────────────────────────────────
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🦾 SyllabOS")
    .addItem("1. Parse My Syllabi",        "parseSyllabi")
    .addSeparator()
    .addItem("2. Build My Week",           "buildWeek")
    .addSeparator()
    .addItem("3. Push to Google Calendar", "pushToCalendar")
    .addSeparator()
    .addItem("4. Full Run (Steps 1–3)",    "fullRun")
    .addSeparator()
    .addItem("⚙ Setup Instructions",      "showSetup")
    .addToUi();
}


// ─────────────────────────────────────────────────────────────────────────────
// STEP 1 — PARSE SYLLABI
// ─────────────────────────────────────────────────────────────────────────────
function parseSyllabi() {
  if (!validateConfig()) return;

  const ui    = SpreadsheetApp.getUi();
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const toast = (msg) => ss.toast(msg, "SyllabOS", 5);

  toast("Reading your syllabi...");

  // Collect syllabus text from all relevant sheets
  const syllabusSheets = [];
  ss.getSheets().forEach(sheet => {
    const name = sheet.getName();
    if (name.toLowerCase().startsWith("syllabus") ||
        name.toLowerCase().startsWith("course") ||
        name === "Input") {
      const text = sheet.getRange("A1").getValue() ||
                   sheet.getDataRange().getValues().flat().filter(Boolean).join("\n");
      if (text && text.toString().trim().length > 50) {
        syllabusSheets.push({ name, text: text.toString() });
      }
    }
  });

  if (syllabusSheets.length === 0) {
    ui.alert(
      "No Syllabi Found",
      "Please add a sheet tab named 'Syllabus_1' and paste your syllabus text into cell A1.\n\n" +
      "You can add multiple syllabi in tabs named Syllabus_1, Syllabus_2, etc.",
      ui.ButtonSet.OK
    );
    return;
  }

  toast(`Found ${syllabusSheets.length} syllabus/syllabi. Parsing with NVIDIA NemoClaw...`);

  const allDeadlines = [];

  syllabusSheets.forEach(({ name, text }) => {
    toast(`Parsing ${name}...`);
    try {
      const deadlines = nimParseSyllabus(text, name);
      allDeadlines.push(...deadlines);
    } catch (e) {
      ss.toast(`Error parsing ${name}: ${e.message}`, "Warning", 8);
    }
  });

  if (allDeadlines.length === 0) {
    ui.alert("No deadlines found. Check that your syllabus text contains assignment dates.");
    return;
  }

  // Sort by date
  allDeadlines.sort((a, b) => (a.date || "").localeCompare(b.date || ""));

  // Write to Deadlines sheet
  writeDeadlinesSheet(allDeadlines);

  toast(`✓ ${allDeadlines.length} deadlines found across ${syllabusSheets.length} course(s). See the Deadlines tab.`);
  ui.alert(
    "✓ Syllabi Parsed!",
    `Found ${allDeadlines.length} deadlines across ${syllabusSheets.length} course(s).\n\n` +
    "Check the 'Deadlines' tab to review them.\n\n" +
    "Next: Run SyllabOS → Build My Week",
    ui.ButtonSet.OK
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// STEP 2 — BUILD WEEKLY SCHEDULE
// ─────────────────────────────────────────────────────────────────────────────
function buildWeek() {
  if (!validateConfig()) return;

  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Read deadlines from the Deadlines sheet
  const deadlinesSheet = ss.getSheetByName("Deadlines");
  if (!deadlinesSheet) {
    ui.alert("No deadlines found. Please run 'Parse My Syllabi' first.");
    return;
  }

  const deadlines = readDeadlinesSheet(deadlinesSheet);
  if (deadlines.length === 0) {
    ui.alert("Deadlines sheet is empty. Please run 'Parse My Syllabi' first.");
    return;
  }

  // Read work schedule if it exists
  const workSheet    = ss.getSheetByName("Work Schedule");
  const workShifts   = workSheet ? readWorkScheduleSheet(workSheet) : [];

  // Get next Monday as week start
  const weekStart = getNextMonday();

  ss.toast("Building your time-blocked week with NVIDIA NemoClaw...", "SyllabOS", 10);

  // Get upcoming deadlines (next 14 days)
  const upcoming = deadlines.filter(d => {
    if (!d.date) return false;
    const due  = new Date(d.date);
    const ws   = new Date(weekStart);
    const diff = (due - ws) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 14;
  });

  let blocks;
  try {
    blocks = nimBuildSchedule(CONFIG.STUDENT_NAME, weekStart, upcoming, workShifts);
  } catch (e) {
    ui.alert("Error building schedule: " + e.message);
    return;
  }

  // Write to Weekly Schedule sheet
  writeScheduleSheet(blocks, weekStart);

  ss.toast(`✓ ${blocks.length} time blocks built for the week of ${weekStart}.`, "SyllabOS", 8);
  ui.alert(
    "✓ Week Built!",
    `${blocks.length} time blocks created for the week of ${weekStart}.\n\n` +
    "Check the 'Weekly Schedule' tab to review.\n\n" +
    "Next: Run SyllabOS → Push to Google Calendar",
    ui.ButtonSet.OK
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// STEP 3 — PUSH TO GOOGLE CALENDAR
// ─────────────────────────────────────────────────────────────────────────────
function pushToCalendar() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const scheduleSheet  = ss.getSheetByName("Weekly Schedule");
  const deadlineSheet  = ss.getSheetByName("Deadlines");

  if (!scheduleSheet && !deadlineSheet) {
    ui.alert("Nothing to push. Run Steps 1 and 2 first.");
    return;
  }

  const confirm = ui.alert(
    "Push to Google Calendar?",
    `This will create events in a new Google Calendar called "${CONFIG.CALENDAR_NAME}".\n\n` +
    "This is safe — it will not modify your existing calendars.\n\n" +
    "Proceed?",
    ui.ButtonSet.YES_NO
  );
  if (confirm !== ui.Button.YES) return;

  ss.toast("Creating Google Calendar events...", "SyllabOS", 10);

  // Get or create SyllabOS calendar
  let calendar = CalendarApp.getCalendarsByName(CONFIG.CALENDAR_NAME)[0];
  if (!calendar) {
    calendar = CalendarApp.createCalendar(CONFIG.CALENDAR_NAME, {
      color:   CalendarApp.Color.TEAL,
      summary: "Created by SyllabOS — your academic life agent",
    });
  }

  let created = 0;
  let errors  = 0;

  // Push weekly schedule blocks
  if (scheduleSheet) {
    const data = scheduleSheet.getDataRange().getValues();
    // Skip header row
    for (let i = 1; i < data.length; i++) {
      const [date, startTime, endTime, title, type, course, notes] = data[i];
      if (!date || !startTime || !endTime || !title) continue;
      try {
        const startDt = parseDateTime(date, startTime);
        const endDt   = parseDateTime(date, endTime);
        if (!startDt || !endDt || endDt <= startDt) continue;

        const event = calendar.createEvent(title, startDt, endDt, {
          description: [
            course ? `Course: ${course}` : "",
            type   ? `Type: ${type}`     : "",
            notes  ? notes               : "",
            "Added by SyllabOS",
          ].filter(Boolean).join(" | "),
        });

        // Set color based on type
        const colorMap = {
          "study":  CalendarApp.EventColor.TEAL,
          "exam":   CalendarApp.EventColor.RED,
          "work":   CalendarApp.EventColor.YELLOW,
          "sleep":  CalendarApp.EventColor.GRAPHITE,
          "family": CalendarApp.EventColor.MAUVE,
          "free":   CalendarApp.EventColor.GREEN,
          "meal":   CalendarApp.EventColor.CYAN,
          "review": CalendarApp.EventColor.RED,
        };
        if (colorMap[type]) {
          event.setColor(colorMap[type]);
        }

        created++;
      } catch (e) {
        errors++;
      }
    }
  }

  // Push semester deadlines from Deadlines sheet
  if (deadlineSheet) {
    const data = deadlineSheet.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      const [course, title, date, time, type, weight, hours, notes] = data[i];
      if (!date || !title) continue;
      try {
        const startDt = parseDateTime(date, time || "23:00");
        const endDt   = parseDateTime(date, bumpTime(time || "23:00", 30));
        if (!startDt || !endDt) continue;

        const typeEmoji = { exam:"🔴 EXAM", homework:"📝 HW", project:"🔧 PROJECT", quiz:"⚡ QUIZ", lab:"🧪 LAB" };
        const prefix    = typeEmoji[type] || "📌";
        const eventTitle = `${prefix}: ${course} — ${title}`;

        calendar.createEvent(eventTitle, startDt, endDt, {
          description: [
            `Course: ${course}`,
            weight ? `Weight: ${weight}` : "",
            hours  ? `Est. study time: ${hours} hour(s)` : "",
            notes  ? notes : "",
            "Added by SyllabOS",
          ].filter(Boolean).join(" | "),
        });
        created++;
      } catch (e) {
        errors++;
      }
    }
  }

  const msg = errors > 0
    ? `✓ ${created} events created. ${errors} errors — some events may have been skipped.`
    : `✓ ${created} events created in your "${CONFIG.CALENDAR_NAME}" calendar!`;

  ss.toast(msg, "SyllabOS", 10);
  ui.alert(
    "✓ Calendar Updated!",
    `${created} events added to Google Calendar.\n\n` +
    `Open Google Calendar to see your semester.\n\n` +
    "Your SyllabOS calendar is color-coded:\n" +
    "🟦 Study blocks\n🔴 Exams\n🟡 Work shifts\n🟢 Free time\n🟣 Family calls",
    ui.ButtonSet.OK
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// FULL RUN — Steps 1–3 in sequence
// ─────────────────────────────────────────────────────────────────────────────
function fullRun() {
  if (!validateConfig()) return;
  parseSyllabi();
  Utilities.sleep(2000);
  buildWeek();
  Utilities.sleep(2000);
  pushToCalendar();
}


// ─────────────────────────────────────────────────────────────────────────────
// NIM API CALLS
// ─────────────────────────────────────────────────────────────────────────────
function nimCall(prompt, maxTokens = 1500, temperature = 0.1) {
  const payload = {
    model:       NIM_MODEL,
    messages:    [{ role: "user", content: prompt }],
    max_tokens:  maxTokens,
    temperature: temperature,
  };

  const options = {
    method:      "post",
    contentType: "application/json",
    headers:     { "Authorization": `Bearer ${CONFIG.NIM_API_KEY}` },
    payload:     JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(NIM_ENDPOINT, options);
  if (response.getResponseCode() !== 200) {
    throw new Error(`NIM API error ${response.getResponseCode()}: ${response.getContentText().substring(0, 200)}`);
  }

  const data = JSON.parse(response.getContentText());
  return data.choices[0].message.content.trim();
}


function nimParseSyllabus(syllabusText, courseName) {
  const prompt = `Extract every graded item and deadline from this syllabus.
Semester: ${CONFIG.SEMESTER_START} to ${CONFIG.SEMESTER_END}.
Course: ${courseName}

Return a JSON array only. Each item must have exactly these fields:
- course: "${courseName}"
- title: short name (e.g. "Homework 1", "Midterm Exam")
- date: YYYY-MM-DD. If only a week number, use the Friday of that week.
- time: HH:MM if specified, else "23:59"
- type: exactly one of: homework | exam | project | quiz | lab | reading | other
- weight: grading % if mentioned, else ""
- estimated_hours: integer 1–20
- notes: brief context, else ""

Return ONLY the JSON array. No explanation. No markdown.

SYLLABUS:
${syllabusText.substring(0, 5000)}`;

  const raw = nimCall(prompt, 2000);
  return extractJSON(raw);
}


function nimBuildSchedule(studentName, weekStart, upcoming, workShifts) {
  const deadlineStr = upcoming.map(d =>
    `- ${d.course}: ${d.title} | Due: ${d.date} | Type: ${d.type} | Est: ${d.estimated_hours || 2}hrs`
  ).join("\n") || "None this week";

  const shiftsStr = workShifts.map(s =>
    `- ${s.day}: ${s.start_time} – ${s.end_time} (${s.hours} hrs)`
  ).join("\n") || "No work shifts";

  const prompt = `Build a complete time-blocked weekly schedule for ${studentName}.
Week of: ${weekStart} (Monday through Sunday)
Wake time: ${CONFIG.WAKE_TIME} | Bedtime: ${CONFIG.SLEEP_TIME}

UPCOMING DEADLINES (next 14 days):
${deadlineStr}

WORK SHIFTS (non-negotiable):
${shiftsStr}

Rules:
1. Never schedule during work shifts
2. Study blocks: 25-min Pomodoro for reading/memorization, 90-min deep work for problem sets
3. Prioritize items due soonest
4. Add 2-3 "Call home 📱" blocks — 10 minutes each
5. Add meals: Breakfast 30min, Lunch 45min, Dinner 45min
6. Protect at least one "Free time — protect this" block per day on non-work days
7. Sunday evening: 30-min "Weekly Review" block
8. Cover every waking hour from ${CONFIG.WAKE_TIME} to ${CONFIG.SLEEP_TIME}

Return a JSON array. Each block:
- day: full day name
- start_time: HH:MM (24-hour)
- end_time: HH:MM (24-hour)
- title: descriptive name
- type: study | work | sleep | social | family | meal | review | free | org
- course: course name if study block, else ""
- notes: one coaching tip if relevant, else ""

Return ONLY the JSON array. No explanation.`;

  const raw = nimCall(prompt, 3000, 0.15);
  return extractJSON(raw);
}


// ─────────────────────────────────────────────────────────────────────────────
// SHEET READ/WRITE HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function writeDeadlinesSheet(deadlines) {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName("Deadlines");
  if (!sheet) sheet = ss.insertSheet("Deadlines");
  sheet.clearContents();

  const headers = ["Course","Title","Date","Time","Type","Weight","Est. Hours","Notes"];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight("bold").setBackground("#1D9E75").setFontColor("#FFFFFF");

  const rows = deadlines.map(d => [
    d.course || "", d.title || "", d.date || "", d.time || "23:59",
    d.type   || "", d.weight || "", d.estimated_hours || 2, d.notes || "",
  ]);

  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }

  // Format date column
  sheet.getRange(2, 3, rows.length, 1).setNumberFormat("yyyy-mm-dd");

  // Freeze header
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, headers.length);
}


function readDeadlinesSheet(sheet) {
  const data    = sheet.getDataRange().getValues();
  const headers = data[0].map(h => h.toString().toLowerCase().trim());
  const deadlines = [];

  for (let i = 1; i < data.length; i++) {
    const row = {};
    headers.forEach((h, j) => { row[h] = data[i][j]; });
    if (row.title && row.date) {
      deadlines.push({
        course:          row.course          || "",
        title:           row.title           || "",
        date:            formatDate(row.date),
        time:            row.time            || "23:59",
        type:            row.type            || "other",
        weight:          row.weight          || "",
        estimated_hours: row["est. hours"]   || 2,
        notes:           row.notes           || "",
      });
    }
  }
  return deadlines;
}


function readWorkScheduleSheet(sheet) {
  const data    = sheet.getDataRange().getValues();
  const headers = data[0].map(h => h.toString().toLowerCase().trim());
  const shifts  = [];

  for (let i = 1; i < data.length; i++) {
    const row = {};
    headers.forEach((h, j) => { row[h] = data[i][j]; });
    if (row.day && row["start time"]) {
      shifts.push({
        day:        row.day         || "",
        start_time: row["start time"] || "09:00",
        end_time:   row["end time"]   || "17:00",
        hours:      row.hours        || 8,
        title:      row.title        || "Work Shift",
        type:       "work",
      });
    }
  }
  return shifts;
}


function writeScheduleSheet(blocks, weekStart) {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName("Weekly Schedule");
  if (!sheet) sheet = ss.insertSheet("Weekly Schedule");
  sheet.clearContents();

  const headers = ["Date","Start Time","End Time","Title","Type","Course","Notes"];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight("bold").setBackground("#1D9E75").setFontColor("#FFFFFF");

  // Map day names to dates
  const dayOffset = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 };
  const ws = new Date(weekStart + "T00:00:00");

  const rows = [];
  blocks.forEach(b => {
    const offset = dayOffset[b.day] || 0;
    const date   = new Date(ws);
    date.setDate(ws.getDate() + offset);
    const dateStr = Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyy-MM-dd");
    rows.push([dateStr, b.start_time || "", b.end_time || "", b.title || "", b.type || "", b.course || "", b.notes || ""]);
  });

  // Sort by date then time
  rows.sort((a, b) => (a[0] + a[1]).localeCompare(b[0] + b[1]));

  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }

  // Color rows by type
  const typeColors = {
    study:  "#E1F5EE", work:   "#FDF0D5", sleep: "#F5F5F4",
    family: "#EEEDFE", free:   "#E8F5E2", meal:  "#E8F4FD",
    review: "#FDECEA", social: "#E8F5E2",
  };

  rows.forEach((row, i) => {
    const color = typeColors[row[4]] || "#FFFFFF";
    sheet.getRange(i + 2, 1, 1, headers.length).setBackground(color);
  });

  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, headers.length);
}


// ─────────────────────────────────────────────────────────────────────────────
// UTILITY FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────
function extractJSON(raw) {
  // Strip markdown fences
  raw = raw.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();

  // Find outermost JSON structure
  const startArr = raw.indexOf("[");
  const endArr   = raw.lastIndexOf("]") + 1;
  if (startArr >= 0 && endArr > startArr) {
    try { return JSON.parse(raw.substring(startArr, endArr)); } catch (e) {}
  }

  const startObj = raw.indexOf("{");
  const endObj   = raw.lastIndexOf("}") + 1;
  if (startObj >= 0 && endObj > startObj) {
    try { return JSON.parse(raw.substring(startObj, endObj)); } catch (e) {}
  }

  throw new Error("Could not extract JSON from NIM response");
}


function getNextMonday() {
  const today = new Date();
  const day   = today.getDay(); // 0=Sun, 1=Mon
  const daysUntilMonday = day === 0 ? 1 : (8 - day) % 7 || 7;
  today.setDate(today.getDate() + daysUntilMonday);
  return Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy-MM-dd");
}


function parseDateTime(dateVal, timeStr) {
  try {
    let dateStr = typeof dateVal === "string"
      ? dateVal
      : Utilities.formatDate(new Date(dateVal), Session.getScriptTimeZone(), "yyyy-MM-dd");

    const [h, m] = (timeStr || "09:00").split(":").map(Number);
    const dt     = new Date(dateStr + "T00:00:00");
    dt.setHours(h || 9, m || 0, 0, 0);
    return dt;
  } catch (e) {
    return null;
  }
}


function bumpTime(timeStr, minutesToAdd) {
  try {
    const [h, m] = timeStr.split(":").map(Number);
    const total  = h * 60 + m + minutesToAdd;
    const nh     = Math.floor(total / 60) % 24;
    const nm     = total % 60;
    return `${String(nh).padStart(2,"0")}:${String(nm).padStart(2,"0")}`;
  } catch (e) {
    return timeStr;
  }
}


function formatDate(val) {
  if (!val) return "";
  if (typeof val === "string") return val.substring(0, 10);
  try {
    return Utilities.formatDate(new Date(val), Session.getScriptTimeZone(), "yyyy-MM-dd");
  } catch (e) {
    return "";
  }
}


function validateConfig() {
  if (CONFIG.NIM_API_KEY === "YOUR_NIM_API_KEY_HERE" || !CONFIG.NIM_API_KEY) {
    SpreadsheetApp.getUi().alert(
      "API Key Required",
      "Please set your free NVIDIA NIM API key in the CONFIG section at the top of the script.\n\n" +
      "Get your free key at: https://build.nvidia.com\n\n" +
      "Then replace YOUR_NIM_API_KEY_HERE with your actual key.",
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    return false;
  }
  return true;
}


function showSetup() {
  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 20px; color: #111; }
      h2 { color: #1D9E75; }
      h3 { color: #085041; }
      code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
      .step { background: #E1F5EE; padding: 12px; border-left: 4px solid #1D9E75; margin: 12px 0; border-radius: 0 6px 6px 0; }
      a { color: #1D9E75; }
    </style>
    <h2>🦾 SyllabOS Setup Guide</h2>

    <div class="step">
      <h3>Step 1 — Get your free NVIDIA NIM key</h3>
      <p>Go to <a href="https://build.nvidia.com" target="_blank">build.nvidia.com</a><br>
      Sign in (free account, no credit card)<br>
      Search: <code>llama-3.3-nemotron-super-49b-v1</code><br>
      Click Get API Key — it starts with <code>nvapi-</code></p>
    </div>

    <div class="step">
      <h3>Step 2 — Add your key to the script</h3>
      <p>Click Extensions → Apps Script<br>
      Find the line: <code>NIM_API_KEY: "YOUR_NIM_API_KEY_HERE"</code><br>
      Replace with your actual key<br>
      Also update <code>STUDENT_NAME</code> with your name<br>
      Click Save (Ctrl+S)</p>
    </div>

    <div class="step">
      <h3>Step 3 — Add your syllabi</h3>
      <p>Create sheet tabs named <code>Syllabus_1</code>, <code>Syllabus_2</code>, etc.<br>
      Paste your syllabus text into cell A1 of each tab<br>
      OR upload syllabi to Google Drive and copy-paste the text</p>
    </div>

    <div class="step">
      <h3>Step 4 — Run SyllabOS</h3>
      <p>Click the <strong>SyllabOS menu</strong> that appeared in your Sheet<br>
      Click <strong>4. Full Run</strong> to do everything at once<br>
      Or run each step individually</p>
    </div>

    <p style="margin-top:20px; color: #666;">
      Free to use. Open source.<br>
      <a href="https://github.com/itsChanelML/syllabos">github.com/itsChanelML/syllabos</a>
    </p>
  `)
  .setWidth(480)
  .setHeight(560);

  SpreadsheetApp.getUi().showModalDialog(html, "SyllabOS Setup");
}