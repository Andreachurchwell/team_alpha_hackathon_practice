from fastapi import APIRouter, HTTPException, UploadFile, File, Header
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

# TEMP placeholders
def verify_token(token: str) -> str:
    return "andrea"

CONTENT = []  # placeholder until DB extraction

class ContentCreateRequest(BaseModel):
    title: str
    body: str

class ContentSearchRequest(BaseModel):
    query: str

@router.post("/content/create")
def content_create(req: ContentCreateRequest, authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    _user = verify_token(token)

    CONTENT.append({"title": req.title, "body": req.body})
    return {"message": "content created"}

@router.post("/content/upload")
async def content_upload(file: UploadFile = File(...), authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    _user = verify_token(token)

    raw = await file.read()
    CONTENT.append({"title": file.filename or "upload", "body": raw.decode("utf-8", errors="ignore")})
    return {"message": "uploaded"}

@router.get("/content/list")
def content_list():
    return {"items": CONTENT}

@router.post("/content/search")
def content_search(req: ContentSearchRequest):
    q = req.query.strip().lower()
    if not q:
        raise HTTPException(status_code=400, detail="query required")
    results = [c for c in CONTENT if q in c["title"].lower() or q in c["body"].lower()]
    return {"cached": False, "results": [{"title": r["title"]} for r in results]}