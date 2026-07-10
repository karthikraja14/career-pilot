#!/usr/bin/env python3
"""
Cover Letter Generator — Template-based cover letters tailored to each JD.

Generates professional cover letters by injecting matching skills,
domain keywords, and company-specific details from the JD.

Usage:
  python cover_letter.py --company "Google" --role "Lead Test Engineer"
  python cover_letter.py --company "Google" --role "Lead QA" --jd-file jd.txt
"""

import os
import re
import textwrap
from datetime import datetime


TEMPLATES = {
    "default": """\
{date}

Dear Hiring Manager,

I am writing to express my strong interest in the {role} position at {company}. \
With {experience_years} years of experience in {domain_phrase}, I am confident \
in my ability to make a meaningful contribution to your team.

{body_paragraph}

{skills_paragraph}

{closing_paragraph}

I would welcome the opportunity to discuss how my experience aligns with \
{company}'s goals. Thank you for considering my application.

Best regards,
{name}
{email}
{phone}""",

    "healthcare": """\
{date}

Dear Hiring Manager,

I am excited to apply for the {role} position at {company}. With {experience_years} \
years of experience in healthcare and MedTech quality engineering, including \
regulatory compliance (ISO 13485, IEC 62304, FDA), I bring a deep understanding \
of the quality standards your industry demands.

{body_paragraph}

{skills_paragraph}

{closing_paragraph}

I look forward to discussing how my healthcare domain expertise and technical \
leadership can benefit {company}. Thank you for your time and consideration.

Best regards,
{name}
{email}
{phone}""",
}


def _build_body_paragraph(resume_data: dict, jd_keywords: dict, company: str) -> str:
    """Build the main body paragraph highlighting relevant experience."""
    # Find most relevant experience bullets
    all_jd_terms = set(jd_keywords.get("technical_skills", []))
    all_jd_terms |= set(jd_keywords.get("compound_matches", []))

    best_bullets = []
    for job in resume_data.get("experience", []):
        for bullet in job.get("bullets", []):
            bullet_lower = bullet.lower()
            score = sum(1 for t in all_jd_terms if t in bullet_lower)
            if score > 0:
                best_bullets.append((score, bullet, job.get("company", "")))

    best_bullets.sort(key=lambda x: -x[0])

    if best_bullets:
        top = best_bullets[0]
        lines = [
            f"In my current role, I have {top[1][:1].lower()}{top[1][1:]}"
        ]
        if len(best_bullets) > 1:
            second = best_bullets[1]
            lines.append(
                f"Additionally, I {second[1][:1].lower()}{second[1][1:]}"
            )
        return " ".join(lines)

    return (
        f"Throughout my career, I have consistently delivered impactful "
        f"solutions that drive measurable results. I am eager to bring this "
        f"track record to {company}."
    )


def _build_skills_paragraph(resume_data: dict, jd_keywords: dict) -> str:
    """Build a paragraph highlighting matching skills."""
    matched_skills = []
    resume_text = ""
    if "skills" in resume_data:
        resume_text = " ".join(resume_data["skills"].values()).lower()

    for skill in jd_keywords.get("technical_skills", []):
        if skill in resume_text:
            matched_skills.append(skill)

    if len(matched_skills) >= 3:
        skills_str = ", ".join(matched_skills[:5])
        remaining = len(matched_skills) - 5
        extra = f" and {remaining} more relevant technologies" if remaining > 0 else ""
        return (
            f"My technical toolkit includes {skills_str}{extra}, "
            f"which directly align with the requirements outlined in your job description."
        )
    elif matched_skills:
        return (
            f"I bring hands-on experience with {', '.join(matched_skills)}, "
            f"complemented by a strong foundation in relevant processes and best practices."
        )
    else:
        return (
            "I bring a versatile technical skill set and a proven ability to "
            "quickly adapt to new tools and technologies as needed."
        )


def _build_closing(resume_data: dict, company: str) -> str:
    """Build the closing paragraph."""
    achievements = resume_data.get("achievements", [])
    if achievements:
        top_achievement = achievements[0]
        return (
            f"Among my key accomplishments: {top_achievement} "
            f"I am excited about the possibility of achieving similar results at {company}."
        )
    return (
        f"I am passionate about delivering excellence and excited about the "
        f"opportunity to contribute to {company}'s success."
    )


def generate_cover_letter(
    resume_data: dict,
    company: str,
    role: str,
    jd_keywords: dict = None,
    template: str = "default",
) -> str:
    """
    Generate a cover letter from resume data and JD keywords.

    Args:
        resume_data: Dict with name, contact, experience, skills, achievements
        company: Target company name
        role: Job title
        jd_keywords: Output from jd_tailorer.extract_jd_keywords() (optional)
        template: Template name ("default" or "healthcare")

    Returns:
        Formatted cover letter string
    """
    if jd_keywords is None:
        jd_keywords = {"technical_skills": [], "compound_matches": [],
                       "domain_keywords": [], "soft_skills": []}

    # Detect if healthcare domain
    domains = jd_keywords.get("domain_keywords", [])
    if any(d in domains for d in ["healthcare", "medtech", "pharmaceutical", "biotech", "clinical"]):
        template = "healthcare"

    contact = resume_data.get("contact", {})
    experience_years = "10"  # Default; could be extracted from resume data

    # Count years from experience entries
    exp_entries = resume_data.get("experience", [])
    if exp_entries:
        first_period = exp_entries[-1].get("period", "")
        year_match = re.search(r'(\d{4})', first_period)
        if year_match:
            start_year = int(year_match.group(1))
            experience_years = str(datetime.now().year - start_year)

    # Determine domain phrase
    if domains:
        domain_phrase = " and ".join(domains[:2])
    else:
        domain_phrase = "software engineering"

    body = _build_body_paragraph(resume_data, jd_keywords, company)
    skills = _build_skills_paragraph(resume_data, jd_keywords)
    closing = _build_closing(resume_data, company)

    tmpl = TEMPLATES.get(template, TEMPLATES["default"])

    letter = tmpl.format(
        date=datetime.now().strftime("%B %d, %Y"),
        role=role,
        company=company,
        experience_years=experience_years,
        domain_phrase=domain_phrase,
        body_paragraph=body,
        skills_paragraph=skills,
        closing_paragraph=closing,
        name=resume_data.get("name", ""),
        email=contact.get("email", ""),
        phone=contact.get("phone", ""),
    )

    # Wrap lines for readability
    wrapped_lines = []
    for line in letter.split("\n"):
        if len(line) > 90:
            wrapped_lines.extend(textwrap.wrap(line, width=88))
        else:
            wrapped_lines.append(line)

    return "\n".join(wrapped_lines)


def save_cover_letter(text: str, company: str, role: str, output_dir: str = "output") -> str:
    """Save cover letter to a text file."""
    os.makedirs(output_dir, exist_ok=True)
    safe_company = re.sub(r'[^\w\s-]', '', company).strip().replace(' ', '_')
    safe_role = re.sub(r'[^\w\s-]', '', role).strip().replace(' ', '_')
    filename = f"Cover_Letter_{safe_company}_{safe_role}.txt"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(text)
    return filepath


def run_cover_letter(company: str = None, role: str = None,
                     jd_text: str = None, jd_file: str = None):
    """Interactive cover letter generation."""
    try:
        from resume_data import RESUME_DATA
    except ImportError:
        print("  Error: resume_data.py not found.")
        return None

    if not company:
        company = input("  Company name: ").strip()
    if not role:
        role = input("  Role/Title: ").strip()
    if not company or not role:
        print("  Company and role are required.")
        return None

    jd_keywords = None
    if jd_file and os.path.exists(jd_file):
        with open(jd_file) as f:
            jd_text = f.read()

    if jd_text:
        from jd_tailorer import extract_jd_keywords
        jd_keywords = extract_jd_keywords(jd_text)

    letter = generate_cover_letter(RESUME_DATA, company, role, jd_keywords)
    print(f"\n{'=' * 60}")
    print(letter)
    print(f"{'=' * 60}")

    filepath = save_cover_letter(letter, company, role)
    print(f"\n  Saved to: {filepath}")
    return letter


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a cover letter")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--jd-file", help="Path to JD text file")
    args = parser.parse_args()
    run_cover_letter(args.company, args.role, jd_file=args.jd_file)
