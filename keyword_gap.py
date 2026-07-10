#!/usr/bin/env python3
"""
ATS Keyword Gap Analysis — Compare your resume against a specific JD.

Shows exactly which keywords the ATS will look for, which ones you have,
and which ones are missing — grouped by priority.

Usage:
  python keyword_gap.py                    # Paste JD interactively
  python keyword_gap.py --jd-file jd.txt   # Read from file
  python keyword_gap.py --resume my.pdf    # Use specific resume PDF
"""

import os
import re
from collections import Counter

from config import TRENDING_SKILLS
from jd_tailorer import extract_jd_keywords, STOP_WORDS


def extract_resume_keywords(resume_text: str) -> set:
    """Extract meaningful keywords from resume text."""
    text_lower = resume_text.lower()
    words = re.findall(r'\b[a-z][a-z+#./-]{1,25}\b', text_lower)
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def analyze_keyword_gap(jd_text: str, resume_text: str) -> dict:
    """
    Perform keyword gap analysis between a JD and resume.

    Returns dict with:
      - matched: keywords found in both
      - missing_critical: important keywords missing from resume
      - missing_nice: nice-to-have keywords missing
      - jd_keywords: full JD keyword extraction
      - match_score: percentage match (0-100)
      - recommendations: list of actionable suggestions
    """
    jd_keywords = extract_jd_keywords(jd_text)
    resume_lower = resume_text.lower()
    resume_words = extract_resume_keywords(resume_text)

    # Technical skills — critical
    tech_matched = [s for s in jd_keywords["technical_skills"] if s in resume_lower]
    tech_missing = [s for s in jd_keywords["technical_skills"] if s not in resume_lower]

    # Compound terms — critical
    compound_matched = [t for t in jd_keywords["compound_matches"] if t in resume_lower]
    compound_missing = [t for t in jd_keywords["compound_matches"] if t not in resume_lower]

    # Soft skills — nice to have
    soft_matched = [s for s in jd_keywords["soft_skills"] if s in resume_lower]
    soft_missing = [s for s in jd_keywords["soft_skills"] if s not in resume_lower]

    # Domain keywords — important if present in JD
    domain_matched = [d for d in jd_keywords["domain_keywords"] if d in resume_lower]
    domain_missing = [d for d in jd_keywords["domain_keywords"] if d not in resume_lower]

    # Tools — critical
    tools_matched = [t for t in jd_keywords["tools"] if t in resume_lower]
    tools_missing = [t for t in jd_keywords["tools"] if t not in resume_lower]

    # High-frequency JD words not in resume (potential keywords to add)
    jd_top_words = jd_keywords["all_keywords"].most_common(30)
    missed_frequent = [
        (word, count) for word, count in jd_top_words
        if word not in resume_words
        and word not in STOP_WORDS
        and count >= 2
        and len(word) > 3
    ]

    # Calculate score
    all_critical = set(jd_keywords["technical_skills"]) | set(jd_keywords["compound_matches"])
    all_matched = set(tech_matched) | set(compound_matched)
    total = len(all_critical) if all_critical else 1
    match_score = round(len(all_matched) / total * 100)

    # Recommendations
    recommendations = []
    if tech_missing:
        top_missing = tech_missing[:5]
        recommendations.append(
            f"Add these technical skills to your resume: {', '.join(top_missing)}"
        )
    if compound_missing:
        top_compound = compound_missing[:3]
        recommendations.append(
            f"Include these terms explicitly: {', '.join(top_compound)}"
        )
    if domain_missing:
        recommendations.append(
            f"Add domain keywords: {', '.join(domain_missing)}"
        )
    if soft_missing:
        recommendations.append(
            f"Mention these soft skills: {', '.join(soft_missing[:3])}"
        )
    if match_score < 50:
        recommendations.append(
            "Your resume may not pass ATS filters. Add missing keywords before applying."
        )
    elif match_score < 70:
        recommendations.append(
            "Decent match but adding missing keywords will improve ATS ranking."
        )

    return {
        "matched": {
            "technical": tech_matched,
            "compound": compound_matched,
            "soft_skills": soft_matched,
            "domain": domain_matched,
            "tools": tools_matched,
        },
        "missing": {
            "technical": tech_missing,
            "compound": compound_missing,
            "soft_skills": soft_missing,
            "domain": domain_missing,
            "tools": tools_missing,
        },
        "missed_frequent_words": missed_frequent[:10],
        "jd_keywords": jd_keywords,
        "match_score": match_score,
        "recommendations": recommendations,
    }


def print_gap_report(gap: dict):
    """Print a formatted keyword gap report."""
    print(f"\n{'=' * 65}")
    print("  ATS KEYWORD GAP ANALYSIS")
    print(f"{'=' * 65}")

    score = gap["match_score"]
    filled = round(score / 5)
    bar = "█" * filled + "░" * (20 - filled)
    if score >= 70:
        verdict = "✓ STRONG"
    elif score >= 50:
        verdict = "~ DECENT"
    else:
        verdict = "✗ WEAK"
    print(f"\n  ATS MATCH: [{bar}] {score}%  {verdict}")

    # Matched
    print(f"\n  ✓ KEYWORDS YOU HAVE (ATS will find these)")
    print("  " + "-" * 50)
    matched = gap["matched"]
    all_matched = (
        matched["technical"] + matched["compound"] +
        matched["tools"] + matched["domain"]
    )
    if all_matched:
        for kw in sorted(set(all_matched)):
            print(f"    + {kw}")
    else:
        print("    (none)")

    # Missing critical
    missing = gap["missing"]
    critical_missing = missing["technical"] + missing["compound"] + missing["tools"]
    if critical_missing:
        print(f"\n  ✗ CRITICAL MISSING (add these to pass ATS)")
        print("  " + "-" * 50)
        for kw in sorted(set(critical_missing)):
            print(f"    - {kw}")

    # Missing nice-to-have
    nice_missing = missing["soft_skills"] + missing["domain"]
    if nice_missing:
        print(f"\n  ~ NICE TO HAVE (add if possible)")
        print("  " + "-" * 50)
        for kw in sorted(set(nice_missing)):
            print(f"    - {kw}")

    # Frequently used JD words not in resume
    if gap["missed_frequent_words"]:
        print(f"\n  📊 FREQUENTLY USED IN JD BUT NOT IN RESUME")
        print("  " + "-" * 50)
        for word, count in gap["missed_frequent_words"][:8]:
            print(f"    {word} (mentioned {count}x)")

    # Recommendations
    if gap["recommendations"]:
        print(f"\n  📋 RECOMMENDATIONS")
        print("  " + "-" * 50)
        for i, rec in enumerate(gap["recommendations"], 1):
            print(f"    {i}. {rec}")

    print(f"\n{'=' * 65}")


def run_gap_analysis(jd_text: str = None, jd_file: str = None,
                     resume_pdf: str = None):
    """Main entry point for keyword gap analysis."""
    # Load JD
    if jd_file and os.path.exists(jd_file):
        with open(jd_file) as f:
            jd_text = f.read()
    elif not jd_text:
        print("\n  Paste the Job Description (press Ctrl+D or Ctrl+Z when done):\n")
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        jd_text = "\n".join(lines)

    if not jd_text or len(jd_text.strip()) < 50:
        print("  JD text too short.")
        return None

    # Load resume text
    if resume_pdf and os.path.exists(resume_pdf):
        from resume_analyzer import extract_text_from_pdf
        resume_text, _ = extract_text_from_pdf(resume_pdf)
    else:
        # Build resume text from resume_data
        try:
            from resume_data import RESUME_DATA
        except ImportError:
            print("  Error: resume_data.py not found.")
            return None

        parts = [RESUME_DATA.get("summary", "")]
        for cat, skills in RESUME_DATA.get("skills", {}).items():
            parts.append(f"{cat}: {skills}")
        for job in RESUME_DATA.get("experience", []):
            parts.append(job.get("role", ""))
            parts.append(job.get("company", ""))
            parts.extend(job.get("bullets", []))
        for ach in RESUME_DATA.get("achievements", []):
            parts.append(ach)
        resume_text = "\n".join(parts)

    gap = analyze_keyword_gap(jd_text, resume_text)
    print_gap_report(gap)
    return gap


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ATS keyword gap analysis")
    parser.add_argument("--jd-file", help="JD text file")
    parser.add_argument("--resume", help="Resume PDF to analyze")
    args = parser.parse_args()
    run_gap_analysis(jd_file=args.jd_file, resume_pdf=args.resume)
