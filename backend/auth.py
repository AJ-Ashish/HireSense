"""
auth.py
Password hashing and JWT token creation/verification.

SECRET_KEY is read from the JWT_SECRET environment variable. The fallback
value is only for local development; set JWT_SECRET on Render (render.yaml
generates one automatically).
"""

import os
import jwt
import datetime
from passlib.context import CryptContext
from fastapi import Header, HTTPException

SECRET_KEY = os.environ.get("JWT_SECRET", "resume-iq-college-project-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24 * 7  # 7 days — convenient for demoing over multiple days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")


def get_current_user(authorization: str = Header(None)) -> dict:
    """
    FastAPI dependency: reads 'Authorization: Bearer <token>' header,
    returns {"user_id": ..., "role": ...} or raises 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1]
    return decode_token(token)


def require_role(user: dict, expected_role: str):
    if user["role"] != expected_role:
        raise HTTPException(status_code=403, detail=f"This action requires a '{expected_role}' account.")
