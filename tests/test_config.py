"""Tests for config.py — validates configuration integrity."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import (
    JOB_SEARCH_CONFIG, PRODUCT_COMPANIES, SERVICE_COMPANIES,
    TRENDING_SKILLS, SCORING_WEIGHTS, GRADE_THRESHOLDS,
    EXPECTED_SECTIONS, ACTION_VERBS, WEAK_PHRASES,
)


class TestJobSearchConfig:
    def test_target_roles_not_empty(self):
        assert len(JOB_SEARCH_CONFIG["target_roles"]) > 0

    def test_experience_years_positive(self):
        assert JOB_SEARCH_CONFIG["experience_years"] > 0

    def test_locations_not_empty(self):
        assert len(JOB_SEARCH_CONFIG["preferred_locations"]) > 0

    def test_domains_not_empty(self):
        assert len(JOB_SEARCH_CONFIG["domains"]) > 0


class TestCompanyLists:
    def test_product_companies_not_empty(self):
        assert len(PRODUCT_COMPANIES) > 50

    def test_service_companies_not_empty(self):
        assert len(SERVICE_COMPANIES) > 5

    def test_no_overlap_product_service(self):
        """Product and service lists should not overlap."""
        overlap = set(PRODUCT_COMPANIES) & set(SERVICE_COMPANIES)
        assert len(overlap) == 0, f"Overlapping companies: {overlap}"

    def test_no_duplicate_product_companies(self):
        assert len(PRODUCT_COMPANIES) == len(set(PRODUCT_COMPANIES))

    def test_no_duplicate_service_companies(self):
        assert len(SERVICE_COMPANIES) == len(set(SERVICE_COMPANIES))


class TestScoringWeights:
    def test_weights_sum_to_one(self):
        total = sum(SCORING_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"

    def test_all_weights_positive(self):
        for key, weight in SCORING_WEIGHTS.items():
            assert weight > 0, f"Weight for {key} is {weight}"

    def test_required_dimensions_present(self):
        required = {"completeness", "ats_compatibility", "impact_statements",
                     "skills_relevance", "structure"}
        assert required.issubset(set(SCORING_WEIGHTS.keys()))


class TestGradeThresholds:
    def test_thresholds_descending(self):
        grades = sorted(GRADE_THRESHOLDS.items(), key=lambda x: -x[1])
        values = [v for _, v in grades]
        assert values == sorted(values, reverse=True)

    def test_f_is_zero(self):
        assert GRADE_THRESHOLDS["F"] == 0

    def test_a_plus_is_highest(self):
        assert GRADE_THRESHOLDS["A+"] == max(GRADE_THRESHOLDS.values())


class TestTrendingSkills:
    def test_categories_not_empty(self):
        assert len(TRENDING_SKILLS) >= 4

    def test_each_category_has_skills(self):
        for category, skills in TRENDING_SKILLS.items():
            assert len(skills) > 0, f"Category '{category}' is empty"

    def test_skills_are_lowercase(self):
        for category, skills in TRENDING_SKILLS.items():
            for skill in skills:
                assert skill == skill.lower(), f"Skill '{skill}' in '{category}' should be lowercase"


class TestExpectedSections:
    def test_has_core_sections(self):
        core = {"contact", "summary", "experience", "education", "skills"}
        assert core.issubset(set(EXPECTED_SECTIONS))


class TestActionVerbs:
    def test_verbs_not_empty(self):
        assert len(ACTION_VERBS) >= 10

    def test_verbs_lowercase(self):
        for verb in ACTION_VERBS:
            assert verb == verb.lower()


class TestWeakPhrases:
    def test_phrases_not_empty(self):
        assert len(WEAK_PHRASES) >= 5

    def test_no_overlap_with_action_verbs(self):
        for phrase in WEAK_PHRASES:
            for verb in ACTION_VERBS:
                assert verb not in phrase.split(), \
                    f"Weak phrase '{phrase}' contains action verb '{verb}'"
