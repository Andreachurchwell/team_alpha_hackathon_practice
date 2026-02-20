from fastapi import Header, HTTPException
from typing import Optional
from app.core.security import verify_token

def get_current_user(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    return verify_token(token)