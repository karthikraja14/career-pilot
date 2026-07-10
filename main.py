#!/usr/bin/env python3
"""
Resume Builder Suite — Main Entry Point
  1. Analyze & Score your resume
  2. Find jobs & track applications (product companies preferred)
"""

import os
import sys
import json

from resume_analyzer import run_analysis
from job_matcher import (
    build_profile_from_analysis,
    generate_job_search_plan,
    add_application,
    list_applications,
    update_application,
    get_tracker_stats,
)
from config import JOB_SEARCH_CONFIG


REPORTS_DIR = "reports"


def get_latest_analysis() -> str | None:
    """Find the most recent resume analysis report."""
    if not os.path.exists(REPORTS_DIR):
        return None
    files = sorted(
        [f for f in os.listdir(REPORTS_DIR) if f.startswith("resume_analysis")],
    )
    return os.path.join(REPORTS_DIR, files[-1]) if files else None


def menu_analyze():
    """Run resume analysis."""
    pdfs = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
    if not pdfs:
        print("\n  No PDF resume found in the current directory.")
        return
    if len(pdfs) == 1:
        pdf_path = pdfs[0]
    else:
        print("\n  Found multiple PDFs:")
        for i, f in enumerate(pdfs, 1):
            print(f"    {i}. {f}")
        choice = input("  Select PDF number: ").strip()
        try:
            pdf_path = pdfs[int(choice) - 1]
        except (ValueError, IndexError):
            print("  Invalid choice.")
            return

    result = run_analysis(pdf_path)
    if result:
        overall = result["overall_score"]
        grade = result["grade"]
        print(f"\n  YOUR SCORE: {overall}/100 (Grade: {grade})")
        if overall < 60:
            print("  ⚠  Your resume needs significant improvement before applying.")
            print("     Fix the priority items above first.")
        elif overall < 75:
            print("  ~  Decent, but fixing the suggestions above will boost your chances.")
        else:
            print("  ✓  Your resume is in good shape. Start applying!")


def menu_job_plan():
    """Generate job search plan."""
    analysis_file = get_latest_analysis()
    if analysis_file:
        profile = build_profile_from_analysis(analysis_file)
        print(f"\n  Using profile from: {analysis_file}")
    else:
        print("\n  No analysis found. Run 'Analyze Resume' first for better matching.")
        print("  Using default profile...")
        profile = {
            "target_roles": JOB_SEARCH_CONFIG["target_roles"],
            "experience_years": JOB_SEARCH_CONFIG["experience_years"],
            "locations": JOB_SEARCH_CONFIG["preferred_locations"],
            "domains": JOB_SEARCH_CONFIG["domains"],
            "current_skills": [],
            "contact": {},
        }

    plan = generate_job_search_plan(profile)
    print(plan)


def menu_add_application():
    """Add a job application to the tracker."""
    print("\n  ADD NEW APPLICATION")
    print("  " + "-" * 40)
    company = input("  Company: ").strip()
    if not company:
        return
    role = input("  Role: ").strip()
    platform = input("  Platform (LinkedIn/Naukri/Indeed/Company/Other): ").strip()
    url = input("  Job URL (optional): ").strip()
    notes = input("  Notes (optional): ").strip()

    entry = add_application(company, role, platform, url=url, notes=notes)
    product_tag = "[PRODUCT]" if entry.get("is_product_company") else "[SERVICE]"
    print(f"\n  ✓ Added: #{entry['id']} {product_tag} {company} — {role}")


def menu_list_applications():
    """List tracked applications."""
    apps = list_applications()
    if not apps:
        print("\n  No applications tracked yet. Add one first.")
        return

    print(f"\n  TRACKED APPLICATIONS ({len(apps)} total)")
    print("  " + "-" * 60)
    print(f"  {'#':>3}  {'Type':8}  {'Company':20}  {'Role':20}  {'Status':10}")
    print("  " + "-" * 60)
    for app in apps:
        tag = "PRODUCT" if app.get("is_product_company") else "SERVICE"
        print(
            f"  {app['id']:>3}  {tag:8}  {app['company'][:20]:20}  "
            f"{app['role'][:20]:20}  {app['status']:10}"
        )


def menu_update_application():
    """Update application status."""
    apps = list_applications()
    if not apps:
        print("\n  No applications to update.")
        return

    menu_list_applications()
    app_id = input("\n  Enter application #: ").strip()
    try:
        app_id = int(app_id)
    except ValueError:
        print("  Invalid ID.")
        return

    print("  New status options: To Apply | Applied | Screening | Interview | Offer | Rejected")
    new_status = input("  New status: ").strip()
    if not new_status:
        return

    result = update_application(app_id, status=new_status)
    if result:
        print(f"  ✓ Updated #{app_id} → {new_status}")
    else:
        print(f"  Application #{app_id} not found.")


def menu_stats():
    """Show application statistics."""
    stats = get_tracker_stats()
    print("\n  APPLICATION STATISTICS")
    print("  " + "-" * 40)
    if stats["total"] == 0:
        print("  No applications tracked yet.")
        return

    print(f"  Total Applications:    {stats['total']}")
    print(f"  Product Companies:     {stats['product_companies']}")
    print(f"  Service Companies:     {stats['service_companies']}")
    print()
    print("  By Status:")
    for status, count in stats["by_status"].items():
        print(f"    {status:15s}: {count}")
    print()
    print("  By Platform:")
    for platform, count in stats["platforms"].items():
        print(f"    {platform:15s}: {count}")


def main():
    """Main interactive menu."""
    print("\n" + "=" * 50)
    print("  RESUME BUILDER & JOB FINDER SUITE")
    print("=" * 50)

    while True:
        print("\n  MAIN MENU")
        print("  " + "-" * 40)
        print("  1.  Analyze & Score Resume")
        print("  2.  Generate Job Search Plan")
        print("  3.  Add Application")
        print("  4.  List Applications")
        print("  5.  Update Application Status")
        print("  6.  View Stats")
        print("  ─── New Features ───")
        print("  7.  ATS Keyword Gap Analysis")
        print("  8.  Tailor Resume for a JD")
        print("  9.  Generate Cover Letter")
        print("  10. Export Resume as DOCX")
        print("  11. Open Dashboard")
        print("  12. Salary Research")
        print("  13. Find Connections at Company")
        print("  14. Resume Version History")
        print("  0.  Exit")
        print()

        choice = input("  Select: ").strip()

        if choice == "1":
            menu_analyze()
        elif choice == "2":
            menu_job_plan()
        elif choice == "3":
            menu_add_application()
        elif choice == "4":
            menu_list_applications()
        elif choice == "5":
            menu_update_application()
        elif choice == "6":
            menu_stats()
        elif choice == "7":
            from keyword_gap import run_gap_analysis
            run_gap_analysis()
        elif choice == "8":
            from jd_tailorer import run_tailorer
            run_tailorer(output_path="output/Tailored_Resume.pdf")
        elif choice == "9":
            from cover_letter import run_cover_letter
            run_cover_letter()
        elif choice == "10":
            from docx_export import run_docx_export
            run_docx_export()
        elif choice == "11":
            from dashboard import run_dashboard
            run_dashboard()
        elif choice == "12":
            from salary_lookup import print_salary_urls
            company = input("  Company: ").strip()
            role = input("  Role: ").strip()
            if company and role:
                print_salary_urls(company, role)
        elif choice == "13":
            from connection_finder import print_connection_urls
            company = input("  Company: ").strip()
            if company:
                print_connection_urls(company)
        elif choice == "14":
            from version_tracker import print_version_history
            print_version_history()
        elif choice == "0":
            print("\n  Good luck with your job search! 🚀\n")
            break
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    # Support direct commands: python main.py analyze | plan | stats
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "analyze":
            menu_analyze()
        elif cmd == "plan":
            menu_job_plan()
        elif cmd == "stats":
            menu_stats()
        elif cmd == "list":
            menu_list_applications()
        elif cmd == "dashboard":
            from dashboard import run_dashboard
            run_dashboard()
        elif cmd == "gap":
            from keyword_gap import run_gap_analysis
            run_gap_analysis()
        elif cmd == "docx":
            from docx_export import run_docx_export
            run_docx_export()
        elif cmd == "versions":
            from version_tracker import print_version_history
            print_version_history()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python main.py [analyze|plan|stats|list|dashboard|gap|docx|versions]")
    else:
        main()
