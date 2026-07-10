"""
LinkedIn Job Apply Bot (Easy Apply + External Apply).

Modes:
  1. EASY APPLY — auto-applies within LinkedIn
  2. EXTERNAL APPLY — opens company career page, collects URL for you
  3. PRODUCT COMPANY SEARCH — searches by company name + role

First run: browser opens → log in manually → session saved.
"""

import os
import sys
import time
import json
import random
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from config import JOB_SEARCH_CONFIG
from apply.base import (
    create_browser,
    close_browser,
    load_answers,
    human_type,
    human_click,
    scroll_into_view,
    random_scroll,
    check_for_captcha,
    check_for_block,
    check_login_required,
    fuzzy_match_question,
    get_resume_path,
)
from apply.safety import (
    can_apply,
    is_already_applied,
    record_application,
    should_stop,
    trigger_cooldown,
    random_delay_between_applies,
    random_delay_page_load,
    random_delay_before_click,
    random_delay_after_submit,
    random_delay_form_field,
    print_stats,
    human_delay,
    DELAY_PAGE_LOAD,
)


PLATFORM = "linkedin"
BASE_URL = "https://www.linkedin.com"

# File to log external apply links for manual follow-up
EXTERNAL_LOG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "external_apply_jobs.json"
)


# ─── Login Check ─────────────────────────────────────────────────────────────

def ensure_logged_in(page: Page) -> bool:
    """Navigate to LinkedIn and check if logged in."""
    page.goto(f"{BASE_URL}/feed/", wait_until="domcontentloaded", timeout=30000)
    random_delay_page_load()

    if "login" in page.url or "checkpoint" in page.url:
        print("\n  ╔══════════════════════════════════════════════════╗")
        print("  ║  LinkedIn login required.                       ║")
        print("  ║  Please log in manually in the browser window.  ║")
        print("  ║  Press ENTER here after you've logged in.       ║")
        print("  ╚══════════════════════════════════════════════════╝\n")
        input("  Press ENTER when logged in > ")
        page.wait_for_timeout(3000)

        if "login" in page.url:
            print("  ✗ Still not logged in. Aborting.")
            return False

    print("  ✓ Logged into LinkedIn")
    return True


# ─── Search URL Builders ─────────────────────────────────────────────────────

def build_search_url(role: str, location: str = "India", easy_apply_only: bool = False) -> str:
    """Build LinkedIn job search URL."""
    role_encoded = role.replace(" ", "%20")
    loc_encoded = location.replace(" ", "%20")
    url = (
        f"{BASE_URL}/jobs/search/"
        f"?keywords={role_encoded}"
        f"&location={loc_encoded}"
        f"&f_E=4%2C5"         # Senior + Director experience level
        f"&sortBy=DD"          # Sort by date (most recent)
    )
    if easy_apply_only:
        url += "&f_AL=true"    # Easy Apply filter
    return url


def build_company_search_url(company: str, role: str, location: str = "India") -> str:
    """Build LinkedIn search URL targeting a specific company."""
    keywords = f"{role} {company}".replace(" ", "%20")
    loc_encoded = location.replace(" ", "%20")
    return (
        f"{BASE_URL}/jobs/search/"
        f"?keywords={keywords}"
        f"&location={loc_encoded}"
        f"&sortBy=DD"
    )


# ─── Job Collection ──────────────────────────────────────────────────────────

def collect_job_listings(page: Page, max_jobs: int = 15) -> list[dict]:
    """
    Scroll through search results and collect job cards.
    Uses multiple selector strategies to handle LinkedIn UI changes.
    """
    jobs = []
    seen_ids = set()

    for scroll_round in range(5):
        page.wait_for_timeout(2000)

        # Strategy: Find all links that point to /jobs/view/
        job_links = page.locator("a[href*='/jobs/view/']").all()

        for link in job_links:
            try:
                if not link.is_visible():
                    continue

                href = link.get_attribute("href") or ""
                if "/jobs/view/" not in href:
                    continue

                # Extract job ID
                parts = href.split("/jobs/view/")
                if len(parts) < 2:
                    continue
                job_id = parts[1].split("/")[0].split("?")[0]
                if not job_id.isdigit():
                    continue
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Get title from the link text
                title = link.inner_text().strip()
                if not title or len(title) < 3:
                    continue
                # Skip if it's just navigation text
                if title.lower() in ("easy apply", "promoted", "viewed", "new"):
                    continue

                # Try to find company name near this link
                company = _extract_company_near_link(link)

                full_url = f"{BASE_URL}/jobs/view/{job_id}/"

                jobs.append({
                    "title": title.split("\n")[0].strip(),  # first line only
                    "company": company,
                    "url": full_url,
                    "job_id": job_id,
                })

                if len(jobs) >= max_jobs:
                    return jobs

            except Exception:
                continue

        # Scroll down to load more
        random_scroll(page)

    return jobs


# ─── Job Relevance Scoring ────────────────────────────────────────────────────

# Build match keywords dynamically from config target_roles
STRONG_MATCH_KEYWORDS = [role.lower() for role in JOB_SEARCH_CONFIG["target_roles"]]
# Add individual words from target roles
for _role in JOB_SEARCH_CONFIG["target_roles"]:
    for _word in _role.lower().split():
        if len(_word) > 3 and _word not in STRONG_MATCH_KEYWORDS:
            STRONG_MATCH_KEYWORDS.append(_word)

# Skills from TRENDING_SKILLS config
MEDIUM_MATCH_KEYWORDS = []
for _cat, _skills in __import__("config").TRENDING_SKILLS.items():
    MEDIUM_MATCH_KEYWORDS.extend(_skills[:5])

NEGATIVE_KEYWORDS = [
    "intern", "internship", "fresher", "0-2 years", "0-1 years",
    "junior", "entry level", "trainee", "graduate",
]


def score_job_relevance(title: str, company: str = "") -> int:
    """
    Score job relevance (0-100). Higher = better fit.
    Returns -1 for clearly irrelevant jobs (should skip).
    """
    title_lower = title.lower()

    # Negative check — skip clearly wrong jobs
    for neg in NEGATIVE_KEYWORDS:
        if neg in title_lower:
            return -1

    score = 0

    # Strong match keywords (core role)
    for kw in STRONG_MATCH_KEYWORDS:
        if kw in title_lower:
            score += 30
            break  # only count once

    # Medium match keywords (skills/domain)
    for kw in MEDIUM_MATCH_KEYWORDS:
        if kw in title_lower:
            score += 10

    # Seniority keywords (Lead/Senior/Principal/Staff/Director/Manager/Architect)
    seniority = ["lead", "senior", "principal", "staff", "director", "manager", "architect", "head"]
    for s in seniority:
        if s in title_lower:
            score += 20
            break

    # Cap at 100
    return min(score, 100)


def _extract_company_near_link(link) -> str:
    """Try to find company name near a job title link."""
    try:
        # Go up to the card container and look for company info
        card = link.locator("xpath=ancestor::li[1]")
        if card.count() == 0:
            card = link.locator("xpath=ancestor::div[contains(@class,'job')][1]")
        if card.count() > 0:
            # Look for company name — try multiple selectors
            for selector in [
                "span[class*='company']",
                "span[class*='subtitle']",
                "div[class*='subtitle'] span",
                "a[class*='company']",
                "span.tvm__text",
            ]:
                el = card.first.locator(selector)
                if el.count() > 0:
                    text = el.first.inner_text().strip()
                    if text and len(text) > 1:
                        return text
    except Exception:
        pass
    return "Unknown"


# ─── Apply Button Detection ─────────────────────────────────────────────────

def _find_apply_button(page: Page) -> tuple[str, any]:
    """
    Find the apply button on a job detail page.
    Returns (apply_type, button_element):
      - ("easy_apply", element) — LinkedIn Easy Apply
      - ("external", element)  — Apply on company site
      - ("applied", None)      — Already applied
      - ("none", None)         — No button found
    """
    page.wait_for_timeout(2000)

    # --- Strategy 1: Look specifically for Easy Apply button ---
    # LinkedIn Easy Apply buttons have specific CSS classes or contain the icon+text
    easy_selectors = [
        "button.jobs-apply-button--top-card",
        "button[aria-label*='Easy Apply']",
        "button.jobs-apply-button",
    ]
    for sel in easy_selectors:
        btns = page.locator(sel).all()
        for btn in btns:
            try:
                if not btn.is_visible():
                    continue
                text = btn.inner_text().strip().lower()
                aria = (btn.get_attribute("aria-label") or "").lower()
                if "easy apply" in text or "easy apply" in aria:
                    return ("easy_apply", btn)
            except Exception:
                continue

    # --- Strategy 2: Scan all visible buttons for Easy Apply text ---
    all_buttons = page.locator("button").all()
    easy_apply_btn = None
    external_btn = None

    for btn in all_buttons:
        try:
            if not btn.is_visible():
                continue

            text = btn.inner_text().strip().lower()
            aria = (btn.get_attribute("aria-label") or "").lower()

            # Already applied check
            if "applied" in text and "easy" not in text:
                return ("applied", None)

            # Easy Apply — must contain "easy" + "apply"
            if "easy apply" in text or "easy apply" in aria:
                easy_apply_btn = btn
                continue

            # Generic "Apply" — likely external
            if text in ("apply", "apply now") or (
                "apply" in aria and "easy" not in aria
            ):
                if not external_btn:
                    external_btn = btn
                continue

        except Exception:
            continue

    if easy_apply_btn:
        return ("easy_apply", easy_apply_btn)
    elif external_btn:
        return ("external", external_btn)
    else:
        return ("none", None)


# ─── Apply Handlers ──────────────────────────────────────────────────────────

def apply_to_job(page: Page, job: dict, answers: dict, context=None) -> str:
    """
    Navigate to a job and apply.
    Returns: "applied", "external", "skipped", "failed", "captcha"
    """
    url = job["url"]
    company = job["company"]
    title = job["title"]

    print(f"\n  ── {title} at {company} ──")

    # Navigate to job page
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except PlaywrightTimeout:
        print(f"    ⊘ Page load timeout — skipping")
        return "skipped"
    random_delay_page_load()

    # Safety checks
    if check_for_captcha(page):
        print("  ✗ CAPTCHA detected! Stopping.")
        trigger_cooldown(PLATFORM)
        return "captcha"

    if check_for_block(page):
        print("  ✗ Account restriction detected! Stopping.")
        trigger_cooldown(PLATFORM)
        return "captcha"

    if check_login_required(page, PLATFORM):
        print("  ✗ Logged out. Stopping.")
        return "captcha"

    # Find the apply button
    apply_type, btn = _find_apply_button(page)

    if apply_type == "applied":
        print(f"    ⊘ Already applied — skipping")
        return "skipped"

    if apply_type == "none":
        print(f"    ⊘ No Apply button found — skipping")
        return "skipped"

    if apply_type == "external":
        return _handle_external_apply(page, btn, job, context)

    if apply_type == "easy_apply":
        return _handle_easy_apply(page, btn, job, answers)

    return "failed"


def _handle_easy_apply(page: Page, btn, job: dict, answers: dict) -> str:
    """Handle Easy Apply flow."""
    print(f"    → Easy Apply")
    random_delay_before_click()
    btn.click()
    page.wait_for_timeout(3000)

    success = _handle_easy_apply_modal(page, answers, job["title"])

    if success:
        print(f"  ✓ Applied: {job['title']} at {job['company']}")
        return "applied"
    else:
        print(f"  ✗ Could not complete Easy Apply")
        return "failed"


def _handle_external_apply(page: Page, btn, job: dict, context=None) -> str:
    """
    Handle external/company site apply.
    Opens the company career page in a new tab.
    Logs the URL for manual follow-up.
    """
    print(f"    → External Apply (company site)")

    external_url = None

    # Try to capture the URL from the new tab that opens
    try:
        with page.context.expect_page(timeout=10000) as new_page_info:
            random_delay_before_click()
            btn.click()
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded", timeout=15000)
        external_url = new_page.url
        print(f"    🔗 Opened: {external_url[:80]}...")
        # Close the new tab to keep the browser clean
        try:
            new_page.close()
        except Exception:
            pass
    except PlaywrightTimeout:
        # No new tab — might have redirected current page or nothing happened
        page.wait_for_timeout(2000)
        if page.url != job["url"] and "linkedin.com/jobs/view" not in page.url:
            external_url = page.url
            print(f"    🔗 Redirected to: {external_url[:80]}...")
            # Navigate back to LinkedIn
            try:
                page.go_back(wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass
    except Exception as e:
        print(f"    ⚠ Could not capture external URL: {e}")

    if external_url:
        portal = _detect_portal_type(external_url)
        _log_external_job(job, external_url, portal)
        print(f"    📋 Portal: {portal} — saved for manual apply")
        # Record as completed so it's counted and not retried
        record_application(PLATFORM, job["url"], job["company"], job["title"], True)
        return "external"
    else:
        print(f"    ⊘ Could not capture external URL — skipping")
        return "skipped"


def _log_external_job(job: dict, external_url: str, portal: str = "Unknown"):
    """Save external apply job to a JSON file for manual follow-up."""
    entries = []
    if os.path.exists(EXTERNAL_LOG):
        with open(EXTERNAL_LOG) as f:
            entries = json.load(f)

    if any(e.get("external_url") == external_url for e in entries):
        return

    entries.append({
        "title": job["title"],
        "company": job["company"],
        "linkedin_url": job["url"],
        "external_url": external_url,
        "portal_type": portal,
        "status": "pending",
        "found_at": datetime.now().isoformat(),
    })

    with open(EXTERNAL_LOG, "w") as f:
        json.dump(entries, f, indent=2)


def _detect_portal_type(url: str) -> str:
    """Detect what career portal the company uses."""
    url_lower = url.lower()
    portals = {
        "workday": "Workday", "myworkdayjobs": "Workday",
        "greenhouse": "Greenhouse",
        "lever.co": "Lever",
        "icims": "iCIMS",
        "taleo": "Taleo",
        "smartrecruiters": "SmartRecruiters",
        "ashbyhq": "Ashby",
        "bamboohr": "BambooHR",
        "successfactors": "SAP SuccessFactors",
        "jobvite": "Jobvite",
        "phenom": "Phenom",
    }
    for key, name in portals.items():
        if key in url_lower:
            return name
    if "careers" in url_lower or "jobs" in url_lower:
        return "Company Career Page"
    return "Unknown"


# ─── Easy Apply Modal Handler ────────────────────────────────────────────────

def _handle_easy_apply_modal(page: Page, answers: dict, job_title: str) -> bool:
    """Walk through the Easy Apply modal steps."""
    max_steps = 8

    for step in range(max_steps):
        page.wait_for_timeout(2000)

        # Check if modal is still open
        modal = page.locator("div[role='dialog'], div[class*='easy-apply'], div[class*='artdeco-modal']")
        if modal.count() == 0:
            return _check_application_submitted(page)

        # Fill form fields
        _fill_form_fields(page, answers, job_title)

        # Handle resume upload
        _handle_resume_upload(page, answers, job_title)

        # Find action buttons inside the modal
        buttons = modal.first.locator("button").all()

        submit_btn = None
        review_btn = None
        next_btn = None
        discard_btn = None

        for btn in buttons:
            try:
                if not btn.is_visible():
                    continue
                text = btn.inner_text().strip().lower()
                aria = (btn.get_attribute("aria-label") or "").lower()

                if "submit" in text or "submit" in aria:
                    submit_btn = btn
                elif "review" in text or "review" in aria:
                    review_btn = btn
                elif "next" in text or "continue" in aria:
                    next_btn = btn
                elif "discard" in text or "dismiss" in text:
                    discard_btn = btn
            except Exception:
                continue

        # Priority: Submit > Review > Next
        if submit_btn:
            random_delay_before_click()
            submit_btn.click()
            random_delay_after_submit()
            return _check_application_submitted(page)

        elif review_btn:
            random_delay_before_click()
            review_btn.click()
            page.wait_for_timeout(2000)
            continue

        elif next_btn:
            random_delay_before_click()
            next_btn.click()
            page.wait_for_timeout(2000)
            continue

        else:
            page.wait_for_timeout(3000)
            if _check_application_submitted(page):
                return True
            if discard_btn:
                print("    ⊘ Modal stuck — closing")
                discard_btn.click()
                return False
            break

    return False


def _fill_form_fields(page: Page, answers: dict, job_title: str):
    """Fill in all visible form fields in the current modal step."""
    modal = page.locator("div[role='dialog']")
    if modal.count() == 0:
        return

    # --- Text & number inputs ---
    inputs = modal.first.locator("input[type='text'], input[type='number'], input:not([type])").all()

    for inp in inputs:
        try:
            if not inp.is_visible() or not inp.is_enabled():
                continue
            inp_type = (inp.get_attribute("type") or "text").lower()
            if inp_type in ("hidden", "checkbox", "radio", "file", "submit"):
                continue

            current_val = inp.input_value().strip()
            if current_val:
                continue

            label = _get_field_label(page, inp)
            answer = fuzzy_match_question(label, answers) if label else None

            if answer:
                inp.click()
                inp.fill(answer)
                random_delay_form_field()
                print(f"    ✏ Filled: {label[:40]} → {answer[:20]}")
        except Exception:
            continue

    # --- Textareas ---
    textareas = modal.first.locator("textarea").all()
    for ta in textareas:
        try:
            if not ta.is_visible() or not ta.is_enabled():
                continue
            if ta.input_value().strip():
                continue
            label = _get_field_label(page, ta)
            answer = fuzzy_match_question(label, answers) if label else None
            if answer:
                ta.click()
                ta.fill(answer)
                random_delay_form_field()
        except Exception:
            continue

    # --- Select dropdowns ---
    selects = modal.first.locator("select").all()

    for select in selects:
        try:
            if not select.is_visible():
                continue
            label = _get_field_label(page, select)
            answer = fuzzy_match_question(label, answers) if label else None
            if answer:
                options = select.locator("option").all()
                for opt in options:
                    opt_text = opt.inner_text().strip().lower()
                    if answer.lower() in opt_text or opt_text in answer.lower():
                        select.select_option(label=opt.inner_text().strip())
                        random_delay_form_field()
                        break
        except Exception:
            continue

    # --- Radio buttons ---
    fieldsets = modal.first.locator("fieldset").all()

    for fieldset in fieldsets:
        try:
            legend = fieldset.locator("legend, span, label").first
            if legend.count() == 0:
                continue
            question = legend.inner_text().strip()
            if not question:
                continue
            answer = fuzzy_match_question(question, answers)
            if answer:
                answer_lower = answer.lower()
                labels = fieldset.locator("label").all()
                for lbl in labels:
                    label_text = lbl.inner_text().strip().lower()
                    if answer_lower in label_text or label_text in answer_lower:
                        lbl.click()
                        random_delay_form_field()
                        break
        except Exception:
            continue


def _get_field_label(page: Page, element) -> str:
    """Try to find the label text for a form field."""
    try:
        aria = element.get_attribute("aria-label")
        if aria:
            return aria

        field_id = element.get_attribute("id")
        if field_id:
            label_el = page.locator(f"label[for='{field_id}']")
            if label_el.count() > 0:
                return label_el.first.inner_text().strip()

        parent_label = element.locator("xpath=ancestor::label")
        if parent_label.count() > 0:
            return parent_label.first.inner_text().strip()

        # Look in closest parent div for a label
        parent_div = element.locator("xpath=ancestor::div[position()<=3]")
        for i in range(min(parent_div.count(), 3)):
            try:
                lbl = parent_div.nth(i).locator("label")
                if lbl.count() > 0:
                    txt = lbl.first.inner_text().strip()
                    if txt:
                        return txt
            except Exception:
                continue

        placeholder = element.get_attribute("placeholder")
        if placeholder:
            return placeholder
    except Exception:
        pass
    return ""


def _handle_resume_upload(page: Page, answers: dict, job_title: str):
    """Upload resume if the form asks for it."""
    try:
        modal = page.locator("div[role='dialog']")
        if modal.count() == 0:
            return

        file_input = modal.first.locator("input[type='file']")
        if file_input.count() == 0:
            return

        # Check if resume is already uploaded
        uploaded = modal.first.locator("[class*='file-name'], [class*='document-upload'] span")
        if uploaded.count() > 0 and uploaded.first.inner_text().strip():
            return

        resume_path = get_resume_path(answers, job_title)
        abs_path = os.path.abspath(resume_path)

        if os.path.exists(abs_path):
            file_input.first.set_input_files(abs_path)
            print(f"    📄 Uploaded: {os.path.basename(abs_path)}")
            page.wait_for_timeout(2000)
        else:
            print(f"    ⚠ Resume not found: {abs_path}")
    except Exception as e:
        print(f"    ⚠ Resume upload error: {e}")


def _check_application_submitted(page: Page) -> bool:
    """Check if the application was submitted."""
    page.wait_for_timeout(2000)

    success_texts = page.locator(
        "text='Application submitted', "
        "text='Your application was sent', "
        "text='application sent', "
        "h2:has-text('applied')"
    )
    if success_texts.count() > 0:
        return True

    content = page.content().lower()
    return any(s in content for s in [
        "application submitted",
        "your application was sent",
        "you applied",
    ])


# ─── Main Run Function ──────────────────────────────────────────────────────

def run_linkedin_apply(
    roles: list[str] | None = None,
    location: str = "India",
    max_applies: int = 10,
    companies: list[str] | None = None,
    easy_apply_only: bool = False,
):
    """
    Main entry point for LinkedIn Apply.

    Args:
        roles: Job titles to search.
        location: Location filter.
        max_applies: Max applications this session.
        companies: If set, search these specific companies.
        easy_apply_only: If True, skip external apply jobs.
    """
    from config import JOB_SEARCH_CONFIG, PRODUCT_COMPANIES

    if roles is None:
        # Use the most relevant roles from config
        roles = JOB_SEARCH_CONFIG["target_roles"][:5]

    allowed, reason = can_apply(PLATFORM)
    if not allowed:
        print(f"\n  ✗ Cannot apply: {reason}")
        print_stats()
        return

    answers = load_answers()
    applied_count = 0
    external_count = 0

    mode = "Product Companies" if companies else "All Jobs"
    apply_mode = "Easy Apply Only" if easy_apply_only else "Easy Apply + External"

    print(f"\n  {'='*55}")
    print(f"  LINKEDIN APPLY BOT")
    print(f"  Mode: {mode} | {apply_mode}")
    print(f"  Roles: {', '.join(roles[:3])}{'...' if len(roles) > 3 else ''}")
    print(f"  Location: {location}")
    print(f"  Max this session: {max_applies}")
    print(f"  {'='*55}")

    pw, context, page = create_browser(PLATFORM)

    try:
        if not ensure_logged_in(page):
            return

        # Build search list
        if companies:
            search_list = []
            for company in companies[:15]:
                for role in roles[:2]:
                    search_list.append({
                        "url": build_company_search_url(company, role, location),
                        "label": f"{role} at {company}",
                    })
            random.shuffle(search_list)
        else:
            # Default: Easy Apply filter so we can auto-apply
            search_list = [
                {"url": build_search_url(role, location, easy_apply_only=True), "label": role}
                for role in roles
            ]

        for search in search_list:
            if applied_count >= max_applies:
                break

            stop, reason = should_stop(PLATFORM)
            if stop:
                print(f"\n  ✗ Stopping: {reason}")
                break

            print(f"\n  ── Searching: {search['label']} ──")

            try:
                page.goto(search["url"], wait_until="domcontentloaded", timeout=60000)
            except PlaywrightTimeout:
                print(f"    ⊘ Search page timeout — trying next search")
                continue

            random_delay_page_load()

            if check_for_captcha(page):
                print("  ✗ CAPTCHA on search page! Stopping.")
                trigger_cooldown(PLATFORM)
                break

            jobs = collect_job_listings(page, max_jobs=15)

            # Filter and sort by relevance
            scored_jobs = []
            for job in jobs:
                score = score_job_relevance(job["title"], job.get("company", ""))
                if score >= 0:  # -1 means irrelevant
                    job["_score"] = score
                    scored_jobs.append(job)
                else:
                    print(f"    ✗ Skipped (irrelevant): {job['title']}")

            # Sort by score descending — best fit first
            scored_jobs.sort(key=lambda j: j["_score"], reverse=True)
            jobs = scored_jobs

            print(f"    Found {len(jobs)} relevant jobs (filtered)")

            if not jobs:
                continue

            for job in jobs:
                if applied_count >= max_applies:
                    break

                stop, reason = should_stop(PLATFORM)
                if stop:
                    print(f"\n  ✗ Stopping: {reason}")
                    break

                allowed, reason = can_apply(PLATFORM)
                if not allowed:
                    print(f"\n  ✗ {reason}")
                    break

                if is_already_applied(job["url"]):
                    continue

                try:
                    result = apply_to_job(page, job, answers, context)

                    if result == "applied":
                        record_application(PLATFORM, job["url"], job["company"], job["title"], True)
                        applied_count += 1
                    elif result == "external":
                        # Already recorded in _handle_external_apply
                        external_count += 1
                        applied_count += 1
                    elif result == "captcha":
                        break
                    elif result == "skipped":
                        pass  # Not an error, just skip
                    else:
                        record_application(PLATFORM, job["url"], job["company"], job["title"], False)

                    random_delay_between_applies()

                except PlaywrightTimeout:
                    print(f"    ⊘ Timeout — skipping")
                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    record_application(PLATFORM, job["url"], job["company"], job["title"], False)

    except KeyboardInterrupt:
        print("\n\n  ⊘ Interrupted by user.")

    finally:
        print(f"\n  ── Session Complete ──")
        print(f"  Easy Applied: {applied_count}")
        print(f"  External (saved for manual): {external_count}")
        if external_count > 0:
            print(f"  → Check data/external_apply_jobs.json for company portal links")
        print_stats()
        close_browser(pw, context)


if __name__ == "__main__":
    run_linkedin_apply()
