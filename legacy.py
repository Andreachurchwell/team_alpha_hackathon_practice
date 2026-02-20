"""
AISE Monolith Practice (Hackathon-Style)
---------------------------------------
One big FastAPI file that runs, but includes intentional anti-patterns:

Auth Service
- Register/login
- "JWT-like" tokens (homebrew, not real JWT)
- MD5 password hashing (BAD)
- Hardcoded SECRET_KEY (BAD)

Chat Service
- "Groq API" integration (stubbed)
- Conversation history saved/loaded (SQLite + globals)
- Session management
- System prompt construction with content context

Content Service
- Upload/list/search content
- Upload bug: writes to an in-memory database that vanishes (BAD)
- Search cache bug: cache never invalidated after upload (BAD)

API Gateway-ish
- CORS config
- Duplicated token verification logic copy-pasted in multiple routes (BAD)
- Mixed responsibilities everywhere (BAD)

Run:
  pip install fastapi uvicorn python-multipart
  uvicorn main:app --reload
Docs:
  http://localhost:8000/docs
"""

import os
import json
import base64
import hashlib
import hmac
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ---------------------------
# "Gateway" setup
# ---------------------------
app = FastAPI(title="AISE Monolith Practice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permissive for hackathon
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Hardcoded secrets (BAD)
# ---------------------------
SECRET_KEY = "replace_me_in_env_but_its_hardcoded_right_now"  # BAD
GROQ_API_KEY = "gsk_fake_key_replace_me"  # BAD (should be env var)
GROQ_MODEL_DEFAULT = "llama-3.3-70b-versatile"

APP_ENV = os.getenv("APP_ENV", "dev")

# ---------------------------
# Global mutable state (BAD)
# ---------------------------
SEARCH_CACHE: Dict[str, Any] = {}  # stale cache bug: never invalidated
SESSION_MEMORY: Dict[str, List[Dict[str, str]]] = {}  # per-session conversation history


# ---------------------------
# SQLite helpers (mixed in here)
# ---------------------------
DB_PATH = "app.db"

def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS content (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          body TEXT NOT NULL,
          created_at INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          session_id TEXT NOT NULL,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          created_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

init_db()


# ---------------------------
# Models
# ---------------------------
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    model: str = GROQ_MODEL_DEFAULT
    session_id: Optional[str] = None

class SummarizeRequest(BaseModel):
    text: str
    model: str = GROQ_MODEL_DEFAULT
    session_id: Optional[str] = None

class ContentCreateRequest(BaseModel):
    title: str
    body: str

class ContentSearchRequest(BaseModel):
    query: str


# ---------------------------
# Security helpers (intentionally "meh")
# ---------------------------
def md5_hash(password: str) -> str:
    # BAD: MD5 is not safe for password hashing
    return hashlib.md5(password.encode("utf-8")).hexdigest()

def sign(data: bytes) -> str:
    sig = hmac.new(SECRET_KEY.encode("utf-8"), data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

def make_token(username: str) -> str:
    payload = {"sub": username, "iat": int(time.time())}
    raw = json.dumps(payload).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    token = f"{b64}.{sign(raw)}"
    return token

def verify_token(token: str) -> str:
    """
    Returns username if valid else raises.
    (Pretends to be JWT verification, but it's homebrew.)
    """
    try:
        b64, sig = token.split(".", 1)
        raw = base64.urlsafe_b64decode(b64 + "==")
        expected = sign(raw)
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Invalid token signature")
        payload = json.loads(raw.decode("utf-8"))
        return payload["sub"]
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed token")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token payload")


# ---------------------------
# Content context (used by chat)
# ---------------------------
def get_recent_content_context(limit: int = 3) -> str:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT title, body FROM content ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No content available yet."

    snippets = []
    for r in rows:
        title = r["title"]
        body = r["body"]
        snippets.append(f"- {title}: {body[:200]}")
    return "\n".join(snippets)


# ---------------------------
# Chat "Groq" client (stubbed)
# ---------------------------
def groq_call_stub(messages: List[Dict[str, str]], model: str) -> str:
    """
    Pretend this calls Groq. We deliberately keep it simple & synchronous.
    Also intentionally ignores GROQ_API_KEY correctness.
    """
    # "LLM response" = echo last user message with tiny transform.
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    return f"(stubbed {model}) I heard you say: {last_user}"


# ---------------------------
# Chat history persistence (mixed responsibilities)
# ---------------------------
def save_chat_to_db(session_id: str, role: str, content: str):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_logs (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, int(time.time())),
    )
    conn.commit()
    conn.close()

def load_chat_from_db(session_id: str, limit: int = 20) -> List[Dict[str, str]]:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM chat_logs WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    # reverse to restore chronological order
    rows = list(reversed(rows))
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ---------------------------
# Routes: System / Health
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok", "env": APP_ENV}

@app.get("/system/profile")
def system_profile():
    # Random system route - no auth needed
    return {
        "app": "AISE Monolith Practice",
        "env": APP_ENV,
        "has_cache_entries": len(SEARCH_CACHE),
        "active_sessions": len(SESSION_MEMORY),
    }


# ---------------------------
# Routes: Auth Service
# ---------------------------
@app.post("/register")
def register(req: RegisterRequest):
    username = req.username.strip().lower()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")

    conn = db_conn()
    cur = conn.cursor()

    pw_hash = md5_hash(req.password)  # BAD
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, pw_hash, int(time.time())),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already exists")

    conn.close()
    return {"message": "registered", "username": username}

@app.post("/login")
def login(req: LoginRequest):
    username = req.username.strip().lower()
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if md5_hash(req.password) != row["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = make_token(username)
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------
# Routes: Chat Service
# NOTE: Auth verification is copy-pasted (BAD)
# ---------------------------
@app.post("/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(default=None)):
    # Copy-pasted token verification (BAD)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    username = verify_token(token)

    # Session id handling (mixed in here)
    session_id = req.session_id or f"{username}-{int(time.time())}"

    # Load conversation history from globals OR DB (messy)
    history = SESSION_MEMORY.get(session_id)
    if history is None:
        history = load_chat_from_db(session_id)
        SESSION_MEMORY[session_id] = history

    # Prompt construction with "program context"
    content_context = get_recent_content_context()
    system_prompt = (
        "You are an AI assistant for the AISE program.\n"
        "Use the following content context when helpful:\n"
        f"{content_context}"
    )

    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({"role": "user", "content": req.message})

    # Copy-pasted Groq call logic (BAD)
    reply = groq_call_stub(messages, req.model)

    # Update memory + persistence
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    save_chat_to_db(session_id, "user", req.message)
    save_chat_to_db(session_id, "assistant", reply)

    return {"reply": reply, "model": req.model, "session_id": session_id}

@app.post("/summarize")
def summarize(req: SummarizeRequest, authorization: Optional[str] = Header(default=None)):
    # Copy-pasted token verification AGAIN (BAD)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    username = verify_token(token)

    session_id = req.session_id or f"{username}-sum-{int(time.time())}"

    prompt = f"Summarize in 2-3 sentences:\n\n{req.text}"
    content_context = get_recent_content_context()
    system_prompt = (
        "You summarize for AISE program notes.\n"
        "Consider this content context:\n"
        f"{content_context}"
    )

    # Copy-pasted Groq call logic (BAD)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    summary = groq_call_stub(messages, req.model)

    # Save minimal log
    save_chat_to_db(session_id, "user", prompt)
    save_chat_to_db(session_id, "assistant", summary)

    return {"summary": summary, "model": req.model, "session_id": session_id, "original_length": len(req.text)}


# ---------------------------
# Routes: Content Service
# ---------------------------
@app.post("/content/create")
def content_create(req: ContentCreateRequest, authorization: Optional[str] = Header(default=None)):
    # Copy-pasted auth AGAIN (BAD)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    _username = verify_token(token)

    # Insert into real DB
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO content (title, body, created_at) VALUES (?, ?, ?)",
        (req.title.strip(), req.body.strip(), int(time.time())),
    )
    conn.commit()
    conn.close()

    # BUG: cache never invalidated after new content (BAD)
    # SEARCH_CACHE.clear()  # intentionally NOT doing this

    return {"message": "content created"}

@app.post("/content/upload")
async def content_upload(file: UploadFile = File(...), authorization: Optional[str] = Header(default=None)):
    # Copy-pasted auth AGAIN (BAD)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    _username = verify_token(token)

    raw = await file.read()
    body = raw.decode("utf-8", errors="ignore")
    title = file.filename or "uploaded.txt"

    # BUG: writes to an in-memory DB that vanishes (BAD)
    mem_conn = sqlite3.connect(":memory:")
    mem_cur = mem_conn.cursor()
    mem_cur.execute(
        "CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, created_at INTEGER)"
    )
    mem_cur.execute(
        "INSERT INTO content (title, body, created_at) VALUES (?, ?, ?)",
        (title, body, int(time.time())),
    )
    mem_conn.commit()
    mem_conn.close()

    # Also: cache not invalidated (BAD)
    return {"message": f"uploaded {title} (but it won't persist due to bug)"}

@app.get("/content/list")
def content_list():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, created_at FROM content ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}

@app.post("/content/search")
def content_search(req: ContentSearchRequest):
    q = req.query.strip().lower()
    if not q:
        raise HTTPException(status_code=400, detail="query required")

    # BUG: stale cache never invalidated (BAD)
    if q in SEARCH_CACHE:
        return {"cached": True, "results": SEARCH_CACHE[q]}

    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, body FROM content WHERE lower(title) LIKE ? OR lower(body) LIKE ? ORDER BY id DESC",
        (f"%{q}%", f"%{q}%"),
    )
    rows = cur.fetchall()
    conn.close()

    results = [{"id": r["id"], "title": r["title"], "preview": r["body"][:120]} for r in rows]
    SEARCH_CACHE[q] = results
    return {"cached": False, "results": results}


# ---------------------------
# Routes: "Analytics" (system-ish)
# ---------------------------
@app.get("/analytics/users")
def analytics_users():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    n = cur.fetchone()["cnt"]
    conn.close()
    return {"user_count": n}

@app.get("/analytics/content")
def analytics_content():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM content")
    n = cur.fetchone()["cnt"]
    conn.close()
    return {"content_count": n}