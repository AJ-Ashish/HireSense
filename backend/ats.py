"""
ats.py
Rule-based ATS (Applicant Tracking System) readiness score for a resume.

Why rule-based: real ATS software mostly checks structure and keywords, not
"meaning", so transparent rules explain a score better than another model
would. Every point lost maps to a specific tip the candidate can act on.

Scoring (100 points):
    Contact details   15   email, phone, LinkedIn/GitHub link
    Sections          25   experience, education, skills (+ projects)
    Skills breadth    15   how many recognised skills appear
    Impact            20   action verbs + quantified results
    Length            10   word count in a readable range
    Clarity           15   weak phrases, first-person pronouns, odd characters

Optionally pass the skills required by a job to also get a keyword check
for that job (reported separately, not part of the 100).
"""

import re

SECTION_PATTERNS = {
    "experience": r"^\s*(work\s+|professional\s+)?(experience|employment|internships?)\b",
    "education": r"^\s*(education|academic|qualifications?)\b",
    "skills": r"^\s*(technical\s+)?(skills|technologies|tech\s+stack|core\s+competencies)\b",
    "projects": r"^\s*(personal\s+|academic\s+)?projects?\b",
    "summary": r"^\s*(summary|profile|objective|about\s+me)\b",
    "certifications": r"^\s*(certifications?|courses|achievements|awards)\b",
}

ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "created", "led", "managed",
    "improved", "reduced", "increased", "optimized", "optimised", "launched",
    "automated", "analyzed", "analysed", "deployed", "engineered", "delivered",
    "architected", "integrated", "migrated", "trained", "mentored", "coordinated",
    "organized", "organised", "achieved", "established", "streamlined", "resolved",
    "collaborated", "researched", "tested", "maintained", "configured", "wrote",
}

WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "helped in", "duties included",
    "tasked with", "involved in", "assisted in", "familiar with",
]


def _lines(text):
    return [l.strip() for l in text.splitlines() if l.strip()]


def _has_section(lines, key):
    pat = re.compile(SECTION_PATTERNS[key], re.IGNORECASE)
    # Headings are short lines; this avoids matching a sentence that merely
    # starts with the word "projects".
    return any(len(l) <= 40 and pat.match(l) for l in lines)


def _strip_bullet(line):
    return re.sub(r"^[\u2022\u25cf\u25aa\-\*\u2013\u2014>\s]+", "", line)


def _category(key, label, max_points):
    return {"key": key, "label": label, "score": 0, "max": max_points, "good": [], "issues": []}


def _finish(cat):
    cat["score"] = max(0, min(cat["max"], round(cat["score"], 1)))
    return cat


def _check_contact(text):
    c = _category("contact", "Contact details", 15)
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        c["score"] += 6
        c["good"].append("Email address found")
    else:
        c["issues"].append(("Add an email address at the top of your resume.", 6))
    if re.search(r"(\+?\d[\d\s().-]{8,}\d)", text):
        c["score"] += 5
        c["good"].append("Phone number found")
    else:
        c["issues"].append(("Add a phone number so recruiters can reach you.", 5))
    if re.search(r"(linkedin\.com|github\.com)", text, re.IGNORECASE):
        c["score"] += 4
        c["good"].append("LinkedIn or GitHub link found")
    else:
        c["issues"].append(("Add your LinkedIn or GitHub profile link.", 4))
    return _finish(c)


def _check_sections(lines):
    c = _category("sections", "Standard sections", 25)
    required = [("experience", "Experience"), ("education", "Education"), ("skills", "Skills")]
    for key, name in required:
        if _has_section(lines, key):
            c["score"] += 7
            c["good"].append(f"{name} section found")
        else:
            c["issues"].append((f"Add a clearly labelled \"{name}\" section; ATS parsers look for these headings.", 7))
    if _has_section(lines, "projects"):
        c["score"] += 4
        c["good"].append("Projects section found")
    else:
        c["issues"].append(("Add a \"Projects\" section; it matters most when you have limited work experience.", 4))
    return _finish(c)


def _check_skills(skills_found):
    c = _category("skills", "Skills breadth", 15)
    n = len(skills_found)
    c["score"] = min(15, n / 10 * 15)
    if n >= 10:
        c["good"].append(f"{n} recognised skills listed")
    else:
        c["issues"].append((f"Only {n} recognised skill keywords found. List the tools and technologies you actually use (aim for 10 or more).", round(15 - c["score"], 1)))
    return _finish(c)


def _check_impact(lines):
    c = _category("impact", "Impact and results", 20)
    bullets = [_strip_bullet(l) for l in lines]

    verb_lines = 0
    for b in bullets:
        first = b.split(" ", 1)[0].lower().strip(",.:;")
        if first in ACTION_VERBS:
            verb_lines += 1
    verb_pts = min(10, verb_lines / 5 * 10)
    c["score"] += verb_pts
    if verb_lines >= 5:
        c["good"].append(f"{verb_lines} bullet points start with strong action verbs")
    else:
        c["issues"].append(("Start more bullet points with action verbs such as Built, Designed, Reduced, Led (aim for 5 or more).", round(10 - verb_pts, 1)))

    number_re = re.compile(r"\d+\s?%|\$\s?\d|\b\d+(\.\d+)?\s?(x|k|m|users|requests|ms|hours|days|people|members|clients)\b|\b\d{2,}\b", re.IGNORECASE)
    # Ignore lines that are mostly contact details or dates.
    quantified = [
        b for b in bullets
        if number_re.search(b) and not re.search(r"@|linkedin|github|\b(19|20)\d{2}\b\s*[-\u2013]", b, re.IGNORECASE)
    ]
    q_pts = min(10, len(quantified) / 3 * 10)
    c["score"] += q_pts
    if len(quantified) >= 3:
        c["good"].append(f"{len(quantified)} lines include numbers or measurable results")
    else:
        c["issues"].append(("Add measurable results, e.g. \"reduced load time by 40%\" or \"served 2,000 users\" (aim for 3 or more).", round(10 - q_pts, 1)))
    return _finish(c)


def _check_length(text):
    c = _category("length", "Length", 10)
    words = len(text.split())
    if 350 <= words <= 800:
        c["score"] = 10
        c["good"].append(f"{words} words, a good length")
    elif words < 350:
        c["score"] = max(0, words / 350 * 10)
        c["issues"].append((f"Your resume is short at {words} words. Add detail on projects, responsibilities and outcomes (aim for 350 to 800 words).", round(10 - c["score"], 1)))
    else:
        c["score"] = max(0, 10 - (words - 800) / 100)
        c["issues"].append((f"Your resume is long at {words} words. Trim it to the most relevant roles and projects (aim for under 800 words).", round(10 - c["score"], 1)))
    return _finish(c)


def _check_clarity(text):
    c = _category("clarity", "Clarity", 15)
    lower = text.lower()
    c["score"] = 15

    weak_found = [p for p in WEAK_PHRASES if p in lower]
    if weak_found:
        penalty = min(6, 2 * len(weak_found))
        c["score"] -= penalty
        shown = ", ".join(f"\"{p}\"" for p in weak_found[:3])
        c["issues"].append((f"Replace weak phrases like {shown} with direct action verbs.", penalty))
    else:
        c["good"].append("No weak filler phrases")

    pronouns = len(re.findall(r"\b(i|my|me)\b", lower))
    if pronouns > 3:
        penalty = min(4, pronouns / 2)
        c["score"] -= penalty
        c["issues"].append(("Remove first-person words (I, my, me). Resumes use implied first person.", round(penalty, 1)))
    else:
        c["good"].append("No first-person wording")

    odd = len(re.findall(r"[^\x00-\x7F\u2022\u2013\u2014\u2019\u201c\u201d]", text))
    if len(text) and odd / len(text) > 0.02:
        c["score"] -= 5
        c["issues"].append(("Many unusual characters or symbols were found. Icons, tables and graphics often break ATS parsing; use plain text.", 5))
    else:
        c["good"].append("Text extracts cleanly")
    return _finish(c)


def _grade(score):
    if score >= 80:
        return "Strong"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Needs work"
    return "Weak"


def analyze(resume_text, skills_found, job_skills=None):
    """
    resume_text   full text of the resume
    skills_found  set of recognised skills found in the resume (ranker.extract_skills)
    job_skills    optional set of skills required by a job

    Returns {score, grade, categories, tips, job_keywords}
    """
    lines = _lines(resume_text)
    categories = [
        _check_contact(resume_text),
        _check_sections(lines),
        _check_skills(skills_found),
        _check_impact(lines),
        _check_length(resume_text),
        _check_clarity(resume_text),
    ]

    total = round(sum(c["score"] for c in categories))

    all_issues = []
    for c in categories:
        for text, lost in c["issues"]:
            all_issues.append({"tip": text, "points": lost, "category": c["label"]})
    all_issues.sort(key=lambda i: i["points"], reverse=True)

    # Expose issues as plain strings per category, with the ranked list separate.
    for c in categories:
        c["issues"] = [text for text, _ in c["issues"]]

    job_keywords = None
    if job_skills:
        matched = sorted(set(job_skills) & set(skills_found))
        missing = sorted(set(job_skills) - set(skills_found))
        job_keywords = {
            "percent": round(len(matched) / len(job_skills) * 100),
            "matched": matched,
            "missing": missing,
        }

    return {
        "score": total,
        "grade": _grade(total),
        "categories": categories,
        "tips": all_issues[:6],
        "job_keywords": job_keywords,
    }
