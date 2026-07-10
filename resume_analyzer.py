#!/usr/bin/env python3
"""
Resume Analyzer & Scorer
Extracts text from PDF resume, scores it across 5 dimensions,
and generates actionable improvement suggestions.
"""

import re
import os
import json
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

from config import (
    TRENDING_SKILLS, SCORING_WEIGHTS, GRADE_THRESHOLDS,
    EXPECTED_SECTIONS, ACTION_VERBS, WEAK_PHRASES,
)


# â”€â”€â”€ PDF Text Extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def extract_text_from_pdf(pdf_path: str) -> tuple[str, int]:
    """Extract text from a PDF file. Returns (text, page_count)."""
    if pdfplumber:
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages), len(pdf.pages)
    elif PdfReader:
        reader = PdfReader(pdf_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages), len(reader.pages)
    else:
        raise ImportError(
            "Install a PDF library: pip install pdfplumber  OR  pip install PyPDF2"
        )


# â”€â”€â”€ Contact Info Extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def extract_contact_info(text: str) -> dict:
    """Extract email, phone, LinkedIn, GitHub from resume text."""
    info = {}

    email = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    if email:
        info["email"] = email[0]

    phone = re.findall(r'[\+]?[\d\s\(\)\-]{10,15}', text)
    if phone:
        info["phone"] = phone[0].strip()

    linkedin = re.findall(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
    if linkedin:
        info["linkedin"] = linkedin[0]

    github = re.findall(r'github\.com/[\w-]+', text, re.IGNORECASE)
    if github:
        info["github"] = github[0]

    return info


# â”€â”€â”€ Section Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SECTION_PATTERNS = {
    "contact": r'(?i)(contact|email|phone|address)',
    "summary": r'(?i)(summary|objective|profile|about\s*me|professional\s*summary)',
    "experience": r'(?i)(experience|work\s*history|employment|professional\s*experience)',
    "education": r'(?i)(education|academic|qualification|degree)',
    "skills": r'(?i)(skills|technical\s*skills|competencies|technologies)',
    "projects": r'(?i)(projects|key\s*projects|notable\s*projects)',
    "certifications": r'(?i)(certifications?|certified|accreditation)',
    "achievements": r'(?i)(achievements?|awards?|honors?|recognition)',
    "publications": r'(?i)(publications?|papers?|research)',
}


def detect_sections(text: str) -> dict[str, bool]:
    """Detect which resume sections are present."""
    return {
        section: bool(re.search(pattern, text))
        for section, pattern in SECTION_PATTERNS.items()
    }


# â”€â”€â”€ Scoring Functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def score_completeness(sections: dict[str, bool]) -> tuple[float, list[str]]:
    """Score based on presence of expected sections (0-100)."""
    suggestions = []
    found = sum(1 for s in EXPECTED_SECTIONS if sections.get(s, False))
    total = len(EXPECTED_SECTIONS)
    score = (found / total) * 100

    for section in EXPECTED_SECTIONS:
        if not sections.get(section, False):
            suggestions.append(
                f"RECOMMENDED: Add a '{section.upper()}' section to strengthen your resume."
            )

    return round(score, 1), suggestions


def score_ats_compatibility(text: str, contact: dict) -> tuple[float, list[str]]:
    """Score ATS-friendliness (0-100)."""
    score = 100.0
    suggestions = []

    # Check for contact info completeness
    if "email" not in contact:
        score -= 20
        suggestions.append("Add an email address â€” essential for ATS parsing.")
    if "phone" not in contact:
        score -= 10
        suggestions.append("Add a phone number â€” most ATS require it.")
    if "linkedin" not in contact:
        score -= 10
        suggestions.append(
            "Add your LinkedIn profile URL â€” most ATS systems and recruiters look for it."
        )
    if "github" not in contact:
        score -= 5
        suggestions.append("Add a GitHub or portfolio link to showcase your work.")

    # Check for common ATS issues
    text_lower = text.lower()
    if len(text.split()) < 300:
        score -= 10
        suggestions.append(
            "Resume seems too short. Aim for 400-600 words for a 7+ year experience resume."
        )
    if len(text.split()) > 1000:
        score -= 5
        suggestions.append("Resume may be too long. Keep it concise â€” 2 pages max.")

    # Check for date formats (ATS prefers consistent dates)
    dates = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b', text)
    if len(dates) < 2:
        score -= 5
        suggestions.append("Use consistent date formats (e.g., 'Jan 2020 - Present') for each role.")

    # Check for standard section headers
    standard_headers = ["experience", "education", "skills"]
    for header in standard_headers:
        if not re.search(rf'(?i)\b{header}\b', text):
            score -= 10
            suggestions.append(
                f"Use standard section header '{header.title()}' â€” ATS may miss non-standard headers."
            )

    return max(round(score, 1), 0), suggestions


def score_impact_statements(text: str) -> tuple[float, list[str]]:
    """Score quality of impact/achievement statements (0-100)."""
    suggestions = []
    text_lower = text.lower()
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Count quantified achievements (numbers + context)
    quantified = re.findall(
        r'\b\d+[%+]?\b.*?(?:reduc|improv|increas|sav|deliver|automat|optimiz|speed|faster)',
        text_lower,
    )
    quant_count = len(quantified)

    # Count action verbs at start of lines
    action_verb_count = 0
    for line in lines:
        first_word = line.split()[0].lower().rstrip('.,;:') if line.split() else ""
        if first_word in ACTION_VERBS:
            action_verb_count += 1

    # Check for weak phrases
    weak_found = [p for p in WEAK_PHRASES if p in text_lower]

    # Calculate score
    score = 0.0
    score += min(quant_count * 15, 40)       # Up to 40 points for quantified achievements
    score += min(action_verb_count * 5, 30)   # Up to 30 points for action verbs
    score += max(30 - len(weak_found) * 10, 0)  # Lose points for weak phrases

    # Suggestions
    if quant_count < 3:
        suggestions.append(
            f"Add MORE quantified achievements (found {quant_count}, need at least 3). "
            "Example: 'Reduced defect leakage by 40%' or 'Automated 200+ test cases'."
        )
    if action_verb_count < 5:
        suggestions.append(
            f"Use MORE action verbs (found {action_verb_count}). Start bullets with: "
            + ", ".join(ACTION_VERBS[:10]) + "..."
        )
    for phrase in weak_found:
        suggestions.append(
            f"REMOVE weak phrase: '{phrase}'. Replace with strong action verbs."
        )

    # Check experience entries for detail
    exp_blocks = re.findall(
        r'(?i)(?:at|@|â€“|-|,)\s*([A-Z][\w\s&]+?)(?:\n|,|\||â€“|-)',
        text,
    )
    for company in exp_blocks[:5]:
        company = company.strip()
        # Count lines mentioning this company context
        company_context = [l for l in lines if company.lower() in l.lower()]
        if len(company_context) < 3:
            suggestions.append(f"Add more detail to your role at '{company}'.")

    return round(min(score, 100), 1), suggestions


def score_skills_relevance(text: str) -> tuple[float, list[str]]:
    """Score how well skills match current market demand (0-100)."""
    suggestions = []
    text_lower = text.lower()

    total_categories = len(TRENDING_SKILLS)
    category_scores = {}

    for category, skills in TRENDING_SKILLS.items():
        found = [s for s in skills if s.lower() in text_lower]
        coverage = len(found) / len(skills) if skills else 0
        category_scores[category] = {
            "found": found,
            "missing": [s for s in skills if s.lower() not in text_lower],
            "coverage": coverage,
        }

        if coverage < 0.3:
            top_missing = [s for s in skills if s.lower() not in text_lower][:4]
            suggestions.append(
                f"Strengthen '{category}' skills â€” consider adding: {', '.join(top_missing)}."
            )

    # Overall score = weighted average of category coverage
    avg_coverage = sum(c["coverage"] for c in category_scores.values()) / total_categories
    score = avg_coverage * 100

    # Special flag for AI/ML
    ai_skills = category_scores.get("AI/ML", {})
    if ai_skills.get("coverage", 0) < 0.2:
        suggestions.append(
            "HIGH PRIORITY: Add AI/ML testing skills (AI testing, LLM, Generative AI) "
            "â€” these are the most in-demand skills for 2025-2026."
        )

    return round(score, 1), suggestions


def score_structure(text: str, page_count: int) -> tuple[float, list[str]]:
    """Score resume structure and formatting (0-100)."""
    suggestions = []
    score = 100.0

    # Page count check
    if page_count > 3:
        score -= 20
        suggestions.append("Reduce to 2 pages â€” recruiters spend ~7 seconds on initial scan.")
    elif page_count > 2:
        score -= 10
        suggestions.append("Consider condensing to 2 pages for better readability.")

    # Check for bullet points
    bullets = len(re.findall(r'[â€¢â—â—‹â– â–ªâ€“\-]\s', text))
    if bullets < 5:
        score -= 15
        suggestions.append("Use more bullet points to improve readability and ATS parsing.")

    # Check for consistent formatting (lines of similar length)
    lines = [l for l in text.split('\n') if l.strip()]
    if lines:
        avg_len = sum(len(l) for l in lines) / len(lines)
        if avg_len < 20:
            score -= 10
            suggestions.append("Lines seem too short â€” expand on your responsibilities and achievements.")

    # Check overall word count relative to experience
    word_count = len(text.split())
    if word_count < 200:
        score -= 20
        suggestions.append("Resume is very sparse. Add more detail about your experience.")

    return max(round(score, 1), 0), suggestions


# â”€â”€â”€ Overall Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def analyze_resume(pdf_path: str) -> dict:
    """Run full resume analysis and return structured results."""
    text, page_count = extract_text_from_pdf(pdf_path)
    word_count = len(text.split())
    contact = extract_contact_info(text)
    sections = detect_sections(text)

    # Score each dimension
    completeness_score, completeness_suggestions = score_completeness(sections)
    ats_score, ats_suggestions = score_ats_compatibility(text, contact)
    impact_score, impact_suggestions = score_impact_statements(text)
    skills_score, skills_suggestions = score_skills_relevance(text)
    structure_score, structure_suggestions = score_structure(text, page_count)

    # Weighted overall score
    scores = {
        "completeness": completeness_score,
        "ats_compatibility": ats_score,
        "impact_statements": impact_score,
        "skills_relevance": skills_score,
        "structure": structure_score,
    }

    overall = sum(
        scores[dim] * SCORING_WEIGHTS[dim] for dim in scores
    )

    # Grade
    grade = "F"
    for g, threshold in sorted(GRADE_THRESHOLDS.items(), key=lambda x: -x[1]):
        if overall >= threshold:
            grade = g
            break

    # Priority fixes (lowest scoring areas first)
    all_suggestions = {
        "completeness": completeness_suggestions,
        "ats_compatibility": ats_suggestions,
        "impact_statements": impact_suggestions,
        "skills_relevance": skills_suggestions,
        "structure": structure_suggestions,
    }

    sorted_dims = sorted(scores.items(), key=lambda x: x[1])
    priority_fixes = []
    for dim, _ in sorted_dims:
        priority_fixes.extend(all_suggestions[dim][:2])
    priority_fixes = priority_fixes[:6]

    return {
        "file": os.path.basename(pdf_path),
        "analyzed_at": datetime.now().isoformat(),
        "page_count": page_count,
        "word_count": word_count,
        "contact_info": contact,
        "sections_found": sections,
        "experience_entries": len(re.findall(
            r'(?i)(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}',
            text,
        )) // 2 or 1,
        "scores": scores,
        "overall_score": round(overall, 1),
        "grade": grade,
        "suggestions": all_suggestions,
        "priority_fixes": priority_fixes,
    }


# â”€â”€â”€ Report Display â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def print_analysis_report(result: dict):
    """Print a formatted analysis report to the console."""
    print("\n" + "=" * 60)
    print("  RESUME ANALYSIS REPORT")
    print("=" * 60)
    print(f"  File:       {result['file']}")
    print(f"  Pages:      {result['page_count']}")
    print(f"  Words:      {result['word_count']}")
    print(f"  Analyzed:   {result['analyzed_at'][:19]}")
    print()

    # Contact info
    print("  CONTACT INFO")
    print("  " + "-" * 40)
    for key, val in result["contact_info"].items():
        print(f"    {key:12s}: {val}")
    print()

    # Scores
    print("  DIMENSION SCORES")
    print("  " + "-" * 40)
    bar_width = 20
    for dim, score in result["scores"].items():
        filled = int(score / 100 * bar_width)
        bar = "â–ˆ" * filled + "â–‘" * (bar_width - filled)
        label = dim.replace("_", " ").title()
        color_mark = "âœ“" if score >= 70 else "âœ—" if score < 50 else "~"
        print(f"    {color_mark} {label:22s} {bar} {score:5.1f}%")

    print()
    overall = result["overall_score"]
    grade = result["grade"]
    filled = int(overall / 100 * bar_width)
    bar = "â–ˆ" * filled + "â–‘" * (bar_width - filled)
    print(f"    OVERALL SCORE        {bar} {overall:5.1f}%  (Grade: {grade})")
    print()

    # Sections
    print("  SECTIONS DETECTED")
    print("  " + "-" * 40)
    for section, found in result["sections_found"].items():
        status = "âœ“ Found" if found else "âœ— Missing"
        print(f"    {section:18s} {status}")
    print()

    # Priority fixes
    print("  TOP PRIORITY FIXES")
    print("  " + "-" * 40)
    for i, fix in enumerate(result["priority_fixes"], 1):
        print(f"    {i}. {fix}")
    print()

    # Detailed suggestions
    print("  DETAILED SUGGESTIONS")
    print("  " + "-" * 40)
    for dim, suggestions in result["suggestions"].items():
        if suggestions:
            label = dim.replace("_", " ").title()
            print(f"\n    [{label}]")
            for s in suggestions:
                print(f"      â†’ {s}")

    print("\n" + "=" * 60)


def save_report(result: dict, output_dir: str = "reports") -> str:
    """Save analysis report as JSON. Returns the output path."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_analysis_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump(result, f, indent=2)
    return filepath


# â”€â”€â”€ Entry Point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_analysis(pdf_path: str = None) -> dict:
    """Run resume analysis â€” finds PDF automatically if not specified."""
    if not pdf_path:
        # Find PDF files in current directory
        pdfs = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
        if not pdfs:
            print("No PDF resume found in current directory.")
            print("Usage: python resume_analyzer.py <resume.pdf>")
            return {}
        pdf_path = pdfs[0]
        print(f"Found resume: {pdf_path}")

    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return {}

    result = analyze_resume(pdf_path)
    print_analysis_report(result)

    report_path = save_report(result)
    print(f"\n  Report saved: {report_path}")

    return result


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else None
    run_analysis(pdf)
