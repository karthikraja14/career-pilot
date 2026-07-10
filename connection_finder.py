#!/usr/bin/env python3
"""
LinkedIn Connection Finder — Find people to connect with at target companies.

Generates LinkedIn search URLs to find employees at your target companies
for networking and referrals. No scraping — opens the right search pages.

Usage:
  python connection_finder.py "Google"
  python connection_finder.py --company "Microsoft" --role "Test"
"""

import webbrowser
from urllib.parse import quote_plus

from config import PRODUCT_COMPANIES, JOB_SEARCH_CONFIG


def generate_connection_urls(company: str, role_keyword: str = "") -> dict:
    """
    Generate LinkedIn People search URLs for networking at a company.

    Returns dict of { search_type: url }
    """
    if not role_keyword:
        role_keyword = JOB_SEARCH_CONFIG.get("target_roles", [""])[0].split()[0].lower()
    company_encoded = quote_plus(company)
    role_encoded = quote_plus(role_keyword)

    urls = {
        "People in your role": (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords={role_encoded}%20{company_encoded}"
            f"&origin=GLOBAL_SEARCH_HEADER"
        ),
        "Engineering Managers": (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords=engineering%20manager%20{company_encoded}"
            f"&origin=GLOBAL_SEARCH_HEADER"
        ),
        "Recruiters": (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords=recruiter%20{company_encoded}"
            f"&origin=GLOBAL_SEARCH_HEADER"
        ),
        "Company Page": (
            f"https://www.linkedin.com/company/{company.lower().replace(' ', '-')}/"
        ),
        "Company Jobs": (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={role_encoded}&company={company_encoded}"
        ),
    }

    return urls


def print_connection_urls(company: str, role_keyword: str = "test"):
    """Print formatted connection search URLs."""
    urls = generate_connection_urls(company, role_keyword)

    print(f"\n  {'=' * 60}")
    print(f"  NETWORKING: {company}")
    print(f"  {'=' * 60}")

    for search_type, url in urls.items():
        print(f"\n  {search_type}:")
        print(f"    {url}")

    print(f"\n  TIP: Connect with a personalized note mentioning")
    print(f"  shared interests or mutual connections.")
    print(f"  {'=' * 60}")


def open_connection_urls(company: str, role_keyword: str = "test"):
    """Open all connection search URLs in browser."""
    urls = generate_connection_urls(company, role_keyword)
    print(f"\n  Opening LinkedIn searches for: {company}")
    for search_type, url in urls.items():
        print(f"    Opening {search_type}...")
        webbrowser.open(url)


def suggest_target_companies(max_companies: int = 10) -> list:
    """Suggest top companies to network at based on config."""
    # Prioritize healthcare companies (domain match)
    healthcare = [c for c in PRODUCT_COMPANIES[:60] if any(
        h in c.lower() for h in ["philips", "siemens", "medtronic", "abbott",
                                  "boston", "stryker", "baxter", "health",
                                  "medical", "roche"]
    )]
    tech = [c for c in PRODUCT_COMPANIES if c in [
        "Google", "Microsoft", "Amazon", "Apple", "Meta",
        "Atlassian", "Salesforce", "Adobe", "Intuit",
    ]]

    suggestions = healthcare[:5] + tech[:5]
    return suggestions[:max_companies]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Find connections at target companies")
    parser.add_argument("company", nargs="?", help="Company name")
    parser.add_argument("--role", default="test", help="Role keyword for search")
    parser.add_argument("--open", action="store_true", help="Open URLs in browser")
    parser.add_argument("--suggest", action="store_true", help="Show suggested companies")
    args = parser.parse_args()

    if args.suggest:
        suggestions = suggest_target_companies()
        print("\n  TOP COMPANIES TO NETWORK AT:")
        for i, c in enumerate(suggestions, 1):
            print(f"    {i}. {c}")
        print()
    elif args.company:
        if args.open:
            open_connection_urls(args.company, args.role)
        else:
            print_connection_urls(args.company, args.role)
    else:
        company = input("  Company: ").strip()
        if company:
            print_connection_urls(company, args.role)
