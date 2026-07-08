"""Auth REST endpoints: signup, login, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth.deps import get_current_user
from auth.security import create_token
from auth.service import EmailTaken, authenticate, create_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


@router.post("/signup", status_code=201)
def signup(body: Credentials) -> dict:
    try:
        user = create_user(body.email, body.password)
    except EmailTaken:
        raise HTTPException(status_code=409, detail="Email already registered")
    return {"user": user, "token": create_token(user["id"], user["email"])}


@router.post("/login")
def login(body: Credentials) -> dict:
    user = authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user": user, "token": create_token(user["id"], user["email"])}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": user}
