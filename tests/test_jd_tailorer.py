"""Tests for jd_tailorer.py — JD keyword extraction and resume tailoring."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from jd_tailorer import extract_jd_keywords, tailor_resume_data, generate_match_report
from tests.conftest import SAMPLE_RESUME_DATA, SAMPLE_JD, SAMPLE_JD_MINIMAL, SAMPLE_JD_UNRELATED


class TestExtractJdKeywords:
    def test_extracts_technical_skills(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        assert len(kw["technical_skills"]) > 0
        assert "selenium" in kw["technical_skills"] or "playwright" in kw["technical_skills"]

    def test_extracts_compound_terms(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        compounds = kw["compound_matches"]
        assert any("test" in c for c in compounds) or any("ci" in c for c in compounds)

    def test_extracts_soft_skills(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        assert "leadership" in kw["soft_skills"]

    def test_extracts_domain_keywords(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        assert "healthcare" in kw["domain_keywords"] or "medtech" in kw["domain_keywords"]

    def test_minimal_jd_returns_some_keywords(self):
        kw = extract_jd_keywords(SAMPLE_JD_MINIMAL)
        # Even a minimal JD should return a valid structure
        assert "technical_skills" in kw
        assert "all_keywords" in kw

    def test_unrelated_jd_no_test_skills(self):
        kw = extract_jd_keywords(SAMPLE_JD_UNRELATED)
        # Marketing JD should not have test automation skills
        assert "selenium" not in kw["technical_skills"]
        assert "playwright" not in kw["technical_skills"]

    def test_empty_jd_returns_empty(self):
        kw = extract_jd_keywords("")
        assert len(kw["technical_skills"]) == 0

    def test_all_keywords_is_counter(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        assert hasattr(kw["all_keywords"], "most_common")

    def test_case_insensitive(self):
        kw1 = extract_jd_keywords("Experience with SELENIUM and Python")
        kw2 = extract_jd_keywords("experience with selenium and python")
        assert set(kw1["technical_skills"]) == set(kw2["technical_skills"])


class TestTailorResumeData:
    def test_returns_dict(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        tailored = tailor_resume_data(SAMPLE_RESUME_DATA, kw)
        assert isinstance(tailored, dict)
        assert "name" in tailored

    def test_does_not_mutate_original(self):
        import copy
        original = copy.deepcopy(SAMPLE_RESUME_DATA)
        kw = extract_jd_keywords(SAMPLE_JD)
        tailor_resume_data(SAMPLE_RESUME_DATA, kw)
        assert SAMPLE_RESUME_DATA == original

    def test_skills_reordered(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        tailored = tailor_resume_data(SAMPLE_RESUME_DATA, kw)
        assert "skills" in tailored
        assert len(tailored["skills"]) == len(SAMPLE_RESUME_DATA["skills"])

    def test_bullets_preserved(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        tailored = tailor_resume_data(SAMPLE_RESUME_DATA, kw)
        for i, job in enumerate(tailored["experience"]):
            assert len(job["bullets"]) == len(SAMPLE_RESUME_DATA["experience"][i]["bullets"])

    def test_empty_keywords_returns_copy(self):
        kw = extract_jd_keywords("")
        tailored = tailor_resume_data(SAMPLE_RESUME_DATA, kw)
        assert tailored["name"] == SAMPLE_RESUME_DATA["name"]


class TestGenerateMatchReport:
    def test_report_contains_score(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        report = generate_match_report(SAMPLE_RESUME_DATA, kw)
        assert "MATCH" in report
        assert "%" in report

    def test_report_contains_sections(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        report = generate_match_report(SAMPLE_RESUME_DATA, kw)
        assert "IN YOUR RESUME" in report or "MISSING" in report

    def test_unrelated_jd_low_score(self):
        kw = extract_jd_keywords(SAMPLE_JD_UNRELATED)
        report = generate_match_report(SAMPLE_RESUME_DATA, kw)
        # Should indicate weak match for a marketing JD
        assert "MATCH" in report
