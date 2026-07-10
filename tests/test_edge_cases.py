"""
Edge case, boundary, and exploratory tests for Career Pilot.
Covers scenarios the main test files don't: malformed input, unicode,
concurrency-like races, extreme values, and integration across modules.
"""
import pytest
import os
import sys
import json
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import (
    PRODUCT_COMPANIES, SERVICE_COMPANIES, SCORING_WEIGHTS,
    TRENDING_SKILLS, JOB_SEARCH_CONFIG,
)
from resume.analyzer import (
    extract_contact_info, detect_sections, score_completeness,
    score_ats_compatibility, score_impact_statements,
    score_skills_relevance, score_structure,
)
from resume.tailorer import extract_jd_keywords, tailor_resume_data
from jobs.cover_letter import generate_cover_letter, save_cover_letter
from jobs.keyword_gap import analyze_keyword_gap, extract_resume_keywords
from tracking.dashboard import generate_dashboard, _esc
from tracking.version_tracker import record_version, get_version_history
from research.salary_lookup import generate_salary_urls
from research.connection_finder import generate_connection_urls
from tests.conftest import SAMPLE_RESUME_DATA, SAMPLE_JD


# ═══════════════════════════════════════════════════════════════════════
# Unicode & Special Character Tests
# ═══════════════════════════════════════════════════════════════════════

class TestUnicodeHandling:
    def test_unicode_in_resume_text(self):
        text = "Résumé: José García — Senior Développeur at Zürich HQ. 日本語テスト."
        info = extract_contact_info(text)
        # Should not crash
        assert isinstance(info, dict)

    def test_unicode_company_in_cover_letter(self):
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Ünïcödé Corp™", "Ëngïnéér")
        assert "Ünïcödé Corp™" in letter

    def test_unicode_in_jd_extraction(self):
        jd = "Expérience with Kubernetes, Docker, and café-driven développement"
        kw = extract_jd_keywords(jd)
        assert "kubernetes" in kw["technical_skills"] or "docker" in kw["technical_skills"]

    def test_emoji_in_text(self):
        text = "🚀 Led team of 10 engineers. Reduced bugs by 50% 🎯"
        info = extract_contact_info(text)
        assert isinstance(info, dict)

    def test_html_injection_in_dashboard(self):
        """Verify XSS-like strings are escaped in dashboard."""
        assert "&lt;" in _esc("<script>")
        assert "&amp;" in _esc("AT&T")
        assert "&quot;" in _esc('He said "hello"')

    def test_unicode_in_salary_urls(self):
        urls = generate_salary_urls("München GmbH", "Ingénieur")
        for url in urls.values():
            assert isinstance(url, str)

    def test_unicode_in_connection_urls(self):
        urls = generate_connection_urls("São Paulo Tech", "engenheiro")
        assert len(urls) >= 4


# ═══════════════════════════════════════════════════════════════════════
# Boundary Value Tests
# ═══════════════════════════════════════════════════════════════════════

class TestBoundaryValues:
    def test_single_word_resume(self):
        score, suggestions = score_structure("hello", page_count=1)
        assert 0 <= score <= 100

    def test_very_long_resume(self):
        """10,000 words should not crash."""
        text = ("Led automation framework " * 2500)
        score, _ = score_impact_statements(text)
        assert 0 <= score <= 100

    def test_zero_page_resume(self):
        score, _ = score_structure("some text", page_count=0)
        assert 0 <= score <= 100

    def test_100_page_resume(self):
        score, suggestions = score_structure("content " * 100, page_count=100)
        assert score < 100  # Should be penalized

    def test_empty_jd_keyword_gap(self):
        gap = analyze_keyword_gap("", "Python Selenium Jenkins")
        assert gap["match_score"] >= 0

    def test_empty_resume_keyword_gap(self):
        gap = analyze_keyword_gap(SAMPLE_JD, "")
        assert isinstance(gap["match_score"], int)

    def test_single_skill_resume(self):
        score, _ = score_skills_relevance("python")
        assert 0 <= score <= 100

    def test_all_sections_missing(self):
        sections = {s: False for s in ["contact", "summary", "experience",
                                        "education", "skills", "projects",
                                        "certifications", "achievements"]}
        score, suggestions = score_completeness(sections)
        assert score == 0
        assert len(suggestions) > 0

    def test_all_sections_present(self):
        sections = {s: True for s in ["contact", "summary", "experience",
                                       "education", "skills", "projects",
                                       "certifications", "achievements"]}
        score, _ = score_completeness(sections)
        assert score == 100

    def test_jd_with_only_stopwords(self):
        kw = extract_jd_keywords("the and or but with from this that")
        assert len(kw["technical_skills"]) == 0


# ═══════════════════════════════════════════════════════════════════════
# Malformed Input Tests
# ═══════════════════════════════════════════════════════════════════════

class TestMalformedInput:
    def test_resume_data_missing_keys(self):
        """Cover letter should handle missing resume data gracefully."""
        minimal = {"name": "Test", "contact": {}}
        letter = generate_cover_letter(minimal, "Co", "Role")
        assert "Co" in letter

    def test_resume_data_empty_experience(self):
        data = copy.deepcopy(SAMPLE_RESUME_DATA)
        data["experience"] = []
        kw = extract_jd_keywords(SAMPLE_JD)
        tailored = tailor_resume_data(data, kw)
        assert tailored["experience"] == []

    def test_resume_data_empty_skills(self):
        data = copy.deepcopy(SAMPLE_RESUME_DATA)
        data["skills"] = {}
        kw = extract_jd_keywords(SAMPLE_JD)
        tailored = tailor_resume_data(data, kw)
        assert tailored["skills"] == {}

    def test_cover_letter_empty_company(self):
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "", "Role")
        assert "Role" in letter

    def test_cover_letter_empty_role(self):
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Google", "")
        assert "Google" in letter

    def test_keyword_gap_jd_is_numbers_only(self):
        gap = analyze_keyword_gap("12345 67890 11111", "Python Java")
        assert isinstance(gap["match_score"], int)

    def test_keyword_gap_resume_is_numbers_only(self):
        gap = analyze_keyword_gap(SAMPLE_JD, "12345 67890 11111")
        assert isinstance(gap["match_score"], int)

    def test_extract_contact_multiple_emails(self):
        text = "email: first@test.com and also second@test.com"
        info = extract_contact_info(text)
        assert info["email"] == "first@test.com"  # Should take first

    def test_detect_sections_non_standard_headers(self):
        text = "MY WORK HISTORY\nSenior Dev at Google\n\nACADEMIC BACKGROUND\nMIT 2020"
        sections = detect_sections(text)
        # "work history" should match experience pattern
        assert isinstance(sections, dict)

    def test_salary_urls_empty_inputs(self):
        urls = generate_salary_urls("", "")
        assert len(urls) >= 4  # Should still generate URL structures

    def test_connection_urls_special_chars(self):
        urls = generate_connection_urls("AT&T / Verizon", "dev ops")
        for url in urls.values():
            assert isinstance(url, str)
            assert url.startswith("https://")


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests (cross-module)
# ═══════════════════════════════════════════════════════════════════════

class TestCrossModuleIntegration:
    def test_tailorer_to_cover_letter_pipeline(self):
        """Extract JD keywords → generate cover letter with those keywords."""
        kw = extract_jd_keywords(SAMPLE_JD)
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Google", "Lead QA", kw)
        assert "Google" in letter
        assert len(letter) > 200

    def test_tailorer_to_keyword_gap_pipeline(self):
        """JD keywords should flow correctly to gap analysis."""
        resume_text = " ".join(SAMPLE_RESUME_DATA["skills"].values())
        gap = analyze_keyword_gap(SAMPLE_JD, resume_text)
        assert "matched" in gap
        assert "missing" in gap

    def test_version_tracker_with_tailored_resume(self, temp_dir, monkeypatch):
        """Track a tailored resume version with keywords."""
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        kw = extract_jd_keywords(SAMPLE_JD)
        matched_skills = kw["technical_skills"][:5]

        record_version("Google", "Lead QA", "tailored.pdf",
                       tailored=True, keywords=matched_skills,
                       cover_letter="cl_google.txt")

        history = get_version_history("Google")
        assert len(history) == 1
        assert history[0]["tailored"] is True
        assert len(history[0]["keywords_used"]) > 0

    def test_config_roles_feed_into_all_modules(self):
        """Config target roles should be usable by all dependent modules."""
        roles = JOB_SEARCH_CONFIG["target_roles"]
        assert len(roles) > 0

        # Salary lookup with first configured role
        urls = generate_salary_urls("Google", roles[0])
        assert len(urls) >= 4

        # Connection finder
        first_word = roles[0].split()[0].lower()
        conn_urls = generate_connection_urls("Google", first_word)
        assert len(conn_urls) >= 4

    def test_dashboard_with_all_statuses(self):
        """Dashboard should handle every possible application status."""
        statuses = ["To Apply", "Applied", "Screening", "Interview",
                     "Offer", "Rejected"]
        apps = [
            {"id": i, "company": f"Co{i}", "role": "Dev",
             "platform": "LinkedIn", "status": s,
             "is_product_company": True, "created_at": "2025-06-01"}
            for i, s in enumerate(statuses, 1)
        ]
        stats = {
            "total_applications": len(apps),
            "status_counts": {s: 1 for s in statuses},
            "platform_counts": {"LinkedIn": len(apps)},
            "product_count": len(apps), "service_count": 0,
            "date_counts": {"2025-06-01": len(apps)},
            "today_stats": {},
            "found_jobs_count": 0, "found_by_verdict": {},
            "funnel": {s: 1 for s in ["Applied", "Screening", "Interview", "Offer", "Rejected"]},
            "applications": apps,
        }
        html = generate_dashboard(stats)
        for status in statuses:
            # Status should appear somewhere in the HTML (as badge or chart data)
            assert status.lower().replace(" ", "-") in html.lower() or status in html


# ═══════════════════════════════════════════════════════════════════════
# Config Consistency Tests
# ═══════════════════════════════════════════════════════════════════════

class TestConfigConsistency:
    def test_all_trending_skills_lowercase(self):
        for category, skills in TRENDING_SKILLS.items():
            for skill in skills:
                assert skill == skill.lower(), \
                    f"Skill '{skill}' in '{category}' must be lowercase"

    def test_no_empty_company_names(self):
        for company in PRODUCT_COMPANIES:
            assert company.strip() != "", "Empty company name in PRODUCT_COMPANIES"
        for company in SERVICE_COMPANIES:
            assert company.strip() != "", "Empty company name in SERVICE_COMPANIES"

    def test_target_roles_reasonable_length(self):
        for role in JOB_SEARCH_CONFIG["target_roles"]:
            assert 3 <= len(role) <= 50, f"Role '{role}' has unreasonable length"

    def test_scoring_weights_are_floats(self):
        for key, val in SCORING_WEIGHTS.items():
            assert isinstance(val, float), f"Weight for {key} should be float, got {type(val)}"

    def test_experience_years_reasonable(self):
        years = JOB_SEARCH_CONFIG["experience_years"]
        assert 0 < years <= 50, f"Experience years {years} seems wrong"

    def test_domains_not_empty(self):
        domains = JOB_SEARCH_CONFIG.get("domains", [])
        assert len(domains) > 0


# ═══════════════════════════════════════════════════════════════════════
# Security / Injection Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSecurityEdgeCases:
    def test_xss_in_company_name_dashboard(self):
        """Ensure HTML-special chars in company names are escaped."""
        malicious = '<img src=x onerror=alert(1)>'
        escaped = _esc(malicious)
        assert "<img" not in escaped
        assert "&lt;" in escaped

    def test_path_traversal_in_cover_letter_save(self, temp_dir):
        """Company name with path chars should not escape output dir."""
        path = save_cover_letter("test", "../../etc/passwd", "Role",
                                 output_dir=temp_dir)
        # File should be inside temp_dir, not escaped
        assert os.path.commonpath([temp_dir, path]) == temp_dir

    def test_null_bytes_in_text(self):
        text = "Hello\x00World with null bytes"
        info = extract_contact_info(text)
        assert isinstance(info, dict)

    def test_very_long_company_name(self):
        long_name = "A" * 10000
        urls = generate_salary_urls(long_name, "Dev")
        assert len(urls) >= 4

    def test_newlines_in_cover_letter_inputs(self):
        letter = generate_cover_letter(
            SAMPLE_RESUME_DATA, "Line1\nLine2", "Role\nTitle"
        )
        assert isinstance(letter, str)


# ═══════════════════════════════════════════════════════════════════════
# Scoring Consistency Tests
# ═══════════════════════════════════════════════════════════════════════

class TestScoringConsistency:
    def test_better_resume_scores_higher_ats(self):
        """Resume with all contact info should score >= resume without."""
        full_contact = {"email": "a@b.com", "phone": "123", "linkedin": "url", "github": "url"}
        empty_contact = {}
        text = "Experience with Python and Selenium testing automation Jenkins CI/CD"

        score_full, _ = score_ats_compatibility(text, full_contact)
        score_empty, _ = score_ats_compatibility(text, empty_contact)
        assert score_full >= score_empty

    def test_more_action_verbs_scores_higher_impact(self):
        """Resume with action verbs should score higher than bland one."""
        strong = "Led team. Designed framework. Automated tests. Reduced bugs. Built CI pipeline."
        weak = "Was involved in testing. Helped with automation. Worked on bugs."

        score_strong, _ = score_impact_statements(strong)
        score_weak, _ = score_impact_statements(weak)
        assert score_strong >= score_weak

    def test_more_skills_scores_higher(self):
        """Resume with more trending skills should score higher."""
        many_skills = "python selenium playwright jenkins docker kubernetes azure jira agile scrum cypress"
        few_skills = "python"

        score_many, _ = score_skills_relevance(many_skills)
        score_few, _ = score_skills_relevance(few_skills)
        assert score_many >= score_few

    def test_scores_always_in_range(self):
        """All scoring functions should return 0-100."""
        text = SAMPLE_JD
        contact = {"email": "test@test.com"}
        sections = {s: True for s in ["contact", "summary", "experience",
                                       "education", "skills"]}

        for score_fn, args in [
            (score_completeness, (sections,)),
            (score_ats_compatibility, (text, contact)),
            (score_impact_statements, (text,)),
            (score_skills_relevance, (text,)),
            (score_structure, (text, 2)),
        ]:
            score, _ = score_fn(*args)
            assert 0 <= score <= 100, f"{score_fn.__name__} returned {score}"
