"""Tests for resume_analyzer.py — Resume scoring engine."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from resume.analyzer import (
    extract_contact_info, detect_sections,
    score_completeness, score_ats_compatibility,
    score_impact_statements, score_skills_relevance,
    score_structure,
)


SAMPLE_RESUME_TEXT = """
Contact: test@example.com | +91 9999999999 | linkedin.com/in/test-user | github.com/testuser

PROFESSIONAL SUMMARY
Lead Test Engineer with 10 years of experience in test automation and quality engineering.
Built Selenium and Playwright frameworks, led teams of 20+ engineers.

WORK EXPERIENCE
Mar 2023 - Present
Lead Test Engineer at Acme Corp
- Led test framework redesign reducing execution time by 60%
- Automated 200+ test cases using Python and Selenium
- Managed 15 engineers across 3 teams
- Reduced defect leakage by 35% through shift-left testing

Jan 2020 - Feb 2023
Senior Test Engineer at Beta Inc
- Designed BDD test framework with Cucumber
- Implemented CI/CD pipeline with Jenkins and Docker

EDUCATION
B.Tech Computer Science, 2014 - Test University

SKILLS
Python, Java, Selenium, Playwright, Jenkins, Docker, Kubernetes, Azure, AWS, Jira

CERTIFICATIONS
ISTQB Foundation Level

ACHIEVEMENTS
- Increased test coverage from 40% to 85%
- Reduced CI pipeline time by 40%
"""


class TestExtractContactInfo:
    def test_extracts_email(self):
        info = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert info.get("email") == "test@example.com"

    def test_extracts_phone(self):
        info = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert "phone" in info

    def test_extracts_linkedin(self):
        info = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert "linkedin" in info

    def test_extracts_github(self):
        info = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert "github" in info

    def test_empty_text(self):
        info = extract_contact_info("")
        assert len(info) == 0

    def test_no_contact_info(self):
        info = extract_contact_info("Just a bunch of random text without contact details.")
        assert "email" not in info


class TestDetectSections:
    def test_detects_experience(self):
        sections = detect_sections(SAMPLE_RESUME_TEXT)
        assert sections.get("experience") is True

    def test_detects_education(self):
        sections = detect_sections(SAMPLE_RESUME_TEXT)
        assert sections.get("education") is True

    def test_detects_skills(self):
        sections = detect_sections(SAMPLE_RESUME_TEXT)
        assert sections.get("skills") is True

    def test_detects_certifications(self):
        sections = detect_sections(SAMPLE_RESUME_TEXT)
        assert sections.get("certifications") is True

    def test_empty_text(self):
        sections = detect_sections("")
        assert all(v is False for v in sections.values())


class TestScoreCompleteness:
    def test_full_resume_high_score(self):
        sections = {s: True for s in ["contact", "summary", "experience", "education",
                                       "skills", "projects", "certifications", "achievements"]}
        score, suggestions = score_completeness(sections)
        assert score == 100.0
        assert len(suggestions) == 0

    def test_missing_sections_lower_score(self):
        sections = {"contact": True, "summary": True, "experience": False,
                     "education": False, "skills": False}
        score, suggestions = score_completeness(sections)
        assert score < 100
        assert len(suggestions) > 0

    def test_empty_sections_zero(self):
        sections = {}
        score, suggestions = score_completeness(sections)
        assert score == 0
        assert len(suggestions) > 0


class TestScoreAtsCompatibility:
    def test_complete_contact_high_score(self):
        contact = {"email": "x@y.com", "phone": "123", "linkedin": "url", "github": "url"}
        score, _ = score_ats_compatibility(SAMPLE_RESUME_TEXT, contact)
        assert score >= 70

    def test_missing_email_deduction(self):
        contact = {"phone": "123"}
        score_no_email, suggestions = score_ats_compatibility(SAMPLE_RESUME_TEXT, contact)
        contact_full = {"email": "x@y.com", "phone": "123", "linkedin": "url", "github": "url"}
        score_full, _ = score_ats_compatibility(SAMPLE_RESUME_TEXT, contact_full)
        assert score_no_email < score_full

    def test_short_resume_penalty(self):
        short_text = "Hello world short resume"
        score, suggestions = score_ats_compatibility(short_text, {"email": "x@y.com"})
        assert score < 100
        assert any("short" in s.lower() for s in suggestions)


class TestScoreImpactStatements:
    def test_quantified_achievements_score(self):
        score, _ = score_impact_statements(SAMPLE_RESUME_TEXT)
        assert score > 0

    def test_no_achievements_low_score(self):
        bland = "I worked at a company. I was involved in testing. I helped the team."
        score, suggestions = score_impact_statements(bland)
        assert score < 50
        assert len(suggestions) > 0

    def test_weak_phrases_flagged(self):
        text = "I was responsible for testing. I was involved in automation."
        _, suggestions = score_impact_statements(text)
        weak_flags = [s for s in suggestions if "weak" in s.lower() or "REMOVE" in s]
        assert len(weak_flags) > 0


class TestScoreSkillsRelevance:
    def test_relevant_skills_score(self):
        text = "python selenium jenkins docker kubernetes playwright cypress api testing jira git agile scrum"
        score, _ = score_skills_relevance(text)
        assert score > 10

    def test_no_skills_low_score(self):
        text = "I have experience in management and communication."
        score, suggestions = score_skills_relevance(text)
        assert score < 30
        assert len(suggestions) > 0


class TestScoreStructure:
    def test_good_structure(self):
        score, _ = score_structure(SAMPLE_RESUME_TEXT, page_count=2)
        assert score >= 60

    def test_too_many_pages(self):
        score, suggestions = score_structure(SAMPLE_RESUME_TEXT, page_count=5)
        assert score < 100
        assert any("page" in s.lower() for s in suggestions)

    def test_very_short(self):
        score, suggestions = score_structure("hello", page_count=1)
        assert score < 100
        assert any("sparse" in s.lower() or "short" in s.lower() for s in suggestions)
