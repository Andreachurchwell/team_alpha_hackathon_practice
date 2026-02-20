from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

# TEMP placeholders
def verify_token(token: str) -> str:
    return "andrea"  # placeholder

def groq_call_stub(messages, model: str) -> str:
    return f"(stubbed {model}) ok"

class ChatRequest(BaseModel):
    message: str
    model: str = "llama-3.3-70b-versatile"
    session_id: Optional[str] = None

class SummarizeRequest(BaseModel):
    text: str
    model: str = "llama-3.3-70b-versatile"
    session_id: Optional[str] = None

@router.post("/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    _user = verify_token(token)

    reply = groq_call_stub([{"role": "user", "content": req.message}], req.model)
    return {"reply": reply, "model": req.model, "session_id": req.session_id}

@router.post("/summarize")
def summarize(req: SummarizeRequest, authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    _user = verify_token(token)

    summary = groq_call_stub([{"role": "user", "content": req.text}], req.model)
    return {"summary": summary, "model": req.model, "session_id": req.session_id}