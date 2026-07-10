"""
Base browser setup and shared utilities for all auto-apply bots.
Uses Playwright with a REAL browser profile (not headless) to avoid detection.
"""

import os
import json
import random

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from apply.safety import (
    human_delay,
    random_delay_page_load,
    random_delay_before_click,
    random_delay_form_field,
    DELAY_FORM_FIELD,
)


# ─── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ANSWERS_FILE = os.path.join(DATA_DIR, "answers.json")
BROWSER_STATE_DIR = os.path.join(DATA_DIR, "browser_state")
LINKEDIN_STATE = os.path.join(BROWSER_STATE_DIR, "linkedin")
NAUKRI_STATE = os.path.join(BROWSER_STATE_DIR, "naukri")


# ─── Answers Loader ──────────────────────────────────────────────────────────

def load_answers() -> dict:
    """Load the pre-filled answers bank."""
    with open(ANSWERS_FILE) as f:
        return json.load(f)


# ─── Browser Setup ────────────────────────────────────────────────────────────

def create_browser(platform: str) -> tuple:
    """
    Launch a REAL Chromium browser with persistent state.
    Returns (playwright, browser_context, page).

    First run: you log in manually. State is saved for future runs.
    """
    state_dir = LINKEDIN_STATE if platform == "linkedin" else NAUKRI_STATE
    os.makedirs(state_dir, exist_ok=True)

    pw = sync_playwright().start()

    context = pw.chromium.launch_persistent_context(
        user_data_dir=state_dir,
        headless=False,                    # MUST be visible — headless gets detected
        channel="chromium",
        viewport={"width": 1366, "height": 768},
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        args=[
            "--disable-blink-features=AutomationControlled",  # hide automation flag
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    # Remove webdriver flag that reveals automation
    page = context.pages[0] if context.pages else context.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    return pw, context, page


def close_browser(pw, context):
    """Safely close browser and Playwright."""
    try:
        context.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass


# ─── Human-Like Interactions ─────────────────────────────────────────────────

def human_type(page: Page, selector: str, text: str, clear_first: bool = True):
    """
    Type text into a field with human-like delays between keystrokes.
    """
    element = page.locator(selector)
    if clear_first:
        element.click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        random_delay_form_field()

    for char in text:
        element.type(char, delay=random.randint(30, 120))  # ms between keys

    random_delay_form_field()


def human_click(page: Page, selector: str):
    """Click with a small random delay before clicking."""
    random_delay_before_click()
    page.locator(selector).click()
    random_delay_page_load()


def scroll_into_view(page: Page, selector: str):
    """Scroll element into view before interacting."""
    page.locator(selector).scroll_into_view_if_needed()
    human_delay((0.5, 1.5))


def random_scroll(page: Page):
    """Simulate random human scrolling."""
    scroll_amount = random.randint(200, 600)
    page.mouse.wheel(0, scroll_amount)
    human_delay((1, 3))


# ─── Detection Checks ────────────────────────────────────────────────────────

def check_for_captcha(page: Page) -> bool:
    """
    Check if a CAPTCHA challenge is VISIBLY blocking the page.
    Only triggers on actual visible captcha elements, not hidden HTML references.
    """
    # Check for visible CAPTCHA iframes or containers
    visible_captcha = page.locator(
        "iframe[src*='captcha'], "
        "iframe[src*='recaptcha'], "
        "iframe[src*='hcaptcha'], "
        "div.g-recaptcha, "
        "div.h-captcha, "
        "#captcha-challenge, "
        "div[class*='captcha-container']"
    )
    if visible_captcha.count() > 0:
        for i in range(visible_captcha.count()):
            try:
                if visible_captcha.nth(i).is_visible():
                    return True
            except Exception:
                continue

    # Check if the entire page is a challenge page (URL-based)
    url = page.url.lower()
    if any(x in url for x in ["checkpoint/challenge", "captcha", "/challenge/"]):
        return True

    # Check for visible "verify you're human" text in the main content
    verify_text = page.locator(
        "text='Verify you\\'re a human', "
        "text='Security Verification', "
        "text='Let\\'s do a quick security check'"
    )
    if verify_text.count() > 0:
        for i in range(verify_text.count()):
            try:
                if verify_text.nth(i).is_visible():
                    return True
            except Exception:
                continue

    return False


def check_for_block(page: Page) -> bool:
    """Check if the account is restricted or blocked (visible text only)."""
    block_texts = page.locator(
        "text='your account has been restricted', "
        "text='temporarily restricted', "
        "text='account suspended', "
        "text='Access Denied'"
    )
    if block_texts.count() > 0:
        for i in range(block_texts.count()):
            try:
                if block_texts.nth(i).is_visible():
                    return True
            except Exception:
                continue

    # URL-based checks
    url = page.url.lower()
    if any(x in url for x in ["/restricted", "/suspended", "access-denied"]):
        return True

    return False


def check_login_required(page: Page, platform: str) -> bool:
    """Check if we've been logged out."""
    if platform == "linkedin":
        return "linkedin.com/login" in page.url or "Sign in" in (page.title() or "")
    elif platform == "naukri":
        return "login" in page.url.lower()
    return False


# ─── Form Helpers ─────────────────────────────────────────────────────────────

def fuzzy_match_question(question_text: str, answers: dict) -> str | None:
    """
    Try to match a form question to our pre-filled answers.
    Uses keyword matching — not exact match.
    """
    q = question_text.lower().strip()
    common = answers.get("common_questions", {})
    experience_map = common.get("years_experience_with", {})
    yesno_map = common.get("do_you_have_experience_with", {})
    personal = answers.get("personal", {})
    professional = answers.get("professional", {})

    # Yes/No authorization questions
    if "legally authorized" in q or "authorized to work" in q:
        return common.get("are_you_legally_authorized", "Yes")
    if "sponsorship" in q:
        return common.get("will_you_now_or_in_future_require_sponsorship", "No")
    if "relocate" in q or "willing to relocate" in q:
        return professional.get("willing_to_relocate", "Yes")

    # Experience years questions
    if "years" in q and "experience" in q:
        for skill, years in experience_map.items():
            if skill.replace("_", " ") in q:
                return years
        # Generic "total experience"
        if "total" in q or not any(s in q for s in experience_map):
            return professional.get("total_experience_years", "10")

    # Yes/No skill questions
    if any(phrase in q for phrase in ["do you have", "experience with", "proficient in", "familiar with"]):
        for skill, answer in yesno_map.items():
            if skill.replace("_", " ") in q:
                return answer

    # Notice period
    if "notice" in q:
        return professional.get("notice_period_text", "30 days")

    # CTC / salary
    if "current" in q and ("ctc" in q or "salary" in q or "compensation" in q):
        return professional.get("current_ctc_lpa", "")
    if "expected" in q and ("ctc" in q or "salary" in q or "compensation" in q):
        return professional.get("expected_ctc_lpa", "")

    # Location
    if "city" in q or "location" in q:
        return personal.get("city", "Bengaluru")

    # Phone
    if "phone" in q or "mobile" in q or "contact number" in q:
        return personal.get("phone", "")

    # Email
    if "email" in q:
        return personal.get("email", "")

    # LinkedIn
    if "linkedin" in q:
        return personal.get("linkedin_url", "")

    # GitHub
    if "github" in q or "portfolio" in q:
        return personal.get("github_url", "")

    return None


def get_resume_path(answers: dict, job_title: str = "") -> str:
    """Pick the right resume variant based on job title."""
    variants = answers.get("resume_variants", {})
    title_lower = job_title.lower()

    if "architect" in title_lower:
        return variants.get("test_architect", variants["default"])
    elif "manager" in title_lower or "director" in title_lower:
        return variants.get("qa_manager", variants["default"])
    elif "lead" in title_lower or "principal" in title_lower or "staff" in title_lower:
        return variants.get("lead_test_engineer", variants["default"])

    return variants.get("default", "output/Resume.pdf")
