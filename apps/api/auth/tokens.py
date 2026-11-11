"""Encrypted per-user OAuth token store (Fernet). Tokens are never logged; decrypted only inside the live adapter."""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet

from apps.api.db import db, one


def _f() -> Fernet:
    key = os.environ.get("TOKEN_ENC_KEY") or base64.urlsafe_b64encode(hashlib.sha256(os.environ.get("APP_SECRET_KEY", "dev").encode()).digest())
    return Fernet(key)


def save_token(user_id: str, provider: str, token: str) -> None:
    db().execute("INSERT OR REPLACE INTO tokens VALUES (?,?,?)", (user_id, provider, _f().encrypt(token.encode())))


def get_token(user_id: str, provider: str = "upwork") -> str:
    r = one("SELECT blob FROM tokens WHERE user_id=? AND provider=?", user_id, provider)
    if not r:
        raise PermissionError("no connected account")
    return _f().decrypt(r["blob"]).decode()
