#!/usr/bin/env python3
"""
Auto-Apply Orchestrator.

Usage:
  python3 -m apply.run                          # Apply on both LinkedIn + Naukri
  python3 -m apply.run linkedin                  # LinkedIn only
  python3 -m apply.run naukri                    # Naukri only
  python3 -m apply.run stats                    # Show today's stats
  python3 -m apply.run external                 # Show pending external apply jobs

  # Product companies only (searches Google, Microsoft, etc.)
  python3 -m apply.run linkedin --product

  # Specific companies
  python3 -m apply.run linkedin --companies "Google,Microsoft,Atlassian"

  # Custom roles + location
  python3 -m apply.run linkedin --roles "Lead Test Engineer,Test Architect"
  python3 -m apply.run linkedin --max 5 --location Bangalore

First run on each platform: browser opens → log in manually → session saved.
Subsequent runs: auto-applies using saved session.
"""

import os
import sys
import json
import argparse

from apply.safety import print_stats, get_today_stats


EXTERNAL_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "external_apply_jobs.json")


def show_external_jobs():
    """Show pending external apply jobs that need manual application."""
    if not os.path.exists(EXTERNAL_LOG):
        print("\n  No external apply jobs collected yet.")
        print("  Run with --product flag to find product company jobs.")
        return

    with open(EXTERNAL_LOG) as f:
        entries = json.load(f)

    pending = [e for e in entries if e.get("status") == "pending"]
    done = [e for e in entries if e.get("status") == "applied"]

    print(f"\n  {'='*65}")
    print(f"  EXTERNAL APPLY JOBS (Company Career Pages)")
    print(f"  {'='*65}")
    print(f"  Total: {len(entries)} | Pending: {len(pending)} | Done: {len(done)}")
    print(f"  {'-'*65}")

    if not pending:
        print("  No pending jobs. All done!")
        return

    for i, job in enumerate(pending, 1):
        portal = job.get("portal_type", "Unknown")
        print(f"\n  {i}. {job['title']}")
        print(f"     Company:  {job['company']}")
        print(f"     Portal:   {portal}")
        print(f"     URL:      {job['external_url'][:80]}")
        print(f"     Found:    {job.get('found_at', 'Unknown')[:10]}")

    print(f"\n  TIP: Open these URLs in your browser and apply manually.")
    print(f"  After applying, update status in data/external_apply_jobs.json")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-apply to jobs on LinkedIn and Naukri"
    )
    parser.add_argument(
        "platform",
        nargs="?",
        default="both",
        choices=["linkedin", "naukri", "both", "stats", "external"],
        help="Platform to apply on (default: both)",
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Comma-separated roles to search (default: from config.py)",
    )
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Location filter (default: India for LinkedIn, Bangalore for Naukri)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Max applications per platform this session",
    )
    parser.add_argument(
        "--product",
        action="store_true",
        help="Search only product-based companies (from config.py)",
    )
    parser.add_argument(
        "--companies",
        type=str,
        default=None,
        help="Comma-separated company names to search (e.g. 'Google,Microsoft')",
    )
    parser.add_argument(
        "--easy-only",
        action="store_true",
        help="Only apply to Easy Apply / Quick Apply jobs (skip external)",
    )

    args = parser.parse_args()

    # Parse inputs
    roles = None
    if args.roles:
        roles = [r.strip() for r in args.roles.split(",")]

    companies = None
    if args.companies:
        companies = [c.strip() for c in args.companies.split(",")]
    elif args.product:
        from config import PRODUCT_COMPANIES
        companies = PRODUCT_COMPANIES[:20]  # top 20 per session

    # Stats only
    if args.platform == "stats":
        print_stats()
        return

    # External jobs view
    if args.platform == "external":
        show_external_jobs()
        return

    print("\n" + "=" * 55)
    print("  AUTO-APPLY JOB BOT")
    print("  Safety: rate-limited, human-like delays, auto-stop")
    if companies:
        print(f"  Companies: {', '.join(companies[:5])}{'...' if len(companies) > 5 else ''}")
    print("=" * 55)

    stats = get_today_stats()
    print(f"\n  Today so far: {stats['total']}/{stats['limits']['total']} total")
    print(f"    LinkedIn: {stats['linkedin']}/{stats['limits']['linkedin']}")
    print(f"    Naukri:   {stats['naukri']}/{stats['limits']['naukri']}")

    # Run LinkedIn
    if args.platform in ("linkedin", "both"):
        remaining = stats["limits"]["linkedin"] - stats["linkedin"]
        if remaining <= 0:
            print(f"\n  ⊘ LinkedIn daily limit already reached.")
        else:
            max_li = min(args.max or 10, remaining)
            print(f"\n  Starting LinkedIn ({max_li} max)...")
            from apply.linkedin import run_linkedin_apply
            run_linkedin_apply(
                roles=roles,
                location=args.location or "India",
                max_applies=max_li,
                companies=companies,
                easy_apply_only=args.easy_only,
            )

    # Run Naukri
    if args.platform in ("naukri", "both"):
        remaining = stats["limits"]["naukri"] - stats["naukri"]
        if remaining <= 0:
            print(f"\n  ⊘ Naukri daily limit already reached.")
        else:
            max_nk = min(args.max or 12, remaining)
            print(f"\n  Starting Naukri ({max_nk} max)...")
            from apply.naukri import run_naukri_apply
            run_naukri_apply(
                roles=roles,
                location=args.location or "Bangalore",
                max_applies=max_nk,
            )

    # Final summary
    print("\n" + "=" * 55)
    print("  SESSION COMPLETE")
    print("=" * 55)
    print_stats()


if __name__ == "__main__":
    main()
