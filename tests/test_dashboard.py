"""Tests for dashboard.py — HTML dashboard generation."""
import pytest
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tracking.dashboard import generate_dashboard, _gather_stats


class TestGenerateDashboard:
    def test_generates_valid_html(self):
        stats = {
            "total_applications": 5,
            "status_counts": {"Applied": 3, "Interview": 1, "Rejected": 1},
            "platform_counts": {"LinkedIn": 3, "Naukri": 2},
            "product_count": 3,
            "service_count": 2,
            "date_counts": {"2025-06-01": 2, "2025-06-02": 3},
            "today_stats": {"linkedin": 2, "naukri": 1, "total": 3},
            "found_jobs_count": 10,
            "found_by_verdict": {"STRONG MATCH": 5, "WEAK": 5},
            "funnel": {"Applied": 3, "Screening": 1, "Interview": 1, "Offer": 0, "Rejected": 1},
            "applications": [
                {"id": 1, "company": "Google", "role": "QA Lead",
                 "platform": "LinkedIn", "status": "Applied",
                 "is_product_company": True, "created_at": "2025-06-01"},
            ],
        }
        html = generate_dashboard(stats)
        assert "<!DOCTYPE html>" in html
        assert "Google" in html
        assert "chart.js" in html.lower() or "Chart" in html

    def test_empty_stats(self):
        stats = {
            "total_applications": 0,
            "status_counts": {},
            "platform_counts": {},
            "product_count": 0,
            "service_count": 0,
            "date_counts": {},
            "today_stats": {},
            "found_jobs_count": 0,
            "found_by_verdict": {},
            "funnel": {"Applied": 0, "Screening": 0, "Interview": 0, "Offer": 0, "Rejected": 0},
            "applications": [],
        }
        html = generate_dashboard(stats)
        assert "<!DOCTYPE html>" in html
        assert "No applications tracked" in html

    def test_html_escaping(self):
        stats = {
            "total_applications": 1,
            "status_counts": {"Applied": 1},
            "platform_counts": {"LinkedIn": 1},
            "product_count": 1, "service_count": 0,
            "date_counts": {"2025-06-01": 1},
            "today_stats": {},
            "found_jobs_count": 0,
            "found_by_verdict": {},
            "funnel": {"Applied": 1, "Screening": 0, "Interview": 0, "Offer": 0, "Rejected": 0},
            "applications": [
                {"id": 1, "company": "<script>alert(1)</script>",
                 "role": "Test", "platform": "LinkedIn",
                 "status": "Applied", "is_product_company": True,
                 "created_at": "2025-06-01"},
            ],
        }
        html = generate_dashboard(stats)
        # Script tag should be escaped
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_large_dataset(self):
        apps = [
            {"id": i, "company": f"Company {i}", "role": "QA",
             "platform": "LinkedIn", "status": "Applied",
             "is_product_company": i % 2 == 0,
             "created_at": f"2025-06-{(i % 28) + 1:02d}"}
            for i in range(100)
        ]
        stats = {
            "total_applications": 100,
            "status_counts": {"Applied": 100},
            "platform_counts": {"LinkedIn": 100},
            "product_count": 50, "service_count": 50,
            "date_counts": {f"2025-06-{d:02d}": 4 for d in range(1, 29)},
            "today_stats": {"total": 5},
            "found_jobs_count": 200,
            "found_by_verdict": {},
            "funnel": {"Applied": 100, "Screening": 0, "Interview": 0, "Offer": 0, "Rejected": 0},
            "applications": apps,
        }
        html = generate_dashboard(stats)
        assert "100" in html


class TestGatherStats:
    def test_returns_valid_structure(self, monkeypatch):
        """Test with no files present."""
        monkeypatch.setattr("tracking.dashboard.TRACKER_FILE", "/nonexistent/path.json")
        monkeypatch.setattr("tracking.dashboard.STATE_FILE", "/nonexistent/state.json")
        monkeypatch.setattr("tracking.dashboard.FOUND_JOBS_FILE", "/nonexistent/found.json")
        stats = _gather_stats()
        assert stats["total_applications"] == 0
        assert "funnel" in stats
