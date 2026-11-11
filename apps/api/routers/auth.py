from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.auth import users
from apps.api.auth.tokens import save_token
from apps.api.db import get_settings, one

router = APIRouter(prefix="/auth", tags=["auth"])


class Creds(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    persona: str = Field(default="ml", pattern="^(ml|web|data)$")


class TokenOut(BaseModel):
    token: str
    user_id: str
    email: str
    persona: str


@router.post("/register", response_model=TokenOut)
def register(c: Creds):
    if one("SELECT id FROM users WHERE email=?", c.email.lower()):
        raise HTTPException(409, "email already registered")
    u = users.create_user(c.email, c.password, c.persona)
    return TokenOut(token=users.make_token(u["id"]), user_id=u["id"], email=u["email"], persona=u["persona"])


@router.post("/login", response_model=TokenOut)
def login(c: Creds):
    u = one("SELECT * FROM users WHERE email=?", c.email.lower())
    if not u or not users.check_pw(c.password, u["pw"]):
        raise HTTPException(401, "invalid credentials")
    return TokenOut(token=users.make_token(u["id"]), user_id=u["id"], email=u["email"], persona=u["persona"])


@router.get("/me")
def me(user: dict = Depends(users.current_user)):
    return {**user, "settings": get_settings(user["id"])}


@router.post("/connect/{provider}")
def connect(provider: str, body: dict, user: dict = Depends(users.current_user)):
    """gigsim: no secret needed. upwork: OAuth 2.1 code exchange is done by the web app against Upwork; the resulting access token is
    stored ENCRYPTED here (never logged). Live mode was not exercised against a real account in this submission."""
    if provider == "upwork" and body.get("access_token"):
        save_token(user["id"], "upwork", body["access_token"])
    return {"connected": provider}
