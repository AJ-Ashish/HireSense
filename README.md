# HireSense — AI Resume Ranking Platform

A two-role platform where HR teams post jobs and get AI-ranked applicants,
and candidates browse jobs, apply, and get resume feedback — all powered by
sentence-embedding based semantic matching.

## Features

**HR side**
- Sign up / log in as an HR user
- Post job openings, and close/reopen them once filled
- **Must-have skills**: the system detects skills in the job description and HR ticks the required ones; resumes missing them rank lower and get a red tag
- View applicants per job, automatically ranked by match score
- See matched/missing skills per applicant for explainability
- Add private notes per applicant (e.g. interview impressions)
- Shortlist or reject applicants (candidates see the status update)
- Filter applicants to only those who meet every must-have skill
- Export the ranked applicant list as a CSV file
- **Bulk screening**: upload up to 25 resumes (PDF/DOCX/TXT) for one job and get them ranked instantly, with CSV export (results are not saved)
- Analytics dashboard: score distribution + most common missing skills across all applicants

**Candidate side**
- Sign up / log in as a candidate
- Upload a resume once (PDF/DOCX/TXT)
- Browse all open jobs with an instant match % against your resume
- Apply to jobs with one click
- Track application status (In review / Shortlisted / Rejected)
- **Status timeline and notifications**: each application shows a timeline (Applied, In review, Shortlisted or Not selected, with dates). When HR changes a status, the candidate sees a red badge on My Applications and a "Recent updates" list
- **ATS score**: a 0-100 readiness score for your resume with a breakdown (contact details, sections, skills, impact, length, clarity), a ranked "what to fix first" list, and an optional keyword check against any job you applied to
- **Learning roadmap**: an ordered, phase-by-phase plan to close skill gaps (prerequisites first, with time estimates, practice tasks and free resources), for all applied jobs or any single job
- Get personalized feedback: which in-demand skills are missing from your resume,
  each paired with curated free YouTube videos and documentation to learn them
- **Career Assistant chatbot**: paste any job description and ask what skills it
  requires, or have an open conversation about your resume and job search —
  powered by Google's free Gemini API

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Auth | JWT (PyJWT) + bcrypt password hashing (passlib) |
| NLP / Matching | Embeddings + cosine similarity with an in-memory cache. Two backends, chosen by `EMBEDDING_BACKEND`: `local` (sentence-transformers, for your laptop) or `gemini` (Gemini embeddings API, light, used on Render) |
| Resume parsing | pdfplumber, python-docx |
| Database | PostgreSQL (Neon) |
| Frontend | HTML/CSS/vanilla JS (no build step) |
| Charts | Chart.js |
| Deployment | Render |

## Project structure

```
resume-ranker-v2/
├── backend/
│   ├── main.py         # FastAPI app + all API routes
│   ├── auth.py          # password hashing + JWT
│   ├── database.py      # PostgreSQL schema + queries
│   ├── parser.py         # resume text extraction
│   ├── ranker.py          # embeddings + scoring
│   ├── ats.py              # rule-based ATS resume score
│   ├── roadmap.py           # learning roadmap builder (prerequisites + phases)
│   ├── resources.py        # curated free learning resources per skill
│   ├── chatbot.py           # Gemini API integration for the career assistant
│   ├── .env.example          # template for GEMINI_API_KEY + DATABASE_URL + JWT_SECRET
│   └── requirements.txt
├── frontend/
│   └── index.html         # full single-page app (auth + both dashboards)
├── uploads/                 # temp storage during resume processing
├── requirements.txt          # root copy for Render's build
├── render.yaml                # Render Blueprint for the web service
└── README.md
```

## Why PostgreSQL instead of SQLite

The original version used SQLite — a single file on disk. That broke in
production: Render's free web services have **no persistent disk**, so every
time the service restarted (idle timeout, redeploy, etc.), the SQLite file
was wiped and recreated empty. That's why job postings, accounts, and
applications kept disappearing without warning.

PostgreSQL is a real, separately-hosted database that survives restarts.
This project uses **[Neon](https://neon.tech)** — a Postgres provider with a
genuinely permanent free tier (no card, no expiration clock), which matters
if your submission is weeks or months away. Render also offers its own
free Postgres, but that one **expires 30 days after creation**, which is too
short for most project timelines — so Neon is used instead, and connected in
via the same `DATABASE_URL` environment variable either way.

## Setting up the database (Neon PostgreSQL)

1. Go to [console.neon.tech/signup](https://console.neon.tech/signup) and sign
   up with Google or GitHub — no credit card required
2. Neon creates a project and a database automatically. On your project's
   dashboard, find the **connection string** (labeled "Connection string" or
   similar) — it looks like: `postgresql://user:password@host/dbname?sslmode=require`
3. Copy that connection string — you'll use it in two places:
   - **Locally:** in `backend/`, copy `.env.example` to `.env` and paste it in as `DATABASE_URL`
   - **On Render:** add it as the `DATABASE_URL` environment variable (see deployment steps below)

This one Neon database can be reused for both local development and your
deployed Render service — they'll share the same data, which is actually
convenient for testing.

## Setting up the Career Assistant chatbot (Gemini API)



## Running locally

```bash
cd resume-ranker-v2
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements-local.txt    # full install with the local AI model
# (or: pip install -r requirements.txt and set EMBEDDING_BACKEND=gemini in backend/.env)

cd backend
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`. You'll land on the login screen.

**To test the full flow:**
1. Click "Create an account" → choose "I'm hiring (HR)" → sign up
2. Post a job (e.g. title "Backend Engineer", description mentioning Python/FastAPI/SQL)
3. Log out, sign up again as "I'm job hunting" (candidate) — use a different email
4. Upload a resume (any PDF/DOCX/TXT with some skills mentioned)
5. Go to "Browse Jobs" → you'll see your match % → click "Apply now"
6. Log back in as the HR account → "Job Postings" → "View applicants" → see the ranked applicant, shortlist them
7. Log back in as the candidate → "My Applications" → see the status changed to "Shortlisted"

> With `EMBEDDING_BACKEND=local` the first start downloads the embedding model into `backend/models/` (once). With `EMBEDDING_BACKEND=gemini` nothing is downloaded and no heavy AI libraries are needed.

**Tuning match percentages:** different embedding models give different raw similarity ranges. Run `python calibrate.py sample_job.txt <folder of resumes>` inside `backend/` and put the suggested `SIM_LOW` and `SIM_HIGH` in `.env` (and in Render's Environment tab).

## Deploying to Render

1. Push this project to a GitHub repo (see commands below)
2. Go to [render.com](https://render.com) → **New +** → **Blueprint** → connect your repo
3. Render reads `render.yaml` (it sets `EMBEDDING_BACKEND=gemini`, generates `JWT_SECRET` for you, and installs only the light packages, so it fits Render's free 512 MB) and will ask you to fill in two values it
   intentionally left blank (secrets never live in the file itself):
   - `DATABASE_URL` — paste your Neon connection string (see above)
   - `GEMINI_API_KEY` — paste your Gemini key
4. Click **Apply** and wait for the build to finish
5. Your live URL (e.g. `https://hiresense.onrender.com`) is your submission link

> If Render doesn't prompt you for those two values during setup, you can
> always add them afterward: go to the `hiresense` service → **Environment** →
> add `DATABASE_URL` and `GEMINI_API_KEY` there.

> Free tier note: the web service sleeps after 15 minutes of inactivity and
> takes ~30-60 seconds to wake up on the next request — open the link a
> minute before your demo. This no longer causes data loss (that was the
> SQLite problem) — it's now just a slow first load. Your Neon database stays
> alive and persistent regardless of whether the web service is asleep.

**If you already have an existing Render web service from before:** you can
reuse it — just go to its Environment tab and add `DATABASE_URL` (your Neon
connection string) and confirm `GEMINI_API_KEY` is still set, then trigger a
manual redeploy so it picks up the new `database.py` code.

## Pushing to GitHub

```bash
cd resume-ranker-v2
git init
git add .
git commit -m "HireSense: full two-role platform with auth, ranking, and analytics"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## Notes for your report / viva

- The JWT secret is read from the `JWT_SECRET` environment variable (never hardcoded)
- Final score with must-have skills: `meaning score x (0.6 + 0.4 x weighted skill coverage)`, where must-haves count double; with no must-haves it is the plain embedding similarity
- The ranking core (embeddings + cosine similarity) is unchanged from the
  single-user version — it's just now called once per application instead
  of once per batch upload, and results are persisted per job/candidate pair
- The project originally used SQLite and was migrated to PostgreSQL after
  discovering that Render's free web services have no persistent disk —
  a good real-world lesson about ephemeral vs. persistent storage worth
  mentioning if asked
