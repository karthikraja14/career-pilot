"""Shared test fixtures and sample data."""
import os
import sys
import json
import pytest
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


SAMPLE_RESUME_DATA = {
    "name": "Test User",
    "title": "Lead Test Engineer",
    "contact": {
        "phone": "(+91) 9999999999",
        "email": "test@example.com",
        "linkedin": "linkedin.com/in/test-user",
        "location": "Bangalore, India",
    },
    "summary": (
        "Lead Test Engineer with 10 years of experience in test automation, "
        "CI/CD, and quality engineering. Built Selenium and Playwright "
        "frameworks, led teams of 20+ engineers, and reduced defect leakage "
        "by 35%. Expert in Python, Java, Jenkins, Docker, and Azure."
    ),
    "skills": {
        "Test Frameworks": "Selenium, Playwright, Pytest, Robot Framework, REST Assured",
        "Programming": "Python, Java, SQL, Bash",
        "CI/CD & DevOps": "Jenkins, Azure DevOps, Docker, Kubernetes, GitHub Actions",
        "Cloud": "Azure, AWS",
        "Testing Types": "API Testing, Performance Testing, Integration Testing",
    },
    "experience": [
        {
            "period": "Mar 2023 -- Present",
            "role": "Lead Test Engineer",
            "company": "Acme Corp -- Platform Team",
            "bullets": [
                "Led test framework redesign reducing execution time by 60%.",
                "Built E2E performance testing scaling to 50,000 concurrent users.",
                "Mentored 15 engineers on automation best practices.",
            ],
        },
        {
            "period": "Jan 2020 -- Feb 2023",
            "role": "Senior Test Engineer",
            "company": "Beta Inc",
            "bullets": [
                "Designed 300+ test cases and automated 80% of regression suite.",
                "Implemented CI/CD pipeline with Jenkins and Docker.",
            ],
        },
    ],
    "achievements": [
        "Test coverage: 40% to 85% | Cycle time reduced 40%.",
        "Scaled perf testing from 100 to 50,000 concurrent users.",
    ],
    "education": [
        {"degree": "B.Tech Computer Science", "year": "2014", "institution": "Test University"},
    ],
    "languages": ["English", "Hindi"],
}

SAMPLE_JD = """
Lead Test Engineer - Cloud Platform

About the Role:
We're looking for a Lead Test Engineer to own our test automation strategy.
You'll lead a team of QA engineers and drive quality across our cloud platform.

Requirements:
- 8+ years of experience in test automation
- Strong experience with Selenium, Playwright, or Cypress
- Proficiency in Python or Java
- Experience with CI/CD pipelines (Jenkins, GitHub Actions)
- Experience with Docker, Kubernetes
- API testing experience (REST, GraphQL)
- Performance testing experience (JMeter, k6, Gatling)
- Experience with Azure or AWS
- Strong understanding of Agile/Scrum methodologies
- Leadership experience managing QA teams
- Healthcare or MedTech domain experience is a plus

Nice to have:
- Experience with AI testing or ML model validation
- BDD/TDD experience
- Security testing knowledge
- ISO 13485 or FDA compliance experience
"""

SAMPLE_JD_MINIMAL = "Looking for a junior developer to help with basic tasks."

SAMPLE_JD_UNRELATED = """
Marketing Manager position. Must have 5 years of experience in
digital marketing, SEO, content strategy, and social media management.
Experience with Google Analytics, HubSpot, and Salesforce preferred.
"""


@pytest.fixture
def sample_resume_data():
    return SAMPLE_RESUME_DATA.copy()


@pytest.fixture
def sample_jd():
    return SAMPLE_JD


@pytest.fixture
def sample_jd_minimal():
    return SAMPLE_JD_MINIMAL


@pytest.fixture
def sample_jd_unrelated():
    return SAMPLE_JD_UNRELATED


@pytest.fixture
def temp_dir():
    """Provide a temporary directory, cleaned up after test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def temp_tracker(temp_dir):
    """Create a temp tracker file with sample data."""
    tracker_dir = os.path.join(temp_dir, "applications")
    os.makedirs(tracker_dir)
    tracker_file = os.path.join(tracker_dir, "tracker.json")
    data = {
        "applications": [
            {
                "id": 1, "company": "Google", "role": "Lead QA",
                "platform": "LinkedIn", "status": "Applied",
                "is_product_company": True, "url": "https://example.com/1",
                "created_at": "2025-06-01T10:00:00",
            },
            {
                "id": 2, "company": "TCS", "role": "Test Lead",
                "platform": "Naukri", "status": "Screening",
                "is_product_company": False, "url": "https://example.com/2",
                "created_at": "2025-06-03T10:00:00",
            },
            {
                "id": 3, "company": "Microsoft", "role": "SDET",
                "platform": "LinkedIn", "status": "Interview",
                "is_product_company": True, "url": "https://example.com/3",
                "created_at": "2025-06-05T10:00:00",
            },
        ],
        "stats": {},
    }
    with open(tracker_file, "w") as f:
        json.dump(data, f)
    return tracker_file
