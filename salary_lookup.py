#!/usr/bin/env python3
"""
Salary Lookup — Generate salary research URLs for matched roles.

Opens Levels.fyi, Glassdoor, and AmbitionBox salary pages for your
target roles and companies. No scraping — just opens the right URLs.

Usage:
  python salary_lookup.py "Google" "Lead Test Engineer"
  python salary_lookup.py --company "Microsoft" --role "SDET Lead"
"""

import re
import webbrowser
from urllib.parse import quote_plus


def generate_salary_urls(company: str, role: str, location: str = "India") -> dict:
    """
    Generate salary research URLs for a company + role combination.

    Returns dict of { platform_name: url }
    """
    company_encoded = quote_plus(company)
    role_encoded = quote_plus(role)
    location_encoded = quote_plus(location)
    company_slug = re.sub(r'[^\w]', '-', company.lower()).strip('-')
    role_slug = re.sub(r'[^\w]', '-', role.lower()).strip('-')

    urls = {
        "Levels.fyi": (
            f"https://www.levels.fyi/companies/{company_slug}/salaries/{role_slug}"
        ),
        "Glassdoor": (
            f"https://www.glassdoor.co.in/Salary/"
            f"{company.replace(' ', '-')}-Salaries-E_IE0,0.htm"
            f"?filter.jobTitleExact={role_encoded}"
        ),
        "AmbitionBox": (
            f"https://www.ambitionbox.com/salaries/"
            f"{company_slug}-salaries?keyword={role_encoded}"
        ),
        "LinkedIn Salary": (
            f"https://www.linkedin.com/salary/search?"
            f"keywords={role_encoded}&countryCode=in"
        ),
        "PayScale": (
            f"https://www.payscale.com/research/IN/Job={role_encoded}/Salary"
        ),
    }

    return urls


def print_salary_urls(company: str, role: str, location: str = "India"):
    """Print formatted salary research URLs."""
    urls = generate_salary_urls(company, role, location)

    print(f"\n  {'=' * 60}")
    print(f"  SALARY RESEARCH: {role} at {company}")
    print(f"  {'=' * 60}")

    for platform, url in urls.items():
        print(f"\n  {platform}:")
        print(f"    {url}")

    print(f"\n  {'=' * 60}")
    return urls


def open_salary_urls(company: str, role: str, location: str = "India"):
    """Open all salary research URLs in the browser."""
    urls = generate_salary_urls(company, role, location)
    print(f"\n  Opening salary data for: {role} at {company}")
    for platform, url in urls.items():
        print(f"    Opening {platform}...")
        webbrowser.open(url)


def batch_salary_lookup(companies: list, role: str) -> dict:
    """
    Generate salary URLs for multiple companies.
    Returns { company: { platform: url } }
    """
    results = {}
    for company in companies:
        results[company] = generate_salary_urls(company, role)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Salary research URLs")
    parser.add_argument("company", nargs="?", help="Company name")
    parser.add_argument("role", nargs="?", help="Role/title")
    parser.add_argument("--open", action="store_true", help="Open URLs in browser")
    args = parser.parse_args()

    if not args.company:
        args.company = input("  Company: ").strip()
    if not args.role:
        args.role = input("  Role: ").strip()

    if args.open:
        open_salary_urls(args.company, args.role)
    else:
        print_salary_urls(args.company, args.role)
