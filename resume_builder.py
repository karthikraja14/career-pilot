#!/usr/bin/env python3
"""
Resume Builder -- ATS-optimized single-column professional PDF resume.

Setup:
  1. Copy resume_data.example.py â†’ resume_data.py
  2. Fill in your details in resume_data.py
  3. Run:  python resume_builder.py
  4. Output: output/Resume.pdf
"""

import os
import sys
from datetime import datetime

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("Install fpdf2:  pip install fpdf2")

try:
    from resume_data import RESUME_DATA
except ImportError:
    print("Error: resume_data.py not found.")
    print("Copy resume_data.example.py to resume_data.py and fill in your details.")
    sys.exit(1)


# =====================================================================
# LAYOUT CONSTANTS
# =====================================================================

PAGE_W, PAGE_H = 210, 297          # A4 mm
MARGIN_L = 15
MARGIN_R = 15
MARGIN_T = 12
MARGIN_B = 12
BODY_W = PAGE_W - MARGIN_L - MARGIN_R

# Colours
HEADER_BG   = (25, 60, 82)        # dark navy
ACCENT      = (25, 60, 82)        # section headings
BODY_TEXT   = (40, 40, 40)
MUTED_TEXT  = (100, 100, 100)
LINE_COLOR  = (25, 60, 82)
WHITE       = (255, 255, 255)


# =====================================================================
# PDF GENERATOR  --  ATS-friendly single-column layout
# =====================================================================

class ATSResumePDF(FPDF):
    """Clean single-column resume optimised for ATS parsing."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=MARGIN_B)

    @staticmethod
    def safe(text: str) -> str:
        reps = {
            "\u2014": "--", "\u2013": "-", "\u2022": "-",
            "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2026": "...", "\u2018": "'", "\u00b7": "-",
            "\u25cf": "-", "\u2192": "->",
        }
        for o, n in reps.items():
            text = text.replace(o, n)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # -- Section heading with underline --
    def section_heading(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*ACCENT)
        self.cell(BODY_W, 6, self.safe(title.upper()))
        self.ln(6)
        self.set_draw_color(*LINE_COLOR)
        self.set_line_width(0.5)
        self.line(MARGIN_L, self.get_y(), PAGE_W - MARGIN_R, self.get_y())
        self.ln(2)

    # -- Bullet point --
    def bullet(self, text, indent=3, size=8.5, line_h=4.0):
        x = self.get_x() + indent
        self.set_font("Helvetica", "", size)
        self.set_text_color(*BODY_TEXT)
        self.set_x(x)
        self.cell(3, line_h, "-")
        self.set_x(x + 4)
        self.multi_cell(BODY_W - indent - 5, line_h, self.safe(text))
        self.ln(0.5)


def build_resume(data: dict, output_path: str) -> str:
    """Build an ATS-optimised single-column PDF resume."""
    pdf = ATSResumePDF()
    pdf.set_margins(MARGIN_L, MARGIN_T, MARGIN_R)
    pdf.add_page()

    # =================================================================
    # HEADER  --  Name, Title, Contact
    # =================================================================
    hdr_h = 30
    pdf.set_fill_color(*HEADER_BG)
    pdf.rect(0, 0, PAGE_W, hdr_h, "F")

    # Name
    pdf.set_xy(MARGIN_L, 6)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*WHITE)
    pdf.cell(BODY_W, 8, pdf.safe(data["name"]))

    # Title
    pdf.set_xy(MARGIN_L, 16)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 215, 225)
    pdf.cell(BODY_W, 5, pdf.safe(data["title"]))

    # Contact line
    c = data["contact"]
    contact_line = (
        f"{c['phone']}  |  {c['email']}  |  {c['linkedin']}  |  "
        f"{c['location']}"
    )
    pdf.set_xy(MARGIN_L, 23)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(180, 200, 215)
    pdf.cell(BODY_W, 4, pdf.safe(contact_line))

    pdf.set_y(hdr_h + 4)

    # =================================================================
    # PROFESSIONAL SUMMARY
    # =================================================================
    pdf.section_heading("Professional Summary")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*BODY_TEXT)
    pdf.multi_cell(BODY_W, 4.0, pdf.safe(data["summary"]))

    # =================================================================
    # TECHNICAL SKILLS  (grouped, comma-separated -- ATS-parseable)
    # =================================================================
    pdf.section_heading("Technical Skills")
    for category, skills_text in data["skills"].items():
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*ACCENT)
        cat_w = pdf.get_string_width(category + ":  ") + 2
        pdf.cell(cat_w, 4.2, pdf.safe(category + ":"))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*BODY_TEXT)
        pdf.multi_cell(BODY_W - cat_w, 4.2, pdf.safe(skills_text))
        pdf.ln(0.8)

    # =================================================================
    # WORK EXPERIENCE
    # =================================================================
    pdf.section_heading("Work Experience")

    for job in data["experience"]:
        # Role + Period on one line
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT)
        role_w = pdf.get_string_width(job["role"]) + 2
        pdf.cell(role_w, 5, pdf.safe(job["role"]))
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*MUTED_TEXT)
        pdf.cell(BODY_W - role_w, 5, pdf.safe(job["period"]), align="R")
        pdf.ln(5)

        # Company
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*MUTED_TEXT)
        pdf.cell(BODY_W, 4, pdf.safe(job["company"]))
        pdf.ln(5)

        # Bullets
        for bullet_text in job["bullets"]:
            pdf.bullet(bullet_text)

        pdf.ln(2)

    # =================================================================
    # KEY ACHIEVEMENTS
    # =================================================================
    pdf.section_heading("Key Achievements")
    for ach in data["achievements"]:
        pdf.bullet(ach)

    # =================================================================
    # EDUCATION
    # =================================================================
    pdf.section_heading("Education")
    for edu in data["education"]:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*BODY_TEXT)
        deg_w = pdf.get_string_width(edu["degree"]) + 2
        pdf.cell(deg_w, 4.5, pdf.safe(edu["degree"]))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*MUTED_TEXT)
        pdf.cell(BODY_W - deg_w, 4.5,
                 pdf.safe(f"  --  {edu['institution']}  ({edu['year']})"))
        pdf.ln(5.5)

    # =================================================================
    # LANGUAGES
    # =================================================================
    pdf.section_heading("Languages")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*BODY_TEXT)
    pdf.cell(BODY_W, 5, pdf.safe("  |  ".join(data["languages"])))

    # ---- Save ----
    pdf.output(output_path)
    return output_path


# =====================================================================
# ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    output_file = "output/Resume.pdf"

    print("\n" + "=" * 50)
    print("  ATS-OPTIMISED RESUME BUILDER")
    print("=" * 50)
    build_resume(RESUME_DATA, output_file)

    size_kb = os.path.getsize(output_file) / 1024
    print(f"\n  Resume saved : {output_file}")
    print(f"  File size    : {size_kb:.1f} KB")
    print(f"\n  Ready to upload to any company portal!")
    print()
