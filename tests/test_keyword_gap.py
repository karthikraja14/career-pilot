"""Tests for keyword_gap.py — ATS keyword gap analysis."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from keyword_gap import analyze_keyword_gap, extract_resume_keywords
from tests.conftest import SAMPLE_RESUME_DATA, SAMPLE_JD, SAMPLE_JD_UNRELATED


def _resume_text_from_data(data: dict) -> str:
    """Build resume text from resume data dict."""
    parts = [data.get("summary", "")]
    for cat, skills in data.get("skills", {}).items():
        parts.append(f"{cat}: {skills}")
    for job in data.get("experience", []):
        parts.append(job.get("role", ""))
        parts.extend(job.get("bullets", []))
    return "\n".join(parts)


class TestExtractResumeKeywords:
    def test_extracts_meaningful_words(self):
        text = "Python Selenium Jenkins Docker automation testing"
        keywords = extract_resume_keywords(text)
        assert "python" in keywords
        assert "selenium" in keywords

    def test_filters_stop_words(self):
        text = "the and or with from this that"
        keywords = extract_resume_keywords(text)
        assert len(keywords) == 0

    def test_empty_text(self):
        keywords = extract_resume_keywords("")
        assert len(keywords) == 0

    def test_short_words_filtered(self):
        text = "I am a QA in IT"
        keywords = extract_resume_keywords(text)
        assert "i" not in keywords
        assert "am" not in keywords


class TestAnalyzeKeywordGap:
    def test_returns_required_keys(self):
        resume_text = _resume_text_from_data(SAMPLE_RESUME_DATA)
        gap = analyze_keyword_gap(SAMPLE_JD, resume_text)
        assert "matched" in gap
        assert "missing" in gap
        assert "match_score" in gap
        assert "recommendations" in gap

    def test_matching_jd_has_high_score(self):
        resume_text = _resume_text_from_data(SAMPLE_RESUME_DATA)
        gap = analyze_keyword_gap(SAMPLE_JD, resume_text)
        # Our sample resume is built for QA roles, should match reasonably
        assert gap["match_score"] >= 30

    def test_unrelated_jd_has_low_score(self):
        resume_text = _resume_text_from_data(SAMPLE_RESUME_DATA)
        gap = analyze_keyword_gap(SAMPLE_JD_UNRELATED, resume_text)
        # Marketing JD should have very few matched technical skills
        matched_tech = gap["matched"]["technical"]
        # No QA/test skills should match in a marketing JD
        assert "selenium" not in matched_tech
        assert "playwright" not in matched_tech

    def test_matched_skills_found(self):
        resume_text = _resume_text_from_data(SAMPLE_RESUME_DATA)
        gap = analyze_keyword_gap(SAMPLE_JD, resume_text)
        all_matched = (gap["matched"]["technical"] +
                       gap["matched"]["compound"] +
                       gap["matched"]["tools"])
        assert len(all_matched) > 0

    def test_missing_skills_identified(self):
        # Use a JD with skills not in our resume
        jd = "Requires Cypress, Gatling, k6, Terraform, Ansible experience"
        resume_text = "I know Python and Selenium"
        gap = analyze_keyword_gap(jd, resume_text)
        assert len(gap["missing"]["technical"]) > 0

    def test_recommendations_generated(self):
        resume_text = "I know Python"
        gap = analyze_keyword_gap(SAMPLE_JD, resume_text)
        assert len(gap["recommendations"]) > 0

    def test_score_is_percentage(self):
        resume_text = _resume_text_from_data(SAMPLE_RESUME_DATA)
        gap = analyze_keyword_gap(SAMPLE_JD, resume_text)
        assert 0 <= gap["match_score"] <= 100

    def test_empty_resume_zero_match(self):
        gap = analyze_keyword_gap(SAMPLE_JD, "")
        assert gap["match_score"] == 0 or len(gap["matched"]["technical"]) == 0

    def test_perfect_match(self):
        # JD that only asks for skills already in resume
        jd = "Looking for someone with Python, Selenium, Jenkins, Docker, Azure"
        resume_text = "Expert in Python, Selenium, Jenkins, Docker, Azure DevOps, Azure Cloud"
        gap = analyze_keyword_gap(jd, resume_text)
        assert gap["match_score"] >= 60
