"""
Safety & Rate Limiting for Auto-Apply Bots.
Ensures we stay under detection thresholds on every platform.
"""

import os
import json
import random
import time
from datetime import datetime, date


# ─── Daily Limits (HARD CAPS — never exceed) ─────────────────────────────────

DAILY_LIMITS = {
    "linkedin": 10,
    "naukri": 12,
    "total": 22,
}

# ─── Delay Ranges (seconds) ──────────────────────────────────────────────────

DELAY_BETWEEN_APPLIES = (1, 3)        # minimal wait between applications
DELAY_PAGE_LOAD = (1, 2)              # wait after page navigation
DELAY_BEFORE_CLICK = (0.5, 1)         # pause before clicking a button
DELAY_FORM_FIELD = (0.3, 0.8)         # pause between filling form fields
DELAY_AFTER_SUBMIT = (1, 3)           # wait after submitting application

# ─── Session Limits ──────────────────────────────────────────────────────────

MAX_SESSION_DURATION_MINUTES = 120     # stop after 2 hours
MAX_CONSECUTIVE_ERRORS = 3             # stop if 3 errors in a row
COOLDOWN_ON_WARNING_HOURS = 48         # pause platform for 48h if warning detected

# ─── State File ──────────────────────────────────────────────────────────────

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
STATE_FILE = os.path.join(STATE_DIR, "apply_state.json")


def _load_state() -> dict:
    """Load daily application state."""
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(STATE_FILE):
        return _new_day_state()

    with open(STATE_FILE) as f:
        state = json.load(f)

    # Reset if it's a new day
    if state.get("date") != str(date.today()):
        return _new_day_state()

    return state


def _new_day_state() -> dict:
    return {
        "date": str(date.today()),
        "counts": {"linkedin": 0, "naukri": 0, "total": 0},
        "applied_urls": [],
        "errors": [],
        "session_start": None,
        "cooldowns": {},
    }


def _save_state(state: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ─── Public API ──────────────────────────────────────────────────────────────

def can_apply(platform: str) -> tuple[bool, str]:
    """
    Check if we can apply on this platform right now.
    Returns (allowed, reason).
    """
    state = _load_state()
    platform = platform.lower()

    # Check cooldown
    cooldown_until = state.get("cooldowns", {}).get(platform)
    if cooldown_until:
        if datetime.now().isoformat() < cooldown_until:
            return False, f"Platform '{platform}' is on cooldown until {cooldown_until}"

    # Check platform daily limit
    platform_count = state["counts"].get(platform, 0)
    platform_limit = DAILY_LIMITS.get(platform, 10)
    if platform_count >= platform_limit:
        return False, f"Daily limit reached for {platform}: {platform_count}/{platform_limit}"

    # Check total daily limit
    total_count = state["counts"].get("total", 0)
    if total_count >= DAILY_LIMITS["total"]:
        return False, f"Total daily limit reached: {total_count}/{DAILY_LIMITS['total']}"

    # Check session duration
    if state.get("session_start"):
        session_start = datetime.fromisoformat(state["session_start"])
        elapsed = (datetime.now() - session_start).total_seconds() / 60
        if elapsed > MAX_SESSION_DURATION_MINUTES:
            return False, f"Session duration exceeded ({elapsed:.0f} min > {MAX_SESSION_DURATION_MINUTES} min). Take a break."

    return True, "OK"


def is_already_applied(url: str) -> bool:
    """Check if we've already applied to this URL (today or historically)."""
    state = _load_state()
    return url in state.get("applied_urls", [])


def record_application(platform: str, url: str, company: str, role: str, success: bool):
    """Record an application attempt."""
    state = _load_state()
    platform = platform.lower()

    if not state.get("session_start"):
        state["session_start"] = datetime.now().isoformat()

    if success:
        state["counts"][platform] = state["counts"].get(platform, 0) + 1
        state["counts"]["total"] = state["counts"].get("total", 0) + 1
        state["applied_urls"].append(url)
        # Clear consecutive errors on success
        state["errors"] = []
    else:
        state["errors"].append({
            "platform": platform,
            "url": url,
            "company": company,
            "time": datetime.now().isoformat(),
        })

    _save_state(state)


def get_consecutive_errors(platform: str) -> int:
    """Count recent consecutive errors for a platform."""
    state = _load_state()
    errors = [e for e in state.get("errors", []) if e["platform"] == platform.lower()]
    return len(errors)


def should_stop(platform: str) -> tuple[bool, str]:
    """Check if we should stop the current session."""
    if get_consecutive_errors(platform) >= MAX_CONSECUTIVE_ERRORS:
        return True, f"Too many consecutive errors on {platform} ({MAX_CONSECUTIVE_ERRORS}). Stopping."

    allowed, reason = can_apply(platform)
    if not allowed:
        return True, reason

    return False, "OK"


def trigger_cooldown(platform: str):
    """Put a platform on cooldown (e.g., after detecting a warning)."""
    state = _load_state()
    cooldown_end = datetime.now().timestamp() + (COOLDOWN_ON_WARNING_HOURS * 3600)
    state.setdefault("cooldowns", {})[platform.lower()] = datetime.fromtimestamp(cooldown_end).isoformat()
    _save_state(state)
    print(f"  ⚠ Platform '{platform}' on cooldown for {COOLDOWN_ON_WARNING_HOURS} hours.")


def get_today_stats() -> dict:
    """Get today's application stats."""
    state = _load_state()
    return {
        "date": state["date"],
        "linkedin": state["counts"].get("linkedin", 0),
        "naukri": state["counts"].get("naukri", 0),
        "total": state["counts"].get("total", 0),
        "errors": len(state.get("errors", [])),
        "limits": DAILY_LIMITS,
    }


# ─── Delay Helpers ───────────────────────────────────────────────────────────

def human_delay(delay_range: tuple[float, float] = DELAY_BETWEEN_APPLIES, label: str = ""):
    """Sleep for a random duration within the given range."""
    delay = random.uniform(*delay_range)
    if label:
        print(f"    ⏳ {label} ({delay:.1f}s)")
    time.sleep(delay)


def random_delay_between_applies():
    """Brief pause between job applications."""
    human_delay(DELAY_BETWEEN_APPLIES)


def random_delay_page_load():
    human_delay(DELAY_PAGE_LOAD)


def random_delay_before_click():
    human_delay(DELAY_BEFORE_CLICK)


def random_delay_form_field():
    human_delay(DELAY_FORM_FIELD)


def random_delay_after_submit():
    human_delay(DELAY_AFTER_SUBMIT, "Waiting after submit")


def print_stats():
    """Print today's stats to terminal."""
    stats = get_today_stats()
    print(f"\n  ── Today's Stats ({stats['date']}) ──")
    print(f"  LinkedIn:  {stats['linkedin']}/{stats['limits']['linkedin']}")
    print(f"  Naukri:    {stats['naukri']}/{stats['limits']['naukri']}")
    print(f"  Total:     {stats['total']}/{stats['limits']['total']}")
    if stats["errors"]:
        print(f"  Errors:    {stats['errors']}")
    print()
