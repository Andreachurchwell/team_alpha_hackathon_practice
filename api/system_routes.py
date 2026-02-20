from fastapi import APIRouter
import os

router = APIRouter()

APP_ENV = os.getenv("APP_ENV", "dev")

@router.get("/health")
def health():
    return {"status": "ok", "env": APP_ENV}

@router.get("/system/profile")
def system_profile():
    return {"app": "AISE Monolith Practice", "env": APP_ENV}

@router.get("/analytics/users")
def analytics_users():
    return {"user_count": 0}  # placeholder until DB extraction

@router.get("/analytics/content")
def analytics_content():
    return {"content_count": 0}  # placeholder until DB extraction