#!/usr/bin/env python3
"""
Job Matcher & Application Tracker
Finds suitable job listings, prioritizes product-based companies,
matches against your resume profile, and tracks applications.
"""

import re
import os
import json
import csv
from datetime import datetime

from config import PRODUCT_COMPANIES, JOB_SEARCH_CONFIG, TRENDING_SKILLS


# ─── Profile Extraction ───────────────────────────────────────────────────────

def build_profile_from_analysis(analysis_path: str) -> dict:
    """Build a job-search profile from resume analysis JSON."""
    with open(analysis_path) as f:
        analysis = json.load(f)

    return {
        "target_roles": JOB_SEARCH_CONFIG["target_roles"],
        "experience_years": JOB_SEARCH_CONFIG["experience_years"],
        "locations": JOB_SEARCH_CONFIG["preferred_locations"],
        "domains": JOB_SEARCH_CONFIG["domains"],
        "current_skills": _extract_skills_from_analysis(analysis),
        "contact": analysis.get("contact_info", {}),
    }


def _extract_skills_from_analysis(analysis: dict) -> list:
    """Extract detected skills from resume text analysis."""
    # This will be populated from the resume text
    all_skills = []
    for category_skills in TRENDING_SKILLS.values():
        all_skills.extend(category_skills)
    return all_skills


# ─── Job Search URL Generators ─────────────────────────────────────────────────

def generate_search_urls(profile: dict) -> dict:
    """Generate job search URLs for multiple platforms."""
    urls = {}

    for role in profile["target_roles"][:5]:
        role_encoded = role.replace(" ", "%20")
        role_plus = role.replace(" ", "+")
        location = profile["locations"][0] if profile["locations"] else "Bangalore"
        loc_encoded = location.replace(" ", "%20")

        # LinkedIn
        urls[f"LinkedIn - {role}"] = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={role_encoded}&location={loc_encoded}"
            f"&f_E=4%2C5&sortBy=R"  # Senior+Director level, sorted by relevance
        )

        # Naukri
        urls[f"Naukri - {role}"] = (
            f"https://www.naukri.com/{role.lower().replace(' ', '-')}-jobs-in-{location.lower()}"
            f"?experience={profile['experience_years']}"
        )

        # Indeed
        urls[f"Indeed - {role}"] = (
            f"https://www.indeed.co.in/jobs?q={role_plus}&l={location}"
        )

    return urls


# ─── Product Company Matcher ──────────────────────────────────────────────────

def match_product_companies(profile: dict) -> list[dict]:
    """Generate targeted search links for product-based companies."""
    matches = []

    for company in PRODUCT_COMPANIES:
        company_lower = company.lower().replace(" ", "")
        company_encoded = company.replace(" ", "%20")

        # Determine relevance
        relevance = "Medium"
        if any(d.lower() in company.lower() for d in ["philips", "siemens", "ge", "medtronic",
                                                        "abbott", "boston", "stryker", "baxter",
                                                        "edwards", "intuitive"]):
            relevance = "High (Healthcare Domain Match)"
        elif any(d.lower() in company.lower() for d in ["google", "microsoft", "amazon", "apple",
                                                          "meta", "atlassian", "salesforce"]):
            relevance = "High (Top Tech)"

        for role in profile["target_roles"][:3]:
            role_encoded = role.replace(" ", "%20")
            matches.append({
                "company": company,
                "role": role,
                "relevance": relevance,
                "careers_search": f"https://www.linkedin.com/jobs/search/?keywords={role_encoded}&company={company_encoded}",
                "company_type": "Product-Based",
            })

    # Sort by relevance
    relevance_order = {"High (Healthcare Domain Match)": 0, "High (Top Tech)": 1, "Medium": 2}
    matches.sort(key=lambda x: relevance_order.get(x["relevance"], 3))
    return matches


# ─── Application Tracker ──────────────────────────────────────────────────────

TRACKER_FILE = "applications/tracker.json"
TRACKER_CSV = "applications/tracker.csv"


def init_tracker():
    """Initialize the application tracker files."""
    os.makedirs("applications", exist_ok=True)
    if not os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "w") as f:
            json.dump({"applications": [], "stats": {}}, f, indent=2)


def add_application(company: str, role: str, platform: str, url: str = "",
                    status: str = "To Apply", notes: str = "") -> dict:
    """Add a new job application to the tracker."""
    init_tracker()

    # Duplicate detection — check if already applied to same company on any platform
    duplicate = check_duplicate_application(company, role)
    if duplicate:
        print(f"  ⚠ Duplicate: Already tracked '{duplicate['role']}' at {duplicate['company']}"
              f" on {duplicate['platform']} ({duplicate['status']})")

    with open(TRACKER_FILE) as f:
        data = json.load(f)

    entry = {
        "id": len(data["applications"]) + 1,
        "company": company,
        "role": role,
        "platform": platform,
        "url": url,
        "status": status,
        "applied_date": None,
        "response_date": None,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "is_product_company": company in PRODUCT_COMPANIES,
    }

    data["applications"].append(entry)
    _save_tracker(data)
    return entry


def update_application(app_id: int, **updates) -> dict | None:
    """Update an existing application entry."""
    init_tracker()
    with open(TRACKER_FILE) as f:
        data = json.load(f)

    for app in data["applications"]:
        if app["id"] == app_id:
            app.update(updates)
            if updates.get("status") == "Applied":
                app["applied_date"] = datetime.now().isoformat()
            _save_tracker(data)
            return app
    return None


def check_duplicate_application(company: str, role: str = None) -> dict | None:
    """
    Check if we've already applied to this company (on any platform).
    Returns the existing application entry if found, else None.
    """
    init_tracker()
    with open(TRACKER_FILE) as f:
        data = json.load(f)

    company_lower = company.lower().strip()
    for app in data["applications"]:
        if app.get("company", "").lower().strip() == company_lower:
            return app
    return None


def get_tracker_stats() -> dict:
    """Get application tracking statistics."""
    init_tracker()
    with open(TRACKER_FILE) as f:
        data = json.load(f)

    apps = data["applications"]
    if not apps:
        return {"total": 0, "message": "No applications tracked yet."}

    stats = {
        "total": len(apps),
        "by_status": {},
        "product_companies": sum(1 for a in apps if a.get("is_product_company")),
        "service_companies": sum(1 for a in apps if not a.get("is_product_company")),
        "platforms": {},
    }

    for app in apps:
        status = app.get("status", "Unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        platform = app.get("platform", "Unknown")
        stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1

    return stats


def _save_tracker(data: dict):
    """Save tracker data to both JSON and CSV."""
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # Also export to CSV for easy viewing
    if data["applications"]:
        with open(TRACKER_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data["applications"][0].keys())
            writer.writeheader()
            writer.writerows(data["applications"])


def list_applications(status_filter: str = None) -> list:
    """List all tracked applications, optionally filtered by status."""
    init_tracker()
    with open(TRACKER_FILE) as f:
        data = json.load(f)

    apps = data["applications"]
    if status_filter:
        apps = [a for a in apps if a.get("status", "").lower() == status_filter.lower()]
    return apps


# ─── Report Generation ─────────────────────────────────────────────────────────

def generate_job_search_plan(profile: dict) -> str:
    """Generate a comprehensive job search action plan."""
    search_urls = generate_search_urls(profile)
    product_matches = match_product_companies(profile)

    # Group product matches by relevance
    high_priority = [m for m in product_matches if "High" in m["relevance"]]
    medium_priority = [m for m in product_matches if m["relevance"] == "Medium"]

    lines = []
    lines.append("=" * 70)
    lines.append("  JOB SEARCH & APPLICATION PLAN")
    lines.append("=" * 70)
    lines.append("")
    lines.append("  YOUR PROFILE")
    lines.append("  " + "-" * 40)
    lines.append(f"    Experience: {profile['experience_years']} years")
    lines.append(f"    Locations:  {', '.join(profile['locations'])}")
    lines.append(f"    Domains:    {', '.join(profile['domains'])}")
    lines.append(f"    Target Roles:")
    for role in profile["target_roles"]:
        lines.append(f"      - {role}")
    lines.append("")

    # Quick search links
    lines.append("  JOB SEARCH LINKS (open in browser)")
    lines.append("  " + "-" * 40)
    for name, url in list(search_urls.items())[:10]:
        lines.append(f"    {name}")
        lines.append(f"      {url}")
    lines.append("")

    # Product company targets
    lines.append("  HIGH PRIORITY - PRODUCT COMPANIES")
    lines.append("  " + "-" * 40)
    seen_companies = set()
    for match in high_priority:
        if match["company"] not in seen_companies:
            seen_companies.add(match["company"])
            lines.append(f"    [{match['relevance']}]")
            lines.append(f"    Company: {match['company']}")
            lines.append(f"    Search:  {match['careers_search']}")
            lines.append("")

    lines.append("  OTHER PRODUCT COMPANIES TO TARGET")
    lines.append("  " + "-" * 40)
    seen_companies_med = set()
    count = 0
    for match in medium_priority:
        if match["company"] not in seen_companies_med and count < 20:
            seen_companies_med.add(match["company"])
            lines.append(f"    - {match['company']}")
            count += 1
    lines.append("")

    # Action plan
    lines.append("  WEEKLY ACTION PLAN")
    lines.append("  " + "-" * 40)
    lines.append("    Week 1-2: Resume Optimization")
    lines.append("      - Fix all priority issues from resume analysis")
    lines.append("      - Create role-specific resume variants")
    lines.append("      - Update LinkedIn profile to match resume")
    lines.append("")
    lines.append("    Week 3-4: Targeted Applications")
    lines.append("      - Apply to 5 healthcare product companies (domain match)")
    lines.append("      - Apply to 5 top tech product companies")
    lines.append("      - Set up job alerts on LinkedIn, Naukri, Indeed")
    lines.append("")
    lines.append("    Ongoing: Track & Follow Up")
    lines.append("      - Track all applications using this tool")
    lines.append("      - Follow up after 1 week if no response")
    lines.append("      - Network with employees at target companies")
    lines.append("")
    lines.append("  APPLICATION TARGETS")
    lines.append("  " + "-" * 40)
    lines.append("    Daily:   2-3 quality applications")
    lines.append("    Weekly:  10-15 applications")
    lines.append("    Split:   70% Product | 30% Service (fallback)")
    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# ─── Entry Point ───────────────────────────────────────────────────────────────

def print_menu():
    """Print interactive menu."""
    print("\n" + "=" * 50)
    print("  JOB MATCHER & APPLICATION TRACKER")
    print("=" * 50)
    print("  1. Generate Job Search Plan")
    print("  2. Add Application")
    print("  3. List Applications")
    print("  4. Update Application Status")
    print("  5. View Stats")
    print("  6. Exit")
    print("=" * 50)


if __name__ == "__main__":
    import sys

    # Check if analysis report exists
    reports_dir = "reports"
    analysis_file = None

    if os.path.exists(reports_dir):
        files = sorted([f for f in os.listdir(reports_dir) if f.startswith("resume_analysis")])
        if files:
            analysis_file = os.path.join(reports_dir, files[-1])

    # Build profile
    if analysis_file:
        profile = build_profile_from_analysis(analysis_file)
        print(f"\nLoaded profile from: {analysis_file}")
    else:
        print("\nNo resume analysis found. Run resume_analyzer.py first.")
        print("Using default profile from config...")
        profile = {
            "target_roles": JOB_SEARCH_CONFIG["target_roles"],
            "experience_years": JOB_SEARCH_CONFIG["experience_years"],
            "locations": JOB_SEARCH_CONFIG["preferred_locations"],
            "domains": JOB_SEARCH_CONFIG["domains"],
            "current_skills": [],
            "contact": {},
        }

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "plan":
            plan = generate_job_search_plan(profile)
            print(plan)
        elif cmd == "stats":
            stats = get_tracker_stats()
            print(json.dumps(stats, indent=2))
        elif cmd == "add":
            if len(sys.argv) >= 5:
                entry = add_application(sys.argv[2], sys.argv[3], sys.argv[4])
                print(f"Added: #{entry['id']} - {entry['company']} - {entry['role']}")
            else:
                print("Usage: python3 job_matcher.py add <company> <role> <platform>")
        elif cmd == "list":
            apps = list_applications()
            for app in apps:
                product_tag = "[PRODUCT]" if app.get("is_product_company") else "[SERVICE]"
                print(f"  #{app['id']} {product_tag} {app['company']} - {app['role']} [{app['status']}]")
        else:
            print(f"Unknown command: {cmd}")
    else:
        # Generate plan by default
        plan = generate_job_search_plan(profile)
        print(plan)
