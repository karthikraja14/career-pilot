"""
YOUR RESUME DATA — Edit this file with your own details.
This file is gitignored. Your personal data stays local.

Copy from resume_data.example.py and fill in your info.
The resume builder imports from this file.
"""

RESUME_DATA = {
    "name": "YOUR NAME",
    "title": "Your Title | Your Specialty",
    "contact": {
        "phone": "(+91) XXXXXXXXXX",
        "email": "your.email@example.com",
        "linkedin": "linkedin.com/in/your-profile",
        "location": "City, Country",
    },
    "summary": (
        "Experienced professional with X years of expertise in [your domain]. "
        "Fill in your own professional summary highlighting key achievements "
        "and the value you bring."
    ),
    "skills": {
        "Core Skills": "Skill 1, Skill 2, Skill 3, Skill 4",
        "Programming": "Language 1, Language 2, Language 3",
        "Tools & Platforms": "Tool 1, Tool 2, Tool 3, Tool 4",
        "Methodologies": "Methodology 1, Methodology 2",
    },
    "experience": [
        {
            "period": "Jan 2023 -- Present",
            "role": "Your Current Role",
            "company": "Company Name",
            "bullets": [
                "Describe your key achievement with quantified results.",
                "Another achievement showing leadership and impact.",
                "Technical contribution with measurable outcome.",
            ],
        },
        {
            "period": "Jan 2020 -- Dec 2022",
            "role": "Your Previous Role",
            "company": "Previous Company",
            "bullets": [
                "Describe your responsibilities and achievements.",
                "Include metrics where possible (e.g., 'Reduced X by 40%').",
            ],
        },
    ],
    "achievements": [
        "Key achievement #1 with quantified impact.",
        "Key achievement #2 with quantified impact.",
    ],
    "education": [
        {"degree": "Your Degree", "year": "20XX", "institution": "Your University"},
    ],
    "languages": ["English"],
}
