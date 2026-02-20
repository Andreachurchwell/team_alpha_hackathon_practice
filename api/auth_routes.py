from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# TEMP placeholders (you'll paste real helpers later)
def make_token(username: str) -> str:
    return f"token-for-{username}"

def md5_hash(pw: str) -> str:
    return pw  # placeholder

# TEMP in-memory user store (until DB extraction)
USERS = {}

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(req: RegisterRequest):
    u = req.username.strip().lower()
    if u in USERS:
        raise HTTPException(status_code=409, detail="Username already exists")
    USERS[u] = md5_hash(req.password)
    return {"message": "registered", "username": u}

@router.post("/login")
def login(req: LoginRequest):
    u = req.username.strip().lower()
    if u not in USERS or USERS[u] != md5_hash(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": make_token(u), "token_type": "bearer"}