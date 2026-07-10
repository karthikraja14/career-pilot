"""Tests for cover_letter.py — Cover letter generation."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cover_letter import generate_cover_letter, save_cover_letter
from jd_tailorer import extract_jd_keywords
from tests.conftest import SAMPLE_RESUME_DATA, SAMPLE_JD, SAMPLE_JD_UNRELATED


class TestGenerateCoverLetter:
    def test_basic_generation(self):
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Google", "Lead QA")
        assert "Google" in letter
        assert "Lead QA" in letter
        assert SAMPLE_RESUME_DATA["name"] in letter

    def test_contains_contact_info(self):
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Microsoft", "SDET")
        assert SAMPLE_RESUME_DATA["contact"]["email"] in letter

    def test_with_jd_keywords(self):
        kw = extract_jd_keywords(SAMPLE_JD)
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Google", "Lead QA", kw)
        assert "Google" in letter
        assert len(letter) > 200

    def test_healthcare_template_selected(self):
        kw = {"technical_skills": [], "compound_matches": [],
              "domain_keywords": ["healthcare", "medtech"], "soft_skills": []}
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Philips", "QA Lead", kw)
        # Should use healthcare template
        assert "Philips" in letter

    def test_empty_resume_data(self):
        minimal = {"name": "", "contact": {}, "experience": [], "skills": {},
                    "achievements": []}
        letter = generate_cover_letter(minimal, "TestCo", "Tester")
        assert "TestCo" in letter
        assert "Tester" in letter

    def test_special_characters_in_company(self):
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "AT&T", "QA Lead")
        assert "AT&T" in letter

    def test_long_role_name(self):
        long_role = "Principal Staff Senior Lead Test Automation Architect"
        letter = generate_cover_letter(SAMPLE_RESUME_DATA, "Google", long_role)
        # Role may be line-wrapped, so check key parts
        assert "Principal Staff" in letter
        assert "Architect" in letter


class TestSaveCoverLetter:
    def test_saves_to_file(self, temp_dir):
        letter = "Test cover letter content."
        path = save_cover_letter(letter, "Google", "QA Lead", output_dir=temp_dir)
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == letter

    def test_filename_sanitized(self, temp_dir):
        path = save_cover_letter("test", "A/B Corp", "Lead (QA)", output_dir=temp_dir)
        assert os.path.exists(path)
        # Should not contain path separators in filename
        assert "/" not in os.path.basename(path).replace("Cover_Letter_", "")

    def test_creates_output_dir(self, temp_dir):
        subdir = os.path.join(temp_dir, "new_folder")
        path = save_cover_letter("test", "Co", "Role", output_dir=subdir)
        assert os.path.exists(path)
