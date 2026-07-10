# Career Pilot ✈️

**Your autopilot for job applications.** Build ATS-optimized resumes, tailor them per JD, auto-apply on LinkedIn & Naukri, and track everything — from the terminal.

Works for **any role**: engineering, product, design, data, marketing, finance, or anything else. Just configure your target roles in `config.py` and go.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-121%20passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAREER PILOT                             │
├────────────┬────────────┬────────────┬────────────┬────────────┤
│  PREPARE   │   MATCH    │   APPLY    │   TRACK    │  RESEARCH  │
├────────────┼────────────┼────────────┼────────────┼────────────┤
│ Resume PDF │ Job Finder │ LinkedIn   │ Dashboard  │ Salary     │
│ DOCX Export│ JD Scorer  │ Naukri     │ Version    │ Connections│
│ Analyzer   │ Keyword Gap│ Easy Apply │ History    │ Duplicates │
│ Tailorer   │ Cover Ltrs │ External   │ Stats      │            │
└────────────┴────────────┴────────────┴────────────┴────────────┘
```

**The flow:**

1. **Build** your resume once → generates ATS-friendly PDF/DOCX
2. **Analyze** it → get a score (0-100) with fix suggestions
3. **Find jobs** → scrapes LinkedIn, scores JDs against your profile
4. **Tailor** → paste a JD, get a customized resume + cover letter
5. **Apply** → bot auto-fills forms, uploads resume, submits
6. **Track** → dashboard shows funnel, stats, timeline, version history

---

## Features

### 📄 Resume Tools
| Feature | What it does |
|---------|-------------|
| **Resume Builder** | Generates ATS-friendly single-column PDF from a Python data file |
| **DOCX Export** | Word document version for portals that reject PDFs |
| **Resume Analyzer** | Scores across 5 dimensions, gives letter grade + fix suggestions |
| **JD Tailorer** | Extracts JD keywords → reorders skills/bullets → generates tailored PDF |
| **Cover Letter** | Template-based generation with JD keyword injection |
| **ATS Keyword Gap** | Shows exactly which ATS keywords you're missing vs. a JD |

### 🤖 Auto-Apply
| Feature | What it does |
|---------|-------------|
| **LinkedIn Bot** | Easy Apply automation with form filling + resume upload |
| **Naukri Bot** | Quick Apply automation with questionnaire handling |
| **Job Finder** | Scrapes LinkedIn for jobs at product companies, scores each JD (0-100) |
| **Safety System** | Rate limits, CAPTCHA detection, cooldowns, daily caps |

### 📊 Tracking & Research
| Feature | What it does |
|---------|-------------|
| **HTML Dashboard** | Dark-themed visual report: funnel, timeline, platform breakdown |
| **Version Tracker** | Logs which resume was sent to which company |
| **Duplicate Detection** | Warns if you've already applied to the same company |
| **Salary Research** | One-click URLs for Levels.fyi, Glassdoor, AmbitionBox, etc. |
| **Connection Finder** | LinkedIn People Search URLs for networking at target companies |

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/karthikraja14/career-pilot.git
cd career-pilot
pip install -r requirements.txt
npx playwright install chromium
```

### 2. Configure

```bash
cp resume_data.example.py resume_data.py     # Your resume content
cp data/answers.example.json data/answers.json  # Your form answers
```

Edit both files with your real details. They are **gitignored** — never pushed.

Customize target roles and companies in `config.py`.

### 3. Run

```bash
python main.py          # Interactive menu with all features
```

---

## Usage Examples

```bash
# Resume
python resume_builder.py                    # Generate PDF
python docx_export.py                       # Generate DOCX
python main.py analyze                      # Score your resume

# JD-specific
python jd_tailorer.py --jd-file jd.txt      # Tailored resume
python cover_letter.py --company "Google" --role "Software Engineer"
python keyword_gap.py --jd-file jd.txt      # ATS gap analysis

# Auto-apply
python -m apply.run linkedin                # LinkedIn Easy Apply
python -m apply.run naukri                  # Naukri Quick Apply
python -m apply.run linkedin --product      # Product companies only
python -m apply.run linkedin --companies "Google,Microsoft"

# Job finder
python -m apply.finder                      # Interactive job discovery
python -m apply.finder --location Bangalore --min-score 50

# Tracking & research
python dashboard.py                         # Open visual dashboard
python salary_lookup.py "Google" "SDE"      # Salary research
python connection_finder.py "Microsoft"     # Find people to connect with
python -m pytest tests/ -v                  # Run 121 tests
```

---

## Project Structure

```
career-pilot/
├── main.py                     # Interactive menu (entry point)
├── resume_builder.py           # PDF resume generator
├── resume_data.example.py      # Template for your resume data
├── resume_analyzer.py          # Resume scoring engine
├── jd_tailorer.py              # JD keyword extraction + tailoring
├── cover_letter.py             # Cover letter generator
├── keyword_gap.py              # ATS keyword gap analysis
├── dashboard.py                # HTML dashboard generator
├── docx_export.py              # DOCX export
├── version_tracker.py          # Resume version history
├── salary_lookup.py            # Salary research URLs
├── connection_finder.py        # LinkedIn connection URLs
├── job_matcher.py              # Job search plan + tracker
├── config.py                   # Your target roles, companies, skills
├── requirements.txt            # Python deps
├── package.json                # Playwright dep
├── apply/
│   ├── run.py                  # Auto-apply orchestrator
│   ├── linkedin.py             # LinkedIn bot
│   ├── naukri.py               # Naukri bot
│   ├── finder.py               # Job finder + JD scorer
│   ├── base.py                 # Browser setup & form helpers
│   └── safety.py               # Rate limiting & safety
├── tests/                      # 121 tests (pytest)
├── data/
│   └── answers.example.json    # Template for form answers
├── output/                     # Generated files (gitignored)
└── reports/                    # Analysis reports (gitignored)
```

---

## Safety & Anti-Detection

The auto-apply system is designed to keep your accounts safe:

| Protection | Implementation |
|-----------|---------------|
| Daily caps | 10 LinkedIn + 12 Naukri (hard limits, never exceeded) |
| Human timing | Random delays between every click, keystroke, and scroll |
| Real browser | Visible Chromium with persistent profile (not headless) |
| CAPTCHA stop | Instantly stops if CAPTCHA or "verify" challenge appears |
| Account safety | Stops on restriction/suspension detection |
| Cooldown | 48-hour pause triggered on any platform warning |
| Session limit | Max 2 hours per session, 3 consecutive errors = stop |
| No re-apply | Tracks all applied URLs, skips duplicates |

---

## Tech Stack

- **Python 3.10+** — Core logic
- **Playwright** — Browser automation (Chromium)
- **fpdf2** — PDF generation
- **pdfplumber** — PDF text extraction
- **python-docx** — DOCX export
- **Chart.js** — Dashboard charts (CDN, no build step)
- **pytest** — Test framework (121 tests)

---

## Contributing

1. Fork the repo
2. Create your branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support the Project

If this tool helped you land interviews or save hours of manual applications, consider buying me a coffee ☕

<a href="https://buymeacoffee.com/karthikraja14">
  <img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=☕&slug=karthikraja14&button_colour=FFDD00&font_colour=000000&font_family=Poppins&outline_colour=000000&coffee_colour=ffffff" />
</a>

**Other ways to support:**
- ⭐ Star this repo — helps others discover it
- 🐛 Report bugs or suggest features via [Issues](../../issues)
- 🔀 Contribute code via Pull Requests
- 📣 Share with friends who are job hunting
- 🌐 Check out more tools at [karthikraja.in](https://karthikraja.in)

---

## Disclaimer

This tool automates job applications using browser automation. Use responsibly and in compliance with each platform's Terms of Service. The authors are not responsible for any account restrictions resulting from usage.

---

## License

MIT — see [LICENSE](LICENSE)
