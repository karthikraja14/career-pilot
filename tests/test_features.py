"""Tests for version_tracker.py, salary_lookup.py, connection_finder.py, and job_matcher duplicate detection."""
import pytest
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tracking.version_tracker import (
    record_version, get_version_history, check_duplicate_company,
    get_resume_for_company, _load_versions, _save_versions,
)
from research.salary_lookup import generate_salary_urls, batch_salary_lookup
from research.connection_finder import generate_connection_urls, suggest_target_companies


# ─── Version Tracker Tests ────────────────────────────────────────────────────

class TestVersionTracker:
    def test_record_and_retrieve(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        entry = record_version("Google", "QA Lead", "resume.pdf")
        assert entry["company"] == "Google"
        assert entry["id"] == 1

        history = get_version_history()
        assert len(history) == 1

    def test_duplicate_detection(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        record_version("Google", "QA Lead", "resume.pdf")
        assert check_duplicate_company("Google") is True
        assert check_duplicate_company("Microsoft") is False

    def test_filter_by_company(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        record_version("Google", "QA Lead", "resume.pdf")
        record_version("Microsoft", "SDET", "resume.pdf")
        record_version("Google", "Test Architect", "tailored.pdf", tailored=True)

        google = get_version_history("Google")
        assert len(google) == 2
        microsoft = get_version_history("Microsoft")
        assert len(microsoft) == 1

    def test_get_resume_for_company(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        record_version("Google", "V1", "resume_v1.pdf")
        record_version("Google", "V2", "resume_v2.pdf")
        latest = get_resume_for_company("Google")
        assert latest["resume_file"] == "resume_v2.pdf"

    def test_no_history(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)
        assert get_version_history() == []
        assert get_resume_for_company("Nonexistent") is None

    def test_tailored_flag(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        record_version("Google", "QA", "r.pdf", tailored=True,
                       keywords=["python", "selenium"])
        entry = get_version_history("Google")[0]
        assert entry["tailored"] is True
        assert "python" in entry["keywords_used"]

    def test_cover_letter_tracked(self, temp_dir, monkeypatch):
        vfile = os.path.join(temp_dir, "versions.json")
        monkeypatch.setattr("tracking.version_tracker.VERSION_FILE", vfile)

        record_version("Google", "QA", "r.pdf", cover_letter="cl.txt")
        entry = get_version_history()[0]
        assert entry["cover_letter"] == "cl.txt"


# ─── Salary Lookup Tests ─────────────────────────────────────────────────────

class TestSalaryLookup:
    def test_generates_urls(self):
        urls = generate_salary_urls("Google", "Lead Test Engineer")
        assert len(urls) >= 4
        for platform, url in urls.items():
            assert url.startswith("https://")

    def test_url_encoding(self):
        urls = generate_salary_urls("Johnson & Johnson", "Lead QA Engineer")
        for url in urls.values():
            # Should not have raw spaces
            assert " " not in url or "+" in url or "%20" in url

    def test_batch_lookup(self):
        companies = ["Google", "Microsoft", "Amazon"]
        results = batch_salary_lookup(companies, "QA Lead")
        assert len(results) == 3
        for company in companies:
            assert company in results
            assert len(results[company]) >= 4

    def test_empty_company(self):
        urls = generate_salary_urls("", "QA")
        assert len(urls) >= 4  # Should still generate URLs

    def test_special_characters(self):
        urls = generate_salary_urls("AT&T", "QA/Test Lead")
        for url in urls.values():
            assert isinstance(url, str)


# ─── Connection Finder Tests ─────────────────────────────────────────────────

class TestConnectionFinder:
    def test_generates_urls(self):
        urls = generate_connection_urls("Google", "engineer")
        assert "People in your role" in urls
        assert "Recruiters" in urls
        assert "Company Page" in urls
        for url in urls.values():
            assert url.startswith("https://")

    def test_custom_role_keyword(self):
        urls = generate_connection_urls("Microsoft", "automation")
        assert "automation" in urls["People in your role"].lower() or \
               "automation" in urls["Company Jobs"].lower()

    def test_suggest_companies(self):
        suggestions = suggest_target_companies(5)
        assert len(suggestions) <= 5
        assert len(suggestions) > 0

    def test_suggest_max(self):
        suggestions = suggest_target_companies(100)
        assert len(suggestions) <= 100


# ─── Job Matcher Duplicate Detection Tests ────────────────────────────────────

class TestDuplicateDetection:
    def test_detect_duplicate(self, temp_dir, monkeypatch):
        from jobs.matcher import add_application, check_duplicate_application
        app_dir = os.path.join(temp_dir, "applications")
        os.makedirs(app_dir, exist_ok=True)
        tracker_file = os.path.join(app_dir, "tracker.json")
        tracker_csv = os.path.join(app_dir, "tracker.csv")
        monkeypatch.setattr("jobs.matcher.TRACKER_FILE", tracker_file)
        monkeypatch.setattr("jobs.matcher.TRACKER_CSV", tracker_csv)

        add_application("Google", "QA Lead", "LinkedIn")
        result = check_duplicate_application("Google")
        assert result is not None
        assert result["company"] == "Google"

    def test_no_false_positive(self, temp_dir, monkeypatch):
        from jobs.matcher import add_application, check_duplicate_application
        app_dir = os.path.join(temp_dir, "applications")
        os.makedirs(app_dir, exist_ok=True)
        tracker_file = os.path.join(app_dir, "tracker.json")
        tracker_csv = os.path.join(app_dir, "tracker.csv")
        monkeypatch.setattr("jobs.matcher.TRACKER_FILE", tracker_file)
        monkeypatch.setattr("jobs.matcher.TRACKER_CSV", tracker_csv)

        add_application("Google", "QA Lead", "LinkedIn")
        result = check_duplicate_application("Microsoft")
        assert result is None

    def test_case_insensitive(self, temp_dir, monkeypatch):
        from jobs.matcher import add_application, check_duplicate_application
        app_dir = os.path.join(temp_dir, "applications")
        os.makedirs(app_dir, exist_ok=True)
        tracker_file = os.path.join(app_dir, "tracker.json")
        tracker_csv = os.path.join(app_dir, "tracker.csv")
        monkeypatch.setattr("jobs.matcher.TRACKER_FILE", tracker_file)
        monkeypatch.setattr("jobs.matcher.TRACKER_CSV", tracker_csv)

        add_application("Google", "QA Lead", "LinkedIn")
        result = check_duplicate_application("google")
        assert result is not None
