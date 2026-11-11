from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.api.db import db, now, one

SECRET = os.environ.get("APP_SECRET_KEY", "dev-secret-change-me")
bearer = HTTPBearer(auto_error=False)


def hash_pw(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    return salt.hex() + "$" + hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def check_pw(pw: str, stored: str) -> bool:
    salt, _ = stored.split("$")
    return hmac.compare_digest(hash_pw(pw, bytes.fromhex(salt)), stored)


def create_user(email: str, pw: str, persona: str = "ml") -> dict:
    uid = "u_" + uuid.uuid4().hex[:10]
    db().execute("INSERT INTO users VALUES (?,?,?,?,?)", (uid, email.lower(), hash_pw(pw), persona, now()))
    return {"id": uid, "email": email.lower(), "persona": persona}


def make_token(uid: str) -> str:
    return jwt.encode({"sub": uid, "iat": int(now()), "exp": int(now()) + 86400 * 7}, SECRET, algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not cred:
        raise HTTPException(401, "not authenticated")
    try:
        uid = jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])["sub"]
    except Exception:  # noqa: BLE001
        raise HTTPException(401, "invalid token")
    u = one("SELECT id,email,persona FROM users WHERE id=?", uid)
    if not u:
        raise HTTPException(401, "unknown user")
    return u


def seed_reviewer() -> None:
    """Reviewer login preloaded with a persona (credentials come from env; they are shared privately, never in the repo)."""
    email = os.environ.get("REVIEWER_EMAIL", "reviewer@gigbid.demo")
    pw = os.environ.get("REVIEWER_PASSWORD", "")
    if pw and not one("SELECT id FROM users WHERE email=?", email):
        create_user(email, pw, os.environ.get("REVIEWER_PERSONA", "ml"))
