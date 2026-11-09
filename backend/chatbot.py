"""
chatbot.py
Integration with Google's Gemini API (free tier) to power the candidate
career-assistant chatbot.

Uses the "gemini-flash-latest" model alias.

Requires the GEMINI_API_KEY environment variable to be set (see .env.example).
"""

import os
import time
import requests


GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-flash-latest:generateContent"
)


SYSTEM_PROMPT = """You are the career assistant inside HireSense, a resume-ranking platform.

You help job-seeking candidates in two main ways:

1. If the user pastes or describes a job description, identify and clearly list
   the key required skills, technologies, and qualifications from it.

2. Answer general career, resume, and job-search questions helpfully and
   practically.

If you know the candidate's resume content (given below), compare it against any
job description they share and point out what matches and what's missing —
be specific and encouraging, not generic.

Keep responses concise, but make sure the answer is complete and does not stop
mid-sentence or mid-point. Use short headings and bullet points when helpful.

Do not answer questions unrelated to careers, jobs, resumes, or skills —
politely redirect back to those topics if asked something off-topic.
"""


def build_system_instruction(resume_text: str | None) -> str:
    if resume_text:
        return (
            f"{SYSTEM_PROMPT}\n\n---\n"
            f"The candidate's resume content:\n{resume_text[:4000]}"
        )

    return (
        f"{SYSTEM_PROMPT}\n\n---\n"
        "The candidate has not uploaded a resume yet."
    )


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to a .env file in the backend folder "
            "(see .env.example) or set it as an environment variable, then restart "
            "the server."
        )

    return key


def call_gemini_with_retry(
    api_key: str,
    payload: dict,
    max_retries: int = 3,
) -> requests.Response:
    """
    Calls Gemini API and retries temporary failures.

    Retries:
    - 429: Rate limit
    - 503: Temporarily unavailable / high demand
    - Network-related request failures

    Backoff:
    - 1st failure -> 2 seconds
    - 2nd failure -> 4 seconds
    """

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                GEMINI_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )

            # Temporary Gemini errors
            if response.status_code in (429, 503):

                # No more retries left
                if attempt == max_retries - 1:
                    return response

                retry_after = response.headers.get("Retry-After")

                try:
                    wait_time = float(retry_after)
                    wait_time = min(max(wait_time, 1), 30)
                except (TypeError, ValueError):
                    wait_time = 2 ** (attempt + 1)

                print(
                    f"Gemini returned {response.status_code}. "
                    f"Retrying in {wait_time:.0f} seconds..."
                )

                time.sleep(wait_time)
                continue

            # Success or non-retryable error
            return response

        except requests.exceptions.RequestException as e:

            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Could not reach the Gemini API after "
                    f"{max_retries} attempts: {str(e)}"
                ) from e

            wait_time = 2 ** (attempt + 1)

            print(
                f"Gemini request failed: {str(e)}. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError("Gemini request failed after all retry attempts.")


def chat(
    message: str,
    history: list[dict],
    resume_text: str | None,
) -> str:
    """
    message: the new user message
    history: list of {"role": "user"|"model", "content": str}, oldest first
    resume_text: the candidate's resume text, or None

    Returns the model's reply as plain text.
    """

    api_key = get_api_key()

    contents = []

    for turn in history:
        contents.append(
            {
                "role": turn["role"],
                "parts": [
                    {
                        "text": turn["content"]
                    }
                ],
            }
        )

    contents.append(
        {
            "role": "user",
            "parts": [
                {
                    "text": message
                }
            ],
        }
    )

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": build_system_instruction(resume_text)
                }
            ]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.6,

            # Increased from 1000 so longer interview/career answers
            # have enough room to finish completely.
            "maxOutputTokens": 1500,
        },
    }

    response = call_gemini_with_retry(
        api_key=api_key,
        payload=payload,
        max_retries=3,
    )

    # ---------- Error handling ----------

    if response.status_code == 429:
        raise RuntimeError(
            "Gemini rate limit is still active after automatic retries. "
            "Please wait a little and try again."
        )

    if response.status_code == 400:
        raise RuntimeError(
            "Gemini API rejected the request — check that your "
            "GEMINI_API_KEY is valid."
        )

    if response.status_code == 503:
        raise RuntimeError(
            "Gemini is temporarily unavailable due to high demand. "
            "Automatic retries were attempted; please try again shortly."
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API error ({response.status_code}): "
            f"{response.text[:300]}"
        )

    # ---------- Parse successful response ----------

    data = {}

    try:
        data = response.json()

        candidate = data["candidates"][0]

        # Gemini may return multiple text parts.
        # Join all of them instead of using only parts[0].
        parts = candidate["content"]["parts"]

        reply = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        finish_reason = candidate.get("finishReason", "unknown")

        if not reply:
            raise RuntimeError(
                f"Gemini returned no usable text "
                f"(reason: {finish_reason})."
            )

        # Useful for debugging when an answer reaches the token limit.
        if finish_reason == "MAX_TOKENS":
            print(
                "Warning: Gemini stopped because it reached "
                "the output token limit. Consider increasing "
                "maxOutputTokens if longer answers are required."
            )

        return reply

    except (KeyError, IndexError, TypeError, ValueError):
        finish_reason = (
            data.get("candidates", [{}])[0].get(
                "finishReason",
                "unknown",
            )
            if isinstance(data, dict)
            else "unknown"
        )

        raise RuntimeError(
            f"Gemini did not return a usable reply "
            f"(reason: {finish_reason}). Try rephrasing."
        )
