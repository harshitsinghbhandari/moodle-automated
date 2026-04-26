"""Moodle helpers — thin wrappers around browser-harness for moodle.iitb.ac.in."""

import json
import os
import re
import urllib.request
from pathlib import Path

# browser-harness helpers are importable because run.py / helpers.py are at repo root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin import ensure_daemon
from helpers import (
    capture_screenshot,
    goto_url,
    js,
    list_tabs,
    page_info,
    wait,
    wait_for_load,
)

BASE = "https://moodle.iitb.ac.in"
CDP_PORT = 9222


def _wait_for(selector, timeout=10):
    """Poll until a CSS selector matches at least one element."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        count = js(f"document.querySelectorAll('{selector}').length")
        if count and count > 0:
            return count
        wait(0.5)
    return 0

# ── Course ID table (Spring 2025) ──────────────────────────────────────────
# Hardcoded for fast lookup. Update when semesters change.
COURSES = {
    8627: "Data Analytics, AI/ML Lab",
    9523: "Design Thinking for Innovation",
    9270: "Design Thinking for Innovation (S3)",
    8498: "Digital Enterprise Systems Lab",
    8307: "Distributed Optimization and Machine Learning",
    9412: "Feedback and Dynamics",
    8710: "Introduction to Artificial Intelligence and Machine Learning",
    9440: "Nonlinear and Discrete Optimization",
    8521: "Optimization Modeling LAB",
    8357: "Organization of Web Information",
}

SHORT_CODES = {
    8627: "IE 201",
    9523: "DE 250-ALL",
    9270: "DE 250-S3",
    8498: "IE 202",
    8307: "SC 646",
    9412: "IE 204",
    8710: "IE 206",
    9440: "IE 208",
    8521: "IE 210",
    8357: "CS 728",
}


def _load_env():
    p = Path(__file__).resolve().parent.parent / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def connect():
    """Auto-fetch WS URL from Chrome on port 9222, set env, start daemon."""
    _load_env()
    try:
        raw = urllib.request.urlopen(
            f"http://localhost:{CDP_PORT}/json/version", timeout=5
        ).read()
        ws_url = json.loads(raw)["webSocketDebuggerUrl"]
    except Exception as e:
        raise RuntimeError(
            f"Cannot reach Chrome on port {CDP_PORT}. "
            "Launch it with:\n"
            '  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\\n'
            '    --user-data-dir="/Users/harshitsinghbhandari/chrome-debug-moodle" \\\n'
            f"    --remote-debugging-port={CDP_PORT} \\\n"
            '    --remote-allow-origins="*" --no-first-run'
        ) from e

    os.environ["BU_CDP_WS"] = ws_url
    ensure_daemon()
    return ws_url


def _resolve_course(course):
    """Accept int ID, str ID, or name substring. Return int course ID."""
    if isinstance(course, int):
        return course
    if isinstance(course, str) and course.isdigit():
        return int(course)
    # Substring match on name or short code
    q = course.lower()
    for cid, name in COURSES.items():
        if q in name.lower() or q in SHORT_CODES.get(cid, "").lower():
            return cid
    raise ValueError(f"No course matching '{course}'. Known: {list(COURSES.values())}")


def courses():
    """Return enrolled courses from the live page. Moodle renders cards lazily (~15s)."""
    goto_url(f"{BASE}/my/courses.php")
    wait_for_load()
    _wait_for(".dashboard-card[data-course-id]", timeout=20)

    raw = js("""
    (() => {
        const cards = document.querySelectorAll('.dashboard-card[data-course-id]');
        return JSON.stringify([...cards].map(c => ({
            id:   parseInt(c.getAttribute('data-course-id')),
            name: (c.querySelector('.multiline') || {}).textContent?.trim() || ''
        })));
    })()
    """)
    return json.loads(raw)


def open_course(course):
    """Navigate to a course page. Accepts ID or name substring."""
    cid = _resolve_course(course)
    goto_url(f"{BASE}/course/view.php?id={cid}")
    wait_for_load()
    return page_info()


def grades(course):
    """Get grades for a course. Returns list of dicts with clean parsed data."""
    cid = _resolve_course(course)
    goto_url(f"{BASE}/grade/report/user/index.php?id={cid}")
    wait_for_load()
    _wait_for("table.generaltable")

    raw = js(r"""
    (() => {
        const rows = [...document.querySelectorAll('table.generaltable tr')];
        return JSON.stringify(rows.slice(1).map(r => {
            const cells = [...r.querySelectorAll('th, td')];
            return cells.map(c => c.textContent.trim().replace(/\s+/g, ' '));
        }));
    })()
    """)

    parsed = []
    for row in json.loads(raw):
        if len(row) < 5:
            continue

        item_raw = row[0]
        # Strip activity type prefix ("AssignmentLab 03" -> "Lab 03")
        item = re.sub(r"^(Assignment|Forum|Quiz|Folder|Resource|URL|Page)", "", item_raw).strip()
        # Strip "Aggregation" prefix for course total
        item = re.sub(r"^Aggregation", "", item).strip()

        weight = row[1].strip()
        # Strip "Actions Grade analysis" from grade cell
        grade_raw = re.sub(r"\s*Actions\s+Grade analysis\s*", "", row[2]).strip()
        grade = grade_raw if grade_raw != "-" else None

        range_val = row[3].strip()
        pct_raw = row[4].strip()
        pct = pct_raw if pct_raw != "-" else None

        feedback = row[5].strip() if len(row) > 5 else ""
        contribution = row[6].strip() if len(row) > 6 else ""

        parsed.append({
            "item": item,
            "weight": weight,
            "grade": grade,
            "range": range_val,
            "percentage": pct,
            "feedback": feedback,
            "contribution": contribution,
        })

    return parsed


def all_grades():
    """Overview grades for all courses (every semester)."""
    goto_url(f"{BASE}/grade/report/overview/index.php")
    wait_for_load()
    wait(0.5)

    raw = js(r"""
    (() => {
        const rows = [...document.querySelectorAll('table tr')];
        return JSON.stringify(rows.slice(1).map(r => {
            const cells = [...r.querySelectorAll('th, td')];
            return cells.map(c => c.textContent.trim().replace(/\s+/g, ' '));
        }));
    })()
    """)

    return [
        {"course": row[0], "grade": row[1] if row[1] != "-" else None}
        for row in json.loads(raw)
        if len(row) >= 2
    ]


def activities(course):
    """List all activities (assignments, forums, resources) on a course page."""
    cid = _resolve_course(course)
    goto_url(f"{BASE}/course/view.php?id={cid}")
    wait_for_load()

    raw = js("""
    (() => {
        const acts = document.querySelectorAll('.activityname a, .aalink.stretched-link');
        const seen = new Set();
        return JSON.stringify([...acts].filter(a => {
            if (seen.has(a.href)) return false;
            seen.add(a.href);
            return a.href.includes('/mod/');
        }).map(a => ({
            name: a.textContent.trim().replace(/\\s+/g, ' '),
            href: a.href,
            type: (a.href.match(/\\/mod\\/(\\w+)\\//) || [])[1] || ''
        })));
    })()
    """)
    return json.loads(raw)


def announcements(course, n=5):
    """Get the latest n announcements from a course's Announcements forum.

    Returns list of dicts: [{title, author, date, body, href}, ...]
    """
    cid = _resolve_course(course)

    # Find the Announcements forum link on the course page
    goto_url(f"{BASE}/course/view.php?id={cid}")
    wait_for_load()

    forum_url = js("""
    (() => {
        const links = document.querySelectorAll('a[href*="/mod/forum/view.php"]');
        for (const a of links) {
            if (a.textContent.includes('Announcement')) return a.href;
        }
        return null;
    })()
    """)
    if not forum_url:
        raise RuntimeError(f"No Announcements forum found for course {cid}")

    # Get discussion listing
    goto_url(forum_url)
    wait_for_load()
    _wait_for("tr.discussion")

    listing = json.loads(js(r"""
    (() => {
        const rows = document.querySelectorAll('tr.discussion[data-discussionid]');
        return JSON.stringify([...rows].slice(0, """ + str(n) + r""").map(r => ({
            id: r.getAttribute('data-discussionid'),
            title: (r.querySelector('.topic a') || {}).title || (r.querySelector('.topic a') || {}).textContent?.trim() || '',
            href: (r.querySelector('.topic a') || {}).href || ''
        })));
    })()
    """))

    # Visit each discussion to get the post body
    results = []
    for disc in listing:
        goto_url(disc["href"])
        wait_for_load()
        wait(0.5)

        post = json.loads(js(r"""
        (() => {
            const article = document.querySelector('[data-region="post"], article, .forumpost');
            if (!article) return JSON.stringify({});
            const author = (article.querySelector('[data-region="author-name"] a, .author a') || {}).textContent?.trim() || '';
            const time = (article.querySelector('time') || {}).textContent?.trim() || '';
            const body = (article.querySelector('[data-region="post-content"], .post-content-container') || {}).textContent?.trim().replace(/\s+/g, ' ') || '';
            return JSON.stringify({ author, time, body });
        })()
        """))

        results.append({
            "title": disc["title"],
            "author": post.get("author", ""),
            "date": post.get("time", ""),
            "body": post.get("body", ""),
            "href": disc["href"],
        })

    return results


def fmt_announcements(ann_list, course_name=""):
    """Format announcements into a readable string (for Discord/terminal)."""
    lines = []
    if course_name:
        lines.append(f"**{course_name} — Latest Announcements**")
        lines.append("")

    for a in ann_list:
        lines.append(f"**{a['title']}**")
        by = f"{a['author']} — " if a["author"] else ""
        lines.append(f"_{by}{a['date']}_")
        body = a["body"]
        if len(body) > 300:
            body = body[:300] + "..."
        lines.append(body)
        lines.append("")

    return "\n".join(lines)


def download_submission(course, assignment_name, save_dir=None):
    """Download a submitted file from an assignment.

    Finds the assignment by substring match on the course page, navigates to it,
    and downloads all submitted files via in-browser fetch (preserves auth cookies).

    Returns list of saved file paths.
    """
    import base64

    if save_dir is None:
        save_dir = str(Path(__file__).resolve().parent.parent / "downloads")
    os.makedirs(save_dir, exist_ok=True)

    cid = _resolve_course(course)
    goto_url(f"{BASE}/course/view.php?id={cid}")
    wait_for_load()

    # Find the assignment link
    q = assignment_name.lower()
    assign_url = js("""
    (() => {
        const links = document.querySelectorAll('a[href*="/mod/assign/view.php"]');
        for (const a of links) {
            if (a.textContent.toLowerCase().includes('""" + q + """')) return a.href;
        }
        return null;
    })()
    """)
    if not assign_url:
        raise RuntimeError(f"No assignment matching '{assignment_name}' in course {cid}")

    goto_url(assign_url)
    wait_for_load()
    wait(1)

    # Find all submission file download links
    files = json.loads(js(r"""
    (() => {
        const links = document.querySelectorAll('a[href*="pluginfile.php"][href*="submission_files"]');
        return JSON.stringify([...links].map(a => ({
            name: a.textContent.trim().replace(/\s+/g, ' '),
            href: a.href
        })));
    })()
    """))

    if not files:
        raise RuntimeError("No submission files found on this assignment page")

    saved = []
    for f in files:
        # Download via in-browser fetch to keep session cookies
        b64 = js("""
        (async () => {
            const resp = await fetch('""" + f["href"] + """');
            const blob = await resp.blob();
            const buf = await blob.arrayBuffer();
            const bytes = new Uint8Array(buf);
            let binary = '';
            const chunkSize = 8192;
            for (let i = 0; i < bytes.length; i += chunkSize) {
                binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
            }
            return btoa(binary);
        })()
        """)

        if not b64:
            continue

        data = base64.b64decode(b64)
        filename = f["name"].split("?")[0]  # strip query params from name
        filepath = os.path.join(save_dir, filename)
        with open(filepath, "wb") as fh:
            fh.write(data)
        saved.append({"path": filepath, "size": len(data), "name": filename})

    return saved


def screenshot(path="/tmp/moodle.png", full=False):
    """Take a screenshot of the current page."""
    capture_screenshot(path, full=full)
    return path


def post_discord(message):
    """Post a message to the Discord webhook from .env."""
    _load_env()
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        raise RuntimeError("DISCORD_WEBHOOK_URL not set in .env")

    import httpx
    resp = httpx.post(url, json={"content": message})
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"Discord webhook failed: {resp.status_code} {resp.text}")
    return resp.status_code


def fmt_grades(grade_list, course_name=""):
    """Format a grades list into a readable string (for Discord/terminal)."""
    lines = []
    if course_name:
        lines.append(f"**{course_name} — Grades**")
        lines.append("")

    lines.append("```")
    for g in grade_list:
        if g["item"] == "Course total":
            lines.append(f"{'─' * 50}")
            lines.append(f"{'TOTAL':<35s} {g['grade'] or '-':>8s}  {g['percentage'] or '-'}")
        elif g["grade"] is not None:
            fb = f"  ⚠ {g['feedback']}" if g["feedback"] else ""
            lines.append(f"{g['item']:<35s} {g['grade']:>8s}  {g['percentage']}{fb}")
        else:
            lines.append(f"{g['item']:<35s} {'—':>8s}  not graded")
    lines.append("```")
    return "\n".join(lines)
