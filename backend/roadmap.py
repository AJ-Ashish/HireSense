"""
roadmap.py
Turns a list of missing skills into an ordered learning roadmap.

Idea: some skills must be learned before others (FastAPI needs Python,
Kubernetes needs Docker). We add any missing prerequisite, work out how deep
each skill sits in that chain, and group skills into phases:

    depth 0  -> Phase: Foundations
    depth 1  -> Phase: Core skills
    depth 2+ -> Phase: Advanced and tools

Inside a phase the skills that appear in the most jobs come first.
Time estimates are rough guesses for a beginner studying part-time, not facts.
"""

# skill -> skills that should be learned first (names match ranker.COMMON_SKILLS)
PREREQS = {
    "fastapi": ["python"], "flask": ["python"], "django": ["python"],
    "pandas": ["python"], "numpy": ["python"], "scikit-learn": ["python", "pandas"],
    "machine learning": ["python"], "deep learning": ["machine learning"],
    "nlp": ["machine learning"], "computer vision": ["deep learning"],
    "tensorflow": ["deep learning"], "pytorch": ["deep learning"],
    "data visualization": ["data analysis"], "power bi": ["data analysis"], "tableau": ["data analysis"],
    "javascript": ["html", "css"], "react": ["javascript"], "angular": ["javascript"],
    "vue": ["javascript"], "typescript": ["javascript"], "node.js": ["javascript"],
    "graphql": ["rest api"], "kubernetes": ["docker"], "mongodb": ["nosql"],
    "postgresql": ["sql"], "mysql": ["sql"], "scrum": ["agile"],
}

# Rough weeks for a beginner (default is 2; soft skills 3).
WEEKS = {
    "python": 4, "java": 5, "javascript": 4, "typescript": 2, "c++": 5, "c#": 5,
    "sql": 3, "nosql": 2, "html": 1, "css": 2, "git": 1, "linux": 2, "excel": 2,
    "machine learning": 5, "deep learning": 5, "nlp": 4, "computer vision": 4,
    "react": 4, "angular": 4, "vue": 3, "node.js": 3, "django": 3, "flask": 2, "fastapi": 2,
    "docker": 2, "kubernetes": 3, "aws": 4, "azure": 4, "gcp": 4,
    "communication": 3, "leadership": 3, "project management": 3,
}

# One concrete thing to build, so the skill ends up on the resume with proof.
PRACTICE = {
    "python": "Write 5 small scripts, such as a file organiser and a quiz game.",
    "sql": "Design a 3-table database and write queries with JOIN and GROUP BY.",
    "javascript": "Build a to-do app that saves items and filters them.",
    "html": "Build a one-page personal portfolio.",
    "css": "Make your portfolio responsive for phones and laptops.",
    "git": "Put a project on GitHub and make commits on a feature branch.",
    "react": "Build a small dashboard that loads data from an API.",
    "fastapi": "Create a REST API with 4 endpoints and a database.",
    "flask": "Create a small web app with a form and a database.",
    "django": "Build a blog with login and an admin panel.",
    "pandas": "Clean and analyse a dataset from Kaggle and write 5 findings.",
    "numpy": "Rewrite a loop-based calculation using arrays and compare speed.",
    "machine learning": "Train a classifier on a Kaggle dataset and report accuracy.",
    "deep learning": "Train a small neural network to recognise handwritten digits.",
    "nlp": "Build a text classifier, for example spam or sentiment detection.",
    "docker": "Containerise one of your projects and run it with docker run.",
    "kubernetes": "Deploy your container on a local cluster with minikube.",
    "aws": "Host a small app on a free-tier EC2 instance or S3 bucket.",
    "docker compose": "Run an app and its database together with Compose.",
    "rest api": "Design and document a CRUD API, then test it with Postman.",
    "postgresql": "Move a project from SQLite to PostgreSQL.",
    "mongodb": "Store and query JSON documents for a small app.",
    "data analysis": "Answer 5 business questions from a sales dataset.",
    "data visualization": "Make a dashboard of 4 charts that tells a clear story.",
    "tableau": "Publish a dashboard from a public dataset.",
    "power bi": "Build a report with 3 visuals and a slicer.",
    "excel": "Build a sheet with pivot tables, lookups and a chart.",
    "agile": "Run a 1-week sprint with your team and write a retro.",
    "communication": "Record a 2-minute explanation of your best project.",
    "leadership": "Lead a small team project and document who did what.",
}

PHASE_NAMES = ["Foundations", "Core skills", "Advanced and tools"]


def _depth(skill, plan, memo):
    """Length of the longest prerequisite chain below this skill (inside the plan)."""
    if skill in memo:
        return memo[skill]
    memo[skill] = 0  # guards against accidental cycles
    parents = [p for p in PREREQS.get(skill, []) if p in plan]
    memo[skill] = 1 + max(_depth(p, plan, memo) for p in parents) if parents else 0
    return memo[skill]


def build_roadmap(missing, have, get_resources, target_label, job_mode=False):
    """
    missing        list of (skill, jobs_count) the candidate lacks
    have           set of skills already on the resume
    get_resources  function skill -> list of {title, url, type}
    target_label   text shown at the top, e.g. "Backend Engineer"
    job_mode       True when the roadmap is for one job (changes the wording)
    """
    plan = {skill: count for skill, count in missing if skill not in have}

    # Pull in prerequisites the candidate lacks, even if no job named them.
    needed_for = {}
    queue = list(plan)
    while queue:
        skill = queue.pop()
        for pre in PREREQS.get(skill, []):
            if pre in have:
                continue
            needed_for.setdefault(pre, []).append(skill)
            if pre not in plan:
                plan[pre] = 0
                queue.append(pre)

    memo = {}
    phases = {0: [], 1: [], 2: []}
    for skill, count in plan.items():
        depth = _depth(skill, plan, memo)
        level = min(depth, 2)
        if count > 0:
            reason = ("Required for this job." if job_mode
                      else f"Appears in {count} job{'s' if count != 1 else ''} you applied to.")
        else:
            reason = "Learn this first: " + ", ".join(sorted(needed_for.get(skill, []))) + " builds on it."
        phases[level].append({
            "skill": skill,
            "reason": reason,
            "is_prerequisite": count == 0,
            "weeks": WEEKS.get(skill, 2),
            "practice": PRACTICE.get(skill, f"Build one small project that uses {skill} and add it to your resume."),
            "resources": get_resources(skill),
            "_count": count,
            "_depth": depth,
        })

    out = []
    for level in (0, 1, 2):
        # Prerequisites first (depth), then the skills asked for most often.
        steps = sorted(phases[level], key=lambda s: (s["_depth"], -s["_count"], s["skill"]))
        for s in steps:
            del s["_count"], s["_depth"]
        if steps:
            out.append({"name": PHASE_NAMES[level], "steps": steps})
    for i, phase in enumerate(out, start=1):
        phase["name"] = f"Phase {i}: {phase['name']}"

    return {
        "target": target_label,
        "skill_count": len(plan),
        "total_weeks": sum(s["weeks"] for p in out for s in p["steps"]),
        "phases": out,
    }
