# moodle-automated

Personal automation for [IITB Moodle](https://moodle.iitb.ac.in) — grades, announcements, submissions, and more. Built on top of [browser-harness](https://github.com/browser-use/browser-harness) (CDP control of a real Chrome session).

## What it does

```python
from moodle.moodle import *

connect()
grades("data analytics")           # parsed grade table, clean dicts
announcements("feedback", n=5)     # latest posts from any course forum
download_submission("IE 201", "lab 02")  # download your submitted files
courses()                          # all enrolled courses with IDs
all_grades()                       # overview grades across every semester
post_discord(fmt_grades(...))      # push to Discord webhook
```

No selenium. No playwright. No headless browser. Connects to your real logged-in Chrome via CDP.

## Setup

**1. Clone and install**

```bash
git clone https://github.com/harshitsinghbhandari/moodle-automated.git
cd moodle-automated
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**2. Launch Chrome with the debug profile**

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$HOME/chrome-debug-moodle" \
  --remote-debugging-port=9222 \
  --remote-allow-origins="*" \
  --no-first-run
```

Log into Moodle in this browser. The session persists across restarts.

**3. Configure `.env`** (optional, for Discord)

```bash
cp .env.example .env
# Add your webhook URL:
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**4. Use it**

```python
from moodle.moodle import *

connect()  # auto-detects Chrome on port 9222

# Check grades
g = grades("data analytics")
print(fmt_grades(g, "Data Analytics"))

# Get latest announcements
anns = announcements("optimization modeling", n=5)
print(fmt_announcements(anns))

# Download a submission
files = download_submission("IE 201", "lab 02")

# Post anything to Discord
post_discord(fmt_grades(g, "Data Analytics"))
```

## API

| Function | Description |
|----------|-------------|
| `connect()` | Connect to Chrome on port 9222, start the CDP daemon |
| `courses()` | List all enrolled courses `[{id, name}, ...]` |
| `open_course(query)` | Navigate to a course by ID or name substring |
| `grades(query)` | Get parsed grades for a course |
| `all_grades()` | Overview grades for all courses, all semesters |
| `activities(query)` | List assignments/forums/resources on a course page |
| `announcements(query, n=5)` | Get latest n announcements from a course forum |
| `download_submission(course, assignment)` | Download submitted files to `downloads/` |
| `screenshot(path)` | Screenshot the current page |
| `post_discord(msg)` | Post to Discord webhook from `.env` |
| `fmt_grades(grades, name)` | Format grades for display |
| `fmt_announcements(anns, name)` | Format announcements for display |

All functions that take a course accept an **int ID**, **string ID**, or **name substring** (case-insensitive).

## Project structure

```
moodle/
  moodle.py        — all the Moodle-specific functions
  navigation.md    — selectors, URL patterns, course ID table, traps
helpers.py         — low-level CDP primitives (click, type, screenshot, etc.)
daemon.py          — CDP websocket bridge
admin.py           — daemon lifecycle management
domain-skills/     — browser-harness skills for other sites
.env               — secrets (gitignored)
downloads/         — downloaded submissions (gitignored)
```

## Built on

[browser-harness](https://github.com/browser-use/browser-harness) — direct CDP control of a real browser, ~600 lines of Python.
