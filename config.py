"""
Configuration for Career Pilot — Resume Builder & Job Auto-Apply Suite.
Customize everything below to match YOUR target roles and preferences.
"""

# â”€â”€â”€ Job Search Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

JOB_SEARCH_CONFIG = {
    "target_roles": [
        "Lead Test Engineer",
        "Test Architect",
        "QA Manager",
        "Quality Engineering Lead",
        "Automation Test Lead",
        "SDET Lead",
        "Test Engineering Manager",
        "Principal QA Engineer",
        "Staff QA Engineer",
        "Director of Quality Engineering",
    ],
    "experience_years": 10,
    "preferred_locations": ["Bangalore", "Chennai", "Hyderabad", "Pune", "Remote"],
    "domains": ["Healthcare", "MedTech", "Fintech", "SaaS", "Cloud", "AI/ML"],
    "remote_ok": True,
}

# â”€â”€â”€ Product-Based Companies (Preferred) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

PRODUCT_COMPANIES = [
    # â”€â”€ Healthcare / MedTech / Medical Devices (YOUR DOMAIN â€” searched first) â”€â”€
    "Philips", "Siemens Healthineers", "GE HealthCare",
    "Medtronic", "Abbott", "Boston Scientific", "Stryker", "Baxter",
    "Edwards Lifesciences", "Intuitive Surgical", "Becton Dickinson",
    "Zimmer Biomet", "Smith & Nephew", "Hologic", "ResMed", "Danaher",
    "Roche", "Alcon", "Olympus", "Hillrom", "Getinge", "Terumo",
    "Cook Medical", "Cardinal Health", "Henry Schein", "Masimo",
    "Insulet", "Integra LifeSciences", "NuVasive", "Penumbra",
    "Globus Medical", "Teleflex", "ICU Medical", "Merit Medical",
    "Fresenius Medical Care", "DaVita", "Elekta", "Varian",
    # Pharma / Life Sciences
    "Pfizer", "Novartis", "AstraZeneca", "Sanofi", "GSK",
    "Merck", "Eli Lilly", "Amgen", "Gilead Sciences", "Regeneron",
    "Bristol Myers Squibb", "Takeda", "Bayer", "Novo Nordisk",
    "AbbVie", "Biogen", "Moderna", "BioNTech", "Genentech",
    # Health Tech / Digital Health
    "Optum", "UnitedHealth Group", "Cerner", "Epic Systems", "Veeva Systems",
    "IQVIA", "Tempus", "Flatiron Health", "Doximity", "Teladoc",
    "Practo", "1mg", "PharmEasy", "Pristyn Care", "MFine",
    "Niramai", "Qure.ai", "SigTuple", "Dozee", "HealthifyMe",
    "Ekincare", "Innovaccer", "CureFit", "Portea Medical",

    # â”€â”€ Big Tech â”€â”€
    "Google", "Microsoft", "Amazon", "Apple", "Meta",
    "Netflix", "Uber", "Airbnb", "Stripe", "Spotify",

    # â”€â”€ Indian Product Companies â”€â”€
    "Flipkart", "Swiggy", "Zomato", "PhonePe", "Razorpay",
    "Freshworks", "Zoho", "Postman", "BrowserStack", "Hasura",
    "Cashfree", "Chargebee", "Clevertap", "Cred", "Dream11",
    "Groww", "Jupiter", "Meesho", "Nykaa", "Ola",
    "ShareChat", "Slice", "Udaan", "Zerodha",

    # â”€â”€ Enterprise / SaaS â”€â”€
    "Atlassian", "Salesforce", "ServiceNow", "Workday",
    "Confluent", "Databricks", "HashiCorp", "Snowflake",
    "Twilio", "Palo Alto Networks", "CrowdStrike",
    "VMware", "Adobe", "Intuit", "Informatica",
    "SAP", "Oracle", "IBM", "Cisco", "Dell Technologies",

    # â”€â”€ Fintech â”€â”€
    "PayPal", "Visa", "Mastercard", "Goldman Sachs",
    "JPMorgan Chase", "Morgan Stanley",
]

# â”€â”€â”€ Service Companies (Fallback) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SERVICE_COMPANIES = [
    "TCS", "Infosys", "Wipro", "HCLTech", "Tech Mahindra",
    "Cognizant", "Accenture", "Capgemini", "Deloitte", "EY",
    "KPMG", "PwC", "LTIMindtree", "Mphasis", "Hexaware",
    "Persistent Systems", "Cyient", "EPAM Systems", "ThoughtWorks",
]

# â”€â”€â”€ Trending Skills (2025-2026) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TRENDING_SKILLS = {
    "Testing": [
        "selenium", "playwright", "cypress", "appium",
        "testng", "junit", "pytest", "robot framework",
        "rest assured", "postman", "k6", "jmeter", "gatling",
        "grafana", "api testing", "performance testing",
        "mobile testing", "security testing",
    ],
    "Programming": [
        "python", "java", "javascript", "typescript",
        "sql", "shell scripting", "groovy", "c#",
    ],
    "CI/CD & DevOps": [
        "jenkins", "github actions", "gitlab ci", "azure devops",
        "docker", "kubernetes", "terraform", "ansible",
        "aws", "azure", "gcp",
    ],
    "Tools": [
        "jira", "confluence", "git", "bitbucket",
        "sonarqube", "allure", "extent reports",
        "browserstack", "sauce labs", "testrail",
    ],
    "Methodologies": [
        "agile", "scrum", "kanban", "safe",
        "devops", "shift-left testing", "continuous testing",
        "tdd", "bdd", "risk-based testing",
    ],
    "AI/ML": [
        "ai testing", "ml model testing", "llm",
        "generative ai", "copilot", "prompt engineering",
        "ai test generation", "chatgpt",
    ],
}

# â”€â”€â”€ Resume Scoring Weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SCORING_WEIGHTS = {
    "completeness": 0.20,
    "ats_compatibility": 0.20,
    "impact_statements": 0.25,
    "skills_relevance": 0.20,
    "structure": 0.15,
}

GRADE_THRESHOLDS = {
    "A+": 95, "A": 90, "B+": 85, "B": 80,
    "C+": 75, "C": 70, "D+": 65, "D": 60,
    "E": 50, "F": 0,
}

# â”€â”€â”€ Expected Resume Sections â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

EXPECTED_SECTIONS = [
    "contact", "summary", "experience", "education",
    "skills", "projects", "certifications", "achievements",
]

OPTIONAL_SECTIONS = ["publications", "volunteer", "languages"]

# â”€â”€â”€ Action Verbs for Impact Statements â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

ACTION_VERBS = [
    "led", "managed", "developed", "designed", "implemented",
    "delivered", "optimized", "automated", "architected",
    "spearheaded", "established", "launched", "reduced",
    "improved", "increased", "streamlined", "built",
    "created", "mentored", "coordinated", "orchestrated",
    "transformed", "migrated", "integrated", "scaled",
]

WEAK_PHRASES = [
    "involved in", "responsible for", "worked on",
    "helped with", "assisted in", "participated in",
    "was part of", "exposure to", "good knowledge of",
]
