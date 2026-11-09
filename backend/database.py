"""
database.py
PostgreSQL storage for the full two-role system: users, job postings, applications.

Migrated from SQLite: SQLite's file lived on Render's ephemeral disk, which is
wiped on every restart/redeploy — so all data (accounts, job postings,
applications) disappeared unpredictably. PostgreSQL is a real, persistent
database that survives restarts.

Requires the DATABASE_URL environment variable (see .env.example and README).
"""

import json
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to your .env file (see .env.example) "
            "for local development, or as an environment variable on Render "
            "(from your Postgres instance's connection string), then restart the server."
        )
    kwargs = {"cursor_factory": RealDictCursor}
    if "sslmode" not in DATABASE_URL:
        kwargs["sslmode"] = "require"
    return psycopg2.connect(DATABASE_URL, **kwargs)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('hr', 'candidate')),
            company TEXT,
            resume_text TEXT,
            resume_filename TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id SERIAL PRIMARY KEY,
            hr_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL REFERENCES job_postings(id),
            candidate_id INTEGER NOT NULL REFERENCES users(id),
            score REAL NOT NULL,
            matched_skills TEXT NOT NULL,
            missing_skills TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'review',
            notes TEXT DEFAULT '',
            applied_at TEXT NOT NULL,
            UNIQUE(job_id, candidate_id)
        )
    """)

    # Migration safety net: if an older deploy already has the applications
    # table without a notes column, add it. Harmless no-op otherwise.
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'applications'
    """)
    existing_cols = [row["column_name"] for row in cur.fetchall()]
    if "notes" not in existing_cols:
        cur.execute("ALTER TABLE applications ADD COLUMN notes TEXT DEFAULT ''")

    # Migration: must-have skills chosen by HR (stored as a JSON list).
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'job_postings'
    """)
    job_cols = [row["column_name"] for row in cur.fetchall()]
    if "must_have_skills" not in job_cols:
        cur.execute("ALTER TABLE job_postings ADD COLUMN must_have_skills TEXT DEFAULT '[]'")

    # History of every status an application has been in. Drives the timeline
    # and the candidate's notifications (seen = FALSE means unread).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS application_events (
            id SERIAL PRIMARY KEY,
            application_id INTEGER NOT NULL REFERENCES applications(id),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            seen BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    # Backfill: applications created before this feature get one "applied"
    # event so their timeline is not empty. Harmless no-op afterwards.
    cur.execute("""
        INSERT INTO application_events (application_id, status, created_at, seen)
        SELECT a.id, 'applied', a.applied_at, TRUE FROM applications a
        WHERE NOT EXISTS (SELECT 1 FROM application_events e WHERE e.application_id = a.id)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL REFERENCES users(id),
            role TEXT NOT NULL CHECK(role IN ('user', 'model')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# ---------- Users ----------

def create_user(name, email, password_hash, role, company=None) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (name, email, password_hash, role, company, created_at)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (name, email, password_hash, role, company, datetime.utcnow().isoformat()),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_candidate_resume(user_id: int, resume_text: str, resume_filename: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET resume_text = %s, resume_filename = %s WHERE id = %s",
        (resume_text, resume_filename, user_id),
    )
    conn.commit()
    conn.close()


# ---------- Job postings ----------

def _decode_job(row) -> dict:
    """Turn a job row into a dict with must_have_skills as a real list."""
    d = dict(row)
    try:
        d["must_have_skills"] = json.loads(d.get("must_have_skills") or "[]")
    except (TypeError, ValueError):
        d["must_have_skills"] = []
    return d


def create_job(hr_id: int, title: str, description: str, must_have_skills=None) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO job_postings (hr_id, title, description, status, created_at, must_have_skills)
               VALUES (%s, %s, %s, 'open', %s, %s) RETURNING id""",
            (hr_id, title, description, datetime.utcnow().isoformat(), json.dumps(must_have_skills or [])),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id
    finally:
        conn.close()


def get_jobs_by_hr(hr_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) AS applicant_count
        FROM job_postings j WHERE j.hr_id = %s ORDER BY j.created_at DESC
    """, (hr_id,))
    rows = cur.fetchall()
    conn.close()
    return [_decode_job(r) for r in rows]


def get_all_open_jobs():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT j.*, u.company, u.name AS hr_name
        FROM job_postings j JOIN users u ON j.hr_id = u.id
        WHERE j.status = 'open' ORDER BY j.created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [_decode_job(r) for r in rows]


def get_job_by_id(job_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM job_postings WHERE id = %s", (job_id,))
    row = cur.fetchone()
    conn.close()
    return _decode_job(row) if row else None


def update_job_status(job_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE job_postings SET status = %s WHERE id = %s", (status, job_id))
    conn.commit()
    conn.close()


# ---------- Applications ----------

def create_application(job_id, candidate_id, score, matched_skills, missing_skills) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO applications (job_id, candidate_id, score, matched_skills, missing_skills, status, applied_at)
            VALUES (%s, %s, %s, %s, %s, 'review', %s) RETURNING id
        """, (job_id, candidate_id, score, json.dumps(matched_skills), json.dumps(missing_skills),
              datetime.utcnow().isoformat()))
        new_id = cur.fetchone()["id"]
        # first step of the timeline: the candidate applied (already seen, so no notification)
        cur.execute("""
            INSERT INTO application_events (application_id, status, created_at, seen)
            VALUES (%s, 'applied', %s, TRUE)
        """, (new_id, datetime.utcnow().isoformat()))
        conn.commit()
        return new_id
    finally:
        conn.close()


def get_applications_for_job(job_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.*, u.name AS candidate_name, u.email AS candidate_email
        FROM applications a JOIN users u ON a.candidate_id = u.id
        WHERE a.job_id = %s ORDER BY a.score DESC
    """, (job_id,))
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["matched_skills"] = json.loads(d["matched_skills"])
        d["missing_skills"] = json.loads(d["missing_skills"])
        results.append(d)
    return results


def get_applications_for_candidate(candidate_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.*, j.title AS job_title, u.company
        FROM applications a
        JOIN job_postings j ON a.job_id = j.id
        JOIN users u ON j.hr_id = u.id
        WHERE a.candidate_id = %s ORDER BY a.applied_at DESC
    """, (candidate_id,))
    rows = cur.fetchall()
    ids = [r["id"] for r in rows]
    timelines = {i: [] for i in ids}
    if ids:
        cur.execute("""
            SELECT application_id, status, created_at FROM application_events
            WHERE application_id = ANY(%s) ORDER BY created_at, id
        """, (ids,))
        for e in cur.fetchall():
            timelines[e["application_id"]].append({"status": e["status"], "at": e["created_at"]})
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["matched_skills"] = json.loads(d["matched_skills"])
        d["missing_skills"] = json.loads(d["missing_skills"])
        d["timeline"] = timelines[d["id"]]
        results.append(d)
    return results


def get_application_by_job_and_candidate(job_id: int, candidate_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE job_id = %s AND candidate_id = %s", (job_id, candidate_id))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_application_status(application_id: int, status: str) -> bool:
    """Returns True if the status changed (and an unread event was recorded)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM applications WHERE id = %s", (application_id,))
        row = cur.fetchone()
        if not row or row["status"] == status:
            return False
        cur.execute("UPDATE applications SET status = %s WHERE id = %s", (status, application_id))
        cur.execute("""
            INSERT INTO application_events (application_id, status, created_at, seen)
            VALUES (%s, %s, %s, FALSE)
        """, (application_id, status, datetime.utcnow().isoformat()))
        conn.commit()
        return True
    finally:
        conn.close()


def get_notifications(candidate_id: int, limit: int = 20):
    """Recent status changes on this candidate's applications (the initial
    'applied' event is not a notification)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.application_id, e.status, e.created_at, e.seen,
               j.title AS job_title, u.company
        FROM application_events e
        JOIN applications a ON e.application_id = a.id
        JOIN job_postings j ON a.job_id = j.id
        JOIN users u ON j.hr_id = u.id
        WHERE a.candidate_id = %s AND e.status <> 'applied'
        ORDER BY e.created_at DESC, e.id DESC LIMIT %s
    """, (candidate_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    cur.execute("""
        SELECT COUNT(*) AS n FROM application_events e
        JOIN applications a ON e.application_id = a.id
        WHERE a.candidate_id = %s AND e.status <> 'applied' AND e.seen = FALSE
    """, (candidate_id,))
    unread = cur.fetchone()["n"]
    conn.close()
    return {"unread": unread, "items": rows}


def mark_notifications_read(candidate_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE application_events SET seen = TRUE
        WHERE seen = FALSE AND application_id IN
              (SELECT id FROM applications WHERE candidate_id = %s)
    """, (candidate_id,))
    conn.commit()
    conn.close()


def update_application_notes(application_id: int, notes: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET notes = %s WHERE id = %s", (notes, application_id))
    conn.commit()
    conn.close()


def get_application_owner_job(application_id: int):
    """Returns the hr_id who owns the job this application belongs to (for permission checks)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT j.hr_id FROM applications a JOIN job_postings j ON a.job_id = j.id WHERE a.id = %s
    """, (application_id,))
    row = cur.fetchone()
    conn.close()
    return row["hr_id"] if row else None


# ---------- Analytics ----------

def get_hr_analytics(hr_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.score, a.missing_skills FROM applications a
        JOIN job_postings j ON a.job_id = j.id WHERE j.hr_id = %s
    """, (hr_id,))
    rows = cur.fetchall()
    conn.close()

    scores = [r["score"] for r in rows]
    skill_counts = {}
    for r in rows:
        for skill in json.loads(r["missing_skills"]):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for s in scores:
        if s <= 20: buckets["0-20"] += 1
        elif s <= 40: buckets["21-40"] += 1
        elif s <= 60: buckets["41-60"] += 1
        elif s <= 80: buckets["61-80"] += 1
        else: buckets["81-100"] += 1

    top_missing = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_applicants": len(scores),
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "score_distribution": buckets,
        "top_missing_skills": [{"skill": k, "count": v} for k, v in top_missing],
    }


def get_candidate_feedback(candidate_id: int):
    """Aggregate missing skills across all of a candidate's applications."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT missing_skills, matched_skills FROM applications WHERE candidate_id = %s", (candidate_id,))
    rows = cur.fetchall()
    conn.close()

    missing_counts = {}
    matched_set = set()
    for r in rows:
        for skill in json.loads(r["missing_skills"]):
            missing_counts[skill] = missing_counts.get(skill, 0) + 1
        for skill in json.loads(r["matched_skills"]):
            matched_set.add(skill)

    top_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)
    return {
        "strong_skills": sorted(matched_set),
        "suggested_skills": [{"skill": k, "appears_in_n_jobs": v} for k, v in top_missing],
    }


# ---------- Chat (candidate chatbot) ----------

def save_chat_message(candidate_id: int, role: str, content: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_messages (candidate_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
            (candidate_id, role, content, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_chat_history(candidate_id: int, limit: int = 20):
    """Returns the most recent `limit` messages, oldest first (ready for the API)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE candidate_id = %s ORDER BY id DESC LIMIT %s",
        (candidate_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in reversed(rows)]


def clear_chat_history(candidate_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_messages WHERE candidate_id = %s", (candidate_id,))
    conn.commit()
    conn.close()
