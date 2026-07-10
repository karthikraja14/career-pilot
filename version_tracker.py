#!/usr/bin/env python3
"""
Resume Version Tracker — Track which resume version was sent to each company.

Logs every resume submission with: company, role, resume variant used,
tailoring keywords (if any), and timestamp.

Usage:
  from version_tracker import record_version, get_version_history
"""

import os
import json
from datetime import datetime


VERSION_FILE = os.path.join("data", "resume_versions.json")


def _load_versions() -> list:
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return json.load(f)
    return []


def _save_versions(versions: list):
    os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
    with open(VERSION_FILE, "w") as f:
        json.dump(versions, f, indent=2)


def record_version(company: str, role: str, resume_file: str,
                   tailored: bool = False, keywords: list = None,
                   cover_letter: str = None) -> dict:
    """
    Record which resume version was sent to a company.

    Args:
        company: Company name
        role: Job title
        resume_file: Path to the resume file sent
        tailored: Whether the resume was tailored for this JD
        keywords: Keywords injected during tailoring
        cover_letter: Path to cover letter file (if any)

    Returns:
        The recorded version entry
    """
    versions = _load_versions()

    entry = {
        "id": len(versions) + 1,
        "company": company,
        "role": role,
        "resume_file": resume_file,
        "tailored": tailored,
        "keywords_used": keywords or [],
        "cover_letter": cover_letter,
        "sent_at": datetime.now().isoformat(),
    }

    versions.append(entry)
    _save_versions(versions)
    return entry


def get_version_history(company: str = None) -> list:
    """
    Get resume version history, optionally filtered by company.
    """
    versions = _load_versions()
    if company:
        return [v for v in versions if v["company"].lower() == company.lower()]
    return versions


def get_resume_for_company(company: str) -> dict | None:
    """Check what resume was sent to a specific company."""
    history = get_version_history(company)
    return history[-1] if history else None


def check_duplicate_company(company: str) -> bool:
    """Check if we've already sent a resume to this company."""
    return len(get_version_history(company)) > 0


def print_version_history():
    """Print formatted version history."""
    versions = _load_versions()
    if not versions:
        print("\n  No resume versions tracked yet.")
        return

    print(f"\n  RESUME VERSION HISTORY ({len(versions)} entries)")
    print("  " + "-" * 65)
    print(f"  {'#':>3}  {'Company':20}  {'Role':20}  {'Tailored':8}  {'Date':10}")
    print("  " + "-" * 65)

    for v in versions:
        tailored = "Yes" if v["tailored"] else "No"
        date = v["sent_at"][:10]
        print(f"  {v['id']:>3}  {v['company'][:20]:20}  {v['role'][:20]:20}  {tailored:8}  {date}")

    print()


if __name__ == "__main__":
    print_version_history()
