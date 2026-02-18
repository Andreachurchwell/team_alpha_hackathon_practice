"""
LEGACY MONOLITH (practice)
One file that runs, with mixed responsibilities:
- routes
- config
- "database"
- external client stub
- business logic
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Monolithic Meltdown Practice")

# --- "config" mixed in here (anti-pattern) ---
APP_ENV = os.getenv("APP_ENV", "dev")

# --- "database" mixed in here (anti-pattern) ---
FAKE_DB = {
    "users": {"andrea": {"name": "Andrea", "role": "admin"}},
    "notes": []
}

# --- models mixed in here (anti-pattern) ---
class NoteIn(BaseModel):
    user: str
    text: str

class NoteOut(BaseModel):
    user: str
    text: str
    created_at: str

# --- "external client" mixed in here (anti-pattern) ---
def fake_external_call(text: str) -> str:
    # Pretend this is calling another service/API
    return text.upper()

# --- business logic mixed in here (anti-pattern) ---
def create_note(user: str, text: str) -> NoteOut:
    if user not in FAKE_DB["users"]:
        raise HTTPException(status_code=404, detail="Unknown user")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    processed = fake_external_call(text)
    note = {
        "user": user,
        "text": processed,
        "created_at": datetime.utcnow().isoformat()
    }
    FAKE_DB["notes"].append(note)
    return NoteOut(**note)

# --- routes mixed in here ---
@app.get("/health")
def health():
    return {"status": "ok", "env": APP_ENV}

@app.get("/users/{username}")
def get_user(username: str):
    user = FAKE_DB["users"].get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/notes", response_model=NoteOut)
def add_note(payload: NoteIn):
    return create_note(payload.user, payload.text)

@app.get("/notes")
def list_notes():
    return FAKE_DB["notes"]