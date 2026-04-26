# Moodle (IITB) — Site map and navigation

Base URL: `https://moodle.iitb.ac.in`

## Prerequisites

Chrome must be launched with the dedicated debug profile (regular Chrome won't work):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="/Users/harshitsinghbhandari/chrome-debug-moodle" \
  --remote-debugging-port=9222 \
  --remote-allow-origins="*" \
  --no-first-run
```

Set `BU_CDP_WS` to the browser's websocket URL (changes every Chrome restart):

```python
import json, urllib.request
ws = json.loads(urllib.request.urlopen("http://localhost:9222/json/version").read())["webSocketDebuggerUrl"]
```

## URL patterns

All pages use `id=<courseId>` except Competencies which uses `courseid=`.

| Page | URL |
|------|-----|
| Dashboard | `/my/` |
| My courses | `/my/courses.php` |
| Course page | `/course/view.php?id={courseId}` |
| Participants | `/user/index.php?id={courseId}` |
| Grades (redirects to User report) | `/grade/report/index.php?id={courseId}` |
| User grade report | `/grade/report/user/index.php?id={courseId}` |
| Overview grades (all courses) | `/grade/report/overview/index.php` |
| Activities | `/course/overview.php?id={courseId}` |
| Competencies | `/admin/tool/lp/coursecompetencies.php?courseid={courseId}` |
| Assignment | `/mod/assign/view.php?id={activityId}` |
| Folder | `/mod/folder/view.php?id={activityId}` |
| Forum | `/mod/forum/view.php?id={activityId}` |
| Category listing | `/course/index.php?categoryid={catId}` |

Note: `courseId` and `activityId` are different — course IDs identify courses, activity IDs identify items within a course. Activity URLs use `/mod/<type>/view.php?id=`.

## Current enrolled courses (Spring 2025)

| Course ID | Short code | Course name |
|-----------|------------|-------------|
| 8627 | IE 201-2025-2 | Data Analytics, AI/ML Lab |
| 9523 | DE 250-2025-2-ALL | Design Thinking for Innovation |
| 9270 | DE 250-2025-2-S3 | Design Thinking for Innovation |
| 8498 | IE 202-2025-2 | Digital Enterprise Systems Lab |
| 8307 | SC 646-2025-2 | Distributed Optimization and Machine Learning |
| 9412 | IE 204-2025-2 | Feedback and Dynamics |
| 8710 | IE 206-2025-2 | Introduction to Artificial Intelligence and Machine Learning |
| 9440 | IE 208-2025-2 | Nonlinear and Discrete Optimization |
| 8521 | IE 210-2025-2 | Optimization Modeling LAB |
| 8357 | CS 728-2025-2 | Organization of Web Information |

Some courses have two entries (e.g. DE 250 has ALL and S3 sections with different IDs).

## List enrolled courses dynamically

Course listing lives at `/my/courses.php`. Each course is a `.dashboard-card[data-course-id]` card.

```python
import json

goto_url("https://moodle.iitb.ac.in/my/courses.php")
wait_for_load()

courses = json.loads(js("""
(() => {
  const cards = document.querySelectorAll('.dashboard-card[data-course-id]');
  return JSON.stringify([...cards].map(c => ({
    id:   c.getAttribute('data-course-id'),
    name: (c.querySelector('.multiline') || {}).textContent?.trim() || ''
  })));
})()
"""))
```

## Open a course

By ID (fastest — use the table above):

```python
goto_url("https://moodle.iitb.ac.in/course/view.php?id=8627")
wait_for_load()
```

By name (substring match):

```python
target = "Data Analytics"

course_id = js("""
(() => {
  const t = '""" + target.lower() + """';
  const card = [...document.querySelectorAll('.dashboard-card[data-course-id]')]
    .find(c => (c.querySelector('.multiline')?.textContent || '').toLowerCase().includes(t));
  return card ? card.getAttribute('data-course-id') : null;
})()
""")

if course_id:
    goto_url(f"https://moodle.iitb.ac.in/course/view.php?id={course_id}")
    wait_for_load()
```

## Course page structure

Each course page has five tabs in `.secondary-navigation`:

| Tab | URL pattern | Notes |
|-----|-------------|-------|
| Course | `/course/view.php?id=` | Main page with sections and activities |
| Participants | `/user/index.php?id=` | Student roster |
| Grades | `/grade/report/index.php?id=` | Redirects to User report |
| Activities | `/course/overview.php?id=` | Grouped by type: Assignments, Forums, Resources |
| Competencies | `/admin/tool/lp/coursecompetencies.php?courseid=` | Learning competencies |

The Course tab shows activities grouped into weekly sections (e.g. "5 January - 11 January"). The General section at the top holds the main assignments and resources.

## Reading grades

### Single course

```python
goto_url("https://moodle.iitb.ac.in/grade/report/user/index.php?id=8627")
wait_for_load()

grades = json.loads(js("""
(() => {
  const rows = [...document.querySelectorAll('table.generaltable tr')];
  return JSON.stringify(rows.slice(1).map(r => {
    const cells = [...r.querySelectorAll('th, td')];
    return cells.map(c => c.textContent.trim().replace(/\\s+/g, ' '));
  }));
})()
"""))
# Each row: [Grade item, Calculated weight, Grade, Range, Percentage, Feedback, Contribution]
```

Table class: `table generaltable user-grade`. Grade rows have class `cat_<id>`. The last row has class `lastrow` and contains the course total aggregation.

### All courses at once

`/grade/report/overview/index.php` shows a "Courses I am taking" table with columns: Course name, Grade. Includes all semesters.

## Announcements

Each course has an "Announcements" forum (type `forum`) linked from the course page. Forum listing is at `/mod/forum/view.php?id={activityId}`.

- Discussion rows: `tr.discussion[data-discussionid]`
- Discussion link: `.topic a` (has `title` attribute with the post title, `href` to `/mod/forum/discuss.php?d={discussionId}`)
- Individual post content: `[data-region="post-content"]` or `.post-content-container`
- Post timestamp: `time` element inside the post article
- Author: `[data-region="author-name"] a`

The forum listing page shows: Discussion title, Started by, Last post date, Replies count.

## Downloading submission files

Assignment pages (`/mod/assign/view.php?id={activityId}`) show submission status, grade, and submitted files.

- Submission file links: `a[href*="pluginfile.php"][href*="submission_files"]`
- URL pattern: `https://moodle.iitb.ac.in/pluginfile.php/{contextId}/assignsubmission_file/submission_files/{submissionId}/{filename}?forcedownload=1`
- **Files require auth** — raw HTTP requests outside the browser get a login page. Use in-browser `fetch()` via `js()` to download with session cookies, then base64-encode and decode on the Python side.
- After download, `submission_files` links may also appear for other students if you have grading permissions — scope to the user's own submission section.

## Stable selectors

| Element | Selector |
|---------|----------|
| Course card (My courses page) | `.dashboard-card[data-course-id]` |
| Course name inside card | `.dashboard-card .multiline` |
| View Course button | `.view-course-btn[href*="course/view.php"]` |
| Course page tabs | `.secondary-navigation a` |
| Grade table | `table.generaltable.user-grade` |
| Grade row | `table.user-grade tr.cat_<categoryId>` |
| Course total row | `table.user-grade tr.lastrow` |
| Activity link on course page | `.activityname a, .aalink.stretched-link` |
| Activity type from URL | `/mod/<type>/view.php` where type = assign, folder, forum, etc. |
| Forum discussion row | `tr.discussion[data-discussionid]` |
| Forum discussion link | `.topic a` (title attr = post title) |
| Forum post content | `[data-region="post-content"]` |
| Forum post author | `[data-region="author-name"] a` |
| Submission file link | `a[href*="pluginfile.php"][href*="submission_files"]` |

## Traps

- `[data-course-id]` appears on nested child elements too, not just the top-level card. Always scope to `.dashboard-card[data-course-id]` to avoid duplicates (6 nested elements per card).
- The "Recent" dropdown in the top nav bar also has `a.dropdown-item[href*="course/view.php"]` links — these are quick-access, not the full listing (only shows ~5 recent courses).
- Grade item text is prefixed with the activity type (e.g. "AssignmentLab 03 submission") — the word "Assignment" is baked into the cell, not a separate column.
- The grade cell includes "Actions Grade analysis" text appended to the numeric grade — strip it when parsing.
- `/grade/report/index.php` redirects to `/grade/report/user/index.php` — use the latter directly.
- Course sections on the course page appear duplicated in the DOM (once in main content, once in the course index sidebar). Activities also appear doubled. Use `.course-content .section` or deduplicate by href.
- The websocket URL in `BU_CDP_WS` changes on every Chrome restart. Re-fetch from `http://localhost:9222/json/version` if connection fails.
- The overview grades page (`/grade/report/overview/index.php`) shows raw point totals without normalisation — different courses have different scales (100, 1000, etc.).
- **Course cards render lazily (~15 seconds after page load).** `document.readyState` is `complete` long before `.dashboard-card[data-course-id]` appears in the DOM. Poll for the selector, don't rely on `wait_for_load()` alone.
- Discord webhooks reject `urllib` requests (Cloudflare error 1010). Use `httpx` instead.
