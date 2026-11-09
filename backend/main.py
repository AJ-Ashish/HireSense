"""
main.py
FastAPI backend for HireSense — a two-role (HR / Candidate) resume ranking platform.

Auth:
    POST /api/auth/signup
    POST /api/auth/login
    GET  /api/auth/me

HR endpoints (role=hr):
    POST /api/jobs                        create a job posting
    GET  /api/jobs                        list my job postings
    GET  /api/jobs/{job_id}/applicants    ranked applicants for a job
    PATCH /api/applications/{app_id}/status   shortlist/reject an applicant
    GET  /api/analytics                   aggregate stats across my postings

Candidate endpoints (role=candidate):
    POST /api/candidate/resume            upload/replace resume
    GET  /api/jobs/public                 browse open jobs (with match % if resume on file)
    POST /api/jobs/detect-skills           skills found in a description (HR picks must-haves)
    POST /api/jobs/{job_id}/apply          apply to a job
    GET  /api/candidate/applications       my application history (with status timeline)
    GET  /api/candidate/notifications      recent status changes + unread count
    POST /api/candidate/notifications/read mark all notifications as read
    GET  /api/candidate/feedback           aggregated skill-gap feedback
    GET  /api/candidate/ats                ATS readiness score (optional ?job_id= for job keywords)
    GET  /api/candidate/roadmap            learning roadmap (optional ?job_id= for one job)
    GET  /api/candidate/open-jobs          light list of open jobs (for the roadmap dropdown)
    POST /api/jobs/{job_id}/bulk-rank      HR: upload many resumes, get them ranked (not saved)
"""

import os
import re
import threading
import shutil
import uuid
import csv
import io

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr

import database as db
import auth
from parser import extract_text, clean_text
from ranker import score_resume, rank_resumes, get_model, extract_skills, embedding_backend, EmbeddingError
from roadmap import build_roadmap
import ats
from resources import get_resources_for_skill
import chatbot

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="HireSense")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(EmbeddingError)
async def embedding_error_handler(request, exc: EmbeddingError):
    """AI matching failed (Gemini busy, key wrong...). Show a clear message, not a crash."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def _warm_model():
    """Load the local AI model in the background so the first real request is not slow."""
    if embedding_backend() != "local":
        return  # the Gemini backend has nothing to load
    try:
        get_model()
        print("AI model ready.")
    except Exception as e:  # never stop the app from starting because of this
        print("Model warm-up failed (it will load on first use):", e)


@app.on_event("startup")
def startup():
    db.init_db()
    threading.Thread(target=_warm_model, daemon=True).start()


@app.get("/api/config")
def public_config():
    """Non-sensitive settings the web page needs."""
    return {"max_bulk_files": max_bulk_files(), "embedding_backend": embedding_backend()}


@app.get("/health")
def health():
    return {"status": "ok"}


# ==================== Schemas ====================

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # "hr" or "candidate"
    company: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class JobCreateRequest(BaseModel):
    title: str
    description: str
    must_have_skills: list[str] = []


class DetectSkillsRequest(BaseModel):
    description: str


class StatusUpdateRequest(BaseModel):
    status: str  # "shortlisted" | "rejected" | "review"


class NotesUpdateRequest(BaseModel):
    notes: str


class JobStatusUpdateRequest(BaseModel):
    status: str  # "open" | "closed"


class ChatRequest(BaseModel):
    message: str


# ==================== Auth ====================

@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    if payload.role not in ("hr", "candidate"):
        raise HTTPException(status_code=400, detail="Role must be 'hr' or 'candidate'.")

    if db.get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    password_hash = auth.hash_password(payload.password)
    user_id = db.create_user(payload.name, payload.email, password_hash, payload.role, payload.company)
    token = auth.create_access_token(user_id, payload.role)

    return {"token": token, "user": {"id": user_id, "name": payload.name, "role": payload.role, "email": payload.email}}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    user = db.get_user_by_email(payload.email)
    if not user or not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = auth.create_access_token(user["id"], user["role"])
    return {
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "role": user["role"], "email": user["email"]},
    }


@app.get("/api/auth/me")
def me(current_user: dict = Depends(auth.get_current_user)):
    user = db.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "id": user["id"], "name": user["name"], "email": user["email"],
        "role": user["role"], "company": user["company"],
        "has_resume": bool(user["resume_text"]),
    }


# ==================== HR endpoints ====================

@app.post("/api/jobs")
def create_job(payload: JobCreateRequest, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    # Keep only must-haves that really appear in the description.
    detected = extract_skills(payload.description)
    must_have = sorted({s.strip().lower() for s in payload.must_have_skills} & detected)
    job_id = db.create_job(current_user["user_id"], payload.title, payload.description, must_have)
    return {"job_id": job_id, "must_have_skills": must_have}


@app.post("/api/jobs/detect-skills")
def detect_job_skills(payload: DetectSkillsRequest, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    return {"skills": sorted(extract_skills(payload.description))}


@app.get("/api/jobs")
def list_my_jobs(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    return db.get_jobs_by_hr(current_user["user_id"])


@app.get("/api/jobs/{job_id}/applicants")
def get_applicants(job_id: int, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    job = db.get_job_by_id(job_id)
    if not job or job["hr_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Job not found.")
    must = set(job.get("must_have_skills") or [])
    applicants = db.get_applications_for_job(job_id)
    for a in applicants:
        a["must_have"] = sorted(must)
        a["missing_must_have"] = [s for s in a["missing_skills"] if s in must]
    return applicants


MAX_BULK_FILE_BYTES = 5 * 1024 * 1024


def max_bulk_files() -> int:
    """Smaller batches with the Gemini backend, to stay inside its free per-minute limits."""
    return 10 if embedding_backend() == "gemini" else 25


def _guess_name(text: str, filename: str) -> str:
    """Best-effort candidate name: a short first line without symbols, else the file name."""
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    if first and len(first) <= 40 and "@" not in first and len(first.split()) <= 5 \
            and sum(c.isdigit() for c in first) <= 2:
        return first
    return os.path.splitext(filename)[0]


@app.post("/api/jobs/{job_id}/bulk-rank")
def bulk_rank(job_id: int, files: list[UploadFile] = File(...), current_user: dict = Depends(auth.get_current_user)):
    """Rank many uploaded resumes against one job. Results are returned, not saved."""
    auth.require_role(current_user, "hr")
    job = db.get_job_by_id(job_id)
    if not job or job["hr_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Job not found.")
    if len(files) > max_bulk_files():
        raise HTTPException(status_code=400, detail=f"Please upload at most {max_bulk_files()} resumes at a time.")

    resumes, errors = [], []
    for i, f in enumerate(files):
        name = f.filename or f"file-{i + 1}"
        ext = os.path.splitext(name)[1].lower()
        if ext not in (".pdf", ".docx", ".txt"):
            errors.append({"filename": name, "error": "Unsupported file type (use PDF, DOCX or TXT)."})
            continue
        temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
        try:
            size = 0
            with open(temp_path, "wb") as out:
                while True:
                    chunk = f.file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BULK_FILE_BYTES:
                        raise ValueError("File is larger than 5 MB.")
                    out.write(chunk)
            text = clean_text(extract_text(temp_path))
            if not text:
                raise ValueError("No extractable text found (scanned image?).")
            resumes.append({"filename": name, "text": text})
        except Exception as e:
            errors.append({"filename": name, "error": str(e)})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    ranked = rank_resumes(job["description"], resumes, job.get("must_have_skills"))
    results = []
    for r in ranked:
        text = r.pop("text")
        email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        r["name"] = _guess_name(text, r["filename"])
        r["email"] = email.group(0) if email else ""
        results.append(r)

    return {
        "job_title": job["title"],
        "must_have": job.get("must_have_skills") or [],
        "results": results,
        "errors": errors,
    }


@app.patch("/api/applications/{application_id}/status")
def update_status(application_id: int, payload: StatusUpdateRequest, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    if payload.status not in ("review", "shortlisted", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be review, shortlisted, or rejected.")

    owner_id = db.get_application_owner_job(application_id)
    if owner_id is None or owner_id != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Application not found.")

    db.update_application_status(application_id, payload.status)
    return {"success": True}


@app.patch("/api/applications/{application_id}/notes")
def update_notes(application_id: int, payload: NotesUpdateRequest, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    owner_id = db.get_application_owner_job(application_id)
    if owner_id is None or owner_id != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Application not found.")

    db.update_application_notes(application_id, payload.notes)
    return {"success": True}


@app.patch("/api/jobs/{job_id}/status")
def update_job_status(job_id: int, payload: JobStatusUpdateRequest, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    if payload.status not in ("open", "closed"):
        raise HTTPException(status_code=400, detail="Status must be 'open' or 'closed'.")

    job = db.get_job_by_id(job_id)
    if not job or job["hr_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Job not found.")

    db.update_job_status(job_id, payload.status)
    return {"success": True}


@app.get("/api/jobs/{job_id}/applicants/export")
def export_applicants_csv(job_id: int, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    job = db.get_job_by_id(job_id)
    if not job or job["hr_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Job not found.")

    applicants = db.get_applications_for_job(job_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Rank", "Candidate Name", "Email", "Score", "Matched Skills", "Missing Skills", "Status", "Notes", "Applied At"])
    for i, a in enumerate(applicants, start=1):
        writer.writerow([
            i, a["candidate_name"], a["candidate_email"], a["score"],
            "; ".join(a["matched_skills"]), "; ".join(a["missing_skills"]),
            a["status"], a.get("notes", ""), a["applied_at"],
        ])
    buffer.seek(0)

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in job["title"])
    filename = f"applicants_{safe_title}.csv".replace(" ", "_")

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/analytics")
def analytics(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "hr")
    return db.get_hr_analytics(current_user["user_id"])


# ==================== Candidate endpoints ====================

@app.post("/api/candidate/resume")
async def upload_resume(resume: UploadFile = File(...), current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")

    ext = os.path.splitext(resume.filename)[1].lower()
    if ext not in (".pdf", ".docx", ".txt"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    try:
        text = clean_text(extract_text(temp_path))
    except Exception as e:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Failed to read resume: {str(e)}")
    os.remove(temp_path)

    if not text:
        raise HTTPException(status_code=400, detail="No extractable text found in the resume.")

    db.update_candidate_resume(current_user["user_id"], text, resume.filename)
    return {"success": True, "filename": resume.filename}


@app.get("/api/jobs/public")
def browse_jobs(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    jobs = db.get_all_open_jobs()

    user = db.get_user_by_id(current_user["user_id"])
    resume_text = user["resume_text"]

    result = []
    for job in jobs:
        entry = {**job}
        if resume_text:
            scored = score_resume(job["description"], resume_text, job.get("must_have_skills"))
            entry["match_score"] = scored["score"]
            entry["missing_must_have"] = scored["missing_must_have"]
        else:
            entry["match_score"] = None
            entry["missing_must_have"] = []
        already_applied = db.get_application_by_job_and_candidate(job["id"], current_user["user_id"])
        entry["already_applied"] = already_applied is not None
        result.append(entry)

    result.sort(key=lambda j: (j["match_score"] is None, -(j["match_score"] or 0)))
    return result


@app.post("/api/jobs/{job_id}/apply")
def apply_to_job(job_id: int, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")

    job = db.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    user = db.get_user_by_id(current_user["user_id"])
    if not user["resume_text"]:
        raise HTTPException(status_code=400, detail="Please upload your resume before applying.")

    if db.get_application_by_job_and_candidate(job_id, current_user["user_id"]):
        raise HTTPException(status_code=400, detail="You've already applied to this job.")

    scored = score_resume(job["description"], user["resume_text"], job.get("must_have_skills"))
    app_id = db.create_application(
        job_id, current_user["user_id"], scored["score"], scored["matched_skills"], scored["missing_skills"]
    )
    return {"application_id": app_id, "score": scored["score"]}


@app.get("/api/candidate/applications")
def my_applications(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    return db.get_applications_for_candidate(current_user["user_id"])


@app.get("/api/candidate/notifications")
def my_notifications(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    return db.get_notifications(current_user["user_id"])


@app.post("/api/candidate/notifications/read")
def read_notifications(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    db.mark_notifications_read(current_user["user_id"])
    return {"success": True}


@app.get("/api/candidate/feedback")
def my_feedback(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    feedback = db.get_candidate_feedback(current_user["user_id"])
    for item in feedback["suggested_skills"]:
        item["resources"] = get_resources_for_skill(item["skill"])
    return feedback


@app.get("/api/candidate/ats")
def my_ats_score(job_id: int | None = None, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    user = db.get_user_by_id(current_user["user_id"])
    if not user["resume_text"]:
        raise HTTPException(status_code=400, detail="Upload your resume first to get an ATS score.")

    job_skills = None
    job_title = None
    if job_id is not None:
        job = db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        job_skills = extract_skills(job["description"])
        job_title = job["title"]

    result = ats.analyze(user["resume_text"], extract_skills(user["resume_text"]), job_skills)
    result["job_title"] = job_title
    return result


@app.get("/api/candidate/open-jobs")
def open_jobs_list(current_user: dict = Depends(auth.get_current_user)):
    """Cheap list of open jobs. No scoring, so it is fast (unlike /api/jobs/public)."""
    auth.require_role(current_user, "candidate")
    return [{"id": j["id"], "title": j["title"], "company": j.get("company")} for j in db.get_all_open_jobs()]


@app.get("/api/candidate/roadmap")
def my_roadmap(job_id: int | None = None, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    user = db.get_user_by_id(current_user["user_id"])
    if not user["resume_text"]:
        raise HTTPException(status_code=400, detail="Upload your resume first to get a learning roadmap.")
    have = extract_skills(user["resume_text"])

    if job_id is not None:
        job = db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        missing = [(s, 1) for s in sorted(extract_skills(job["description"]) - have)]
        return build_roadmap(missing, have, get_resources_for_skill, job["title"], job_mode=True)

    feedback = db.get_candidate_feedback(current_user["user_id"])
    missing = [(i["skill"], i["appears_in_n_jobs"]) for i in feedback["suggested_skills"]]
    return build_roadmap(missing, have, get_resources_for_skill, "All your applications")


@app.post("/api/candidate/chat")
def send_chat_message(payload: ChatRequest, current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    user = db.get_user_by_id(current_user["user_id"])
    history = db.get_chat_history(current_user["user_id"], limit=20)

    try:
        reply = chatbot.chat(message, history, user["resume_text"])
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    db.save_chat_message(current_user["user_id"], "user", message)
    db.save_chat_message(current_user["user_id"], "model", reply)

    return {"reply": reply}


@app.get("/api/candidate/chat/history")
def get_chat_history(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    return db.get_chat_history(current_user["user_id"], limit=50)


@app.delete("/api/candidate/chat/history")
def clear_chat(current_user: dict = Depends(auth.get_current_user)):
    auth.require_role(current_user, "candidate")
    db.clear_chat_history(current_user["user_id"])
    return {"success": True}


# Serve frontend as static files (single deployable service)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
