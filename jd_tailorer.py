#!/usr/bin/env python3
"""
JD Tailorer — Customize your resume for a specific job description.

Extracts keywords from a JD, highlights matching skills,
reweights skill sections, and generates a tailored PDF.

Usage:
  python jd_tailorer.py                    # Paste JD interactively
  python jd_tailorer.py --jd-file jd.txt   # Read JD from file
"""

import re
import os
import sys
from collections import Counter

from config import TRENDING_SKILLS


# ─── Keyword Extraction ──────────────────────────────────────────────────────

# Common filler words to ignore when extracting JD keywords
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "about", "up", "also", "well", "back", "even", "still", "new", "way",
    "our", "we", "you", "your", "their", "its", "this", "that", "these",
    "those", "it", "he", "she", "they", "i", "me", "my", "work", "role",
    "team", "company", "experience", "years", "strong", "ability",
    "looking", "join", "including", "within", "across", "ensure",
    "required", "preferred", "plus", "bonus", "etc", "eg", "ie",
    "working", "good", "great", "excellent", "skills", "knowledge",
    "understanding", "responsibilities", "requirements", "qualifications",
    "what", "who", "whom", "which",
}

# Known multi-word tech terms to detect as single units
COMPOUND_TERMS = [
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "data science", "data engineering", "data pipeline",
    "ci/cd", "ci cd", "continuous integration", "continuous delivery",
    "continuous deployment", "test automation", "test framework",
    "api testing", "performance testing", "load testing", "stress testing",
    "security testing", "mobile testing", "regression testing",
    "integration testing", "unit testing", "end to end", "e2e testing",
    "shift left", "shift-left", "quality assurance", "quality engineering",
    "azure devops", "github actions", "gitlab ci",
    "rest assured", "robot framework", "test cases", "test plan",
    "test strategy", "design patterns", "microservices", "web services",
    "cross functional", "cross-functional", "stakeholder management",
    "root cause analysis", "risk based", "risk-based",
    "medical device", "health tech", "med tech",
    "iso 13485", "iec 62304", "fda", "hipaa",
    "cosmos db", "azure cloud", "shell scripting",
]


def extract_jd_keywords(jd_text: str) -> dict:
    """
    Extract and categorize keywords from a job description.

    Returns dict with:
      - technical_skills: list of tech skills found
      - soft_skills: list of soft skills found
      - tools: list of tools/platforms found
      - domain_keywords: list of domain-specific terms
      - all_keywords: Counter of all meaningful words
      - compound_matches: multi-word terms found
    """
    jd_lower = jd_text.lower()

    # 1. Find compound terms first
    compound_matches = []
    for term in COMPOUND_TERMS:
        if term in jd_lower:
            compound_matches.append(term)

    # 2. Find trending skills mentioned in JD
    tech_from_config = []
    for category, skills in TRENDING_SKILLS.items():
        for skill in skills:
            if skill.lower() in jd_lower:
                tech_from_config.append(skill.lower())

    # 3. Extract all meaningful single words
    words = re.findall(r'\b[a-z][a-z+#./-]{1,25}\b', jd_lower)
    word_counts = Counter(w for w in words if w not in STOP_WORDS and len(w) > 2)

    # 4. Categorize
    soft_skill_markers = [
        "leadership", "communication", "collaboration", "mentoring",
        "problem-solving", "analytical", "critical thinking", "teamwork",
        "adaptability", "ownership", "initiative", "proactive",
        "attention to detail", "time management", "interpersonal",
    ]
    soft_skills = [s for s in soft_skill_markers if s in jd_lower]

    # 5. Separate domain keywords
    domain_markers = [
        "healthcare", "medtech", "fintech", "saas", "enterprise",
        "e-commerce", "banking", "insurance", "telecom", "retail",
        "automotive", "aerospace", "defense", "education", "gaming",
        "pharmaceutical", "biotech", "clinical", "regulatory",
    ]
    domain_keywords = [d for d in domain_markers if d in jd_lower]

    return {
        "technical_skills": list(set(tech_from_config)),
        "soft_skills": soft_skills,
        "tools": [t for t in tech_from_config if t in [
            "jira", "confluence", "git", "bitbucket", "sonarqube",
            "allure", "browserstack", "sauce labs", "testrail",
            "jenkins", "docker", "kubernetes", "terraform", "ansible",
        ]],
        "domain_keywords": domain_keywords,
        "all_keywords": word_counts,
        "compound_matches": compound_matches,
    }


def tailor_resume_data(resume_data: dict, jd_keywords: dict) -> dict:
    """
    Create a tailored copy of resume data optimized for a specific JD.

    - Reorders skills to put JD-matching ones first
    - Adds a 'Tailored For' note
    - Highlights matching experience bullets
    """
    import copy
    tailored = copy.deepcopy(resume_data)

    jd_skills = set(jd_keywords["technical_skills"])
    jd_compounds = set(jd_keywords["compound_matches"])
    all_jd_terms = jd_skills | jd_compounds

    # Reorder skills: put matching categories first, and within each
    # category move matching skills to the front
    if "skills" in tailored:
        reordered_skills = {}
        matched_cats = []
        unmatched_cats = []

        for category, skills_text in tailored["skills"].items():
            skills_lower = skills_text.lower()
            match_count = sum(1 for s in all_jd_terms if s in skills_lower)
            if match_count > 0:
                matched_cats.append((category, skills_text, match_count))
            else:
                unmatched_cats.append((category, skills_text))

        # Sort matched categories by match count (highest first)
        matched_cats.sort(key=lambda x: -x[2])

        for cat, text, _ in matched_cats:
            reordered_skills[cat] = text
        for cat, text in unmatched_cats:
            reordered_skills[cat] = text

        tailored["skills"] = reordered_skills

    # Score experience bullets — mark which ones are most relevant
    if "experience" in tailored:
        for job in tailored["experience"]:
            scored_bullets = []
            for bullet in job["bullets"]:
                bullet_lower = bullet.lower()
                relevance = sum(1 for t in all_jd_terms if t in bullet_lower)
                scored_bullets.append((relevance, bullet))
            # Sort bullets: most relevant first
            scored_bullets.sort(key=lambda x: -x[0])
            job["bullets"] = [b for _, b in scored_bullets]

    return tailored


def generate_match_report(resume_data: dict, jd_keywords: dict) -> str:
    """Generate a text report showing how well the resume matches the JD."""
    lines = []
    lines.append("=" * 60)
    lines.append("  JD MATCH REPORT")
    lines.append("=" * 60)

    # Skills match
    jd_skills = set(jd_keywords["technical_skills"])
    resume_text = ""
    if "skills" in resume_data:
        resume_text = " ".join(resume_data["skills"].values()).lower()
    if "summary" in resume_data:
        resume_text += " " + resume_data["summary"].lower()

    matched = [s for s in jd_skills if s in resume_text]
    missing = [s for s in jd_skills if s not in resume_text]

    lines.append(f"\n  SKILLS MATCH: {len(matched)}/{len(jd_skills)}")
    lines.append("  " + "-" * 40)

    if matched:
        lines.append(f"  ✓ IN YOUR RESUME ({len(matched)}):")
        for s in sorted(matched):
            lines.append(f"    + {s}")

    if missing:
        lines.append(f"\n  ✗ MISSING FROM RESUME ({len(missing)}):")
        for s in sorted(missing):
            lines.append(f"    - {s}")

    # Domain match
    if jd_keywords["domain_keywords"]:
        lines.append(f"\n  DOMAIN KEYWORDS:")
        lines.append("  " + "-" * 40)
        for d in jd_keywords["domain_keywords"]:
            status = "✓" if d in resume_text else "✗"
            lines.append(f"    {status} {d}")

    # Soft skills
    if jd_keywords["soft_skills"]:
        lines.append(f"\n  SOFT SKILLS MENTIONED:")
        lines.append("  " + "-" * 40)
        for s in jd_keywords["soft_skills"]:
            status = "✓" if s in resume_text else "✗"
            lines.append(f"    {status} {s}")

    # Score
    total_terms = len(jd_skills) + len(jd_keywords.get("compound_matches", []))
    if total_terms > 0:
        all_terms = jd_skills | set(jd_keywords.get("compound_matches", []))
        all_matched = sum(1 for t in all_terms if t in resume_text)
        score = round(all_matched / len(all_terms) * 100)
        lines.append(f"\n  OVERALL MATCH SCORE: {score}%")
        if score >= 70:
            lines.append("  ✓ Strong match — apply with confidence")
        elif score >= 50:
            lines.append("  ~ Decent match — consider adding missing skills")
        else:
            lines.append("  ✗ Weak match — tailor your resume before applying")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def run_tailorer(jd_text: str = None, jd_file: str = None, output_path: str = None):
    """
    Main entry point for JD tailoring.
    Returns (tailored_data, match_report, jd_keywords).
    """
    # Load JD
    if jd_file and os.path.exists(jd_file):
        with open(jd_file) as f:
            jd_text = f.read()
    elif not jd_text:
        print("\n  Paste the Job Description below (press Ctrl+D or Ctrl+Z when done):\n")
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        jd_text = "\n".join(lines)

    if not jd_text or len(jd_text.strip()) < 50:
        print("  JD text too short. Please provide a complete job description.")
        return None, None, None

    # Load resume data
    try:
        from resume_data import RESUME_DATA
    except ImportError:
        print("  Error: resume_data.py not found.")
        print("  Copy resume_data.example.py → resume_data.py and fill in your details.")
        return None, None, None

    # Extract keywords
    jd_keywords = extract_jd_keywords(jd_text)

    # Generate match report
    report = generate_match_report(RESUME_DATA, jd_keywords)
    print(report)

    # Tailor resume
    tailored = tailor_resume_data(RESUME_DATA, jd_keywords)

    # Generate PDF if resume_builder is available
    if output_path:
        try:
            from resume_builder import build_resume
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            build_resume(tailored, output_path)
            print(f"\n  Tailored resume saved: {output_path}")
        except ImportError:
            print("  Could not generate PDF (fpdf2 not installed).")

    return tailored, report, jd_keywords


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tailor resume to a JD")
    parser.add_argument("--jd-file", help="Path to JD text file")
    parser.add_argument("--output", default="output/Tailored_Resume.pdf",
                        help="Output PDF path")
    args = parser.parse_args()
    run_tailorer(jd_file=args.jd_file, output_path=args.output)
