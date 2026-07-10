"""Tests for apply/safety.py — Rate limiting and safety checks."""
import pytest
import json
import os
import sys
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestSafety:
    def test_new_day_state(self, temp_dir, monkeypatch):
        from apply.safety import _new_day_state
        state = _new_day_state()
        assert state["date"] == str(date.today())
        assert state["counts"]["linkedin"] == 0
        assert state["counts"]["total"] == 0

    def test_can_apply_fresh_state(self, temp_dir, monkeypatch):
        from apply.safety import can_apply, _save_state, _new_day_state, STATE_FILE
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        allowed, reason = can_apply("linkedin")
        assert allowed is True
        assert reason == "OK"

    def test_daily_limit_enforced(self, temp_dir, monkeypatch):
        from apply.safety import can_apply, record_application, STATE_FILE
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        # Record 10 LinkedIn applications
        for i in range(10):
            record_application("linkedin", f"url_{i}", "Co", "Role", True)

        allowed, reason = can_apply("linkedin")
        assert allowed is False
        assert "limit" in reason.lower()

    def test_is_already_applied(self, temp_dir, monkeypatch):
        from apply.safety import is_already_applied, record_application
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        record_application("linkedin", "https://job.com/1", "Co", "Role", True)
        assert is_already_applied("https://job.com/1") is True
        assert is_already_applied("https://job.com/2") is False

    def test_consecutive_errors(self, temp_dir, monkeypatch):
        from apply.safety import should_stop, record_application
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        # Record 3 failures (max consecutive errors)
        for i in range(3):
            record_application("linkedin", f"url_{i}", "Co", "Role", False)

        stop, reason = should_stop("linkedin")
        assert stop is True
        assert "error" in reason.lower()

    def test_cooldown_blocks_apply(self, temp_dir, monkeypatch):
        from apply.safety import can_apply, trigger_cooldown
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        trigger_cooldown("linkedin")
        allowed, reason = can_apply("linkedin")
        assert allowed is False
        assert "cooldown" in reason.lower()

    def test_get_today_stats(self, temp_dir, monkeypatch):
        from apply.safety import get_today_stats, record_application
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        record_application("linkedin", "url_1", "Co", "Role", True)
        record_application("naukri", "url_2", "Co2", "Role2", True)

        stats = get_today_stats()
        assert stats["linkedin"] == 1
        assert stats["naukri"] == 1
        assert stats["total"] == 2

    def test_total_daily_limit(self, temp_dir, monkeypatch):
        from apply.safety import can_apply, record_application, DAILY_LIMITS
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        # Fill up to total limit
        for i in range(DAILY_LIMITS["total"]):
            platform = "linkedin" if i < 10 else "naukri"
            record_application(platform, f"url_{i}", "Co", "Role", True)

        allowed, reason = can_apply("naukri")
        assert allowed is False

    def test_success_clears_errors(self, temp_dir, monkeypatch):
        from apply.safety import should_stop, record_application, get_consecutive_errors
        state_file = os.path.join(temp_dir, "apply_state.json")
        monkeypatch.setattr("apply.safety.STATE_FILE", state_file)
        monkeypatch.setattr("apply.safety.STATE_DIR", temp_dir)

        # 2 errors, then success
        record_application("linkedin", "url_1", "Co", "Role", False)
        record_application("linkedin", "url_2", "Co", "Role", False)
        record_application("linkedin", "url_3", "Co", "Role", True)

        stop, _ = should_stop("linkedin")
        assert stop is False
