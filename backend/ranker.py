"""
ranker.py
Core scoring engine: sentence embeddings + cosine similarity, plus
keyword-based skill extraction for explainability.

Two interchangeable embedding backends, chosen with EMBEDDING_BACKEND:

  local   sentence-transformers model running on this machine (default).
          Best on a laptop. Needs torch, which is heavy (about 500 MB of RAM).
  gemini  Google's Gemini embeddings API over HTTPS. Needs no AI libraries,
          so it fits easily on a small free server such as Render's free plan.
          Uses the same GEMINI_API_KEY as the career assistant.

Everything else (skills, must-have scoring, caching) is identical for both.
"""

import os
import re
import time
import threading
from functools import lru_cache

import numpy as np
import requests

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L3-v2"

# Local model files are kept inside the project (backend/models).
MODEL_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

GEMINI_BATCH_SIZE = 50        # texts per request (the API accepts up to 100)
MAX_EMBED_CHARS = 6000        # keeps each text under the API's input limit

_model = None
_model_lock = threading.Lock()


class EmbeddingError(Exception):
    """The AI matching step failed. The message is safe to show to the user."""


def embedding_backend() -> str:
    backend = os.environ.get("EMBEDDING_BACKEND", "local").strip().lower()
    return backend if backend in ("local", "gemini") else "local"


def get_model():
    """Load the local sentence-transformers model (local backend only)."""
    global _model

    if _model is None:
        with _model_lock:  # the warm-up thread and a user request may arrive together
            if _model is None:
                import torch
                from sentence_transformers import SentenceTransformer

                torch.set_num_threads(1)
                model = SentenceTransformer(
                    MODEL_NAME,
                    device="cpu",
                    cache_folder=MODEL_CACHE_DIR,
                )
                model.max_seq_length = 256
                model.eval()
                _model = model

    return _model


COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql", "nosql",
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "linux",
    "html", "css", "rest api", "graphql", "mongodb", "postgresql", "mysql",
    "data analysis", "data visualization", "excel", "power bi", "tableau",
    "communication", "leadership", "project management", "agile", "scrum",
]


def extract_skills(text: str) -> set:
    text_lower = text.lower()
    found = set()

    for skill in COMMON_SKILLS:
        pattern = (
            r"(?<![a-zA-Z0-9])"
            + re.escape(skill)
            + r"(?![a-zA-Z0-9])"
        )

        if re.search(pattern, text_lower):
            found.add(skill)

    return found


def _encode_local(texts: list[str]):
    """Normalized embeddings from the local model."""
    try:
        import torch
        model = get_model()
    except ImportError:
        raise EmbeddingError(
            "The local AI model is not installed. Install requirements-local.txt, "
            "or set EMBEDDING_BACKEND=gemini."
        )

    with torch.inference_mode():
        embeddings = model.encode(
            texts,
            batch_size=1,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    return embeddings


def _post_with_retry(url: str, key: str, body: dict, tries: int = 3) -> dict:
    """POST to Gemini. Retries busy / rate-limited replies with a short wait."""
    last = "network problem"
    for attempt in range(tries):
        try:
            r = requests.post(
                url,
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
        except requests.exceptions.RequestException:
            last = "network problem"
        else:
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                last = "the Gemini free limit was reached" if r.status_code == 429 else f"service busy ({r.status_code})"
            else:
                raise EmbeddingError(
                    f"Gemini rejected the matching request (error {r.status_code}). "
                    "Please check that GEMINI_API_KEY is correct."
                )
        time.sleep(1.5 * (2 ** attempt))
    raise EmbeddingError(f"The AI matching service is busy right now ({last}). Please try again in a minute.")


def _encode_gemini(texts: list[str]):
    """Normalized embeddings from the Gemini embeddings API."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key or key == "your_gemini_api_key_here":
        raise EmbeddingError("GEMINI_API_KEY is not set, so AI matching cannot run.")

    model = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"

    vectors = []
    for i in range(0, len(texts), GEMINI_BATCH_SIZE):
        batch = texts[i:i + GEMINI_BATCH_SIZE]
        body = {"requests": [
            {
                "model": f"models/{model}",
                "content": {"parts": [{"text": (t[:MAX_EMBED_CHARS] or " ")}]},
                "taskType": "SEMANTIC_SIMILARITY",
                "outputDimensionality": 768,
            }
            for t in batch
        ]}
        data = _post_with_retry(url, key, body)
        embeddings = data.get("embeddings") or []
        if len(embeddings) != len(batch):
            raise EmbeddingError("The AI matching service sent an unexpected reply. Please try again.")
        vectors.extend(e["values"] for e in embeddings)

    arr = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms   # normalized, so dot product = cosine similarity


def _encode(texts: list[str]):
    """Embeddings for a list of texts using the chosen backend."""
    if embedding_backend() == "gemini":
        return _encode_gemini(texts)
    return _encode_local(texts)


def _calibrate(similarity: float) -> float:
    """
    Optional rescaling of raw cosine similarity, set with SIM_LOW and SIM_HIGH.
    Different embedding models give different raw ranges (for example 0.3 to 0.6
    for one and 0.6 to 0.9 for another). Mapping the real range to 0..1 keeps
    the match percentage meaningful. Defaults (0 and 1) change nothing.
    """
    try:
        low = float(os.environ.get("SIM_LOW", "0"))
        high = float(os.environ.get("SIM_HIGH", "1"))
    except ValueError:
        return similarity
    if (low, high) == (0.0, 1.0) or high <= low:
        return similarity
    return min(1.0, max(0.0, (similarity - low) / (high - low)))


@lru_cache(maxsize=512)
def _embed_one(text: str):
    """
    Embedding for one text, remembered in memory. Browsing jobs scores one resume
    against every open job, so without this the same resume (and the same job
    descriptions) would be re-embedded on every page load. Results are identical.
    """
    return _encode([text])[0]


def combine_score(semantic: float, job_skills: set, resume_skills: set, must_have: set) -> float:
    """
    Blend meaning similarity with skill coverage when HR has marked must-have skills.

        weighted coverage = (2 x must-haves matched + nice-to-haves matched)
                            / (2 x must-haves total  + nice-to-haves total)
        final score       = semantic x (0.6 + 0.4 x weighted coverage)

    Full coverage keeps the semantic score as it is; no coverage keeps 60% of it,
    so a resume missing the required skills sinks in the ranking. If the job has
    no must-have skills the semantic score is returned unchanged (old behaviour).
    """
    must = set(must_have) & set(job_skills)
    if not must:
        return semantic
    nice = set(job_skills) - must
    total = 2 * len(must) + len(nice)
    got = 2 * len(must & resume_skills) + len(nice & resume_skills)
    coverage = got / total
    # max(..., 0): a negative similarity times a penalty would wrongly move the score up.
    return round(max(semantic, 0) * (0.6 + 0.4 * coverage), 2)


def score_resume(job_description: str, resume_text: str, must_have=None) -> dict:
    """
    Score a single resume against a single job description.

    must_have: optional list of skills HR marked as required for this job.

    Returns:
        {
            "score": float,                 # final score (uses must-haves if given)
            "semantic_score": float,        # meaning similarity only
            "matched_skills": list[str],
            "missing_skills": list[str],
            "missing_must_have": list[str]  # required skills the resume lacks
        }
    """
    # With normalized embeddings, cosine similarity equals dot product.
    similarity = _calibrate(float(_embed_one(job_description) @ _embed_one(resume_text)))
    semantic = round(similarity * 100, 2)

    jd_skills = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)

    matched = sorted(jd_skills & resume_skills)
    missing = sorted(jd_skills - resume_skills)
    must = set(must_have or []) & jd_skills

    return {
        "score": combine_score(semantic, jd_skills, resume_skills, must),
        "semantic_score": semantic,
        "matched_skills": matched,
        "missing_skills": missing,
        "missing_must_have": sorted(must - resume_skills),
    }


def rank_resumes(
    job_description: str,
    resumes: list[dict],
    must_have=None,
) -> list[dict]:
    """
    Batch version (used by HR bulk screening).

    resumes = [{"id": ..., "filename": ..., "text": ...}, ...]
    must_have = optional list of required skills for the job

    Returns resumes augmented with score / semantic_score / matched_skills /
    missing_skills / missing_must_have, sorted by score descending.
    """
    if not resumes:
        return []

    jd_embedding = _embed_one(job_description)
    resume_embeddings = _encode([r["text"] for r in resumes])

    # Normalized vectors -> dot product = cosine similarity.
    similarities = resume_embeddings @ jd_embedding

    jd_skills = extract_skills(job_description)
    must = set(must_have or []) & jd_skills

    results = []
    for i, resume in enumerate(resumes):
        resume_skills = extract_skills(resume["text"])
        semantic = round(_calibrate(float(similarities[i])) * 100, 2)
        results.append({
            **resume,
            "score": combine_score(semantic, jd_skills, resume_skills, must),
            "semantic_score": semantic,
            "matched_skills": sorted(jd_skills & resume_skills),
            "missing_skills": sorted(jd_skills - resume_skills),
            "missing_must_have": sorted(must - resume_skills),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
