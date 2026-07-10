#!/usr/bin/env python3
"""
Interactive Job Finder — Product Companies Only.

Searches LinkedIn for jobs at product-based companies,
reads each JD, scores it against your profile, and presents
the best-fit jobs one-by-one for YOU to decide.

Usage:
  python3 -m apply.finder
  python3 -m apply.finder --location Bangalore
  python3 -m apply.finder --min-score 50
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from apply.base import create_browser, close_browser
from config import PRODUCT_COMPANIES, JOB_SEARCH_CONFIG


BASE_URL = "https://www.linkedin.com"
FOUND_JOBS_LOG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "found_jobs.json"
)
SEEN_JOBS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "seen_job_ids.json"
)

# Role search queries — derived from your config.py target_roles
ROLE_SEARCHES = [role.lower() for role in JOB_SEARCH_CONFIG["target_roles"][:7]]


def _load_seen_jobs() -> set:
    """Load previously seen job IDs to avoid showing duplicates."""
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()


def _save_seen_jobs(seen: set):
    """Save seen job IDs."""
    os.makedirs(os.path.dirname(SEEN_JOBS_FILE), exist_ok=True)
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)


# ─── Your Profile (loaded from config — customize in config.py) ───────────────

# Build role keywords from config target_roles
_role_words = set()
for _r in JOB_SEARCH_CONFIG["target_roles"]:
    _role_words.update(w.lower() for w in _r.split() if len(w) > 2)

# Build core skills from TRENDING_SKILLS in config
_all_skills = []
for _category, _skills in __import__("config").TRENDING_SKILLS.items():
    _all_skills.extend(_skills)

MY_PROFILE = {
    "title": JOB_SEARCH_CONFIG["target_roles"][0],
    "experience_years": JOB_SEARCH_CONFIG["experience_years"],
    "core_skills": _all_skills,
    "leadership_skills": [
        "lead", "team management", "strategy", "architecture",
        "mentoring", "stakeholder management",
        "planning", "release management", "cross-functional",
    ],
    "domains": [d.lower() for d in JOB_SEARCH_CONFIG.get("domains", [])],
    "seniority_keywords": [
        "lead", "senior", "principal", "staff", "manager",
        "director", "architect", "head", "vp",
    ],
    "role_keywords": list(_role_words),
    "negative_keywords": [
        "intern", "internship", "fresher", "0-2 years", "0-1 years",
        "junior", "entry level", "trainee", "graduate",
    ],
}


# ─── JD Scoring ──────────────────────────────────────────────────────────────

def score_jd(title: str, jd_text: str) -> dict:
    """
    Score a job description against the user's profile.
    Returns dict with score (0-100), breakdown, and verdict.
    """
    title_lower = title.lower()
    jd_lower = jd_text.lower()
    full_text = f"{title_lower} {jd_lower}"

    # Instant reject
    for neg in MY_PROFILE["negative_keywords"]:
        if neg in title_lower:
            return {"score": 0, "verdict": "SKIP", "reason": f"Negative keyword: {neg}"}

    breakdown = {}

    # 1. Role match (0-30 pts)
    role_hits = [k for k in MY_PROFILE["role_keywords"] if k in full_text]
    role_score = min(len(role_hits) * 10, 30)
    breakdown["role_match"] = f"{role_score}/30 ({', '.join(role_hits[:3])})"

    # 2. Seniority match (0-15 pts)
    seniority_hits = [k for k in MY_PROFILE["seniority_keywords"] if k in full_text]
    seniority_score = min(len(seniority_hits) * 8, 15)
    breakdown["seniority"] = f"{seniority_score}/15 ({', '.join(seniority_hits[:2]) or 'none'})"

    # 3. Skills match (0-30 pts)
    skill_hits = [s for s in MY_PROFILE["core_skills"] if s in full_text]
    skill_score = min(len(skill_hits) * 3, 30)
    breakdown["skills"] = f"{skill_score}/30 ({len(skill_hits)} matched)"
    breakdown["matched_skills"] = skill_hits

    # 4. Leadership keywords (0-10 pts)
    lead_hits = [k for k in MY_PROFILE["leadership_skills"] if k in full_text]
    lead_score = min(len(lead_hits) * 3, 10)
    breakdown["leadership"] = f"{lead_score}/10 ({', '.join(lead_hits[:3]) or 'none'})"

    # 5. Domain match (0-10 pts)
    domain_hits = [d for d in MY_PROFILE["domains"] if d in full_text]
    domain_score = min(len(domain_hits) * 5, 10)
    breakdown["domain"] = f"{domain_score}/10 ({', '.join(domain_hits[:2]) or 'none'})"

    # 6. Experience level check (0-5 pts)
    exp_score = 0
    import re
    exp_matches = re.findall(r'(\d+)\s*[\-\+to]*\s*(\d*)\s*(?:years|yrs|yr)', jd_lower)
    for match in exp_matches:
        low = int(match[0])
        high = int(match[1]) if match[1] else low + 3
        if low <= 10 <= high + 2:
            exp_score = 5
            break
    breakdown["experience_fit"] = f"{exp_score}/5"

    total = role_score + seniority_score + skill_score + lead_score + domain_score + exp_score

    if total >= 60:
        verdict = "STRONG MATCH"
    elif total >= 40:
        verdict = "GOOD MATCH"
    elif total >= 25:
        verdict = "POSSIBLE"
    else:
        verdict = "WEAK"

    return {
        "score": total,
        "verdict": verdict,
        "breakdown": breakdown,
    }


# ─── LinkedIn Helpers ────────────────────────────────────────────────────────

def ensure_logged_in(page: Page) -> bool:
    """Check LinkedIn login."""
    page.goto(f"{BASE_URL}/feed/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    if "login" in page.url or "checkpoint" in page.url:
        print("\n  ╔══════════════════════════════════════════════════╗")
        print("  ║  LinkedIn login required.                       ║")
        print("  ║  Please log in manually in the browser window.  ║")
        print("  ║  Press ENTER here after you've logged in.       ║")
        print("  ╚══════════════════════════════════════════════════╝\n")
        input("  Press ENTER when logged in > ")
        page.wait_for_timeout(3000)
        if "login" in page.url:
            print("  ✗ Still not logged in.")
            return False

    print("  ✓ Logged into LinkedIn\n")
    return True


def search_company_jobs(page: Page, company: str, location: str, seen_ids: set) -> list[dict]:
    """Search LinkedIn for jobs at a specific company using configured role keywords."""
    loc = location.replace(" ", "%20")
    all_jobs = {}  # job_id -> job dict (deduped across searches)

    for role_query in ROLE_SEARCHES:
        keywords = f"{company} {role_query}".replace(" ", "%20")
        url = (
            f"{BASE_URL}/jobs/search/"
            f"?keywords={keywords}"
            f"&location={loc}"
            f"&sortBy=DD"
            f"&f_E=4%2C5"       # Senior + Director level
            f"&f_TPR=r2592000"   # Past month (30 days)
        )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeout:
            continue

        page.wait_for_timeout(2000)

        # Scroll deeper — 6 scrolls to load ~25-40 results
        for scroll in range(6):
            links = page.locator("a[href*='/jobs/view/']").all()

            for link in links:
                try:
                    if not link.is_visible():
                        continue
                    href = link.get_attribute("href") or ""
                    if "/jobs/view/" not in href:
                        continue
                    parts = href.split("/jobs/view/")
                    if len(parts) < 2:
                        continue
                    job_id = parts[1].split("/")[0].split("?")[0]
                    if not job_id.isdigit():
                        continue
                    # Skip already seen in this session or previous sessions
                    if job_id in all_jobs or job_id in seen_ids:
                        continue

                    title = link.inner_text().strip().split("\n")[0].strip()
                    if not title or len(title) < 3:
                        continue
                    if title.lower() in ("easy apply", "promoted", "viewed", "new"):
                        continue

                    all_jobs[job_id] = {
                        "title": title,
                        "company": company,
                        "url": f"{BASE_URL}/jobs/view/{job_id}/",
                        "job_id": job_id,
                    }
                except Exception:
                    continue

            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(1000)

    return list(all_jobs.values())


def read_job_description(page: Page, url: str) -> str:
    """Navigate to a job page and extract the JD text."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except PlaywrightTimeout:
        return ""

    page.wait_for_timeout(3000)

    # Try to expand "Show more" / "See more" if present
    try:
        for btn in page.locator("button").all():
            try:
                if btn.is_visible():
                    t = btn.inner_text().strip().lower()
                    if "show more" in t or "see more" in t:
                        btn.click()
                        page.wait_for_timeout(1000)
                        break
            except Exception:
                continue
    except Exception:
        pass

    # Extract full text from the main section
    try:
        main_text = page.locator("main").first.inner_text().strip()
    except Exception:
        return ""

    if not main_text:
        return ""

    # Find the JD section — it starts after "About the job"
    markers = ["about the job", "job description", "description"]
    main_lower = main_text.lower()

    for marker in markers:
        idx = main_lower.find(marker)
        if idx >= 0:
            # Take text from after the marker
            jd_start = idx + len(marker)
            jd_text = main_text[jd_start:].strip()

            # Cut off at common end markers
            end_markers = [
                "show less", "about the company", "similar jobs",
                "people also viewed", "set alert", "am i a good fit",
            ]
            for em in end_markers:
                em_idx = jd_text.lower().find(em)
                if em_idx > 100:
                    jd_text = jd_text[:em_idx].strip()
                    break

            if len(jd_text) > 50:
                return jd_text

    # Fallback: return everything after the first 500 chars (skip header/nav)
    if len(main_text) > 500:
        return main_text[300:]

    return main_text


def detect_apply_type(page: Page) -> str:
    """Check what kind of apply button is on the page."""
    buttons = page.locator("button").all()
    for btn in buttons:
        try:
            if not btn.is_visible():
                continue
            text = btn.inner_text().strip().lower()
            aria = (btn.get_attribute("aria-label") or "").lower()
            if "easy apply" in text or "easy apply" in aria:
                return "Easy Apply"
            if text in ("apply", "apply now"):
                return "External Apply"
        except Exception:
            continue
    return "Unknown"


def _log_found_job(job: dict, score_info: dict, apply_type: str):
    """Save found job to log."""
    entries = []
    if os.path.exists(FOUND_JOBS_LOG):
        with open(FOUND_JOBS_LOG) as f:
            entries = json.load(f)

    entries.append({
        "title": job["title"],
        "company": job["company"],
        "url": job["url"],
        "score": score_info["score"],
        "verdict": score_info["verdict"],
        "apply_type": apply_type,
        "found_at": datetime.now().isoformat(),
    })

    with open(FOUND_JOBS_LOG, "w") as f:
        json.dump(entries, f, indent=2)


# ─── Display ─────────────────────────────────────────────────────────────────

def display_job(job: dict, jd_text: str, score_info: dict, apply_type: str, index: int):
    """Display a job with detailed match report for user decision."""
    score = score_info["score"]
    verdict = score_info["verdict"]
    bd = score_info.get("breakdown", {})

    # Score bar
    filled = round(score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    # Verdict label
    if score >= 60:
        label = "🟢 STRONG MATCH"
    elif score >= 40:
        label = "🟡 GOOD MATCH"
    elif score >= 25:
        label = "🟠 POSSIBLE"
    else:
        label = "🔴 WEAK"

    print(f"\n  {'━'*65}")
    print(f"  JOB #{index}  |  {apply_type}")
    print(f"  {'━'*65}")
    print(f"  📌 {job['title']}")
    print(f"  🏢 {job['company']}")
    print(f"  🔗 {job['url']}")
    print(f"  {'─'*65}")
    print(f"  MATCH: {score}/100  [{bar}]  {label}")
    print(f"  {'─'*65}")

    # Detailed breakdown
    if bd:
        print(f"  📊 MATCH BREAKDOWN:")
        print(f"     Role Fit:      {bd.get('role_match', '-')}")
        print(f"     Seniority:     {bd.get('seniority', '-')}")
        print(f"     Skills:        {bd.get('skills', '-')}")
        print(f"     Leadership:    {bd.get('leadership', '-')}")
        print(f"     Domain:        {bd.get('domain', '-')}")
        print(f"     Experience:    {bd.get('experience_fit', '-')}")

    # Show matched skills clearly
    matched = bd.get("matched_skills", [])
    if matched:
        print(f"  {'─'*65}")
        print(f"  ✅ YOUR SKILLS IN JD: {', '.join(matched)}")

    # Show what's missing (skills in profile but not in JD)
    missing = [s for s in MY_PROFILE["core_skills"][:15] if s not in matched]
    if missing and matched:
        not_found = [s for s in missing if s in [
            "selenium", "playwright", "python", "java", "api testing",
            "performance testing", "docker", "kubernetes", "jenkins",
            "azure", "aws",
        ]]
        if not_found:
            print(f"  ⚠️  NOT IN JD:       {', '.join(not_found[:8])}")

    # Show JD snippet
    if jd_text:
        # Clean up and show first meaningful lines
        lines = [l.strip() for l in jd_text.split("\n") if l.strip() and len(l.strip()) > 10]
        snippet = " | ".join(lines[:5])
        if len(snippet) > 350:
            snippet = snippet[:350]
        print(f"  {'─'*65}")
        print(f"  📄 JD: {snippet}...")

    print(f"  {'━'*65}")


# ─── Main ────────────────────────────────────────────────────────────────────

def run_finder(location: str = "India", min_score: int = 25, max_companies: int = 20, top_n: int = 3):
    """Interactive job finder — scrapes ALL jobs per company, shows only top matches."""

    companies = PRODUCT_COMPANIES[:max_companies]

    print(f"\n  {'='*65}")
    print(f"  INTERACTIVE JOB FINDER — Product Companies")
    print(f"  {'='*65}")
    print(f"  Profile:    Lead Test Engineer, 10 yrs exp")
    print(f"  Companies:  {len(companies)} product companies")
    print(f"  Location:   {location}")
    print(f"  Min Score:  {min_score}/100")
    print(f"  Strategy:   Scrape ALL → Score ALL → Show TOP {top_n} per company")
    print(f"  {'='*65}")
    print(f"  Controls:   ENTER or Y = Apply  |  N = Skip  |  Q = Quit")
    print(f"  {'='*65}")

    pw, context, page = create_browser("linkedin")

    try:
        if not ensure_logged_in(page):
            return

        # Load previously seen job IDs
        seen_ids = _load_seen_jobs()
        print(f"  📋 {len(seen_ids)} jobs already seen (will skip)\n")

        job_index = 0
        applied = 0
        skipped = 0
        searched = 0
        quit_flag = False

        for company in companies:
            if quit_flag:
                break

            print(f"\n  🔍 Searching: {company} (7 role queries)...")
            searched += 1

            jobs = search_company_jobs(page, company, location, seen_ids)
            if not jobs:
                print(f"    No new jobs found at {company}")
                continue

            print(f"    Found {len(jobs)} new jobs — reading & scoring ALL JDs...")

            # ── Score ALL jobs first ──
            scored_jobs = []
            for i, job in enumerate(jobs):
                seen_ids.add(job["job_id"])

                jd_text = read_job_description(page, job["url"])
                if not jd_text:
                    continue

                score_info = score_jd(job["title"], jd_text)
                apply_type = detect_apply_type(page)

                scored_jobs.append({
                    "job": job,
                    "jd_text": jd_text,
                    "score_info": score_info,
                    "apply_type": apply_type,
                })

                # Progress indicator
                print(f"      [{i+1}/{len(jobs)}] {job['title'][:40]}... → {score_info['score']}/100", end="\r")

            print()  # clear progress line

            if not scored_jobs:
                print(f"    ⊘ No JDs could be read at {company}")
                continue

            # ── Sort by score, take top N above min_score ──
            scored_jobs.sort(key=lambda x: x["score_info"]["score"], reverse=True)
            best_jobs = [j for j in scored_jobs if j["score_info"]["score"] >= min_score][:top_n]

            if not best_jobs:
                best_score = scored_jobs[0]["score_info"]["score"] if scored_jobs else 0
                print(f"    ⊘ No matches ≥ {min_score} at {company} (best was {best_score}/100)")
                continue

            print(f"    ✅ {len(best_jobs)} best match(es) from {len(scored_jobs)} jobs:")

            # ── Present only the best matches ──
            for match in best_jobs:
                job_index += 1

                display_job(match["job"], match["jd_text"], match["score_info"],
                           match["apply_type"], job_index)
                _log_found_job(match["job"], match["score_info"], match["apply_type"])

                print()
                choice = input("  ➤ Apply? [Y/Enter=Yes, N=Skip, Q=Quit] > ").strip().lower()

                if choice in ("q", "quit", "exit"):
                    print("\n  Quitting...")
                    quit_flag = True
                    break

                if choice in ("", "y", "yes"):
                    # Navigate back to the job page for user to apply
                    page.goto(match["job"]["url"], wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2000)
                    print(f"  → Job page is open in the browser. Apply now!")
                    input("  Press ENTER after applying > ")
                    applied += 1
                    print(f"  ✓ Marked as applied ({applied} total)")
                else:
                    skipped += 1
                    print(f"  ⊘ Skipped")

        _save_seen_jobs(seen_ids)
        _print_summary(job_index, applied, skipped, searched)

    except KeyboardInterrupt:
        print("\n\n  ⊘ Interrupted.")
        if 'seen_ids' in dir():
            _save_seen_jobs(seen_ids)
        _print_summary(job_index if 'job_index' in dir() else 0,
                       applied if 'applied' in dir() else 0,
                       skipped if 'skipped' in dir() else 0,
                       searched if 'searched' in dir() else 0)

    finally:
        close_browser(pw, context)


def _print_summary(shown: int, applied: int, skipped: int, companies_searched: int):
    """Print session summary."""
    print(f"\n  {'='*60}")
    print(f"  SESSION SUMMARY")
    print(f"  {'='*60}")
    print(f"  Companies searched: {companies_searched}")
    print(f"  Jobs shown:         {shown}")
    print(f"  Applied:            {applied}")
    print(f"  Skipped:            {skipped}")
    print(f"  {'='*60}")
    if os.path.exists(FOUND_JOBS_LOG):
        print(f"  All found jobs saved to: data/found_jobs.json")


# ─── Clear LinkedIn Applied List ─────────────────────────────────────────────

def clear_linkedin_applied(page: Page):
    """Navigate to LinkedIn 'My Jobs' → 'Applied' and archive all jobs."""
    import time

    print("\n  🧹 Clearing LinkedIn 'Applied' jobs list...")
    page.goto("https://www.linkedin.com/my-items/saved-jobs/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # Click "Applied" tab/filter
    applied_tab = page.locator("button:has-text('Applied'), a:has-text('Applied')").first
    if applied_tab.is_visible():
        applied_tab.click()
        page.wait_for_timeout(3000)
    else:
        # Try direct URL
        page.goto("https://www.linkedin.com/my-items/saved-jobs/?cardType=APPLIED", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

    archived_count = 0
    max_attempts = 100  # safety limit

    for _ in range(max_attempts):
        # Find job cards with dismiss/archive/more-options buttons
        dismiss_buttons = page.locator(
            "button[aria-label*='Dismiss'], "
            "button[aria-label*='dismiss'], "
            "button[aria-label*='Remove'], "
            "button[aria-label*='remove'], "
            "button[aria-label*='Archive'], "
            "button[aria-label*='archive']"
        )

        if dismiss_buttons.count() == 0:
            # Try the 3-dot menu approach
            more_buttons = page.locator(
                "button[aria-label*='more actions'], "
                "button[aria-label*='More actions'], "
                "button.artdeco-dropdown__trigger"
            )
            if more_buttons.count() == 0:
                break

            # Click first 3-dot menu
            more_buttons.first.click()
            page.wait_for_timeout(1000)

            # Look for "Archive" or "Remove" in dropdown
            archive_option = page.locator(
                "div[role='menuitem']:has-text('Archive'), "
                "li:has-text('Archive'), "
                "span:has-text('Archive')"
            ).first
            if archive_option.is_visible():
                archive_option.click()
            else:
                remove_option = page.locator(
                    "div[role='menuitem']:has-text('Remove'), "
                    "li:has-text('Remove'), "
                    "span:has-text('Remove')"
                ).first
                if remove_option.is_visible():
                    remove_option.click()
                else:
                    # Close menu if nothing found
                    page.keyboard.press("Escape")
                    break
        else:
            dismiss_buttons.first.click()

        archived_count += 1
        page.wait_for_timeout(random.uniform(1.0, 2.0) * 1000)
        print(f"    Cleared {archived_count} jobs...", end="\r")

    print(f"\n  ✓ Cleared {archived_count} jobs from Applied list.")
    return archived_count


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Interactive Job Finder — Product Companies")
    parser.add_argument("--location", default="India", help="Location filter (default: India)")
    parser.add_argument("--min-score", type=int, default=25, help="Minimum match score 0-100 (default: 25)")
    parser.add_argument("--companies", type=int, default=20, help="Max companies to search (default: 20)")
    parser.add_argument("--top", type=int, default=3, help="Show top N best matches per company (default: 3)")
    parser.add_argument("--reset-seen", action="store_true", help="Clear seen jobs history and start fresh")
    parser.add_argument("--clear-applied", action="store_true", help="Clear LinkedIn 'Applied' list before searching")
    args = parser.parse_args()

    if args.reset_seen:
        if os.path.exists(SEEN_JOBS_FILE):
            os.remove(SEEN_JOBS_FILE)
            print("  ✓ Seen jobs history cleared.")

    if args.clear_applied:
        pw, context, page = create_browser("linkedin")
        try:
            if ensure_logged_in(page):
                clear_linkedin_applied(page)
        finally:
            close_browser(pw, context)

    run_finder(
        location=args.location,
        min_score=args.min_score,
        max_companies=args.companies,
        top_n=args.top,
    )


if __name__ == "__main__":
    main()
