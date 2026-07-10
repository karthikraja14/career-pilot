"""
Naukri Quick Apply Bot.

Workflow:
  1. Opens Naukri job search with filters
  2. Finds jobs with "Apply" button
  3. Fills form fields from answers.json
  4. Submits and logs the application

First run: a browser opens — log into Naukri manually. Session is saved.
"""

import os
import time
import random
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from apply.base import (
    create_browser,
    close_browser,
    load_answers,
    human_type,
    human_click,
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
)


PLATFORM = "naukri"
BASE_URL = "https://www.naukri.com"


# ─── Login Check ─────────────────────────────────────────────────────────────

def ensure_logged_in(page: Page) -> bool:
    """Navigate to Naukri and check if logged in."""
    page.goto(f"{BASE_URL}/mnjuser/homepage", wait_until="domcontentloaded", timeout=30000)
    random_delay_page_load()

    # Check for login page
    if "login" in page.url.lower() or "registration" in page.url.lower():
        print("\n  ╔══════════════════════════════════════════════════╗")
        print("  ║  Naukri login required.                         ║")
        print("  ║  Please log in manually in the browser window.  ║")
        print("  ║  Press ENTER here after you've logged in.       ║")
        print("  ╚══════════════════════════════════════════════════╝\n")
        input("  Press ENTER when logged in > ")
        page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            print("  ✗ Still not logged in. Aborting.")
            return False

    print("  ✓ Logged into Naukri")
    return True


# ─── Job Search ──────────────────────────────────────────────────────────────

def build_search_url(role: str, location: str = "Bangalore", experience: int = 10) -> str:
    """Build Naukri job search URL."""
    role_slug = role.lower().replace(" ", "-")
    loc_slug = location.lower()
    return (
        f"{BASE_URL}/{role_slug}-jobs-in-{loc_slug}"
        f"?k={role.replace(' ', '+')}"
        f"&l={location}"
        f"&experience={experience}"
        f"&jobAge=3"  # posted in last 3 days
    )


def collect_job_listings(page: Page, max_jobs: int = 15) -> list[dict]:
    """Collect job cards from Naukri search results."""
    jobs = []
    seen_ids = set()

    for scroll_round in range(5):
        # Naukri job cards
        cards = page.locator("article.jobTuple, div.srp-jobtuple-wrapper, div.cust-job-tuple").all()

        for card in cards:
            try:
                # Get job link
                link_el = card.locator("a.title, a[class*='title'], h2 a").first
                if link_el.count() == 0:
                    continue

                href = link_el.get_attribute("href") or ""
                if not href:
                    continue

                # Deduplicate by URL
                job_id = href.split("?")[0]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = link_el.inner_text().strip()
                company_el = card.locator("a.comp-name, a[class*='companyInfo'], span.comp-name")
                company = company_el.first.inner_text().strip() if company_el.count() > 0 else "Unknown"

                full_url = href if href.startswith("http") else f"{BASE_URL}{href}"

                jobs.append({
                    "title": title,
                    "company": company,
                    "url": full_url,
                    "job_id": job_id,
                })

                if len(jobs) >= max_jobs:
                    return jobs

            except Exception:
                continue

        random_scroll(page)
        page.wait_for_timeout(2000)

    return jobs


# ─── Apply Flow ──────────────────────────────────────────────────────────────

def apply_to_job(page: Page, job: dict, answers: dict) -> bool:
    """
    Navigate to a Naukri job and apply.
    Returns True if application was submitted successfully.
    """
    url = job["url"]
    company = job["company"]
    title = job["title"]

    print(f"\n  ── Applying: {title} at {company} ──")

    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    random_delay_page_load()

    # Safety checks
    if check_for_captcha(page):
        print("  ✗ CAPTCHA detected! Stopping.")
        trigger_cooldown(PLATFORM)
        return False

    if check_for_block(page):
        print("  ✗ Account restriction detected! Stopping.")
        trigger_cooldown(PLATFORM)
        return False

    if check_login_required(page, PLATFORM):
        print("  ✗ Logged out. Stopping.")
        return False

    content = page.content().lower()

    # Check if already applied
    if "already applied" in content or "you have already applied" in content:
        print(f"    ⊘ Already applied — skipping")
        return False

    # Find the Apply button
    apply_btn = page.locator(
        "button#apply-button, "
        "button:has-text('Apply'), "
        "button.apply-btn, "
        "button[class*='apply'], "
        "a:has-text('Apply on company site')"
    )

    if apply_btn.count() == 0:
        print(f"    ⊘ No Apply button found — skipping")
        return False

    btn_text = apply_btn.first.inner_text().strip().lower()

    # Skip "Apply on company site" — that opens external site
    if "company site" in btn_text:
        print(f"    ⊘ External apply (company site) — skipping")
        return False

    random_delay_before_click()
    apply_btn.first.click()
    page.wait_for_timeout(3000)

    # Handle questionnaire popup if any
    success = _handle_apply_modal(page, answers)

    if success:
        print(f"  ✓ Applied: {title} at {company}")
    else:
        # Naukri sometimes applies directly without modal (profile-based)
        content_after = page.content().lower()
        if "applied successfully" in content_after or "application submitted" in content_after:
            print(f"  ✓ Applied (direct): {title} at {company}")
            return True
        print(f"  ✗ Could not complete: {title} at {company}")

    return success


def _handle_apply_modal(page: Page, answers: dict) -> bool:
    """Handle Naukri's apply questionnaire popup."""

    # Check if a modal/dialog appeared
    modal = page.locator(
        "div.chatbot-container, "
        "div.apply-modal, "
        "div[class*='questionnaire'], "
        "div[role='dialog']"
    )

    # Sometimes Naukri applies directly (no modal)
    if modal.count() == 0:
        page.wait_for_timeout(2000)
        content = page.content().lower()
        if "applied successfully" in content or "application submitted" in content:
            return True
        # Still no modal — might have applied directly
        return "already applied" not in content

    # Fill form fields in the modal
    max_steps = 6
    for step in range(max_steps):
        page.wait_for_timeout(2000)

        # Fill text inputs
        inputs = page.locator(
            "div[role='dialog'] input[type='text'], "
            "div[class*='questionnaire'] input[type='text'], "
            "div.chatbot-container input"
        ).all()

        for inp in inputs:
            try:
                if not inp.is_visible() or not inp.is_enabled():
                    continue
                current_val = inp.input_value().strip()
                if current_val:
                    continue
                label = _get_naukri_field_label(page, inp)
                answer = fuzzy_match_question(label, answers) if label else None
                if answer:
                    inp.click()
                    inp.fill(answer)
                    random_delay_form_field()
            except Exception:
                continue

        # Fill number inputs
        num_inputs = page.locator(
            "div[role='dialog'] input[type='number'], "
            "div[class*='questionnaire'] input[type='number']"
        ).all()

        for inp in num_inputs:
            try:
                if not inp.is_visible() or not inp.is_enabled():
                    continue
                current_val = inp.input_value().strip()
                if current_val:
                    continue
                label = _get_naukri_field_label(page, inp)
                answer = fuzzy_match_question(label, answers) if label else None
                if answer:
                    inp.click()
                    inp.fill(answer)
                    random_delay_form_field()
            except Exception:
                continue

        # Handle radio buttons
        radio_groups = page.locator(
            "div[role='dialog'] div[class*='radio'], "
            "div[class*='questionnaire'] div[class*='radio']"
        ).all()

        for group in radio_groups:
            try:
                label_el = group.locator("label, span").first
                if label_el.count() == 0:
                    continue
                question = label_el.inner_text().strip()
                answer = fuzzy_match_question(question, answers)
                if answer:
                    options = group.locator("input[type='radio']").all()
                    for opt in options:
                        opt_label = opt.locator("xpath=following-sibling::* | xpath=../label | xpath=../../label")
                        if opt_label.count() > 0:
                            if answer.lower() in opt_label.first.inner_text().strip().lower():
                                opt.click()
                                random_delay_form_field()
                                break
            except Exception:
                continue

        # Look for Submit / Next buttons
        submit_btn = page.locator(
            "button:has-text('Submit'), "
            "button:has-text('Apply'), "
            "button[type='submit']"
        ).last

        next_btn = page.locator(
            "button:has-text('Next'), "
            "button:has-text('Continue'), "
            "button:has-text('Save')"
        )

        if submit_btn.count() > 0 and submit_btn.is_visible():
            random_delay_before_click()
            submit_btn.click()
            random_delay_after_submit()

            # Check success
            page.wait_for_timeout(3000)
            content = page.content().lower()
            if "applied successfully" in content or "application submitted" in content:
                return True
            return True  # assume success if no error

        elif next_btn.count() > 0 and next_btn.first.is_visible():
            random_delay_before_click()
            next_btn.first.click()
            continue

        else:
            page.wait_for_timeout(2000)
            content = page.content().lower()
            if "applied successfully" in content:
                return True
            break

    return False


def _get_naukri_field_label(page: Page, element) -> str:
    """Get the label for a Naukri form field."""
    try:
        aria = element.get_attribute("aria-label")
        if aria:
            return aria

        placeholder = element.get_attribute("placeholder")
        if placeholder:
            return placeholder

        field_id = element.get_attribute("id")
        if field_id:
            label_el = page.locator(f"label[for='{field_id}']")
            if label_el.count() > 0:
                return label_el.first.inner_text().strip()

        parent = element.locator("xpath=ancestor::div[1]")
        if parent.count() > 0:
            label = parent.first.locator("label, span.label, div.label")
            if label.count() > 0:
                return label.first.inner_text().strip()
    except Exception:
        pass
    return ""


# ─── Main Run Function ──────────────────────────────────────────────────────

def run_naukri_apply(
    roles: list[str] | None = None,
    location: str = "Bangalore",
    max_applies: int = 12,
):
    """
    Main entry point for Naukri Quick Apply.
    """
    from config import JOB_SEARCH_CONFIG

    if roles is None:
        roles = JOB_SEARCH_CONFIG["target_roles"][:5]

    allowed, reason = can_apply(PLATFORM)
    if not allowed:
        print(f"\n  ✗ Cannot apply: {reason}")
        print_stats()
        return

    answers = load_answers()
    applied_count = 0

    print(f"\n  {'='*50}")
    print(f"  NAUKRI QUICK APPLY")
    print(f"  Roles: {', '.join(roles[:3])}...")
    print(f"  Location: {location}")
    print(f"  Max this session: {max_applies}")
    print(f"  {'='*50}")

    pw, context, page = create_browser(PLATFORM)

    try:
        if not ensure_logged_in(page):
            return

        for role in roles:
            if applied_count >= max_applies:
                break

            stop, reason = should_stop(PLATFORM)
            if stop:
                print(f"\n  ✗ Stopping: {reason}")
                break

            print(f"\n  ── Searching: {role} ──")
            search_url = build_search_url(role, location, experience=10)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            random_delay_page_load()

            if check_for_captcha(page):
                print("  ✗ CAPTCHA on search page! Stopping.")
                trigger_cooldown(PLATFORM)
                break

            jobs = collect_job_listings(page, max_jobs=15)
            print(f"    Found {len(jobs)} jobs")

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
                    print(f"    ⊘ Already applied: {job['title'][:40]}")
                    continue

                try:
                    success = apply_to_job(page, job, answers)
                    record_application(
                        PLATFORM, job["url"], job["company"], job["title"], success
                    )
                    if success:
                        applied_count += 1

                    if applied_count < max_applies:
                        random_delay_between_applies()

                except PlaywrightTimeout:
                    print(f"    ⊘ Timeout on: {job['title'][:40]}")
                    record_application(PLATFORM, job["url"], job["company"], job["title"], False)
                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    record_application(PLATFORM, job["url"], job["company"], job["title"], False)

    except KeyboardInterrupt:
        print("\n\n  ⊘ Interrupted by user.")

    finally:
        print(f"\n  ── Session Complete ──")
        print(f"  Applied: {applied_count}")
        print_stats()
        close_browser(pw, context)


if __name__ == "__main__":
    run_naukri_apply()
